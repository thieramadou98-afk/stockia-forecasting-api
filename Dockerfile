# StockIA.web — image unique : API FastAPI + interface statique /ui/
# Build (racine du dépôt) : docker build -t stockia-web .
# Azure App Service : définir WEBSITES_PORT=8000 + STOCKIA_SECRET_KEY sur la Web App.
FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="StockIA.web"
LABEL org.opencontainers.image.description="8INF206 — API inventaire + UI /ui/"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/backend

RUN pip install --no-cache-dir --upgrade pip

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY frontend /app/frontend

EXPOSE 8000

# Port : 8000 par défaut ; Render/Fly passent souvent la variable PORT
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
