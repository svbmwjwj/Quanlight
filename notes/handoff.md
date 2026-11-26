---
created: 2026-11-26
updated: 2026-11-26
---

# Quanlight 交接

## 2026-11-26（初版）

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

## 2026-11-26（协调会话）

### 状态更新

- 手机：本人确认已从 iCloud 备份恢复 Quantumult X 配置，MitM 已重新打开。
- 决策编号预留：D-021 本会话已写；D-022 归官方 IP 数据子对话；D-023 归发布流程子对话；D-024 归匹配模型子对话。

### 本人决定

- 待办 4a：GitHub `api.github.com/meta` 与 Google `goog.json` 两者都接入为官方数据（D-022，由子对话写）。
- 待办 4b：Telegram、Twitter、GitHub、LinkedIn 保持独立成包（D-021，已写入设计文档“服务包”一节）。
- 待办 3：稍后再开，等匹配模型改完、本人在手机旁时进行。
- 规则集自动更新：官方 `sample.conf` 写明省略 `update-interval` 时默认每 86400 秒同步一次；本人决定写 `update-interval=-1` 关闭自动同步（D-023，由发布流程子对话写）。

### 子对话

各在自己的 worktree 分支上提交，不推送、不合并；合并到 `main` 前须经本人同意。

- 待办 1，匹配模型：会话 `match-type-priority`，分支名含 `type-priority-matching`；只改 `match.py`、`check.py`、相关测试与设计文档“构建与检查”一节。
- 待办 2，发布流程：会话 `manual-release`，分支名含 `manual-release`；只改工作流、模板、私人配置与设计文档“发布与订阅”一节。
- 待办 4a，官方 IP 数据：会话 `official-ip-upstreams`，分支名含 `official-ip-upstreams`；只改 github、google 清单、上游同步代码与设计文档“参考数据的导入”一节。

### 仍待开始

- 待办 3：真机观测，用 Quantumult X 自带的配置编辑与 MitM 加“HTTP 抓取”，本人在场安装临时证书。
- 待办 5、6 不变。

### 子对话结果（均未推送、未合并）

- 待办 1：分支 `claude/type-priority-matching-c9041b`，提交 `c7b715a`；71 个测试通过，构建产物与改动前逐字节相同。类型顺序 `host` > `host-suffix` > `host-wildcard` > `host-keyword`，后三者为社区说法、暂定；D-024 未用。
- 待办 2：分支 `claude/manual-release-8b7666`，提交 `40148f4`、`8f816a0`、`9de75c7`；65 个测试通过。定时与推送只做试构建并在 Actions 摘要中报告与 `release` 的差异；发布须在 Actions 页面手动运行 `build` 并勾选 `publish`；读取 `release` 失败时发布直接失败。`[filter_remote]` 统一 `update-interval=-1`（D-023），节点与重写订阅不变。工作流 YAML 只做了解析，未跑 actionlint。
- 待办 4a：分支 `claude/official-ip-upstreams-55f065`，提交 `e3b6eff`、`0e0d97d`；80 个测试通过，构建通过，与大陆网段无重叠。GitHub 取 `web`、`api`、`git`、`packages`、`copilot` 共 184 段；Google 取全部 148 段（D-022）。

### 新发现的待议事项

- 包顺序检查：`cross_check()` 的“更具体的包在前”仍按列表顺序判断；类型优先后，前面包的 `host-suffix` 不再遮住后面包的 `host`，`claude` 须排在 `google` 前这条约束可能过严。
- YouTube 的 IP：`goog.json` 含 YouTube 服务器网段，`youtube` 包没有 IP 规则，只凭 IP 访问的 YouTube 流量会命中 `google` 列表。

### 合并与后续（同日）

- 三个子对话的分支已合并进 `main`（`9347daf`、`b7f1298`、`32883d0`），合并后测试与本地构建通过。
- YouTube 并入 `google` 包（本人决定，D-024，`c83eb5f`）。发布后 `release` 不再有 `ios/youtube.list`；私人配置 `iOS.conf` 的 `youtube` 行要在发布之后再删，之前删会让 YouTube 暂时失去代理。
- 包顺序检查改为对每条 `host`、`host-suffix`、`host-wildcard` 规则用模拟器实际路由，须先命中本包（`f0e895f`）。原检查对“后面包的 `host` 落在前面包的 `host-suffix` 下”误报，且不检查通配符被后面包的后缀抢走的情况。
- 待办 3 已开子对话 `device-observation`，本人在场；它负责 claude、apns、telegram、twitter、github、linkedin、crypto 清单，google 相关发现只写进报告。另请它验证 Telegram 等应用的通知在 APNs 走代理时能到达（本人指出 APNs 必须走代理）。
- macOS 第 3 阶段：本人决定暂不做。
- 首次人工发布：等真机观测通过后，在 Actions 页面手动运行 `build` 并勾选 `publish`。

### 暂停（同日）

- 本人出门，真机观测暂停。子对话 `device-observation` 的交接笔记在共享笔记目录 `device-observation-handover.md`；分支 `claude/device-observation-db6446` 有 D-025（`1767b1f`），尚未合并。
- D-025：“分流匹配优化”开启时类型顺序为 `host` > `host-suffix` > `host-wildcard` > `host-keyword`，与 `match.py` 的暂定顺序一致；关闭时主机规则按加载顺序匹配。
- 已观测：Claude 应用（`claude.ai`、Sift、Datadog、Sentry 走 `ai`，`fcmtoken.googleapis.com` 命中 google）。未观测：claude.ai 网页记录、其余应用、Telegram 推送。
- WDA 运行器已停止；回来后按 `~/tools/wda/README.md` 重新启动。

## 2026-11-26（新对话入口）

前面各节是过程记录；新对话从本节读起，需要细节时再回看。

### 当前状态

- `main`：工作区干净，本地提交均未推送到 `origin/main`；`release` 分支仍是第一次自动发布的旧产物。
- 已合并：匹配模型（类型优先）、人工发布（D-023）、官方 IP 数据（D-022）、YouTube 并入 google（D-024）、包顺序检查改用模拟器。
- 未合并：分支 `claude/device-observation-db6446` 的 `1767b1f`，只含 D-025 决策文件；清单未改。合并后还要在设计文档“构建与检查”一节补 D-025 标注。
- 残留 worktree：`.claude/worktrees/` 下四个，其中三个子对话分支已合并，可在本人同意后清理。
- 旧会话：协调会话 `quanlight-next` 与子对话 `device-observation` 均已停下，不再使用。

### 真机观测的恢复资料

- 详细交接在私密笔记 `~/.config/quanlight/notes/device-observation-handover.md`（含局域网地址，不进仓库）。
- 要点：Claude 应用已观测；claude.ai 网页记录已采集未读出；Telegram、X、GitHub、LinkedIn、Google、加密货币应用与 APNs 通知未做。
- 暂定收窄：`siftscience.com` 可改为 `host, api3.siftscience.com`；其余 broad 条目待网页记录。
- 手机：暂停时用的是 `ios-lan-probe.conf`（带 4 个探针列表与局域网列表源），本人出门前应已切回 `ios-phone_bak_20261126.conf`；恢复观测时先确认手机当前配置。

### 待本人决定

- 是否合并 D-025 分支、是否推送 `main`。
- 真机观测何时继续（需本人在场）。
- 观测通过后首次人工发布：Actions 页面手动运行 `build` 并勾选 `publish`；发布后再从私人 `iOS.conf` 删去 `youtube` 行。
- 观测结束时：保留 `iOS.conf` 还是恢复备份，是否删除临时证书 `5B974D20`。

### 其余待办

- 待办 6 的次要问题不变；macOS 第 3 阶段暂不做。
