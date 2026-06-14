from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from iknowfirst.db.models import Base

def make_session_factory(database_url: str, create: bool = True):
    engine = create_engine(database_url, pool_pre_ping=True)
    if create:
        Base.metadata.create_all(engine)
    return sessionmaker(engine)
