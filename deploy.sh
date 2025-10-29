#!/bin/bash

# Деплой бота на сервер с отключением IPv6 и использованием IPv4
SERVER="5.183.188.107"
USER="root"

echo "=== Загрузка файлов на сервер ==="
scp -4 bot_webhook.py requirements.txt .env ${USER}@${SERVER}:/root/AI-IdeaFactory/

echo ""
echo "=== Настройка и запуск на сервере ==="
ssh -4 ${USER}@${SERVER} << 'ENDSSH'
# Отключаем IPv6
if ! grep -q "disable_ipv6" /etc/sysctl.conf; then
    echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf
    echo "net.ipv6.conf.default.disable_ipv6 = 1" >> /etc/sysctl.conf
    echo "net.ipv6.conf.lo.disable_ipv6 = 1" >> /etc/sysctl.conf
    sysctl -p
    echo "✅ IPv6 отключен"
else
    echo "✅ IPv6 уже отключен"
fi

# Останавливаем старые процессы
pkill -9 -f bot_webhook 2>/dev/null
pkill -9 -f cloudflared 2>/dev/null
sleep 2

# Переходим в директорию проекта
cd /root/AI-IdeaFactory
source venv/bin/activate

# Обновляем зависимости
pip install -q -r requirements.txt

# Запускаем cloudflared tunnel
nohup cloudflared tunnel --url http://127.0.0.1:8000 > /var/log/cloudflared.log 2>&1 &
sleep 10

# Получаем URL туннеля
TUNNEL_URL=$(grep -oP 'https://[^/]+\.trycloudflare\.com' /var/log/cloudflared.log | tail -1)

if [ -z "$TUNNEL_URL" ]; then
    echo "❌ Не удалось получить URL туннеля"
    tail -20 /var/log/cloudflared.log
    exit 1
fi

echo "✅ Tunnel URL: $TUNNEL_URL"

# Обновляем .env с URL туннеля
sed -i '/^WEBHOOK_URL=/d' .env
echo "WEBHOOK_URL=$TUNNEL_URL" >> .env

# Запускаем бота
nohup python bot_webhook.py > /var/log/bot_webhook.log 2>&1 &
sleep 5

echo ""
echo "=== Статус процессов ==="
ps aux | grep -E "(cloudflared|python.*bot_webhook)" | grep -v grep

echo ""
echo "=== Порты ==="
netstat -tlpn | grep 8000

echo ""
echo "=== Лог бота (последние 20 строк) ==="
tail -20 /var/log/bot_webhook.log

echo ""
echo "=== Webhook URL для установки ==="
WEBHOOK_URL="${TUNNEL_URL}/8463982300:AAE5SCDdKQYzBMUXEo7fRhAd8YnvYMdWLFo"
echo "$WEBHOOK_URL"

# Сохраняем URL для установки webhook
echo "$WEBHOOK_URL" > /tmp/webhook_url.txt
ENDSSH

echo ""
echo "=== Установка webhook через Telegram API ==="
WEBHOOK_URL=$(ssh -4 ${USER}@${SERVER} 'cat /tmp/webhook_url.txt')
curl -s -X POST "https://api.telegram.org/bot8463982300:AAE5SCDdKQYzBMUXEo7fRhAd8YnvYMdWLFo/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${WEBHOOK_URL}\"}" | python3 -m json.tool

echo ""
echo "✅ Деплой завершен!"
echo "Webhook URL: $WEBHOOK_URL"
