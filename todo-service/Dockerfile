FROM python:3.13-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY main.py .

# Создаём директорию для данных
RUN mkdir -p /app/data

# Объявляем том для хранения базы данных
VOLUME /app/data

# Порт на котором работает приложение
EXPOSE 80

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]