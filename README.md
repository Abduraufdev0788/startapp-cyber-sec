# Telegram Phishing & Scam Detection Platform

> **Production-grade, security-focused Telegram monitoring and phishing detection backend.**  
> Built with **FastAPI**, **Telethon**, **python-telegram-bot**, **PostgreSQL**, **Celery**, **Redis**, and **Google Gemini AI**.

---

## 🛡️ Overview

This platform connects to authorized Telegram accounts, ingests incoming messages in real-time across channels and groups, extracts links, runs rigorous **SSRF and DNS rebinding protections**, and analyzes threat signals using technical enrichment (DNS, WHOIS, SSL, login forms) combined with **Google Gemini structured AI evaluation**.

When high-risk phishing or scam threats are detected, the system immediately alerts users via the official Telegram Bot with explainable reasons and defanged links.

---

## 🚀 Key Features

* **Real-time Telegram Monitoring:** Ingests live incoming messages via Telethon without historical archive dumps.
* **AES-256-GCM Envelope Encryption:** Persistent Telethon sessions are protected with authenticated encryption and Associated Authenticated Data (AAD) bound to user IDs.
* **SSRF & DNS Rebinding Defenses:** Rejects all loopback, link-local, private (RFC 1918), and cloud metadata IP addresses (`169.254.169.254`).
* **Homograph & Punycode Normalization:** Resolves Cyrillic/Latin spoofing attacks and strips tracking query parameters (`utm_*`, `fbclid`).
* **Structured Gemini AI Output:** Evaluates social engineering and credential harvesting using strict Pydantic JSON contracts.
* **Deterministic Brand Protection:** Flags unauthorized pages impersonating major services (Telegram, banks, payment providers).
* **Defanged Notifications:** Telegram bot alerts deliver safe `hxxps://...[.]com` previews with actionable security advice.

---

## 🏗️ Architecture

The backend follows a **Modular Monolith** architecture:

```text
phishing-detector-backend/
├── app/
│   ├── api/v1/             # REST endpoints (Health, URL Scans, Auth)
│   ├── core/               # Security primitives (AES-256-GCM, Argon2id, JWT), Config, Logging
│   ├── db/                 # Async SQLAlchemy 2.x engine, Base models, Session management
│   ├── modules/
│   │   ├── users/          # User entities & authentication
│   │   ├── telegram_accounts/ # Encrypted Telethon session models
│   │   ├── telegram_chats/ # Chat & message metadata
│   │   ├── url_scanning/   # URL canonicalization pipeline & SSRF guards
│   │   ├── threat_intelligence/ # Safe HTTP fetcher, DNS, WHOIS enrichment
│   │   ├── risk_engine/    # Multi-factor risk calculation (0-100 score)
│   │   ├── notifications/  # Notification tracking & delivery
│   │   └── audit/          # Security audit trail
│   ├── integrations/
│   │   ├── gemini/         # Google GenAI SDK client adapter
│   │   ├── telethon/       # MTProto monitoring manager
│   │   └── telegram_bot/   # python-telegram-bot notification handler
│   └── workers/            # Celery background tasks
├── docs/                   # Complete engineering & security documentation
└── tests/                  # Unit, Integration, and Security test suites
```

---

## 📋 Prerequisites

* **Python:** 3.11+
* **Docker & Docker Compose**
* **Telegram API credentials:** `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
* **Google Gemini API Key:** from [Google AI Studio](https://aistudio.google.com/)

---

## ⚡ Quick Start

### 1. Clone & Configure Environment

```bash
git clone https://github.com/.../phishing-detector-backend.git
cd phishing-detector-backend

# Copy environment template
cp .env.example .env
```

Generate a secure 32-byte master encryption key:
```bash
openssl rand -hex 32
```
Add the output to `APP_MASTER_KEY` in `.env`.

### 2. Run with Docker Compose

```bash
docker compose up -d --build
```

Services started:
* `api`: http://localhost:8000 (Swagger docs at `/docs`)
* `postgres`: PostgreSQL 16
* `redis`: Redis 7
* `celery-worker`: Background scanner & enrichment
* `celery-beat`: Scheduled cleanup tasks
* `telethon-monitor`: Telegram account monitor daemon
* `bot`: Telegram notification bot

### 3. Local Development (Without Docker)

```bash
# Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Start local PostgreSQL and Redis containers only
docker compose up -d postgres redis

# Run FastAPI server
uvicorn app.main:app --reload --port 8000
```

---

## 🧪 Running Automated Tests

```bash
# Run all unit and security tests
pytest

# Run with test coverage
pytest --cov=app --cov-report=term-missing

# Run security tests only
pytest tests/security/
```

---

## 📚 Documentation

Comprehensive project documentation is available in the [`docs/`](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/README.md) directory:

* [Architecture Overview](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/01-architecture/01-system-overview.md)
* [Threat Model & Security](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/02-security/01-threat-model.md)
* [AES-256-GCM Encryption Standard](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/02-security/03-encryption.md)
* [Database ERD & Models](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/03-database/01-erd.md)
* [Foydalanuvchi Maʼlumotlari Qoʻllanmasi (User Input Guide)](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/USER_DATA_REQUIREMENTS.md)
* [Google Gemini Contract](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/05-detection-engine/03-gemini-contract.md)
* [Deployment Topology](file:///home/abdurauf/dasturlash/loyihalarim/startapp-cyber-sec/docs/08-operations/01-deployment.md)
