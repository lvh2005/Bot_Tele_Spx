import os
import subprocess
import threading
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Bot SPX Telegram dang hoat dong on dinh 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("🌐 Dang khoi dong Web Server phu...")
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("🤖 Dang kich hoat file Bot.py...")
    try:
        # Chạy đúng file Bot.py (chữ B viết hoa) như trên GitHub của bạn
        subprocess.run(["python", "Bot.py"], check=True)
    except Exception as e:
        print(f"❌ Loi khi chay file Bot.py: {e}")
