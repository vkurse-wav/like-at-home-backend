from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from .database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Основные данные
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(50), default="pending", index=True)  # pending, paid, cancelled

    # Заказ
    items = Column(JSON)  # [{id, name, qty, price}, ...]
    total_baht = Column(Integer)
    total_rub = Column(Integer)

    # Контекст (стол или доставка)
    order_type = Column(String(20))  # 'dinein' или 'delivery'
    context = Column(JSON)  # {table: "5"} или {name, phone, address, comment}

    # Платёж
    payment_confirmed_at = Column(DateTime, nullable=True)
    telegram_message_id = Column(Integer, nullable=True)

    # Метаданные
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "items": self.items,
            "total_baht": self.total_baht,
            "total_rub": self.total_rub,
            "order_type": self.order_type,
            "context": self.context,
            "payment_confirmed_at": self.payment_confirmed_at.isoformat() if self.payment_confirmed_at else None,
        }
