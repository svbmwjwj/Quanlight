---
id: D-021
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# Telegram、Twitter、GitHub、LinkedIn 保持独立成包

## 决定

`telegram`、`twitter`、`github`、`linkedin` 四个包保持独立，不按 D-018 的“同类合并”合成一个包。D-018 的合并只适用于加密货币服务。

## 备选

- 四个全部合并为一个包：订阅行数最少，但只能统一指定一个策略。
- Telegram、Twitter、LinkedIn 合并为社交包，GitHub 独立。

## 缘由

用户在 D-018 之后被问到同类合并规则是否推广到其他服务，选择保持独立，各包可以分别指定策略与开关。
