from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import sqlite3
import os

# Путь к базе данных
DB_PATH = "/app/data/todo.db" if os.path.exists("/app/data") else "todo.db"

# Модель данных для создания задачи
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

# Модель данных для обновления задачи
class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

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
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            completed BOOLEAN NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Выполняется при запуске
    init_db()
    print(f"Database initialized at {DB_PATH}")
    yield
    # Выполняется при остановке (опционально)

# Создаём приложение FastAPI
app = FastAPI(title="ToDo Service", version="1.0.0", lifespan=lifespan)

# Добавляем CORS для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# POST /items - Создать новую задачу
@app.post("/items", status_code=201)
def create_task(task: TaskCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, description, completed) VALUES (?, ?, ?)",
        (task.title, task.description, task.completed)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    
    return {
        "id": task_id,
        "title": task.title,
        "description": task.description,
        "completed": task.completed
    }

# GET /items - Получить все задачи
@app.get("/items")
def get_all_tasks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()
    conn.close()
    
    return [dict(task) for task in tasks]

# GET /items/{item_id} - Получить задачу по ID
@app.get("/items/{item_id}")
def get_task(item_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (item_id,))
    task = cursor.fetchone()
    conn.close()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return dict(task)

# PUT /items/{item_id} - Обновить задачу
@app.put("/items/{item_id}")
def update_task(item_id: int, task: TaskUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (item_id,))
    existing_task = cursor.fetchone()
    
    if not existing_task:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_fields = []
    update_values = []
    
    if task.title is not None:
        update_fields.append("title = ?")
        update_values.append(task.title)
    
    if task.description is not None:
        update_fields.append("description = ?")
        update_values.append(task.description)
    
    if task.completed is not None:
        update_fields.append("completed = ?")
        update_values.append(task.completed)
    
    if update_fields:
        update_values.append(item_id)
        query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, update_values)
        conn.commit()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (item_id,))
    updated_task = cursor.fetchone()
    conn.close()
    
    return dict(updated_task)

# DELETE /items/{item_id} - Удалить задачу
@app.delete("/items/{item_id}")
def delete_task(item_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (item_id,))
    task = cursor.fetchone()
    
    if not task:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    
    cursor.execute("DELETE FROM tasks WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Task deleted successfully"}

# Корневой эндпоинт
@app.get("/")
def root():
    return {"message": "ToDo Service is running!"}