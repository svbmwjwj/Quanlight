---
created: 2026-11-26
updated: 2026-11-26
---

# Quanlight 交接

## 2026-11-26

### 必读

- 设计文档：`notes/rule-repo-design.md`；决策日志：`notes/decisions/`（D-001～D-020，被取代的已标 `superseded`）。
- 项目约定：仓库根目录 `CLAUDE.md`（注释用中文、仓库名大写而链接小写、私人配置不进仓库）。
- 私密补充：`~/.config/quanlight/notes/rule-repo-design.md`（加密货币服务的选择依据，不进仓库）。

### 现状

- 仓库：GitHub `svbmwjwj/Quanlight`，公开；本地 `~/Developer/quanlight`，分支 `main`，与远程同步。
- 构建器：`src/quanlight/`，65 个测试通过（`uv run pytest -q`）。本地构建要用 `GITHUB_TOKEN=$(gh auth token) uv run quanlight build --out dist`，否则会触发 GitHub API 未登录限额。
- 发布：`.github/workflows/build.yml` 目前每天北京时间 02:00 与推送 `main` 时自动构建并发布到 `release` 分支（D-020 要求改为人工发布，尚未实施）。
- iOS 服务包：`apns`、`claude`、`crypto`、`telegram`、`twitter`、`github`、`linkedin`、`youtube`、`google`，加 `direct-exceptions` 共 10 个列表。
- 订阅地址：`https://raw.githubusercontent.com/svbmwjwj/quanlight/release/ios/<名>.list`；境内镜像在前面加 `https://ghfast.top/`（D-015）。
- 模板：`templates/ios_blacklist.conf`、`templates/macos_whitelist.conf`。
- 私人配置：`~/.config/quanlight/configs/`。
  - `iOS.conf`：已改为订阅 Quanlight 全部 iOS 包的黑名单配置，尚未导入手机。
  - `ios-phone_bak_20261126.conf`：手机上原配置（代理托底）的导出备份，另有一份副本在 iCloud 的 `Quantumult X/Profiles/`。
- 手机：第一次探针后，本人需从 iCloud 导入上述备份并重新打开 MitM 开关；接手时先确认已恢复。

### 真机操作

- 工具：`~/tools/wda`（WebDriverAgent）。本次新增了 `apps/quantumultx.json`、`apps/safari.json`，含禁止点按的危险词。
- WDA 用免费开发者账号签名，约 7 天过期；过期时按 `~/tools/wda/README.md` 重建，团队 ID `VSUGQJ79G3`，并请本人在 iPhone 上信任开发者证书。
- 已知行为：
  - Quantumult X 更新规则资源后会自动重启隧道，重启前的请求记录会丢失；用 `wda.py start` 重新打开应用也会触发。
  - Quantumult X 拉取规则资源不经过自身隧道，访问不到 `[http_backend]` 提供的 `127.0.0.1:9999`。
  - 用 `xcrun devicectl device process launch --payload-url <网址> com.apple.mobilesafari` 可直接让 Safari 打开网址。
- 本人建议：以后用 Quantumult X 自带工具提高效率——在设置里直接“编辑”配置，用 MitM 加“HTTP 抓取”观察请求命中的规则；本人可以安装临时证书。

### 探针结论（D-019）

- 本地先于远程；`host` 先于 `host-suffix`，即使排在后面；同类型按订阅顺序；`*.x` 不匹配裸域名；主机规则不匹配 CNAME 目标。
- 未测：“分流匹配优化”开关的影响；`host-suffix`、`host-wildcard`、`host-keyword` 之间的优先级。

### 待办，建议各开一个子对话

1. 构建器匹配模型（代码）：把 `src/quanlight/match.py` 的 `route()` 与 `check.py` 的误伤检查改为 D-019 的“类型优先”语义，先写失败测试；同时更新设计文档“构建与检查”一节。
2. 发布流程（代码与 CI）：按 D-020 把每日任务改为只检测、只出报告；发布改为手动触发；模板与私人配置去掉 `update-interval`，确认 Quantumult X 省略该参数时的默认行为。
3. 真机观测与剩余探针（真机）：用 MitM 加“HTTP 抓取”补测“分流匹配优化”与类型优先级；按服务观测实际请求，收窄 Claude 包中 7 条 `broad` 条目，补漏掉的依赖。需要本人在场安装临时证书。
4. 待本人决定后再做：
   - 是否接入 GitHub `api.github.com/meta` 与 Google `gstatic.com/ipranges/goog.json` 的官方数据自动同步。
   - Telegram、Twitter、GitHub、LinkedIn 是否按 D-018 的同类合并规则合成一个包。
5. macOS 第 3 阶段（设计与代码）：直连列表、`macos_whitelist.conf` 中写死的 Claude 规则与 `host-keyword, ., main` 的取舍。
6. 延后的次要问题：
   - 清单缺字段时以 traceback 退出；IP 写法未规范化；检查数据无数量下限。
   - 工作流令牌作用域过宽；读取 `release` 失败时仍会推送；jsDelivr 刷新无重试。
   - LinkedIn 两条 `*-msedge.net` 可能是 CNAME 目标；IPFS 缺 `dweb.link` 等网关。
   - Uniswap、Etherscan、Hyperliquid 的来源仍写旧配置，每周差异报告跟踪不到。
