# 01. Mahalliy Muhitni Oʻrnatish (Local Development Setup)

## 1. Kirish va Maqsad

Ushbu hujjat loyiha ustida ishlaydigan dasturchilar uchun mahalliy kompyuterda (Linux / macOS / WSL2) toʻliq ishlab chiqish muhitini tez va xatolarsiz sozlash boʻyicha bosqichma-bosqich qoʻllanmadir.

---

## 2. Talab Qilinadigan Dasturiy Ta'minot (Prerequisites)

* **Python:** `3.11` yoki undan yuqori versiya.
* **Docker va Docker Compose:** PostgreSQL va Redis xizmatlarini konteynerda ishga tushirish uchun.
* **Git:** Kod bazasini boshqarish uchun.

---

## 3. Bosqichma-bosqich Oʻrnatish Koʻrsatmasi

### 1-qadam: Repozitoriyani Klonlash va Virtual Muhit Yaratish
```bash
git clone https://github.com/.../phishing-detector-backend.git
cd phishing-detector-backend

# Virtual muhitni yaratish va faollashtirish
python3.11 -m venv .venv
source .venv/bin/activate
```

### 2-qadam: Bogʻliqliklarni Oʻrnatish
```bash
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```

### 3-qadam: Konfiguratsiya Faylini Sozlash
```bash
cp .env.example .env
```
`.env` faylini ochib, quyidagi parametrlarni kiritasiz:
* `APP_MASTER_KEY`: 32-baytlik tasodifiy heks satr (Generatsiya: `openssl rand -hex 32`).
* `TELEGRAM_API_ID` va `TELEGRAM_API_HASH`: [my.telegram.org](https://my.telegram.org) saytidan olingan kalitlar.
* `GEMINI_API_KEY`: Google AI Studio orqali olingan bepul API kalit.

### 4-qadam: Baza va Redis Konteynerlarini Ishga Tushirish
Barcha xizmatlarni mahalliy kompyuterga oʻrnatib oʻtirmaslik uchun faqat baza va Redis konteynerda ishga tushiriladi:
```bash
docker compose up -d postgres redis
```

### 5-qadam: Ma'lumotlar Bazasi Migratsiyalarini Qoʻllash
```bash
alembic upgrade head
```

---

## 4. Xizmatlarni Mahalliy Ishga Tushirish

Loyihani sinab koʻrish uchun alohida terminallarda quyidagi jarayonlar ishga tushiriladi:

1. **FastAPI REST Server (Hot-reload bilan):**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   API hujjati brauzerda ochiladi: `http://localhost:8000/docs`.

2. **Celery Fon Ishchilari:**
   ```bash
   celery -A app.workers.celery_app worker -l info
   ```

3. **Telegram Bot Xizmati:**
   ```bash
   python -m app.integrations.telegram_bot.bot
   ```

4. **Telethon Monitor Jarayoni:**
   ```bash
   python -m app.integrations.telethon.monitor
   ```
