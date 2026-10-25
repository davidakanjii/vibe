# Delivery scope and launch gates

The source request describes a substantial commercial platform. This repository is an initial implementation with explicit unfinished areas. Existing code and automated tests are authoritative for behavior; inclusion in the design does not mean a feature is complete. No generated placeholder metric is operational evidence.

| Request area | Delivery / boundary | Work required before commercial use |
| --- | --- | --- |
| PWA / interface | Next.js TypeScript responsive interface, manifest/service worker and install assets | Real-device browser matrix, accessibility assessment against WCAG 2.2 AA, offline privacy and cache checks |
| Authentication | Persistent sessions, username/email login, operator admin bootstrap, encrypted TOTP enrollment, replay-resistant MFA and MFA-required privileged sessions | Email delivery/verification and password reset/recovery, OAuth/phone integration, account export/deletion and independent security review |
| Tenant permissions | Organization membership, server authorization and event ownership foundation | Exhaustive role/resource/event coverage, invitation/reinstatement lifecycle, audited privileged bootstrap |
| Events | Persistent organizer/event/channel lifecycle foundation | Full scheduling, venue/check-in/ticket categories, branding, private admissions and analytics coverage |
| Payments | Paystack integration boundary with server verification and webhook idempotency | Test credentials, provider test evidence, accounting reconciliation, refunds, invoices, subscription lifecycle and production approval |
| Licensing | Event activation/channel/listener policy boundary | Race-safe live admission reconciliation, duration/subscription enforcement, all commercial plans and auditable entitlements |
| Multi-DJ audio | LiveKit event/channel credential boundary and local optional server | Full ingest and browser SDK integration where absent, lifecycle/health events, TURN, revocation, measured load and real-device playback |
| Hypeman | Persistent scoped routing API plus tested PCM16 server DSP for ducking, gain, clipping, priority, mute/PTT and event/zone boundaries; raw SFU publishing denied to hypemen | Connect the DSP engine to a LiveKit PCM transport adapter, operator broadcast-all provisioning, revocation/health handling and physical acoustic tests; microphone delivery stays disabled until then |
| Geography | Extensible data architecture; PostGIS-capable local database | Authoritative licensed Nigeria hierarchy import with provenance, cascading selectors, spatial indexes/queries and consent/retention |
| Social | Initial API/UI community foundation where present | Media validation/scanning/transcoding, full profiles/comments/mentions/groups, blocking/privacy/moderation coverage |
| Trending | Transparent ranking design | Production ranking job, geographical scopes, spam resistance, source-backed metrics and moderation review |
| Marketplace | Disabled sensitive paid categories; legal boundary documented | Identity/age verification, booking/payment/review/dispute/safety workflows and jurisdiction/provider eligibility approvals |
| Advertising | Consent-first product design | Campaign approvals, budgets, frequency caps, scoped targeting, reporting, push/email providers and opt-out enforcement |
| Admin analytics | MFA-protected database metrics, user suspension/reinstatement with session revocation, audited licence controls, organisation list and audit history | Full date/tenant/location filters, measured live audio quality, per-currency financial reporting and operational telemetry |
| Storage / background work | Optional S3-compatible MinIO and Redis/RQ process configuration | Bucket/access policies, signed uploads, scanning/processing, idempotent jobs, retries/dead-letter visibility and operational alerting |
| Deployment | Docker Compose, CI checks, single-VM Terraform and HTTPS overlay | Actual account/DNS/secrets, digest locking/scanning, hosted monitoring, backup automation/restore drill, release approvals and deployment validation |

## Acceptance evidence

Do not equate a successful build with feature acceptance. Record actual test commands, environment, exit code and failures in the final delivery report. CI must run independently after the repository is pushed. Container and Terraform configurations require validation with their actual tools and target credentials. Payment provider verification requires real provider test requests. SFU transport, background playback and microphone quality require physical devices and an actual network.

## External blockers

- Domain ownership and provisional-name trademark/brand clearance.
- Paystack test/live credentials and merchant eligibility approval; external webhook URL.
- Email/SMS/OAuth/push provider configuration and consent records.
- Production SFU/TURN/mixer infrastructure, audio hardware, venue Wi-Fi measurements and browser/device test access.
- Music/public-performance and redistribution rights, plus legal review for each launch jurisdiction.
- Verified geographical data licence/provenance and import approval.
- Marketplace category review, payment-provider approval, identity/age-verification provider and human safety operations.
- Production AWS account, DNS, secure secrets, backup destination, incident owners and independent security/privacy/accessibility reviews.

Until these gates and incomplete systems are resolved, use local development and controlled testing only. The repository must not be described as a completed, audited or deployed production platform.
