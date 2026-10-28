# 02. Konfiguratsiya va Atrof-Muhit Oʻzgaruvchilari (Configuration)

## 1. Kirish va Maqsad

Loyiha Twelve-Factor App tamoyiliga amal qiladi: barcha konfiguratsiyalar koddan qatʼiy ajratilgan boʻlib, atrof-muhit oʻzgaruvchilari (Environment Variables) orqali boshqariladi.

Ushbu hujjat tizimning barcha konfiguratsion parametrlari, ularning turlari, standart qiymatlari va validatsiya qoidalarini belgilaydi.

---

## 2. Toʻliq Konfiguratsiya Parametrlari Jadvali

| Oʻzgaruvchi | Turi | Majburiy | Standart | Tavsifi |
| :--- | :---: | :---: | :--- | :--- |
| `ENVIRONMENT` | String | Ha | `production` | Muhit: `development`, `staging`, `production` |
| `DEBUG` | Bool | Yoʻq | `false` | Batafsil xatoliklar (faqat dev muhitda `true`) |
| `LOG_LEVEL` | String | Yoʻq | `INFO` | Loglash darajasi: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `APP_MASTER_KEY` | String | **Ha** | — | **AES-256-GCM** uchun 32-baytlik heksadesimal kalit |
| `JWT_SECRET_KEY` | String | **Ha** | — | JWT tokenlarini imzolash uchun 64+ belgili maxfiy satr |
| `DATABASE_URL` | String | **Ha** | — | PostgreSQL ulanish manzili (`postgresql+asyncpg://...`) |
| `REDIS_URL` | String | **Ha** | — | Redis brokeri manzili (`redis://:password@host:6379/0`) |
| `TELEGRAM_API_ID` | Int | **Ha** | — | Telegram MTProto API ID raqami |
| `TELEGRAM_API_HASH` | String | **Ha** | — | Telegram MTProto API Hash kaliti |
| `TELEGRAM_BOT_TOKEN`| String | **Ha** | — | Telegram xabarnoma bot tokeni |
| `GEMINI_API_KEY` | String | **Ha** | — | Google Gemini AI API kaliti |
| `GEMINI_MODEL` | String | Yoʻq | `gemini-1.5-flash`| AI modeli nomi |
| `SCANNER_TIMEOUT` | Int | Yoʻq | `5` | Havolani yuklash maksimal vaqti (soniya) |
| `SCANNER_MAX_BYTES`| Int | Yoʻq | `2097152` | Maksimal javob hajmi (2 MB = 2097152 bayt) |
| `SCANNER_MAX_REDIRECTS`| Int | Yoʻq | `5` | Maksimal yoʻnaltirishlar soni |

---

## 3. Pydantic Settings orqali Tezkor Tekshiruv (Fail-Fast Validation)

Tizim ishga tushayotganda `app/core/config.py` moduli barcha oʻzgaruvchilarni qatʼiy tekshiradi. Agar birorta muhim kalit yetishmasa yoki kalit zaif (masalan, master key 32 bayt boʻlmasa), server darhol toʻxtaydi va xatolik beradi:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    APP_MASTER_KEY: str = Field(..., min_length=64) # 32 bytes hex
    DATABASE_URL: str
    REDIS_URL: str
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_BOT_TOKEN: str
    GEMINI_API_KEY: str
    
    @field_validator("APP_MASTER_KEY")
    def validate_key_length(cls, v: str) -> str:
        if len(bytes.fromhex(v)) != 32:
            raise ValueError("APP_MASTER_KEY aniq 32 bayt (64 hex belgi) bo'lishi shart!")
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```
