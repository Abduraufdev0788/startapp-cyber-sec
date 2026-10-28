# 04. Xatolik Kodlari va Standart Javoblar (Error Codes)

## 1. Kirish va Maqsad

Ushbu hujjat API xatoliklarini standartlashtirish, foydalanuvchi va frontend ishlab chiquvchilarga xatolik sababini aniq tushuntirish hamda ichki server xatolarida xavfsizlik maʼlumotlarini yashirish qoidalarini belgilaydi.

---

## 2. Xatolik Kodlari Lug'ati

| HTTP Status | Xatolik Kodi (`code`) | Tavsif |
| :---: | :--- | :--- |
| **400** | `INVALID_URL_SCHEME` | Faqat `http://` va `https://` protokollari qabul qilinadi |
| **400** | `SSRF_ATTEMPT_BLOCKED` | Havola xususiy, lokal yoki xavfli IP manzilga yoʻnaltirilgan |
| **400** | `PHONE_CODE_INVALID` | Kiritilgan Telegram SMS/OTP kodi notoʻgʻri |
| **400** | `PASSWORD_2FA_INVALID`| Telegram 2FA bulutli paroli notoʻgʻri |
| **401** | `UNAUTHORIZED` | Soʻrovda token taqdim etilmagan |
| **401** | `TOKEN_EXPIRED` | JWT access token muddati tugagan |
| **401** | `TOKEN_REVOKED` | Ushbu token bekor qilingan (Logout qilingan) |
| **403** | `FORBIDDEN` | Ushbu amalni bajarish uchun rolingiz yetarli emas |
| **404** | `NOT_FOUND` | Soʻralgan resurs (hisob, havola, chat) topilmadi |
| **409** | `ACCOUNT_ALREADY_CONNECTED`| Ushbu Telegram hisobi allaqachon tizimga ulangan |
| **422** | `VALIDATION_ERROR` | Yuborilgan JSON maydonlari Pydantic sxemasiga mos kelmadi |
| **429** | `RATE_LIMIT_EXCEEDED` | Qisqa vaqt ichida juda koʻp soʻrov yuborildi |
| **429** | `TELEGRAM_FLOOD_WAIT` | Telegram soʻrovlarni vaqtincha chekladi (Kutish soniyasi beriladi) |
| **502** | `TARGET_UNREACHABLE` | Tekshirilayotgan tashqi sayt ochilmadi yoki timeout berdi |
| **503** | `AI_PROVIDER_UNAVAILABLE`| Google Gemini xizmati vaqtincha javob bermayapti |
| **500** | `INTERNAL_SERVER_ERROR` | Tizimda kutilmagan ichki xatolik yuz berdi |

---

## 3. Ichki Xatoliklarni Yashirish (Security Redaction)

* Ishlab chiqarish muhitida `500 Internal Server Error` yuz berganda:
  * Foydalanuvchiga hech qachon Python stack trace, SQL soʻrov yoki fayl yoʻllari koʻrsatilmaydi!
  * Faqat quyidagi xavfsiz javob qaytariladi:
    ```json
    {
      "success": false,
      "error": {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "Kutilmagan xatolik yuz berdi. Xavfsizlik jurnali tekshirilmoqda."
      },
      "meta": {
        "request_id": "req-98765-abcdef"
      }
    }
    ```
  * Xatolikning toʻliq tafsiloti esa xavfsiz server loglariga faqat `request_id` bilan bogʻlangan holda yoziladi.
