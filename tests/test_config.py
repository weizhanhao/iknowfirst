import textwrap
from iknowfirst.config import load_config, PushConfig

def test_load_config_parses_sources_and_expands_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AGNES_API_KEY", "k-123")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(textwrap.dedent("""
        poll_interval_minutes: 5
        rsshub_base_url: "http://localhost:1200"
        sources:
          youtube_channels:
            - { name: "Karpathy", handle: "@AndrejKarpathy" }
          x_accounts: ["karpathy"]
          bilibili_uids: []
          arxiv_categories: ["cs.AI"]
        keywords:
          Agent: ["MCP", "智能体"]
          模型: ["GPT-5.5"]
        engagement: { enabled: true, track_window_hours: 24, sample_interval_minutes: 60 }
        trendscout: { enabled: true, run_time: "08:30", lookback_days: 7, mode: "suggest" }
        llm:
          provider: "agnes"
          base_url: "http://x/v1"
          model: "agnes-2.0-flash"
          api_key_env: "AGNES_API_KEY"
          fallback: "deepseek"
        push:
          wecom_webhook_env: "WECOM_WEBHOOK_URL"
          major_value_threshold: 80
          digest_times: ["09:00", "20:00"]
    """), encoding="utf-8")
    cfg = load_config(str(cfg_file))
    assert cfg.poll_interval_minutes == 5
    assert cfg.sources.youtube_channels[0].handle == "@AndrejKarpathy"
    # 关键词分组被展开成一个去重小写集合
    assert cfg.all_keywords() == {"mcp", "智能体", "gpt-5.5"}
    assert cfg.llm.resolved_api_key == "k-123"


def test_load_config_expands_env_in_values(tmp_path, monkeypatch):
    monkeypatch.setenv("AGNES_API_KEY", "k")
    monkeypatch.setenv("MY_BASE", "https://api.example.com/v1")
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        'rsshub_base_url: "http://r:1200"\n'
        'sources: {youtube_channels: [], x_accounts: [], bilibili_uids: [], arxiv_categories: []}\n'
        'keywords: {}\n'
        'llm: {provider: agnes, base_url: "${MY_BASE}", model: m, api_key_env: AGNES_API_KEY}\n'
        'push: {wecom_webhook_env: WECOM_WEBHOOK_URL}\n', encoding="utf-8")
    cfg = load_config(str(cfg_file))
    assert cfg.llm.base_url == "https://api.example.com/v1"


def test_push_config_has_default_velocity_major_threshold():
    push = PushConfig(wecom_webhook_env="WECOM_WEBHOOK_URL")
    assert push.velocity_major_threshold == 2000.0


def test_push_config_velocity_major_threshold_is_configurable():
    push = PushConfig(wecom_webhook_env="WECOM_WEBHOOK_URL", velocity_major_threshold=500.0)
    assert push.velocity_major_threshold == 500.0
