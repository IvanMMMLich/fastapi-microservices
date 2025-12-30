# FastAPI Microservices

Два микросервиса на FastAPI с Docker контейнеризацией:
- **ToDo Service** - управление списком задач (CRUD)
- **URL Shortener** - сокращение ссылок с QR-кодами в цвете

## 🚀 Запуск через Docker

### Создание томов
```bash
docker volume create todo_data
docker volume create shorturl_data
```

### Запуск контейнеров
```bash
# ToDo Service (порт 8000)
docker run -d -p 8000:80 -v todo_data:/app/data --name todo-container ivansycev/todo-service:latest

# URL Shortener (порт 8001)
docker run -d -p 8001:80 -v shorturl_data:/app/data --name shorturl-container ivansycev/shorturl-service:latest
```

### Доступ к API
- ToDo Service: http://localhost:8000/docs
- URL Shortener: http://localhost:8001/docs

## 📦 Docker Hub
- ToDo Service: https://hub.docker.com/r/ivansycev/todo-service
- URL Shortener: https://hub.docker.com/r/ivansycev/shorturl-service

## 🛠️ Локальная разработка

### Установка зависимостей
```bash
python -m venv venv
source venv/bin/activate
pip install -r todo-service/requirements.txt
pip install -r shorturl-service/requirements.txt
```

### Запуск локально
```bash
# ToDo Service
cd todo-service
uvicorn main:app --reload --port 8000

# URL Shortener
cd shorturl-service
uvicorn main:app --reload --port 8001
```

## 📝 Особенности

**ToDo Service:**
- CRUD операции для задач
- Веб-интерфейс (index.html)
- SQLite база данных

**URL Shortener:**
- Создание коротких ссылок
- QR-коды с выбором цвета (градиентный пикер)
- Статистика переходов
- Веб-интерфейс (index.html)
- SQLite база данных

## 🏗️ Структура проекта
```
fastapi-microservices/
├── todo-service/
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── index.html
├── shorturl-service/
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── index.html
└── README.md
```