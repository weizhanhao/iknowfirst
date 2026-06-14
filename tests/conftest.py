import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from iknowfirst.db.models import Base
from iknowfirst.db.repository import ItemRepository


@pytest.fixture
def repo():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return ItemRepository(sessionmaker(engine))
