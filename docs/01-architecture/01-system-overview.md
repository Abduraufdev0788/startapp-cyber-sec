# 01. Tizim Arxitekturasi va Umumiy Koʻrinish (System Overview)

## 1. Kirish va Maqsad

Telegram Fishing va Firibgarlikni Aniqlash Platformasi — foydalanuvchilarning Telegram hisoblari orqali xabarlarni xavfsiz kuzatuvchi, xabarlar tarkibidagi havolalarni (URL) tahlil qiluvchi va sun'iy intellekt (Google Gemini) yordamida fishing/firibgarlik tahdidlarini real vaqt rejimida aniqlovchi xavfsizlik backend tizimidir.

Tizim arxitekturasi **Modular Monolith** (Modulli Monolit) tamoyiliga asoslangan boʻlib, mikroxizmatlarning murakkabligisiz yuqori darajada ajratilgan domen modullari, mustaqil fon ishchilari (workers) va qatʼiy xavfsizlik chegaralarini taʼminlaydi.

---

## 2. Umumiy Arxitektura Diagrammasi

Quyidagi diagrammada tizimning asosiy komponentlari va ular orasidagi oʻzaro aloqalar tasvirlangan:

```mermaid
flowchart TB
    subgraph Telegram_Ecosystem["Telegram Ekotizimi"]
        TG_User["Foydalanuvchi / Guruhlar / Kanallar"]
        TG_Servers["Telegram API / MTProto Serverlari"]
        TG_Bot_User["Bot Foydalanuvchisi / Admin"]
    end

    subgraph Platform_Core["Himoyalangan Platforma (Modular Monolith)"]
        subgraph Ingestion_Layer["Qabul Qilish Qatlami"]
            Telethon_Worker["Telethon Account Monitor\n(Userbot Client Manager)"]
            FastAPI_Server["FastAPI REST API\n(Autentifikatsiya va Boshqaruv)"]
            TGBot_Service["Telegram Bot Xizmati\n(python-telegram-bot)"]
        end

        subgraph Messaging_and_Cache["Navbat va Kesh"]
            Redis_Queue["Redis Broker & Cache\n(Skanerlash navbati, Natijalar keshi)"]
        end

        subgraph Processing_Layer["Qayta Ishlash Qatlami (Celery)"]
            Worker_Scan["Celery Scan Worker\n(URL Normalizatsiya, SSRF Himoya)"]
            Worker_Enrich["Celery Enrichment Worker\n(DNS, WHOIS, TLS, HTTP Fetch)"]
            Worker_AI["Celery AI Worker\n(Gemini Structured Output)"]
            Worker_Notify["Celery Notification Worker\n(Xabarnomalarni yetkazish)"]
        end

        subgraph Data_Storage["Ma'lumotlar Saqlash"]
            PostgreSQL[("PostgreSQL Ma'lumotlar Bazasi\n(Shifrlangan sessiyalar, skan tarixi)")]
            Vault_KeyStore["Key Store / KMS\n(AES-256 Master Key)"]
        end
    end

    subgraph External_Services["Tashqi Xizmatlar (Tashqi Tarmoq)"]
        Target_Website["Tekshirilayotgan Veb-sayt\n(Cheklangan HTTP Fetch)"]
        Threat_Feeds["Tahdid Razvedkasi Bazalari\n(Reputation & Blocklists)"]
        Gemini_API["Google Gemini 1.5 / 2.0 API\n(Xavfni tahlil qilish)"]
    end

    %% Aloqalar
    TG_User --> TG_Servers
    TG_Servers <-->|MTProto (Sessiya)| Telethon_Worker
    TG_Bot_User <-->|Bot API| TGBot_Service

    Telethon_Worker -->|Xabar va URL larni yuborish| Redis_Queue
    FastAPI_Server <-->|Ma'lumotlar almashinuvi| PostgreSQL
    FastAPI_Server -->|Task boshlash| Redis_Queue

    Redis_Queue --> Worker_Scan
    Worker_Scan --> Worker_Enrich
    Worker_Enrich -->|Xavfsiz HTTP so'rov| Target_Website
    Worker_Enrich -->|DNS/WHOIS/Obro'| Threat_Feeds
    Worker_Enrich --> Worker_AI
    Worker_AI -->|Strukturali tahlil| Gemini_API
    Worker_AI -->|Natijani saqlash| PostgreSQL
    Worker_AI --> Worker_Notify
    Worker_Notify -->|Alert yuborish| TGBot_Service

    Vault_KeyStore -.->|Shifrlash kaliti| Telethon_Worker
    Vault_KeyStore -.->|Shifrlash kaliti| FastAPI_Server
```

---

## 3. Asosiy Komponentlar va Ularning Mas'uliyatlari

### 3.1 FastAPI REST API Gateway
* **Vazifasi:** Tizimning asosiy tashqi interfeysi. Web boshqaruv paneli, mobil ilovalar va ma'muriy vositalar uchun HTTP/JSON API taqdim etadi.
* **Xususiyatlari:**
  * Asinxron (asyncio) arxitektura.
  * JWT orqali foydalanuvchilarni autentifikatsiya qilish.
  * Telegram hisobini ulash (login flow, OTP kiritish, 2FA qoʻllab-quvvatlash) orkestratsiyasi.
  * Skan natijalari va statistikani taqdim etish.
  * Tizim salomatligi (Health check) va tayyorlik (Readiness probe) tekshiruvlari.

### 3.2 Telethon Account Monitor (Userbot Manager)
* **Vazifasi:** Foydalanuvchi tomonidan ulangan Telegram akkauntlar nomidan kiruvchi xabarlarni qabul qilish.
* **Xususiyatlari:**
  * Telegram MTProto protokoli orqali ishlaydi.
  * Har bir ulangan akkaunt alohida, mustaqil va izolyatsiyalangan sessiya holatiga ega.
  * Xabarlarning tarixini (arxivini) toʻliq yuklab olmaydi; faqat yangi kelgan xabarlar oqimini (Events.NewMessage) tinglaydi.
  * Matn va Telegram entitilaridan (MessageEntityTextUrl, MessageEntityUrl) havolalarni ajratib oladi va Celery navbatiga yoʻnaltiradi.

### 3.3 Telegram Bot Xizmati (`python-telegram-bot`)
* **Vazifasi:** Foydalanuvchilar bilan toʻgʻridan-toʻgʻri muloqot va ogohlantirish kanali.
* **Xususiyatlari:**
  * Foydalanuvchiga tizim haqida ma'lumot beradi.
  * Aniqlangan xavfli, shubhali fishing havolalari haqida darhol xabar (alert) yuboradi.
  * Foydalanuvchiga ogohlantirish sozlamalarini (sezgirlik darajasi, qaysi chatlar uchun ogohlantirish olish) boshqarish imkonini beradi.

### 3.4 Celery Fon Ishchilari (Background Workers)
Tizim yuklamasini API va Telegram oqimidan ajratish uchun barcha resurs talab qiluvchi vazifalar Celery orqali bajariladi:
* **URL Normalizer & Validator:** Havolani tozalash, qisqartirilgan URL-larni yechish, tracking parametrlarini olib tashlash.
* **SSRF Guard & HTTP Fetcher:** Tashqi serverga soʻrov yuborishdan oldin IP manzilni tekshirish (ichki tarmoqqa kirishni bloklash) va xavfsiz sahifa maʼlumotlarini yuklab olish.
* **Enrichment Worker:** DNS yozuvlari, WHOIS domen roʻyxatdan oʻtgan sana, SSL sertifikati holatini yigʻish.
* **AI Evaluation Worker:** Yigʻilgan barcha dalillarni (evidence) Google Gemini modeliga joʻnatish va qatʼiy JSON formatida xulosa olish.
* **Notification Worker:** Natija asosida tegishli ogohlantirishlarni shakllantirish va yuborish.

### 3.5 Redis (Xabarlar Brokeri va Kesh)
* Celery vazifalar navbati uchun transport vositasi.
* Qayta skan qilishni oldini olish maqsadida tekshirilgan URL-larning natijalarini vaqtinchalik keshlash (TTL bilan).
* FloodWait va tezlikni cheklovchi (Rate Limiting) token bucket hisoblagichlari.

### 3.6 PostgreSQL (Asosiy Relyatsion Baza)
* Foydalanuvchilar hisoblari va autentifikatsiya maʼlumotlari.
* **Shifrlangan Telethon sessiyalari** (faqat AES-256-GCM shifrlangan shifromatn saqlanadi).
* Kuzatilayotgan guruh va kanallar metamaʼlumotlari.
* Skanerlangan havolalar, toʻplangan dalillar (evidence audit trail), xavf ballari va AI xulosalari.
* Yuborilgan ogohlantirishlar tarixi.

---

## 4. Komponentlararo Muloqot Qoidalari

1. **API va Celery oʻrtasida:** FastAPI toʻgʻridan-toʻgʻri ogʻir tarmoq yoki AI amallarini bajarmaydi; u faqat Celery tasklarini ishga tushiradi (`apply_async`) va vazifa identifikatorini (task_id) qaytaradi.
2. **Telethon va Maʼlumotlar bazasi oʻrtasida:** Telethon hodisalari roʻyxatdan oʻtganda toʻgʻridan-toʻgʻri bazaga uzoq vaqt sessiya ushlab turmaslik uchun, xabarlarni navbatga uzatadi yoki qisqa tranzaksiya bilan faqat kerakli metamaʼlumotlarni qayd etadi.
3. **Izolyatsiya:** Telethon va Telegram Bot ikkita butunlay alohida jarayon (yoki thread/event loop) hisoblanadi. Ular umumiy xotirani boʻlishmaydi; faqat Redis va PostgreSQL orqali sinxronlashadi.

---

## 5. Ishonchlilik va Nosozliklarga Bardoshlilik (Fault Tolerance)

* **Telegram uzilishlari:** Telethon monitoring uzilib qolsa, avtomatik eksponentsial orqaga chekinish (exponential backoff) bilan qayta ulanish logikasi mavjud.
* **Tashqi saytlarning ishlamasligi:** Tekshirilayotgan sayt ochilmasa yoki timeout bersa, tizim uni "xavfsiz" deb baholamaydi; xulosa "Nomaʼlum / Tekshirib boʻlmadi" (Unknown / Unreachable) deb belgilanadi.
* **Gemini API uzilishlari:** Agar Google Gemini API vaqtincha ishlamasa yoki kvota tugasa, tizim toʻxtab qolmaydi; anʼanaviy qoidalar bazasi (Rule-based heuristics) asosida taxminiy ball hisoblanadi va AI tahlili kechiktirilgan navbatga oʻtkaziladi.
* **Idempotentlik:** Bir xil xabar yoki havola bir necha marta kelsa ham, qayta skan qilinmaydi va foydalanuvchiga takroriy ogohlantirishlar yuborilmaydi.
