from datetime import datetime, timedelta
from iknowfirst.engagement.tracker import likes_per_hour

def test_likes_per_hour_growth():
    t0 = datetime(2026, 6, 14, 10, 0)
    samples = [(t0, 100), (t0 + timedelta(hours=2), 5100)]   # (sampled_at, likes)
    assert likes_per_hour(samples) == 2500.0

def test_single_sample_returns_zero():
    assert likes_per_hour([(datetime(2026, 6, 14, 10, 0), 100)]) == 0.0

def test_empty_returns_zero():
    assert likes_per_hour([]) == 0.0
