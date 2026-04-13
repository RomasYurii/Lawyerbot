# Використовуємо легку офіційну версію Python
FROM python:3.11-slim

# Встановлюємо робочу директорію в контейнері
WORKDIR /app

# Спочатку копіюємо requirements, щоб Docker закешував встановлені бібліотеки
COPY requirements.txt .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь інший код
COPY . .

# Відкриваємо порт для вебхуків WayForPay
EXPOSE 8080

# Запускаємо нашого бота
CMD ["python", "run.py"]