# 01. REST API Umumiy Koʻrinish va Standartlar (API Overview)

## 1. Kirish va Maqsad

Ushbu hujjat FastAPI asosidagi RESTful API arxitekturasini, versiyalash qoidalarini, soʻrov va javob formatlarining umumiy konvertini (Response Envelope) hamda soʻrovlarni kuzatish (Request ID Tracing) standartlarini belgilaydi.

---

## 2. Asosiy API Tamoyillari

1. **Baza URL va Versiyalash:** Barcha marshrutlar versiyalangan holda taqdim etiladi: `/api/v1/...`.
2. **Format:** Barcha kiruvchi va chiquvchi maʼlumotlar qatʼiy `application/json` formatida boʻladi.
3. **Interaktiv Hujjatlar:** FastAPI avtomatik tarzda Swagger (`/docs`) va ReDoc (`/redoc`) interfeyslarini taqdim etadi (ishlab chiqarishda oʻchirib qoʻyish mumkin).
4. **Idempotentlik:** `GET`, `PUT`, `DELETE` soʻrovlari idempotent boʻlishi lozim.

---

## 3. Standart Javob Konverti (Response Envelope)

Barcha API javoblari frontend va mijozlar uchun bir xil standart qolipda (envelope) qaytariladi:

### 3.1 Muvaffaqiyatli Javob (Success Response)
```json
{
  "success": true,
  "data": {
    "scan_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "verdict": "PHISHING",
    "risk_score": 92
  },
  "meta": {
    "timestamp": "2026-10-22T18:00:00Z",
    "request_id": "req-f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }
}
```

### 3.2 Xatolik Javobi (Error Response)
```json
{
  "success": false,
  "error": {
    "code": "SSRF_ATTEMPT_BLOCKED",
    "message": "Kiritilgan havola xususiy ichki tarmoq manziliga yo'naltirilgan va xavfsizlik nuqtai nazaridan bloklandi.",
    "details": []
  },
  "meta": {
    "timestamp": "2026-10-22T18:00:00Z",
    "request_id": "req-f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }
}
```

---

## 4. Soʻrovlarni Kuzatish (Request ID Tracing)

* Har bir kelgan HTTP soʻrov FastAPI `CorrelationIdMiddleware` middleware orqali tekshiriladi.
* Agar mijozdan `X-Request-ID` sarlavhasi kelmasa, tizim avtomatik yangi UUID generatsiya qiladi.
* Ushbu `request_id` barcha tegishli loglar, Celery tasklari va javob sarlavhalariga qoʻshiladi. Bu biror muammo chiqqanda aniq bitta soʻrov boʻyicha barcha harakatlarni loglardan bir zumda topish imkonini beradi.
