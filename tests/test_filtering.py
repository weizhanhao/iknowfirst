from iknowfirst.filtering import match_keywords

def test_match_case_insensitive_and_cjk():
    kws = {"gpt-5.5", "智能体", "mcp"}
    assert match_keywords("Deep dive into GPT-5.5 release", kws) == ["gpt-5.5"]
    assert match_keywords("聊聊智能体与 MCP 协议", kws) == ["mcp", "智能体"]  # 返回排序去重
    assert match_keywords("无关内容", kws) == []
