---
id: D-008
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# 推送服务单独成包并走代理

## 决定

Apple 推送服务（APNs）作为独立的服务包，统一走代理，不与任何具体应用捆绑。

## 备选

- 放进 Telegram 包：APNs 是所有应用共用的通道，捆绑后语义不清，订阅关系也会重复。
- 走直连：Telegram 等境外应用的推送可能不稳定。

## 缘由

Telegram 等应用依赖 APNs 推送，用户接受“节点中断时所有应用的推送一起中断”的代价，并要求把推送服务统一设为代理。
