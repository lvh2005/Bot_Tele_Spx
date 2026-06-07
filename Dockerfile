```dockerfile
# Sử dụng Base Image chuẩn của Playwright chứa sẵn Python và các driver trình duyệt cần thiết
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Thiết lập thư mục làm việc trong máy ảo Docker
WORKDIR /app

# Sao chép danh sách thư viện và tiến hành cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào Docker
COPY . .

# Cổng giao tiếp cho Flask Web Server (tương thích với file run.py)
EXPOSE 8080

# Chạy file kích hoạt run.py (file này sẽ tự khởi chạy bot.py sau khi bật web server)
CMD ["python", "run.py"]

```
