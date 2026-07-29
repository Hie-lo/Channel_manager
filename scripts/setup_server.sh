#!/bin/bash

# اسکریپت نصب اولیه سرور Ubuntu

echo "🚀 شروع نصب پیش‌نیازها..."

# آپدیت سیستم
apt update && apt upgrade -y

# نصب Docker
echo "🐳 نصب Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# نصب Docker Compose
echo "🔧 نصب Docker Compose..."
apt install -y docker-compose-plugin

# نصب Git
echo "📦 نصب Git..."
apt install -y git

# ساخت پوشه پروژه
echo "📁 ساخت پوشه پروژه..."
mkdir -p /opt/channel-manager-bot
cd /opt/channel-manager-bot

echo "✅ نصب پیش‌نیازها کامل شد!"
echo ""
echo "📋 گام‌های بعدی:"
echo "1. کد پروژه رو در /opt/channel-manager-bot قرار بده"
echo "2. فایل .env.production رو بساز"
echo "3. فایل secrets/google_service_account.json رو قرار بده"
echo "4. docker compose up -d رو اجرا کن"