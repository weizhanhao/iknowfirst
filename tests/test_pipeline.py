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

class ScoreAnalyzer:
    def __init__(self, score): self._score = score
    def analyze(self, title, text, likes_per_hour=0.0):
        tier = "major" if self._score >= 80 else "normal"
        return AnalysisResult("摘要", [], "看", self._score, tier)

def test_arxiv_below_super_threshold_not_pushed():
    repo = _repo()
    item = repo.add_new("arxiv", "a1", "Agent 论文", "http://a/1", None, None, status="new")
    notifier = FakeNotifier()
    p = Pipeline(repo, keywords={"agent"}, fetcher=FakeFetcher(),
                 analyzer=ScoreAnalyzer(88), notifier=notifier, arxiv_major_threshold=95)
    p.process(item)
    assert notifier.handled == []                      # 88 < 95,论文不推
    assert repo.items_by_status("analyzed")[0].external_id == "a1"

def test_arxiv_super_major_is_pushed():
    repo = _repo()
    item = repo.add_new("arxiv", "a2", "Agent 重磅论文", "http://a/2", None, None, status="new")
    notifier = FakeNotifier()
    p = Pipeline(repo, keywords={"agent"}, fetcher=FakeFetcher(),
                 analyzer=ScoreAnalyzer(96), notifier=notifier, arxiv_major_threshold=95)
    p.process(item)
    assert len(notifier.handled) == 1                  # 96 >= 95,推

def test_video_unaffected_by_arxiv_threshold():
    repo = _repo()
    item = repo.add_new("youtube", "v3", "Agent 视频", "http://y/v3", None, None, status="new")
    notifier = FakeNotifier()
    p = Pipeline(repo, keywords={"agent"}, fetcher=FakeFetcher(),
                 analyzer=ScoreAnalyzer(85), notifier=notifier, arxiv_major_threshold=95)
    p.process(item)
    assert len(notifier.handled) == 1                  # 视频不受论文门槛影响

def test_pipeline_sets_error_status_on_failure():
    repo = _repo()
    item = repo.add_new("youtube", "v9", "GPT-5.5 解读", "http://y/v9", None, None, status="new")
    class BoomFetcher:
        def fetch(self, item): raise RuntimeError("fetch failed")
    notifier = FakeNotifier()
    p = Pipeline(repo, keywords={"gpt-5.5"}, fetcher=BoomFetcher(),
                 analyzer=FakeAnalyzer(), notifier=notifier)
    p.process(item)                                  # 不抛
    assert notifier.handled == []
    assert repo.items_by_status("error")[0].external_id == "v9"
