# AI 动态雷达 (iknowfirst) — 设计文档

**日期:** 2026-06-14
**状态:** 已与用户确认,待评审

---

## 1. 目标与背景

每天/实时掌握**全球 AI 动态**,重点是**视频**(大佬科普、论文解读、深度讲解)。
系统主动监控多个信源,对**命中关键词**的内容做 **AI 深度解读**,再结合**真实热度(点赞/评论增速)**判断价值,通过**企业微信机器人 webhook** 推送给用户。

**核心诉求:第一时间。** 设计上保证"发现实时(5 分钟轮询),解读只加几分钟"。

### 成功标准

- 顶级大佬 / 重磅内容,从发布到推送 **≤ 15 分钟**。
- 推送的每条都带"讲了啥 / 亮点 / 要不要看"的中文解读,**点开前就能判断值不值得看**。
- 关键词与信源清单**用户可自行配置**(v1 用 YAML,v2 加网页后台)。
- 重磅秒推、普通汇总,**不刷屏**。

### 非目标 (YAGNI)

- v1 不做网页后台(YAML 配置起步)。
- v1 不做 arXiv/X 的热度追踪(它们的热度信号弱或需付费 API)。
- 不做多用户 / 账号体系(单用户自用工具)。
- 不做历史内容补推(首次启动只记录快照,从启动那刻往后推)。

---

## 2. 关键决策(已与用户确认)

| 项 | 方案 |
|---|---|
| 信源 | YouTube + X + B站 + arXiv/HF,**全部经 RSSHub 统一成 RSS** |
| 价值判断 | **AI 深度解读** + **热度增速双信号**(YouTube/B站) |
| 推送策略 | **分级**:重磅(高分)秒推;普通攒着每天 1–2 次汇总推 |
| 推送渠道 | **企业微信机器人 webhook** |
| 数据库 | **MySQL**,经**仓储模式(Repository Pattern)**封装,便于后续迁移 |
| LLM | **Agnes AI(免费、OpenAI 兼容)为主力**,配置可切换到 DeepSeek/Gemini |
| 部署 | **阿里云香港轻量服务器**(约 24–38 元/月),**无域名、无备案、无代理** |
| 配置 | **YAML 配置文件**起步,网页后台留 v2 |
| 轮询频率 | 每 **5 分钟** |
| 技术栈 | **Python**(沿用用户既有后端栈),SQLAlchemy + yt-dlp + httpx + OpenAI SDK |
| 选题自进化 | **TrendScout 模块(v1)**:定期用 LLM 从已采集内容流中发现"未在关键词库里的新热词/新模型名",推企微"建议新增关键词"由用户确认后并入。免费、无需额外搜索 API |
| 默认信源/关键词 | 由 `deep-research` 调研产出(见 §6),覆盖 2026.6 当下主流大佬/频道/热词;用户可随时改 |

---

## 3. 整体架构(数据流)

```
信源(YouTube / X / B站 / arXiv·HF)
   │  RSSHub 适配层:统一成 RSS
   ▼
[1] Collector 采集器 ──每 5 分钟轮询──▶ 发现新条目
   │   去重(MySQL processed items),首启只记快照不补推
   ▼
[2] Filter 召回 ──关键词匹配(读 YAML)──▶ 命中的入库,进入处理流水线
   │   ▲
   │   └─ TrendScout 选题侦察:定期用 LLM 从内容流里挖"新热词" → 推企微建议你扩充关键词
   │
   ├─────────────────────────────────────────┐
   ▼                                          ▼
[3] Fetcher 内容抓取                      [4] EngagementTracker 热度追踪
   拉视频字幕 / 论文摘要 / 正文              对 YouTube/B站 条目,发布后定期采样
   抓不到则降级用 标题+简介                  播放/点赞/评论数 → 计算增速
   │                                          │
   └──────────────┬───────────────────────────┘
                  ▼
[5] Analyzer AI 解读
    LLM(Agnes)读原料 → 结构化摘要 + 价值评分
    融合"热度增速"得到最终分级
                  ▼
[6] Notifier 分级推送
    ├─ 高分/重磅 ──▶ 立刻推企微
    └─ 普通     ──▶ 待汇总队列,定时(09:00 / 20:00)打包推
```

**设计原则:6 个模块各司其职、低耦合。** 任一模块降级/失败不阻断整体:
- 字幕抓不到 → 降级用标题+简介解读,并在推送标注"⚠️ 未取到字幕"。
- 热度接口失败 → 仅用 AI 评分,不阻断推送。
- Agnes 限速/不可用 → 切换备用 LLM。

---

## 4. 模块详细设计

### 4.1 Collector 采集器

- 输入:YAML 中的 RSSHub 订阅地址列表(每个信源一条 RSS URL)。
- 行为:每 5 分钟拉取所有 feed,解析条目,用 `external_id`(信源内唯一 ID,如 YouTube videoId)对照 MySQL `items` 表去重。
- **首次启动**:把当前所有条目写入库并标记为 `seen`(不进入处理流水线),避免一上来刷屏。此后只处理新出现的条目。
- 容错:单个 feed 拉取失败只记日志、跳过,不影响其他 feed。

### 4.2 Filter 召回

- 读 YAML 中的 `keywords`,对条目的标题+简介做匹配(大小写不敏感,支持中英文)。
- 命中 → 状态置 `matched`,进入处理流水线;未命中 → 标记 `skipped`(仍入库,便于回溯/调关键词)。
- 关键词匹配是"召回",真正的价值过滤交给 Analyzer。

### 4.3 Fetcher 内容抓取

| 信源 | 抓取内容 | 手段 | 降级 |
|---|---|---|---|
| YouTube | 自动字幕 | `yt-dlp` 拉 captions | 标题+简介 |
| arXiv/HF | abstract | RSS 自带 | —— |
| B站 | 简介(有字幕则字幕) | RSSHub / 字幕接口 | 标题+简介 |
| X | 推文正文 | RSSHub 自带 | 标题 |

- **降级原则**:绝不因抓不到原料而漏推;只降低解读深度并在推送中标注。

### 4.4 EngagementTracker 热度追踪 (v1 仅 YouTube/B站)

- 对 YouTube/B站 的 `matched` 条目,在发布后的**追踪窗口(默认 24h)**内,**每 60 分钟采样一次** 播放/点赞/评论数,写入 `engagement_samples`(时间序列)。
- 计算**增速**:单位时间内点赞/评论的增长率(如"前 2 小时点赞 +5000")。
- 接口:
  - YouTube → **YouTube Data API v3**(免费额度 1 万单位/天,需用户提供 API Key)。
  - B站 → 公开播放数据接口。
- 增速作为 Analyzer 价值评分的**加权输入**;接口失败则该信号缺省,不阻断。
- 追踪窗口结束后停止采样,释放配额。

### 4.5 Analyzer AI 解读

- 用 LLM(Agnes,OpenAI 兼容)对原料生成**结构化解读**:
  - `summary` 一句话中文总结
  - `highlights` 2–4 个亮点
  - `recommendation` 要不要看 / 适合谁
  - `value_score` 0–100 价值分
- **最终分级** = `f(value_score, 热度增速)`:两者任一突出即可判"重磅"。阈值在 YAML 配置(默认 `value_score ≥ 80` 或 热度增速进入高位 → 重磅)。
- LLM 层经**适配器封装**:`LLMClient` 接口 + `AgnesClient`/`DeepSeekClient`/`GeminiClient` 实现,配置切换,主力失败自动降级到备用。
- 输入做长度裁剪,避免超长文本超出上下文 / 浪费配额。

### 4.6 Notifier 分级推送

- **重磅**:解读完成立即组装企微消息卡片(Markdown)推送。
- **普通**:写入"待汇总队列",在配置的时间点(默认 09:00、20:00)把队列里多条打包成一条汇总消息推送。
- 企微消息内容:标题、信源、作者、一句话摘要、亮点、要不要看、原始链接、(若有)热度增速、降级标注。
- 推送结果记录到 `pushes` 表,失败重试(指数退避)。

### 4.7 TrendScout 选题侦察 (v1) —— 关键词自进化

解决"漏掉刚冒出来、还没配进关键词的新东西"的盲区。**关键设计:不依赖任何外部搜索 API,免费且自洽**——直接从系统自己已经在采集的内容流里挖新词。

- **数据来源**:近 N 天(默认 7 天)采集到的所有条目标题/简介(`items` 表,含未命中关键词的 `skipped` 条目——它们正是潜在新热点)。
- **行为**:每天定时(默认 08:30,赶在早间汇总前)把这批标题喂给 LLM,提示词:"找出这些标题里反复出现、但不在当前关键词库中的 AI 新模型名/新术语/新热点",产出**候选新关键词 + 出现频次 + 一句理由**。
- **策略(已确认)**:**稳妥模式**——不自动并入,而是**推一条企微"📈 本周新热词建议:DeepSeek-V4 / Nano Banana 2 …,回复要加哪些"**,由用户确认后人工/半自动加入 YAML。
- 可选增强:额外订阅 1–2 个 AI 资讯聚合 RSS(如 Hacker News AI、机器之心)经 RSSHub 进流,扩大新词来源面。
- 容错:LLM 不可用则当天跳过,不影响主流程。

---

## 5. 数据模型 (MySQL)

> 全部经 `Repository` 接口访问,业务层不直接写 SQL,便于迁移。

- **items**:`id, source_type(youtube/x/bilibili/arxiv), external_id(uniq), title, url, author, published_at, raw_text, status(seen/matched/skipped/analyzed/pushed), created_at`
- **engagement_samples**:`id, item_id(fk), sampled_at, views, likes, comments`
- **analyses**:`id, item_id(fk), summary, highlights(json), recommendation, value_score, tier(major/normal), model_used, created_at`
- **pushes**:`id, item_id(fk), tier, digest_batch_id(nullable), pushed_at, status`

---

## 6. 配置 (YAML 示例)

> 以下默认值由 2026-06-14 的 `deep-research` 调研产出。**已核验 X handle 直接写入;YouTube channelId 仅写入调研中能确证的两个,其余用 `handle` 字段,部署时由程序解析成稳定 channelId**(避免写错 ID)。

```yaml
poll_interval_minutes: 5
rsshub_base_url: "http://localhost:1200"   # 本机部署的 RSSHub

sources:
  youtube_channels:        # 有 channel_id 的直接用;只有 handle 的部署时解析
    - { name: "Andrej Karpathy",        handle: "@AndrejKarpathy" }
    - { name: "Yannic Kilcher",         channel_id: "UCZHmQk67mSJgfCCTn7xBfew" }
    - { name: "Two Minute Papers",      handle: "@twominutepapers" }
    - { name: "3Blue1Brown",            handle: "@3blue1brown" }
    - { name: "Lex Fridman",            handle: "@lexfridman" }
    - { name: "Dwarkesh Patel",         handle: "@DwarkeshPatel" }
    - { name: "bycloud",                channel_id: "UCgfe2ooZD3VJPB6aJAnuQng" }
    - { name: "AI Explained",           handle: "@aiexplained-official" }
    - { name: "StatQuest",              handle: "@statquest" }
    - { name: "AI Coffee Break",        handle: "@AICoffeeBreak" }      # 部署时核验
    - { name: "ML Street Talk",         handle: "@MachineLearningStreetTalk" }  # 部署时核验

  x_accounts: [ "karpathy", "ykilcher", "rasbt", "DrJimFan", "dwarkesh_sp",
                "bycloudai", "joshuastarmer", "lexfridman", "sama", "ylecun" ]

  bilibili_uids:           # UID 部署时按名字在 B站搜索确认(仅"跟李沐学AI"已知空间号)
    - { name: "跟李沐学AI",            uid: "1567748478" }
    - { name: "ZOMI酱",                uid: "" }
    - { name: "chaofa用代码打点酱油",   uid: "" }
    - { name: "飞天闪客",              uid: "" }
    - { name: "梗直哥",                uid: "" }
    - { name: "二次元的Datawhale",     uid: "" }

  arxiv_categories: [ "cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.RO" ]
  hf_daily_papers: true

# 关键词按主题分组管理(匹配时全部展开为一个集合,大小写不敏感,中英文均匹配)
keywords:
  前沿模型: [ "GPT-5.5", "Claude Opus 4.8", "Gemini 3.5", "DeepSeek-V4", "Qwen3.6",
             "Kimi K2", "GLM-5", "Grok 4", "Llama 4", "MoE", "1M context", "开源权重" ]
  Agent: [ "agentic engineering", "智能体", "multi-agent", "agent swarm", "MCP",
           "Model Context Protocol", "context engineering", "上下文工程", "LangGraph", "computer use" ]
  AI编程: [ "Claude Code", "Codex", "Cursor", "Windsurf", "Gemini CLI", "SWE-bench", "Devin" ]
  多模态视频: [ "Sora", "Veo", "Nano Banana", "Kling", "Runway", "图生视频", "lip-sync", "唇形同步" ]
  推理训练: [ "RLVR", "GRPO", "test-time compute", "推理模型", "reasoning model",
            "Mamba", "diffusion LLM", "扩散语言模型", "speculative decoding" ]
  具身智能: [ "VLA", "世界模型", "world model", "具身智能", "GR00T", "Optimus",
            "physical AI", "空间智能", "humanoid", "机器人" ]
  其他热点: [ "SLM", "小模型", "端侧", "on-device", "超级智能", "superintelligence", "RAG", "向量数据库" ]

engagement:
  enabled: true
  track_window_hours: 24
  sample_interval_minutes: 60

trendscout:
  enabled: true
  run_time: "08:30"
  lookback_days: 7
  mode: "suggest"            # suggest(推企微建议) | auto(自动并入)

llm:
  provider: "agnes"               # agnes | deepseek | gemini
  base_url: "${AGNES_BASE_URL}"   # 从 Agnes 后台文档获取
  model: "agnes-2.0-flash"
  api_key_env: "AGNES_API_KEY"
  fallback: "deepseek"

push:
  wecom_webhook_env: "WECOM_WEBHOOK_URL"
  major_value_threshold: 80
  digest_times: [ "09:00", "20:00" ]
```

**密钥**(`AGNES_API_KEY`、`WECOM_WEBHOOK_URL`、`YOUTUBE_API_KEY`)走**环境变量**,绝不硬编码。

---

## 7. 部署

- **阿里云香港轻量**(1核2G 起),Docker Compose 跑三个服务:
  1. `rsshub`(官方镜像,信源适配层)
  2. `mysql`
  3. `ai-radar`(本项目,Python)
- 无域名 / 无备案 / 无代理(香港节点直达 YouTube/X/arXiv;企微 webhook 全球可达)。
- 调度:进程内调度器(APScheduler)跑 5 分钟轮询 + 定时汇总 + 热度采样。

---

## 8. 错误处理与可观测性

- 每个外部调用(RSSHub / yt-dlp / Data API / LLM / 企微)都显式 try/except,失败记结构化日志,不静默吞错。
- 关键失败(LLM 全部不可用、企微连续推送失败)→ 单独告警(企微推一条"系统异常"提醒)。
- 幂等:去重库保证重启不重复推。

---

## 9. 测试策略

遵循 TDD + 80% 覆盖:
- **单元**:关键词匹配、去重逻辑、增速计算、分级函数、企微消息组装、LLM 适配器(mock)。
- **集成**:Collector→Filter→Fetcher→Analyzer→Notifier 全链路(mock 外部接口)。
- **降级路径**:字幕缺失、热度接口失败、Agnes 限速切备用,均需有用例覆盖。

---

## 10. 版本边界

- **v1**:YouTube + X + B站 + arXiv/HF;AI 深度解读;YouTube/B站 热度增速;**TrendScout 关键词自进化(建议模式)**;YAML 配置;分级推送;阿里云香港部署。
- **v2**:
  - **多角色评审团**(panel):对**重磅条目**用多个视角 LLM(技术新颖性/实用价值/适合谁/摘要)并行深挖,汇总成精读卡片;不拖慢普通条目的"第一时间"。
  - **每周深度盘点**:用多智能体(可由 Claude 离线 Workflow 跑)出一份"本周 AI 全景报告"。
  - 网页后台(IP:端口,无需域名)配置关键词/信源;arXiv/X 热度信号;X 官方 API(若需更稳)。
