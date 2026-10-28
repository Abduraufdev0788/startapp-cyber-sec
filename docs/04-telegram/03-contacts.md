# 03. Kontaktlar Boshqaruvi va Maxfiylik (Telegram Contacts Synchronization)

## 1. Kirish va Maqsad

Telegram foydalanuvchilarining kontaktlar roʻyxati shaxsiy maʼlumotlar toifasiga kiradi. Tizim baʼzi xavfsizlik funksiyalarini (masalan: "Faqat notanish shaxslardan yoki kontaktda boʻlmagan foydalanuvchilardan kelgan havolalarni qattiqroq tekshirish" yoki "Kontaktlar nomidan kelayotgan fishing xabarlarini aniqlash") taʼminlash uchun kontaktlar maʼlumotidan foydalanishi mumkin.

Biroq, ushbu jarayon qatʼiy ravishda **ixtiyoriy (Opt-in)** va maxfiylik talablariga muvofiq amalga oshiriladi.

---

## 2. Kontaktlar Maxfiyligi Tamoyillari

```mermaid
flowchart TD
    User["Foydalanuvchi"] --> Consent{"Kontaktlarni sinxronlashga\nanıq rozilik berilganmi?"}
    Consent -->|Yo'q (Standart holat)| NoSync["Kontaktlar yuklab olinmaydi.\nFaqat guruh xabarlari tahlil qilinadi."]
    Consent -->|Ha (Opt-in)| Sync["Faqat kerakli minimal maydonlar olinadi:\nTelegram ID, Ism, Telefon Hash"]
    Sync --> Protect["Telefon raqami ochiq holda saqlanmaydi\n(HMAC-SHA256 hesh qilinadi)"]
    Protect --> Control["Foydalanuvchi istalgan paytda\nkontaktlarni o'chirib tashlashi mumkin"]
```

### Majburiy Qoidalar:
1. **Standart holatda oʻchiq (Opt-in by default):** Akkaunt ulanganda kontaktlar avtomatik sinxronlanmaydi. Foydalanuvchi boshqaruv panelida bunga alohida ruxsat berishi kerak.
2. **Spam va Xabarlar Yuborish Taqiqlangan:** Kontaktlar roʻyxatidagi shaxslarga tizim nomidan yoki foydalanuvchi hisobidan hech qachon ommaviy xabarlar, taklifnomalar yoki spam yuborilmaydi.
3. **Yashirin Telefon Raqamlariga Hurmat:** Telegram Maxfiylik Sozlamalari (Privacy Settings) orqali yashirilgan telefon raqamlarini aylanib oʻtishga (bypass) urinilmaydi.

---

## 3. Saqlanadigan Maydonlar Minimalizmi

Agar foydalanuvchi kontaktlar sinxronizatsiyasiga ruxsat bersa, faqat quyidagi maydonlar saqlanadi:

* `contact_telegram_id`: Foydalanuvchining Telegram ID-si.
* `first_name`, `last_name`: Kontaktning ismi (Telegramda koʻrinishi boʻyicha).
* `phone_number_hash`: Telefon raqamining oʻzi emas, balki qidiruv uchun tuzlangan HMAC heshi.

---

## 4. Kontaktlarni Oʻchirish va Boshqarish

* Foydalanuvchi istalgan vaqtda kontaktlar sinxronizatsiyasini oʻchirib qoʻyishi mumkin (`POST /api/v1/contacts/purge`).
* Bu soʻrov yuborilganda, foydalanuvchiga tegishli barcha saqlangan kontakt yozuvlari maʼlumotlar bazasidan zudlik bilan oʻchirib yuboriladi.
