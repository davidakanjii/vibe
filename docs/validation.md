# Verification record — 25 October 2026

Verified locally on Windows with Node.js, bundled Python and SQLite. This is implementation evidence, not production acceptance.

| Check | Actual result |
| --- | --- |
| `frontend: npm run build` | Passed Next.js production compile, TypeScript, static generation and standalone output |
| `frontend: npm run typecheck` | Passed |
| Standalone production start | `npm start` wrapper ran the compiled standalone server; page, event API proxy, manifest, PNG icon and offline HTML returned HTTP 200 |
| `backend: pytest -q` | 27 passed after administrator/MFA, blank-code and local-only skip regression checks; one dependency deprecation warning in Starlette TestClient/httpx |
| Alembic `upgrade head` | Passed initial, `0002` and `0003` upgrades against local SQLite; production PostgreSQL remains a CI/deployment check |
| `python infra/smoke_local.py` | Passed through the actual Next.js proxy and running API, with persistent labelled test records |
| Browser discovery | Fictional seeded database events load; genre filter reduces four results to one Amapiano event |
| Browser responsive QA | Desktop and 390 × 844 mobile layouts inspected; mobile hero clipping fixed |
| Browser accessibility spot check | Native modal isolates accessibility tree and traps keyboard focus; mobile hidden sidebar removed from focus/navigation tree |
| PWA | Manifest and PNG icons supplied; offline fallback avoids caching authenticated API/session data; production installation/device behavior unverified |
| Render startup wrapper | Driver conversion and bad-configuration unit checks passed during authoring; cloud deployment unverified |

## Automated security and audio coverage

Tests exercise session expiry, Origin/CSRF rejection, tenant ownership, licence expiry, live-event schedule, capacity and idempotent admissions, independently verified Paystack webhook amount matching and replay handling, LiveKit room/publisher claims and token lifetime, preference/report/ticket boundaries, hypeman cross-event/channel/zone rejection, and PCM16 ducking/gain/clipping/priority routing.

Administrator tests also cover encrypted TOTP storage, password-verified and expiring enrollment, legacy sessions denied privileged access, fresh-code replay rejection, MFA-gated account/licence actions and suspension revocation. An explicit development-only bootstrap switch permits a user-chosen 10-character local password; production bootstrap continues to require at least 12 characters. No real administrator credential or database is included in source archives or Git.

Blank optional authenticator codes are normalized to absent input. Regular members can sign in without MFA, unconfirmed administrators reach enrollment, and confirmed administrators remain denied without a code. Malformed nonempty codes still fail validation. The frontend omits blank codes and automatically offers enrollment only after valid credentials return the explicit enrollment-required response.

An explicitly requested development-only MFA skip was tested with password checks intact. Production environment, non-loopback origin/client and disabling the flag all deny password-only admin access. The local setting is excluded from source archives and deployment templates. The UI labels these sessions as local testing rather than MFA verified.

The payment provider is mocked in tests. No real Paystack checkout or transaction was performed. The SFU is not connected during tests. PCM tests validate the DSP library, not end-to-end microphone transport or acoustic quality.

## Manual environment notes

The preview database contains four fictional `[Sample]` events and explicitly labelled `[Test]` records from HTTP smoke checks. The seed runs only when explicitly requested in development. Production starts without these fixtures. Stock concert artwork is decorative, not evidence of a venue partnership.

Python test dependencies were installed in ignored `backend/.deps` in this workspace. The normal documented development flow uses a virtual environment. Some local dependency ACLs required approved execution outside the sandbox; those paths are not deployment configuration.

## Unverified launch conditions

Docker Engine and Terraform were unavailable locally, so containers and infrastructure were not executed here. The CI definition includes container builds, PostgreSQL migrations and PostGIS detection but has not run on a remote repository. No Render/AWS deployment, domain, provider configuration, load test, independent security audit, WCAG compliance audit or physical Android/iOS/Bluetooth test is claimed.

See [requirements](requirements.md) for outstanding feature implementation and [Render preview](render-preview.md) for the first hosted evaluation environment.
