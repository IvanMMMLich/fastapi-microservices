from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional
from contextlib import asynccontextmanager
import sqlite3
import os
import string
import random
import qrcode
from io import BytesIO

# Путь к базе данных
DB_PATH = "/app/data/shorturl.db" if os.path.exists("/app/data") else "shorturl.db"

# Модель для создания короткой ссылки
class URLCreate(BaseModel):
    url: HttpUrl

# Модель для генерации QR-кода
class QRCodeRequest(BaseModel):
    url: str
    color: str = "#000000"

# Функция для подключения к базе данных
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Функция для инициализации базы данных
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_id TEXT UNIQUE NOT NULL,
            full_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            clicks INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# Генерация случайного short_id
def generate_short_id(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"Database initialized at {DB_PATH}")
    
    # Выводим статистику при запуске
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM urls")
    count = cursor.fetchone()["count"]
    cursor.execute("SELECT SUM(clicks) as total_clicks FROM urls")
    total_clicks = cursor.fetchone()["total_clicks"] or 0
    conn.close()
    
    print(f"📊 Всего ссылок в базе: {count}")
    print(f"👆 Всего переходов: {total_clicks}")
    print("=" * 50)
    
    yield

# Создаём приложение FastAPI
app = FastAPI(title="URL Shortener Service", version="1.0.0", lifespan=lifespan)

# Добавляем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# POST /shorten - Создать короткую ссылку
@app.post("/shorten")
def shorten_url(url_data: URLCreate):
    conn = get_db()
    cursor = conn.cursor()
    
    # Проверяем существует ли уже такой URL
    cursor.execute("SELECT short_id FROM urls WHERE full_url = ?", (str(url_data.url),))
    existing = cursor.fetchone()
    
    if existing:
        conn.close()
        print(f"♻️ URL уже существует: {existing['short_id']}")
        return {
            "short_id": existing["short_id"],
            "short_url": f"http://localhost:8001/{existing['short_id']}",
            "full_url": str(url_data.url),
            "message": "URL already exists"
        }
    
    # Генерируем уникальный short_id
    while True:
        short_id = generate_short_id()
        cursor.execute("SELECT id FROM urls WHERE short_id = ?", (short_id,))
        if not cursor.fetchone():
            break
    
    # Сохраняем в базу
    cursor.execute(
        "INSERT INTO urls (short_id, full_url) VALUES (?, ?)",
        (short_id, str(url_data.url))
    )
    conn.commit()
    
    # Получаем новый счётчик ссылок
    cursor.execute("SELECT COUNT(*) as count FROM urls")
    count = cursor.fetchone()["count"]
    conn.close()
    
    print(f"✅ Создана новая ссылка: {short_id} | Всего ссылок: {count}")
    
    return {
        "short_id": short_id,
        "short_url": f"http://localhost:8001/{short_id}",
        "full_url": str(url_data.url)
    }

# GET /all - Получить все ссылки
@app.get("/all")
def get_all_urls():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urls ORDER BY created_at DESC")
    urls = cursor.fetchall()
    conn.close()
    
    return [dict(url) for url in urls]

# GET /stats/{short_id} - Получить статистику
@app.get("/stats/{short_id}")
def get_stats(short_id: str):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM urls WHERE short_id = ?", (short_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    return {
        "short_id": result["short_id"],
        "full_url": result["full_url"],
        "created_at": result["created_at"],
        "clicks": result["clicks"]
    }

# POST /qrcode - Генерация QR-кода
@app.post("/qrcode")
def generate_qr_code(qr_data: QRCodeRequest):
    try:
        # Создаём QR-код
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data.url)
        qr.make(fit=True)
        
        # Создаём изображение с выбранным цветом
        img = qr.make_image(fill_color=qr_data.color, back_color="white")
        
        # Сохраняем в BytesIO
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        print(f"🎨 Сгенерирован QR-код цвета: {qr_data.color}")
        
        return StreamingResponse(buf, media_type="image/png")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# DELETE /delete/{short_id} - Удалить ссылку
@app.delete("/delete/{short_id}")
def delete_url(short_id: str):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM urls WHERE short_id = ?", (short_id,))
    url = cursor.fetchone()
    
    if not url:
        conn.close()
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    cursor.execute("DELETE FROM urls WHERE short_id = ?", (short_id,))
    conn.commit()
    
    # Получаем новый счётчик ссылок
    cursor.execute("SELECT COUNT(*) as count FROM urls")
    count = cursor.fetchone()["count"]
    conn.close()
    
    print(f"🗑️ Удалена ссылка: {short_id} | Осталось ссылок: {count}")
    
    return {"message": "URL deleted successfully"}

# GET /{short_id} - Редирект на полный URL
@app.get("/{short_id}")
def redirect_to_url(short_id: str):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT full_url FROM urls WHERE short_id = ?", (short_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    # Увеличиваем счётчик кликов
    cursor.execute("UPDATE urls SET clicks = clicks + 1 WHERE short_id = ?", (short_id,))
    conn.commit()
    
    # Получаем обновлённое количество кликов
    cursor.execute("SELECT clicks FROM urls WHERE short_id = ?", (short_id,))
    clicks = cursor.fetchone()["clicks"]
    conn.close()
    
    print(f"🔗 Переход по ссылке: {short_id} | Всего переходов: {clicks}")
    
    return RedirectResponse(url=result["full_url"])

# Корневой эндпоинт
@app.get("/")
def root():
    return {"message": "URL Shortener Service is running!"}