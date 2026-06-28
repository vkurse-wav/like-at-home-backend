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

# --- Userbot (Telethon) для общения с P1 ---
# API_ID / API_HASH берутся на https://my.telegram.org → API development tools
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")          # твой номер для входа
P1_USERNAME = os.getenv("P1_USERNAME", "")               # @username или id чата P1
# Userbot запускается только там, где ENABLE_USERBOT=true (на DO, он всегда онлайн)
ENABLE_USERBOT = os.getenv("ENABLE_USERBOT", "false").lower() == "true"
# Путь к файлу сессии Telethon (создаётся один раз скриптом авторизации)
SESSION_PATH = os.getenv("SESSION_PATH", "userbot_session")

# Сервер
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# Курс
VKP_RATE = float(os.getenv("VKP_RATE", "2.60"))
