from __future__ import annotations
import os
import yaml
from pydantic import BaseModel, Field, model_validator

class YoutubeChannel(BaseModel):
    name: str
    handle: str | None = None
    channel_id: str | None = None

    @model_validator(mode="after")
    def require_handle_or_channel_id(self) -> "YoutubeChannel":
        if self.handle is None and self.channel_id is None:
            raise ValueError("youtube channel needs handle or channel_id")
        return self

class BilibiliUp(BaseModel):
    name: str
    uid: str = ""

class Sources(BaseModel):
    youtube_channels: list[YoutubeChannel] = Field(default_factory=list)
    x_accounts: list[str] = Field(default_factory=list)
    bilibili_uids: list[BilibiliUp] = Field(default_factory=list)
    arxiv_categories: list[str] = Field(default_factory=list)
    hf_daily_papers: bool = False

class Engagement(BaseModel):
    enabled: bool = True
    track_window_hours: int = 24
    sample_interval_minutes: int = 60

class TrendScout(BaseModel):
    enabled: bool = True
    run_time: str = "08:30"
    lookback_days: int = 7
    mode: str = "suggest"

class LLM(BaseModel):
    provider: str
    base_url: str
    model: str
    api_key_env: str
    fallback: str | None = None

    @property
    def resolved_api_key(self) -> str:
        key = os.environ.get(self.api_key_env, "")
        if not key:
            raise RuntimeError(f"missing env var {self.api_key_env} for LLM api key")
        return key

class PushConfig(BaseModel):
    wecom_webhook_env: str
    major_value_threshold: int = 80
    velocity_major_threshold: float = 2000.0
    digest_times: list[str] = Field(default_factory=lambda: ["09:00", "20:00"])

    @property
    def webhook_url(self) -> str:
        url = os.environ.get(self.wecom_webhook_env, "")
        if not url:
            raise RuntimeError(f"missing env var {self.wecom_webhook_env} for wecom webhook")
        return url

class Config(BaseModel):
    poll_interval_minutes: int = 5
    rsshub_base_url: str
    sources: Sources
    keywords: dict[str, list[str]] = Field(default_factory=dict)
    engagement: Engagement = Field(default_factory=Engagement)
    trendscout: TrendScout = Field(default_factory=TrendScout)
    llm: LLM
    push: PushConfig

    def all_keywords(self) -> set[str]:
        out: set[str] = set()
        for group in self.keywords.values():
            for kw in group:
                out.add(kw.strip().lower())
        return out

def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    expanded = os.path.expandvars(raw_text)
    raw = yaml.safe_load(expanded)
    return Config.model_validate(raw)
