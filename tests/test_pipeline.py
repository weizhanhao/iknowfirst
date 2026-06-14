from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from iknowfirst.db.models import Base
from iknowfirst.db.repository import ItemRepository
from iknowfirst.analyzer import AnalysisResult
from iknowfirst.fetcher.base import FetchResult
from iknowfirst.pipeline import Pipeline

def _repo():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return ItemRepository(sessionmaker(engine))

class FakeFetcher:
    def fetch(self, item): return FetchResult(text="正文", degraded=False)

class FakeAnalyzer:
    def analyze(self, title, text, likes_per_hour=0.0):
        return AnalysisResult("摘要", ["h"], "看", 90, "major")

class FakeNotifier:
    def __init__(self): self.handled = []
    def handle(self, **kw): self.handled.append(kw)

def test_pipeline_filters_fetches_analyzes_notifies_and_sets_status():
    repo = _repo()
    item = repo.add_new("youtube", "v1", "GPT-5.5 解读", "http://y/v1", None, None, status="new")
    notifier = FakeNotifier()
    p = Pipeline(repo, keywords={"gpt-5.5"}, fetcher=FakeFetcher(),
                 analyzer=FakeAnalyzer(), notifier=notifier)
    p.process(item)
    assert len(notifier.handled) == 1
    assert notifier.handled[0]["res"].tier == "major"
    assert repo.items_by_status("analyzed")[0].external_id == "v1"

def test_pipeline_skips_when_no_keyword_match():
    repo = _repo()
    item = repo.add_new("youtube", "v2", "无关闲聊", "http://y/v2", None, None, status="new")
    notifier = FakeNotifier()
    p = Pipeline(repo, keywords={"gpt-5.5"}, fetcher=FakeFetcher(),
                 analyzer=FakeAnalyzer(), notifier=notifier)
    p.process(item)
    assert notifier.handled == []
    assert repo.items_by_status("skipped")[0].external_id == "v2"
