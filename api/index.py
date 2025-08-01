# Обновлённый index.py — бот отправляет PDF-бриф лично @yudanov_g (ID 292012626)
from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from fpdf import FPDF
import tempfile
from openai import OpenAI

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

ADMIN_CHAT_ID = 292012626  # @yudanov_g

user_states = {}
questions = [
    "Как Вас зовут? Пожалуйста укажите свое ФИО, что бы мы знали как к Вам обращаться",
    "Как называется ваш проект или продукт?",
    "Какова основная цель продвижения?",
    "Кто является вашей целевой аудиторией?",
    "Кто ваши основные конкуренты?",
    "Какие каналы продвижения вы планируете использовать?",
    "Каких результатов вы ожидаете?",
    "Какой у вас рекламный бюджет?",
    "Какие сроки запуска проекта?",
    "Оставьте Ваш номер телефона для связи."
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
                reply = "Здравствуйте! Я помогу вам составить проектный бриф.\n" + questions[0]
                self.send_typing(chat_id)
                self.send_message(chat_id, reply)
            else:
                if state["step"] < len(questions):
                    state["answers"].append(user_text)
                    state["step"] += 1
                    if state["step"] < len(questions):
                        question_text = questions[state["step"]]
                        prompt = f"Поблагодари пользователя за ответ и деликатно задай следующий вопрос:\n'{question_text}'"
                        ai_reply = self.generate_reply(prompt)
                        self.send_typing(chat_id)
                        self.send_message(chat_id, ai_reply)
                    else:
                        self.send_typing(chat_id)
                        self.send_message(chat_id, "Спасибо! Я формирую бриф...")
                        brief_text = self.generate_brief(state["answers"])
                        pdf_path = self.create_pdf(brief_text)
                        self.send_pdf(ADMIN_CHAT_ID, pdf_path)
                        os.remove(pdf_path)
                        self.send_message(chat_id, "Бриф отправлен менеджеру. Спасибо!")
                else:
                    self.send_message(chat_id, "Бриф уже составлен. Ожидайте обратной связи в ближайшие 24 часа. Спасибо за обращение!")

            user_states[chat_id] = state

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def send_message(self, chat_id, text):
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text
        })

    def send_typing(self, chat_id):
        requests.post(f"{TELEGRAM_API_URL}/sendChatAction", json={
            "chat_id": chat_id,
            "action": "typing"
        })

    def generate_reply(self, prompt):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Ошибка AI: {str(e)}"

    def generate_brief(self, answers):
        combined = "\n".join([f"{i+1}. {q}\nОтвет: {a}" for i, (q, a) in enumerate(zip(questions, answers))])
        prompt = f"Составь деловой проектный бриф по следующим ответам клиента:\n{combined}\n\nСтруктурируй текст с подзаголовками и деловым стилем."
        try:
            response = client.chat.completions.create(
                model="openai/gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Ошибка генерации брифа: {str(e)}"

    def create_pdf(self, text):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, text)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(temp.name)
        return temp.name

    def send_pdf(self, chat_id, pdf_path):
        with open(pdf_path, 'rb') as f:
            requests.post(f"{TELEGRAM_API_URL}/sendDocument", data={
                "chat_id": chat_id
            }, files={"document": f})
