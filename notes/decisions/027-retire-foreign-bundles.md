---
id: D-027
created: 2026-11-26
updated: 2026-11-26
type: overturn
source: user
status: active
supersedes: D-018, D-021, D-022, D-024
doc: notes/rule-repo-design.md
---

# 境外服务包只保留 APNs

## 决定

- 退役 `claude`、`crypto`、`google`、`telegram`、`twitter`、`github`、`linkedin` 七个包；这些服务由 `final` 的代理托底，不拆分策略，统一走一般代理（用户）。
- 保留 `apns` 包（D-008），订阅时排在直连列表前面，强制走代理（用户）。
- 随包退役的机制：`cn-exception` 与 `direct-exceptions.list`、`breadth = "broad"` 与复核日期（Claude）。
- D-022 接入的 GitHub、Google 官方网段不再进入产物，改作反向检查的数据：大陆 IP 列表与它们不得重叠（Claude）。

## 被推翻的原判断

- D-018、D-021：加密货币合并为一个包，`telegram`、`twitter`、`github`、`linkedin` 各自独立，以便分别指定策略。
- D-022：`github`、`google` 包接入官方网段作为代理规则。
- D-024：YouTube 并入 `google` 包。

## 备选

- 保留 `claude`、`crypto` 以走 `ai`、`crypto` 策略：用户暂时不需要拆分策略。
- APNs 也交给托底：直连数据或境内 DNS 若把推送服务器判为直连，Telegram 等应用就收不到通知，显式规则可以先截住。

## 缘由

改为代理托底后（D-026），未命中的境外流量本来就走代理，境外服务包只在需要单独指定策略时才有用。用户表示暂时不拆策略；同时指出 APNs 直连时 Telegram 这类通知收不到，所以 APNs 必须显式走代理。
