---
id: D-011
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: superseded
supersedes:
doc: notes/rule-repo-design.md
---

# iOS 首批服务包的范围

## 决定

- Google 与 YouTube 分成两个包，Gmail、Google Play 归入 Google 包。
- 加密货币收 Rainbow、Phantom、Kraken，各自成包；币安不收录（选择依据见私密笔记）。
- Claude 包尽可能完整，以 macOS 配置中整理的 Claude 规则为起点。
- Telegram、Twitter、GitHub、LinkedIn 沿用旧 `iOS.conf` 中已启用的订阅范围。

## 备选

- 加密货币沿用综合列表：会把大量不需要的交易所与链上服务送去代理。
- Claude 只收 claude.ai 与 API：遗漏身份验证、风控与遥测，这些部分直连会暴露所在地区。

## 缘由

用户确认了 YouTube 单独成包与加密货币服务包的范围，并要求 Claude 包参考其在 macOS 配置中的整理尽量覆盖完整。一个产品一个包的拆分粒度由 Claude 决定，便于分别指定策略。

由 D-012 取代。
