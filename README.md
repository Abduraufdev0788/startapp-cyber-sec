# Telegram Phishing & Scam Detection Platform

> **Production-grade, security-focused Telegram monitoring and phishing detection backend.**  
> Built with **FastAPI**, **Telethon**, **python-telegram-bot**, **PostgreSQL**, **Celery**, **Redis**, and **Google Gemini AI**.

---

## 🛡️ Overview

The **Telegram Phishing & Scam Detection Platform** is a security-critical modular monolith backend designed to proactively detect, analyze, and neutralize phishing campaigns, credential harvesters, and malicious URLs shared across Telegram channels and groups.

Authorized users connect their Telegram accounts via an explicit OAuth/MTProto verification flow. The backend monitors incoming messages in real-time without dumping historical archives, extracts and normalizes URLs, applies multi-layer **SSRF and DNS rebinding protections**, enriches domain telemetry (DNS, WHOIS/RDAP, TLS, HTTP redirects), and utilizes **Google Gemini structured AI analysis** to compute an explainable risk verdict (0–100 score). High-risk threats trigger instant defanged Telegram alert notifications (`hxxps://...[.]com`) with actionable guidance.

---

## 🚀 Key Features

* **Real-time Telegram Monitoring:** Continuous MTProto event listener via Telethon with graceful reconnection and rate-limit recovery.
* **AES-256-GCM Envelope Encryption:** Persistent user sessions and credentials are encrypted using authenticated envelope encryption bound to user IDs via Associated Authenticated Data (AAD).
* **Robust SSRF & DNS Rebinding Defenses:** Strict IP resolution validator blocking loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), private networks (RFC 1918), IPv6 unique local/loopback, and cloud metadata endpoints.
* **URL Canonicalization & Homograph Normalization:** Strips tracking parameters (`utm_*`, `fbclid`, `gclid`), resolves Punycode / IDN homograph spoofing, and computes deterministic SHA-256 hashes for fast lookup.
* **Structured Gemini AI Output:** Validates suspicious social engineering tactics using strict Pydantic JSON schemas on Google Gemini 2.5 Flash models.
* **Deterministic Brand Protection:** Flags unauthorized web assets that impersonate major financial institutions, government portals, or Telegram itself.
* **Role-Based Access Control (RBAC):** Granular access tiers (`USER`, `ANALYST`, `ADMIN`) securing administrative dashboards, scan histories, and audit logs.
* **Redis-Backed Atomic Rate Limiting:** Built-in protection against brute-force and DoS attacks on authentication and scanning endpoints with automatic fail-open resilience.
* **Observability & Probes:** K8s/Docker-ready `/api/v1/health/liveness` and `/api/v1/health/readiness` probes verifying PostgreSQL and Redis connections.

---

## 🏗️ Architecture & Directory Layout

```text
phishing-detector-backend/
├── app/
│   ├── api/
│   │   ├── deps.py             # Auth dependencies & RBAC (get_current_user, get_current_admin_user)
│   │   └── v1/
│   │       ├── router.py       # API v1 route aggregator
│   │       └── endpoints/      # admin, auth, health, notifications, scans, telegram
│   ├── core/
│   │   ├── config.py           # Pydantic Settings & environment variables
│   │   ├── exceptions.py       # Global domain exceptions (AppException, Auth, Forbidden)
│   │   ├── logging.py          # Structured JSON & console logger configuration
│   │   ├── rate_limit.py       # Redis atomic INCR+EXPIRE sliding window rate limiter
│   │   └── security.py         # AES-256-GCM envelope cipher, Argon2id, JWT issuance
│   ├── db/
│   │   ├── base.py             # SQLAlchemy DeclarativeBase
│   │   ├── models.py           # Centralized mapper registry export
│   │   └── session.py          # Async & Sync SQLAlchemy 2.x session factories
│   ├── modules/
│   │   ├── audit/              # Audit trails (IP, User-Agent, Event, Timestamp)
│   │   ├── notifications/      # Notification models & delivery tracking
│   │   ├── risk_engine/        # Multi-factor risk engine (0-100 score calculation)
│   │   ├── telegram_accounts/  # Encrypted MTProto session records
│   │   ├── telegram_chats/     # Chat, channel, and message metadata
│   │   ├── threat_intelligence/# Safe HTTP fetcher, DNS, RDAP/WHOIS enricher
│   │   ├── url_scanning/       # URL pipeline, hashers, and SSRF guard
│   │   └── users/              # User models & Argon2id authentication
│   ├── integrations/
│   │   ├── gemini/             # Google GenAI SDK client adapter with schema enforcement
│   │   ├── telegram_bot/       # python-telegram-bot alert dispatcher
│   │   └── telethon/           # User-account MTProto monitoring engine
│   ├── static/
│   │   └── admin/              # Admin Web Dashboard (HTML5, Vanilla CSS, JS)
│   └── workers/
│       ├── celery_app.py       # Celery configuration & queue routing
│       └── tasks/              # Background scanning & notification delivery tasks
├── docs/                       # Architecture, threat model, encryption, and API docs
├── scripts/
│   ├── create_admin.py         # CLI tool to create or promote administrator accounts
├── tests/
│   ├── security/               # SSRF and network isolation tests
│   └── unit/                   # Admin, Auth, Health, Pipeline, Risk, Scans, Telegram tests
├── Dockerfile                  # Production container definition
├── docker-compose.yml          # Multi-container orchestration stack
├── alembic.ini                 # Database migration configuration
├── pyproject.toml              # Ruff, Mypy, and Pytest configuration
└── requirements.txt            # Pinned production dependencies
```

---

## 📋 Prerequisites

Ensure your host environment meets the following specifications:

* **Operating System:** Linux (Ubuntu 22.04+ recommended), macOS, or Windows with WSL2
* **Python:** 3.11 or 3.12+
* **Docker & Docker Compose:** Docker Engine 24+ and Docker Compose v2+
* **PostgreSQL:** Version 16+ (provided automatically via Docker)
* **Redis:** Version 7+ (provided automatically via Docker)
* **Telegram API Credentials:** `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
* **Telegram Bot Token:** Created via [@BotFather](https://t.me/BotFather)
* **Google Gemini API Key:** Generated from [Google AI Studio](https://aistudio.google.com/)

---

## ⚙️ Environment Configuration

### 1. Create `.env` file

Copy the provided template to create your local environment file:

```bash
cp .env.example .env
```

### 2. Generate Cryptographic Master Keys

The platform mandates a 32-byte (64 hex characters) AES-256 master key for envelope encryption and a high-entropy secret for JWT signing. Generate them using `openssl`:

```bash
# Generate 32-byte AES-256-GCM Master Key
openssl rand -hex 32

# Generate 64-character JWT Secret Key
openssl rand -hex 32
```

### 3. Configure Key Variables in `.env`

Edit your `.env` file and insert the generated secrets along with your external credentials:

```dotenv
# Environment mode: development | staging | production
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO

# Security & Cryptography
APP_MASTER_KEY=<paste_32_byte_hex_key_here>
JWT_SECRET_KEY=<paste_64_character_hex_key_here>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database (PostgreSQL 16)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_secure_password
POSTGRES_DB=phishing_db
DATABASE_URL=postgresql+asyncpg://postgres:postgres_secure_password@postgres:5432/phishing_db
SYNC_DATABASE_URL=postgresql://postgres:postgres_secure_password@postgres:5432/phishing_db

# Redis 7
REDIS_PASSWORD=redis_secure_password
REDIS_URL=redis://:redis_secure_password@redis:6379/0

# Telegram API & Bot Credentials
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef0123456789abcdef0123456789
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ_example

# Google Gemini AI
GEMINI_API_KEY=AIzaSyD-YourGeminiApiKeyHere
GEMINI_MODEL=gemini-2.5-flash

# Scanner & Network Constraints (SSRF & DoS Defenses)
SCANNER_CONNECT_TIMEOUT_SECONDS=5
SCANNER_TOTAL_TIMEOUT_SECONDS=10
SCANNER_MAX_RESPONSE_BYTES=2097152 # 2 MB ceiling
SCANNER_MAX_REDIRECTS=5
```

> [!WARNING]
> Never commit `.env` into git. The repository includes a strict `.dockerignore` and `.gitignore` preventing secret leaks.

---

## 🗄️ Database Migrations

The database schema is managed via **Alembic**.

### Apply All Migrations

When running locally with active PostgreSQL:

```bash
alembic upgrade head
```

*(In Docker Compose, the `migration` container automatically runs `alembic upgrade head` before dependent services start).*

### Create a New Migration Revision

If you modify models in `app/modules/*/models.py`:

```bash
alembic revision --autogenerate -m "describe_schema_change"
alembic upgrade head
```

---

## 🚀 Running the Application

### Option A: Running via Docker Compose (Recommended for Production & Staging)

Docker Compose orchestrates the full multi-process stack with isolated networks and healthchecks.

#### 1. Build and Start All Containers

```bash
docker compose up -d --build
```

#### 2. Verify Container Status

```bash
docker compose ps
```

All 7 core services should report as healthy or running:
| Service | Container Name | Description | Host Port |
|---|---|---|---|
| `postgres` | `phishing_postgres` | PostgreSQL 16 relational database | Internal (5432) |
| `redis` | `phishing_redis` | Redis 7 queue broker & cache | Internal (6379) |
| `migration` | `phishing_migration` | Alembic migration runner (runs once & exits) | N/A |
| `api` | `phishing_api` | FastAPI web app & Admin dashboard | `8001:8000` |
| `celery-worker` | `phishing_celery_worker`| Celery worker (queues: `scanning`, `notifications`)| N/A |
| `celery-beat` | `phishing_celery_beat` | Celery scheduler daemon | N/A |
| `telethon-monitor`| `phishing_telethon_monitor`| MTProto account message listener | N/A |
| `bot` | `phishing_bot` | Telegram notification & alert bot | N/A |

#### 3. Inspect Live Logs

```bash
# Follow logs for all services
docker compose logs -f

# Follow logs for the API and Background Scanner specifically
docker compose logs -f api celery-worker
```

#### 4. Stop All Services

```bash
docker compose down
```

---

### Option B: Running Locally (Bare-Metal Development)

For local development and debugging without containerizing application processes:

#### 1. Setup Virtual Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 3. Start Infrastructure Only (PostgreSQL & Redis)

Start database and broker containers in the background:

```bash
docker compose up -d postgres redis
```

*(Ensure `.env` points `DATABASE_URL` and `REDIS_URL` to `localhost` rather than container hostnames when running bare-metal).*

#### 4. Run Database Migrations

```bash
alembic upgrade head
```

#### 5. Create an Administrator Account

Use the built-in management CLI script:

```bash
python -m scripts.create_admin --email admin@example.com --password YourAdminPassword123!
```

#### 6. Start the Application Processes

Open separate terminal windows or process managers for each component:

**Terminal 1 — FastAPI Application Server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Celery Worker:**
```bash
celery -A app.workers.celery_app worker -l info -c 4 -Q celery,scanning,notifications
```

**Terminal 3 — Telegram Notification Bot:**
```bash
python -m app.integrations.telegram_bot.bot
```

**Terminal 4 — Telethon MTProto Monitor:**
```bash
python -m app.integrations.telethon.monitor
```

---

## 🌐 Endpoints & Admin Dashboard

Once the API service is running, access the following interfaces:

* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs) (or `http://localhost:8001/docs` under Docker port mapping)
* **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Admin Web Dashboard:** [http://localhost:8000/admin/](http://localhost:8000/admin/)
  * Displays real-time scan statistics, live phishing risk feed, connected accounts, and delivery audit logs.
  * Click **"Admin Kirish"** (Admin Login) to authenticate using your administrator email and password or input a direct JWT Bearer token.
* **Liveness Probe:**
  ```bash
  curl http://localhost:8000/api/v1/health/liveness
  # Response: {"status":"ok"}
  ```
* **Readiness Probe (Verifies PostgreSQL & Redis):**
  ```bash
  curl http://localhost:8000/api/v1/health/readiness
  # Response: {"status":"ready","timestamp":"...","dependencies":{"database":"connected","redis":"connected"}}
  ```

---

## 🧪 Automated Testing Suite

The project includes unit, security, integration, and SSRF test suites verified with `pytest` and `pytest-asyncio`.

### 1. Run Complete Test Suite

```bash
pytest
```

Output should confirm all 65+ tests pass cleanly:
```text
============================== 65 passed in 1.60s ==============================
```

### 2. Run Tests with Code Coverage

```bash
pytest --cov=app --cov-report=term-missing
```

### 3. Run Specific Test Suites

```bash
# Run SSRF & Network Rebinding Security tests
pytest tests/security/test_ssrf.py -v

# Run Admin RBAC & Dashboard endpoint tests
pytest tests/unit/test_admin_api.py -v

# Run Authentication & JWT lifecycle tests
pytest tests/unit/test_auth_api.py -v

# Run Health Readiness & Rate Limiting tests
pytest tests/unit/test_health_and_rate_limit.py -v

# Run URL Normalization & Hash Pipeline tests
pytest tests/unit/test_pipeline.py -v

# Run Risk Engine & Threat Assessment tests
pytest tests/unit/test_risk_engine.py -v

# Run Telegram Bot & Notification Dispatch tests
pytest tests/unit/test_notifications.py tests/unit/test_notifications_api.py -v

# Run Telethon Account Authorization tests
pytest tests/unit/test_telegram_accounts.py tests/unit/test_telegram_api.py -v
```

---

## 🔍 Code Quality & Static Analysis

We enforce strict linting and type contracts via **Ruff**:

```bash
# Run linter across application, scripts, and tests
ruff check app tests scripts

# Auto-fix fixable formatting/import issues
ruff check app tests scripts --fix

# Verify code formatting
ruff format --check app tests scripts
```

---

## 🔒 Security Architecture Highlights

1. **Envelope Encryption for Telegram Sessions:**  
   Telegram MTProto sessions are never stored in plaintext. They are encrypted using `AES-256-GCM` with a 12-byte random nonce and authenticated with Associated Authenticated Data (AAD) derived from `user_id`, preventing cross-account ciphertext substitution.
2. **SSRF Guard:**  
   The scanner resolves hostnames and evaluates all resulting IP addresses before initiating an outbound connection. Requests targeting private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.0/8`), or link-local/cloud metadata (`169.254.169.254`) are blocked at the socket level.
3. **Bounded HTTP Fetching:**  
   External requests are strictly constrained by connect timeouts (5s), total execution limits (10s), max byte caps (2 MB), and redirection depth (max 5 hops) to guard against slowloris and resource exhaustion attacks.
4. **Defanged Output:**  
   Alert notifications defang URLs (e.g. `hxxps[://]badsite[.]com`) to prevent accidental clicks by end users or security analysts.

---

## 🛠️ Troubleshooting & FAQ

* **Issue: `429 Too Many Requests` on `/api/v1/auth/login` or `/telegram/auth/send-code`**  
  *Cause:* Built-in Redis sliding window rate limiter has been triggered.  
  *Solution:* Wait 60 seconds for the window to reset or clear testing keys in Redis via `redis-cli DEL rl_login:<ip>`.
* **Issue: `401 Unauthorized` accessing `/api/v1/admin/*`**  
  *Cause:* Admin endpoints require `Authorization: Bearer <token>` where the user's role is `ADMIN`.  
  *Solution:* Generate an admin user via `python -m scripts.create_admin ...`, log in via `/api/v1/auth/login`, and use the returned `access_token`.
* **Issue: `503 Service Unavailable` on `/api/v1/health/readiness`**  
  *Cause:* Either PostgreSQL or Redis failed health verification.  
  *Solution:* Check `docker compose ps` and logs for `postgres` and `redis`. Ensure credentials and network accessibility in `.env` are accurate.
* **Issue: Telegram `FloodWaitError` during verification**  
  *Cause:* Telegram MTProto enforces rate limits on phone authentication attempts.  
  *Solution:* Wait for the duration specified in the FloodWait exception before retrying. Do not spam auth requests.

---

## 📄 License & Security

This project is licensed under the terms of the private enterprise repository license.  
To report a security vulnerability or disclose a bug, please refer to our guidelines in [`SECURITY.md`](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/SECURITY.md).
