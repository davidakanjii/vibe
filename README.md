# VibeSync

VibeSync is a mobile-first entertainment platform under active development. The repository contains a Next.js PWA, a FastAPI modular monolith, database migrations, tests, and local deployment configuration. The name is provisional pending brand, domain, and trademark clearance.

**This delivery is an engineering foundation, not a production certification.** Read [delivery scope](docs/requirements.md) for implemented boundaries and launch gaps. No live payments, hardware audio results, security audit, or deployment are claimed.

## Run locally

Prerequisites: Docker Engine with Compose v2, available ports 3000 and 8000, and internet access to retrieve container images and dependencies.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose logs -f api web
```

Open [VibeSync](http://localhost:3000) and [API documentation](http://localhost:8000/docs). Create an account in the application. The database starts empty; there are no real-world event, financial, or administrative geography fixtures.

The migration container runs `alembic upgrade head` before the API or RQ worker starts. Database and Redis ports stay on the Docker network. Web/API ports bind only to the local machine. This configuration uses development cookies and must not be exposed as a public deployment.

```powershell
docker compose ps
docker compose logs worker migrate
docker compose stop
```

Named volumes retain database, queue and optional object data. `docker compose down` retains volumes; adding `--volumes` permanently removes them.

## Optional services

```powershell
docker compose --profile storage up -d minio
docker compose --profile audio up -d livekit
```

MinIO is a local S3-compatible development endpoint at port 9000, with a console at port 9001. Buckets and private/public policies require configuration; starting MinIO does not enable a complete media pipeline. LiveKit is explicitly a local development server. Its development key/secret must be configured to match backend token issuance. It is not an implemented server-side hypeman mixer or a production TURN deployment.

## Developer checks

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
cd ..\frontend
npm ci
npm run build
```

CI repeats backend tests, the frontend production build, Compose parsing, image builds, migrations against PostgreSQL, and PostGIS availability. A committed frontend npm lockfile controls dependency resolution. Container base tags are intentionally explicit major/version selections but are not immutable digests; production releases must resolve, scan and pin reviewed digests. Python requirements currently specify compatible version ranges; create a reviewed transitive hash lock before release.

## Deployment and design

- [Free Render preview](docs/render-preview.md): `render.yaml` and exact setup steps, with free-tier limits and missing audio/worker capabilities.
- [Operations and deployment](docs/operations.md): AWS VM Terraform, HTTPS, backups, recovery and release process.
- [Architecture and audio](docs/architecture.md): trust boundaries, licensing, audio trade-offs and device verification.
- [Threat model](docs/security.md): security controls and remaining risks.
- [Delivery requirements](docs/requirements.md): scope and unverified dependencies.
- [Verification record](docs/validation.md): actual automated and browser checks, with explicit verification limits.

Use Paystack test credentials first. Provider secrets stay on the backend. Browser checkout success never serves as payment confirmation. Paid marketplace categories remain disabled pending legal, provider eligibility, and identity verification work.

Administrator accounts use an operator-only bootstrap command and mandatory authenticator enrollment. See [administrator setup](backend/README.md) for key generation, hidden password prompts, first sign-in, and recovery. Local credentials and data do not transfer to a hosted deployment.

For controlled local event activation, an infrastructure operator can issue a time-limited licence from inside the API container:

```powershell
docker compose exec api python -m app.provision ORGANIZATION_ID --expires-at 2027-01-01T00:00:00+00:00 --operator LOCAL-TEST-TICKET
```

Replace the organization ID and audit ticket. This explicit trusted-operator action is not a user self-service purchase and must not be used to bypass the payment and privileged-administration review required for launch.
