"""Регистрация и авторизация"""
import re
import bcrypt
from fastapi import FastAPI, HTTPException, Depends
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from email_validator import validate_email, EmailNotValidError
from database import Base, engine, async_session
from models import Client

#Пароль должен содержать от 6 до 20 символов, хотя бы одну заглавную букву,
#а также цифру и спец. символ
REG = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*#?&])[A-Za-z\\d@$!#%*?&]{6,20}$"
app = FastAPI()

class ClientMod(BaseModel):
    """Класс клиента"""
    email: str
    password: str
    role: str = "user"

class Settings(BaseModel):
    """Настройки для JWT токена"""
    authjwt_secret_key: str = "secret"
    authjwt_token_location: set = {"cookies"}
    authjwt_cookie_csrf_protect: bool = False

async def get_db():
    """Использование базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db = async_session()
    try:
        yield db
    finally:
        await db.close()

async def create_client(client: ClientMod, db: AsyncSession):
    """Создание нового клиента"""
    client.email = client.email.strip()
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(bytes(client.password, 'utf-8'), salt)
    client_db = Client(email = client.email, password = hashed_password, role = client.role)
    db.add(client_db)
    await db.commit()
    return {"msg":"Successfully registered"}

async def get_client_by_email(email: str, db: AsyncSession):
    """Получение одного клиента"""
    email = email.strip()
    email_db = await db.execute(select(Client).where(Client.email == email))
    return  email_db.scalars().first()

async def email_validator_address(email):
    """Валидация почты"""
    try:
        valid = validate_email(email)
        return True
    except EmailNotValidError:
        return False

async def password_validator(password):
    """Валидация пароля"""
    pat = re.compile(REG)
    mat = re.search(pat, password)
    if mat:
        return True
    return False

@AuthJWT.load_config
def get_config():
    """Установка настроек токена"""
    return Settings()

@app.post("/register")
async def signup(client: ClientMod, db: AsyncSession = Depends(get_db), authorize: AuthJWT = Depends()):
    """Регистрация"""
    if await get_client_by_email(client.email, db):
        return HTTPException(status_code=409,detail="Email already exists")
    if not email_validator_address(client.email) or not password_validator(client.password):
        return HTTPException(status_code=401,detail="Bad email or password")
    access_token = authorize.create_access_token(subject=client.email, user_claims={"role":client.role})
    refresh_token = authorize.create_refresh_token(subject=client.email, user_claims={"role":client.role})
    authorize.set_access_cookies(access_token)
    authorize.set_refresh_cookies(refresh_token)
    return await create_client(client,db)

@app.post("/login")
async def login(client: ClientMod, db: AsyncSession = Depends(get_db), authorize: AuthJWT = Depends()):
    """Авторизация"""
    client_from_db = await get_client_by_email(client.email, db)
    if not client_from_db:
        raise HTTPException(status_code=404,detail="Email not found")
    access_token = authorize.create_access_token(subject=client_from_db.email, user_claims={"role": client_from_db.role})
    refresh_token = authorize.create_refresh_token(subject=client_from_db.email, user_claims={"role": client_from_db.role})
    authorize.set_access_cookies(access_token)
    authorize.set_refresh_cookies(refresh_token)
    return {"msg":"Successfully login"}

@app.delete("/logout")
async def logout(authorize: AuthJWT = Depends()):
    """Выход из аккаунта"""
    authorize.jwt_required()
    authorize.unset_jwt_cookies()
    return {"msg":"Successfully logout"}
