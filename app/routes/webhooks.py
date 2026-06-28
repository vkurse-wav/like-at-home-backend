from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
import requests
from ..database import get_db
from ..models import Order
from ..schemas import PaymentWebhookSchema
from ..config import BOT_TOKEN, BOT_CHAT_ID

router = APIRouter(prefix="/webhook", tags=["webhooks"])

@router.post("/payment")
async def payment_webhook(
    payload: PaymentWebhookSchema,
    db: Session = Depends(get_db)
):
    """
    Webhook от бота Дамиана об оплате заказа

    Пример:
    POST /webhook/payment
    {
        "order_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "paid",
        "amount_rub": 480
    }
    """

    try:
        order_uuid = UUID(payload.order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    # Ищем заказ
    order = db.query(Order).filter(Order.id == order_uuid).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if payload.status == "paid":
        # Подтверждаем платёж
        order.status = "paid"
        order.payment_confirmed_at = datetime.utcnow()

        db.commit()
        db.refresh(order)

        # Отправляем подтверждение в Telegram
        await send_confirmation_to_bot(order)

        return {
            "status": "success",
            "message": "Payment confirmed",
            "order_id": str(order.id),
            "order_status": order.status
        }

    elif payload.status == "failed":
        order.status = "cancelled"
        db.commit()

        return {
            "status": "error",
            "message": "Payment failed",
            "order_id": str(order.id)
        }

    return {"status": "unknown"}

async def send_confirmation_to_bot(order: Order):
    """Отправить подтверждение оплаты в Telegram"""

    message = f"""
✅ Платёж подтвержден!

Заказ ID: `{order.id}`
Статус: ОПЛАЧЕНО ✓

Сумма: ₽{order.total_rub}

Спасибо за заказ!
"""

    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": BOT_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=5
        )
    except Exception as e:
        print(f"Error sending confirmation: {e}")

@router.get("/health")
async def health_check():
    """Проверка здоровья сервера"""
    return {"status": "ok", "service": "like-at-home-backend"}
