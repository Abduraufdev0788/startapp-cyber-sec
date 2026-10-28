# 03. Tizim Monitoringi va Metrikalar (Observability & Monitoring)

## 1. Kirish va Maqsad

Kiberxavfsizlik va backend barqarorligini taʼminlash uchun tizimning ichki holati doimiy ravishda koʻrinadigan (observable) boʻlishi lozim.

Ushbu hujjat tizim salomatligi (Health Checks), metrikalar (Prometheus), strukturalashtirilgan JSON loglar hamda operatsion muammolarni oldindan ogohlantirish (Alerting) standartlarini belgilaydi.

---

## 2. Salomatlik Tekshiruvlari (Health Checks)

Kubernetes yoki Docker sogʻliqni nazorat qiluvchi (Healthcheck) mexanizmlari uchun 2 ta endpoint taqdim etiladi:

1. **Liveness Probe (`GET /api/v1/health/liveness`):**
   * Jarayon (process) tirik ekanligini bildiradi.
   * Doim tezkor `200 OK` qaytaradi. Agar javob bermasa, konteyner qayta ishga tushiriladi (restart).
2. **Readiness Probe (`GET /api/v1/health/readiness`):**
   * Tizim tashqi soʻrovlarni qabul qilishga toʻliq tayyormi yoki yoʻqligini tekshiradi:
     * PostgreSQL ulanishi: `SELECT 1;`
     * Redis kesh ulanishi: `PING -> PONG`
     * Celery broker holati.
   * Agar baza yoki Redis ishlamayotgan boʻlsa, `503 Service Unavailable` qaytaradi va Nginx yuklamani ushbu konteynerga yoʻnaltirmaydi.

---

## 3. Prometheus Metriklari (`/metrics`)

Tizim monitoring paneli (Grafana) uchun quyidagi asosiy metrikalarni taqdim etadi:

* `http_requests_total`: HTTP soʻrovlarining umumiy soni (status kodlar va yoʻllar boʻyicha).
* `http_request_duration_seconds`: API javob qaytarish tezligi gistogrammasi.
* `active_telethon_accounts`: Hozirda faol monitoring olib borayotgan Telegram hisoblari soni.
* `scanned_urls_total{verdict="PHISHING|BENIGN"}`: Skan qilingan havolalar soni xulosalar boʻyicha.
* `celery_queue_length`: Celery navbatida kutib turgan vazifalar soni.
* `gemini_api_latency_seconds`: Google Gemini AI javob berish vaqti.

---

## 4. Strukturalashtirilgan JSON Loglar

Barcha loglar oddiy matn emas, balki ELK (Elasticsearch/Logstash/Kibana) yoki Grafana Loki uchun qulay boʻlgan **JSON formatida** chiqariladi:

```json
{
  "timestamp": "2026-10-22T18:10:00.123Z",
  "level": "INFO",
  "logger": "app.modules.url_scanning.service",
  "message": "Havola muvaffaqiyatli baholandi",
  "request_id": "req-98765-abcdef",
  "domain": "fake-bank[.]uz",
  "verdict": "PHISHING",
  "risk_score": 95,
  "evaluated_by": "GEMINI_1_5_FLASH"
}
```

* Barcha loglarda parollar, SMS kodlar va Telegram sessiya satrlari avtomatik `[REDACTED]` ga almashtiriladi.
