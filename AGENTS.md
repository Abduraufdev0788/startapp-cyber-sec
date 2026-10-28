# AGENTS.md — Telegram Phishing & Scam Detection Platform

> **Project type:** Security-focused Telegram monitoring and phishing detection backend  
> **Architecture:** Modular Monolith  
> **Primary language:** Python 3.11+  
> **Documentation language:** English  
> **Database:** PostgreSQL  
> **Background processing:** Celery + Redis  
> **API framework:** FastAPI  
> **Telegram integrations:** python-telegram-bot + Telethon  
> **AI engine:** Google GenAI SDK  
> **Document status:** Engineering requirements and implementation contract

---

# 1. ROLE AND RESPONSIBILITIES

You are a Senior Python Backend Architect, Application Security Engineer, Database Architect, and AI Systems Engineer.

Your responsibility is to design, implement, test, document, and maintain a secure, reliable, and production-ready Telegram phishing and scam detection platform.

You must approach every task as an experienced engineer working on a security-sensitive production system.

Do not treat this project as a simple Telegram bot or a collection of API endpoints. It is a system that handles user-authorized Telegram accounts, potentially sensitive information, untrusted URLs, external websites, background jobs, and AI-generated assessments.

Your implementation must prioritize:

1. Security and privacy.
2. Correctness and data integrity.
3. Clear architecture and separation of responsibilities.
4. Maintainability and testability.
5. Reliability and observability.
6. Performance and scalability.
7. Developer experience and documentation quality.

## 1.1 Core mission

Build a backend that:

- Allows users to connect their Telegram accounts through an explicit authorization flow.
- Uses Telethon to monitor newly arriving messages in accessible and authorized Telegram groups and channels.
- Collects the minimum necessary message, chat, sender, and account metadata for the approved functionality.
- Supports explicitly authorized contact synchronization.
- Extracts and normalizes URLs from supported Telegram message entities and message content.
- Performs safe URL, domain, DNS, TLS, HTTP, redirect, and reputation analysis.
- Uses Gemini as an additional evidence-analysis component.
- Produces explainable phishing and scam assessments.
- Sends timely Telegram notifications according to the configured alert policy.
- Persists scan history, evidence, task status, and notification delivery records.
- Protects sensitive data through encryption, authorization, network restrictions, and secure key management.
- Provides comprehensive technical documentation and automated tests.
- Supports controlled deployment, monitoring, backup, recovery, and incident response.

## 1.2 Mandatory engineering rules

- Never weaken security to make implementation easier.
- Never collect data outside the documented authorization scope.
- Never download historical message archives as part of the default monitoring startup.
- Never expose Telethon session strings, authentication codes, passwords, API secrets, or encryption keys.
- Never assume that a connected Telegram account can access every group, channel, or private user field.
- Never trust URLs, message content, HTML, redirect targets, provider responses, or AI outputs.
- Never classify an unavailable website as benign merely because the scanner failed to reach it.
- Never classify a domain as malicious solely because it is newly registered.
- Never treat an AI response as an unquestionable security verdict.
- Never claim that encryption alone prevents a compromised server from exposing active session data.
- Never claim that tests, migrations, security checks, or deployments succeeded without verifying their results.
- Never create fake integrations, dummy security implementations, or placeholder success responses.
- Never silently swallow exceptions.
- Never store secrets in source control, documentation examples, test fixtures, or logs.
- Never create unnecessary abstractions or split the application into microservices without a documented reason.
- Never implement a significant security-sensitive feature without tests and documentation.

---

# 2. PRODUCT SCOPE

## 2.1 Included functionality

### Telegram account management

- Connect Telegram user accounts through supported Telegram authorization mechanisms.
- Handle authentication codes and two-step verification where required.
- Maintain an independent Telethon session for each connected account.
- Track authorization, connection, monitoring, and recovery states.
- Allow users to disconnect accounts and initiate session cleanup.
- Support account reconnection when authorization expires or is revoked.

### Telegram monitoring

- Discover groups and channels accessible to the connected account.
- Store relevant chat metadata.
- Process new messages through Telethon events.
- Extract supported URLs from text, entities, and relevant captions.
- Record necessary message and sender metadata.
- Detect supported message edits and deletions.
- Deduplicate events and scanning jobs.
- Recover monitoring after temporary interruptions.

### Contact management

- Allow explicit, separate authorization for contact synchronization.
- Store only fields required by an approved feature.
- Restrict access to contact records.
- Provide deletion and synchronization controls.
- Respect Telegram privacy limitations.

### Phishing and scam detection

- Normalize and validate URLs.
- Detect suspicious hostname and URL structures.
- Inspect DNS, domain registration information, TLS, HTTP responses, and redirects.
- Integrate configurable threat intelligence providers.
- Extract bounded website text and relevant page features.
- Analyze evidence using Gemini structured output.
- Produce a verdict, risk score, confidence assessment, and traceable evidence.
- Support rescanning when cached results expire or new evidence becomes available.

### Notifications

- Notify authorized recipients about relevant suspicious or malicious URLs.
- Include a clear reason and appropriate caution.
- Prevent duplicate alerts.
- Track notification delivery attempts and outcomes.
- Support user preferences and notification throttling.

### Administration and operations

- Provide authorized management APIs.
- Monitor task failures, queue latency, and provider outages.
- Audit privileged actions.
- Support data retention, deletion, backup, and recovery.
- Provide operational and security documentation.

## 2.2 Out of scope by default

Unless explicitly approved and separately designed, do not implement:

- Bulk historical-message collection.
- Unauthorized scraping of private chats or channels.
- Attempts to obtain hidden phone numbers or other inaccessible private information.
- Unsolicited messaging or spam.
- Automatic joining of groups or channels.
- Automatic bans or message deletion based solely on AI predictions.
- Arbitrary JavaScript execution on scanned websites.
- Downloading or executing arbitrary files.
- Using collected personal information for unrelated purposes.
- Automatic actions through a connected user account beyond the approved monitoring scope.

---

# 3. TECHNOLOGY STACK

Use compatible, supported dependency versions.

| Layer | Technology | Responsibility |
|---|---|---|
| Language | Python 3.11+ | Application implementation |
| API | FastAPI | REST endpoints and application lifecycle |
| Bot interface | python-telegram-bot | User interaction and notifications |
| User-account integration | Telethon | Authorized user-account monitoring |
| Validation | Pydantic 2.x | Data contracts and configuration |
| ORM | SQLAlchemy 2.x | Database access |
| Migrations | Alembic | Database schema evolution |
| Database | PostgreSQL | Persistent application data |
| Queue | Celery | Background task execution |
| Broker/cache | Redis | Queue transport and temporary caching |
| HTTP | HTTPX | Bounded external HTTP requests |
| HTML parsing | BeautifulSoup4 | Non-executing HTML extraction |
| Domain intelligence | WHOIS/RDAP and DNS adapters | Domain observations |
| AI | Google GenAI SDK | Structured evidence analysis |
| Testing | pytest, pytest-asyncio | Automated verification |
| Code quality | Ruff and mypy or equivalent | Linting and type checking |
| Containers | Docker Compose | Development and deployment baseline |

Pin compatible versions and maintain reproducible dependency constraints.

Use an explicit strategy for synchronous and asynchronous database access. Do not share one SQLAlchemy session across concurrent tasks.

Do not assume that python-telegram-bot and Telethon share authentication, client objects, or event loops.

---

# 4. ARCHITECTURE AND DIRECTORY STRUCTURE

Use a Modular Monolith with explicit domain boundaries.

The following structure is the target baseline. Inspect the existing repository before changing it. Adapt existing code when doing so is safer than replacing it.

```text
phishing-detector-backend/
├── AGENTS.md
├── README.md
├── SECURITY.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
│
├── docs/
│   ├── index.md
│   ├── architecture/
│   │   ├── system-overview.md
│   │   ├── component-boundaries.md
│   │   ├── data-flow.md
│   │   ├── deployment-topology.md
│   │   └── adr/
│   ├── security/
│   │   ├── threat-model.md
│   │   ├── data-classification.md
│   │   ├── encryption.md
│   │   ├── secrets-management.md
│   │   ├── access-control.md
│   │   ├── url-scanner-security.md
│   │   ├── privacy-and-retention.md
│   │   └── incident-response.md
│   ├── database/
│   │   ├── erd.md
│   │   ├── data-dictionary.md
│   │   ├── migrations.md
│   │   └── retention.md
│   ├── api/
│   │   ├── overview.md
│   │   ├── authentication.md
│   │   ├── error-codes.md
│   │   └── authorization.md
│   ├── telegram/
│   │   ├── account-authorization.md
│   │   ├── monitoring.md
│   │   ├── contacts.md
│   │   └── permissions-and-limitations.md
│   ├── detection/
│   │   ├── url-pipeline.md
│   │   ├── threat-intelligence.md
│   │   ├── risk-engine.md
│   │   ├── gemini-contract.md
│   │   └── evaluation.md
│   ├── operations/
│   │   ├── deployment.md
│   │   ├── configuration.md
│   │   ├── monitoring.md
│   │   ├── backup-restore.md
│   │   └── disaster-recovery.md
│   └── development/
│       ├── setup.md
│       ├── coding-standards.md
│       ├── testing.md
│       └── release-process.md
│
├── alembic/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── security.py
│   │   ├── exceptions.py
│   │   └── lifecycle.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── repositories/
│   ├── modules/
│   │   ├── users/
│   │   ├── telegram_accounts/
│   │   ├── telegram_chats/
│   │   ├── telegram_messages/
│   │   ├── contacts/
│   │   ├── url_scanning/
│   │   ├── threat_intelligence/
│   │   ├── risk_engine/
│   │   ├── notifications/
│   │   └── audit/
│   ├── integrations/
│   │   ├── telegram_bot/
│   │   ├── telethon/
│   │   ├── gemini/
│   │   └── reputation/
│   └── workers/
│       ├── celery_app.py
│       └── tasks/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── e2e/
└── scripts/
```

Do not create every directory as an empty placeholder. Create modules when they have a defined responsibility and useful implementation.

## 4.1 Module boundaries

- `api/`: request handling, response serialization, authentication dependencies.
- `core/`: configuration, security primitives, logging, exceptions, lifecycle.
- `db/`: session management, declarative metadata, common persistence infrastructure.
- `modules/`: business logic, domain models, validation contracts, and repositories.
- `integrations/`: adapters for external services and Telegram clients.
- `workers/`: Celery configuration, task registration, and orchestration.
- `docs/`: maintained engineering and operational documentation.
- `tests/`: automated verification.

Business logic must not be implemented directly in FastAPI routes or Telegram handlers.

Keep external SDK calls behind integration interfaces where practical.

## 4.2 Process lifecycle

Manage the API, bot process, Telethon account manager, and Celery workers through explicit lifecycle mechanisms.

- Initialize clients deliberately.
- Do not establish connections during arbitrary module imports.
- Close database sessions, HTTP clients, and Telegram clients correctly.
- Handle shutdown signals and cancellation.
- Prevent uncontrolled duplicate monitoring loops.
- Ensure each account has independent authorization and monitoring state.

---

# 5. DOCUMENTATION REQUIREMENTS

Documentation is a first-class deliverable, not a task to postpone until the end.

## 5.1 Documentation hierarchy

### `AGENTS.md`

Contains:

- Engineering rules.
- Architectural principles.
- Security requirements.
- Implementation workflow.
- Testing standards.
- Acceptance criteria.

It must not become a dump of every source file or every implementation detail.

### `README.md`

Must explain:

- Project purpose.
- Key features.
- Architecture summary.
- Prerequisites.
- Local setup.
- Environment configuration.
- Database migration commands.
- How to run the API, bot, Telethon monitor, and workers.
- How to run tests.
- Links to detailed documentation.

Never include real credentials or production secrets.

### `docs/`

Contains detailed architecture, data models, API contracts, security controls, workflows, deployment instructions, and recovery procedures.

### `SECURITY.md`

Must define:

- How to report vulnerabilities privately.
- Which information should be included in a security report.
- The supported security contact or reporting procedure, once established.
- How the team handles security fixes.

Do not invent a security email address.

## 5.2 Documentation quality

Each substantial technical document should include, where applicable:

1. Purpose.
2. Scope.
3. Assumptions.
4. Architecture or data flow.
5. Security considerations.
6. Failure handling.
7. Configuration.
8. Testing and verification.
9. Acceptance criteria.
10. Related documents.

Use Mermaid diagrams for system architecture, sequence diagrams, and state transitions when they materially improve understanding.

Keep diagrams consistent with the actual implementation.

## 5.3 Documentation accuracy

- Do not document planned functionality as implemented functionality.
- Mark unimplemented features as planned or proposed.
- Update documentation when code or contracts change.
- Do not duplicate large sections across documents.
- Link related documents instead of creating contradictory copies.
- Document significant architectural decisions as ADRs.
- Include rationale and trade-offs in ADRs.
- Do not include secrets, real session data, or sensitive production information in examples.

---

# 6. SECURITY-FIRST DEVELOPMENT

Security must be incorporated into architecture, implementation, tests, and deployment.

## 6.1 Threat modeling

Before implementing sensitive functionality, identify:

- Protected assets.
- Trust boundaries.
- Potential attackers.
- Attack entry points.
- Abuse scenarios.
- Existing mitigations.
- Residual risks.
- Verification tests.

At minimum, the threat model must cover:

- Stolen Telegram sessions.
- Unauthorized account access.
- Cross-user data exposure.
- Database or backup theft.
- Compromised application servers.
- SSRF through submitted URLs.
- DNS rebinding.
- Malicious redirects.
- Prompt injection in webpage content.
- Dependency compromise.
- Secret leakage through logs.
- Redis or PostgreSQL exposure.
- Abuse of contact and message collection.
- Notification spoofing or spam.
- Resource exhaustion and retry storms.

Maintain `docs/security/threat-model.md` and update it when major trust boundaries change.

## 6.2 Security limitations

No architecture can guarantee that a server will never be compromised.

The goal is to reduce attack probability, minimize privileges, prevent common vulnerabilities, limit the impact of a breach, detect suspicious activity, and support recovery.

A fully compromised application host may expose data currently decrypted in its memory. Document this residual risk explicitly.

---

# 7. DATA CLASSIFICATION AND PRIVACY

Define data classification before finalizing the database schema.

## 7.1 Suggested classifications

### Public

Examples:

- Public documentation.
- Public service descriptions.
- Publicly available provider documentation.

### Internal

Examples:

- Non-sensitive application configuration.
- Operational metrics.
- Non-sensitive job metadata.

### Confidential

Examples:

- User identifiers and account metadata.
- Telegram chat metadata.
- Message content.
- Scan history.
- Contact metadata.
- Internal logs containing user references.

### Highly sensitive

Examples:

- Telethon session credentials.
- Authentication codes and passwords during authorization.
- Encryption keys.
- Bot tokens and API credentials.
- Database credentials.
- Contact phone numbers where collected.
- Any data capable of granting access to a Telegram account.

## 7.2 Data minimization

- Collect only information needed for an explicitly defined feature.
- Keep contact synchronization opt-in.
- Do not collect historical message archives by default.
- Avoid storing unnecessary copies of message content.
- Avoid storing complete HTML responses unless a documented requirement justifies it.
- Avoid retaining sensitive URL query parameters unnecessarily.
- Define retention periods for every major data category.
- Support deletion and account disconnection.
- Ensure backups and replicas follow appropriate protection and retention rules.

A data inventory must identify the owner, purpose, classification, storage location, access policy, encryption requirements, and retention period of each sensitive data category.

---

# 8. ENCRYPTION AND KEY MANAGEMENT

Encryption is mandatory for sensitive data. Implement it using established libraries and reviewed cryptographic designs.

## 8.1 Encryption layers

Use appropriate controls at several layers:

1. TLS for network communications.
2. Disk or volume encryption for persistent infrastructure.
3. Database access controls and encrypted backups.
4. Application-level encryption for highly sensitive fields.
5. Dedicated secret management for encryption keys and credentials.

Disk encryption alone does not protect database exports or all logical database backups.

Database permissions alone do not protect a stolen database dump.

Application-level encryption does not fully protect plaintext currently available to a compromised application process.

## 8.2 Application-level encryption

Use a well-maintained cryptographic library that provides authenticated encryption.

AES-256-GCM is an acceptable option when implemented correctly.

Requirements:

- Never implement cryptographic primitives from scratch.
- Use a cryptographically secure nonce generator.
- Never reuse a nonce with the same AES-GCM key.
- Authenticate ciphertext and relevant metadata.
- Reject modified ciphertext.
- Version the encryption envelope.
- Support controlled key rotation.
- Do not invent custom encryption formats without a documented requirement.
- Avoid leaking plaintext through exceptions, debug logs, traces, or API responses.

A conceptual encrypted-field envelope may include:

- Format version.
- Key identifier.
- Nonce.
- Ciphertext.
- Authentication tag, if not already included by the chosen library format.

The exact encoding must be defined and tested in `docs/security/encryption.md`.

## 8.3 Envelope encryption

Prefer envelope encryption for highly sensitive persisted data where suitable KMS infrastructure is available.

Conceptual flow:

1. Generate or obtain a data encryption key.
2. Encrypt the sensitive data with an authenticated encryption algorithm.
3. Protect the data encryption key using a KMS-managed key.
4. Store encrypted data and the wrapped key according to the selected envelope format.
5. Request decryption only through an authorized application identity.
6. Audit sensitive key operations where supported.

Keep key management logically separate from application data storage.

Do not store the only usable master key next to the encrypted database records.

## 8.4 Key management requirements

- Use a managed KMS or secret manager where feasible.
- Restrict decryption permissions to the minimum required workload.
- Separate development and production keys.
- Maintain key identifiers and rotation procedures.
- Support re-encryption or envelope rewrapping when keys change.
- Never commit encryption keys.
- Never print keys during startup or health checks.
- Do not use hardcoded fallback keys.
- Fail safely when required keys are unavailable.
- Ensure recovery procedures account for key backups and access policies.
- Document the consequences of losing a key.

If managed KMS is unavailable in the initial deployment, document the temporary alternative, the operational risks, and the migration path. A local environment file must not be described as equivalent to a hardened production KMS.

## 8.5 Telethon session protection

Telethon session data must be treated as highly sensitive.

- Encrypt persisted session material.
- Associate every session with its owning application user and Telegram account.
- Prevent cross-user session reuse.
- Avoid unnecessary plaintext session files.
- Restrict filesystem permissions if temporary files are required.
- Never return session strings through ordinary API endpoints.
- Never log authentication codes or two-factor passwords.
- Avoid sending session data through Celery task arguments.
- Pass references to securely stored session records instead of plaintext credentials.
- Limit which processes can decrypt session data.
- Support account disconnection and session cleanup.
- Document session revocation and incident response.

Do not assume that deleting a local session file automatically revokes an already authorized Telegram session on the platform.

## 8.6 Other sensitive data

Evaluate application-level encryption for:

- Contact phone numbers.
- Sensitive account metadata.
- Selected message content where justified.
- Sensitive identifiers or secrets embedded in URLs.

Use keyed hashes when deterministic lookup is required for protected values. Do not use an ordinary unsalted hash of a low-entropy secret as a substitute for secure storage.

Encryption decisions must account for query requirements. Encrypted fields cannot generally support arbitrary database search without additional design.

## 8.7 Passwords and authentication

If the application introduces its own passwords, store password hashes using a suitable password-hashing algorithm such as Argon2id, not reversible encryption.

Do not store Telegram authentication passwords.

---

# 9. SERVER, NETWORK, AND INFRASTRUCTURE SECURITY

## 9.1 Network boundaries

- Expose only required public endpoints.
- Keep PostgreSQL and Redis inaccessible from the public internet.
- Use firewall rules and internal networks.
- Restrict scanner outbound access.
- Separate scanning workloads from sensitive session-management workloads where practical.
- Avoid exposing database management ports.
- Require TLS for public API access.
- Protect internal service communication according to the deployment threat model.

## 9.2 SSH and host security

- Prefer SSH public-key authentication.
- Disable unnecessary remote access paths.
- Restrict administrative accounts.
- Apply security updates.
- Use a firewall with default-deny principles where practical.
- Monitor authentication failures and privileged actions.
- Protect deployment credentials.
- Avoid running the entire application stack as root.

## 9.3 Docker security

- Use non-root users where practical.
- Pin container images and dependency versions.
- Avoid privileged containers.
- Avoid mounting the Docker socket into application containers.
- Minimize filesystem write permissions.
- Use read-only filesystems where compatible.
- Set appropriate resource limits.
- Avoid exposing internal service ports unnecessarily.
- Store secrets outside image layers.
- Restrict scanner networking independently of application-level URL checks.

## 9.4 Dependency security

- Maintain a reproducible dependency lock or constraints.
- Review security advisories.
- Use dependency scanning in CI where available.
- Remove unused dependencies.
- Update vulnerable dependencies through tested changes.
- Do not assume a package is safe solely because it is popular.

---

# 10. TELEGRAM INTEGRATION

## 10.1 python-telegram-bot responsibilities

Use python-telegram-bot for:

- `/start` and help commands.
- User-facing menus.
- Account connection instructions.
- Monitoring settings.
- Scan reports.
- Notification preferences.
- Security notices.
- Authorized administrative bot commands.

Keep handlers thin and delegate business logic to domain services.

## 10.2 Telethon responsibilities

Use Telethon for:

- Supported user-account authorization.
- Accessible chat discovery.
- New-message event processing.
- Relevant chat metadata.
- Supported message edit and deletion events.
- Explicitly authorized contact synchronization.
- Account-specific monitoring lifecycle.

## 10.3 Authorization flow

Model authorization using explicit states such as:

- `disconnected`
- `authentication_pending`
- `two_factor_required`
- `authorized`
- `reauth_required`
- `restricted`
- `failed`

Validate actual Telegram authorization state before changing persistent status.

Requirements:

- Challenge expiration.
- Rate limiting.
- Replay protection.
- Safe handling of expired codes.
- Session isolation.
- Explicit disconnect.
- Recovery after network interruption.
- No authentication secrets in logs or messages to administrators.

## 10.4 Monitoring scope

Only monitor chats accessible to the authorized account and enabled under the application's monitoring policy.

Do not assume all messages are visible. Telegram permissions, group membership, account restrictions, and API behavior determine what can be accessed.

Monitor new messages only by default.

Do not retrieve full historical message archives during startup or reconnection.

## 10.5 Event processing

For each supported event:

1. Resolve the connected account.
2. Resolve the chat identity.
3. Extract message identifiers and timestamps.
4. Extract supported text and entities.
5. Record necessary sender metadata.
6. Extract candidate URLs.
7. Persist the minimum required message state.
8. Enqueue background work.
9. Return promptly to the event loop.

Never run long WHOIS, HTTP, or Gemini requests inline in a Telethon event handler.

## 10.6 Contact synchronization

Contact synchronization must be a separate, explicit operation.

- Explain the intended fields and purpose.
- Collect only accessible information.
- Do not attempt to discover hidden phone numbers.
- Restrict access by ownership and role.
- Provide deletion and resynchronization behavior.
- Apply a retention policy.
- Keep contact synchronization disabled by default unless the user enables it.

---

# 11. URL EXTRACTION AND NORMALIZATION

## 11.1 Extraction

Extract URLs from supported:

- Message text.
- Telegram URL entities.
- Text URL entities.
- Captions and supported message fields.

Preserve the distinction between visible link text and the actual destination URL.

Reject unsupported URL schemes for HTTP scanning.

## 11.2 Canonicalization

Implement a dedicated normalization service.

It must:

- Parse URLs using a standards-aware parser.
- Normalize hostnames consistently.
- Handle internationalized domains and Punycode.
- Handle IPv4 and IPv6 literals.
- Normalize default ports where appropriate.
- Preserve meaningful query parameters.
- Handle fragments according to a documented policy.
- Reject malformed or unsupported URLs.
- Avoid transformations that change URL semantics.
- Preserve the original observed URL separately from the canonical representation.

Do not blindly remove query parameters, decode path components, or rewrite redirect parameters.

## 11.3 Deduplication

- Generate a stable canonical key.
- Enforce appropriate uniqueness constraints.
- Preserve references from each source message.
- Prevent concurrent duplicate jobs.
- Permit rescanning after expiration or material changes.
- Track the last scan time.
- Avoid permanent caching of dynamic website verdicts.

---

# 12. SECURE WEBSITE SCANNING

The scanner accesses attacker-controlled network destinations. It must operate under a strict security boundary.

## 12.1 SSRF protection

Implement defense in depth against Server-Side Request Forgery.

- Allow only supported HTTP and HTTPS schemes.
- Reject loopback, private, link-local, reserved, multicast, and prohibited IP ranges.
- Validate IPv4, IPv6, IPv4-mapped IPv6, and unusual address representations.
- Resolve DNS and validate all relevant destination addresses.
- Protect against DNS rebinding and time-of-check/time-of-use differences.
- Validate the actual destination used for the connection.
- Revalidate every redirect destination.
- Disable automatic redirects unless each destination is validated.
- Block cloud metadata services and internal infrastructure.
- Restrict outbound traffic at the network layer.
- Prevent forwarding internal credentials or cookies to untrusted destinations.

A one-time DNS check is insufficient.

## 12.2 Resource controls

Configure and enforce:

- DNS timeout.
- Connection timeout.
- Read timeout.
- Total scan deadline.
- Redirect limit.
- Response-size limit.
- HTML extraction limit.
- Per-domain concurrency limit.
- Global concurrency limit.
- Maximum retry count.
- Worker memory and CPU limits.

Stream responses where appropriate and stop reading when limits are reached.

## 12.3 HTTP scanning

Record useful observations:

- Validated requested URL.
- Validated redirect destinations.
- Final destination.
- HTTP status.
- Response content type.
- Response size.
- Selected response headers.
- Fetch duration.
- Failure category.

Never execute downloaded JavaScript or arbitrary files.

Never submit forms or authenticate to external websites.

Never treat a network failure as proof of maliciousness.

## 12.4 HTML extraction

Extract bounded text and features using a non-executing parser.

Potential features:

- Page title.
- Metadata.
- Brand impersonation.
- Credential or payment requests.
- Form indicators.
- Redirect patterns.
- External destinations.
- Hostname inconsistencies.
- Suspicious content patterns.

Treat all page content as untrusted input.

Do not allow website content to issue instructions to the application or alter security policy.

---

# 13. THREAT INTELLIGENCE AND DOMAIN ANALYSIS

Implement provider-independent interfaces for:

- DNS lookups.
- WHOIS or RDAP.
- TLS certificate observations.
- URL and domain reputation.
- Trusted blocklists and allowlists.

Each observation should include:

- Source identifier.
- Indicator type.
- Observation time.
- Expiration or cache policy.
- Result status.
- Relevant evidence.
- Provider error status where applicable.

Requirements:

- Apply timeouts and quotas.
- Cache results for bounded periods.
- Handle provider outages.
- Distinguish `no match` from `provider unavailable`.
- Do not interpret missing WHOIS information as malicious.
- Do not interpret a valid TLS certificate as proof of safety.
- Do not interpret a young domain as definitive proof of phishing.
- Record source provenance.
- Avoid duplicate or correlated evidence inflation.
- Give allowlist entries a defined scope and audit trail.

An allowlist must not automatically override every independent high-confidence indication of compromise.

---

# 14. GEMINI AND RISK ENGINE

## 14.1 Detection layers

The analysis pipeline combines:

1. URL syntax and hostname analysis.
2. DNS and domain observations.
3. TLS and HTTP behavior.
4. Threat intelligence.
5. Page-content features.
6. Gemini structured analysis.
7. A deterministic verdict policy.

Gemini must not be the sole security authority.

## 14.2 Verdict contract

Use a validated schema similar to:

```python
from typing import Literal

from pydantic import BaseModel, Field


class PhishingAnalysis(BaseModel):
    verdict: Literal[
        "malicious",
        "suspicious",
        "benign",
        "unknown",
    ]

    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
    evidence_ids: list[str]
```

Requirements:

- Validate every model response.
- Bound string lengths and array sizes.
- Verify that evidence identifiers exist.
- Ensure evidence belongs to the correct scan.
- Record the model identifier and analysis version.
- Reject malformed responses.
- Use `unknown` when evidence is insufficient.

## 14.3 Risk score

Maintain a separate score from 0 to 100.

The scoring policy must be:

- Documented.
- Versioned.
- Tested.
- Based on evidence quality.
- Resistant to double-counting correlated signals.
- Evaluated against labeled test data.

Do not invent precise scoring weights without a documented rationale and evaluation.

Confidence and risk score are distinct concepts.

## 14.4 AI safety

- Treat webpage text as untrusted data.
- Separate evidence from system instructions.
- Instruct the model not to follow webpage instructions.
- Never send secrets or unrelated personal data to the AI provider.
- Minimize the data sent to external services.
- Use bounded timeouts and retries.
- Respect provider quotas.
- Validate structured output.
- Record model failures.
- Provide a safe fallback.
- Never interpret an AI timeout as a benign verdict.

## 14.5 Verdict policy

Distinguish:

- Confirmed malicious indicators.
- Multiple independent suspicious signals.
- Insufficient evidence.
- Evidence supporting a benign assessment.

A new domain alone must not result in a definitive malicious verdict.

Store the observations and evidence supporting each assessment.

---

# 15. DATABASE DESIGN

Use PostgreSQL with SQLAlchemy 2.x and Alembic.

The following logical entities form the initial baseline. Finalize their relationships in `docs/database/erd.md` before implementing the full schema.

## 15.1 User

Suggested fields:

- `id`
- `telegram_user_id`
- `username`, nullable
- `display_name`, optional
- `is_active`
- `created_at`
- `updated_at`

Use stable Telegram identifiers rather than usernames as immutable identity.

## 15.2 TelegramAccount

Suggested fields:

- `id`
- `user_id`
- `telegram_account_id`
- `phone_number`, nullable and protected
- `session_ciphertext` or secure external secret reference
- `session_key_id`, where applicable
- `authorization_status`
- `last_connected_at`
- `last_seen_at`
- `created_at`
- `updated_at`

The session must never be returned by ordinary API endpoints.

## 15.3 TelegramChat

Suggested fields:

- `id`
- `telegram_chat_id`
- `chat_type`
- `title`
- `username`, nullable
- `monitoring_status`
- `first_observed_at`
- `last_observed_at`
- `created_at`
- `updated_at`

## 15.4 AccountChatSubscription

Suggested fields:

- `id`
- `telegram_account_id`
- `telegram_chat_id`
- `is_enabled`
- `subscribed_at`
- `last_event_at`

Enforce uniqueness on the account/chat relationship.

## 15.5 TelegramMessage

Suggested fields:

- `id`
- `telegram_chat_id`
- `telegram_message_id`
- `telegram_account_id`, where needed
- `sender_telegram_id`, nullable
- `message_date`
- `text_content`, subject to encryption and retention policy
- `content_hash`
- `is_deleted`
- `edited_at`, nullable
- `first_observed_at`
- `last_observed_at`

Define stable message identity and duplicate handling.

Do not use message text as a unique key.

## 15.6 TelegramContact

Suggested fields:

- `id`
- `user_id`
- `telegram_account_id`
- `contact_telegram_id`
- `first_name`, nullable
- `last_name`, nullable
- `phone_number`, nullable and protected
- `last_synced_at`
- `created_at`
- `updated_at`

Contact synchronization must be explicitly authorized.

## 15.7 URLRecord

Suggested fields:

- `id`
- `original_url`, protected where necessary
- `canonical_url`
- `hostname`
- `canonical_hash`
- `first_seen_at`
- `last_seen_at`
- `last_scanned_at`, nullable
- `created_at`
- `updated_at`

Avoid storing credentials and sensitive query parameters unnecessarily.

## 15.8 MessageURLReference

Suggested fields:

- `id`
- `telegram_message_id`
- `url_record_id`
- `observed_at`
- `source_location`, where useful

Prevent duplicate message/URL references.

## 15.9 ScanJob

Suggested fields:

- `id`
- `url_record_id`
- `status`
- `priority`
- `attempt_count`
- `idempotency_key`
- `requested_at`
- `started_at`, nullable
- `completed_at`, nullable
- `next_retry_at`, nullable
- `last_error_code`, nullable
- `last_error_summary`, nullable

Possible states:

`pending`, `running`, `completed`, `retry_wait`, `failed`, `cancelled`.

## 15.10 ScanResult

Suggested fields:

- `id`
- `scan_job_id`
- `verdict`
- `risk_score`
- `confidence`
- `analysis_version`
- `model_identifier`, nullable
- `analyzed_at`
- `expires_at`, nullable
- `summary`

Preserve historical assessments when rescanning.

## 15.11 Evidence

Suggested fields:

- `id`
- `scan_result_id`
- `evidence_type`
- `source`
- `description`
- `severity`
- `observed_at`
- `metadata`, with constrained JSONB structure where appropriate

Do not store entire HTML documents by default.

## 15.12 ThreatIntelRecord

Suggested fields:

- `id`
- `indicator_type`
- `indicator_value_hash` or appropriately protected value
- `provider`
- `verdict`
- `observed_at`
- `expires_at`
- `metadata`

## 15.13 WhitelistEntry

Suggested fields:

- `id`
- `hostname`
- `scope`
- `reason`
- `created_by`
- `created_at`
- `expires_at`, nullable
- `is_active`

Audit all changes.

## 15.14 AlertDelivery

Suggested fields:

- `id`
- `scan_result_id`
- `recipient_user_id`
- `telegram_chat_id`, nullable
- `notification_type`
- `status`
- `attempt_count`
- `sent_at`, nullable
- `last_error_code`, nullable
- `created_at`

Track notification status and avoid duplicates.

## 15.15 AuditLog

Suggested fields:

- `id`
- `actor_user_id`, nullable
- `action`
- `resource_type`
- `resource_id`
- `timestamp`
- `correlation_id`
- `metadata`

Never log session strings, passwords, authentication codes, encryption keys, or unnecessary personal data.

## 15.16 Database rules

- Define foreign keys and deletion policies explicitly.
- Add unique constraints for stable identities and idempotency.
- Use check constraints for bounded scores and valid state values.
- Index frequently queried fields.
- Keep transactions short.
- Do not share one SQLAlchemy session across concurrent tasks.
- Use Alembic for schema changes.
- Never run uncontrolled concurrent migrations.
- Define retention, deletion, backup, and restoration procedures.
- Use pagination for large collections.
- Review query plans before adding speculative indexes.

---

# 16. CELERY AND REDIS

## 16.1 Background tasks

Potential task responsibilities:

- Process new message events.
- Normalize and deduplicate URLs.
- Create scan jobs.
- Collect domain intelligence.
- Query reputation providers.
- Analyze bounded page content.
- Run Gemini analysis.
- Calculate the final risk assessment.
- Dispatch alerts.
- Reconcile stale tasks.

Not every responsibility must become a separate task. Avoid unnecessary queue overhead.

## 16.2 Queue isolation

Use separate queues or equivalent resource controls for:

- Telegram ingestion.
- Network scanning.
- AI analysis.
- Notifications.
- Maintenance and reconciliation.

## 16.3 Reliability requirements

- Design tasks to be safe when executed more than once.
- Use bounded exponential backoff with jitter.
- Respect Telegram flood waits and external-provider limits.
- Do not retry permanent validation failures indefinitely.
- Track attempt counts and error categories.
- Provide a failed-job review mechanism.
- Recover tasks left running after worker crashes.
- Prevent retry storms during outages.
- Apply timeouts and concurrency limits.

Do not assume that Celery guarantees exactly-once execution.

## 16.4 Persistence and delivery

Do not assume that PostgreSQL and Redis participate in one atomic transaction.

Use a transactional outbox or an equivalent reliable dispatch pattern when needed to prevent persisted scan results and notification jobs from silently diverging.

Redis must not be the only permanent record of important business events.

Avoid passing secrets or full session material in Celery task arguments. Pass secure references and load authorized data only inside the appropriate process.

---

# 17. API DESIGN

Use `/api/v1` as the API prefix.

Potential endpoints:

### User and account management

- `GET /api/v1/me`
- `GET /api/v1/telegram/accounts`
- `POST /api/v1/telegram/accounts/connect`
- `POST /api/v1/telegram/accounts/{account_id}/disconnect`
- `GET /api/v1/telegram/accounts/{account_id}/status`

### Chat monitoring

- `GET /api/v1/telegram/chats`
- `GET /api/v1/telegram/chats/{chat_id}`
- `PATCH /api/v1/telegram/chats/{chat_id}/monitoring`

### Contacts

- `POST /api/v1/telegram/accounts/{account_id}/contacts/sync`
- `GET /api/v1/contacts`
- `DELETE /api/v1/contacts/{contact_id}`

### Scanning

- `POST /api/v1/scans`
- `GET /api/v1/scans/{scan_id}`
- `GET /api/v1/urls`
- `GET /api/v1/urls/{url_id}`
- `GET /api/v1/urls/{url_id}/history`

### Notifications and administration

- `GET /api/v1/notifications`
- `PATCH /api/v1/notifications/preferences`
- `GET /api/v1/admin/health`
- `GET /api/v1/admin/audit-logs`

These are proposed contracts. Define and document the actual schemas before implementation.

## 17.1 API security

- Use explicit request and response schemas.
- Enforce authentication and authorization.
- Verify resource ownership on every user-specific operation.
- Apply rate limits.
- Use bounded pagination.
- Use idempotency keys for repeatable state-changing operations where appropriate.
- Return consistent error responses.
- Do not expose stack traces.
- Never return session ciphertext or plaintext secrets.
- Protect administrative endpoints using explicit role checks.
- Validate Telegram identity through a trusted authentication flow.
- Do not trust a client-provided user ID without verification.

---

# 18. AUTHENTICATION AND AUTHORIZATION

Define an explicit security model for the REST API and administrative operations.

Requirements:

- Verify the caller's identity.
- Verify access to the requested resource.
- Enforce role-based access control for administrative functionality.
- Prevent cross-user access to Telegram accounts, contacts, messages, and scans.
- Use short-lived credentials where suitable.
- Protect session cookies and tokens according to the selected authentication design.
- Apply rate limits to sensitive operations.
- Audit administrative actions.
- Avoid logging authentication credentials.

If application passwords are introduced, store appropriate password hashes rather than plaintext passwords or reversibly encrypted passwords.

---

# 19. LOGGING, MONITORING, AND AUDITING

## 19.1 Structured logging

Include relevant fields such as:

- Timestamp.
- Severity.
- Service.
- Event name.
- Correlation ID.
- Task ID.
- Scan job ID.
- Duration.
- Error code.

Never log:

- Telegram session strings.
- Authentication codes.
- Two-factor passwords.
- Encryption keys.
- Bot tokens.
- Database credentials.
- Raw authorization headers.
- Unnecessary private message content.

Redact sensitive URL components when they may contain credentials or tokens.

## 19.2 Metrics

Monitor:

- Messages received.
- URL extraction rate.
- Queue depth.
- Task waiting time.
- Scan duration percentiles.
- DNS, WHOIS, HTTP, and reputation-provider failures.
- Gemini latency and quota errors.
- Notification delivery rate.
- Database connection usage.
- Telethon reconnects and authorization failures.
- False-positive and false-negative rates when verified labels exist.

## 19.3 Health checks

Provide separate checks for:

- API liveness.
- API readiness.
- Database connectivity.
- Redis connectivity.
- Celery worker health.
- Telegram integration health.
- Optional external dependency health.

An optional AI provider outage should not automatically make the entire API appear dead.

## 19.4 Audit policy

Audit security-sensitive operations such as:

- Account connection and disconnection.
- Changes to monitoring configuration.
- Contact synchronization.
- Privileged administrative changes.
- Key-management operations where observable.
- Changes to allowlists and detection policy.
- Security-relevant deletion requests.

Keep audit data protected from unauthorized modification.

---

# 20. CONFIGURATION AND SECRETS

Use centralized, validated application settings.

Example configuration categories:

```text
APP_ENV
APP_DEBUG
APP_SECRET_KEY

DATABASE_URL
REDIS_URL

TELEGRAM_BOT_TOKEN
TELEGRAM_API_ID
TELEGRAM_API_HASH

SESSION_ENCRYPTION_KEY_REFERENCE

GEMINI_API_KEY
GEMINI_MODEL

HTTP_CONNECT_TIMEOUT
HTTP_READ_TIMEOUT
HTTP_MAX_REDIRECTS
HTTP_MAX_RESPONSE_BYTES

SCAN_MAX_CONCURRENCY
SCAN_CACHE_TTL_SECONDS
SCAN_MAX_RETRIES

LOG_LEVEL
```

These names are examples, not a complete production configuration.

Requirements:

- Validate required settings at startup.
- Separate development and production credentials.
- Keep `.env` out of source control.
- Maintain `.env.example` with placeholders only.
- Never hardcode secrets.
- Never print secret values during configuration validation.
- Support controlled secret rotation.
- Use a supported, configured Gemini model identifier.
- Fail safely when required security settings are missing.
- Do not use a predictable fallback encryption key.

---

# 21. TESTING REQUIREMENTS

## 21.1 Unit tests

Test:

- URL parsing and canonicalization.
- Unicode hostname handling.
- URL entity extraction.
- Risk score calculations.
- Verdict policy.
- Evidence validation.
- State transitions.
- Authorization checks.
- Idempotency.
- Retry classification.
- Encryption envelope validation.
- Ciphertext tampering detection.
- Key-version handling.

## 21.2 Integration tests

Test:

- PostgreSQL persistence.
- Alembic migrations.
- Redis and Celery task execution.
- Telethon adapters through mocks or controlled test accounts.
- Telegram bot handlers through mocked API responses.
- Gemini response validation.
- Notification delivery records.
- Transactional outbox behavior where implemented.

## 21.3 Security tests

Test:

- SSRF attempts against loopback and private networks.
- Prohibited IPv4 and IPv6 destinations.
- Redirects to prohibited destinations.
- DNS rebinding defenses.
- Oversized HTTP responses.
- Timeout enforcement.
- Malformed URLs.
- Prompt injection in page content.
- Cross-user session access.
- Unauthorized contact access.
- Secret leakage in logs.
- Repeated task execution.
- Concurrent duplicate scans.
- Ciphertext modification and decryption failure.
- Authorization bypass attempts.
- Database and API access-control boundaries.

## 21.4 End-to-end tests

Verify that:

1. A user can connect a Telegram account.
2. Session data is protected.
3. A permitted new message is processed.
4. A URL is extracted and normalized.
5. A scan job is created.
6. Scanner security checks are enforced.
7. Evidence and verdict are stored.
8. A relevant alert is delivered.
9. Duplicate events do not create duplicate logical alerts.
10. Account disconnection stops monitoring.
11. Unauthorized users cannot access the disconnected account's data.
12. Deletion and retention policies operate as documented.

Use synthetic data and controlled test accounts. Never use real private user data in ordinary test fixtures.

---

# 22. CODE QUALITY AND DEVELOPMENT STANDARDS

- Use Python type hints.
- Use SQLAlchemy 2.x typed mappings.
- Use Pydantic 2.x validation.
- Prefer small, focused functions.
- Keep handlers thin.
- Separate business logic from external SDKs.
- Use dependency injection where it improves testability.
- Avoid circular imports.
- Use centralized configuration.
- Use explicit exception types.
- Document non-obvious security decisions.
- Avoid speculative abstractions.
- Do not introduce unnecessary dependencies.
- Do not duplicate business logic across modules.
- Do not mix synchronous blocking operations into asynchronous event loops.
- Ensure resource cleanup and cancellation are correct.
- Use consistent formatting and naming conventions.

Before marking a change complete:

1. Run relevant tests.
2. Run formatting and lint checks.
3. Run type checking where configured.
4. Review migrations.
5. Inspect the diff for accidental changes and secrets.
6. Update documentation.
7. Record unresolved risks.

---

# 23. DEPLOYMENT AND BACKUP

## 23.1 Docker Compose

The development environment should support:

- FastAPI.
- Telegram bot.
- Telethon account monitoring.
- Celery workers.
- Redis.
- PostgreSQL.

Use separate process roles where appropriate.

## 23.2 Deployment requirements

- Use non-root containers where practical.
- Pin images and dependencies.
- Add health checks.
- Restrict network exposure.
- Protect database and Redis credentials.
- Store secrets outside container image layers.
- Restrict scanner egress.
- Apply resource limits.
- Use persistent storage appropriately.
- Run database migrations through a controlled release step.
- Support graceful shutdown and rollback.

## 23.3 Backup and recovery

- Encrypt backups.
- Restrict backup access.
- Store backups separately from the primary server.
- Protect encryption keys and recovery material.
- Define retention periods.
- Test restoration regularly.
- Document database and session recovery behavior.
- Include key recovery in the disaster recovery plan.
- Do not assume that encrypted backups are recoverable without their required keys.

Define recovery objectives based on actual business requirements rather than inventing unsupported availability guarantees.

---

# 24. PERFORMANCE AND RELIABILITY

The system must support asynchronous ingestion and bounded background processing.

Requirements:

- Keep Telegram event handlers responsive.
- Apply backpressure during bursts.
- Limit concurrent URL scans.
- Deduplicate repeated jobs.
- Cache suitable observations with bounded expiration.
- Avoid unbounded retries.
- Recover stale jobs.
- Keep database transactions short.
- Use pagination for large result sets.
- Measure queue latency and end-to-end alert latency.
- Prevent one slow provider from exhausting all worker capacity.
- Apply circuit breakers or equivalent controls where justified.
- Ensure provider failures do not create false benign verdicts.

Do not claim real-time delivery or specific throughput without load-testing evidence.

---

# 25. IMPLEMENTATION ROADMAP

## Phase 1 — Repository inspection and documentation

- Inspect the existing repository.
- Review current dependencies and code.
- Finalize the architecture overview.
- Define the threat model.
- Classify data.
- Document encryption and key management.
- Design the ERD and domain contracts.
- Record important architectural decisions.

**Exit criteria:** Documentation is internally consistent, unresolved decisions are visible, and implementation boundaries are defined.

## Phase 2 — Foundations

- Configure FastAPI.
- Configure PostgreSQL and SQLAlchemy.
- Establish Alembic.
- Implement validated settings.
- Establish structured logging.
- Configure tests and quality checks.
- Implement authentication and authorization foundations.

**Exit criteria:** The application starts reliably, migrations work, and baseline checks pass.

## Phase 3 — Encryption and session security

- Implement the encryption envelope.
- Establish key-management integration.
- Implement protected session persistence.
- Define key rotation and recovery.
- Add tampering and access-control tests.

**Exit criteria:** Sensitive persisted data is protected, key handling is documented, and failure modes are tested.

## Phase 4 — Telegram integration

- Implement the bot interface.
- Implement Telethon authorization.
- Implement account lifecycle management.
- Discover accessible chats.
- Process new-message events.
- Add deduplication and reconnect behavior.
- Implement explicit contact synchronization if required.

**Exit criteria:** Account isolation, session protection, and new-message ingestion work as designed.

## Phase 5 — Secure scanning

- Implement URL extraction and normalization.
- Implement SSRF defenses.
- Add DNS, domain, TLS, and HTTP analysis.
- Integrate reputation providers.
- Persist scan jobs and evidence.

**Exit criteria:** Security tests pass and network/resource restrictions are enforced.

## Phase 6 — Risk engine and AI

- Implement deterministic signals.
- Define the scoring policy.
- Integrate Gemini structured output.
- Add evidence validation.
- Add fallback behavior.
- Build a labeled evaluation set.

**Exit criteria:** Known cases produce expected behavior and insufficient evidence results in `unknown` where appropriate.

## Phase 7 — Notifications and API

- Implement alert dispatch.
- Add delivery tracking.
- Implement notification preferences.
- Expose authorized scan results.
- Add rate limiting and audit controls.

**Exit criteria:** Alerts are traceable, duplicate delivery is controlled, and API access boundaries are tested.

## Phase 8 — Production readiness

- Configure operational monitoring.
- Run security and load tests.
- Test backup and restore.
- Document incident response.
- Review data retention.
- Verify deployment and rollback.
- Review all acceptance criteria.

**Exit criteria:** Production requirements are met, known limitations are documented, and critical security checks pass.

---

# 26. ACCEPTANCE CRITERIA

A feature is complete only when its implementation, tests, and documentation are verified.

## Documentation

- [ ] README provides accurate setup instructions.
- [ ] Architecture and data-flow diagrams match the implementation.
- [ ] ERD and data dictionary match the migrations.
- [ ] Threat model documents major attack paths.
- [ ] Encryption design documents key management and rotation.
- [ ] API contracts document authentication and authorization.
- [ ] Deployment and recovery procedures are documented.
- [ ] Planned functionality is not misrepresented as implemented.

## Encryption and security

- [ ] Sensitive persisted fields have documented protection.
- [ ] Telethon sessions are not stored in plaintext in the database.
- [ ] Encryption keys are not committed or logged.
- [ ] Nonce handling follows the selected cryptographic library's requirements.
- [ ] Modified ciphertext is rejected.
- [ ] Key rotation and recovery procedures are documented.
- [ ] Database and backup access is restricted.
- [ ] Secrets do not appear in ordinary API responses.
- [ ] Cross-user access is prevented and tested.
- [ ] Server and container privileges are minimized.

## Telegram monitoring

- [ ] Authorization uses supported Telegram mechanisms.
- [ ] Account ownership is enforced.
- [ ] Only new messages are processed by default.
- [ ] No historical bulk import occurs during startup.
- [ ] Accessible chats are discovered within platform permissions.
- [ ] URLs are extracted from supported text and entities.
- [ ] Duplicate events are handled safely.
- [ ] Edits and deletions are handled where supported.
- [ ] Contact synchronization is explicitly authorized.
- [ ] Disconnection stops monitoring and triggers defined cleanup.

## Scanner and AI

- [ ] Unsupported URL schemes are rejected.
- [ ] SSRF protections cover prohibited destinations.
- [ ] Redirect destinations are revalidated.
- [ ] Response sizes and timeouts are enforced.
- [ ] Arbitrary JavaScript is not executed.
- [ ] Provider failures are distinguishable from clean results.
- [ ] Gemini output is schema-validated.
- [ ] Evidence references are verified.
- [ ] Confidence and risk score are separate.
- [ ] The system can return `unknown`.
- [ ] AI outages do not create false benign verdicts.

## Background processing

- [ ] Tasks are idempotent.
- [ ] Retries are bounded.
- [ ] Failed jobs can be inspected.
- [ ] Stuck tasks can be reconciled.
- [ ] Queue overload does not block ingestion.
- [ ] Notifications have delivery tracking.
- [ ] Duplicate alerts are controlled.

## Database and API

- [ ] Schema changes have reviewed Alembic migrations.
- [ ] Required foreign keys and constraints exist.
- [ ] User-specific resources enforce ownership.
- [ ] Administrative endpoints enforce roles.
- [ ] Pagination is bounded.
- [ ] Sensitive fields are excluded from normal responses.
- [ ] Retention and deletion behavior is tested.

## Operations

- [ ] Health checks distinguish core failures from optional dependency outages.
- [ ] Logs contain correlation identifiers and exclude secrets.
- [ ] Metrics cover queueing, scanning, AI, and notifications.
- [ ] Backup restoration has been tested.
- [ ] Deployment and rollback are documented.
- [ ] Known limitations and residual security risks are recorded.

---

# 27. AGENT EXECUTION PROTOCOL

## 27.1 Before every substantial task

1. Inspect the repository and actual files.
2. Read this document and relevant detailed documentation.
3. Identify existing functionality and avoid unnecessary duplication.
4. Review dependency compatibility.
5. Identify affected modules, contracts, database models, and migrations.
6. Assess security and privacy implications.
7. Write an implementation plan.
8. Identify tests and acceptance criteria.

Do not assume that the repository matches the target directory structure.

## 27.2 During implementation

1. Work incrementally.
2. Implement and validate domain contracts before wiring modules together.
3. Add tests with each feature.
4. Use mocks for external providers in ordinary unit tests.
5. Update migrations with model changes.
6. Keep sensitive logic explicit and auditable.
7. Avoid unrelated refactoring.
8. Do not remove security controls to bypass failing tests.
9. Do not silently change requirements.
10. Do not store secrets in test fixtures or documentation.
11. Do not claim that a partially implemented security feature is complete.
12. Update the relevant documentation as behavior changes.

## 27.3 After implementation

1. Run relevant tests.
2. Run linting and type checks.
3. Review the final diff.
4. Check for accidental secret leakage.
5. Verify migration consistency.
6. Confirm acceptance criteria.
7. Update documentation.
8. Report what changed.
9. Report tests actually run and their results.
10. List known limitations, unresolved decisions, and remaining risks.

## 27.4 Decision hierarchy

When requirements conflict, prioritize:

1. Security and privacy.
2. Explicit product requirements.
3. Telegram platform constraints.
4. Data integrity.
5. Reliability.
6. Maintainability.
7. Performance.
8. Convenience.

Ask for clarification when ambiguity materially affects security, privacy, or data architecture. Otherwise, choose the safest reasonable default and document the decision.

---

# 28. DEFINITION OF DONE

The platform is ready for an initial production release only when:

- Documentation is accurate and complete for implemented features.
- Telegram account authorization and monitoring work reliably.
- New-message ingestion is idempotent.
- Sensitive persisted data is protected.
- Key management and recovery are documented.
- Cross-user data access is prevented.
- URL scanning is protected against SSRF and resource exhaustion.
- Risk assessments have traceable evidence.
- AI failures and provider outages are handled safely.
- Notifications are tracked and deduplicated.
- Database migrations and automated tests pass.
- Backup and restoration procedures are verified.
- Operational monitoring is configured.
- Security-sensitive acceptance criteria are satisfied.
- Known limitations and residual risks are documented.

**Final principle:** Build a security product, not merely a Telegram bot that calls an AI API. Every sensitive operation must be controlled, every verdict must be explainable, every important workflow must be testable, and every security claim must be supported by implementation and verification.
