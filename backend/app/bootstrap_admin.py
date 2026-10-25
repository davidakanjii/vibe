"""Operator-only privileged bootstrap. Secrets enter only through hidden prompts."""
import argparse
from getpass import getpass
import re
import pyotp
from sqlalchemy import select,delete,func
from .config import settings,SessionLocal
from .models import User,Session,MfaEnrollment,Audit
from .security import hasher
from .mfa import encrypt_secret

def bootstrap(db,email,username,password,allow_development_password=False):
    email=email.strip().lower(); username=username.strip()
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{2,39}',username): raise ValueError('Username must be 3–40 letters, digits or underscores, starting with a letter')
    if '@' not in email or '.' not in email.split('@')[-1]: raise ValueError('A valid account email is required')
    minimum=12
    if allow_development_password:
        if settings.environment!='development': raise ValueError('Development password exception is forbidden outside development')
        minimum=10
    if not minimum<=len(password)<=128: raise ValueError(f'Password must contain {minimum}–128 characters')
    collision=db.scalar(select(User).where(func.lower(User.username)==username.lower(),User.email!=email))
    if collision: raise ValueError('Username already belongs to another account')
    user=db.scalar(select(User).where(User.email==email).with_for_update())
    if not user: user=User(email=email,display_name=username); db.add(user)
    user.username=username; user.password_hash=hasher.hash(password); user.platform_admin=True; user.suspended=False
    user.mfa_secret_encrypted=encrypt_secret(pyotp.random_base32()); user.mfa_confirmed=False; user.mfa_last_step=-1
    db.flush()
    db.execute(delete(Session).where(Session.user_id==user.id)); db.execute(delete(MfaEnrollment).where(MfaEnrollment.user_id==user.id))
    db.add(Audit(actor_id='operator:bootstrap',action='admin.bootstrap.mfa_pending',resource_id=user.id))
    db.commit(); return user

def main():
    parser=argparse.ArgumentParser(description='Provision/reset an administrator; complete authenticator enrollment in the application.')
    parser.add_argument('--email',required=True); parser.add_argument('--username',required=True)
    parser.add_argument('--allow-development-password',action='store_true',help='Development only: permit a 10-character password; production always requires 12+')
    args=parser.parse_args()
    password=getpass('Administrator password: ')
    confirm=getpass('Confirm administrator password: ')
    if password!=confirm: parser.error('Passwords do not match')
    try:
        with SessionLocal() as db: user=bootstrap(db,args.email,args.username,password,args.allow_development_password)
    except ValueError as exc: parser.error(str(exc))
    print(f'Administrator {user.username} provisioned. Complete enrollment in the app.')
if __name__=='__main__': main()
