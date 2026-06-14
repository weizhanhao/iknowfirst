from iknowfirst.preflight import Check, run_checks, all_ok, format_report

def test_run_checks_collects_results_and_catches_exceptions():
    def ok_check(): return Check("a", True, "fine")
    def boom_check(): raise RuntimeError("down")
    results = run_checks([ok_check, boom_check])
    assert results[0].ok is True
    assert results[1].ok is False and "down" in results[1].detail
    assert results[1].name == "boom_check"

def test_all_ok():
    assert all_ok([Check("a", True), Check("b", True)]) is True
    assert all_ok([Check("a", True), Check("b", False)]) is False

def test_format_report_marks_pass_and_fail():
    rep = format_report([Check("配置", True, "x"), Check("密钥", False, "缺少 X")])
    assert "✅ 配置" in rep and "❌ 密钥" in rep and "缺少 X" in rep
