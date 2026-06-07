# Sử dụng Base Image chuẩn của Playwright chứa sẵn Python và các driver trình duyệt
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Thiết lập thư mục làm việc trong máy ảo Docker
WORKDIR /app

# BỎ QUA requirements.txt - Cài đặt trực tiếp các thư viện bằng lệnh pip3 hệ thống
# Điều này bảo đảm các thư viện luôn được cài đặt sạch sẽ, không lo bị lỗi copy-paste
RUN pip3 install --no-cache-dir \
    pyTelegramBotAPI==4.18.0 \
    requests==2.31.0 \
    Flask==3.0.3 \
    playwright==1.44.0

# Sao chép toàn bộ mã nguồn vào Docker
COPY . .

# Mở cổng giao tiếp cho Flask Web Server
EXPOSE 8080

# Chạy file kích hoạt run.py bằng python3 chuẩn hóa
CMD ["python3", "run.py"]
