"""Добавление комикса, сценариста, художника и издательства"""
import re
from pika import ConnectionParameters, BlockingConnection
from fastapi import FastAPI, HTTPException, Depends, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi_jwt_auth import AuthJWT
from database import engine, Base, async_session
from models import Comic, Writer, Publisher, Artist

#Название комикса от 1 до 100 символов, также цифры и спец. символы
REG_COMIC = "^[A-Za-z0-9\\s\\-_,\\.:;()''""#]+$"
#ФИО сценариста или художника
REG_NAME = "^([a-zA-Z]{2,}\\s[a-zA-Z]{1,}\\'?-?[a-zA-Z]{2,}\\s?([a-zA-Z]{1,})?)"
#Название издателя
REG_PUB = "^[A-Za-z0-9\\s\\-_,\\.:;()''""!]+$"
CONNECTION_PARAMS = ConnectionParameters(host="localhost")
app = FastAPI()

class Settings(BaseModel):
    """Настройки для проверки JWT токена"""
    authjwt_secret_key: str = "secret"
    authjwt_token_location: set = {"cookies"}
    authjwt_cookie_csrf_protect: bool = False

class ComicMod(BaseModel):
    """Класс комикса"""
    title: str
    amount: str
    price: str
    publisher: str
    writer: str
    artist: str

class PublisherMod(BaseModel):
    """Класс издателя"""
    name: str

class WriterMod(BaseModel):
    """Класс сценариста"""
    name: str

class ArtistMod(BaseModel):
    """Класс художника"""
    name: str

async def get_db():
    """Использование базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db = async_session()
    try:
        yield db
    finally:
        await db.close()

async def validator(valid, reg):
    """Валидация пароля"""
    pat = re.compile(reg)
    mat = re.search(pat, valid)
    if mat:
        return True
    return False

async def create_comic(comic: ComicMod, db: AsyncSession):
    """Создание нового комикса"""
    comic.title = comic.title.strip()
    comic_writer = await get_writer_by_name(comic.writer, db)
    comic_publisher = await get_publisher_by_name(comic.publisher, db)
    comic_artist = await get_artist_by_name(comic.artist, db)
    try:
        if not comic.amount.isnumeric() or int(comic.amount)<0:
            return HTTPException(status_code=401,detail="Bad amount")
        if not comic.price.isdigit() or float(comic.price)<0:
            return HTTPException(status_code=401,detail="Bad price")
        if not validator(comic.title, REG_COMIC):
            return HTTPException(status_code=401,detail="Bad title")
        if comic_writer is None:
            comic_writer = await create_writer(WriterMod(name = comic.writer), db)
        if comic_publisher is None:
            comic_publisher = await create_publisher(PublisherMod(name = comic.publisher), db)
        if comic_artist is None:
            comic_artist = await create_artist(ArtistMod(name = comic.artist), db)
        comic_db = Comic(title = comic.title, amount = int(comic.amount), price = float(comic.price),
                        publisher_id = comic_publisher.id, writer_id = comic_writer.id,
                        artist_id = comic_artist.id)
        db.add(comic_db)
        await db.commit()
        return {"msg":"Successfully added comic"}
    except HTTPException as e:
        return e

async def create_publisher(pub: PublisherMod, db: AsyncSession):
    """Создание нового издательства"""
    pub.name = pub.name.strip()
    if not validator(pub.name, REG_PUB):
        raise HTTPException(status_code=401,detail="Bad publisher name")
    if await get_publisher_by_name(pub.name, db):
        raise HTTPException(status_code=409,detail="Publisher already exists")
    pub_db = Publisher(name = pub.name)
    db.add(pub_db)
    await db.commit()
    await db.refresh(pub_db)
    return pub_db

async def create_writer(writ: WriterMod, db: AsyncSession):
    """Создание нового сценариста"""
    writ.name = writ.name.strip()
    if not validator(writ.name, REG_NAME):
        raise HTTPException(status_code=401,detail="Bad writer")
    if await get_writer_by_name(writ.name, db):
        raise HTTPException(status_code=409,detail="Writer already exists")
    writ_db = Writer(name = writ.name)
    db.add(writ_db)
    await db.commit()
    await db.refresh(writ_db)
    return writ_db

async def create_artist(art: ArtistMod, db: AsyncSession):
    """Создание нового художника"""
    art.name = art.name.strip()
    if not validator(art.name, REG_NAME):
        raise HTTPException(status_code=401,detail="Bad artist")
    if await get_artist_by_name(art.name, db):
        raise HTTPException(status_code=409,detail="Artist already exists")
    art_db = Artist(name = art.name)
    db.add(art_db)
    await db.commit()
    await db.refresh(art_db)
    return art_db

async def get_comic_by_title(title: str, db: AsyncSession):
    """Получение комикса"""
    title = title.strip()
    title_db = await db.execute(select(Comic).where(Comic.title == title))
    return title_db.scalar()

async def get_writer_by_name(name: str, db: AsyncSession):
    """Получение сценариста"""
    name = name.strip()
    name_db = await db.execute(select(Writer).where(Writer.name == name))
    return name_db.scalars().first()

async def get_artist_by_name(name: str, db: AsyncSession):
    """Получение художника"""
    name = name.strip()
    name_db = await db.execute(select(Artist).where(Artist.name == name))
    return name_db.scalars().first()

async def get_publisher_by_name(name: str, db: AsyncSession):
    """Получение издателя"""
    name = name.strip()
    name_db = await db.execute(select(Publisher).where(Publisher.name == name))
    return name_db.scalars().first()

async def producer():
    with BlockingConnection(CONNECTION_PARAMS) as conn:
        with conn.channel() as ch:
            ch.queue_declare(queue="comics")
            ch.basic_publish(
                exchange = "",
                routing_key = "comics",
                body = "Hello"
            )
            print("Message sent")

@AuthJWT.load_config
def get_config():
    """Установка настроек токена"""
    return Settings()

#async def get_jwt_token_role(access_token_cookie: str | None = Cookie(default=None), authorize: AuthJWT = Depends()):
    """Роль пользователя"""
    #return authorize.get_raw_jwt(access_token_cookie)["role"]

@app.post("/create/comic")
async def new_comic(comic: ComicMod, db: AsyncSession = Depends(get_db)):
    """Создание комикса"""
    #if await get_jwt_token_role() != "admin":
        #return HTTPException(status_code=403,detail="Permission denied")
    if await get_comic_by_title(comic.title, db):
        return HTTPException(status_code=409,detail="Comic already exists")
    return await create_comic(comic,db)

@app.post("/create/writer")
async def new_writer(writer: WriterMod, db: AsyncSession = Depends(get_db)):
    """Создание комикса"""
    #if await get_jwt_token_role() != "admin":
        #return HTTPException(status_code=403,detail="Permission denied")
    if await get_writer_by_name(writer.name, db):
        return HTTPException(status_code=409,detail="Writer already exists")
    return await create_writer(writer, db)

@app.post("/create/artist")
async def new_artist(artist: ArtistMod, db: AsyncSession = Depends(get_db)):
    """Создание комикса"""
    #if await get_jwt_token_role() != "admin":
        #return HTTPException(status_code=403,detail="Permission denied")
    if await get_artist_by_name(artist.name, db):
        return HTTPException(status_code=409,detail="Artist already exists")
    return await create_artist(artist, db)

@app.post("/create/pub")
async def new_pub(pub: PublisherMod, db: AsyncSession = Depends(get_db)):
    """Создание комикса"""
    #if await get_jwt_token_role() != "admin":
        #return HTTPException(status_code=403,detail="Permission denied")
    if await get_publisher_by_name(pub.name, db):
        return HTTPException(status_code=409,detail="Publisher already exists")
    return await create_publisher(pub, db)

@app.get("/view/comics")
async def view_comics(db: AsyncSession = Depends(get_db)):
    """JSON всех комиксов"""
    comics = await db.execute(select(Comic))
    return comics.scalars().all()

@app.get("/view/publishers")
async def view_pubs(db: AsyncSession = Depends(get_db)):
    """JSON всех издательств"""
    pubs = await db.execute(select(Publisher))
    return pubs.scalars().all()

@app.get("/view/writers")
async def view_writers(db: AsyncSession = Depends(get_db)):
    """JSON всех сценаристов"""
    writers = await db.execute(select(Writer))
    return writers.scalars().all()

@app.get("/view/artists")
async def view_artists(db: AsyncSession = Depends(get_db)):
    """JSON всех художников"""
    artists = await db.execute(select(Artist))
    return artists.scalars().all()

@app.delete("/delete/comic")
async def delete_comic_by_title(title = Body(), db: AsyncSession = Depends(get_db)):
    """Удаление комикса"""
    #if await get_jwt_token_role() != "admin":
        #return HTTPException(status_code=403,detail="Permission denied")
    comic = await get_comic_by_title(title=title["title"], db = db)
    if not comic:
        return HTTPException(status_code=404,detail="Title not found")
    db.delete(comic)
    await db.commit()
    return {"msg":"Successfully deleted comic"}

@app.delete("/delete/publisher")
async def delete_pub_by_name(name = Body(), db: AsyncSession = Depends(get_db)):
    """Удаление издателя"""
    #if await get_jwt_token_role() != "admin":
        #return HTTPException(status_code=403,detail="Permission denied")
    pub = await get_publisher_by_name(name=name["name"], db = db)
    if not pub:
        return HTTPException(status_code=404,detail="Name not found")
    db.delete(pub)
    await db.commit()
    return {"msg":"Successfully deleted publisher"}

@app.delete("/delete/writer")
async def delete_writer_by_name(name = Body(), db: AsyncSession = Depends(get_db)):
    """Удаление сценариста"""
    #if await get_jwt_token_role() != "admin":
        #return HTTPException(status_code=403,detail="Permission denied")
    writer = await get_writer_by_name(name=name["name"], db = db)
    if not writer:
        return HTTPException(status_code=404,detail="Name not found")
    db.delete(writer)
    await db.commit()
    return {"msg":"Successfully deleted writer"}

@app.delete("/delete/artist")
async def delete_artist_by_name(name = Body(), db: AsyncSession = Depends(get_db)):
    """Удаление художника"""
    #if await get_jwt_token_role() != "admin":
        #return HTTPException(status_code=403,detail="Permission denied")
    artist = await get_artist_by_name(name=name["name"], db = db)
    if not artist:
        return HTTPException(status_code=404,detail="Name not found")
    db.delete(artist)
    await db.commit()
    return {"msg":"Successfully deleted artist"}

@app.patch("/patch/comicamount")
async def update_comic_amount(data = Body(), db: AsyncSession = Depends(get_db)):
    """Удаление комикса"""
    #if await get_jwt_token_role() != "admin":
        #return HTTPException(status_code=403,detail="Permission denied")
    title = data["title"]
    amount = data["amount"]
    comic = await get_comic_by_title(title=title, db = db)
    if not comic:
        return HTTPException(status_code=404,detail="Title not found")
    comic.amount = amount
    await db.commit()
    return {"msg":"Successfully changed amount"}

@app.post("/buy")
async def buy_comic(data: str = Body(), db: AsyncSession = Depends(get_db)):
    """Покупка комикса"""
    await producer()
    """comics = list(data)
    comics_for_buy = []
    for comic in comics:
        comic_buy = await get_comic_by_title(comic.title, db)
        if not await comic_buy:
            return HTTPException(status_code=404,detail="Comic not found")
        comics_for_buy.append(comic_buy)
    return await create_comic(comic,db)"""
