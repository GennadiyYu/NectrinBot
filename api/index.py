from http.server import BaseHTTPRequestHandler
import json
import os
import requests
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

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

                    # GPT-ответ
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": user_text}]
                    )
                    reply_text = response.choices[0].message.content.strip()
                    print(f"🤖 Ответ GPT: {reply_text}")

                except Exception as e:
                    reply_text = f"Ошибка OpenAI: {str(e)}"
                    print("❌ OpenAI error:", str(e))

                # Отправка в Telegram
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