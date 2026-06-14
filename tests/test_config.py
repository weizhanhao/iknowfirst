import textwrap
from iknowfirst.config import load_config

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
