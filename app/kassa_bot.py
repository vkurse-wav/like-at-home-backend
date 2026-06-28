"""
Касса-бот (@vkurse_kassa_bot) на Bot API для общения с P1.

P1 - это личный аккаунт партнёра с автоответчиком (на тесте - @kate_yourdevil).
Бот не может писать первым, поэтому P1 один раз жмёт /start у бота - так бот
узнаёт его chat_id (его надо прописать в .env как P1_CHAT_ID).

Что делает (long-polling, крутится на DO):
  1. Опрашивает заказы со статусом awaiting_link. Шлёт P1 сумму (только число),
     ставит link_requested.
  2. Слушает сообщения от P1:
     - ссылка (http...) -> кладёт в payment_link самого старого link_requested,
       ставит link_sent.
     - «Готово ✅» с суммой ₽ -> находит неоплаченный заказ с этой суммой, ставит paid.

Запуск (на DO): ENABLE_KASSA_BOT=true python -m app.kassa_bot
Узнать chat_id того, кто нажал /start: python -m app.kassa_bot --whoami
"""
import re
import sys
import time
from datetime import datetime

import requests

from .config import KASSA_BOT_TOKEN, P1_CHAT_ID
from .database import SessionLocal
from .models import Order

API = f"https://api.telegram.org/bot{KASSA_BOT_TOKEN}"

POLL_INTERVAL = 2          # как часто проверять заказы, ждущие ссылку (сек)
AMOUNT_TOLERANCE = 1.0     # допуск при сравнении сумм (руб)

URL_RE = re.compile(r"https?://\S+")
AMOUNT_RE = re.compile(r"([\d\s ]+(?:[.,]\d+)?)\s*₽")
DONE_RE = re.compile(r"готово", re.IGNORECASE)


# ---------- Telegram helpers ----------

def tg_get_updates(offset=None, timeout=20):
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    try:
        r = requests.get(f"{API}/getUpdates", params=params, timeout=timeout + 10)
        return r.json().get("result", [])
    except Exception as e:
        print(f"[kassa] getUpdates error: {e}")
        return []


def tg_send(chat_id, text):
    try:
        requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print(f"[kassa] sendMessage error: {e}")


# ---------- Парсинг ----------

def parse_amount(text):
    m = AMOUNT_RE.search(text or "")
    if not m:
        return None
    raw = m.group(1).replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


# ---------- Работа с заказами ----------

def send_pending_requests():
    """Найти заказы awaiting_link и отправить P1 сумму."""
    if not P1_CHAT_ID:
        return
    db = SessionLocal()
    try:
        pending = (
            db.query(Order)
            .filter(Order.status == "awaiting_link")
            .order_by(Order.created_at.asc())
            .all()
        )
        for order in pending:
            tg_send(P1_CHAT_ID, str(order.total_rub))
            order.status = "link_requested"
            db.commit()
            print(f"[kassa] P1 отправлено 'надо {order.total_rub}' по заказу {order.id}")
    except Exception as e:
        print(f"[kassa] send_pending error: {e}")
    finally:
        db.close()


def handle_link(link):
    """Ссылку привязываем к самому старому заказу в статусе link_requested."""
    db = SessionLocal()
    try:
        order = (
            db.query(Order)
            .filter(Order.status == "link_requested")
            .order_by(Order.created_at.asc())
            .first()
        )
        if not order:
            print(f"[kassa] пришла ссылка, но нет заказа в ожидании: {link}")
            return
        order.payment_link = link
        order.status = "link_sent"
        db.commit()
        print(f"[kassa] ссылка привязана к заказу {order.id}")
    except Exception as e:
        print(f"[kassa] handle_link error: {e}")
    finally:
        db.close()


def handle_payment(amount):
    """Подтверждение оплаты: ищем неоплаченный заказ с подходящей суммой."""
    db = SessionLocal()
    try:
        candidates = (
            db.query(Order)
            .filter(Order.status.in_(("link_sent", "link_requested", "awaiting_link", "pending")))
            .order_by(Order.created_at.asc())
            .all()
        )
        for order in candidates:
            if abs((order.total_rub or 0) - amount) <= AMOUNT_TOLERANCE:
                order.status = "paid"
                order.payment_confirmed_at = datetime.utcnow()
                db.commit()
                print(f"[kassa] заказ {order.id} оплачен ({amount} ₽)")
                return
        print(f"[kassa] оплата {amount} ₽, но подходящий заказ не найден")
    except Exception as e:
        print(f"[kassa] handle_payment error: {e}")
    finally:
        db.close()


def handle_p1_message(text):
    """Сообщение от P1: либо подтверждение оплаты, либо ссылка."""
    if DONE_RE.search(text):
        amount = parse_amount(text)
        if amount is not None:
            handle_payment(amount)
            return
    url = URL_RE.search(text)
    if url:
        handle_link(url.group(0))


# ---------- Режимы запуска ----------

def whoami():
    """Показать chat_id тех, кто недавно писал боту (для настройки P1_CHAT_ID)."""
    updates = tg_get_updates(timeout=2)
    seen = {}
    for u in updates:
        msg = u.get("message") or u.get("edited_message")
        if not msg:
            continue
        chat = msg.get("chat", {})
        seen[chat.get("id")] = (chat.get("username"), chat.get("first_name"), msg.get("text"))
    if not seen:
        print("Никто ещё не писал боту. Попроси P1/@kate нажать /start и повтори.")
        return
    print("Кто писал боту (chat_id -> @username, имя, последнее сообщение):")
    for cid, (un, name, txt) in seen.items():
        print(f"  {cid} -> @{un} | {name} | {txt!r}")


def run():
    if not KASSA_BOT_TOKEN:
        raise RuntimeError("KASSA_BOT_TOKEN не задан в .env")
    print(f"[kassa] запущен. P1_CHAT_ID={P1_CHAT_ID or 'НЕ ЗАДАН - оплата не пойдёт'}")
    offset = None
    last_poll = 0.0
    while True:
        # 1) Входящие сообщения (короткий long-poll)
        updates = tg_get_updates(offset=offset, timeout=10)
        for u in updates:
            offset = u["update_id"] + 1
            msg = u.get("message") or u.get("edited_message")
            if not msg:
                continue
            chat_id = str(msg.get("chat", {}).get("id"))
            text = msg.get("text", "") or ""
            if P1_CHAT_ID and chat_id == str(P1_CHAT_ID):
                handle_p1_message(text)
            else:
                # любой другой /start - подскажем chat_id в лог
                print(f"[kassa] сообщение от chat_id={chat_id} (@{msg.get('chat',{}).get('username')}): {text!r}")

        # 2) Раз в POLL_INTERVAL проверяем заказы, ждущие ссылку
        now = time.time()
        if now - last_poll >= POLL_INTERVAL:
            send_pending_requests()
            last_poll = now


if __name__ == "__main__":
    if "--whoami" in sys.argv:
        whoami()
    else:
        run()
