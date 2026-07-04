FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

# Run migrations, then start the API. Simple and correct for a single-instance
# setup; if you ever scale api-server to >1 replica, move the migration step
# to its own one-shot job so it doesn't race across containers.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
