---
id: D-024
created: 2026-11-26
updated: 2026-11-26
type: overturn
source: user
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# YouTube 并入 google 包

## 决定

`youtube` 包的规则并入 `google` 包，不再单独成包；`google` 包不再排除 v2fly 的 `include:youtube`。

## 被推翻的原判断

D-012 让 YouTube 单独成包，`google` 包排除 `include:youtube`。D-012 的其余服务范围不变。

## 备选

- 保持独立，并给 `youtube` 包补上 YouTube 的 IP 网段：`goog.json` 不区分 YouTube 与其他 Google 服务，无法拆出。

## 缘由

D-022 接入的 `goog.json` 含 YouTube 服务器网段，只凭 IP 访问的 YouTube 流量本来就会命中 `google` 列表；用户据此决定两者合二为一，不再拆分。

## 影响

发布后 `release` 分支不再有 `ios/youtube.list`，订阅了它的配置须删掉这一行；发布前删掉则 YouTube 暂时失去代理。
