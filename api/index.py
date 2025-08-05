# index.py с оценкой ответов GPT (релевантность)
from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from fpdf import FPDF
import tempfile
import shutil
from openai import OpenAI

STATE_FILE = "/tmp/user_states.json"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

ADMIN_CHAT_ID = 292012626

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        user_states = json.load(f)
else:
    user_states = {}

questions = [
    "Как вас зовут? Напишите ФИО?",
    "Наименование бренда, продукта или услуги?",
    "Какой ваш запрос?",
    "Планирумый бюджет на реализацию проеекта? Такой вопрос задаем ввиду порога входа в агентство, от 20 млн. рублей в год",
    "Есть ли дополнительная информация которую бы вы хотели озвучить?",
    "Как можно с вами связаться?"
]

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        update = json.loads(body)

        message = update.get("message", {})
        chat_id = str(message.get("chat", {}).get("id"))
        user_text = message.get("text", "")

        if chat_id:
            state = user_states.get(chat_id, {"step": 0, "answers": [], "mode": "brief"})

            if user_text == "/start":
                state = {"step": 0, "answers": [], "mode": "brief"}
                reply = "Здравствуйте! Я задам вам всего 6 вопросов, которые помогут понять горизонты нашего совместного сотрудничества.\n" + questions[0]
                self.send_typing(chat_id)
                self.send_message(chat_id, reply)

            elif user_text == "/reset":
                user_states[chat_id] = {"step": 0, "answers": [], "mode": "brief"}
                self.save_states()
                self.send_message(chat_id, "Ваше состояние сброшено. Напишите /start, чтобы начать заново.")

            elif user_text == "/state":
                self.send_message(chat_id, f"Ваше текущее состояние:\n{json.dumps(state, ensure_ascii=False, indent=2)}")

            elif state.get("mode") == "chat":
                self.send_typing(chat_id)
                reply = self.chat_gpt_reply(user_text)
                self.send_message(chat_id, reply)

            else:
                if state["step"] < len(questions):
                    current_question = questions[state["step"]]
                    is_valid, feedback = self.evaluate_answer(current_question, user_text)
                    if is_valid:
                        state["answers"].append(user_text)
                        state["step"] += 1
                        if state["step"] < len(questions):
                            next_q = questions[state["step"]]
                            prompt = f"Поблагодари пользователя за ответ и деликатно задай следующий вопрос:\n'{next_q}'"
                            ai_reply = self.generate_reply(prompt)
                            self.send_typing(chat_id)
                            self.send_message(chat_id, ai_reply)
                        else:
                            self.send_typing(chat_id)
                            self.send_message(chat_id, "Спасибо! Я отправил информацию нашему специалисту...")
                            brief_text = self.generate_brief(state["answers"])
                            try:
                                pdf_path = self.create_pdf(brief_text)
                                self.send_pdf(ADMIN_CHAT_ID, pdf_path)
                                os.remove(pdf_path)
                                self.send_message(chat_id, "Вижу, что он уже получил документ и скоро с вами свяжется. Ожидайте обратную связь в ближайшие 24 часа")
                                state["mode"] = "chat"
                                self.send_message(chat_id, "А пока мы ждём, я готов обсудить с вами любые вопросы по рекламе, маркетингу и продвижению.")
                            except Exception as e:
                                self.send_message(chat_id, "Произошла ошибка. Менеджер уведомлён.")
                    else:
                        self.send_typing(chat_id)
                        self.send_message(chat_id, feedback + f"\nПожалуйста, ответьте по теме.\n{current_question}")

                else:
                    self.send_message(chat_id, "Специалисты уже получили бриф. Ожидайте обратной связи. Или можем просто поболтать о рекламе")

            user_states[chat_id] = state
            self.save_states()

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def save_states(self):
        with open(STATE_FILE, "w") as f:
            json.dump(user_states, f)

    def send_message(self, chat_id, text):
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": int(chat_id),
            "text": text
        })

    def send_typing(self, chat_id):
        requests.post(f"{TELEGRAM_API_URL}/sendChatAction", json={
            "chat_id": int(chat_id),
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

    def chat_gpt_reply(self, message):
        prompt = f"Ты деловой и экспертный AI-ассистент по маркетингу. Ответь на вопрос клиента подробно и с эмпатией:\n{message}"
        return self.generate_reply(prompt)

    def evaluate_answer(self, question, answer):
        prompt = f"Оцени ответ пользователя на предмет соответствия вопросу.\nВопрос: {question}\nОтвет: {answer}\n\nЕсли ответ по теме — скажи 'OK'. Если нет — объясни, почему, и попроси ответить по теме."
        try:
            response = self.generate_reply(prompt)
            if response.strip().upper().startswith("OK"):
                return True, ""
            else:
                return False, response.strip()
        except:
            return True, ""

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
        with open(pdf_path, 'rb') as f:
            response = requests.post(f"{TELEGRAM_API_URL}/sendDocument", data={
                "chat_id": int(chat_id)
            }, files={"document": f})
