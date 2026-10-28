# Security Policy

## Reporting Security Issues

We take the security of this platform seriously. If you discover a vulnerability or security flaw, please report it responsibly so we can resolve the issue before it is publicly disclosed.

### How to Report

Please do NOT file public GitHub issues for security vulnerabilities.

Submit your report privately via email to the engineering security team:
* **Subject:** `[SECURITY VULNERABILITY] <Brief Description>`
* **Information to include:**
  1. Description of the vulnerability and its potential impact.
  2. Detailed reproduction steps or Proof of Concept (PoC).
  3. Affected components, endpoints, or files.
  4. Any proposed mitigations or fixes.

### Response & Handling Timeline

1. **Initial Acknowledgment:** Within 48 hours of receipt.
2. **Assessment & Verification:** Within 5 business days.
3. **Fix & Release:** A patch will be developed, tested, and deployed to all supported environments.
4. **Public Disclosure:** Coordinated only after the patch is verified and deployed.

### Scope

In-scope areas:
* Telethon session persistence & decryption flaws.
* SSRF and DNS rebinding bypasses in the URL scanner.
* Authentication, authorization, and tenant isolation bypasses (IDOR).
* Sensitive data exposure in logs, APIs, or database backups.
* Prompt injection causing critical decision bypass in the risk engine.

Out-of-scope:
* Social engineering attacks against platform operators.
* Denial of service (DDoS) against public demo infrastructure.
