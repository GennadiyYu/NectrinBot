from http.server import BaseHTTPRequestHandler
import json
import os
import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-3.5-turbo"  # можно заменить на другие, например mistralai/mixtral

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            update = json.loads(body)

            print("🔹 Получен update:", json.dumps(update, indent=2))

            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            user_text = message.get("text", "")

            if chat_id and user_text:
                try:
                    print(f"📨 Сообщение от пользователя: {user_text}")

                    # Запрос к OpenRouter
                    response = requests.post(
                        OPENROUTER_URL,
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://nectarin.ru",  # желательно указывать свой домен
                            "X-Title": "Nectarin AI Assistant"
                        },
                        json={
                            "model": MODEL,
                            "messages": [{"role": "user", "content": user_text}]
                        }
                    )

                    result = response.json()
                    reply_text = result["choices"][0]["message"]["content"].strip()
                    print(f"🤖 Ответ OpenRouter: {reply_text}")

                except Exception as e:
                    reply_text = f"Ошибка OpenRouter: {str(e)}"
                    print("❌ Ошибка OpenRouter:", str(e))

                # Отправка ответа пользователю
                tg_response = requests.post(TELEGRAM_API_URL, json={
                    "chat_id": chat_id,
                    "text": reply_text
                })

                print(f"📤 Telegram API статус: {tg_response.status_code}")
                print(f"📤 Telegram API ответ: {tg_response.text}")

        except Exception as global_error:
            print("🔥 Ошибка в Webhook:", str(global_error))

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")