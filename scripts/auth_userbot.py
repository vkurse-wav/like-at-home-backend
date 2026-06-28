"""
Одноразовая авторизация userbot-сессии Telethon.

Запусти ОДИН раз локально:
    python scripts/auth_userbot.py

Введёшь номер телефона и код из Telegram. После этого появится файл
userbot_session.session - его нужно положить рядом с приложением на DO
(или примонтировать в Docker), и userbot будет заходить без повторного кода.

Нужны в .env: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE
(API_ID/API_HASH берутся на https://my.telegram.org → API development tools)
"""
import os
import sys

# Чтобы импортировать app.config при запуске из корня проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient
from app.config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_PHONE,
    SESSION_PATH,
)


def main():
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("❌ Задай TELEGRAM_API_ID и TELEGRAM_API_HASH в .env")
        return

    with TelegramClient(SESSION_PATH, TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
        client.start(phone=TELEGRAM_PHONE or None)
        me = client.get_me()
        print(f"✅ Авторизован как: {me.first_name} (@{me.username})")
        print(f"✅ Сессия сохранена в {SESSION_PATH}.session")


if __name__ == "__main__":
    main()
