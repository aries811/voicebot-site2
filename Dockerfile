FROM python:3.10-slim

# Оновлення пакунків та встановлення потрібних бібліотек (libstdc++6 і libasound2)
RUN apt-get update && apt-get install -y \
    libstdc++6 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копіюємо всі файли проекту в контейнер
COPY . .

# Робимо RHVoice-client виконуваним
RUN chmod +x RHVoice-client

# Встановлюємо Python-залежності без кешу
RUN pip install --no-cache-dir -r requirements.txt

# Визначаємо команду запуску додатку
CMD ["python", "app.py"]
