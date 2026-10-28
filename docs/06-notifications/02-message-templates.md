# 02. Xabarnoma Shablonlari va Ilovaga Yoʻnaltirish (Message Templates & Deep Linking)

## 1. Kirish va Maqsad

Zararli havola aniqlanganda foydalanuvchini faqat Telegram orqali ogohlantirish yetarli emas. Foydalanuvchi xabarni oʻqimasdan oʻtkazib yuborishi mumkin. Shu sababli, bot yuboradigan har bir ogohlantirish ichida **asosiy ilovaga olib boruvchi maxsus tugma (Deep Link / WebApp)** joylashtiriladi.

Foydalanuvchi ilovaga kirganida, ekranda doimiy bloklovchi ogohlantirish oynasi (Persistent Modal) paydo boʻladi va u xabarni oʻchirib yubormaguncha (`is_dismissed=True`) oyna yopilmaydi.

---

## 2. Havolalarni Zararsizlantirish (URL Defanging)

Ogohlantirish xabarida havola quyidagicha xavfsiz matnga aylantiriladi:
* `http://` -> `hxxp://`
* `https://` -> `hxxps://`
* `.` (nuqta) -> `[.]`
* Masalan: `https://fake-telegram-login.com` -> `hxxps://fake-telegram-login[.]com`

---

## 3. Telegram Bot Xabarnoma Shablonlari va Tugmalar

### 3.1 🔴 Favqulodda Xavfli Fishing (Critical Phishing Alert)

```text
🚨 DIQQAT: TELEGRAMINGIZGA XAVFLI FISHING HAVOLASI KELDI!

📍 Guruh/Chat: {chat_title}
🔗 Zararli Havola: {defanged_url}
🎯 Soxtalashtirilgan Brend: {impersonated_brand}
⚠️ Xavf Darajasi: {risk_score}/100 (O'ta Yuqori)

🔍 Aniqlangan Asosiy Belgilar:
• {reason_1}
• {reason_2}
• {reason_3}

🛡 TAVSIYA ETILADIGAN HARAKATLAR:
1. Ushbu havolaga aslo kirmang!
2. Parol, karta yoki Telegram SMS kodlarini kiritmang!

⚠️ Ushbu xavf ilovangizda faol holatda saqlanmoqda. Xavfni ko'rish va o'chirish uchun quyidagi tugmani bosing:
```

#### Inline Tugmalar (Inline Keyboard):
```text
[ 📲 Ilovaga o'tish va xavfni ko'rish ]  --> https://app.phishguard.uz/alerts/{alert_id}
[ ❓ Qo'llab-quvvatlash xizmati ]         --> https://t.me/phishguard_support
```

---

### 3.2 🟡 Firibgarlik va Shubhali Havola (Scam / Warning Alert)

```text
⚠️ OGOHLANTIRISH: SHUBHALI FIRIBGARLIK HAVOLASI KELDI!

📍 Guruh/Chat: {chat_title}
🔗 Havola: {defanged_url}
⚠️ Xavf Darajasi: {risk_score}/100 (O'rtacha / Shubhali)

🔍 Nima uchun shubhali?
• {reason_1}
• {reason_2}

💡 Sayt yangi ochilgan yoki soxta sovg'alar va'da qilmoqda.
```

#### Inline Tugmalar:
```text
[ 📲 Ilovada ko'rish va bartaraf etish ] --> https://app.phishguard.uz/alerts/{alert_id}
```

---

## 4. Ilovadagi Doimiy Oyna (App Persistent Alert Modal)

Foydalanuvchi ilovaga kirganda:
1. Ilova avtomatik `GET /api/v1/notifications/active` soʻrovini yuboradi.
2. Agar oʻchirilmagan xavflar boʻlsa (`has_active_alerts: true`):
   * Ekranning markazida qizil ramkali bloklovchi ogohlantirish oynasi chiqadi.
   * Unda xavfli havola, tahlil sabablari va tavsiyalar koʻrsatiladi.
3. Foydalanuvchi pastdagi **"Tushundim / Xavfni o'chirish"** tugmasini bosgandagina:
   * Ilova `POST /api/v1/notifications/{alert_id}/dismiss` soʻrovini joʻnatadi.
   * Xavf oʻchirilgan deb belgilanadi va oyna yopiladi.
