from datetime import timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe, compare_digest
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DB
from .config import settings, db_session
from .models import User, Session, Membership, now
hasher=PasswordHasher()
def utc(value): return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

def current_user(request:Request,db:DB=Depends(db_session)):
    token=request.cookies.get('vs_session','')
    session=db.get(Session,sha256(token.encode()).hexdigest())
    if not session or utc(session.expires_at)<=now(): raise HTTPException(401,'Sign in required')
    user=db.get(User,session.user_id)
    if not user or user.suspended: raise HTTPException(403,'Account unavailable')
    if request.method not in ('GET','HEAD','OPTIONS'):
        if request.headers.get('origin')!=settings.app_origin: raise HTTPException(403,'Invalid origin')
        if not compare_digest(request.headers.get('x-csrf-token',''),session.csrf): raise HTTPException(403,'Invalid CSRF token')
    request.state.session=session
    return user

def issue_session(db,user,response,mfa_verified=False):
    token=token_urlsafe(48); csrf=token_urlsafe(32)
    db.add(Session(token_hash=sha256(token.encode()).hexdigest(),user_id=user.id,mfa_verified=mfa_verified,csrf=csrf,expires_at=now()+timedelta(days=7))); db.commit()
    secure=settings.environment=='production'
    response.set_cookie('vs_session',token,httponly=True,secure=secure,samesite='lax',max_age=604800,path='/')
    response.set_cookie('vs_csrf',csrf,secure=secure,samesite='lax',max_age=604800,path='/')
    return {'user':profile(user),'csrf_token':csrf,'mfa_verified':mfa_verified}
def profile(user): return {'id':user.id,'email':user.email,'display_name':user.display_name,'marketing_consent':user.marketing_consent,'username':user.username,'platform_admin':user.platform_admin,'mfa_enabled':bool(user.mfa_secret_encrypted and user.mfa_confirmed)}
def manager(db,user,org_id):
    member=db.scalar(select(Membership).where(Membership.organisation_id==org_id,Membership.user_id==user.id,Membership.role.in_(['organiser','venue_manager'])))
    if not member: raise HTTPException(403,'Organisation management permission required')

def require_admin(request:Request,user:User=Depends(current_user)):
    if not user.platform_admin or not request.state.session.mfa_verified or not user.mfa_secret_encrypted or not user.mfa_confirmed:
        raise HTTPException(403,'Administrator with a verified MFA session required')
    return user
