---
id: D-002
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: superseded
supersedes:
doc: notes/rule-repo-design.md
---

# proxy.list 纳入 v2fly 境外域名

## 决定

`proxy.list` 除 gfwlist 外，还纳入 v2fly `geolocation-!cn` 展开后的条目，其中带 `@cn` 属性的条目排除，归入 `direct-intl.list`。

## 备选

- 只用 gfwlist：列表较小，但未被墙的境外网站要先查一次 DNS，解析到大陆 IP 时会直连。

## 缘由

用户要求未被墙的境外网站也不必先查 DNS。纳入后这些域名在域名阶段就确定走代理，不再向国内 DNS 暴露查询，也不受解析结果影响。排除 `@cn` 条目由 Claude 决定，避免把有大陆节点的境外服务送去代理。
