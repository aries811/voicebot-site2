FROM python:3.10-slim

RUN apt-get update && apt-get install -y \ 
    libstdc++6 libasound2     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN chmod +x RHVoice-client

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "app.py"]