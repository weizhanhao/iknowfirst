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

---

## 5. 数据模型 (MySQL)

> 全部经 `Repository` 接口访问,业务层不直接写 SQL,便于迁移。

- **items**:`id, source_type(youtube/x/bilibili/arxiv), external_id(uniq), title, url, author, published_at, raw_text, status(seen/matched/skipped/analyzed/pushed), created_at`
- **engagement_samples**:`id, item_id(fk), sampled_at, views, likes, comments`
- **analyses**:`id, item_id(fk), summary, highlights(json), recommendation, value_score, tier(major/normal), model_used, created_at`
- **pushes**:`id, item_id(fk), tier, digest_batch_id(nullable), pushed_at, status`

---

## 6. 配置 (YAML 示例)

```yaml
poll_interval_minutes: 5

rsshub_base_url: "http://localhost:1200"   # 本机部署的 RSSHub

sources:
  youtube_channels:        # RSSHub 路由会据此生成 feed
    - { name: "Karpathy",        id: "UCXUPKJO5MZQDB_Q1bL1lwww" }
    - { name: "TwoMinutePapers", id: "UCbfYPyITQ-7l4upoX8nvctg" }
    - { name: "LexFridman",      id: "UCSHZKyawb77ixDdsGog4iWA" }
  x_accounts:    [ "sama", "karpathy", "ylecun" ]
  bilibili_uids: [ ]
  arxiv_categories: [ "cs.AI", "cs.CL", "cs.LG" ]

keywords: [ "Sora", "GPT", "Gemini", "多模态", "RAG", "Agent", "具身智能", "扩散模型", "强化学习" ]

engagement:
  enabled: true
  track_window_hours: 24
  sample_interval_minutes: 60

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

- **v1**:YouTube + X + B站 + arXiv/HF;AI 深度解读;YouTube/B站 热度增速;YAML 配置;分级推送;阿里云香港部署。
- **v2**:网页后台(IP:端口,无需域名)配置关键词/信源;arXiv/X 热度信号;X 官方 API(若需更稳)。
