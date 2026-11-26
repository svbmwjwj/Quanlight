---
id: D-018
created: 2026-11-26
updated: 2026-11-26
type: overturn
source: user
status: active
supersedes: D-012
doc: notes/rule-repo-design.md
---

# 加密货币服务合并为一个包

## 决定

加密货币相关的钱包、交易所与链上服务，以及它们共用的 WalletConnect 中继，合并为一个 `crypto` 包。拆分粒度改为：同一类、通常走同一策略的服务合并为一个包；需要单独指定策略或单独开关的产品才独立成包。D-012 的其余服务范围不变。

## 被推翻的原判断

D-012 按一个产品一个包拆分，加密货币分成 8 个包，另有共享包 `shared-walletconnect`。

## 备选

- 保持一个产品一个包：订阅行数多，而这些服务实际都走同一个 `crypto` 策略。

## 缘由

用户认为规则集划分太细，加密货币可以汇总在一起。“同类合并”的一般规则由 Claude 从这一要求推出，待用户确认是否也适用于其他服务。
