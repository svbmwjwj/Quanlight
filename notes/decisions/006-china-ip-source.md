---
id: D-006
created: 2026-11-26
updated: 2026-11-26
type: research
source: claude
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# 大陆 IP 采用 gaoyifan/china-operator-ip

## 决定

`direct-ip.list` 由 gaoyifan/china-operator-ip 的 `china.txt` 与 `china6.txt` 生成。构建时与 APNIC 登记为 CN 的网段做差异统计，只记录、不并入。

## 备选

- APNIC 登记表：按登记地，不按实际使用地，会收入阿里国际等境外宣告的网段。
- misakaio/chnroutes2：只看 BGP，比 gaoyifan 少约 6,250 万个地址，且没有 IPv6。
- 17mon/china_ip_list、Hackl0us/GeoIP2-CN：基于 IPIP 商业库，许可含 NC 条款，多收约 1,300 万个登记在新加坡的地址；17mon 已约 21 个月未更新。
- MaxMind GeoLite2：需注册和密钥，再分发有条件，大陆判定准确度常被指出不足。

## 缘由

gaoyifan 同时使用 BGP 路由与 RIR 登记：要求宣告方经可信国内运营商接入，排除 AS45102 等境外宣告，再用登记为 CN 但未宣告的网段兜底。它每日更新，同时有 IPv4 与 IPv6，许可证为 MIT，维护者对准确性问题通常当天或次日响应。抽样中阿里香港、新加坡、美国与腾讯海外的 IP 都未被误收。Loyalsoldier/geoip 的 `cn` 与它完全相同，不必另行依赖。
