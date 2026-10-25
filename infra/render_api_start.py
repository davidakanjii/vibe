"""Render preview launcher: normalize driver, migrate, then replace process with API.

No secrets are printed. Migrations run at every wake/restart because free web
services have no paid pre-deploy phase. Keep this deployment single-instance.
"""
import os
from pathlib import Path
import subprocess
import sys


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgresql://"):]
    elif database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgres://"):]
    if not database_url.startswith("postgresql+psycopg://"):
        raise SystemExit("Render preview requires its PostgreSQL DATABASE_URL")
    origin = os.environ.get("APP_ORIGIN", "")
    if not origin.startswith("https://") or origin.endswith("/"):
        raise SystemExit("Set APP_ORIGIN to the exact frontend HTTPS origin without a trailing slash")
    if not os.environ.get("REDIS_URL"):
        raise SystemExit("REDIS_URL is required for production authentication throttling")
    os.environ["DATABASE_URL"] = database_url
    os.chdir(Path(__file__).resolve().parents[1] / "backend")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app",
                             "--host", "0.0.0.0", "--port", os.environ.get("PORT", "10000")])


if __name__ == "__main__":
    main()
