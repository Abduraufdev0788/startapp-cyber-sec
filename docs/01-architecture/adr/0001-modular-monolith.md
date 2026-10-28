# ADR 0001: Tizim Arxitekturasi Sifatida "Modular Monolith" Tanlovi

## 1. Holat (Status)
**Qabul qilingan (Accepted)** — Sana: 2026-10-22

---

## 2. Kontekst (Context)

Biz Telegram hisoblarini kuzatuvchi, xabarlardagi havolalarni tekshiruvchi va sun'iy intellekt orqali fishing/firibgarlikni aniqlovchi xavfsizlikka yoʻnaltirilgan backend tizimini loyihalashtirmoqdamiz.

Ushbu tizim bir nechta murakkab domenlarni oʻz ichiga oladi:
* Telegram foydalanuvchi hisoblarini ulash va MTProto orqali monitoring qilish.
* URL normalizatsiyasi va SSRF-dan himoyalangan tarmoq tahlili.
* Domen, DNS, SSL va tashqi obroʻ (reputation) maʼlumotlarini toʻplash.
* Google Gemini AI bilan strukturali integratsiya.
* Foydalanuvchilarni xabardor qilish va xavfsiz audit tizimi.

Ushbu talablarni amalga oshirish uchun dasturiy arxitektura modelini tanlashimiz zarur edi.

---

## 3. Koʻrib Chiqilgan Variantlar (Options Considered)

1. **Toʻliq Mikroxizmatlar (Microservices Architecture):**
   * Alohida xizmatlar: Auth Service, Telegram Monitor Service, Scanner Service, AI Service, Notification Service.
2. **Klassik Tartibsiz Monolit (Traditional Monolith):**
   * Hamma narsa bitta umumiy katalogda, marshrutlar ichida bevosita biznes mantiq yozilgan tizim.
3. **Modulli Monolit (Modular Monolith):**
   * Yagona repozitoriy va yagona deploy qilinuvchi baza, lekin ichida qatʼiy ajratilgan domen modullari, mustaqil repozitoriylar, adapterlar va fon ishchilari (Celery).

---

## 4. Qabul Qilingan Qaror (Decision)

Biz **Modular Monolith** (Modulli Monolit) arxitekturasini tanladik.

Fon rejimida bajariladigan ogʻir vazifalar (URL skanerlash, AI tahlil, tashqi HTTP soʻrovlar) mustaqil Celery workerlariga yuklatiladi.

---

## 5. Qaror Asoslari va Afzalliklari (Rationale)

1. **Kiberxavfsizlik va Kriptografik Boshqaruv:**
   * Telethon sessiyalari va maxfiy maʼlumotlarni shifrlash kalitlari (AES-256 Master Key) yagona himoyalangan perimetrda saqlanadi. Mikroxizmatlararo shifrlangan kalitlarni tarmoq orqali qayta-qayta uzatish xavfi (Network Exposure) kamayadi.
2. **Operatsion Sodpalik (Operational Simplicity):**
   * Mikroxizmatlar uchun talab qilinadigan murakkab xizmatlarni aniqlash (Service Discovery), taqsimlangan tranzaksiyalar (Saga/2PC), alohida Kubernetes klasterlari va tarmoq kechikishlari (Network Latency) oldi olinadi.
3. **Tranzaksion Butunlik (ACID Integrity):**
   * Baza doirasida maʼlumotlarning aniqligi va izchilligini kafolatlash oson (masalan: foydalanuvchi oʻchirilganda, unga tegishli barcha sessiyalar va skanlar toʻgʻri oʻchirilishi).
4. **Kelajakda Ajratish Imkoniyati (Evolutionary Path):**
   * Har bir modul (`modules/url_scanning`, `modules/telegram_accounts` va h.k.) oʻzining alohida interfeysi va repozitoriyalariga ega. Agar kelajakda URL skanerlashga juda katta yuklama tushsa, ushbu modulni mustaqil mikroxizmatga ajratib chiqarish minimal kuch talab qiladi.

---

## 6. Salbiy Oqibatlar va Ularni Yengillashtirish (Consequences & Mitigations)

* **Xavf:** Dasturchilar shoshib, modullar orasidagi chegaralarni buzishi (bir modul boshqasining ichki bazasiga toʻgʻridan-toʻgʻri murojaat qilishi) mumkin.
* **Yechim:** Qatʼiy linting, kod standartlari (`AGENTS.md` qoidalari) va qatlamlararo importlarni tekshiruvchi testlar joriy etiladi.
