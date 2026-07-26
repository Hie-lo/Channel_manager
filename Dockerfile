FROM python:3.13-slim

# تنظیمات پایه
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ساخت پوشه کاری
WORKDIR /app

# نصب وابستگی‌های سیستمی
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# کپی و نصب کتابخانه‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کد برنامه
COPY . .

# اجرای ربات
CMD ["python", "-m", "app.main"]