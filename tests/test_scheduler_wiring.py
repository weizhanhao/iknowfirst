from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from iknowfirst.db.models import Base
from iknowfirst.db.repository import ItemRepository
from iknowfirst.analyzer import AnalysisResult
from iknowfirst.fetcher.base import FetchResult
from iknowfirst.scheduler import run_poll_cycle
from iknowfirst.sources.feeds import Feed
from iknowfirst.sources.collector import Collector, ParsedEntry
from iknowfirst.pipeline import Pipeline

def test_run_poll_cycle_processes_new_items():
    engine = create_engine("sqlite://"); Base.metadata.create_all(engine)
    repo = ItemRepository(sessionmaker(engine))
    feeds = [Feed("youtube", "http://rss/1", "K")]
    entries = [ParsedEntry("v1", "GPT-5.5 解读", "http://y/v1", "K", None)]
    collector = Collector(repo, parser=lambda f: entries)

    class FakeFetcher:
        def fetch(self, item): return FetchResult(text="正文", degraded=False)
    class FakeAnalyzer:
        def analyze(self, title, text, likes_per_hour=0.0):
            return AnalysisResult("摘要", [], "看", 90, "major")
    class FakeNotifier:
        def __init__(self): self.handled = []
        def handle(self, **kw): self.handled.append(kw)

    notifier = FakeNotifier()
    pipeline = Pipeline(repo, {"gpt-5.5"}, FakeFetcher(), FakeAnalyzer(), notifier)

    run_poll_cycle(collector, feeds, pipeline, first_run=False)
    assert len(notifier.handled) == 1
