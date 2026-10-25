# Backend implementation and boundaries

Run `pip install -r requirements.txt`, `alembic upgrade head`, then `uvicorn app.main:app --host 0.0.0.0 --port 8000`. API reference: `/docs`. PostgreSQL is the deployment database; SQLite is supported for isolated tests and local work. Run `python -m pytest tests -q`.

Browser mutations require the configured `APP_ORIGIN` and authenticated mutations additionally require `X-CSRF-Token` from registration/login/me. Sessions are random opaque values stored as SHA256 hashes; passwords use Argon2id. Production cookies require HTTPS. Production authentication throttling uses Redis and fails closed on Redis failure. Do not trust arbitrary proxy forwarded IP headers. Configure proxy and distributed IP rate limits before public deployment.

Organisations are tenant boundaries. Creator membership permits management, but never grants a paid licence. Explicit operator provisioning requires protected deployment access and creates an audit row: `python -m app.provision ORGANISATION_ID --expires-at 2027-01-01T00:00:00+00:00 --operator CHANGE_TICKET_ID`. Browser privileged licence provisioning requires an enrolled, MFA-verified administrator session. Role names exist in membership records; this slice exposes organiser, venue_manager and verified_service_provider checks, not all twelve role workflows.

Local fixtures are opt-in: set `ENVIRONMENT=development` and `LOCAL_SEED_PASSWORD` (12+ characters), then `python -m app.seed`. All fixture events have `[Sample]` descriptions and fictional venues. These records are not production activity.

Event state transitions require active licences. Live tokens additionally require live schedule, joined attendance or explicit channel publisher assignment. Rooms are scoped per event/channel; credentials expire within five minutes or earlier at licence/event expiry. LiveKit credentials and an accessible SFU are required. SFU room participant limits, listener occupancy coordination, server-side hypeman mixing/ducking, microphone routing priority, stream metrics, real browser/device latency and background playback remain unimplemented/unverified. Hypeman raw SFU publication is denied: only DJ assignments can publish. PUT /api/events/{id}/mic-routing persists assigned hypeman routes with event/zone enforcement, mute, PTT, active state and gain; broadcast-all requires an operator-set allow_broadcast_all grant. Responses explicitly return transport_ready=false. app/audio_mixer.py implements actual fixed-block PCM16 DSP (48 kHz stereo, 10 ms), saturating clipping, voice gain, music ducking, trusted priority and per-channel routing isolation. It has no network adapter: LiveKit PCM ingress, mixer scheduling/egress, codec handling, feedback prevention and browser PTT transport remain unimplemented. The library is not a live audio service.

Paystack checkout uses server-stored event price. Webhooks require HMAC-SHA512 and independent server-side transaction verification matching reference, amount and currency; database row locks serialize successful processing under PostgreSQL. No browser callback grants attendance. A full event puts verified payments into `refund_required` for reconciliation; automated refunds, receipts and a reconciliation worker remain unimplemented. Paystack credentials and live/test gateway transactions remain unverified.

RQ entrypoint `app.jobs.expire_sessions` deletes expired sessions and is safe to retry; scheduling/queueing and operational retry policy are deployment responsibilities. Other pending production systems include email verification/password recovery/OAuth, moderated media uploads and object storage, source-verified geographical data/PostGIS queries, blocked users/reports/comments, campaign approval and marketing delivery, provider identity/age verification, complete subscriptions/add-ons, privacy export/deletion and comprehensive operational analytics. Professional bookings require operator-created verified provider membership; companionship categories reject validation and cannot be enabled through API.

The initial migration uses frozen metadata in alembic/initial_schema.py. Future schema migrations must be explicit; never edit the frozen initial schema. This is a functional initial application slice, not a claim of production readiness or a security audit.



## Privileged administrator setup and MFA

For explicitly approved loopback-only development testing, set `DEV_SKIP_ADMIN_MFA=true` in an ignored backend `.env` and restart the API. The default is false. The skip requires `ENVIRONMENT=development`, a loopback application origin and a loopback client address. Password and administrator checks still apply, logins are audited, and sessions are not falsely marked MFA-verified. Production and non-loopback clients reject the skip. Set the flag to false and restart to restore mandatory MFA; existing password-only sessions immediately lose privileged access. This switch is deliberately absent from deployment templates.

No administrator is created at registration or application startup. Keep `MFA_ENCRYPTION_KEY` in the deployment secret store (Fernet key, generated once using `Fernet.generate_key()`); preserve a protected backup. Rotating this key without re-enrollment makes existing encrypted identities unusable. Never publish `.env`, database copies, authenticator secrets or recovery credentials.

After setting the key and running `alembic upgrade head`, an operator with protected deployment/database access runs:

```sh
python -m app.bootstrap_admin --email YOUR_ACCOUNT_EMAIL --username YOUR_USERNAME
```

The command prompts twice using hidden `getpass` input. It stores an Argon2 password hash, an encrypted newly generated TOTP secret and an unconfirmed enrollment; it prints only the username and an instruction to complete enrollment in the app. Existing account bootstrap resets MFA and revokes all existing sessions and enrollment challenges. Production passwords require at least 12 characters. The explicit `--allow-development-password` flag permits at least 10 characters only when `ENVIRONMENT=development`; it refuses to run with that exception in any other environment. Do not put passwords into command arguments, source files or logs.

In the application's login form, enter username/email and password, then choose authenticator setup. The password-verified enrollment-start API returns the secret and otpauth URI only for an unconfirmed administrator and creates a five-minute hashed opaque challenge cookie. The confirmation API requires a correct TOTP, consumes the challenge, confirms enrollment and creates an MFA-verified session. The app should keep the returned enrollment secret only in transient UI state and clear it on completion. Confirmed accounts cannot retrieve that secret through the enrollment endpoint. Do not add external QR generation or analytics to this screen.

Subsequent administrator sign-ins require password plus a fresh six-digit TOTP. Atomic database compare-and-update rejects reused time steps across workers. The current or previous 30-second time step is accepted; server clock synchronization is required. Codes used to confirm enrollment cannot immediately be reused for a separate sign-in. Recovery/reset requires the same protected operator bootstrap command; no unauthenticated recovery bypass exists.

Privileged sessions carry a server-stored MFA flag; user promotion does not upgrade existing sessions. Admin metrics, users, licences, organisations and audit endpoints require both administrator status and an enrolled MFA-verified session. Suspending/reinstating users revokes their sessions and writes an audit event. Administrator self-suspension through this API is blocked. Revenue metrics currently report verified NGN ticket revenue only.

APIs: `POST /api/auth/mfa/enroll/start {email,password}`, `POST /api/auth/mfa/enroll/confirm {otp}`, `POST /api/auth/login {email,password,otp?}`, `GET /api/admin/{metrics,users,organisations,audit}`, `PUT /api/admin/users/{id}/status {suspended}`, and `PUT /api/admin/organisations/{id}/licence`. Enrollment/login enforce configured origin and rate limits. All API responses use no-store and Vary: Cookie.

MFA implementation has automated functional/security tests, not an independent audit. Hardware security keys, recovery codes and remote identity verification are not implemented. Production still requires secure operator access, TLS, secret management, stable clock sync, backups and security review.
