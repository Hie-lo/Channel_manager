FROM python:3.12-slim

# جلوگیری از بافر output
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# نصب پیش‌نیازها
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# پوشه کار
WORKDIR /app

# نصب dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# کپی کد
COPY . .

# ساخت پوشه‌های موردنیاز
RUN mkdir -p logs secrets

# اجرا
CMD ["python", "-m", "app.main"]