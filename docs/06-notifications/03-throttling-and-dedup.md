# 03. Xabarnomalarni Cheklash va Spamdan Himoya (Throttling & Deduplication)

## 1. Kirish va Maqsad

Guruhlarda koʻpincha bitta spammer bir daqiqada 10-20 ta bir xil fishing xabarlarini yuborishi yoki oʻnlab guruhlarda bir xil havola tarqatilishi mumkin. Agar bot har bir xabar uchun foydalanuvchiga alohida ogohlantirish yuborsa:
1. Foydalanuvchi xabarlar koʻpligidan bezor boʻladi (Notification Fatigue).
2. Telegram Bot API tezlik limitiga (`Telegram API 429: Too Many Requests`) tushib, xizmat vaqtincha bloklanadi.

Ushbu hujjat xabarnomalarni cheklash (Throttling), takroriylikni filtrlash (Deduplication) va ommaviy xabarlarni guruhlash mexanizmlarini belgilaydi.

---

## 2. Takroriy Ogohlantirishlarni Filtrlash (Deduplication)

```mermaid
flowchart TD
    ScanAlert["Yangi Xavf Aniqlanganda (Task)"] --> CheckRedis{"Redis Tekshiruvi:\nalert_sent:{user_id}:{url_hash}"}
    
    CheckRedis -->|Kalit mavjud (So'nggi 1 soatda yuborilgan)| Skip["OGOHLANTIRISH YUBORILMAYDI\n(Bazada 'THROTTLED' deb qayd etiladi)"]
    
    CheckRedis -->|Kalit yo'q| Send["Bot orqali Ogohlantirish Yuborish"]
    Send --> SetKey["Redis'ga yozish:\nalert_sent:{user_id}:{url_hash} (TTL: 1 soat)"]
```

* Agar bir xil zararli havola bitta foydalanuvchi koʻrayotgan 5 ta turli guruhda uchrasa ham, foydalanuvchiga faqat **bitta birinchi ogohlantirish** yuboriladi. Keyingi takrorlanishlar 1 soat davomida bostiriladi (Throttled).

---

## 3. Telegram Bot API Cheklovlariga Muvofiqlik

Telegram rasmiy Bot API quyidagi qatʼiy cheklovlarga ega:
* **Bitta chatga:** Soniyasiga koʻpi bilan **1 ta xabar**.
* **Global barcha chatlarga:** Soniyasiga koʻpi bilan **30 ta xabar**.

### Celery Ishchi Sozlamalari:
* Xabarnomalar yuboruvchi Celery navbati (`notifications_queue`) uchun maxsus tezlik chegarasi oʻrnatiladi:
  ```python
  @celery_app.task(
      bind=True,
      rate_limit="20/s",  # Soniyasiga ko'pi bilan 20 ta xabar
      max_retries=3,
      default_retry_delay=5
  )
  def send_telegram_alert_task(self, user_id, message_text):
      ...
  ```
* Agar Telegram `RetryAfter` (429 xatolik) qaytarsa, Celery taski Telegram soʻragan soniyaga avtomatik kechiktiriladi (`countdown = exc.retry_after`).
