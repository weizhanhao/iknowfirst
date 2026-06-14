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

def test_existing_ids_and_add_new(repo):
    assert repo.existing_external_ids(["a", "b"]) == set()
    repo.add_new("youtube", "a", "标题A", "http://y/a", author=None, published_at=None, status="seen")
    assert repo.existing_external_ids(["a", "b"]) == {"a"}

def test_set_status_and_fetch_matched(repo):
    item = repo.add_new("youtube", "c", "标题C", "http://y/c", author=None, published_at=None, status="matched")
    matched = repo.items_by_status("matched")
    assert [i.external_id for i in matched] == ["c"]
    repo.set_status(item.id, "analyzed")
    assert repo.items_by_status("matched") == []
