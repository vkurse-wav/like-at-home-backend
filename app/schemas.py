from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class OrderItemSchema(BaseModel):
    id: str
    name: str
    qty: int
    price: int

class OrderCreateSchema(BaseModel):
    items: List[OrderItemSchema]
    total_baht: int
    total_rub: int
    order_type: str  # 'dinein' или 'delivery'
    context: Dict  # {table: "5"} или {name, phone, address, comment}

class OrderResponseSchema(BaseModel):
    id: str
    created_at: datetime
    status: str
    items: List[OrderItemSchema]
    total_baht: int
    total_rub: int
    order_type: str
    context: Dict
    payment_confirmed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaymentWebhookSchema(BaseModel):
    order_id: str
    status: str  # 'paid' или 'failed'
    payment_method: Optional[str] = "telegram"
    amount_rub: Optional[int] = None
