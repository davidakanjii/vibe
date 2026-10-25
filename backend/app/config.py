from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
class Settings(BaseSettings):
    database_url: str='sqlite:///./vibesync.db'
    app_origin: str='http://localhost:3000'
    environment: str='development'
    paystack_secret_key: str=''
    livekit_api_key: str=''
    livekit_api_secret: str=''
    livekit_url: str=''
    mfa_encryption_key: str=''
    redis_url: str='redis://localhost:6379/0'
    model_config=SettingsConfigDict(env_file='.env',extra='ignore')
settings=Settings()
engine=create_engine(settings.database_url,connect_args={'check_same_thread':False} if settings.database_url.startswith('sqlite') else {},pool_pre_ping=True)
SessionLocal=sessionmaker(engine,expire_on_commit=False)
def db_session():
    with SessionLocal() as db: yield db
