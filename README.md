
# Nectarin AI Bot (PDF Brief Generator)

## Что умеет:
- Пошаговый бриф по 9 вопросам
- Сбор всех ответов
- Генерация PDF-файла с итогами
- Отправка PDF прямо в Telegram

## Как запустить:
1. Развернуть проект на Vercel
2. Добавить переменные:
   - `OPENROUTER_API_KEY`
   - `TELEGRAM_TOKEN`
3. Прописать Webhook:
   https://api.telegram.org/bot<token>/setWebhook?url=https://<project>.vercel.app/api
