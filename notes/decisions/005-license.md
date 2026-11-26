---
id: D-005
created: 2026-11-26
updated: 2026-11-26
type: research
source: claude
status: superseded
supersedes:
doc: notes/rule-repo-design.md
---

# 代码 MIT，产物 LGPL-2.1

## 决定

仓库的构建代码以 MIT 发布。发布分支上的产物以 LGPL-2.1 发布，附 COPYING 全文，并用 NOTICE 列出各数据源与许可：dnsmasq-china-list（WTFPL）、v2fly/domain-list-community（MIT，保留其版权声明）、gfwlist（LGPL-2.1）、gaoyifan/china-operator-ip（MIT）。

## 备选

- 整个仓库用 GPL-3.0：同类项目 Loyalsoldier/v2ray-rules-dat、MetaCubeX/meta-rules-dat 都这样做，但构建代码也会受约束。
- 整个仓库用 MIT：`proxy.list` 由 gfwlist 派生，与 LGPL-2.1 冲突。

## 缘由

LGPL 的约束只落在由 gfwlist 派生的数据上，构建代码不是其派生作品。代码与产物分在不同分支，各自携带许可文本即可。这是基于许可证文本的推断，不是法律意见；域名清单是否构成受版权保护的作品本身也有争议。
