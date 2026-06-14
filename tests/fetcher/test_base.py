from iknowfirst.fetcher.base import FetchResult

def test_fetch_result_degraded_flag():
    full = FetchResult(text="完整字幕……", degraded=False)
    deg = FetchResult(text="仅标题+简介", degraded=True, note="未取到字幕")
    assert not full.degraded
    assert deg.degraded and deg.note == "未取到字幕"
