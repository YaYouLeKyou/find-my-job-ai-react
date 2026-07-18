# Backend FastAPI - FindMyJobAI
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module (imported by api.py via sys.path)
COPY shared/ ./shared/

# Copy api.py into /app/backend/ to match railway.toml startCommand
COPY backend/api.py ./backend/api.py

# Expose port
EXPOSE 8000

# Run from /app/backend/ (api.py is there, shared/ is at /app/shared/)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
