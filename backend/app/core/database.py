import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings
from sqlalchemy.pool import StaticPool
if settings.database_url.startswith('sqlite:///'):
    db_path = settings.database_url.replace('sqlite:///', '')
    if db_path and db_path != ':memory:':
        Path(os.path.dirname(os.path.abspath(db_path))).mkdir(parents=True, exist_ok=True)
connect_args = {'check_same_thread': False} if settings.database_url.startswith('sqlite') else {}
pool_kwargs = {'poolclass': StaticPool} if ':memory:' in settings.database_url else {'pool_pre_ping': True}
engine = create_engine(settings.database_url, connect_args=connect_args, **pool_kwargs)
if settings.database_url.startswith('sqlite'):

    @event.listens_for(engine, 'connect')
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.close()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db() -> None:
    from backend.app.models import entities
    Base.metadata.create_all(bind=engine)
