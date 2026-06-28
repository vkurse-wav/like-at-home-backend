"""
Userbot на аккаунте Дамиана (Telethon) для общения с P1.

Что делает:
  1. Каждые N секунд смотрит заказы со статусом awaiting_link.
     Для каждого пишет P1 сумму (только число) и ждёт ответную ссылку,
     кладёт её в order.payment_link, ставит статус link_sent.
  2. Слушает входящие сообщения от P1. Когда приходит «Готово ✅» с суммой
     в рублях - находит заказ с такой суммой и метит его paid.

Запуск (на DO, где бот всегда онлайн):
    ENABLE_USERBOT=true python -m app.userbot

Сессия создаётся один раз скриптом scripts/auth_userbot.py.
"""
import asyncio
import re
from datetime import datetime

from telethon import TelegramClient, events

from .config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    P1_USERNAME,
    SESSION_PATH,
)
from .database import SessionLocal
from .models import Order

# Интервал опроса заказов, ожидающих ссылку (сек)
POLL_INTERVAL = 3
# Сколько ждём ответную ссылку от P1 (сек)
LINK_TIMEOUT = 60
# Допуск при сравнении сумм (руб). Суммы почти всегда уникальны по копейкам.
AMOUNT_TOLERANCE = 1.0

# Регексы
URL_RE = re.compile(r"https?://\S+")
# Сумма в рублях в начале сообщения: «35560.00 ₽» / «620 ₽» / «5 555,50 ₽»
AMOUNT_RE = re.compile(r"([\d\s]+(?:[.,]\d+)?)\s*₽")
DONE_RE = re.compile(r"готово", re.IGNORECASE)


def _parse_amount(text: str):
    """Достаём сумму в рублях из текста сообщения P1."""
    m = AMOUNT_RE.search(text)
    if not m:
        return None
    raw = m.group(1).replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _find_unpaid_order_by_amount(db, amount: float):
    """Самый старый неоплаченный заказ с подходящей суммой."""
    candidates = (
        db.query(Order)
        .filter(Order.status.in_(("awaiting_link", "link_sent", "pending")))
        .order_by(Order.created_at.asc())
        .all()
    )
    for order in candidates:
        if abs((order.total_rub or 0) - amount) <= AMOUNT_TOLERANCE:
            return order
    return None


async def _request_link_for_order(client, order_id, total_rub):
    """Пишем P1 сумму и ждём ответную ссылку. Возвращаем URL или None."""
    try:
        async with client.conversation(P1_USERNAME, timeout=LINK_TIMEOUT) as conv:
            await conv.send_message(f"Надо {total_rub}")
            resp = await conv.get_response()
            url_match = URL_RE.search(resp.raw_text or "")
            if url_match:
                return url_match.group(0)
            # Иногда ответ приходит несколькими сообщениями - ждём ещё одно
            resp2 = await conv.get_response()
            url_match = URL_RE.search(resp2.raw_text or "")
            if url_match:
                return url_match.group(0)
    except asyncio.TimeoutError:
        print(f"[userbot] P1 не ответил за {LINK_TIMEOUT}с по заказу {order_id}")
    except Exception as e:
        print(f"[userbot] Ошибка запроса ссылки для {order_id}: {e}")
    return None


async def poll_loop(client):
    """Фоновый цикл: обрабатываем заказы, ждущие ссылку."""
    while True:
        db = SessionLocal()
        try:
            pending = (
                db.query(Order)
                .filter(Order.status == "awaiting_link")
                .filter(Order.payment_link.is_(None))
                .order_by(Order.created_at.asc())
                .all()
            )
            for order in pending:
                oid = str(order.id)
                total_rub = order.total_rub
                print(f"[userbot] Запрашиваю ссылку у P1 для {oid} на {total_rub} ₽")
                link = await _request_link_for_order(client, oid, total_rub)
                if link:
                    order.payment_link = link
                    order.status = "link_sent"
                    db.commit()
                    print(f"[userbot] Ссылка получена для {oid}: {link}")
        except Exception as e:
            print(f"[userbot] poll_loop error: {e}")
        finally:
            db.close()
        await asyncio.sleep(POLL_INTERVAL)


def register_handlers(client):
    """Слушаем входящие от P1 об успешной оплате."""

    @client.on(events.NewMessage(chats=P1_USERNAME))
    async def on_p1_message(event):
        text = event.raw_text or ""
        if not DONE_RE.search(text):
            return  # не сообщение об оплате
        amount = _parse_amount(text)
        if amount is None:
            print(f"[userbot] Не смог разобрать сумму в: {text!r}")
            return

        db = SessionLocal()
        try:
            order = _find_unpaid_order_by_amount(db, amount)
            if not order:
                print(f"[userbot] Оплата на {amount} ₽, но заказ не найден")
                return
            order.status = "paid"
            order.payment_confirmed_at = datetime.utcnow()
            db.commit()
            print(f"[userbot] Заказ {order.id} оплачен ({amount} ₽)")
        except Exception as e:
            print(f"[userbot] Ошибка обработки оплаты: {e}")
        finally:
            db.close()


async def main():
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise RuntimeError("TELEGRAM_API_ID / TELEGRAM_API_HASH не заданы в .env")
    if not P1_USERNAME:
        raise RuntimeError("P1_USERNAME не задан в .env")

    client = TelegramClient(SESSION_PATH, TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.start()  # сессия уже авторизована скриптом auth_userbot.py
    print("[userbot] Запущен и слушает P1")

    register_handlers(client)
    await poll_loop(client)


if __name__ == "__main__":
    asyncio.run(main())
