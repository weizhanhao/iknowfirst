import pytest
from iknowfirst.llm.factory import FallbackLLM

class OK:
    name = "ok"
    def complete(self, system: str, user: str) -> str:
        return '{"ok": true}'

class Boom:
    name = "boom"
    def complete(self, system: str, user: str) -> str:
        raise RuntimeError("rate limited")

def test_fallback_uses_primary_when_ok():
    llm = FallbackLLM(primary=OK(), fallback=Boom())
    assert llm.complete("s", "u") == '{"ok": true}'

def test_fallback_switches_on_primary_failure():
    llm = FallbackLLM(primary=Boom(), fallback=OK())
    assert llm.complete("s", "u") == '{"ok": true}'

def test_raises_when_both_fail():
    llm = FallbackLLM(primary=Boom(), fallback=Boom())
    with pytest.raises(RuntimeError):
        llm.complete("s", "u")
