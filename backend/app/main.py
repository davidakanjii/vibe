import hashlib, hmac, json, time
from collections import defaultdict, deque
from datetime import timedelta
import httpx, jwt
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session as DB
from sqlalchemy.exc import IntegrityError
from .config import settings, db_session
from .models import *
from .schemas import *
from .security import current_user, issue_session, profile, manager, hasher, utc, require_admin, local_admin_mfa_skip
DUMMY_PASSWORD_HASH=hasher.hash('constant-time-invalid-account-password')
app=FastAPI(title='VibeSync API',version='0.1.0')
D=Depends(db_session); U=Depends(current_user)
def public(row): return {c.name:getattr(row,c.name) for c in row.__table__.columns}
def event_get(db,id):
    row=db.get(Event,id)
    if not row: raise HTTPException(404,'Event not found')
    return row
def audit(db,user,action,id): db.add(Audit(actor_id=user.id,action=action,resource_id=id))
def licensed(db,event):
    licence=db.get(Licence,event.organisation_id)
    if not licence or utc(licence.expires_at)<=now(): raise HTTPException(403,'Active organiser licence required')
    return licence
# Single-process development limiter. Production uses Redis shared counters and fails closed.
_attempts=defaultdict(deque)
def throttle(request,key):
    identity=f'{key}:{request.client.host if request.client else "unknown"}'
    if settings.environment=='production':
        from redis import Redis
        try:
            redis=Redis.from_url(settings.redis_url,socket_timeout=2)
            bucket=f'auth:{identity}:{int(time.time())//60}'
            count=redis.incr(bucket); redis.expire(bucket,65)
        except Exception: raise HTTPException(503,'Authentication temporarily unavailable')
        if count>10: raise HTTPException(429,'Try again later')
    else:
        queue=_attempts[identity]; current=time.monotonic()
        while queue and queue[0]<current-60: queue.popleft()
        if len(queue)>=20: raise HTTPException(429,'Try again later')
        queue.append(current)
def auth_origin(request):
    if request.headers.get('origin')!=settings.app_origin: raise HTTPException(403,'Invalid origin')
@app.get('/health')
def health(db:DB=D):
    db.execute(select(1)); return {'status':'ok'}
@app.post('/api/auth/register',status_code=201)
def register(data:Register,request:Request,response:Response,db:DB=D):
    auth_origin(request); throttle(request,'register')
    user=User(email=data.email,display_name=data.display_name,password_hash=hasher.hash(data.password),marketing_consent=data.marketing_consent)
    db.add(user)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409,'Email already registered')
    return issue_session(db,user,response)
@app.post('/api/auth/login')
def login(data:Login,request:Request,response:Response,db:DB=D):
    auth_origin(request); throttle(request,'login')
    identity=data.email.strip().lower()
    user=db.scalar(select(User).where((func.lower(User.email)==identity)|(func.lower(User.username)==identity)))
    try: valid=hasher.verify(user.password_hash if user else DUMMY_PASSWORD_HASH,data.password)
    except Exception: valid=False
    if not valid or user.suspended: raise HTTPException(401,'Invalid credentials')
    verified=False
    if user.platform_admin and local_admin_mfa_skip(request):
        audit(db,user,'admin.login.local_mfa_skip',user.id)
    elif user.platform_admin:
        if not user.mfa_confirmed: raise HTTPException(403,'MFA enrollment required')
        from .mfa import verify_fresh_totp
        verified=verify_fresh_totp(db,user,data.otp)
    return issue_session(db,user,response,mfa_verified=verified)
@app.get('/api/auth/me')
@app.get('/api/me')
def me(request:Request,user:User=U): return {'user':profile(user),'csrf_token':request.state.session.csrf,'mfa_verified':request.state.session.mfa_verified,'development_mfa_skip':bool(user.platform_admin and local_admin_mfa_skip(request))}
@app.post('/api/auth/logout',status_code=204)
def logout(request:Request,response:Response,user:User=U,db:DB=D):
    db.delete(db.get(Session,request.state.session.token_hash)); db.commit()
    response.delete_cookie('vs_session'); response.delete_cookie('vs_csrf')
@app.get('/api/organisations')
def organisations(user:User=U,db:DB=D):
    return [public(o) for o in db.scalars(select(Organisation).join(Membership).where(Membership.user_id==user.id)).unique()]
@app.post('/api/organisations',status_code=201)
def organisation_create(data:OrganisationIn,user:User=U,db:DB=D):
    org=Organisation(name=data.name); db.add(org); db.flush()
    db.add(Membership(organisation_id=org.id,user_id=user.id,role='organiser')); audit(db,user,'organisation.create',org.id); db.commit(); return public(org)
@app.get('/api/events')
def events(city:str|None=None,genre:str|None=None,db:DB=D):
    query=select(Event).where(Event.status.in_(['published','live'])).order_by(Event.starts_at).limit(100)
    if city: query=query.where(Event.city.ilike(city))
    if genre: query=query.where(Event.genre.ilike(genre))
    return [public(e) for e in db.scalars(query)]
@app.get('/api/organisations/{id}/events')
def managed_events(id:str,user:User=U,db:DB=D):
    manager(db,user,id); return [public(e) for e in db.scalars(select(Event).where(Event.organisation_id==id))]
@app.post('/api/events',status_code=201)
def event_create(data:EventIn,user:User=U,db:DB=D):
    manager(db,user,data.organisation_id); event=Event(**data.model_dump()); db.add(event); db.flush(); audit(db,user,'event.create',event.id); db.commit(); return public(event)
@app.get('/api/events/{id}')
def event_detail(id:str,db:DB=D):
    event=event_get(db,id)
    if event.status not in ['published','live','closed']: raise HTTPException(404,'Event not found')
    return {**public(event),'channels':[public(c) for c in db.scalars(select(Channel).where(Channel.event_id==id))]}
@app.put('/api/events/{id}')
def event_edit(id:str,data:EventIn,user:User=U,db:DB=D):
    event=event_get(db,id); manager(db,user,event.organisation_id)
    if data.organisation_id!=event.organisation_id: raise HTTPException(403,'Cannot move event between tenants')
    if event.status!='draft': raise HTTPException(409,'Only drafts can be edited')
    for k,v in data.model_dump().items(): setattr(event,k,v)
    audit(db,user,'event.edit',id); db.commit(); return public(event)
@app.post('/api/events/{id}/status')
def event_status(id:str,data:StateIn,user:User=U,db:DB=D):
    event=event_get(db,id); manager(db,user,event.organisation_id)
    transitions={'draft':['published','cancelled'],'published':['live','cancelled'],'live':['closed','cancelled']}
    if data.status not in transitions.get(event.status,[]): raise HTTPException(409,'Invalid event transition')
    if data.status in ['published','live']: licensed(db,event)
    if data.status=='live' and not utc(event.starts_at)<=now()<utc(event.ends_at): raise HTTPException(409,'Outside event schedule')
    event.status=data.status; audit(db,user,'event.'+data.status,id); db.commit(); return public(event)
@app.get('/api/events/{id}/channels')
def channels(id:str,db:DB=D):
    event=event_get(db,id)
    if event.status not in ['published','live','closed']: raise HTTPException(404,'Event not found')
    return [public(c) for c in db.scalars(select(Channel).where(Channel.event_id==id))]
@app.post('/api/events/{id}/channels',status_code=201)
def channel_create(id:str,data:ChannelIn,user:User=U,db:DB=D):
    event=db.scalar(select(Event).where(Event.id==id).with_for_update())
    if not event: raise HTTPException(404,'Event not found')
    manager(db,user,event.organisation_id); licence=licensed(db,event)
    count=db.scalar(select(func.count()).select_from(Channel).where(Channel.event_id==id))
    if count>=licence.max_channels: raise HTTPException(409,'Licensed channel limit reached')
    if data.dj_user_id and not db.get(User,data.dj_user_id): raise HTTPException(422,'DJ account not found')
    row=Channel(event_id=id,**data.model_dump()); db.add(row); db.flush()
    if data.dj_user_id: db.add(Assignment(event_id=id,user_id=data.dj_user_id,channel_id=row.id,role='dj'))
    audit(db,user,'channel.create',row.id); db.commit(); return public(row)
@app.post('/api/events/{id}/assignments',status_code=201)
def assign(id:str,data:AssignmentIn,user:User=U,db:DB=D):
    event=event_get(db,id); manager(db,user,event.organisation_id); channel=db.get(Channel,data.channel_id)
    if not channel or channel.event_id!=id or not db.get(User,data.user_id): raise HTTPException(422,'Invalid event channel or user')
    row=Assignment(event_id=id,**data.model_dump())
    if db.get(Assignment,(id,data.user_id,data.channel_id,data.role)): return {'status':'assigned'}
    db.add(row); audit(db,user,'assignment.create',id); db.commit(); return {'status':'assigned'}
@app.post('/api/events/{id}/join')
def join(id:str,user:User=U,db:DB=D):
    event=db.scalar(select(Event).where(Event.id==id).with_for_update())
    if not event or event.status not in ['published','live']: raise HTTPException(404,'Event unavailable')
    licensed(db,event)
    if event.price_minor: raise HTTPException(402,'Verified ticket purchase required')
    if not db.get(Attendance,(id,user.id)):
        if db.scalar(select(func.count()).select_from(Attendance).where(Attendance.event_id==id))>=event.capacity: raise HTTPException(409,'Event is full')
        db.add(Attendance(event_id=id,user_id=user.id)); db.commit()
    return {'status':'joined','event_id':id}
@app.post('/api/events/{id}/channels/{channel_id}/token')
def stream_token(id:str,channel_id:str,publish:bool=False,user:User=U,db:DB=D):
    event=event_get(db,id); licence=licensed(db,event); channel=db.get(Channel,channel_id)
    if event.status!='live' or not channel or channel.event_id!=id or not utc(event.starts_at)<=now()<utc(event.ends_at): raise HTTPException(403,'Channel is not live')
    assignment=db.scalar(select(Assignment).where(Assignment.event_id==id,Assignment.channel_id==channel_id,Assignment.user_id==user.id,Assignment.role=='dj'))
    if publish and not assignment: raise HTTPException(403,'Channel publishing assignment required')
    if not publish and not db.get(Attendance,(id,user.id)): raise HTTPException(403,'Join event first')
    if not all([settings.livekit_api_key,settings.livekit_api_secret,settings.livekit_url]): raise HTTPException(503,'Live audio infrastructure is not configured')
    # Listener capacity must be enforced by the SFU room configuration; token does not claim occupancy.
    exp=int(min((now()+timedelta(minutes=5)).timestamp(),utc(event.ends_at).timestamp(),utc(licence.expires_at).timestamp()))
    token=jwt.encode({'iss':settings.livekit_api_key,'sub':user.id,'nbf':int(now().timestamp()),'exp':exp,'video':{'roomJoin':True,'room':f'event-{id}-channel-{channel_id}','canPublish':publish,'canPublishSources':['microphone'] if publish else [],'canSubscribe':True,'canPublishData':False}},settings.livekit_api_secret,algorithm='HS256')
    audit(db,user,'stream.publish' if publish else 'stream.listen',channel_id); db.commit()
    return {'token':token,'url':settings.livekit_url,'expires_at':exp,'max_participants':licence.max_listeners}
@app.get('/api/feed')
def feed(db:DB=D):
    result=[]
    for post in db.scalars(select(Post).where(Post.hidden==False).order_by(Post.created_at.desc()).limit(50)):
        author=db.get(User,post.author_id)
        result.append({**public(post),'author':{'id':author.id,'display_name':author.display_name},'reaction_count':db.scalar(select(func.count()).select_from(Reaction).where(Reaction.post_id==post.id))})
    return result
@app.post('/api/feed',status_code=201)
def post_create(data:PostIn,user:User=U,db:DB=D):
    if data.event_id:
        event=event_get(db,data.event_id)
        if event.status not in ['published','live','closed']: raise HTTPException(404,'Event not found')
    row=Post(author_id=user.id,**data.model_dump()); db.add(row); db.commit(); return public(row)
@app.post('/api/posts/{id}/reactions')
def react(id:str,user:User=U,db:DB=D):
    post=db.get(Post,id)
    if not post or post.hidden: raise HTTPException(404,'Post not found')
    if not db.get(Reaction,(id,user.id)): db.add(Reaction(post_id=id,user_id=user.id)); db.commit()
    return {'status':'reacted'}
@app.delete('/api/posts/{id}/reactions',status_code=204)
def unreact(id:str,user:User=U,db:DB=D):
    row=db.get(Reaction,(id,user.id))
    if row: db.delete(row); db.commit()
@app.post('/api/users/{id}/follow')
def follow(id:str,user:User=U,db:DB=D):
    if id==user.id or not db.get(User,id): raise HTTPException(422,'Invalid follow target')
    if not db.get(Follow,(user.id,id)): db.add(Follow(follower_id=user.id,followed_id=id)); db.commit()
    return {'status':'following'}
@app.delete('/api/users/{id}/follow',status_code=204)
def unfollow(id:str,user:User=U,db:DB=D):
    row=db.get(Follow,(user.id,id))
    if row: db.delete(row); db.commit()
@app.post('/api/bookings',status_code=201)
def book(data:BookingIn,user:User=U,db:DB=D):
    verified=db.scalar(select(Membership).where(Membership.user_id==data.provider_id,Membership.role=='verified_service_provider'))
    if not verified: raise HTTPException(403,'Verified professional provider required')
    if data.starts_at.tzinfo is None or data.starts_at<=now(): raise HTTPException(422,'Future timezone-aware schedule required')
    row=Booking(requester_id=user.id,**data.model_dump()); db.add(row); db.commit(); return public(row)
@app.get('/api/bookings')
def bookings(user:User=U,db:DB=D): return [public(b) for b in db.scalars(select(Booking).where((Booking.requester_id==user.id)|(Booking.provider_id==user.id)))]
@app.post('/api/bookings/{id}/status')
def booking_state(id:str,data:StateIn,user:User=U,db:DB=D):
    row=db.get(Booking,id)
    if not row or user.id not in [row.requester_id,row.provider_id]: raise HTTPException(404,'Booking not found')
    allowed=(data.status=='accepted' and user.id==row.provider_id and row.status=='requested') or (data.status=='cancelled' and row.status in ['requested','accepted'])
    if not allowed: raise HTTPException(409,'Invalid booking transition')
    row.status=data.status; db.commit(); return public(row)
@app.put('/api/admin/organisations/{id}/licence')
def grant_licence(id:str,data:LicenceIn,user:User=Depends(require_admin),db:DB=D):
    if not db.get(Organisation,id): raise HTTPException(404,'Organisation not found')
    if data.expires_at.tzinfo is None or data.expires_at<=now(): raise HTTPException(422,'Future timezone-aware expiry required')
    row=db.get(Licence,id)
    if not row: row=Licence(organisation_id=id); db.add(row)
    row.expires_at=data.expires_at; row.max_channels=data.max_channels; row.max_listeners=data.max_listeners
    audit(db,user,'admin.licence.grant',id); db.commit(); return public(row)
@app.get('/api/admin/metrics')
def metrics(user:User=Depends(require_admin),db:DB=D):
    return {'registered_users':db.scalar(select(func.count()).select_from(User)),'live_events':db.scalar(select(func.count()).select_from(Event).where(Event.status=='live')),'posts':db.scalar(select(func.count()).select_from(Post)),'verified_ticket_revenue_minor':db.scalar(select(func.coalesce(func.sum(Payment.amount),0)).where(Payment.status=='success',Payment.currency=='NGN'))}
@app.post('/api/payments/checkout')
def checkout(data:dict,user:User=U,db:DB=D):
    event=event_get(db,str(data.get('event_id','')))
    if event.status not in ['published','live'] or event.price_minor<=0: raise HTTPException(409,'Ticket is unavailable')
    if not settings.paystack_secret_key: raise HTTPException(503,'Payments not configured')
    payment=Payment(user_id=user.id,event_id=event.id,amount=event.price_minor,currency=event.currency); db.add(payment); db.commit()
    try:
        with httpx.Client(timeout=15) as client:
            response=client.post('https://api.paystack.co/transaction/initialize',headers={'Authorization':'Bearer '+settings.paystack_secret_key},json={'email':user.email,'amount':payment.amount,'currency':payment.currency,'reference':payment.reference})
            response.raise_for_status(); payload=response.json()
        if not payload.get('status'): raise ValueError()
        return {'reference':payment.reference,'authorization_url':payload['data']['authorization_url']}
    except Exception: raise HTTPException(502,'Payment provider unavailable')
@app.post('/api/payments/webhook')
async def webhook(request:Request,db:DB=D):
    if not settings.paystack_secret_key: raise HTTPException(503,'Payments not configured')
    body=await request.body()
    if len(body)>65536: raise HTTPException(413,'Payload too large')
    expected=hmac.new(settings.paystack_secret_key.encode(),body,hashlib.sha512).hexdigest()
    if not hmac.compare_digest(expected,request.headers.get('x-paystack-signature','')): raise HTTPException(401,'Invalid signature')
    try: payload=json.loads(body)
    except ValueError: raise HTTPException(400,'Invalid JSON')
    if payload.get('event')!='charge.success': return {'received':True}
    reference=str(payload.get('data',{}).get('reference',''))
    payment=db.scalar(select(Payment).where(Payment.reference==reference).with_for_update())
    if not payment: raise HTTPException(404,'Unknown payment')
    if payment.status=='success': return {'received':True}
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            verified=await client.get('https://api.paystack.co/transaction/verify/'+payment.reference,headers={'Authorization':'Bearer '+settings.paystack_secret_key}); verified.raise_for_status(); details=verified.json()['data']
        except Exception: raise HTTPException(502,'Payment verification unavailable')
    if details.get('status')!='success' or details.get('reference')!=payment.reference or details.get('amount')!=payment.amount or details.get('currency')!=payment.currency: raise HTTPException(409,'Verified payment does not match order')
    event=db.scalar(select(Event).where(Event.id==payment.event_id).with_for_update())
    if not db.get(Attendance,(event.id,payment.user_id)):
        count=db.scalar(select(func.count()).select_from(Attendance).where(Attendance.event_id==event.id))
        if count>=event.capacity:
            payment.status='refund_required'; db.commit(); return {'received':True,'status':'refund_required'}
        db.add(Attendance(event_id=event.id,user_id=payment.user_id))
    payment.status='success'; db.add(Audit(actor_id=payment.user_id,action='payment.verified',resource_id=payment.reference)); db.commit(); return {'received':True}
@app.get('/api/tickets')
def tickets(user:User=U,db:DB=D):
    return [{'id':a.event_id+':'+a.user_id,'event_id':a.event_id,'status':'confirmed'} for a in db.scalars(select(Attendance).where(Attendance.user_id==user.id))]
@app.patch('/api/me/preferences')
def preferences(data:PreferencesIn,user:User=U,db:DB=D):
    user.marketing_consent=data.marketing_email; audit(db,user,'marketing.opt_in' if data.marketing_email else 'marketing.opt_out',user.id); db.commit(); return profile(user)
@app.post('/api/reports',status_code=201)
def report(data:ReportIn,user:User=U,db:DB=D):
    model={'post':Post,'user':User,'event':Event,'booking':Booking}[data.target_type]
    target=db.get(model,data.target_id)
    if not target: raise HTTPException(404,'Target not found')
    if data.target_type=='booking' and user.id not in [target.requester_id,target.provider_id]: raise HTTPException(404,'Target not found')
    if data.target_type=='event' and target.status=='draft': raise HTTPException(404,'Target not found')
    row=Report(reporter_id=user.id,**data.model_dump()); db.add(row); db.commit(); return {'id':row.id,'status':row.status}


@app.put('/api/events/{id}/mic-routing')
def mic_routing(id:str,data:MicRoutingIn,user:User=U,db:DB=D):
    event=event_get(db,id); licensed(db,event)
    if event.status!='live' or not utc(event.starts_at)<=now()<utc(event.ends_at): raise HTTPException(403,'Event is not live')
    # Routing ownership comes exclusively from assigned hypeman channels.
    assignments=list(db.scalars(select(Assignment).where(Assignment.event_id==id,Assignment.user_id==user.id,Assignment.role=='hypeman')))
    if not assignments: raise HTTPException(403,'Hypeman assignment required')
    permitted={a.channel_id for a in assignments}
    selected=set(data.channel_ids)
    if len(selected)!=len(data.channel_ids): raise HTTPException(422,'Duplicate channel routes')
    if not selected<=permitted: raise HTTPException(403,'Channel is not assigned to this hypeman')
    if data.active and not selected and not data.broadcast_all: raise HTTPException(422,'Select at least one channel')
    route=db.get(HypemanRoute,(id,user.id))
    if data.broadcast_all and (not route or not route.allow_broadcast_all): raise HTTPException(403,'Broadcast-all requires operator authorisation')
    channels=list(db.scalars(select(Channel).where(Channel.id.in_(selected or permitted),Channel.event_id==id)))
    zones={c.zone for c in channels}
    if len(zones)!=1: raise HTTPException(403,'Microphone routes must stay within one assigned venue zone')
    zone=next(iter(zones))
    if route and route.zone!=zone: raise HTTPException(403,'Existing microphone identity is scoped to another zone')
    if not route: route=HypemanRoute(event_id=id,user_id=user.id,zone=zone); db.add(route)
    effective=selected
    if data.broadcast_all:
        effective={c.id for c in db.scalars(select(Channel).where(Channel.event_id==id,Channel.zone==zone))}
    route.channel_ids=json.dumps(sorted(effective)); route.muted=data.muted; route.push_to_talk=data.push_to_talk; route.active=data.active; route.gain=data.gain; route.broadcast_all=data.broadcast_all
    audit(db,user,'microphone.routing.configure',id); db.commit()
    return {'event_id':id,'zone':zone,'channel_ids':sorted(effective),'muted':route.muted,'push_to_talk':route.push_to_talk,'active':route.active,'gain':route.gain,'broadcast_all':route.broadcast_all,'transport_ready':False,'message':'Routing saved. Live microphone delivery requires the server mixer transport adapter.'}

@app.get('/api/admin/users')
def admin_users(user:User=Depends(require_admin),db:DB=D):
    return [{**profile(row),'suspended':row.suspended} for row in db.scalars(select(User).order_by(User.email).limit(200))]
@app.put('/api/admin/users/{id}/status')
def admin_account_status(id:str,data:AccountStatusIn,user:User=Depends(require_admin),db:DB=D):
    from sqlalchemy import delete
    target=db.get(User,id)
    if not target: raise HTTPException(404,'User not found')
    if id==user.id: raise HTTPException(409,'Cannot suspend your own privileged account')
    target.suspended=data.suspended
    db.execute(delete(Session).where(Session.user_id==id))
    audit(db,user,'admin.account.suspend' if data.suspended else 'admin.account.reinstate',id); db.commit()
    return {**profile(target),'suspended':target.suspended}

@app.post('/api/auth/mfa/enroll/start')
def mfa_enroll_start(data:MfaEnrollStart,request:Request,response:Response,db:DB=D):
    from secrets import token_urlsafe
    from sqlalchemy import delete
    import pyotp
    from .mfa import decrypt_secret
    auth_origin(request); throttle(request,'mfa-enroll-start')
    identity=data.email.strip().lower()
    user=db.scalar(select(User).where((func.lower(User.email)==identity)|(func.lower(User.username)==identity)).with_for_update())
    try: valid=hasher.verify(user.password_hash if user else DUMMY_PASSWORD_HASH,data.password)
    except Exception: valid=False
    if not valid or user.suspended or not user.platform_admin: raise HTTPException(401,'Invalid enrollment credentials')
    if user.mfa_confirmed: raise HTTPException(409,'MFA already enrolled; contact a protected operator for recovery')
    if not user.mfa_secret_encrypted: raise HTTPException(403,'Operator MFA setup required')
    secret=decrypt_secret(user.mfa_secret_encrypted)
    token=token_urlsafe(48)
    db.execute(delete(MfaEnrollment).where(MfaEnrollment.user_id==user.id))
    db.add(MfaEnrollment(token_hash=hashlib.sha256(token.encode()).hexdigest(),user_id=user.id,expires_at=now()+timedelta(minutes=5)))
    audit(db,user,'mfa.enrollment.start',user.id); db.commit()
    response.set_cookie('vs_mfa_enrollment',token,httponly=True,secure=settings.environment=='production',samesite='strict',max_age=300,path='/api/auth/mfa/enroll')
    response.headers['Cache-Control']='no-store'
    return {'secret':secret,'otpauth_uri':pyotp.TOTP(secret).provisioning_uri(name=user.email,issuer_name='VibeSync'),'expires_in':300}
@app.post('/api/auth/mfa/enroll/confirm')
def mfa_enroll_confirm(data:MfaEnrollConfirm,request:Request,response:Response,db:DB=D):
    from sqlalchemy import delete
    from .mfa import verify_fresh_totp
    auth_origin(request); throttle(request,'mfa-enroll-confirm')
    token=request.cookies.get('vs_mfa_enrollment','')
    challenge=db.scalar(select(MfaEnrollment).where(MfaEnrollment.token_hash==hashlib.sha256(token.encode()).hexdigest()).with_for_update())
    if not challenge or utc(challenge.expires_at)<=now(): raise HTTPException(401,'Enrollment challenge expired; start again')
    user=db.scalar(select(User).where(User.id==challenge.user_id).with_for_update())
    if not user or user.suspended or not user.platform_admin or user.mfa_confirmed: raise HTTPException(403,'Enrollment unavailable')
    verify_fresh_totp(db,user,data.otp)
    user.mfa_confirmed=True
    db.execute(delete(MfaEnrollment).where(MfaEnrollment.user_id==user.id))
    db.execute(delete(Session).where(Session.user_id==user.id))
    audit(db,user,'mfa.enrollment.confirm',user.id)
    result=issue_session(db,user,response,mfa_verified=True)
    response.delete_cookie('vs_mfa_enrollment',path='/api/auth/mfa/enroll')
    response.headers['Cache-Control']='no-store'
    return result
@app.get('/api/admin/organisations')
def admin_organisations(user:User=Depends(require_admin),db:DB=D):
    return [{**public(row),'licence':public(db.get(Licence,row.id)) if db.get(Licence,row.id) else None} for row in db.scalars(select(Organisation).order_by(Organisation.name).limit(200))]
@app.get('/api/admin/audit')
def admin_audit(limit:int=50,user:User=Depends(require_admin),db:DB=D):
    if not 1<=limit<=200: raise HTTPException(422,'Limit must be 1–200')
    return [public(row) for row in db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(limit))]
@app.middleware('http')
async def private_response_headers(request:Request,call_next):
    response=await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control']='no-store'
        response.headers['Pragma']='no-cache'
        response.headers['Vary']='Cookie'
    response.headers['X-Content-Type-Options']='nosniff'
    return response
