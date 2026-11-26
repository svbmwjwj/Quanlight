---
created: 2026-11-26
updated: 2026-11-26
---

# Quanlight 第 2 阶段实现计划

执行方式：本会话逐任务实现（superpowers:executing-plans），最后做一次整体审查。

## 概要

- 目标：建成 iOS 首批服务包，私人配置与模板改为订阅这些包。
- 设计文档：`notes/rule-repo-design.md`，执行时与本计划一起读。
- 构建器不改动；每个包是 `bundles/<name>.toml` 加若干样本，由现有的误伤检查、交叉检查和样本测试把关。
- 探针结果尚未出来。有包含关系的包（Claude 与 Google、Google 与其大陆节点例外）按“窄的在前，且尽量用 `host`”安排，两种匹配语义下结论一致。

## 全局约束

- 每条规则按设计文档“规则类型的选用”选最窄类型；`host-suffix` 只用于该服务独有的域名。
- v2fly 导入后逐条审核；只作为 CNAME 目标出现的主机（如 `*.map.fastly.net`、`*.akamaiedge.net`）不收录，写进 `v2fly_ignore`。
- `breadth = "broad"` 条目必须写 `reason` 与 `review_by`，复核日期统一为 `2027-02-28`。
- `ip-asn` 必须写 `asn_verified`，记录查询来源与日期。
- 每个包至少两条样本：一条必须命中该包，一条相近但必须直连的主机。
- 每完成一个任务运行 `uv run pytest -q` 与 `uv run quanlight build --out dist`，两者都通过才提交。

## 订阅顺序

| order | 包 | 理由 |
|---|---|---|
| 10 | `apns` | 已有 |
| 20 | `claude` | 含 `maps.googleapis.com`，须在 `google` 之前 |
| 30～37 | `rainbow`、`phantom`、`kraken`、`uniswap`、`etherscan`、`hyperliquid`、`arweave`、`ipfs` | 互不包含 |
| 40 | `telegram` | 已有 |
| 50 | `twitter` | |
| 60 | `github` | |
| 70 | `linkedin` | |
| 80 | `youtube` | |
| 90 | `google` | 覆盖面最宽，排最后 |

## 任务 1：Twitter、GitHub、LinkedIn、YouTube

- [ ] 用 `import-v2fly` 生成四个包的初稿，`order` 按上表。
- [ ] 审核：
  - `twitter`：`twitter.map.fastly.net` 为 CNAME 目标，移入 `v2fly_ignore`。
  - `github`：S3 与 Azure Blob 上的 `full:` 主机是客户端直接请求的下载与日志主机，保留为 `host`；`npmjs`、`github-copilot` 随 v2fly 一并收录。
  - `linkedin`：`l-0005.dc-msedge.net`、`l-0005.l-msedge.net` 是微软共享边缘节点，改为 `host`；`full:e122475.dscg.akamaiedge.net` 为 CNAME 目标，移入 `v2fly_ignore`；`@cn` 条目成为直连例外。
  - `youtube`：逐条确认后缀归 YouTube 或 Google 独有。
- [ ] 样本：`x.com`、`pbs.twimg.com` 期望 `twitter`；`github.com`、`objects.githubusercontent.com` 期望 `github`；`www.linkedin.com` 期望 `linkedin`；`www.youtube.com`、`i.ytimg.com` 期望 `youtube`；`www.bilibili.com` 期望 `direct`。
- [ ] 构建通过后提交 `feat: add twitter, github, linkedin and youtube bundles`。

## 任务 2：Google

- [ ] `import-v2fly google --bundle google --order 90 --exclude youtube`。
- [ ] 审核：展开后的各文件（Android、Firebase、Flutter、Go、Kaggle 等）均为 Google 所有，后缀保留；CNAME 目标移入 `v2fly_ignore`；`@cn` 条目成为直连例外。
- [ ] 构建，逐条处理误伤：确属 Google 且在大陆可直连的，标为 `cn-exception`；确属国内服务的，从包中删除或改为更窄的规则。
- [ ] 样本：`www.google.com`、`mail.google.com`、`play.googleapis.com` 期望 `google`；直连例外中任选两条期望 `direct`。
- [ ] 提交 `feat: add google bundle`。

## 任务 3：Claude

- [ ] 合并 v2fly `anthropic` 与旧 macOS 配置中整理的 Claude 规则，`order = 20`。
- [ ] 规则类型：
  - 核心域名用 `host-suffix`。
  - Sentry 用 v2fly 提供的专属主机 `o1158394.ingest.us.sentry.io`，不再整域收录 `sentry.io`。
  - Datadog 用 `browser-intake-us5-datadoghq.com` 与 v2fly 的 `http-intake.logs.us5.datadoghq.com`。
  - `statsigapi.net`、`intercom.io`、`intercomcdn.com`、`withpersona.com`、`frompersona.com` 为多租户平台，按 `broad` 收录。
  - Sift：只收其独有域名，按 `broad` 收录；三条旧关键词规则不再使用。
  - `maps.googleapis.com` 用 `host`。
  - IP：`160.79.104.0/21`、`2607:6bc0::/32`；ASN 399358 先查询归属，确属 Anthropic 才收录。
- [ ] 样本：`claude.ai`、`api.anthropic.com`、`maps.googleapis.com` 期望 `claude`；`fonts.googleapis.com` 期望 `google`。
- [ ] 提交 `feat: add claude bundle`。

## 任务 4：加密货币

- [ ] 八个包，`order` 30～37，各自成包：
  - `kraken`：v2fly `kraken`。
  - 其余以旧 iOS 配置的手写规则为起点，`source = "legacy:ios"`：`phantom.app`、`rainbow.me`、`uniswap.org`、`etherscan.io`、`hyperliquid.xyz`、`arweave.net`、`ipfs.io`。
  - `arweave.net` 与 `ipfs.io` 的网关使用子域，改为 `host-suffix`。
- [ ] 样本：每个包的主域名期望该包。
- [ ] 提交 `feat: add crypto bundles`。

## 任务 5：模板与私人配置

- [ ] `templates/ios.conf` 按订阅顺序列出全部服务包；Claude 用 `ai` 策略，加密货币用 `crypto` 策略，其余用 `proxy`。
- [ ] 私人 `~/.config/quanlight/configs/iOS.conf`：先备份，再把 Google、LinkedIn、GitHub、Twitter、加密货币的原订阅与本地 Claude、加密货币规则换成对应的 Quanlight 包；未覆盖的服务（如已关闭的 OpenAI、Gemini 订阅）保持原样。
- [ ] 提交 `docs: list all bundles in the iOS template`。

## 任务 6：审查与发布

- [ ] 独立审查者检查全部清单的规则类型与误伤豁免。
- [ ] 修正重要问题后推送，确认 Actions 构建成功、各镜像地址可下载。
