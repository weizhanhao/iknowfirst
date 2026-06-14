from iknowfirst.db.models import Item
from iknowfirst.fetcher.youtube import YoutubeFetcher

def _item():
    return Item(source_type="youtube", external_id="v1", title="GPT-5.5 深度解读",
                url="http://y/v1", raw_text=None)

def test_returns_subtitles_when_available():
    f = YoutubeFetcher(extract_subtitles=lambda url: "这是字幕正文，很长很长")
    res = f.fetch(_item())
    assert res.degraded is False
    assert "字幕正文" in res.text

def test_degrades_to_title_when_no_subtitles():
    f = YoutubeFetcher(extract_subtitles=lambda url: None)
    res = f.fetch(_item())
    assert res.degraded is True
    assert "GPT-5.5 深度解读" in res.text
    assert res.note == "未取到字幕"

def test_degrades_on_extractor_error():
    def boom(url): raise RuntimeError("yt-dlp failed")
    res = YoutubeFetcher(extract_subtitles=boom).fetch(_item())
    assert res.degraded is True
