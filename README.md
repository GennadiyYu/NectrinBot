
# Nectarin Telegram AI Bot — OpenRouter Version

✅ Работает с https://openrouter.ai — бесплатный API-доступ к GPT-3.5, Mixtral, Claude и др.

## Переменные окружения (в Vercel)

- `OPENROUTER_API_KEY` — ключ с https://openrouter.ai
- `TELEGRAM_TOKEN` — токен от @BotFather

## Как использовать

1. Импортируй в GitHub
2. Задеплой на Vercel
3. Пропиши Webhook:
   https://api.telegram.org/bot<token>/setWebhook?url=https://<vercel-project>.vercel.app/api
