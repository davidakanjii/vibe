# Operations and deployment

## Selected environment

The initial infrastructure target is one AWS EC2 Ubuntu 24.04 VM in an existing VPC/public subnet, with encrypted EBS, a static Elastic IP, restricted SSH and public HTTP/HTTPS. It deliberately avoids Kubernetes. `infra/terraform` provisions this host and installs Docker through cloud-init. It does not deploy application code, provide high availability, configure backups, or provision production audio infrastructure. The VM is a single failure domain.

Choose the AWS region after latency, residency, cost and legal review. The default `eu-west-1` is a configurable starting point, not a Nigeria residency claim. Obtain a verified Ubuntu AMI matching the selected region and architecture. Existing VPC, subnet internet routing, EC2 key and AWS credentials are required. Keep Terraform state in an encrypted, access-controlled remote backend with locking before team use; configure that backend locally for the actual account. Do not commit state.

```sh
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Replace all placeholders and review the planned account, region, resources and cost.
terraform init
terraform fmt -check
terraform validate
terraform plan -out=release.tfplan
# Apply only after the reviewed plan is authorized.
terraform apply release.tfplan
```

No Terraform apply or infrastructure deployment has been performed for this delivery. Terraform version constraints are supplied; generate and commit a reviewed `.terraform.lock.hcl` after initialization in the target environment.

## First web release

1. Point an approved DNS hostname at the Elastic IP. SSH from the restricted administrator address; verify cloud-init completion and Docker/Compose availability.
2. Transfer or check out a reviewed immutable repository revision into a release directory. Prefer CI-built, scanned, digest-pinned images in a registry before commercial launch; the included workflow builds and checks images but does not publish or deploy them automatically.
3. Create `.env` outside version control with restrictive permissions (`chmod 600`). Use strong PostgreSQL credentials; percent-encode URL-reserved password characters in `DATABASE_URL` if changing the URL construction. Set `DOMAIN=approved.example`, `APP_ORIGIN=https://approved.example`, `ENVIRONMENT=production`, and approved provider credentials. The frontend uses the same-origin API proxy, so no public API hostname is required.
4. Build and start with `docker compose -f compose.yaml -f infra/production.compose.yaml up -d --build`. Review migration, API, worker, web and Caddy logs. Caddy obtains HTTPS certificates only with working DNS, reachable ports 80/443 and successful certificate issuance.
5. Verify HTTPS, account creation/login/logout, origin protection, tenant denial cases, actual event lifecycle, webhook test delivery and cookie Secure/HttpOnly flags. Confirm private services are unreachable from the internet. Rehearse rollback before admitting real users.

The optional LiveKit development profile must never be exposed as production audio infrastructure. Deploy LiveKit separately with its reviewed release configuration, TLS/WSS hostname, TURN, appropriate UDP/TCP firewall policy, signed server events, private credentials and measured capacity. The Terraform security group intentionally excludes audio media ports.

## Backup and restore

Define a business-approved RPO and RTO before launch. At minimum take encrypted off-host daily database backups and a backup immediately before every migration, monitor their age and test restoration into an isolated environment. Redis AOF is persistence for queue recovery, not a database backup or a guarantee of exactly-once jobs. Back up object data, bucket policies and release metadata separately. Restrict and audit backup access; establish retention and deletion schedules.

Example database dump from the repository root (a POSIX shell inside the VM):

```sh
mkdir -p backups
docker compose exec -T db pg_dump -U vibesync -d vibesync -Fc > backups/vibesync.dump
# Encrypt and copy off-host using approved backup tooling; never leave the sole copy on the VM.
```

Restore only to a fresh isolated database, using `pg_restore --no-owner`, and verify counts, constraints, migrations, login and representative authorization/payment flows. A command succeeding is not sufficient proof of recovery. Never restore over the live database without an incident plan and authorization.

## Monitoring and incidents

Configure external HTTPS availability monitoring, API error/latency metrics, database saturation, disk capacity, queue depth and oldest job, failed/retried jobs, backup age, payment verification failures, webhook delays, certificate expiry, and SFU/relay bitrate, packet loss and participant state. Alert thresholds and an on-call destination must be assigned; this repository does not provide an active hosted monitoring service. Logs should carry request identifiers while avoiding secrets and unnecessary personal data.

For a suspected compromise, contain access, revoke sessions and provider/streaming credentials, preserve restricted audit evidence, suspend affected operations and follow the approved incident communications process. Reconcile pending payments with the provider after recovery; do not grant licences from cached browser state. Define escalation owners for privacy, payments, moderation and audio incidents.

## Release and rollback

CI validates changes on push/pull request. Deployment is intentionally manual until an account, registry and release approver are configured. Record revision, image digests, migration head and configuration version per release. Use backward-compatible expand/migrate/contract schema changes. If a migration is irreversible or data has changed, rollback requires a forward repair or a reviewed restore, not a blind `alembic downgrade`. Keep the previous reviewed images and a tested backup. The VM and Compose architecture do not provide zero-downtime releases or automatic failover.
