from iknowfirst.config import Config
from iknowfirst.sources.feeds import build_feeds

def _cfg():
    return Config.model_validate({
        "rsshub_base_url": "http://rss:1200",
        "sources": {
            "youtube_channels": [
                {"name": "K", "channel_id": "UC123"},
                {"name": "T", "handle": "@two"},
            ],
            "x_accounts": ["karpathy"],
            "bilibili_uids": [{"name": "李沐", "uid": "1567748478"}, {"name": "空", "uid": ""}],
            "arxiv_categories": ["cs.AI"],
        },
        "keywords": {},
        "llm": {"provider": "agnes", "base_url": "x", "model": "m", "api_key_env": "AGNES_API_KEY"},
        "push": {"wecom_webhook_env": "WECOM_WEBHOOK_URL"},
    })

def test_build_feeds_covers_sources_and_types():
    feeds = build_feeds(_cfg())
    urls = {f.url for f in feeds}
    types = {f.source_type for f in feeds}
    assert "http://rss:1200/youtube/channel/UC123" in urls
    assert "http://rss:1200/youtube/user/@two" in urls
    assert "http://rss:1200/twitter/user/karpathy" in urls
    assert "http://rss:1200/bilibili/user/video/1567748478" in urls
    assert "http://rss:1200/arxiv/cs.AI" in urls
    # uid 为空的 B 站源被跳过
    assert types == {"youtube", "x", "bilibili", "arxiv"}

def test_hf_daily_papers_feed():
    from iknowfirst.config import Config
    cfg = Config.model_validate({
        "rsshub_base_url": "http://rss:1200",
        "sources": {
            "youtube_channels": [],
            "x_accounts": [],
            "bilibili_uids": [],
            "arxiv_categories": [],
            "hf_daily_papers": True,
        },
        "keywords": {},
        "llm": {"provider": "agnes", "base_url": "x", "model": "m", "api_key_env": "AGNES_API_KEY"},
        "push": {"wecom_webhook_env": "WECOM_WEBHOOK_URL"},
    })
    feeds = build_feeds(cfg)
    urls = {f.url for f in feeds}
    assert "http://rss:1200/huggingface/daily-papers" in urls
    hf_feed = next(f for f in feeds if "huggingface" in f.url)
    assert hf_feed.source_type == "arxiv"
