"""Добавление заказа"""
from pika import ConnectionParameters, BlockingConnection
from fastapi import FastAPI, HTTPException, Depends, Cookie
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_jwt_auth import AuthJWT
from database import engine, Base, async_session
from models import Order
CONNECTION_PARAMS = ConnectionParameters(host="localhost")
app = FastAPI()

class Settings(BaseModel):
    """Настройки для проверки JWT токена"""
    authjwt_secret_key: str = "secret"
    authjwt_token_location: set = {"cookies"}
    authjwt_cookie_csrf_protect: bool = False

class OrderMod(BaseModel):
    """Класс комикса"""
    email: str = None
    price: int
    items: str

async def get_db():
    """Использование базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db = async_session()
    try:
        yield db
    finally:
        await db.close()

async def create_order(order: OrderMod, db: AsyncSession):
    """Создание заказа"""
    order_db = Order(client = order.email, price = order.price, items = order.items)
    db.add(order_db)
    await db.commit()
    return {"msg":"Successfully created order"}
def callback(ch, method, properties, body):
    print(body.decode())
    ch.basic_ack(delivery_tag=method.delivery_tag)

async def consumer():
    with BlockingConnection(CONNECTION_PARAMS) as conn:
        with conn.channel() as ch:
            ch.queue_declare(queue="comics")
            ch.basic_consume(
                queue = "comics",
                on_message_callback = callback
            )
            ch.start_consuming()

@AuthJWT.load_config
def get_config():
    """Установка настроек токена"""
    return Settings()

#async def get_jwt_token_role(access_token_cookie: str | None = Cookie(default=None), authorize: AuthJWT = Depends()):
    """Роль пользователя"""
    #return authorize.get_raw_jwt(access_token_cookie)["role"]

@app.get("/order")
async def new_comic():
    """Создание заказа"""
    await consumer()
    """order.email = authorize.get_raw_jwt(access_token_cookie)["sub"]
    if not order.email:
        return HTTPException(status_code=404,detail="Email not found")
    return await create_order(order,db)"""

#order: OrderMod, db: AsyncSession = Depends(get_db), access_token_cookie: str = Cookie(), authorize: AuthJWT = Depends()