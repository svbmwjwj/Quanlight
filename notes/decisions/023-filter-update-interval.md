---
id: D-023
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# 规则集关闭自动同步

## 决定

- 配置中 `[filter_remote]` 的每一行写 `update-interval=-1`，关闭自动同步；发布后在设备上手动更新（用户原话：“设为 -1 关闭”）。
- 范围：两份模板、本人的 `iOS.conf` 与 `macOS.conf`，以及构建器生成的发布说明片段。
- `[server_remote]` 与 `[rewrite_remote]` 有意保持原有的 `update-interval`，D-020 只涉及规则集。

## 备选

- 省略 `update-interval`：Quantumult X 对所有远程资源默认每 86400 秒自动同步一次，仍会自动更新，不符合 D-020。

## 缘由

D-020 要求规则集不设置自动更新时间。官方 `sample.conf` 说明默认同步间隔为 86400 秒，负数才关闭自动同步[^1]，因此只有显式写 -1 才能做到手动更新。

[^1]: https://raw.githubusercontent.com/crossutility/Quantumult-X/master/sample.conf （v1.5.5 build 914）第 117～118 行，`[server_remote]` 之前的注释：“The default sync interval for all kinds of remote resources is 86400 seconds.”
