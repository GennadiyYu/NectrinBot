from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from fpdf import FPDF
import tempfile

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-3.5-turbo"

user_states = {}

questions = [
    "Как называется ваш проект или продукт?",
    "Какова основная цель продвижения?",
    "Кто является вашей целевой аудиторией?",
    "Кто ваши основные конкуренты?",
    "Какие каналы продвижения вы планируете использовать?",
    "Каких результатов вы ожидаете?",
    "Какой у вас рекламный бюджет?",
    "Какие сроки запуска проекта?",
    "Есть ли дополнительная информация?"
]

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        update = json.loads(body)

        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_text = message.get("text", "")

        if chat_id:
            state = user_states.get(chat_id, {"step": 0, "answers": []})

            if user_text == "/start":
                state = {"step": 0, "answers": []}
                reply = "Привет! Я помогу составить бриф. " + questions[0]
            else:
                if state["step"] < len(questions):
                    state["answers"].append(user_text)
                    state["step"] += 1
                    if state["step"] < len(questions):
                        reply = questions[state["step"]]
                    else:
                        reply = "Спасибо! Формирую бриф в PDF..."
                        pdf_path = self.create_pdf(state["answers"])
                        self.send_pdf(chat_id, pdf_path)
                        os.remove(pdf_path)
                else:
                    reply = "Бриф уже собран. Напишите /start, чтобы начать заново."

            user_states[chat_id] = state

            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": reply
            })

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def create_pdf(self, answers):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Бриф от Nectarin", ln=True, align="C")
        for i, (q, a) in enumerate(zip(questions, answers), 1):
            pdf.ln(5)
            pdf.multi_cell(0, 10, f"{i}. {q}\nОтвет: {a}")
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(temp.name)
        return temp.name

    def send_pdf(self, chat_id, pdf_path):
        with open(pdf_path, 'rb') as f:
            requests.post(f"{TELEGRAM_API_URL}/sendDocument", data={
                "chat_id": chat_id
            }, files={"document": f})