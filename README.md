# Daily PM Growth Brief

一个低维护、低 token 成本的每日行业简报自动化项目。

它会每天自动抓取 AI、产品工具、电商平台、零售媒体、广告和中国科技零售动态，生成一份中文 Markdown 简报，并定时同步到飞书文档。这个仓库适合：

- 想给自己搭一个“每天打开就能看”的行业晨报的人
- 想学习如何用 GitHub Actions + Python + 飞书文档做轻量自动化的人
- 想做“弱网可退化、质量不够就不乱发”的内容自动化的人

## 项目特点

- 几乎不依赖大模型：默认链路主要是 RSS 抓取、规则评分、回退策略和飞书写回
- 可云端定时运行：电脑关机也能生成并推送
- 有质量保护：抓不到足够好的内容时，保留上一份高质量简报
- 有多级回退：`live -> candidates -> feed_cache -> archive -> preserve`
- 只依赖 Python 标准库，部署轻

## 适合公开学习的点

- 如何做“每天自动更新”的个人情报系统
- 如何设计 source health / feed cache / archive fallback
- 如何把 Markdown 内容直接同步到飞书 wiki / docx
- 如何在 GitHub Actions 里跑一个近乎零 token 消耗的内容流水线

## 云端每日运行

项目已内置 GitHub Actions workflow：

```text
.github/workflows/daily-pm-brief.yml
```

它会在每天 **Asia/Shanghai 08:40 / 08:55 / 09:10** 触发兜底调度，并把最新简报追加写回飞书文档：

```text
https://my.feishu.cn/wiki/S466w3hCViJ4qNk6iiicURt8nsb
```

### 需要的仓库 Secrets

在 GitHub 仓库中配置：

- `LARK_APP_ID`
- `LARK_APP_SECRET`

workflow 会用这两个值在云端非交互初始化 `lark-cli`，然后用 **bot 身份** 更新飞书文档，因此不依赖本机登录态，也不需要每天手动续 user token。

### 飞书侧前置条件

目标 wiki / 文档必须允许这个飞书应用访问，否则云端能生成简报，但无法写回文档。最稳妥的做法是：

1. 确认应用已开通文档 / wiki 相关 scopes。
2. 把目标 wiki 页面或所在知识库分享给该应用 / bot。
3. 手动在本机先验证一次：

```bash
python3 scripts/run_daily_brief_cloud.py
```

如果你只想验证生成、不写回飞书：

```bash
python3 scripts/run_daily_brief_cloud.py --skip-publish
```

## 快速运行

```bash
python3 -m pm_brief.cli
```

生成文件会写入：

```text
reports/YYYY-MM-DD.md
```

每天固定阅读入口会写入：

```text
reports/today.md
```

你可以把 `reports/today.md` 固定到常用编辑器、Obsidian、Finder 侧边栏或 Codex 工作区里。每天自动化运行后，这个文件会更新为当天简报。

历史候选与评分会追加到：

```text
data/archive.jsonl
```

成功抓到的实时文章还会缓存到：

```text
data/feed_cache.json
```

## 配置来源

编辑 `config/sources.json` 可以调整：

- `sources`：RSS 来源、分类、可信度、语言、是否启用。
- `manual_sources`：暂不稳定自动抓取、但值得人工关注的来源，例如小红书账号、播客、YouTube 创作者主页。
- `lookback_days`：抓取最近几天内容。
- `limit_per_source`：每个来源最多抓取多少条。
- `weights`：评分权重。当前采用 Impact 30%、Novelty 25%、Source Quality 20%、PM Relevance 15%、Actionability 10%。

当前系统只会自动抓取 `sources` 中 `enabled: true` 的 RSS/Atom/YouTube RSS。小红书、部分播客和没有稳定 RSS 的创作者主页放在 `manual_sources`，用于人工补充和后续扩展，不参与每日自动抓取。

## 云端运行入口

云端推荐直接执行：

```bash
python3 scripts/run_daily_brief_cloud.py
```

这个脚本会顺序执行：

1. `validate_sources.py`
2. 先检查飞书文档里是否已经存在“当天日期”的标题；如果已经发布，直接退出，不再重复生成
3. `pm_brief.cli`
4. 用 `lark-cli` 将最终 Markdown 追加写回飞书 wiki

如果当天网络异常、候选不足或回退内容太弱，脚本不会硬发低质量新稿，而是保留上一份高质量简报并把保留版本以“当天说明”的形式追加到飞书，不会覆盖掉历史简报。

## 运行健康状态

每次生成后会写入：

```text
reports/status.md
```

这个文件记录本次运行日期、启用来源数、抓取条数、候选条数、入选条数、失败来源，以及是否保留了已有报告。看到 `today.md` 没更新时，先看 `reports/status.md` 可以区分是自动化没跑、抓取失败，还是当天没有高质量候选。

状态里新增了：

- `Live article count`：本次真正从外部源实时拿到的文章数。
- `Fallback mode`：当前走的是 `none`、`feed_cache`、`archive` 还是 `preserved`。

## 来源健康检查

低成本排查 RSS 问题时先运行：

```bash
python3 scripts/validate_sources.py
```

脚本会并发检查 `config/sources.json` 中的自动源，并更新：

```text
data/source_health.json
```

连续失败达到 `source_failure_threshold` 的来源会被标记为 `unstable`。日报生成默认跳过 unstable 来源，避免坏源拖慢每日自动化。重要来源可以在配置中设置：

```json
"failure_policy": "always_try"
```

这样即使历史状态为 unstable，也会继续尝试抓取。

## 联网候选兜底

如果本地 RSS 抓取失败或候选不足，可以先用联网检索生成候选 JSON，再交给同一套评分和模板：

```bash
python3 -m pm_brief.cli --candidates-file data/candidates/YYYY-MM-DD.json
```

候选文件格式见 `docs/candidate-schema.md`。每日自动化应在本地抓取候选不足时使用这个兜底路径，目标是保证每天有足够量的高质量来源进入筛选。

## 回退顺序

当前生成链路按以下顺序回退：

1. 实时抓取的 live feed 内容
2. 外部研究补写的 candidates 文件
3. 近几天成功抓取过的 `feed_cache`
4. 本地 `archive` 历史候选
5. 若回退后仍没有足够强的 Must Read / AI Watch，则保留上一份有效 `today.md`

这保证了两个目标同时成立：

- 网络正常时，优先输出当天的新鲜高质量内容。
- 网络异常时，不会把 `source_health.json` 错误污染，也不会硬生成一份低质量日报。
- GitHub Actions 即使触发多次，也只会在“当天还没发布”时真正生成一次，因此不会按触发次数重复消耗 token。

## Token 成本

当前云端方案几乎不依赖模型推理：

- 来源抓取、评分、筛选、回退、飞书写回全部是 Python + RSS + `lark-cli`
- 不需要每天调用大模型总结全文
- 只有你后续主动引入“联网研究候选 + AI 摘要增强”时，token 消耗才会明显上升

这也是目前最适合“每日稳定自动跑”的低成本方案。

## 输出结构

每份简报包含：

1. Today’s One-Line Signal
2. Must Read
3. AI Product Watch
4. Marketplace & Seller Growth
5. PM Thinking
6. 5-Minute Learning Card
7. 原文阅读清单
8. 今日归档标签

## 运行测试

```bash
python3 -m unittest discover -s tests
```

## 设计原则

- 少而精：没有足够重要的内容时不强行凑数。
- 可溯源：每条内容保留原文链接、来源、发布时间。
- 可维护：第一版只依赖 Python 标准库，避免本地环境被依赖问题卡住。
- 可扩展：Markdown 是主格式，后续可以加 HTML、PDF、飞书文档或邮件推送。
