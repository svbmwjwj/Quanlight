---
id: D-028
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: superseded
supersedes:
doc: notes/rule-repo-design.md
---

# 直连数据取宽口径

## 决定

直连列表由三部分组成，每次构建从上游同步：

- dnsmasq-china-list 的 `accelerated-domains.china.conf` 全量，生成 `host-suffix`。
- v2fly `geolocation-cn` 展开后的条目，按导入映射生成；带 `@!cn` 的条目不导入。
- gaoyifan/china-operator-ip 的大陆网段（D-006），生成 `ip-cidr` 与 `ip6-cidr`，作为未命中域名解析后的 IP 回退。

## 备选

- 窄口径：只用 `geolocation-cn` 加 IP 回退。列表小，但服务器或 CDN 在境外的国内域名会被 IP 回退判为境外，走代理。

## 缘由

用户采纳 Claude 的建议。dnsmasq-china-list 按域名的权威 DNS 是否在境内收录，不依赖解析结果，能补上窄口径漏掉的、国内应用使用境外 CDN 的情形，这正是代理托底最需要避免的误判。窄口径是宽口径的子集，若真机内存撑不住，构建器少接一个数据源即可退回。

## 待验证

- 内存：D-003 不以内存为约束，但几万条规则在 iOS 上能否稳定运行未经验证。首次构建后在手机上导入并使用一两天，观察 Quantumult X 隧道是否被系统重启。
- 代价：未命中的境外域名都会先经境内 DNS 解析一次，这是代理托底的固有代价，两种口径相同。
