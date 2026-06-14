from iknowfirst.db.models import Item
from iknowfirst.fetcher.dispatch import FetcherDispatch

def test_arxiv_uses_abstract_from_raw_text():
    d = FetcherDispatch(youtube=None)
    item = Item(source_type="arxiv", external_id="a1", title="Sparse Attention",
                url="http://a/1", raw_text="We propose DSA, a sparse attention…")
    res = d.fetch(item)
    assert "DSA" in res.text and res.degraded is False

def test_x_and_bilibili_use_title_plus_raw():
    d = FetcherDispatch(youtube=None)
    item = Item(source_type="x", external_id="t1", title="新模型发布", url="http://x/1", raw_text="详情见视频")
    res = d.fetch(item)
    assert "新模型发布" in res.text and "详情见视频" in res.text

def test_youtube_delegates_to_injected_fetcher():
    class FakeYT:
        def fetch(self, item):
            from iknowfirst.fetcher.base import FetchResult
            return FetchResult(text="字幕", degraded=False)
    d = FetcherDispatch(youtube=FakeYT())
    item = Item(source_type="youtube", external_id="v1", title="t", url="u", raw_text=None)
    assert d.fetch(item).text == "字幕"
