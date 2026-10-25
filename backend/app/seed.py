"""Explicit fictional local fixtures; never invoked on startup."""
import os
from datetime import datetime, timezone
from sqlalchemy import select
from .config import settings, SessionLocal
from .models import User, Organisation, Membership, Licence, Event, Channel
from .security import hasher

def main():
    if settings.environment!='development': raise SystemExit('Seed is development-only')
    password=os.environ.get('LOCAL_SEED_PASSWORD','')
    if len(password)<12: raise SystemExit('Set LOCAL_SEED_PASSWORD to at least 12 characters')
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email=='organiser@example.test')): print('Local fixtures already exist'); return
        user=User(email='organiser@example.test',display_name='Local sample organiser',password_hash=hasher.hash(password)); db.add(user); db.flush()
        org=Organisation(name='Fictional local events'); db.add(org); db.flush()
        db.add(Membership(organisation_id=org.id,user_id=user.id,role='organiser'))
        db.add(Licence(organisation_id=org.id,expires_at=datetime(2027,1,1,tzinfo=timezone.utc),max_channels=4,max_listeners=100))
        samples=[('Lagos After Dark','Afrobeats','Victoria Island',7),('Mainland Sessions','Amapiano','Ikeja',14),('The Sunday Social','R&B','Lekki',15),('Neon Frequencies','Electronic','Yaba',21)]
        for title,genre,venue,day in samples:
            event=Event(organisation_id=org.id,title=title,description='[Sample] Fictional development event. No real booking, venue partnership or live stream.',venue=venue+' · fictional venue',city='Lagos',genre=genre,starts_at=datetime(2026,11,day,18,tzinfo=timezone.utc),ends_at=datetime(2026,11,day,23,tzinfo=timezone.utc),status='published',capacity=100,price_minor=0,currency='NGN'); db.add(event); db.flush()
            db.add(Channel(event_id=event.id,name=genre,genre=genre,dj_user_id=user.id))
        db.commit(); print('Created fictional fixtures; sign in as organiser@example.test using LOCAL_SEED_PASSWORD')
if __name__=='__main__': main()
