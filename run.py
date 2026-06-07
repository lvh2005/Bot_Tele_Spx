import os
import subprocess
import threading
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Bot SPX Telegram dang hoat dong 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def fix_bot_token(file_path):
    """Tự động đè Token cũ thành biến môi trường để người dùng không cần sửa thủ công"""
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Ép file bot.py phải đọc Token từ Render thay vì dùng chuỗi cũ đã chết
    if 'os.environ.get("TELEGRAM_TOKEN")' not in content:
        import re
        fixed_content = re.sub(
            r'TELEGRAM_TOKEN\s*=\s*["\'].*?["\']', 
            'TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")', 
            content
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed_content)
        print(f"⚙️ Tự động cấu hình lại Token thành công cho file {file_path}!")

if __name__ == "__main__":
    print("🌐 Dang khoi dong Web Server phu de lien ket voi Render...")
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Tự động nhận diện file chính
    bot_file = "bot.py" if os.path.exists("bot.py") else "Bot.py"
    
    # Tiến hành ép đè cấu hình Token tự động
    fix_bot_token(bot_file)
        
    print(f"🤖 Dang kich hoat bot tai file: {bot_file}...")
    try:
        subprocess.run(["python3", bot_file], check=True)
    except Exception as e:
        print(f"❌ Co loi xay ra khi chay bot: {e}")
