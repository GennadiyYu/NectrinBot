# Nectarin Telegram AI Bot (Vercel-ready)

## 🔧 Установка и деплой

1. Склонируй этот проект в GitHub
2. Перейди на https://vercel.com/import/git и выбери репозиторий
3. Установи переменные окружения:
   - OPENAI_API_KEY — твой ключ OpenAI
   - TELEGRAM_TOKEN — токен Telegram-бота (от @BotFather)

4. После успешного деплоя получи URL, например:
   https://nectarin-bot.vercel.app/api

5. Пропиши Webhook:
   https://api.telegram.org/bot<твой_токен>/setWebhook?url=https://nectarin-bot.vercel.app/api