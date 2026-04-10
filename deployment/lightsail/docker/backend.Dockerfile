FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY backend/ ./backend/

RUN pip install --no-cache-dir .

RUN mkdir -p /app/data /app/uploaded_datasets

EXPOSE 8080

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
