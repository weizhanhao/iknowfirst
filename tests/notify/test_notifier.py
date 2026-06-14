from iknowfirst.analyzer import AnalysisResult
from iknowfirst.notify.notifier import format_card, Notifier

def _res(tier="major"):
    return AnalysisResult(summary="讲了稀疏注意力", highlights=["DSA", "省显存"],
                          recommendation="推荐看", value_score=88, tier=tier)

def test_format_card_contains_key_fields():
    card = format_card(title="Sparse Attention", url="http://a/1", author="K",
                       source_type="arxiv", res=_res(), likes_per_hour=0, degraded=False)
    assert "Sparse Attention" in card and "讲了稀疏注意力" in card
    assert "DSA" in card and "http://a/1" in card

def test_format_card_marks_degraded():
    card = format_card("t", "u", None, "youtube", _res(), 0, degraded=True)
    assert "未取到字幕" in card or "⚠️" in card

class FakeWecom:
    def __init__(self): self.sent = []
    def send_markdown(self, content): self.sent.append(content)

def test_major_pushes_immediately_normal_queues():
    wecom = FakeWecom()
    n = Notifier(wecom)
    n.handle(title="重磅", url="u", author=None, source_type="youtube", res=_res("major"), likes_per_hour=0, degraded=False)
    n.handle(title="普通", url="u2", author=None, source_type="youtube", res=_res("normal"), likes_per_hour=0, degraded=False)
    assert len(wecom.sent) == 1                 # 只有重磅即时推
    assert "重磅" in wecom.sent[0]
    assert n.digest_queue_size() == 1           # 普通进队列

def test_flush_digest_sends_one_combined_message_and_clears():
    wecom = FakeWecom()
    n = Notifier(wecom)
    n.handle("普通1", "u1", None, "youtube", _res("normal"), 0, False)
    n.handle("普通2", "u2", None, "arxiv", _res("normal"), 0, False)
    n.flush_digest()
    assert len(wecom.sent) == 1
    assert "普通1" in wecom.sent[0] and "普通2" in wecom.sent[0]
    assert n.digest_queue_size() == 0

def test_flush_empty_digest_sends_nothing():
    wecom = FakeWecom()
    n = Notifier(wecom)
    n.flush_digest()
    assert wecom.sent == []

def test_flush_digest_keeps_queue_when_send_fails():
    class BrokenWecom:
        def send_markdown(self, content): raise RuntimeError("wecom down")
    n = Notifier(BrokenWecom())
    n.handle("普通1", "u1", None, "youtube", _res("normal"), 0, False)
    n.flush_digest()                       # 不抛
    assert n.digest_queue_size() == 1      # 队列保留,待重试

def test_safe_send_swallows_wecom_exception():
    class BrokenWecom:
        def send_markdown(self, content): raise RuntimeError("wecom down")
    n = Notifier(BrokenWecom())
    n.handle("x", "u", None, "youtube", _res("major"), 0, False)  # major 即时推,不得抛
    assert n.digest_queue_size() == 0

def test_push_spike_sends_correct_content():
    class FakeWecom:
        def __init__(self): self.sent = []
        def send_markdown(self, content): self.sent.append(content)
    wecom = FakeWecom()
    n = Notifier(wecom)
    n.push_spike(title="热门视频", url="http://y/1", author="K",
                 source_type="youtube", likes_per_hour=2500.0)
    assert len(wecom.sent) == 1
    assert "热度飙升" in wecom.sent[0]
    assert "赞/小时" in wecom.sent[0]
