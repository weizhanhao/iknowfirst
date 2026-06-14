from __future__ import annotations
import httpx

class WecomClient:
    def __init__(self, webhook_url: str, timeout: float = 10.0):
        self._url = webhook_url
        self._timeout = timeout

    def send_markdown(self, content: str) -> None:
        payload = {"msgtype": "markdown", "markdown": {"content": content}}
        resp = httpx.post(self._url, json=payload, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"wecom error {data.get('errcode')}: {data.get('errmsg')}")
