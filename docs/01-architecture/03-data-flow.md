# 03. Ma'lumotlar Oqimi (End-to-End Data Flow)

## 1. Kirish va Maqsad

Ushbu hujjat tizimda maʼlumotlarning harakatlanish zanjirini bosqichma-bosqich yoritadi: Telegram xabari qabul qilingan paytdan boshlab, havolalarni ajratib olish, xavfsizlik filtrlari, tashqi tahlillar, sun'iy intellekt xulosasi va foydalanuvchiga ogohlantirish yetkazilgunga qadar boʻlgan toʻliq sikl.

---

## 2. Toʻliq Ketma-ketlik Diagrammasi (Sequence Diagram)

Quyidagi diagrammada tizimning barcha ishtirokchi qismlari oʻrtasidagi maʼlumotlar oqimi keltirilgan:

```mermaid
sequenceDiagram
    autonumber
    actor TargetChat as Telegram Chat / Guruh
    participant Telethon as Telethon Account Monitor
    participant Redis as Redis (Kesh & Broker)
    participant WorkerScan as Celery: URL & SSRF Worker
    participant ExtTarget as Maqsadli Veb-sayt
    participant WorkerEnrich as Celery: Enrichment Worker
    participant Gemini as Google Gemini AI
    participant DB as PostgreSQL Bazasi
    participant WorkerNotify as Celery: Alert Worker
    participant TGBot as Telegram Xabarnoma Boti
    actor User as Yakuniy Foydalanuvchi

    TargetChat->>Telethon: Yangi xabar keladi (matn yoki entitiyda havola bor)
    Note over Telethon: Faqat yangi xabar olinadi.<br/>Arxiv yuklanmaydi.
    Telethon->>Telethon: URL-larni ajratish (Entities & Regex)
    
    Telethon->>Redis: Havola allaqachon tekshirilganmi? (Kesh tekshiruvi)
    alt Keshda mavjud (Tekshirilgan va muddati o'tmagan)
        Redis-->>Telethon: Keshdagi xulosa qaytadi (Skan takrorlanmaydi)
    else Yangi havola
        Telethon->>Redis: Skanerlash vazifasini navbatga qo'yish (Task enqueue)
        Redis->>WorkerScan: Vazifani qabul qilish
        
        Note over WorkerScan: 1. URL Normalizatsiyasi<br/>2. SSRF & DNS Rebinding tekshiruvi
        WorkerScan->>WorkerScan: Private IP tekshiruvi (127.0.0.1, 192.168.x.x, 10.x.x.x BLOKLANADI)
        
        alt Agar IP xavfli/ichki tarmoq bo'lsa
            WorkerScan->>DB: "SSRF_BLOCKED" xulosasini saqlash
        else URL tashqi va xavfsiz bo'lsa
            WorkerScan->>WorkerEnrich: Ma'lumot to'plashga uzatish
            
            par Obro' va Domen ma'lumotlari
                WorkerEnrich->>WorkerEnrich: DNS yozuvlari va WHOIS (Domen yoshi)
            and Xavfsiz HTTP So'rov
                WorkerEnrich->>ExtTarget: Cheklangan HTTP GET (Timeout 5s, Max 2MB)
                ExtTarget-->>WorkerEnrich: HTML sarlavhalari, Title, Meta, Bounded Text
            end
            
            WorkerEnrich->>Gemini: Strukturali baholash so'rovi (JSON Schema bilan)
            Gemini-->>WorkerEnrich: Xavf xulosasi (Verdict, Score: 0-100, Reason)
            
            WorkerEnrich->>DB: Skan natijalari va barcha dalillarni (Evidence) saqlash
            WorkerEnrich->>Redis: Natijani keshga yozish (TTL: 24 soat)
            
            alt Agar Xavf darajasi yuqori bo'lsa (Masalan, Score >= 65)
                WorkerEnrich->>WorkerNotify: Ogohlantirish vazifasini yoqish
                WorkerNotify->>Redis: Ushbu foydalanuvchiga yaqinda shu xabar yuborildimi? (Throttling)
                alt Spam/Takroriy emas
                    WorkerNotify->>TGBot: Ogohlantirish yuborish
                    TGBot->>User: ⚠️ DIQQAT: Xavfli fishing havolasi aniqlandi!
                    WorkerNotify->>DB: Xabarnoma yetkazilgani tarixini saqlash
                end
            end
        end
    end
```

---

## 3. Bosqichma-bosqich Tahlil Jarayoni

### 1-bosqich: Xabarni Tutib Olish va Havolalarni Ajratish
* Telethon mijozi `events.NewMessage` hodisasini qabul qiladi.
* Xabardan barcha havolalar quyidagi manbalardan olinadi:
  1. `MessageEntityUrl` — ochiq yozilgan havolalar (masalan: `https://example.com`).
  2. `MessageEntityTextUrl` — matn ostiga yashiringan havolalar (masalan: `[bu yerga bosing](https://phishing-site.com)`).
  3. Matn ichidagi qidiruv (Regex yordamida kiritilgan havolalar).
* Har bir havola umumiy kanonik koʻrinishga (canonical form) keltiriladi:
  * Katta-kichik harflar bir xillashtiriladi (domen qismida).
  * URL oxiridagi keraksiz treking parametrlar (`utm_source`, `fbclid`, `gclid`) tozalanadi.
  * Punycode (IDN homografik hujumlar) tahlil qilinadi (masalan, `xn--...` koʻrinishiga oʻtkaziladi).

### 2-bosqich: Takrorlanishni Tekshirish va Kesh (Deduplication)
* Havolaning SHA-256 heshi hisoblanadi.
* Redis'dan `scanned_urls:hash` kaliti tekshiriladi.
* Agar havola oxirgi 24 soat ichida toʻliq skan qilingan boʻlsa va bazada yangi xulosa mavjud boʻlsa, qayta ogʻir tarmoq va AI soʻrovlari yuborilmaydi (keshdagi natijadan foydalaniladi).

### 3-bosqich: SSRF va Tarmoq Xavfsizligi Tekshiruvi
* **Kiberxavfsizlik talabi:** Foydalanuvchi taqdim etgan URL orqali bizning serverimiz ichki tarmoqlarini (AWS metadata, localhost, 127.0.0.1, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) skan qilishiga yoʻl qoʻyilmasligi shart.
* Havola domeni DNS orqali IP manzilga yechiladi (Resolve).
* Olingan barcha IP-lar qora roʻyxatdan (Private/Loopback/Link-local IP) tekshiriladi. Agar ichki tarmoqqa tegishli boʻlsa, soʻrov darhol toʻxtatiladi va xavfli hodisa sifatida qayd etiladi.

### 4-bosqich: Tashqi Tahlil va Dalillarni Toʻplash (Enrichment)
Xavfsiz deb topilgan tashqi URL boʻyicha quyidagi dalillar (evidence) toʻplanadi:
1. **Domen va DNS maʼlumotlari:**
   * Domen roʻyxatdan oʻtgan sana (agar yaqinda ochilgan boʻlsa, fishing ehtimoli yuqori).
   * A, MX, NS, TXT yozuvlari mavjudligi.
2. **SSL/TLS Sertifikati:**
   * Emitent (Let's Encrypt, Cloudflare, etc.).
   * Sertifikat amal qilish muddati va Common Name.
3. **HTTP Javobi (Bounded Fetch):**
   * HTTP status kodi (200, 301, 302, 404).
   * Yoʻnaltirishlar (Redirects) zanjiri — havola boshqa xavfli domenga yoʻnaltiryaptimi?
   * Sahifa HTML kodidan: Title, Meta description, Favicon havolasi, forma va inputlar mavjudligi (`type="password"` bormi?).
   * HTML sahifadagi matn (faqat dastlabki 50-100 KB matn olinadi, ortiqcha maʼlumotlar xotiradan tozalanadi).

### 5-bosqich: Sun'iy Intellekt Tahlili (Google Gemini)
* Yigʻilgan barcha dalillar (domen yoshi, sertifikat, redirect zanjiri, sahifa sarlavhasi va matni) strukturali prompt koʻrinishida Gemini API'ga yuboriladi.
* Gemini erkin matn emas, balki qatʼiy **JSON Schema** boʻyicha javob qaytaradi:
  * `verdict`: `PHISHING` | `SCAM` | `SUSPICIOUS` | `BENIGN` | `UNKNOWN`
  * `risk_score`: 0 dan 100 gacha son.
  * `confidence`: 0.0 dan 1.0 gacha ishonch koeffitsienti.
  * `reasons`: Sabablari va dalillar roʻyxati.
  * `impersonated_brand`: Soxtalashtirilgan brend nomi (masalan: "Telegram", "Click", "Payme", "Binance").

### 6-bosqich: Xavf Dvigateli (Risk Engine) Yakuniy Qarori
* Tizim nafaqat sun'iy intellektga, balki deterministik (qoidalarga asoslangan) tekshiruvlarga ham tayanadi.
* Masalan: agar domen 2 kun oldin ochilgan boʻlsa va sahifada Telegram login soʻralsa, hatto AI adashib "xavfsiz" desa ham, Risk Engine avtomatik yuqori xavf (CRITICAL) belgilaydi.
* Barcha dalillar va yakuniy qaror PostgreSQL maʼlumotlar bazasida audit uchun saqlanadi.

### 7-bosqich: Xabarnoma Yuborish (Notification)
* Agar yakuniy xavf bali belgilangan chegaradan (Threshold, masalan 65) yuqori boʻlsa:
  * Xabarnoma vazifasi ishga tushadi.
  * Foydalanuvchi sozlamalari tekshiriladi (Ushbu chat uchun ogohlantirishlar yoqilganmi?).
  * Telegram bot orqali foydalanuvchiga aniq, tushunarli va nima uchun xavfli ekani izohlangan ogohlantirish xabari yetkaziladi.
