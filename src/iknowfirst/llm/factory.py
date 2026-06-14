from __future__ import annotations
import logging

log = logging.getLogger(__name__)

class FallbackLLM:
    """主力失败时自动降级到备用。primary/fallback 须实现 complete(system, user)->str。"""
    def __init__(self, primary, fallback=None):
        self._primary = primary
        self._fallback = fallback

    @property
    def name(self) -> str:
        return f"fallback({getattr(self._primary, 'name', '?')}->{getattr(self._fallback, 'name', '?')})"

    def complete(self, system: str, user: str) -> str:
        try:
            return self._primary.complete(system, user)
        except Exception:
            log.warning("primary LLM %s failed; trying fallback", getattr(self._primary, "name", "?"))
            if self._fallback is None:
                raise
            try:
                return self._fallback.complete(system, user)
            except Exception:
                log.error("fallback LLM %s also failed", getattr(self._fallback, "name", "?"))
                raise
