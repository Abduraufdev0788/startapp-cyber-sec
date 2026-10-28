# 01. Ogohlantirish Siyosati va Qoidalari (Alert Policy)

## 1. Kirish va Maqsad

Fishing va firibgarlikni aniqlash tizimining yakuniy natijasi — bu xavf haqida foydalanuvchini oʻz vaqtida, aniq va tushunarli tarzda ogohlantirishdir. Biroq, haddan tashqari koʻp va keraksiz ogohlantirishlar (Alert Fatigue) foydalanuvchining e'tiborsizligiga yoki botni bloklab qoʻyishiga olib keladi.

Ushbu hujjat qachon, kimga va qanday shartlar asosida ogohlantirish xabarnomalari yuborilishini belgilovchi siyosatni (Alert Policy) oʻz ichiga oladi.

---

## 2. Ogohlantirish Mezonlari (Trigger Criteria)

Xabarnomalar xavf bali (`risk_score`) va xulosaga (`verdict`) asoslangan holda 2 ta toifaga boʻlinadi:

```mermaid
flowchart TD
    Verdict["Xavf Bahosi"] --> Check{"Xavf Bali Qanday?"}
    
    Check -->|Score < 60 (BENIGN / LOW)| NoAlert["Ogohlantirish yuborilmaydi\n(Faqat audit va statistikada saqlanadi)"]
    Check -->|Score 60 - 79 (SCAM / SUSPICIOUS)| WarningAlert["🟡 OGOHLANTIRISH (Warning Alert)\nEhtiyotkorlikka chaqiruvchi xabar"]
    Check -->|Score >= 80 (CRITICAL PHISHING)| CriticalAlert["🔴 XAVF (Critical Phishing Alert)\nZudlik bilan ogohlantirish"]
```

---

## 3. Qabul Qiluvchilarni Tanlash va Qoidalar

1. **Faqat Vakolatli Foydalanuvchiga Yuborish:**
   * Ogohlantirish xabarlari hech qachon guruhning oʻziga (ommaviy chatga) yoki begona odamlarga yuborilmaydi.
   * Ogohlantirish faqat ushbu xabarni kuzatgan va hisobini tizimga ulagan **platforma foydalanuvchisining rasmiy Telegram Botdagi shaxsiy yozishmasiga (Direct Message)** yuboriladi.
2. **Foydalanuvchi Sozlamalari (User Preferences):**
   * Foydalanuvchi bot sozlamalari orqali:
     * Ogohlantirish sezgirligini tanlashi mumkin (Faqat qizil/kritik xavflar yoki shubhali saytlar ham).
     * Alohida guruhlar uchun ogohlantirishlarni vaqtincha oʻchirib qoʻyishi (Mute) mumkin.

---

## 4. Xavfsizlik va Spamdan Himoya

* Tizim hech qachon foydalanuvchi hisobidan (Userbot orqali) javob xabari yozmaydi (chunki bu Telegram qoidalariga koʻra hisobning bloklanishiga olib kelishi mumkin).
* Barcha xabarlar faqat Telegram tomonidan tasdiqlangan rasmiy Bot API orqali amalga oshiriladi.
