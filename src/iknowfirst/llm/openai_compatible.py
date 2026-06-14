from __future__ import annotations
from openai import OpenAI

class OpenAICompatibleLLM:
    """适配 Agnes / DeepSeek / Gemini 等 OpenAI 兼容端点。"""
    def __init__(self, name: str, base_url: str, api_key: str, model: str):
        self.name = name
        self._model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""
