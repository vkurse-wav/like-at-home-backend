import os
from dotenv import load_dotenv

load_dotenv()

# БД
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/like_at_home")

# Telegram бот
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_CHAT_ID = os.getenv("BOT_CHAT_ID", "")  # ID Дамиана в Telegram

# VKURSE Pay
VKURSE_PAY_BOT_URL = "https://t.me/vkurse_pay_bot"

# Сервер
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# Курс
VKP_RATE = float(os.getenv("VKP_RATE", "2.60"))
