# 02. Ma'lumotlar Bazasi Lug'ati (Data Dictionary)

## 1. Kirish va Maqsad

Ushbu hujjat PostgreSQL maʼlumotlar bazasidagi har bir jadval, uning ustunlari (maydonlari), maʼlumot turlari, cheklovlari va xavfsizlik tasnifi boʻyicha toʻliq va batafsil maʼlumotnoma (Data Dictionary) hisoblanadi.

---

## 2. Jadvallar Boʻyicha Batafsil Tavsif

### 2.1 `users` — Foydalanuvchilar Jadvali
Tizimga kirish huquqiga ega foydalanuvchilar hisoblari.

| Ustun Nomi | Ma'lumot Turi | Nullable | Standart Qiymat | Tasnifi | Tavsifi |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `id` | `UUID` | ❌ | `gen_random_uuid()` | Ochiq | Birlamchi kalit (PK) |
| `email` | `VARCHAR(255)` | ❌ | — | Maxfiy | Foydalanuvchi elektron pochtasi (Unique) |
| `hashed_password`| `VARCHAR(255)` | ❌ | — | Oʻta Sezgir | Argon2id bilan heshlangan parol |
| `role` | `VARCHAR(32)` | ❌ | `'USER'` | Ichki | Rol: `'USER'`, `'ANALYST'`, `'ADMIN'` |
| `is_active` | `BOOLEAN` | ❌ | `TRUE` | Ichki | Akkaunt faolligi holati |
| `created_at` | `TIMESTAMPTZ` | ❌ | `NOW()` | Ichki | Roʻyxatdan oʻtgan vaqt |
| `updated_at` | `TIMESTAMPTZ` | ❌ | `NOW()` | Ichki | Soʻnggi oʻzgarish vaqti |

---

### 2.2 `telegram_accounts` — Ulangan Telegram Akkauntlari
Telethon orqali monitoring qilish uchun foydalanuvchilar tomonidan ulangan hisoblar.

| Ustun Nomi | Ma'lumot Turi | Nullable | Standart Qiymat | Tasnifi | Tavsifi |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `id` | `UUID` | ❌ | `gen_random_uuid()` | Ochiq | Birlamchi kalit (PK) |
| `user_id` | `UUID` | ❌ | — | Maxfiy | `users(id)` ga tashqi kalit (FK, Cascade) |
| `telegram_user_id`| `BIGINT` | ❌ | — | Maxfiy | Telegram'dagi unikal User ID |
| `phone_number_hash`| `VARCHAR(64)`| ❌ | — | Oʻta Sezgir | Qidiruv uchun telefon raqamining HMAC-SHA256 heshi |
| `encrypted_session`| `BYTEA` | ❌ | — | **Oʻta Sezgir**| **AES-256-GCM** bilan shifrlangan Telethon sessiyasi |
| `status` | `VARCHAR(32)` | ❌ | `'CONNECTED'` | Ichki | `'CONNECTED'`, `'DISCONNECTED'`, `'REVOKED'` |
| `auth_state` | `VARCHAR(32)` | ❌ | `'AUTHORIZED'` | Ichki | Login holati (`AUTHORIZED`, `NEED_CODE`, `NEED_2FA`) |
| `last_connected_at`| `TIMESTAMPTZ`| ❌ | `NOW()` | Ichki | Soʻnggi muvaffaqiyatli ulanish vaqti |
| `created_at` | `TIMESTAMPTZ` | ❌ | `NOW()` | Ichki | Ulangan vaqt |

---

### 2.3 `telegram_chats` — Kuzatilayotgan Guruh va Kanallar
Ulangan hisob aʼzo boʻlgan va monitoring qilinayotgan chatlar.

| Ustun Nomi | Ma'lumot Turi | Nullable | Standart Qiymat | Tasnifi | Tavsifi |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `id` | `UUID` | ❌ | `gen_random_uuid()` | Ochiq | Birlamchi kalit (PK) |
| `account_id` | `UUID` | ❌ | — | Maxfiy | `telegram_accounts(id)` ga FK |
| `telegram_chat_id`| `BIGINT` | ❌ | — | Maxfiy | Telegram'dagi Chat/Channel ID |
| `title` | `VARCHAR(255)` | ❌ | — | Maxfiy | Guruh yoki kanal nomi |
| `type` | `VARCHAR(32)` | ❌ | — | Ichki | `'CHANNEL'`, `'SUPERGROUP'`, `'GROUP'`, `'PRIVATE'` |
| `is_monitored` | `BOOLEAN` | ❌ | `TRUE` | Ichki | Monitoring yoqilgan/oʻchirilganligi |
| `created_at` | `TIMESTAMPTZ` | ❌ | `NOW()` | Ichki | Aniqlangan vaqt |

---

### 2.4 `scanned_urls` — Skanerlangan Havolalar
Telegram xabarlaridan ajratib olingan va tahlilga yuborilgan barcha unikal havolalar.

| Ustun Nomi | Ma'lumot Turi | Nullable | Standart Qiymat | Tasnifi | Tavsifi |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `id` | `UUID` | ❌ | `gen_random_uuid()` | Ochiq | Birlamchi kalit (PK) |
| `url_hash` | `CHAR(64)` | ❌ | — | Ichki | `SHA-256(canonical_url)` — tezkor kesh indeksi (UK) |
| `raw_url` | `TEXT` | ❌ | — | Maxfiy | Xabardan olingan asl havola |
| `canonical_url` | `TEXT` | ❌ | — | Maxfiy | Tozalangan, parametrlardan xoli kanonik havola |
| `domain` | `VARCHAR(255)` | ❌ | — | Ochiq | Havola domeni (masalan: `example.com`) |
| `status` | `VARCHAR(32)` | ❌ | `'PENDING'` | Ichki | `'PENDING'`, `'ENRICHED'`, `'EVALUATED'`, `'BLOCKED'` |
| `last_scanned_at` | `TIMESTAMPTZ` | ❌ | `NOW()` | Ichki | Oxirgi marta toʻliq skan qilingan vaqt |
| `created_at` | `TIMESTAMPTZ` | ❌ | `NOW()` | Ichki | Birinchi marta uchragan vaqt |

---

### 2.5 `threat_intelligence` — Domen va Saytning Texnik Dalillari
Skaner va tashqi manbalar (DNS, WHOIS, SSL, HTTP fetcher) orqali yigʻilgan xom dalillar.

| Ustun Nomi | Ma'lumot Turi | Nullable | Standart Qiymat | Tasnifi | Tavsifi |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `id` | `UUID` | ❌ | `gen_random_uuid()` | Ochiq | Birlamchi kalit (PK) |
| `url_id` | `UUID` | ❌ | — | Ochiq | `scanned_urls(id)` ga FK va Unique (1:1) |
| `domain_age_days` | `INTEGER` | ❌ | `0` | Ochiq | Domen roʻyxatdan oʻtganidan beri necha kun oʻtgani |
| `registrar` | `VARCHAR(255)` | ⭕ | `NULL` | Ochiq | Domen registratori |
| `dns_records` | `JSONB` | ❌ | `'{}'` | Ichki | A, AAAA, MX, NS, TXT yozuvlari roʻyxati |
| `ssl_issuer` | `VARCHAR(255)` | ⭕ | `NULL` | Ochiq | SSL sertifikatini bergan tashkilot |
| `ssl_valid` | `BOOLEAN` | ❌ | `FALSE` | Ochiq | Sertifikat haqiqiy va amaldami? |
| `http_status` | `INTEGER` | ⭕ | `NULL` | Ichki | HTTP status javob kodi (200, 404, 301) |
| `response_time_ms`| `INTEGER` | ⭕ | `NULL` | Ichki | Sayt javob qaytarish tezligi (ms) |
| `has_login_form` | `BOOLEAN` | ❌ | `FALSE` | Ichki | HTML sahifada kirish formasi bormi? |
| `has_password_input`| `BOOLEAN` | ❌ | `FALSE` | Ichki | `<input type="password">` mavjudmi? |
| `redirect_chain` | `JSONB` | ❌ | `'[]'` | Ichki | Yoʻnaltirishlar (Redirects) zanjiri |
| `text_excerpt` | `TEXT` | ⭕ | `NULL` | Maxfiy | Sahifaning dastlabki qisqartirilgan matni (max 50KB) |
| `created_at` | `TIMESTAMPTZ` | ❌ | `NOW()` | Ichki | Dalillar toʻplangan vaqt |

---

### 2.6 `threat_assessments` — Yakuniy Xavf Xulosasi va AI Bahosi
Google Gemini va ichki Risk Engine tomonidan chiqarilgan yakuniy qaror.

| Ustun Nomi | Ma'lumot Turi | Nullable | Standart Qiymat | Tasnifi | Tavsifi |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `id` | `UUID` | ❌ | `gen_random_uuid()` | Ochiq | Birlamchi kalit (PK) |
| `url_id` | `UUID` | ❌ | — | Ochiq | `scanned_urls(id)` ga FK va Unique (1:1) |
| `verdict` | `VARCHAR(32)` | ❌ | — | Maxfiy | `'PHISHING'`, `'SCAM'`, `'SUSPICIOUS'`, `'BENIGN'`, `'UNKNOWN'` |
| `risk_score` | `INTEGER` | ❌ | `0` | Maxfiy | Xavf bali (0 dan 100 gacha) |
| `confidence` | `FLOAT` | ❌ | `0.0` | Maxfiy | Tizimning oʻz xulosasiga ishonch darajasi (0.0 - 1.0) |
| `impersonated_brand`| `VARCHAR(128)`| ⭕ | `NULL` | Maxfiy | Oʻxshatilgan soxta brend (masalan: "Telegram", "Click") |
| `reasons` | `JSONB` | ❌ | `'[]'` | Maxfiy | Xavfni tasdiqlovchi dalillar roʻyxati |
| `gemini_response` | `JSONB` | ⭕ | `NULL` | Maxfiy | Gemini modelidan olingan xom strukturali javob |
| `evaluated_by` | `VARCHAR(64)` | ❌ | — | Ichki | Baholagan tizim: `'GEMINI_1_5_FLASH'` yoki `'HEURISTIC'` |
| `created_at` | `TIMESTAMPTZ` | ❌ | `NOW()` | Ichki | Baholangan vaqt |

---

### 2.7 `notifications` — Xabarnomalar Yetkazish Tarixi
Foydalanuvchilarga yuborilgan ogohlantirishlar jurnali.

| Ustun Nomi | Ma'lumot Turi | Nullable | Standart Qiymat | Tasnifi | Tavsifi |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `id` | `UUID` | ❌ | `gen_random_uuid()` | Ochiq | Birlamchi kalit (PK) |
| `user_id` | `UUID` | ❌ | — | Maxfiy | `users(id)` ga FK |
| `url_id` | `UUID` | ❌ | — | Maxfiy | `scanned_urls(id)` ga FK |
| `telegram_chat_id`| `BIGINT` | ❌ | — | Maxfiy | Xabarnoma yuborilgan Telegram chat |
| `alert_type` | `VARCHAR(64)` | ❌ | — | Ichki | `'CRITICAL_PHISHING'`, `'SCAM_WARNING'` |
| `delivery_status` | `VARCHAR(32)` | ❌ | `'PENDING'` | Ichki | `'PENDING'`, `'SENT'`, `'FAILED'`, `'THROTTLED'` |
| `attempts` | `INTEGER` | ❌ | `0` | Ichki | Yuborishga urinishlar soni |
| `sent_at` | `TIMESTAMPTZ` | ⭕ | `NULL` | Ichki | Muvaffaqiyatli yetkazilgan vaqt |
| `created_at` | `TIMESTAMPTZ` | ❌ | `NOW()` | Ichki | Yaratilgan vaqt |
