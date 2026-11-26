---
id: D-003
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# 不以设备内存为约束

## 决定

规则集的取舍只看是否科学、完善，不考虑规则条数与 iPhone 上 Quantumult X 的内存占用。

## 备选

- 控制总条数：以去重和精简为目标之一，必要时牺牲覆盖。

## 缘由

用户明确不在意 iPhone 上的内存占用。设计文档原有的“精简”目标随之删除，待定事项中的内存调研取消。
