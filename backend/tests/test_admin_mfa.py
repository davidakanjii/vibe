import pytest
from datetime import timedelta
from hashlib import sha256
from cryptography.fernet import Fernet
import pyotp
from sqlalchemy import select
from app.config import settings
from app.models import User,Session,MfaEnrollment,Audit,now
from app.bootstrap_admin import bootstrap
from app.mfa import decrypt_secret
from test_security import setup,signup

ORIGIN={'origin':'http://localhost:3000'}

@pytest.fixture
def mfa_key(monkeypatch):
    monkeypatch.setattr(settings,'mfa_encryption_key',Fernet.generate_key().decode())

def make_pending(factory,username='TestAdmin'):
    with factory() as db:
        user=bootstrap(db,'admin@example.test',username,'test-only-admin-password')
        return user.id

def enroll(client):
    result=client.post('/api/auth/mfa/enroll/start',headers=ORIGIN,json={'email':'TestAdmin','password':'test-only-admin-password'})
    assert result.status_code==200,result.text
    secret=result.json()['secret']
    otp=pyotp.TOTP(secret).now()
    confirmed=client.post('/api/auth/mfa/enroll/confirm',headers=ORIGIN,json={'otp':otp})
    assert confirmed.status_code==200,confirmed.text
    return secret,confirmed.json(),otp

def test_bootstrap_encrypts_and_no_admin_without_mfa(setup,mfa_key):
    client,factory=setup
    user_id=make_pending(factory)
    with factory() as db:
        user=db.get(User,user_id)
        assert user.username=='TestAdmin' and user.platform_admin
        assert user.mfa_secret_encrypted.startswith('gAAAA')
        assert decrypt_secret(user.mfa_secret_encrypted)!=user.mfa_secret_encrypted
        assert user.mfa_confirmed is False
    assert client.post('/api/auth/login',headers=ORIGIN,json={'email':'TestAdmin','password':'test-only-admin-password'}).status_code==403
    headers,regular=signup(client)
    assert client.get('/api/admin/users').status_code==403
    assert client.get('/api/admin/organisations').status_code==403
    assert client.get('/api/admin/audit').status_code==403
    # Simulate legacy session created before privilege promotion: never implicitly trusted.
    with factory() as db:
        target=db.get(User,regular['id']); target.platform_admin=True
        target.mfa_secret_encrypted=db.get(User,user_id).mfa_secret_encrypted; target.mfa_confirmed=True; db.commit()
    assert client.get('/api/admin/metrics').status_code==403

def test_enrollment_challenge_secret_requires_credentials_and_expires(setup,mfa_key):
    client,factory=setup; user_id=make_pending(factory)
    assert client.post('/api/auth/mfa/enroll/start',headers=ORIGIN,json={'email':'TestAdmin','password':'wrong'}).status_code==401
    assert client.post('/api/auth/mfa/enroll/start',json={'email':'TestAdmin','password':'test-only-admin-password'}).status_code==403
    response=client.post('/api/auth/mfa/enroll/start',headers=ORIGIN,json={'email':'TestAdmin','password':'test-only-admin-password'})
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    assert 'otpauth://' in response.json()['otpauth_uri']
    with factory() as db:
        challenge=db.scalar(select(MfaEnrollment)); assert challenge.token_hash!=client.cookies['vs_mfa_enrollment']
        challenge.expires_at=now()-timedelta(seconds=1); db.commit()
    otp=pyotp.TOTP(response.json()['secret']).now()
    assert client.post('/api/auth/mfa/enroll/confirm',headers=ORIGIN,json={'otp':otp}).status_code==401
    assert client.get('/api/admin/users').status_code==401

def test_enrollment_login_mfa_replay_and_admin_operations(setup,mfa_key,monkeypatch):
    client,factory=setup
    # A second member exists so suspension and session revocation have a concrete target.
    headers,member=signup(client,'member@example.test')
    member_cookie=client.cookies['vs_session']
    org=client.post('/api/organisations',headers=headers,json={'name':'Test Organisation'}).json()['id']
    user_id=make_pending(factory)
    secret,session,otp=enroll(client)
    assert session['mfa_verified'] is True and session['user']['mfa_enabled'] is True
    admin_headers={**ORIGIN,'x-csrf-token':session['csrf_token']}
    assert client.get('/api/admin/metrics').status_code==200
    assert len(client.get('/api/admin/users').json())==2
    assert client.get('/api/admin/organisations').json()[0]['licence'] is None
    licence=client.put('/api/admin/organisations/'+org+'/licence',headers=admin_headers,json={'expires_at':(now()+timedelta(days=1)).isoformat(),'max_channels':4,'max_listeners':100})
    assert licence.status_code==200
    assert client.get('/api/admin/organisations').json()[0]['licence']['max_channels']==4
    assert client.put('/api/admin/users/'+member['id']+'/status',headers=admin_headers,json={'suspended':True}).status_code==200
    with factory() as db:
        assert db.get(Session,sha256(member_cookie.encode()).hexdigest()) is None
        assert db.get(User,member['id']).suspended
    assert client.put('/api/admin/users/'+member['id']+'/status',headers=admin_headers,json={'suspended':False}).status_code==200
    assert client.put('/api/admin/users/'+user_id+'/status',headers=admin_headers,json={'suspended':True}).status_code==409
    assert any(row['action']=='admin.account.suspend' for row in client.get('/api/admin/audit').json())
    assert client.post('/api/auth/mfa/enroll/start',headers=ORIGIN,json={'email':'TestAdmin','password':'test-only-admin-password'}).status_code==409
    assert client.post('/api/auth/login',headers=ORIGIN,json={'email':'TestAdmin','password':'test-only-admin-password'}).status_code==401
    assert client.post('/api/auth/login',headers=ORIGIN,json={'email':'TestAdmin','password':'test-only-admin-password','otp':otp}).status_code==401
    invalid=next(code for code in ['000000','111111','222222'] if not pyotp.TOTP(secret).verify(code,valid_window=1))
    assert client.post('/api/auth/login',headers=ORIGIN,json={'email':'TestAdmin','password':'test-only-admin-password','otp':invalid}).status_code==401
    # Controlled clock advance: a new fresh timestep can authenticate; old step stays rejected.
    import app.mfa as mfa
    from datetime import datetime,timezone
    future=datetime.now(timezone.utc)+timedelta(seconds=60)
    class FutureClock:
        @staticmethod
        def now(tz=None): return future
    monkeypatch.setattr(mfa,'datetime',FutureClock)
    result=client.post('/api/auth/login',headers=ORIGIN,json={'email':'testadmin','password':'test-only-admin-password','otp':pyotp.TOTP(secret).at(future)})
    assert result.status_code==200 and result.json()['mfa_verified'] is True

def test_development_password_exception_is_explicit_and_forbidden_production(setup,mfa_key,monkeypatch):
    _,factory=setup
    with factory() as db:
        with pytest.raises(ValueError): bootstrap(db,'example@example.test','ShortAdmin','1234567890')
        user=bootstrap(db,'example@example.test','ShortAdmin','1234567890',True)
        assert user.platform_admin and not user.mfa_confirmed
        monkeypatch.setattr(settings,'environment','production')
        with pytest.raises(ValueError): bootstrap(db,'example@example.test','ShortAdmin','1234567890',True)

def test_bootstrap_reset_revokes_sessions_and_confirmation(setup,mfa_key):
    client,factory=setup; user_id=make_pending(factory); _,session,_=enroll(client)
    with factory() as db:
        assert db.scalar(select(Session).where(Session.user_id==user_id))
        bootstrap(db,'admin@example.test','TestAdmin','new-test-admin-password')
        assert db.scalar(select(Session).where(Session.user_id==user_id)) is None
        assert not db.get(User,user_id).mfa_confirmed
    assert client.get('/api/me').status_code==401
