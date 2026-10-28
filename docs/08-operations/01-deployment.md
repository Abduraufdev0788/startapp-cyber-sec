# 01. Ishga Tushirish va Konteynerlashtirish (Deployment Guide)

## 1. Kirish va Maqsad

Loyiha ishlab chiqarish (Production) muhitida toʻliq konteynerlashtirilgan holda **Docker** va **Docker Compose** (yoki Kubernetes) orqali boshqariladi.

Ushbu hujjat Dockerfile tuzilishi, non-root xavfsizlik talablari, Compose xizmatlari va jonli serverda ishga tushirish jarayonini belgilaydi.

---

## 2. Koʻp Bosqichli Dockerfile (Multi-Stage Dockerfile)

Xavfsizlik va hajm tejamkorligi uchun **Multi-Stage Build** va **Non-root foydalanuvchi** ishlatiladi:

```dockerfile
# 1-bosqich: Bog'liqliklarni yig'ish (Builder)
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 2-bosqich: Yakuniy Xavfsiz Ishchi Obraz (Runner)
FROM python:3.11-slim AS runner

WORKDIR /app

# Kiberxavfsizlik: Root bo'lmagan foydalanuvchi yaratish
RUN useradd -u 10001 -m -s /bin/bash appuser && \
    apt-get update && apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

USER appuser
ENV PATH="/home/appuser/.local/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 3. Docker Compose Xizmatlari Arxitekturasi

Tizim quyidagi asosiy xizmatlardan iborat:
1. `postgres`: PostgreSQL 16 maʼlumotlar bazasi.
2. `redis`: Kesh va Celery vazifalar navbati.
3. `migration`: Baza ishga tushishi bilan `alembic upgrade head` ni bajaruvchi bir martalik servis.
4. `api`: FastAPI REST API serveri.
5. `telethon-monitor`: Telegram hisoblarini doimiy tinglovchi fon xizmati.
6. `bot`: Foydalanuvchilar bilan muloqot qiluvchi rasmiy Telegram Bot.
7. `celery-worker`: URL skanerlash, maʼlumot boyitish va AI tahlil ishchilari.
8. `celery-beat`: Davriy tozalash va tekshiruv vazifalari.

---

## 4. Ishga Tushirish Ketma-ketligi

Serverda loyihani ishga tushirish:
```bash
# 1. Repozitoriyani klonlash
git clone https://github.com/.../phishing-detector-backend.git
cd phishing-detector-backend

# 2. Maxfiy o'zgaruvchilarni sozlash
cp .env.example .env
nano .env  # Parollar va API kalitlarni kiritish

# 3. Konteynerlarni yig'ish va ishga tushirish
docker compose build
docker compose up -d

# 4. Holat va loglarni tekshirish
docker compose ps
docker compose logs -f api
```
