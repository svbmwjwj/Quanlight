---
id: D-009
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# 按最窄类型选用规则

## 决定

每条规则选能覆盖目标流量的最窄类型：独有的可注册域名或子区用 `host-suffix`；共享域名下的单个主机用 `host`；有固定模式时用 `host-wildcard`；`host-keyword` 与 `ip-asn` 默认不用，必须写明理由并通过误伤检查；IP 网段只用官方公布或可核实的范围；不用 `user-agent`。构建时用国内直连数据集检查每个代理条目，误伤必须显式豁免。

## 备选

- 直接沿用上游写法：v2fly 等数据源几乎全部写成后缀，社区列表常见 `akadns.net`、`17.0.0.0/8` 这类过宽条目。

## 缘由

用户要求参考 Quantumult X 的规则类型科学选用，不误伤其他规则，不用最宽的类型简单粗暴地解决。具体的选用标准与检查方式由 Claude 制定。
