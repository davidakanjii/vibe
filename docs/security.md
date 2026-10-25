# Security model and launch review

This document is a threat model, not an independent audit or compliance opinion. Read the backend tests and code for the exact implemented controls.

| Boundary / threat | Intended control | Verification before launch |
| --- | --- | --- |
| Browser impersonates another user | Opaque authenticated session, hashed server-side session value, expiry, HttpOnly cookie, secure cookies under HTTPS | Session theft/revocation, logout, recovery and CSRF tests; shared-device behavior |
| User accesses another tenant's event | Server membership, role and resource checks on each operation | Negative tests across tenants and roles, including object identifiers and nested resources |
| Untrusted origin makes authenticated changes | Same-origin frontend, explicit allowed origin and request origin validation | Verify all state-changing endpoints, webhook exemptions, reverse-proxy origin behavior |
| Password and login abuse | Strong password hashing and validation; rate limiting requires review | Distributed throttling, credential stuffing, recovery enumeration and denial-of-service testing |
| Forged or replayed Paystack payment | Provider HMAC signature, server transaction verification, amount/currency/reference checks, idempotent database update | Test provider retries, out-of-order callbacks, duplicates, wrong amount and reconciliation |
| Stolen stream token | Short-lived event/channel-scoped grants and least-privilege publishing | Revocation disconnect, concurrent admission races, session expiry, token replay and SFU webhook verification |
| Unsafe uploads / identity exposure | Private storage, signed URLs, type/size limits, malware quarantine | Media pipeline remains a launch gate; do not accept identity uploads without reviewed retention/access controls |
| Privileged account takeover | Encrypted TOTP enrollment, MFA-verified privileged sessions, replay rejection, audited bootstrap, least privilege and session revocation | Independent review, recovery codes/hardware security keys and verified operator recovery remain launch work |
| Misleading or unlawful marketplace | Disabled paid companionship categories, per-category policy gates | Legal and payment-provider eligibility approval, adult identity verification, human safety/dispute operations |
| Supply-chain or leaked secret | Environment configuration, no committed credentials, CI least privilege | Hash-lock dependencies, reviewed image digests, scanning, rotation and secret manager integration |
| Data loss / operator mistake | Encrypted storage, backups and migration review | Off-host encrypted backups, restore drills, retention, incident response and documented RPO/RTO |

Do not log passwords, session tokens, Paystack secrets, payment card details or sensitive identity content. Restrict audit logs to authorized staff and define retention. Do not place credentials in Terraform variables or state. Store production secrets in a managed vault and inject them at release time; `.env` is only a local development convenience and a manual bootstrap mechanism, not a full secret-management system.

Before public launch, commission independent authorization and payment review, privacy/data-protection review for Nigeria and supported jurisdictions, accessibility assessment, penetration testing, dependency review and abuse-response readiness. Administrative reinstatement, provider verification and report handling require accountable human operators; a dashboard alone is not an operational moderation program.
