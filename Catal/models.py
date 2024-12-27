"""Модель комикса"""
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base

class Comic(Base):
    """Класс комикса"""
    __tablename__ = "comics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(unique=True)
    amount: Mapped[int] = mapped_column()
    price: Mapped[int] = mapped_column()
    publisher_id: Mapped[int] = mapped_column(ForeignKey("publishers.id"))
    publisher = relationship("Publisher", back_populates = "comics")
    writer_id: Mapped[int] = mapped_column(ForeignKey("writers.id"))
    writer = relationship("Writer", back_populates = "comics")
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"))
    artist = relationship("Artist", back_populates = "comics")

class Publisher(Base):
    """Класс издателя"""
    __tablename__ = "publishers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column()
    comics = relationship("Comic", back_populates = "publisher", cascade="all, delete-orphan")

class Writer(Base):
    """Класс сценариста"""
    __tablename__ = "writers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column()
    comics = relationship("Comic", back_populates = "writer", cascade="all, delete-orphan")

class Artist(Base):
    """Класс художника"""
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column()
    comics = relationship("Comic", back_populates = "artist", cascade="all, delete-orphan")
