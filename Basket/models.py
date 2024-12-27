"""Модель заказа"""
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class Order(Base):
    """Класс заказа"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client: Mapped[str] = mapped_column(unique=True)
    price: Mapped[int] = mapped_column()
    items: Mapped[str] = mapped_column()