"""RQ task entrypoints. Jobs must be explicitly queued by operational workflows."""
from sqlalchemy import select, delete
from .config import SessionLocal
from .models import Session, now

def expire_sessions():
    with SessionLocal() as db:
        result=db.execute(delete(Session).where(Session.expires_at<now())); db.commit()
        return result.rowcount
