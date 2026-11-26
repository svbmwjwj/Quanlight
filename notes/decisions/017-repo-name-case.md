---
id: D-017
created: 2026-11-26
updated: 2026-11-26
type: overturn
source: user
status: active
supersedes: D-001
doc: notes/rule-repo-design.md
---

# GitHub 仓库名首字母大写

## 决定

GitHub 仓库名为 `Quanlight`。本地开发目录 `~/Developer/quanlight`、本机数据目录 `~/.config/quanlight/` 与 Python 包名 `quanlight` 保持小写。

## 被推翻的原判断

D-001 把仓库、本地开发目录与本机数据目录统一命名为全小写的 `quanlight`。

## 备选

- 本地目录也改为大写：与 `~/Developer` 下其他项目的小写命名不一致，也违反全局命名规则中目录用 kebab-case 的约定。

## 缘由

用户要求仓库名首字母大写。本地目录与包名保持小写由 Claude 决定，以遵循命名规则与 Python 包名惯例。
