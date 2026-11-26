---
id: D-019
created: 2026-11-26
updated: 2026-11-26
type: research
source: claude
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# Quantumult X 的规则匹配语义（真机探针）

## 决定

按以下语义建模构建器的模拟器：

- `[filter_local]` 先于 `[filter_remote]`。
- 规则类型有优先级：`host` 先于 `host-suffix`，即使 `host` 所在的列表排在后面。
- 同一类型内，按订阅顺序，排在前面的列表先命中。
- `host-wildcard` 的 `*.example.com` 不匹配裸域名 `example.com`。
- 主机规则不匹配 CNAME 目标。

## 证据

2026-11-26 在 iPhone 15 Pro Max 上用探针配置实测，结果取自 Quantumult X 的请求记录与 DNS 拦截记录：

- `www.example.net`：本地 `host` 直连与远程 `host` 拒绝并存，命中本地规则 `HOST, WWW.EXAMPLE.NET, DIRECT`。
- `www.example.org`：前一个列表 `host-suffix, example.org` 拒绝，后一个列表 `host, www.example.org` 直连，命中 `HOST, WWW.EXAMPLE.ORG, DIRECT`。
- `www.example.com`：两个列表都是 `host-suffix, example.com`，前拒绝后直连，命中前者 `HOST-SUFFIX, EXAMPLE.COM, REJECT`。
- `www.iana.org` 命中 `HOST-WILDCARD, *.IANA.ORG, REJECT`；`iana.org` 直连。
- `host, www.microsoft.com-c-3.edgekey.net` 拒绝未生效，`www.microsoft.com` 照常直连。
- 设置页的官方说明：“靠前的规则优先级更高，可点击‘分流规则’查看顺序”；“分流规则”页显示加载后的顺序为本地规则、FINAL、各远程列表依次排列。

## 未验证

- “分流匹配优化”开关开与关时结果是否不同；本次只在当时的开关状态下测试。
- `host-suffix` 与 `host-wildcard`、`host-keyword` 之间的优先级；社区说法为 `host-suffix` 先于 `host-wildcard` 先于 `host-keyword`。

## 影响

构建器 `src/quanlight/match.py` 的 `route()` 目前按“列表顺序优先、同列表内任一命中”建模，与“类型优先”不一致，需要修改。现有产物不受影响：直连例外全部是 `host` 类型，Claude 包的 `maps.googleapis.com` 也是 `host`，在两种语义下结论相同。
