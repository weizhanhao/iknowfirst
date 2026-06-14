import json
import httpx, respx, pytest
from iknowfirst.notify.wecom import WecomClient

@respx.mock
def test_send_markdown_posts_correct_payload():
    route = respx.post("https://qyapi.weixin.qq.com/hook").mock(
        return_value=httpx.Response(200, json={"errcode": 0, "errmsg": "ok"}))
    WecomClient("https://qyapi.weixin.qq.com/hook").send_markdown("**重磅**\n标题")
    assert route.called
    body = json.loads(route.calls.last.request.content)
    assert body["msgtype"] == "markdown"
    assert "重磅" in body["markdown"]["content"]

@respx.mock
def test_send_raises_on_wecom_error_code():
    respx.post("https://qyapi.weixin.qq.com/hook").mock(
        return_value=httpx.Response(200, json={"errcode": 93000, "errmsg": "invalid webhook"}))
    with pytest.raises(RuntimeError):
        WecomClient("https://qyapi.weixin.qq.com/hook").send_markdown("x")
