from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
class Register(BaseModel):
    email:str=Field(min_length=5,max_length=254)
    password:str=Field(min_length=12,max_length=128)
    display_name:str=Field(min_length=1,max_length=80)
    marketing_consent:bool=False
    @field_validator('email')
    @classmethod
    def email_valid(cls,v):
        if '@' not in v or '.' not in v.split('@')[-1]: raise ValueError('Valid email required')
        return v.strip().lower()
class Login(BaseModel):
    email:str
    password:str=Field(max_length=128)
    otp:str|None=Field(default=None,pattern='^[0-9]{6}$')
    @field_validator('otp',mode='before')
    @classmethod
    def optional_otp(cls,value):
        if isinstance(value,str): return value.strip() or None
        return value
class OrganisationIn(BaseModel): name:str=Field(min_length=2,max_length=120)
class EventIn(BaseModel):
    organisation_id:str
    title:str=Field(min_length=3,max_length=160)
    description:str=Field(default='',max_length=5000)
    venue:str=Field(default='',max_length=160)
    city:str=Field(default='',max_length=100)
    genre:str=Field(default='',max_length=80)
    starts_at:datetime
    ends_at:datetime
    capacity:int=Field(default=100,ge=1,le=100000)
    price_minor:int=Field(default=0,ge=0,le=100000000)
    currency:str=Field(default='NGN',pattern='^[A-Z]{3}$')
    @model_validator(mode='after')
    def dates(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None: raise ValueError('Timezone required')
        if self.ends_at<=self.starts_at: raise ValueError('End must follow start')
        return self
class ChannelIn(BaseModel):
    name:str=Field(min_length=1,max_length=80)
    genre:str=Field(default='',max_length=80)
    dj_user_id:str|None=None
class PostIn(BaseModel):
    body:str=Field(min_length=1,max_length=3000)
    event_id:str|None=None
class AssignmentIn(BaseModel):
    user_id:str
    channel_id:str
    role:str=Field(pattern='^(dj|hypeman)$')
class BookingIn(BaseModel):
    provider_id:str
    category:str=Field(pattern='^(host|usher|performer|brand_ambassador)$')
    starts_at:datetime
class StateIn(BaseModel): status:str
class LicenceIn(BaseModel):
    expires_at:datetime
    max_channels:int=Field(ge=1,le=32)
    max_listeners:int=Field(ge=1,le=100000)
class PreferencesIn(BaseModel): marketing_email:bool
class ReportIn(BaseModel):
    target_type:str=Field(pattern='^(post|user|event|booking)$')
    target_id:str=Field(min_length=1,max_length=36)
    reason:str=Field(min_length=5,max_length=2000)
class MicRoutingIn(BaseModel):
    channel_ids:list[str]=Field(max_length=32)
    muted:bool=True
    push_to_talk:bool=True
    active:bool=False
    gain:float=Field(default=1.0,ge=0,le=4,allow_inf_nan=False)
    broadcast_all:bool=False

class AccountStatusIn(BaseModel): suspended:bool
class MfaEnrollStart(BaseModel):
    email:str=Field(max_length=254)
    password:str=Field(max_length=128)
class MfaEnrollConfirm(BaseModel): otp:str=Field(pattern='^[0-9]{6}$')
