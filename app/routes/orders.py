from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID
import requests
from ..database import get_db
from ..models import Order
from ..schemas import OrderCreateSchema, OrderResponseSchema
from ..config import BOT_TOKEN, BOT_CHAT_ID, VKURSE_PAY_BOT_URL

router = APIRouter(prefix="/api/orders", tags=["orders"])

@router.post("", response_model=OrderResponseSchema)
async def create_order(
    order: OrderCreateSchema,
    request: Request,
    db: Session = Depends(get_db)
):
    """Создать новый заказ"""

    # Создаём заказ в БД
    db_order = Order(
        items=[item.dict() for item in order.items],
        total_baht=order.total_baht,
        total_rub=order.total_rub,
        order_type=order.order_type,
        context=order.context,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", ""),
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Отправляем уведомление боту (не блокируем если ошибка)
    try:
        await send_order_to_bot(db_order, db)
    except Exception as e:
        print(f"Warning: Failed to send bot notification: {e}")

    return db_order

async def send_order_to_bot(order: Order, db: Session):
    """Отправить заказ боту для обработки оплаты"""

    # Формируем сообщение
    items_text = "\n".join([
        f"  • {item['name']} × {item['qty']} = ฿{item['price'] * item['qty']}"
        for item in order.items
    ])

    context_text = ""
    if order.order_type == "dinein":
        context_text = f"🍽️ Столик: {order.context.get('table', 'N/A')}"
    else:
        context_text = f"🛵 Адрес: {order.context.get('address', 'N/A')}"

    message = f"""
🧾 Новый заказ

Заказ ID: `{order.id}`

{items_text}

Итого: ฿{order.total_baht} = ₽{order.total_rub}

{context_text}

Ссылка на оплату: {VKURSE_PAY_BOT_URL}?start={order.id}
"""

    # Отправляем в Telegram (если токены установлены)
    if not BOT_TOKEN or not BOT_CHAT_ID:
        print("Warning: BOT_TOKEN or BOT_CHAT_ID not configured")
        return

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": BOT_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            order.telegram_message_id = data.get("result", {}).get("message_id")
            db.merge(order)
            db.commit()
        else:
            print(f"Telegram API error: {response.status_code}")
    except Exception as e:
        print(f"Error sending message to bot: {e}")

@router.post("/{order_id}/request-link", response_model=OrderResponseSchema)
def request_payment_link(order_id: str, db: Session = Depends(get_db)):
    """
    Клиент нажал «получить ссылку на оплату».
    Зовём SBP z1.php напрямую (id_order=LAH{order_id}SBP) и сразу кладём
    url_pay/qr в заказ. При сбое API - откат на awaiting_link (бот-fallback).
    """
    from .. import sbp
    from ..config import SBP_CALLBACK_URL, SBP_DIRECT_ENABLED

    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    order = db.query(Order).filter(Order.id == order_uuid).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Уже есть ссылка или заказ оплачен - просто возвращаем
    if order.payment_link or order.status == "paid":
        return order

    # Прямой вызов SBP (только если включён боевой режим SBP_DIRECT_ENABLED)
    if SBP_DIRECT_ENABLED and sbp.configured():
        try:
            data = sbp.create_payment(
                rub=order.total_rub,
                id_order=sbp.order_id_for(order_id),
                callback_url=SBP_CALLBACK_URL,
            )
            order.payment_link = data.get("url_pay")
            order.payment_qr = data.get("qr")
            order.status = "link_sent"
            db.commit()
            db.refresh(order)
            print(f"[orders] SBP ссылка создана для {order_id}")
            return order
        except Exception as e:
            # Не светим креды/детали; падаем в fallback на бота
            print(f"[orders] SBP z1.php сбой для {order_id}: {type(e).__name__}")

    # Fallback: помечаем awaiting_link - бот кассы попробует через P1
    if order.status in ("pending", "awaiting_link"):
        order.status = "awaiting_link"
        db.commit()
        db.refresh(order)
    return order

@router.get("/{order_id}", response_model=OrderResponseSchema)
async def get_order(order_id: str, db: Session = Depends(get_db)):
    """Получить статус заказа"""
    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    order = db.query(Order).filter(Order.id == order_uuid).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order

@router.get("")
async def list_orders(db: Session = Depends(get_db), skip: int = 0, limit: int = 50):
    """Список последних заказов (для админки)"""
    orders = db.query(Order).order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    return [order.to_dict() for order in orders]
