"""
Колбэк SBP об оплате (Ресто / Like at Home).

ВАЖНО (безопасность): /sbp/callback - публичный endpoint, телу НЕ доверяем.
Из тела берём только id_order, затем ПЕРЕПРОВЕРЯЕМ статус через st.php своими
кредами и засчитываем оплату только при st == CONFIRMED. Перевод в paid -
идемпотентный (UPDATE ... WHERE status != 'paid').
"""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import update
from uuid import UUID
from datetime import datetime

from ..database import get_db
from ..models import Order
from .. import sbp

router = APIRouter(prefix="/sbp", tags=["sbp"])


def _mark_paid_if_confirmed(order_id_str: str, db: Session) -> bool:
    """Перепроверяет статус в SBP и идемпотентно метит заказ оплаченным."""
    try:
        order_uuid = UUID(order_id_str)
    except (ValueError, TypeError):
        print(f"[sbp] колбэк: кривой order_id {order_id_str!r}")
        return False

    order = db.query(Order).filter(Order.id == order_uuid).first()
    if not order:
        print(f"[sbp] колбэк: заказ {order_id_str} не найден")
        return False
    if order.status == "paid":
        return True  # уже оплачен - идемпотентно

    # Перепроверка статуса своими кредами (телу колбэка не доверяем)
    st = sbp.check_status(sbp.order_id_for(order_id_str))
    if st != "CONFIRMED":
        print(f"[sbp] колбэк по {order_id_str}: st={st!r}, не засчитываю")
        return False

    # Идемпотентный перевод в paid
    res = db.execute(
        update(Order)
        .where(Order.id == order_uuid, Order.status != "paid")
        .values(status="paid", payment_confirmed_at=datetime.utcnow())
    )
    db.commit()
    if res.rowcount:
        print(f"[sbp] заказ {order_id_str} оплачен (CONFIRMED)")
    return True


@router.post("/callback")
async def sbp_callback(request: Request, db: Session = Depends(get_db)):
    """Триггер от SBP. Из тела берём только id_order, статус перепроверяем сами."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    id_order = body.get("id_order", "")
    order_id = sbp.parse_order_id(id_order)
    if not order_id:
        # не наш префикс (LAH...) или мусор - молча ок, чтобы SBP не ретраил
        return {"status": "ignored"}

    _mark_paid_if_confirmed(order_id, db)
    # Всегда 200, чтобы SBP не зацикливал ретраи; засчитываем только по st.php
    return {"status": "ok"}


@router.get("/health")
async def sbp_health():
    return {"status": "ok", "sbp_configured": sbp.configured()}
