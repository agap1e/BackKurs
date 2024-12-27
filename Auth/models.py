"""Модель пользователя"""
from sqlalchemy.orm import  Mapped, mapped_column
from database import Base

class Client(Base):
    """Пользователь"""
    __tablename__ = "client"
    id: Mapped[int] = mapped_column(primary_key=True,index=True)
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column()
    role: Mapped[str] = mapped_column()