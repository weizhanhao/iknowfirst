# iknowfirst — AI 动态雷达

## 部署（阿里云香港轻量，无域名/无代理）
1. 安装 Docker + Docker Compose。
2. `cp .env.example .env`，填入 Agnes/企微/YouTube 的真实值；`cp config.example.yaml config.yaml`，核对/修改信源与关键词。
3. `docker compose up -d`（首次拉起 rsshub + mysql + app）。
4. app 启动会先做"首启快照"（不补推历史），之后每 5 分钟轮询、命中→解读→推送。

## 配置 LLM 降级（可选）
在 `main.build_llm` 中把 fallback 换成第二个 `OpenAICompatibleLLM`（如 DeepSeek），各自用对应 env。

## 待部署时确认的占位
- YouTube 频道：只有 handle 没 channel_id 的，用 `yt-dlp --print channel_id <url>` 解析后回填 config。
- B站 up 主 uid：站内搜索确认后回填。
- Agnes base_url：从 Agnes 后台文档页确认。
