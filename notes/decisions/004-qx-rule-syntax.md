---
id: D-004
created: 2026-11-26
updated: 2026-11-26
type: research
source: claude
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# 产物只用官方规则类型

## 决定

产物只使用官方 `sample.conf` 列出的规则类型：`host`、`host-suffix`、`host-keyword`、`host-wildcard`、`ip-cidr`、`ip6-cidr`、`geoip`、`ip-asn`、`user-agent`。每行保留三列，不加 `no-resolve`；v2fly 的 `regexp:` 条目丢弃并计数。

## 备选

- 把正则转换为 `host-wildcard`：只有少数正则能等价转换，收益小于维护成本。
- 省略第三列：官方没有说明有 `force-policy` 时能否省略，未验证。

## 缘由

官方 `sample.conf` 第 257～277 行列出的类型里没有正则主机规则，也没有 `no-resolve`；官方 `filter.snippet` 采用三列格式。v2fly `geolocation-!cn` 展开后约有 158 条 `regexp:`，丢弃影响很小。
