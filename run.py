import os
import subprocess
import threading
from flask import Flask

# Khởi tạo Web Server Flask gọn nhẹ để duy trì kết nối với Render
app = Flask('')

@app.route('/')
def home():
    return "Bot SPX Telegram dang hoat dong 24/7!"

def run_flask():
    # Nhận cổng kết nối động từ Render
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # 1. Khởi động Web Server Flask ở luồng riêng biệt
    print("🌐 Dang khoi dong Web Server phu de lien ket voi Render...")
    threading.Thread(target=run_flask, daemon=True).start()
    
    # 2. Tự động kiểm tra xem file code chính của bạn tên là 'bot.py' hay 'Bot.py'
    bot_file = "bot.py"
    if os.path.exists("bot.py"):
        bot_file = "bot.py"
    elif os.path.exists("Bot.py"):
        bot_file = "Bot.py"
    else:
        # Nếu không tìm thấy cả hai, liệt kê các file đang có để dễ debug
        print("❌ Khong tim thay file bot.py hoac Bot.py trong thu muc!")
        print("Cac file hien tai dang co:", os.listdir("."))
        
    print(f"🤖 Da tim thay file code chinh. Dang kich hoat: {bot_file}...")
    try:
        # Khởi chạy file code chính bằng python3 để đảm bảo tính đồng bộ cao nhất
        subprocess.run(["python3", bot_file], check=True)
    except Exception as e:
        print(f"❌ Co loi xay ra khi chay file {bot_file}: {e}")

