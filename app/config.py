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

# --- Прямой API SBP (api.sbp.business) ---
# Креды ТОЛЬКО из окружения, НИКОГДА в коде/логах.
SBP_BASE = os.getenv("SBP_BASE", "https://api.sbp.business/api_v1")
SBP_LOGIN = os.getenv("SBP_LOGIN", "")
SBP_PASSWORD = os.getenv("SBP_PASSWORD", "")      # terminal_key (Basic auth)
SBP_API_KEY = os.getenv("SBP_API_KEY", "")        # x-api-key (ключ терминала)
# Куда SBP шлёт колбэк об оплате (публичный бэк Ресто на Render)
SBP_CALLBACK_URL = os.getenv(
    "SBP_CALLBACK_URL",
    "https://like-at-home-api.onrender.com/sbp/callback",
)
# Префикс заявок Ресто (не пересекается с VKP кошелька и BORD у P1)
SBP_ORDER_PREFIX = "LAH"
SBP_ORDER_SUFFIX = "SBP"
