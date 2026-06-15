from datetime import datetime

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

def test_add_new_truncates_overlong_fields(repo):
    long_author = "作者," * 300  # 远超 255
    item = repo.add_new("arxiv", "x:1", "标" * 600, "http://a/" + "u" * 1200,
                        author=long_author, published_at=None, status="seen")
    got = repo.items_by_status("seen")[0]
    assert len(got.author) <= 255
    assert len(got.title) <= 512
    assert len(got.url) <= 1024

def test_set_raw_text(repo):
    item = repo.add_new("youtube", "d", "标题D", "http://y/d", author=None, published_at=None, status="matched")
    repo.set_raw_text(item.id, "字幕正文")
    got = repo.items_by_status("matched")[0]
    assert got.raw_text == "字幕正文"

def test_engagement_samples_roundtrip(repo):
    t1 = datetime(2026, 6, 15, 10, 0)
    t2 = datetime(2026, 6, 15, 11, 0)
    item = repo.add_new("youtube", "yt:video:vid1", "热门视频", "http://y/1",
                        author="K", published_at=None, status="analyzed")
    repo.add_engagement_sample(item.id, 1000, 100, 5, sampled_at=t1)
    repo.add_engagement_sample(item.id, 2000, 200, 10, sampled_at=t2)
    samples = repo.likes_samples_for(item.id)
    assert len(samples) == 2
    assert all(isinstance(s[0], datetime) for s in samples)
    likes_values = {s[1] for s in samples}
    assert likes_values == {100, 200}

def test_youtube_tracked_items_filters_correctly(repo):
    cutoff = datetime(2020, 1, 1)
    item_ok = repo.add_new("youtube", "yt:video:ok", "正常视频", "http://y/ok",
                            author=None, published_at=None, status="analyzed")
    repo.add_new("youtube", "yt:video:skip", "已跳过", "http://y/skip",
                  author=None, published_at=None, status="skipped")
    tracked = repo.youtube_tracked_items(cutoff)
    ids = {i.external_id for i in tracked}
    assert "yt:video:ok" in ids
    assert "yt:video:skip" not in ids

def test_mark_engagement_promoted(repo):
    item = repo.add_new("youtube", "yt:video:promo", "飙升视频", "http://y/p",
                         author=None, published_at=None, status="analyzed")
    assert not item.engagement_promoted
    repo.mark_engagement_promoted(item.id)
    tracked = repo.youtube_tracked_items(datetime(2020, 1, 1))
    promoted = next(i for i in tracked if i.external_id == "yt:video:promo")
    assert promoted.engagement_promoted is True
