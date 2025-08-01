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
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        update = json.loads(body)

        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_text = message.get("text", "")

        if chat_id and user_text:
            try:
                # Отправка запроса в OpenAI
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": user_text}]
                )
                reply_text = response.choices[0].message.content.strip()
            except Exception as e:
                reply_text = "Ошибка AI: " + str(e)

            # Отправка ответа обратно в Telegram
            requests.post(TELEGRAM_API_URL, json={
                "chat_id": chat_id,
                "text": reply_text
            })

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")