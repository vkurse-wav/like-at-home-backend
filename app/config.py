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

# --- Kassa bot (Bot API) для общения с P1 ---
# Отдельный бот @vkurse_kassa_bot: шлёт P1 сумму, ловит ссылку и подтверждение оплаты.
KASSA_BOT_TOKEN = os.getenv("KASSA_BOT_TOKEN", "")
# chat_id партнёра P1 (на тесте - @kate_yourdevil). Заполняется после того, как P1
# один раз нажмёт /start у бота (бот узнает chat_id и мы пропишем его сюда).
P1_CHAT_ID = os.getenv("P1_CHAT_ID", "")
# Поллер бота запускается только там, где ENABLE_KASSA_BOT=true (на DO, always-on).
ENABLE_KASSA_BOT = os.getenv("ENABLE_KASSA_BOT", "false").lower() == "true"

# Сервер
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# Курс
VKP_RATE = float(os.getenv("VKP_RATE", "2.60"))
