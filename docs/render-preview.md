# Free Render preview

The included `render.yaml` configures two free web services, one free PostgreSQL database and one free Key Value instance for a short-lived preview. It does not deploy a production event/audio service. No Render account, repository connection or deployment has been created by this delivery.

## Deploy the preview

1. Create a GitHub/GitLab/Bitbucket repository with the **contents of `vibesync` at its root**, including `render.yaml`. Push the reviewed code. If instead retaining a parent repository, adjust all Blueprint paths/root directories accordingly before creating services.
2. Sign in to Render and connect that repository. Choose **New → Blueprint**, select the repository and review the resources. Confirm every selected instance is **Free** and review any proposed charge before creation. The Blueprint disables automatic deployments; subsequent releases are manual.
3. Set API `APP_ORIGIN` to the expected frontend origin, for example `https://vibesync-web-preview.onrender.com`. Set frontend `API_INTERNAL_URL` to the expected API origin, for example `https://vibesync-api-preview.onrender.com`. Both require `https://`, no path and no trailing slash. Names may be unavailable; examples are not reserved URLs. Set `MFA_ENCRYPTION_KEY` privately in the API environment to a freshly generated Fernet key (see backend README). Preserve and back up that key securely; changing it invalidates enrolled administrator identities. Never commit it or post it in chat.
4. After Render assigns actual URLs, copy each service's exact public URL from its dashboard. Correct `APP_ORIGIN` on the API service and `API_INTERNAL_URL` on the frontend service. **Rebuild/redeploy the frontend after changing its API URL**, because Next.js resolves its rewrite during the build. Redeploy the API after its origin changes. Until both values match, authentication should fail safely.
5. Wait for healthy API `/health` and frontend `/`. Open the frontend public HTTPS URL; register, sign in, create an organization, create a draft event and verify persistence after a service restart. Confirm cookies are Secure and HttpOnly and that an unapproved origin cannot register or mutate data. Test the public preview on a phone. Do not add real customer or sensitive identity data.

The API startup script selects the installed psycopg PostgreSQL driver, runs Alembic and binds Uvicorn to Render's `$PORT`. It deliberately does not use a paid pre-deploy command. Re-running migrations on a single preview instance is acceptable here; production needs a controlled migration/release phase. The database and Key Value instance accept no public connections. API calls go through the frontend same-origin proxy to the API's public HTTPS URL because free web instances cannot receive private-network requests. [Render Blueprint reference](https://render.com/docs/blueprint-spec).

Free web services do not provide interactive shell/one-off jobs, so the operator licence CLI cannot be invoked in the free service dashboard. Preview account, draft-event and community workflows work without an active licence; licensed publishing/live admissions remain gated. Do not add an unauthenticated licence-grant endpoint to work around this. A controlled workstation can run the CLI with time-limited database access only if an operator explicitly configures restricted access, credentials and an audit record; that is outside this default Blueprint.

## Limits to understand

As checked on 25 October 2026, free Render web services sleep after 15 idle minutes and share 750 monthly instance-hours per workspace. Two continuously running web services exceed that allowance. Cold starts affect both the frontend and API. Free PostgreSQL is limited to 1 GB, expires after 30 days, and has no managed backups; export or replace it before expiry. Free Key Value loses data on restart. Free web instances lack shell access and persistent disks. Usage limits can suspend service or incur charges if payment settings permit. Review [Render's current free-service rules](https://render.com/docs/free) before deploying.

There is no free RQ background worker in this Blueprint. It does not enable queue-based media processing, scheduled maintenance, private S3 media storage, PostGIS spatial application features, or self-hosted UDP SFU/TURN/mixing. Production auth uses Key Value for throttling and fails closed if it is unavailable. Treat its free in-memory state as expendable.

For a future audio preview, supply reviewed LiveKit Cloud `LIVEKIT_URL`, `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` on the API service. A hosted provider's own allowance and billing are separate; no free allowance is assumed. The browser listener/DJ input controls and PCM mixer library are implemented. The hypeman mixer transport adapter, live admission reconciliation and physical-device tests remain incomplete. Paystack likewise requires test credentials and a verified webhook test; leave payment credentials unset for an interface/account preview.

## Suggested next step

Use Render Free to let a small review group explore account, draft-event and community flows. When ready for sustained testing, use always-on web/database services with backups and a worker, and an independently configured audio provider. Commercial launch still depends on the requirements and verification gates in `requirements.md`.
