FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libstdc++6 \
    libgcc1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY shared ./shared

WORKDIR /app

EXPOSE 8080
CMD ["bash", "-lc", "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT"]
