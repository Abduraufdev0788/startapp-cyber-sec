# 02. Kodlash Standartlari va Sifat Nazorati (Coding Standards)

## 1. Kirish va Maqsad

Kiberxavfsizlikka yoʻnaltirilgan tizimda kod sifati toʻgʻridan-toʻgʻri xavfsizlik darajasini belgilaydi. Dasturdagi oddiy e'tiborsizlik, istisnolarni e'tiborsiz qoldirish yoki xom tipizatsiya xavfli zaifliklarga sabab boʻlishi mumkin.

Ushbu hujjat loyihada qoʻllaniladigan qatʼiy Python kodlash standartlari, statik tahlil (Linting) va tipizatsiya (Type Checking) qoidalarini belgilaydi.

---

## 2. Asosiy Qoidalar va Vositalar

| Asbob | Vazifasi | Konfiguratsiya Fayli | Buyruq |
| :--- | :--- | :--- | :--- |
| **Ruff** | Tezkor linter va kod formatlash (Black, Flake8, Isort oʻrniga) | `pyproject.toml` | `ruff check .` / `ruff format .` |
| **Mypy** | Qatʼiy statik tipizatsiya tekshiruvi (Type checking) | `pyproject.toml` | `mypy app` |
| **Pytest** | Avtomatlashtirilgan testlarni bajarish | `pytest.ini` | `pytest` |

---

## 3. Qat'iy Muhandislik Qoidalari (Mandatory Rules)

1. **Xatoliklarni Hech Qachon Jim Yutmang (No Silent Exception Swallowing):**
   ```python
   # ❌ QAT'IYAN TAQIQLANADI:
   try:
       await process_url(url)
   except Exception:
       pass  # Xatolik yashirildi!

   # ✅ TO'G'RI:
   try:
       await process_url(url)
   except TargetUnreachableError as e:
       logger.warning("Maqsadli sayt ochilmadi: %s", str(e), exc_info=True)
       return ScanStatus.UNREACHABLE
   ```
2. **Qat'iy Tipizatsiya (Strict Typing):**
   * Barcha funksiyalar kiruvchi argumentlari va qaytaruvchi qiymati uchun toʻliq Type Annotation boʻlishi shart:
     ```python
     async def get_account_by_id(db: AsyncSession, account_id: UUID) -> TelegramAccount | None:
         ...
     ```
3. **Asinxron Rejimda Bloklovchi So'rovlar Qilmang (No Blocking I/O):**
   * `async def` ichida hech qachon `requests.get()`, `time.sleep()` yoki `open()` kabi sinxron bloklovchi funksiyalarni ishlatmang.
   * Doim asinxron alternativlardan foydalaning: `httpx.AsyncClient()`, `asyncio.sleep()`, `aiofiles`.
4. **Pydantic Modellaridan Majburiy Foydalanish:**
   * Barcha tashqi maʼlumotlar (API soʻrovlari, Gemini javoblari, Redis kesh maʼlumotlari) faqat Pydantic orqali validatsiya qilinadi. Lugʻat (dict) bilan koʻr-koʻrona ishlash taqiqlanadi.
