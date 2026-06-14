from iknowfirst.analyzer import Analyzer, AnalysisResult, decide_tier

class FakeLLM:
    name = "fake"
    def __init__(self, payload): self._p = payload
    def complete(self, system, user): return self._p

def test_decide_tier_by_score_or_velocity():
    assert decide_tier(value_score=85, likes_per_hour=0, threshold=80) == "major"
    assert decide_tier(value_score=50, likes_per_hour=3000, threshold=80, velocity_major=2000) == "major"
    assert decide_tier(value_score=50, likes_per_hour=10, threshold=80) == "normal"

def test_analyze_parses_json_payload():
    payload = '{"summary":"讲了稀疏注意力","highlights":["DSA","省显存"],"recommendation":"推荐看","value_score":88}'
    a = Analyzer(FakeLLM(payload), major_value_threshold=80)
    res = a.analyze(title="Sparse Attention", text="...", likes_per_hour=0)
    assert isinstance(res, AnalysisResult)
    assert res.value_score == 88 and res.tier == "major"
    assert res.highlights == ["DSA", "省显存"]

def test_analyze_handles_non_json_gracefully():
    a = Analyzer(FakeLLM("模型抽风返回了纯文本"), major_value_threshold=80)
    res = a.analyze(title="t", text="x", likes_per_hour=0)
    assert res.value_score == 0 and res.tier == "normal"
    assert res.summary  # 用原始文本兜底
