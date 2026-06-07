```python
import os
import subprocess
import threading
from flask import Flask

# Khởi tạo một Web Server Flask cực kỳ gọn nhẹ
app = Flask('')

@app.route('/')
def home():
    # Trang web hiển thị khi truy cập vào link Render của bạn
    return "Bot SPX Telegram đang hoạt động ổn định 24/7!"

def run_flask():
    # Render sẽ cấp cổng mạng ngẫu nhiên qua biến PORT, mặc định là 8080 nếu chạy test
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # 1. Chạy Web Server Flask ở một luồng (thread) riêng để tránh bị Render tắt server
    print("🌐 Đang khởi động Web Server phụ để liên kết với Render...")
    threading.Thread(target=run_flask, daemon=True).start()
    
    # 2. Khởi chạy file code bot gốc của bạn (bot.py) mà không sửa bất cứ dòng nào
    print("🤖 Đang chạy file code bot gốc (bot.py)...")
    try:
        # Sử dụng subprocess để chạy file bot.py độc lập, giữ nguyên cấu trúc khởi tạo ban đầu
        subprocess.run(["python", "bot.py"], check=True)
    except Exception as e:
        print(f"❌ Có lỗi xảy ra trong quá trình chạy file bot.py: {e}")

```
