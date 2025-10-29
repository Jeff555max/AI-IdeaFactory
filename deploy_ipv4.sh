#!/bin/bash

# Деплой бота на сервер с использованием IPv4
SERVER="5.183.188.107"
USER="root"
PASSWORD="C2rCrLxW6v56t6Vn"
REMOTE_DIR="/root/AI-IdeaFactory"

echo "🚀 Деплой AI-IdeaFactory бота на $SERVER..."

# Загружаем файлы через IPv4
echo "📤 Загрузка файлов..."
sshpass -p "$PASSWORD" scp -4 -o StrictHostKeyChecking=no bot_webhook.py ai_client.py prompts.py requirements.txt .env $USER@$SERVER:$REMOTE_DIR/

# Подключаемся и настраиваем
echo "⚙️ Настройка сервера..."
sshpass -p "$PASSWORD" ssh -4 -o StrictHostKeyChecking=no $USER@$SERVER << 'ENDSSH'
set -e

# Отключаем IPv6
echo "Отключение IPv6..."
sysctl -w net.ipv6.conf.all.disable_ipv6=1 2>/dev/null || true
sysctl -w net.ipv6.conf.default.disable_ipv6=1 2>/dev/null || true
sysctl -w net.ipv6.conf.lo.disable_ipv6=1 2>/dev/null || true

# Останавливаем старые процессы
echo "Остановка старых процессов..."
pkill -9 -f bot_webhook || true
pkill -9 -f cloudflared || true
sleep 2

# Переходим в директорию
cd /root/AI-IdeaFactory

# Активируем venv и обновляем зависимости
echo "Установка зависимостей..."
source venv/bin/activate
pip install -q -r requirements.txt

# Запускаем cloudflared
echo "Запуск Cloudflare Tunnel..."
nohup cloudflared tunnel --url http://127.0.0.1:8001 > /var/log/cloudflared.log 2>&1 &
sleep 8

# Получаем URL туннеля
TUNNEL_URL=$(grep -oP 'https://[^/]+\.trycloudflare\.com' /var/log/cloudflared.log | tail -1)
echo "Tunnel URL: $TUNNEL_URL"

# Обновляем .env
sed -i '/^WEBHOOK_URL=/d' .env
echo "WEBHOOK_URL=$TUNNEL_URL" >> .env

# Запускаем бота
echo "Запуск бота..."
nohup python bot_webhook.py > /var/log/bot_webhook.log 2>&1 &
sleep 5

# Проверяем статус
echo ""
echo "=== Процессы ==="
ps aux | grep cloudflared | grep -v grep
ps aux | grep bot_webhook | grep -v grep

echo ""
echo "=== Порты ==="
netstat -tlpn | grep 8001

echo ""
echo "=== Лог бота ==="
tail -10 /var/log/bot_webhook.log

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "📌 Webhook URL:"
echo "$TUNNEL_URL/8463982300:AAE5SCDdKQYzBMUXEo7fRhAd8YnvYMdWLFo"
ENDSSH

echo ""
echo "✅ Скрипт деплоя завершен!"
