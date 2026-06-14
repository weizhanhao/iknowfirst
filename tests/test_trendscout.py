from iknowfirst.trendscout import TrendScout

class FakeLLM:
    name = "fake"
    def __init__(self, payload): self._p = payload
    def complete(self, system, user): return self._p

class FakeWecom:
    def __init__(self): self.sent = []
    def send_markdown(self, c): self.sent.append(c)

def test_suggests_new_keywords_not_in_current_set():
    payload = '{"new_keywords":["DeepSeek-V4","Nano Banana 2","GPT-5.5"]}'
    wecom = FakeWecom()
    ts = TrendScout(FakeLLM(payload), wecom, mode="suggest")
    added = ts.run(titles=["t1", "t2"], current_keywords={"gpt-5.5"})
    assert set(added) == {"DeepSeek-V4", "Nano Banana 2"}   # GPT-5.5 已存在被过滤
    assert len(wecom.sent) == 1
    assert "DeepSeek-V4" in wecom.sent[0]

def test_no_new_keywords_sends_nothing():
    wecom = FakeWecom()
    ts = TrendScout(FakeLLM('{"new_keywords":[]}'), wecom, mode="suggest")
    assert ts.run(titles=["x"], current_keywords=set()) == []
    assert wecom.sent == []

def test_empty_titles_skips_llm():
    wecom = FakeWecom()
    ts = TrendScout(FakeLLM('{"new_keywords":["x"]}'), wecom, mode="suggest")
    assert ts.run(titles=[], current_keywords=set()) == []
    assert wecom.sent == []
