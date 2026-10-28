# 01. Ma'lumotlar Bazasi Modeli (Entity-Relationship Diagram — ERD)

## 1. Kirish va Maqsad

Ushbu hujjat PostgreSQL maʼlumotlar bazasining relyatsion modelini, jadvallar oʻrtasidagi munosabatlarni, birlamchi va tashqi kalitlarni (Primary / Foreign Keys) hamda kardinallik (1:1, 1:N, N:M) qoidalarini belgilaydi.

Sxema maʼlumotlar minimallashtirish, kaskadli tozalash (ON DELETE CASCADE) va tezkor qidiruv indekslarini hisobga olgan holda loyihalashtirilgan.

---

## 2. Toʻliq ERD Diagrammasi (Mermaid)

```mermaid
erDiagram
    USERS ||--o{ TELEGRAM_ACCOUNTS : "ega bo'ladi (1:N)"
    USERS ||--o{ NOTIFICATIONS : "qabul qiladi (1:N)"
    USERS ||--o{ AUDIT_LOGS : "amal bajaradi (1:N)"

    TELEGRAM_ACCOUNTS ||--o{ TELEGRAM_CHATS : "kuzatadi (1:N)"
    TELEGRAM_CHATS ||--o{ TELEGRAM_MESSAGES : "o'z ichiga oladi (1:N)"

    TELEGRAM_MESSAGES ||--o{ SCANNED_URLS : "havolani o'z ichiga oladi (N:M orqali yoki bog'langan)"
    
    SCANNED_URLS ||--o| THREAT_INTELLIGENCE : "texnik tahlilga ega (1:1)"
    SCANNED_URLS ||--o| THREAT_ASSESSMENTS : "yakuniy bahoga ega (1:1)"
    SCANNED_URLS ||--o{ NOTIFICATIONS : "ogohlantirish yaratadi (1:N)"

    USERS {
        uuid id PK
        string email UK
        string hashed_password
        string role "USER | ANALYST | ADMIN"
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    TELEGRAM_ACCOUNTS {
        uuid id PK
        uuid user_id FK
        bigint telegram_user_id UK
        string phone_number_hash
        bytea encrypted_session "AES-256-GCM"
        string status "CONNECTED | DISCONNECTED | REVOKED | ERROR"
        string auth_state "AUTHORIZED | NEED_CODE | NEED_PASSWORD"
        timestamp last_connected_at
        timestamp created_at
    }

    TELEGRAM_CHATS {
        uuid id PK
        uuid account_id FK
        bigint telegram_chat_id
        string title
        string type "CHANNEL | SUPERGROUP | GROUP | PRIVATE"
        boolean is_monitored
        timestamp created_at
    }

    TELEGRAM_MESSAGES {
        uuid id PK
        uuid chat_id FK
        bigint telegram_message_id
        bigint sender_id
        string sender_username
        boolean has_urls
        integer url_count
        timestamp message_date
        timestamp created_at
    }

    SCANNED_URLS {
        uuid id PK
        string url_hash UK "SHA-256(canonical_url)"
        text raw_url
        text canonical_url
        string domain
        string status "PENDING | ENRICHED | EVALUATED | FAILED | BLOCKED"
        timestamp last_scanned_at
        timestamp created_at
    }

    THREAT_INTELLIGENCE {
        uuid id PK
        uuid url_id FK,UK
        integer domain_age_days
        string registrar
        jsonb dns_records
        string ssl_issuer
        boolean ssl_valid
        integer http_status
        integer response_time_ms
        boolean has_login_form
        boolean has_password_input
        jsonb redirect_chain
        text text_excerpt "Max 50KB"
        timestamp created_at
    }

    THREAT_ASSESSMENTS {
        uuid id PK
        uuid url_id FK,UK
        string verdict "PHISHING | SCAM | SUSPICIOUS | BENIGN | UNKNOWN"
        integer risk_score "0-100"
        float confidence "0.0-1.0"
        string impersonated_brand
        jsonb reasons
        jsonb gemini_response
        string evaluated_by "GEMINI_1_5_FLASH | HEURISTIC_FALLBACK"
        timestamp created_at
    }

    NOTIFICATIONS {
        uuid id PK
        uuid user_id FK
        uuid url_id FK
        bigint telegram_chat_id
        string alert_type "CRITICAL_PHISHING | SCAM_WARNING"
        string delivery_status "PENDING | SENT | FAILED | THROTTLED"
        integer attempts
        timestamp sent_at
        timestamp created_at
    }

    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK "nullable"
        string action "ACCOUNT_CONNECT | LOGIN | CONFIG_CHANGE"
        string ip_address
        string user_agent
        jsonb details
        timestamp created_at
    }
```

---

## 3. Aloqalar va Bogʻliqlik Qoidalari (Constraints & Foreign Keys)

1. **`users` -> `telegram_accounts`:**
   * Bir foydalanuvchi bir nechta Telegram hisoblarini ulashi mumkin (`1:N`).
   * Foydalanuvchi oʻchirilganda: `ON DELETE CASCADE` (Barcha unga tegishli hisoblar oʻchiriladi).
2. **`telegram_accounts` -> `telegram_chats`:**
   * Bitta hisob koʻplab guruh va kanallarni kuzatishi mumkin (`1:N`).
   * Hisob oʻchirilganda: `ON DELETE CASCADE`.
3. **`scanned_urls` -> `threat_intelligence` & `threat_assessments`:**
   * Bitta URL bitta texnik tahlil va bitta yakuniy bahoga ega boʻladi (`1:1`).
   * Bu havolalarni qayta-qayta tekshirish oʻrniga tezkor indekslangan `url_hash` orqali kesh natijasini darhol topish imkonini beradi.
4. **`scanned_urls` -> `notifications`:**
   * Agar bitta xavfli havola bir nechta guruhda tarqalsa, u boʻyicha turli foydalanuvchilarga alohida ogohlantirishlar yoziladi (`1:N`).

---

## 4. Qidiruv Indekslari (Indexes Strategy)

Yuqori unumdorlik va tezkor tahlil uchun quyidagi muhim indekslar yaratiladi:
* `scanned_urls(url_hash)` — **UNIQUE B-Tree Index**. Har bir kelgan havolani mikrosoniyalarda topish uchun.
* `scanned_urls(domain)` — Domen boʻyicha filtrlash.
* `threat_assessments(verdict, risk_score)` — Xavfli fishing tahlillarini hisobotlarda tezkor guruhlash uchun.
* `telegram_accounts(user_id, status)` — Foydalanuvchining faol akkauntlarini tez yuklash uchun.
* `notifications(user_id, delivery_status)` — Yetkazilmagan xabarlarni filtrlash uchun.
