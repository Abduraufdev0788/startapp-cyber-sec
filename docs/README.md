# Telegram Fishing va Firibgarlikni Aniqlash Platformasi — Texnik Hujjatlar

Ushbu katalog loyihaning toʻliq muhandislik, xavfsizlik, arxitektura va amaliy foydalanish hujjatlarini oʻz ichiga oladi. Loyiha Telegram foydalanuvchi hisoblari orqali xabarlarni xavfsiz kuzatish, kelib tushgan havolalarni (URL) chuqur tahlil qilish, kiberxavflarni aniqlash hamda sun'iy intellekt (Google Gemini) yordamida fishing va firibgarlik (scam) ehtimolini baholash tizimi hisoblanadi.

---

## 📌 Hujjatlar Mundarijasi (Roadmap)

| Boʻlim | Hujjat | Tavsif |
| :--- | :--- | :--- |
| **01. Arxitektura** | [01-system-overview.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/01-architecture/01-system-overview.md) | Tizimning umumiy tuzilishi, komponentlar va oʻzaro bogʻliqliklar |
| | [02-component-boundaries.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/01-architecture/02-component-boundaries.md) | Modullar chegarasi, mas'uliyatlar taqsimoti va qoidalar |
| | [03-data-flow.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/01-architecture/03-data-flow.md) | Xabarni qabul qilishdan ogohlantirish yuborishgacha boʻlgan maʼlumot oqimi |
| | [04-deployment-topology.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/01-architecture/04-deployment-topology.md) | Konteynerlar, tarmoqlar va server infratuzilmasi |
| | [adr/0001-modular-monolith.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/01-architecture/adr/0001-modular-monolith.md) | ADR: Modular Monolith arxitektura tanlovi asosi |
| **02. Xavfsizlik** | [01-threat-model.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/02-security/01-threat-model.md) | Tahdidlar modeli (STRIDE, xavf vektorlari va qarshi choralar) |
| | [02-data-classification.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/02-security/02-data-classification.md) | Maʼlumotlar tasnifi (Ochiq, Maxfiy, Oʻta sezgir maʼlumotlar) |
| | [03-encryption.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/02-security/03-encryption.md) | AES-256-GCM ilova darajasidagi shifrlash va konvert formati |
| | [04-secrets-management.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/02-security/04-secrets-management.md) | Kalitlar, tokenlar va parollarni xavfsiz boshqarish |
| | [05-access-control.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/02-security/05-access-control.md) | Rolga asoslangan kirish huquqi (RBAC) va izolyatsiya |
| | [06-url-scanner-security.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/02-security/06-url-scanner-security.md) | SSRF, DNS Rebinding va zaharli sahifalardan himoyalanish |
| | [07-privacy-and-retention.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/02-security/07-privacy-and-retention.md) | Maxfiylik va maʼlumotlarni oʻchirish/saqlash muddati |
| | [08-incident-response.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/02-security/08-incident-response.md) | Xavfsizlik insidentlariga munosabat bildirish rejasi |
| **03. Maʼlumotlar bazasi** | [01-erd.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/03-database/01-erd.md) | Relyatsion maʼlumotlar modeli diagrammasi (ERD) |
| | [02-data-dictionary.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/03-database/02-data-dictionary.md) | Jadvallar va maydonlarning batafsil maʼlumotnomasi |
| | [03-migrations.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/03-database/03-migrations.md) | Alembic migratsiyalari va sxema oʻzgarishlari tartibi |
| | [04-retention-policy.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/03-database/04-retention-policy.md) | Arxivlash va eski xabarlarni tozalash jarayoni |
| **04. Telegram** | [01-account-authorization.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/04-telegram/01-account-authorization.md) | Telethon orqali foydalanuvchi hisobini xavfsiz ulash |
| | [02-monitoring.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/04-telegram/02-monitoring.md) | Chatlarni monitoring qilish, event listener va xabarlarni qabul qilish |
| | [03-contacts.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/04-telegram/03-contacts.md) | Kontaktlar sinxronizatsiyasi va cheklovlar |
| | [04-limits-and-restrictions.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/04-telegram/04-limits-and-restrictions.md) | Telegram API cheklovlari va FloodWait bilan ishlash |
| **05. Fishingni aniqlash** | [01-url-pipeline.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/05-detection-engine/01-url-pipeline.md) | Havolalarni ajratib olish va tozalash quvuri |
| | [02-threat-intelligence.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/05-detection-engine/02-threat-intelligence.md) | Domen, DNS, SSL/TLS va obroʻ tahlili |
| | [03-gemini-contract.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/05-detection-engine/03-gemini-contract.md) | Google Gemini AI soʻrovlar shabloni va JSON sxemasi |
| | [04-risk-engine.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/05-detection-engine/04-risk-engine.md) | Xavf ballarini hisoblash qoidalari va xulosa chiqarish |
| | [05-caching-and-dedup.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/05-detection-engine/05-caching-and-dedup.md) | Qayta tekshirishlarni oldini olish va Redis kesh mexanizmi |
| **06. Ogohlantirishlar** | [01-alert-policy.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/06-notifications/01-alert-policy.md) | Ogohlantirish mezonlari va qoidalari |
| | [02-message-templates.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/06-notifications/02-message-templates.md) | Telegram bot xabarnoma shablonlari |
| | [03-throttling-and-dedup.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/06-notifications/03-throttling-and-dedup.md) | Takroriy xabarlarni filtrlash va limitlash |
| **07. API** | [01-overview.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/07-api/01-overview.md) | FastAPI REST arxitekturasi va umumiy tamoyillar |
| | [02-authentication.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/07-api/02-authentication.md) | JWT tokenlar va sessiya boshqaruvi |
| | [03-endpoints.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/07-api/03-endpoints.md) | Barcha endpointlar spetsifikatsiyasi |
| | [04-error-codes.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/07-api/04-error-codes.md) | Xatoliklar kodi va standart javoblar |
| **08. Operatsiyalar** | [01-deployment.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/08-operations/01-deployment.md) | Ishga tushirish (Deploy) va konteynerlashtirish |
| | [02-configuration.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/08-operations/02-configuration.md) | Sozlamalar va `.env` parametrlari |
| | [03-monitoring.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/08-operations/03-monitoring.md) | Tizim salomatligi, metrikalar va loglar |
| | [04-backup-and-recovery.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/08-operations/04-backup-and-recovery.md) | Zaxira nusxalash va avariyadan keyin tiklash |
| **09. Ishlab chiqish** | [01-local-setup.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/09-development/01-local-setup.md) | Mahalliy muhitni sozlash |
| | [02-coding-standards.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/09-development/02-coding-standards.md) | Kodlash standartlari, linting va formatlash |
| | [03-testing.md](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/09-development/03-testing.md) | Test turlari va sifat kafolati |

---

## 🎯 Asosiy Muhandislik Tamoyillari

Ushbu platforma oddiy Telegram boti emas, balki kiberxavfsizlik talablariga toʻliq javob beradigan ishlab chiqarish darajasidagi tizimdir. Ishlab chiqishda quyidagi tamoyillarga qat'iy amal qilinadi:

1. **Security-First (Birinchi oʻrinda xavfsizlik):** Dasturlash qulayligi uchun xavfsizlik hech qachon qurbon qilinmaydi.
2. **Data Minimization (Maʼlumotlarni minimallashtirish):** Faqat ruxsat berilgan va funksional zarur boʻlgan metadata saqlanadi. Xabarlar arxivi yuklab olinmaydi.
3. **Session Protection (Sessiyalar himoyasi):** Telethon sessiyalari ilova darajasida AES-256-GCM orqali shifrlanadi, ochiq holda loglarga yoki API orqali uzatilmaydi.
4. **Untrusted Input (Ishonchsiz kiruvchi maʼlumotlar):** Hech bir URL, havola, tashqi veb-sayt kontenti yoki hatto AI javobi mutlaq toʻgʻri deb ishonilmaydi.
5. **Explainable AI (Tushuntirilishi mumkin boʻlgan AI):** Gemini bergan baho yagona haqiqat hisoblanmaydi; u har doim texnik dalillar (DNS, SSL, Domen yoshi, HTTP javoblari) bilan mustahkamlanadi.
