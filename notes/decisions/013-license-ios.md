---
id: D-013
created: 2026-11-26
updated: 2026-11-26
type: research
source: claude
status: active
supersedes: D-005
doc: notes/rule-repo-design.md
---

# 构建代码与 iOS 产物均为 MIT

## 决定

构建代码与 iOS 产物均以 MIT 发布。NOTICE 列出产物的数据来源：v2fly/domain-list-community（MIT，保留其版权声明）、Telegram 官方公布的网段、旧配置中本人整理的规则。第 3 阶段若使用 gfwlist（LGPL-2.1），相关产物的许可证届时重新判断。

## 备选

- 沿用 D-005，产物以 LGPL-2.1 发布：D-005 的依据是产物含 gfwlist 数据，iOS 服务包不使用 gfwlist，这个依据不成立。

## 缘由

D-007 把配置拆成 iOS 黑名单与 macOS 白名单后，iOS 服务包的数据只来自 v2fly、官方公布的网段与手写规则，均无 copyleft 约束。检查用的 dnsmasq-china-list 与 gaoyifan/china-operator-ip 只用于构建时检查，不进入产物。这是基于许可证文本的推断，不是法律意见。
