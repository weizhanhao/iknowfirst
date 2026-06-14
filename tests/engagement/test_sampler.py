from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from iknowfirst.db.models import Base
from iknowfirst.db.repository import ItemRepository
from iknowfirst.engagement.sampler import EngagementSampler

def _repo():
    e = create_engine("sqlite://"); Base.metadata.create_all(e)
    return ItemRepository(sessionmaker(e))

class FakeNotifier:
    def __init__(self): self.spikes = []
    def push_spike(self, title, url, author, source_type, likes_per_hour):
        self.spikes.append((title, likes_per_hour))

def test_sampler_pushes_spike_when_velocity_crosses_threshold():
    repo = _repo(); now = datetime(2026, 6, 15, 12, 0)
    item = repo.add_new("youtube", "yt:video:vid1", "热门视频", "http://y/1",
                        author="K", published_at=None, status="analyzed")
    repo.add_engagement_sample(item.id, 1000, 100, 5, sampled_at=now - timedelta(hours=2))
    notifier = FakeNotifier()
    sampler = EngagementSampler(repo, fetch=lambda vid: (9000, 5100, 50), notifier=notifier,
                                velocity_major_threshold=2000.0, track_window_hours=24)
    sampler.run_once(now)
    assert len(notifier.spikes) == 1 and notifier.spikes[0][0] == "热门视频"

def test_sampler_does_not_repush_already_promoted():
    repo = _repo(); now = datetime(2026, 6, 15, 12, 0)
    item = repo.add_new("youtube", "yt:video:vid1", "热门视频", "http://y/1",
                        author=None, published_at=None, status="analyzed")
    repo.add_engagement_sample(item.id, 1000, 100, 5, sampled_at=now - timedelta(hours=2))
    notifier = FakeNotifier()
    sampler = EngagementSampler(repo, fetch=lambda vid: (9000, 5100, 50), notifier=notifier,
                                velocity_major_threshold=2000.0, track_window_hours=24)
    sampler.run_once(now); sampler.run_once(now)
    assert len(notifier.spikes) == 1

def test_sampler_no_push_below_threshold():
    repo = _repo(); now = datetime(2026, 6, 15, 12, 0)
    item = repo.add_new("youtube", "yt:video:vid1", "普通视频", "http://y/1",
                        author=None, published_at=None, status="analyzed")
    repo.add_engagement_sample(item.id, 1000, 100, 5, sampled_at=now - timedelta(hours=2))
    notifier = FakeNotifier()
    sampler = EngagementSampler(repo, fetch=lambda vid: (1100, 120, 6), notifier=notifier,
                                velocity_major_threshold=2000.0, track_window_hours=24)
    sampler.run_once(now)
    assert notifier.spikes == []

def test_sampler_skips_no_video_id():
    repo = _repo(); now = datetime(2026, 6, 15, 12, 0)
    repo.add_new("youtube", "no-id-here", "无ID", "http://x/none", None, None, status="analyzed")
    def boom(vid): raise RuntimeError("api down")
    notifier = FakeNotifier()
    sampler = EngagementSampler(repo, fetch=boom, notifier=notifier,
                                velocity_major_threshold=2000.0, track_window_hours=24)
    sampler.run_once(now)
    assert notifier.spikes == []

def test_sampler_swallows_fetch_error():
    repo = _repo(); now = datetime(2026, 6, 15, 12, 0)
    repo.add_new("youtube", "yt:video:vidX", "有ID但接口炸", "http://y/x", None, None, status="analyzed")
    def boom(vid): raise RuntimeError("api down")
    notifier = FakeNotifier()
    sampler = EngagementSampler(repo, fetch=boom, notifier=notifier,
                                velocity_major_threshold=2000.0, track_window_hours=24)
    sampler.run_once(now)                # 有合法 video_id → 进入 fetch → 抛错被吞，不崩
    assert notifier.spikes == []
