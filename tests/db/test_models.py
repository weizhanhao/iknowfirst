from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from iknowfirst.db.models import Base, Item, Analysis

def test_item_roundtrip():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        item = Item(source_type="youtube", external_id="vid1", title="GPT-5.5 解读", url="http://y/1")
        s.add(item); s.commit()
        got = s.query(Item).filter_by(external_id="vid1").one()
        assert got.status == "seen"   # 默认状态
        a = Analysis(item_id=got.id, summary="x", recommendation="看", value_score=88, tier="major", model_used="agnes")
        s.add(a); s.commit()
        assert got.analyses[0].value_score == 88
