---
id: D-010
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: superseded
supersedes:
doc: notes/rule-repo-design.md
---

# 先建规则库，再做 iOS，最后做 macOS

## 决定

分三个阶段：先搭建规则库骨架（结构、清单格式、构建、检查、发布），再做 iOS 黑名单的服务包，最后做 macOS 白名单。

## 备选

- 先做 macOS 白名单：已有较完整的设计，但用户的手机使用更迫切。

## 缘由

用户明确要求先搭建自己的规则库，再设计 iOS 的配置。
