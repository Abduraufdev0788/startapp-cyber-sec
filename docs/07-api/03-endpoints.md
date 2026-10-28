# 03. API Endpointlari Spetsifikatsiyasi (API Endpoints Specification)

## 1. Kirish va Maqsad

Ushbu hujjat tizimdagi barcha asosiy REST API endpointlari, ularning HTTP metodlari, qabul qiluvchi parametrlar (Request Body/Query) va qaytaruvchi javoblari (Response DTO) spetsifikatsiyasini belgilaydi.

---

## 2. Endpointlar Guruhi

### 2.1 Autentifikatsiya (`/api/v1/auth`)

| Metod | Marshrut | Ruxsat | Tavsif |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/auth/register` | Ommaviy | Yangi foydalanuvchini roʻyxatdan oʻtkazish |
| `POST` | `/api/v1/auth/login` | Ommaviy | Tizimga kirish (Email va parol orqali token olish) |
| `POST` | `/api/v1/auth/refresh` | Ommaviy | Refresh token orqali yangi access token olish |
| `POST` | `/api/v1/auth/logout` | USER | Akkauntdan chiqish (Tokenni qora roʻyxatga kiritish) |

---

### 2.2 Telegram Hisoblarini Boshqarish (`/api/v1/telegram`)

| Metod | Marshrut | Ruxsat | Tavsif |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/telegram/auth/send-code` | USER | Telefon raqamiga tasdiqlash kodi yuborish |
| `POST` | `/api/v1/telegram/auth/verify-code` | USER | Telegram kodini kiritish |
| `POST` | `/api/v1/telegram/auth/verify-2fa` | USER | 2FA parolini kiritish (agar mavjud boʻlsa) |
| `GET` | `/api/v1/telegram/accounts` | USER | Ulangan Telegram hisoblari roʻyxatini olish |
| `DELETE`| `/api/v1/telegram/accounts/{id}` | USER | Hisobni uzish va sessiyani toʻliq oʻchirish |
| `GET` | `/api/v1/telegram/accounts/{id}/chats`| USER | Ushbu hisob aʼzo boʻlgan guruhlar roʻyxati |

---

### 2.3 Havolalarni Skanerlash va Tahlil (`/api/v1/scans`)

| Metod | Marshrut | Ruxsat | Tavsif |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/scans` | USER | Yangi havolani qoʻlda tekshirishga yuborish |
| `GET` | `/api/v1/scans/{scan_id}` | USER | Aniq bir havola skan natijasi va AI xulosasini olish |
| `GET` | `/api/v1/scans` | USER | Foydalanuvchining skan tarixi (Filtr va Paginatsiya bilan) |
| `POST` | `/api/v1/scans/{scan_id}/rescan`| USER | Havolani majburiy qayta skan qilish |

#### Namunaviy Soʻrov: `POST /api/v1/scans`
```json
{
  "url": "https://t.me/free_crypto_airdrop_bot?start=12345"
}
```

#### Namunaviy Javob: `200 OK`
```json
{
  "success": true,
  "data": {
    "scan_id": "c3a9f078-43d9-4876-96b4-cb30eb5a6d5c",
    "status": "EVALUATED",
    "canonical_url": "https://t.me/free_crypto_airdrop_bot",
    "domain": "t.me",
    "verdict": "SCAM",
    "risk_score": 85,
    "confidence": 0.92,
    "impersonated_brand": "Telegram / Hamster Kombat",
    "reasons": [
      "Soxta moliyaviy va'dalar (bepul kriptovalyuta tarqatish) aniqlandi.",
      "Foydalanuvchilardan shaxsiy hamyon kalitlarini kiritish talab qilinmoqda."
    ],
    "scanned_at": "2026-10-22T18:05:00Z"
  }
}
```

---

### 2.4 Tizim Salomatligi va Monitoring (`/api/v1/health`)

| Metod | Marshrut | Ruxsat | Tavsif |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/v1/health/liveness` | Ommaviy | API jarayoni tirikligini tekshirish (K8s Liveness) |
| `GET` | `/api/v1/health/readiness` | Ommaviy | Baza, Redis va Celery tayyorligini tekshirish (K8s Readiness) |
