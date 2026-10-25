import os
os.environ['DATABASE_URL']='sqlite://'
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app, _attempts
from app.config import db_session
from app.models import Base, User, Licence, Session, Attendance, Payment, Event, now

@pytest.fixture
def setup(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings,'app_origin','http://localhost:3000')
    monkeypatch.setattr(settings,'environment','development')
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine); factory=sessionmaker(engine,expire_on_commit=False)
    def override():
        with factory() as db: yield db
    app.dependency_overrides[db_session]=override; _attempts.clear()
    with TestClient(app) as client: yield client,factory
    app.dependency_overrides.clear(); engine.dispose()
def signup(client,email='alice@example.test'):
    result=client.post('/api/auth/register',headers={'origin':'http://localhost:3000'},json={'email':email,'password':'a-long-password-458','display_name':'Alice'})
    assert result.status_code==201,result.text
    return {'origin':'http://localhost:3000','x-csrf-token':result.json()['csrf_token']},result.json()['user']
def event_data(org):
    return {'organisation_id':org,'title':'Test event','starts_at':(now()-timedelta(minutes=1)).isoformat(),'ends_at':(now()+timedelta(hours=2)).isoformat()}
def test_sessions_hashed_and_csrf_enforced(setup):
    client,factory=setup; headers,user=signup(client)
    with factory() as db:
        row=db.scalar(select(Session)); assert row.token_hash!=client.cookies['vs_session']; assert len(row.token_hash)==64
        assert db.get(User,user['id']).password_hash.startswith('$argon2')
    assert client.post('/api/organisations',json={'name':'Tenant'}).status_code==403
    assert client.post('/api/organisations',headers={**headers,'origin':'https://evil.test'},json={'name':'Tenant'}).status_code==403
    assert client.post('/api/organisations',headers=headers,json={'name':'Tenant'}).status_code==201
    assert client.post('/api/auth/logout',headers=headers).status_code==204
    assert client.get('/api/me').status_code==401

def test_tenant_isolation_and_licence_gating(setup):
    client,factory=setup; headers,user=signup(client)
    org=client.post('/api/organisations',headers=headers,json={'name':'Tenant A'}).json()['id']
    event=client.post('/api/events',headers=headers,json=event_data(org)).json()
    assert client.get('/api/events/'+event['id']).status_code==404
    assert client.post('/api/events/'+event['id']+'/status',headers=headers,json={'status':'published'}).status_code==403
    with factory() as db: db.add(Licence(organisation_id=org,expires_at=now()+timedelta(days=1),max_channels=1,max_listeners=10)); db.commit()
    path='/api/events/'+event['id']
    assert client.post(path+'/channels',headers=headers,json={'name':'DJ One'}).status_code==201
    assert client.post(path+'/channels',headers=headers,json={'name':'DJ Two'}).status_code==409
    assert client.post(path+'/status',headers=headers,json={'status':'published'}).status_code==200
    assert len(client.get('/api/events').json())==1
    headers2,_=signup(client,'bob@example.test')
    assert client.post(path+'/status',headers=headers2,json={'status':'live'}).status_code==403
    assert client.post('/api/events',headers=headers2,json=event_data(org)).status_code==403

def test_reactions_unique_and_companionship_disabled(setup):
    client,_=setup; headers,user=signup(client)
    post=client.post('/api/feed',headers=headers,json={'body':'My first post'}).json()
    for _ in range(2): assert client.post('/api/posts/'+post['id']+'/reactions',headers=headers).status_code==200
    assert client.get('/api/feed').json()[0]['reaction_count']==1
    assert client.post('/api/bookings',headers=headers,json={'provider_id':user['id'],'category':'companionship','starts_at':(now()+timedelta(days=2)).isoformat()}).status_code==422

def test_stream_denies_cross_event_and_unassigned_publish(setup):
    client,factory=setup; headers,user=signup(client)
    org=client.post('/api/organisations',headers=headers,json={'name':'Tenant'}).json()['id']
    with factory() as db: db.add(Licence(organisation_id=org,expires_at=now()+timedelta(days=1),max_channels=4,max_listeners=10)); db.commit()
    event=client.post('/api/events',headers=headers,json=event_data(org)).json(); path='/api/events/'+event['id']
    channel=client.post(path+'/channels',headers=headers,json={'name':'Secure room'}).json()
    for status in ['published','live']: assert client.post(path+'/status',headers=headers,json={'status':status}).status_code==200
    token_path=path+'/channels/'+channel['id']+'/token'
    assert client.post(token_path+'?publish=true',headers=headers).status_code==403
    assert client.post(token_path,headers=headers).status_code==403
    assert client.post(path+'/join',headers=headers).status_code==200
    assert client.post(token_path,headers=headers).status_code==503
    assert client.post(path+'/channels/wrong/token',headers=headers).status_code==403

def test_webhook_signature_rejected(setup,monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings,'paystack_secret_key','secret')
    client,_=setup
    assert client.post('/api/payments/webhook',json={'event':'charge.success'},headers={'x-paystack-signature':'bad'}).status_code==401
def test_expired_sessions_and_licences(setup):
    client,factory=setup; headers,user=signup(client)
    org=client.post('/api/organisations',headers=headers,json={'name':'Tenant'}).json()['id']
    event=client.post('/api/events',headers=headers,json=event_data(org)).json()
    with factory() as db:
        db.add(Licence(organisation_id=org,expires_at=now()-timedelta(seconds=1),max_channels=1,max_listeners=1)); db.commit()
    assert client.post('/api/events/'+event['id']+'/status',headers=headers,json={'status':'published'}).status_code==403
    with factory() as db:
        session=db.scalar(select(Session)); session.expires_at=now()-timedelta(seconds=1); db.commit()
    assert client.get('/api/me').status_code==401

def test_tickets_preferences_reports(setup):
    client,factory=setup; headers,user=signup(client)
    assert client.get('/api/tickets').json()==[]
    assert client.get('/api/me').json()['user']['marketing_consent'] is False
    assert client.patch('/api/me/preferences',headers=headers,json={'marketing_email':True}).status_code==200
    assert client.get('/api/me').json()['user']['marketing_consent'] is True
    post=client.post('/api/feed',headers=headers,json={'body':'Reportable content'}).json()
    assert client.post('/api/reports',headers=headers,json={'target_type':'post','target_id':post['id'],'reason':'Inappropriate content'}).status_code==201
    assert client.get('/api/admin/metrics').status_code==403

def test_webhook_independent_verification_and_idempotency(setup,monkeypatch):
    import hashlib,hmac,json
    from app.config import settings
    import app.main as main
    monkeypatch.setattr(settings,'paystack_secret_key','test-secret')
    client,factory=setup; headers,user=signup(client)
    org=client.post('/api/organisations',headers=headers,json={'name':'Tenant'}).json()['id']
    event=client.post('/api/events',headers=headers,json=event_data(org)).json()
    with factory() as db:
        db.add(Payment(reference='ref-test',user_id=user['id'],event_id=event['id'],amount=50000,currency='NGN')); db.commit()
    verified={'status':'success','reference':'ref-test','amount':1,'currency':'NGN'}
    calls=[]
    class Reply:
        def raise_for_status(self): pass
        def json(self): return {'data':verified}
    class Provider:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def get(self,*args,**kwargs): calls.append(args); return Reply()
    monkeypatch.setattr(main.httpx,'AsyncClient',Provider)
    body=json.dumps({'event':'charge.success','data':{'reference':'ref-test','amount':50000}}).encode()
    signature=hmac.new(b'test-secret',body,hashlib.sha512).hexdigest()
    def webhook(): return client.post('/api/payments/webhook',content=body,headers={'x-paystack-signature':signature,'content-type':'application/json'})
    assert webhook().status_code==409
    with factory() as db: assert db.get(Payment,'ref-test').status=='pending'; assert db.get(Attendance,(event['id'],user['id'])) is None
    verified['amount']=50000
    assert webhook().status_code==200
    assert webhook().status_code==200
    assert len(calls)==2
    with factory() as db: assert db.get(Payment,'ref-test').status=='success'; assert db.get(Attendance,(event['id'],user['id'])) is not None
    assert len(client.get('/api/tickets').json())==1
def test_attendance_capacity_enforced_and_rejoin_idempotent(setup):
    client,factory=setup; headers,user=signup(client)
    org=client.post('/api/organisations',headers=headers,json={'name':'Tenant'}).json()['id']
    with factory() as db: db.add(Licence(organisation_id=org,expires_at=now()+timedelta(days=1),max_channels=1,max_listeners=1)); db.commit()
    data=event_data(org); data['capacity']=1
    event=client.post('/api/events',headers=headers,json=data).json(); path='/api/events/'+event['id']
    assert client.post(path+'/status',headers=headers,json={'status':'published'}).status_code==200
    assert client.post(path+'/join',headers=headers).status_code==200
    assert client.post(path+'/join',headers=headers).status_code==200
    bob,_=signup(client,'bob@example.test')
    assert client.post(path+'/join',headers=bob).status_code==409

def test_livekit_token_has_exact_room_and_short_expiry(setup,monkeypatch):
    import jwt
    from app.config import settings
    monkeypatch.setattr(settings,'livekit_api_key','test-key')
    monkeypatch.setattr(settings,'livekit_api_secret','a'*40)
    monkeypatch.setattr(settings,'livekit_url','wss://example.test')
    client,factory=setup; headers,user=signup(client)
    org=client.post('/api/organisations',headers=headers,json={'name':'Tenant'}).json()['id']
    with factory() as db: db.add(Licence(organisation_id=org,expires_at=now()+timedelta(days=1),max_channels=1,max_listeners=1)); db.commit()
    event=client.post('/api/events',headers=headers,json=event_data(org)).json(); path='/api/events/'+event['id']
    channel=client.post(path+'/channels',headers=headers,json={'name':'Assigned DJ','dj_user_id':user['id']}).json()
    for status in ['published','live']: assert client.post(path+'/status',headers=headers,json={'status':status}).status_code==200
    response=client.post(path+'/channels/'+channel['id']+'/token?publish=true',headers=headers)
    assert response.status_code==200
    claims=jwt.decode(response.json()['token'],'a'*40,algorithms=['HS256'])
    assert claims['sub']==user['id']
    assert claims['video']['room']==f"event-{event['id']}-channel-{channel['id']}"
    assert claims['video']['canPublishSources']==['microphone']
    assert claims['exp']-claims['nbf']<=300
def test_hypeman_routing_is_event_zone_scoped_and_raw_publish_denied(setup):
    from app.models import Assignment,Channel,HypemanRoute
    client,factory=setup; headers,user=signup(client)
    org=client.post('/api/organisations',headers=headers,json={'name':'Tenant'}).json()['id']
    with factory() as db: db.add(Licence(organisation_id=org,expires_at=now()+timedelta(days=1),max_channels=8,max_listeners=100)); db.commit()
    event=client.post('/api/events',headers=headers,json=event_data(org)).json(); path='/api/events/'+event['id']
    channels=[client.post(path+'/channels',headers=headers,json={'name':name}).json() for name in ['main','other','vip']]
    other_event=client.post('/api/events',headers=headers,json=event_data(org)).json()
    other_channel=client.post('/api/events/'+other_event['id']+'/channels',headers=headers,json={'name':'foreign'}).json()
    for status in ['published','live']: client.post(path+'/status',headers=headers,json={'status':status})
    payload={'channel_ids':[channels[0]['id']],'muted':False,'active':True,'push_to_talk':True,'gain':1,'broadcast_all':False}
    assert client.put(path+'/mic-routing',headers=headers,json=payload).status_code==403
    with factory() as db:
        db.add(Assignment(event_id=event['id'],channel_id=channels[0]['id'],user_id=user['id'],role='hypeman'))
        db.add(Assignment(event_id=event['id'],channel_id=channels[2]['id'],user_id=user['id'],role='hypeman'))
        db.get(Channel,channels[2]['id']).zone='vip'; db.commit()
    result=client.put(path+'/mic-routing',headers=headers,json=payload)
    assert result.status_code==200 and result.json()['transport_ready'] is False
    assert client.post(path+'/channels/'+channels[0]['id']+'/token?publish=true',headers=headers).status_code==403
    for selected in [[other_channel['id']],[channels[1]['id']],[channels[0]['id'],channels[2]['id']]]:
        assert client.put(path+'/mic-routing',headers=headers,json={**payload,'channel_ids':selected}).status_code==403
    assert client.put(path+'/mic-routing',headers=headers,json={**payload,'broadcast_all':True}).status_code==403
    with factory() as db:
        route=db.get(HypemanRoute,(event['id'],user['id'])); route.allow_broadcast_all=True; db.commit()
    result=client.put(path+'/mic-routing',headers=headers,json={**payload,'broadcast_all':True})
    assert result.status_code==200
    assert set(result.json()['channel_ids'])=={channels[0]['id'],channels[1]['id']}
