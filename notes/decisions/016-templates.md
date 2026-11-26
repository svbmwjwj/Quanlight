---
id: D-016
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# 私人配置留在本机，仓库提供模板

## 决定

本人的 iOS 与 macOS 配置只放在 `~/.config/quanlight/configs/`。仓库的 `templates/` 提供可直接借鉴的模板，去掉私人订阅、密钥、节点检测脚本、MITM 证书、个人域名与个人金融服务的规则，用 `<...>` 占位。

## 备选

- 不提供模板：其他人需要从零拼装订阅顺序与策略。

## 缘由

用户要求私人配置放在本机隐私目录，仓库中要有其他人可以直接借鉴、去掉隐私信息的模板。
