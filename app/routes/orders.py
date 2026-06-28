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

    # Отправляем уведомление боту
    await send_order_to_bot(db_order)

    return db_order

async def send_order_to_bot(order: Order):
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

    # Отправляем в Telegram
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
            # Обновляем БД с ID сообщения
            from ..database import SessionLocal
            db = SessionLocal()
            db.merge(order)
            db.commit()
    except Exception as e:
        print(f"Error sending message to bot: {e}")

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
