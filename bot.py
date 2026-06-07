import time
import re
import threading
import json
import os
import telebot
from playwright.sync_api import sync_playwright

# ===================== CẤU HÌNH =====================
TELEGRAM_TOKEN   = "8982926423:AAE-zPEAKcQD4zX-HhNCQSSOuzLLEfaafl0"
POLL_INTERVAL    = 5 * 60   # Poll mỗi 5 phút
MAX_ORDERS       = 10       # Tối đa 10 đơn / người
STATE_FILE       = "tracking_state.json"
SPX_URL_TEMPLATE = "https://tramavandon.com/spx/?tracking_number={code}"
# ====================================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# DB structure:
# tracking_db = {
#   "SPXVN123": {
#       "subscribers": {
#           "123456789": {"chat_id": 123456789, "nickname": "Áo xanh"}
#       },
#       "seen_statuses": ["key1", ...]
#   }
# }
tracking_db: dict = {}
db_lock = threading.Lock()


# ===================== LƯU / TẢI STATE =====================
def load_state():
    global tracking_db
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)

            # --- Migration: cấu trúc cũ dùng "chat_ids" → cấu trúc mới "subscribers" ---
            for code, data in raw.items():
                if "chat_ids" in data and "subscribers" not in data:
                    data["subscribers"] = {
                        str(cid): {"chat_id": cid, "nickname": ""}
                        for cid in data.pop("chat_ids")
                    }
                if "subscribers" not in data:
                    data["subscribers"] = {}
                if "seen_statuses" not in data:
                    data["seen_statuses"] = []
                # Xóa key thừa từ version cũ
                data.pop("carrier", None)

            tracking_db = raw
            print(f"✅ Đã tải state: {len(tracking_db)} mã đang theo dõi")
        except Exception as e:
            print(f"⚠️ Không tải được state: {e}")
            tracking_db = {}

def save_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(tracking_db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Không lưu được state: {e}")


# ===================== PARSE INPUT =====================
def parse_input(text: str) -> list[dict]:
    """
    Hỗ trợ nhiều mã cách nhau bằng ' | '
    Mỗi segment: `SPXVN... Tên gợi nhớ`
    Trả về: [{"code": ..., "nickname": ...}, ...]
    """
    results = []
    for seg in text.split("|"):
        seg = seg.strip()
        if not seg:
            continue
        parts = seg.split(None, 1)
        code = parts[0].upper()
        nickname = parts[1].strip() if len(parts) > 1 else ""
        if code.startswith("SPX") and len(code) >= 8:
            results.append({"code": code, "nickname": nickname})
    return results


# ===================== CÀO DỮ LIỆU SPX =====================
def cao_data_spx(code: str) -> list[dict]:
    """Trả về list [{"time":..., "status":..., "location":..., "next_location":...}]"""
    url = SPX_URL_TEMPLATE.format(code=code)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(4000)

            full_text = page.locator("body").inner_text()
            lines = [l.strip() for l in full_text.split("\n") if l.strip()]
            time_pattern = r"\d{1,2}:\d{2}\s+\d{1,2}/\d{1,2}/\d{4}"

            in_section = False
            for idx, line in enumerate(lines):
                if "Đơn đang di chuyển" in line:
                    in_section = True
                    continue
                if "Giải đáp mọi thắc mắc" in line or "Hãy cẩn thận" in line:
                    break
                if in_section and re.match(time_pattern, line):
                    entry = {"time": line, "status": "", "location": "", "next_location": ""}
                    if idx + 1 < len(lines):
                        entry["status"] = lines[idx + 1]
                    for j in range(idx + 2, min(idx + 6, len(lines))):
                        if lines[j].startswith("Location:") or "Kho:" in lines[j]:
                            entry["location"] = lines[j]
                        if lines[j].startswith("Next Location:") or "Kế tiếp:" in lines[j]:
                            entry["next_location"] = lines[j]
                    results.append(entry)
        except Exception as e:
            print(f"❌ Lỗi cào [{code}]: {e}")
        finally:
            browser.close()
    return results


# ===================== HELPER =====================
def make_key(entry: dict) -> str:
    return f"{entry['time']}|{entry['status']}"

def format_push(code: str, nickname: str, entry: dict) -> str:
    label = f"`{code}`" + (f" _({nickname})_" if nickname else "")
    lines = [
        f"🔔 *SPX Update:* {entry['status']}",
        f"━━━━━━━━━━━━━━━━━━",
        f"🟠 {label}",
        f"📍 *Status:* {entry['status']}",
        f"🕒 *Date:* {entry['time']}",
    ]
    if entry.get("location"):
        lines.append(f"📌 *Location:* {entry['location']}")
    if entry.get("next_location"):
        lines.append(f"➡️ *Next:* {entry['next_location']}")
    return "\n".join(lines)

def get_user_orders(chat_id: int) -> list[dict]:
    uid = str(chat_id)
    return [
        {"code": code, "nickname": data["subscribers"][uid].get("nickname", "")}
        for code, data in tracking_db.items()
        if uid in data.get("subscribers", {})
    ]


# ===================== ĐĂNG KÝ THEO DÕI =====================
def register_order(chat_id: int, code: str, nickname: str) -> tuple[bool, str]:
    uid = str(chat_id)

    with db_lock:
        orders = get_user_orders(chat_id)
        if any(o["code"] == code for o in orders):
            return False, f"ℹ️ Bạn đã theo dõi `{code}` rồi!"
        if len(orders) >= MAX_ORDERS:
            return False, f"⚠️ Đã đạt giới hạn {MAX_ORDERS} đơn. Dùng `/stop` để bỏ bớt."

    entries = cao_data_spx(code)
    if not entries:
        return False, f"❌ Không tìm thấy đơn `{code}`. Kiểm tra lại mã nhé!"

    seen = set(make_key(e) for e in entries)
    latest = entries[0]

    with db_lock:
        if code not in tracking_db:
            tracking_db[code] = {"subscribers": {}, "seen_statuses": []}
        tracking_db[code]["subscribers"][uid] = {"chat_id": chat_id, "nickname": nickname}
        existing = set(tracking_db[code].get("seen_statuses", []))
        tracking_db[code]["seen_statuses"] = list(existing | seen)
        save_state()

    label = f"`{code}`" + (f" _({nickname})_" if nickname else "")
    confirm = (
        f"✅ *Đã đăng ký theo dõi:*\n"
        f"🟠 {label}\n"
        f"🔔 Bot sẽ tự push khi có cập nhật mới.\n\n"
        f"📍 *Trạng thái mới nhất:*\n"
        f"🕒 {latest['time']}\n"
        f"➡️ {latest['status']}"
    )
    if latest.get("location"):
        confirm += f"\n📌 {latest['location']}"
    return True, confirm


# ===================== BACKGROUND POLLING =====================
def polling_loop():
    print("🔄 Background polling đã khởi động...")
    while True:
        time.sleep(POLL_INTERVAL)
        with db_lock:
            snapshot = {
                code: {
                    "subscribers": dict(data.get("subscribers", {})),
                    "seen_statuses": list(data.get("seen_statuses", [])),
                }
                for code, data in tracking_db.items()
            }

        for code, data in snapshot.items():
            try:
                print(f"🔍 Poll: {code}")
                entries = cao_data_spx(code)
                if not entries:
                    continue

                seen = set(data["seen_statuses"])
                new_entries = [e for e in entries if make_key(e) not in seen]
                if not new_entries:
                    continue

                with db_lock:
                    if code not in tracking_db:
                        continue
                    for e in new_entries:
                        seen.add(make_key(e))
                    tracking_db[code]["seen_statuses"] = list(seen)
                    subs = dict(tracking_db[code].get("subscribers", {}))
                    save_state()

                for entry in reversed(new_entries):
                    for uid, sub in subs.items():
                        nickname = sub.get("nickname", "")
                        msg = format_push(code, nickname, entry)
                        try:
                            bot.send_message(sub["chat_id"], msg, parse_mode="Markdown")
                        except Exception as e:
                            print(f"  ⚠️ Không gửi được tới {sub['chat_id']}: {e}")

                print(f"  ✅ Pushed {len(new_entries)} update cho {code}")

            except Exception as e:
                print(f"❌ Lỗi poll [{code}]: {e}")


# ===================== HANDLERS =====================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "🤖 *Bot Theo Dõi Đơn Hàng SPX*\n\n"
        "📥 *Thêm đơn:*\n"
        "`/add SPXVN... Tên gợi nhớ`\n"
        "Hoặc nhắn thẳng mã vào đây cũng được!\n\n"
        "📌 *Thêm nhiều mã cùng lúc* — ngăn bằng ` | `:\n"
        "`SPXVN... Áo xanh | SPXVN... Quần`\n\n"
        "📋 *Lệnh:*\n"
        "`/add` — Thêm đơn theo dõi\n"
        "`/list` — Danh sách đơn đang theo dõi\n"
        "`/stop SPXVN...` — Dừng 1 đơn\n"
        "`/stopall` — Dừng tất cả\n"
    )
    bot.reply_to(message, text, parse_mode="Markdown")


def process_add(message):
    """Xử lý thêm đơn — dùng chung cho /add và nhắn thẳng"""
    raw = re.sub(r"^/add\s*", "", message.text, flags=re.IGNORECASE).strip()
    entries = parse_input(raw)

    if not entries:
        bot.reply_to(message,
            "⚠️ Không nhận ra mã SPX.\n"
            "Ví dụ: `SPXVN063346521046 Áo xanh`",
            parse_mode="Markdown")
        return

    chat_id = message.chat.id
    for entry in entries:
        code, nickname = entry["code"], entry["nickname"]
        status_msg = bot.send_message(
            chat_id,
            f"🔍 Đang kiểm tra `{code}`" + (f" _({nickname})_" if nickname else "") + "...",
            parse_mode="Markdown"
        )
        success, reply = register_order(chat_id, code, nickname)
        bot.edit_message_text(reply, chat_id=chat_id,
                              message_id=status_msg.message_id, parse_mode="Markdown")


@bot.message_handler(commands=['add'])
def cmd_add(message):
    process_add(message)


@bot.message_handler(commands=['list'])
def cmd_list(message):
    chat_id = message.chat.id
    with db_lock:
        orders = get_user_orders(chat_id)

    if not orders:
        bot.reply_to(message,
            "📭 Bạn chưa theo dõi đơn nào.\n"
            "Dùng `/add SPXVN... Tên` để thêm.", parse_mode="Markdown")
        return

    lines = []
    for o in orders:
        line = f"🟠 `{o['code']}`"
        if o["nickname"]:
            line += f" — _{o['nickname']}_"
        lines.append(line)

    bot.reply_to(message,
        f"📦 *Đang theo dõi ({len(orders)}/{MAX_ORDERS}):*\n\n" + "\n".join(lines),
        parse_mode="Markdown")


@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Dùng: `/stop SPXVN...`", parse_mode="Markdown")
        return
    code = parts[1].upper()
    uid  = str(message.chat.id)
    with db_lock:
        if code in tracking_db and uid in tracking_db[code].get("subscribers", {}):
            nickname = tracking_db[code]["subscribers"][uid].get("nickname", "")
            del tracking_db[code]["subscribers"][uid]
            if not tracking_db[code]["subscribers"]:
                del tracking_db[code]
            save_state()
            label = f"`{code}`" + (f" _({nickname})_" if nickname else "")
            bot.reply_to(message, f"✅ Đã dừng theo dõi {label}.", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"⚠️ Bạn không theo dõi mã `{code}`.", parse_mode="Markdown")


@bot.message_handler(commands=['stopall'])
def cmd_stopall(message):
    uid = str(message.chat.id)
    count = 0
    with db_lock:
        for code in list(tracking_db.keys()):
            if uid in tracking_db[code].get("subscribers", {}):
                del tracking_db[code]["subscribers"][uid]
                count += 1
                if not tracking_db[code]["subscribers"]:
                    del tracking_db[code]
        save_state()
    bot.reply_to(message, f"✅ Đã dừng theo dõi *{count}* đơn hàng.", parse_mode="Markdown")


@bot.message_handler(func=lambda m: True)
def handle_plain(message):
    raw = message.text.strip()
    if parse_input(raw):
        process_add(message)
    else:
        bot.reply_to(message,
            "🤔 Không nhận ra mã SPX.\n"
            "Dùng `/add SPXVN... Tên gợi nhớ` hoặc `/help` để xem hướng dẫn.",
            parse_mode="Markdown")


# ===================== MAIN =====================
if __name__ == "__main__":
    load_state()
    threading.Thread(target=polling_loop, daemon=True).start()
    print("🤖 Bot đang chạy... (Ctrl+C để tắt)")
    bot.infinity_polling()
