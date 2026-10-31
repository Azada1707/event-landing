# Production image for the event registration landing.
# Uses a persistent volume for the SQLite DB so registrations survive redeploys.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    EVENT_DB_PATH=/data/registrations.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data

# Default overrides for production; set real secrets via the host (see .env.example).
ENV SECRET_KEY="change-me-in-prod" \
    ADMIN_USER="admin" \
    ADMIN_PASSWORD="change-me-in-prod"

EXPOSE 8000

# gunicorn serves the Flask app; SQLite DB lives on the /data volume.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 60 app:app"]