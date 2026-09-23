# Security Policy

We treat the security and privacy of TelegramWarden installations seriously. If you find a security vulnerability, please report it responsibly by following the instructions below.

## Supported versions

Security fixes are released for the active `main` branch and current stable tagged versions.

| Version       | Supported |
| ------------- | --------- |
| main (latest) | Yes       |
| v1.1.x        | Yes       |
| < 1.0.0       | No        |

## Reporting a vulnerability

Do not report security vulnerabilities in public GitHub issues, pull requests, or public discussions.

To report a vulnerability safely:

1. **GitHub Security Advisories (Preferred):**
   Open the repository on GitHub, navigate to the **Security** tab, select **Report a vulnerability**, and submit your report privately.

2. **Direct contact:**
   If private advisory reporting is unavailable, reach out directly to the maintainer on Telegram: [@ivanchikbyte](https://t.me/ivanchikbyte).

### Information to include

To help us investigate and patch the issue quickly, include:

* A clear summary of the vulnerability type (for example, authentication bypass, SQL injection, token leakage, unauthenticated endpoint access, or rate-limit evasion).
* The specific files, endpoints, or handlers affected.
* Step-by-step instructions to reproduce the issue, including example requests or payloads where applicable.
* The expected security impact and affected configurations.
* Any suggested fix or remediation steps you have identified.

## Third-party AI processing

When optional integrations are enabled, message texts leave the server perimeter:

* **TypeSafe Jev** (`JEV_ENABLED=true`): sanitized message text is sent to `api.typesafe.ai` (USA, SaaS, no on-premise option) for Tier-1 triage. No media bytes are sent, only text. Disable with `JEV_ENABLED=false` to keep all text processing on DeepSeek/Groq only.
* **DeepSeek / Groq**: message texts are sent to the configured LLM providers for verdicts (see `DEEPSEEK_BASE_URL`, `FALLBACK_BASE_URL`).

## Response timeline and remediation

1. **Acknowledgment:** We will acknowledge your report within 48 hours of receipt.
2. **Assessment:** We will confirm the issue, determine severity, and assess affected components within 5 business days.
3. **Fix and verification:** We will develop and test a fix in a private branch.
4. **Coordinated disclosure:** Once a release with the fix is available, we will announce it and credit your responsible disclosure (unless you prefer to remain anonymous).
