---
id: D-012
created: 2026-11-26
updated: 2026-11-26
type: overturn
source: user
status: superseded
supersedes: D-011
doc: notes/rule-repo-design.md
---

# 首批服务包补回链上服务

## 决定

iOS 首批服务包的范围：

- Google 与 YouTube 分成两个包，Gmail、Google Play 归入 Google 包。
- 加密货币：Rainbow、Phantom、Kraken，以及旧配置中手写的 Uniswap、Etherscan、Hyperliquid、Arweave、IPFS，各自成包；币安不收录（选择依据见私密笔记）。
- Claude 包尽可能完整，以 macOS 配置中整理的 Claude 规则为起点。
- Telegram、Twitter、GitHub、LinkedIn 沿用旧 `iOS.conf` 中已启用的订阅范围。

## 被推翻的原判断

D-011 只收 Rainbow、Phantom、Kraken，旧配置中的 Uniswap、Etherscan、Hyperliquid、Arweave、IPFS 不再收录。

## 备选

- 维持 D-011：这些服务在默认直连下会直连。

## 缘由

用户要求把旧配置中手写的这些链上服务也加上。
