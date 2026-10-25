"""TOTP secrets are encrypted at rest and disclosed only during password-verified initial enrollment."""
from datetime import datetime, timezone
from cryptography.fernet import Fernet, InvalidToken
import pyotp
from fastapi import HTTPException
from sqlalchemy import update
from .config import settings
from .models import User

def cipher():
    try: return Fernet(settings.mfa_encryption_key.encode())
    except (ValueError,TypeError): raise HTTPException(503,'MFA key is not configured correctly')
def encrypt_secret(secret:str)->str: return cipher().encrypt(secret.encode()).decode()
def decrypt_secret(secret:str)->str:
    try: return cipher().decrypt(secret.encode()).decode()
    except InvalidToken: raise HTTPException(503,'MFA key does not match enrolled identity')
def verify_fresh_totp(db,user,otp:str|None):
    if not otp: raise HTTPException(401,'MFA code required')
    if not user.mfa_secret_encrypted: raise HTTPException(403,'Privileged account requires operator MFA enrollment')
    totp=pyotp.TOTP(decrypt_secret(user.mfa_secret_encrypted))
    step=int(datetime.now(timezone.utc).timestamp())//totp.interval
    # Tight 30s time window; preceding step accepted for normal delivery drift.
    matched=next((candidate for candidate in (step,step-1) if candidate>=0 and totp.verify(otp,for_time=candidate*totp.interval,valid_window=0)),None)
    if matched is None: raise HTTPException(401,'Invalid MFA code')
    changed=db.execute(update(User).where(User.id==user.id,User.mfa_last_step<matched).values(mfa_last_step=matched))
    if changed.rowcount!=1: raise HTTPException(401,'MFA code has already been used')
    # Persist with the session insertion transaction, preventing replay across workers.
    return True
