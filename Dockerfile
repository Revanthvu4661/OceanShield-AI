FROM python:3.11-slim

WORKDIR /app

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY models/ ./models/
COPY src/ ./src/

WORKDIR /app/backend
RUN pip install --no-cache-dir -r requirements.txt

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
