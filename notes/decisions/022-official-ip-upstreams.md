---
id: D-022
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: superseded
supersedes:
doc: notes/rule-repo-design.md
---

# 接入 GitHub 与 Google 的官方网段

## 决定

- `github` 包以 `[[upstream]]` 接入 `https://api.github.com/meta`，kind 为 `github-meta`；`google` 包接入 `https://www.gstatic.com/ipranges/goog.json`，kind 为 `google-ipranges`。
- GitHub meta 只取客户端直接访问的键：`web`、`api`、`git`、`packages`、`copilot`，合并去重（键的取舍 Claude）。
- 不取的键：`hooks`、`importer`、`github_enterprise_importer` 是 GitHub 主动向外连接的出口；`actions`、`actions_macos` 是运行器所在的云网段，数量八千余条；`codespaces` 是用户虚拟机；`shared_ingress` 没有文档说明；`pages` 已被 `web` 的网段覆盖（Claude）。
- goog.json 取全部 `ipv4Prefix` 与 `ipv6Prefix`（Claude）。
- 任一所需键缺失、为空或网段无法解析时，构建失败，由人复核格式变化（Claude）。
- 请求 `api.github.com` 时带上 `GITHUB_TOKEN`，避免共享出口 IP 的匿名限流（Claude）。

## 备选

- 不接入：IP 直连请求与 DNS 被污染时的回退无从覆盖。
- 手工抄进清单：官方数据变动时清单落后，失去 `[[upstream]]` 每次同步的意义。
- 取 GitHub meta 的全部键：`actions` 等网段是共享云资源，会把无关流量送进代理。

## 缘由

两份数据都由服务方官方发布、语义稳定，符合设计文档对 `[[upstream]]` 的限定。按 D-020，发布仍在真机检测之后手动进行，上游变化只在审阅后进入设备。

2026-11-26 的数据：GitHub 五个键合并后 184 条（IPv4 182、IPv6 2），Google 148 条（IPv4 132、IPv6 16）；误伤检查与 gaoyifan/china-operator-ip 无重叠，构建通过。

goog.json 也包含 YouTube 的服务器网段；`youtube` 包没有 IP 规则，只按 IP 访问的 YouTube 流量会落到 `google` 包。
