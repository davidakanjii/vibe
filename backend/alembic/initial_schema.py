from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    email: Mapped[str]=mapped_column(String(254),unique=True)
    display_name: Mapped[str]=mapped_column(String(80))
    password_hash: Mapped[str]=mapped_column(Text)
    suspended: Mapped[bool]=mapped_column(Boolean,default=False)
    platform_admin: Mapped[bool]=mapped_column(Boolean,default=False)
    marketing_consent: Mapped[bool]=mapped_column(Boolean,default=False)
class Session(Base):
    __tablename__='sessions'
    token_hash: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    csrf: Mapped[str]=mapped_column(String(64))
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
class Organisation(Base):
    __tablename__='organisations'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    name: Mapped[str]=mapped_column(String(120))
class Membership(Base):
    __tablename__='memberships'
    organisation_id: Mapped[str]=mapped_column(ForeignKey('organisations.id'),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    role: Mapped[str]=mapped_column(String(40),primary_key=True)
class Licence(Base):
    __tablename__='licences'
    organisation_id: Mapped[str]=mapped_column(ForeignKey('organisations.id'),primary_key=True)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    max_channels: Mapped[int]=mapped_column(Integer,default=4)
    max_listeners: Mapped[int]=mapped_column(Integer,default=100)
class Event(Base):
    __tablename__='events'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organisation_id: Mapped[str]=mapped_column(ForeignKey('organisations.id'))
    title: Mapped[str]=mapped_column(String(160))
    description: Mapped[str]=mapped_column(Text,default='')
    venue: Mapped[str]=mapped_column(String(160),default='')
    city: Mapped[str]=mapped_column(String(100),default='')
    genre: Mapped[str]=mapped_column(String(80),default='')
    starts_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    status: Mapped[str]=mapped_column(String(20),default='draft')
    capacity: Mapped[int]=mapped_column(Integer,default=100)
    price_minor: Mapped[int]=mapped_column(Integer,default=0)
    currency: Mapped[str]=mapped_column(String(3),default='NGN')
class Channel(Base):
    __tablename__='channels'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'))
    name: Mapped[str]=mapped_column(String(80))
    genre: Mapped[str]=mapped_column(String(80),default='')
    dj_user_id: Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True)
class Assignment(Base):
    __tablename__='assignments'
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    channel_id: Mapped[str]=mapped_column(ForeignKey('channels.id'),primary_key=True)
    role: Mapped[str]=mapped_column(String(20),primary_key=True)
class Attendance(Base):
    __tablename__='attendance'
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
class Post(Base):
    __tablename__='posts'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    author_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    body: Mapped[str]=mapped_column(Text)
    event_id: Mapped[str|None]=mapped_column(ForeignKey('events.id'),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    hidden: Mapped[bool]=mapped_column(Boolean,default=False)
class Reaction(Base):
    __tablename__='reactions'
    post_id: Mapped[str]=mapped_column(ForeignKey('posts.id'),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
class Follow(Base):
    __tablename__='follows'
    follower_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    followed_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
class Booking(Base):
    __tablename__='bookings'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    requester_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    provider_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    category: Mapped[str]=mapped_column(String(40))
    starts_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    status: Mapped[str]=mapped_column(String(20),default='requested')
class Payment(Base):
    __tablename__='payments'
    reference: Mapped[str]=mapped_column(String(80),primary_key=True,default=uid)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'))
    amount: Mapped[int]=mapped_column(Integer)
    currency: Mapped[str]=mapped_column(String(3))
    status: Mapped[str]=mapped_column(String(20),default='pending')
class Audit(Base):
    __tablename__='audit'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    actor_id: Mapped[str|None]=mapped_column(String(36),nullable=True)
    action: Mapped[str]=mapped_column(String(100))
    resource_id: Mapped[str]=mapped_column(String(100))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Report(Base):
    __tablename__='reports'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    reporter_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    target_type: Mapped[str]=mapped_column(String(20))
    target_id: Mapped[str]=mapped_column(String(36))
    reason: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(20),default='open')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
