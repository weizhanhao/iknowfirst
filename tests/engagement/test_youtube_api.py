import httpx, respx, pytest
from iknowfirst.db.models import Item
from iknowfirst.engagement.youtube_api import extract_video_id, fetch_stats

def _it(ext, url=""):
    return Item(source_type="youtube", external_id=ext, title="t", url=url)

def test_extract_video_id_from_rss_id():
    assert extract_video_id(_it("yt:video:abcDEF12345")) == "abcDEF12345"

def test_extract_video_id_from_url():
    assert extract_video_id(_it("x", "https://www.youtube.com/watch?v=abcDEF12345")) == "abcDEF12345"
    assert extract_video_id(_it("x", "https://youtu.be/abcDEF12345")) == "abcDEF12345"

def test_extract_video_id_none_when_unknown():
    assert extract_video_id(_it("x", "https://example.com/foo")) is None

@respx.mock
def test_fetch_stats_parses_counts():
    respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
        return_value=httpx.Response(200, json={"items": [{"statistics": {
            "viewCount": "1000", "likeCount": "50", "commentCount": "7"}}]}))
    assert fetch_stats("vid", "key") == (1000, 50, 7)

@respx.mock
def test_fetch_stats_missing_like_comment_default_zero():
    respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
        return_value=httpx.Response(200, json={"items": [{"statistics": {"viewCount": "9"}}]}))
    assert fetch_stats("vid", "key") == (9, 0, 0)

@respx.mock
def test_fetch_stats_raises_when_no_item():
    respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
        return_value=httpx.Response(200, json={"items": []}))
    with pytest.raises(RuntimeError):
        fetch_stats("vid", "key")
