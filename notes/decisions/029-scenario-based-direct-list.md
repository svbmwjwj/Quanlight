---
id: D-029
created: 2026-11-26
updated: 2026-11-26
type: overturn
source: user
status: active
supersedes: D-028
doc: notes/rule-repo-design.md
---

# 直连规则按常用场景整理

## 决定

直连列表只覆盖本人常用的国内应用与场景，其余国内流量交给大陆 IP 回退：

- 常用应用（用户）：微信、QQ、小红书、支付宝、云闪付、中国银行、招商银行、淘宝、京东、美团、抖音、滴滴、12306、iCloud 中国区、App Store（直连）。
- 每个应用取 v2fly 对应的公司或服务文件，不手写域名（Claude）：`tencent`（微信、QQ）、`xiaohongshu`、`alibaba`（支付宝、淘宝）、`unionpay`（云闪付）、`boc`、`cmb`、`jd`、`meituan`、`douyin`、`didi`。
- `host-suffix, cn` 一条覆盖全部 .cn 域名，12306 的 `12306.cn` 由它覆盖（Claude）。
- iCloud 中国区与 App Store 取 dnsmasq-china-list 的 `apple.china.conf`，它收录的是在大陆有节点、应走境内解析的 Apple 域名（Claude）。
- 大陆网段 gaoyifan/china-operator-ip 照旧作为 IP 回退（D-006）。

## 被推翻的原判断

D-028 取宽口径：dnsmasq-china-list `accelerated-domains.china.conf` 全量加 v2fly `geolocation-cn`，产物约 12 万条。

## 备选

- 维持宽口径：覆盖最全，但上游每次变动都有成千上万行差异，人工审阅不现实，iOS 内存也待验证。

## 缘由

用户认为全量中国规则数量太庞大、验证效率太低，改为按自己的常用场景整理。规则量降到几千条，上游变化只需审阅所用公司文件的几行差异；每个应用都能写样本直接验证。不在名单上、且服务器在境外的国内应用会走代理，发现后补进名单。
