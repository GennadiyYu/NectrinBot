# index.py с временным путём для шрифта (Vercel-friendly)
from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from fpdf import FPDF
import tempfile
import shutil
from openai import OpenAI

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

ADMIN_CHAT_ID = 292012626  # @yudanov_g

user_states = {}
questions = [
    "Как называется ваш проект или продукт?",
    "Какова основная цель продвижения?",
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
                        print("📄 Сгенерирован бриф:", brief_text[:200])
                        try:
                            pdf_path = self.create_pdf(brief_text)
                            print("📄 PDF создан, путь:", pdf_path)
                            self.send_pdf(ADMIN_CHAT_ID, pdf_path)
                            os.remove(pdf_path)
                            self.send_message(chat_id, "Бриф отправлен менеджеру. Спасибо!")
                        except Exception as e:
                            print("❌ Ошибка при создании или отправке PDF:", str(e))
                            self.send_message(chat_id, "Произошла ошибка при формировании брифа. Менеджер уведомлён.")

                else:
                    self.send_message(chat_id, "Бриф уже составлен. Напишите /start, чтобы начать заново.")

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
        source_font = os.path.join(os.path.dirname(__file__), "../fonts/DejaVuSans.ttf")
        tmp_font_dir = "/tmp/fonts"
        os.makedirs(tmp_font_dir, exist_ok=True)
        tmp_font = os.path.join(tmp_font_dir, "DejaVuSans.ttf")
        shutil.copyfile(source_font, tmp_font)
        pdf.add_font("DejaVu", "", tmp_font, uni=True)
        pdf.set_font("DejaVu", size=12)
        pdf.multi_cell(0, 10, text)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(temp.name)
        return temp.name

    def send_pdf(self, chat_id, pdf_path):
        print("📤 Пытаюсь отправить PDF в Telegram...")
        with open(pdf_path, 'rb') as f:
            response = requests.post(f"{TELEGRAM_API_URL}/sendDocument", data={
                "chat_id": chat_id
            }, files={"document": f})
        print("📤 Ответ Telegram sendDocument:", response.status_code, response.text)
