---
id: D-025
created: 2026-11-26
updated: 2026-11-26
type: research
source: claude
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# “分流优化”开关与主机规则类型的优先级（真机探针）

## 决定

构建器按“分流优化”开启时的语义建模，类型顺序为 `host` > `host-suffix` > `host-wildcard` > `host-keyword`，同类型按加载顺序；`src/quanlight/match.py` 的 `HOST_TYPE_PRIORITY` 暂定值得到证实，无需修改。私人配置与模板须开启“分流优化”，否则类型优先不成立。

## 证据

2026-11-26 在 iPhone 15 Pro Max（Quantumult X 1.8.1）上实测。四个远程探针列表排在 `[filter_remote]` 最前，依次为：

- A，拒绝：`host-keyword, xample.com`、`host-keyword, xample.org`、`host-suffix, iana.org`。
- B，直连：`host-wildcard, *.example.com`、`host-wildcard, *.example.org`、`host, www.iana.org`。
- C，直连：`host-suffix, example.com`。
- D，直连，单个列表内依次为 `host-keyword, xample.net`、`host-wildcard, *.example.net`、`host-suffix, example.net`。

结果取自首页请求记录与“DNS 阻止的域名”页：

- 开启“分流优化”：`www.example.com` 命中 C 的 `HOST-SUFFIX`；`www.example.org` 命中 B 的 `HOST-WILDCARD`；`www.example.net` 命中 D 内排在最后的 `HOST-SUFFIX`。
- 关闭“分流优化”：`www.example.com`、`www.example.org` 都命中 A 的 `HOST-KEYWORD`；`www.example.net` 命中 D 内排在最前的 `HOST-KEYWORD`；`www.iana.org` 命中 A 的 `HOST-SUFFIX, IANA.ORG`，排在后面的 `host` 规则未生效。
- 应用内“分流优化”的说明：关闭时，host 相关类型的规则完全按照加载顺序匹配；开启时更趋向于精度匹配，同样精度的规则按加载顺序匹配；只能在 VPN 断开时更改。
- D-019 中 `host` 胜过排在前面的 `host-suffix`，按上述说明只可能发生在开启状态，与本次结果一致；本次开启状态下未能重测 `www.iana.org`（Safari 没有发出新请求）。

## 影响

- 类型优先只在开启“分流优化”时成立；关闭时退化为纯加载顺序，`direct-exceptions` 须排在所有服务包之前的现有约定仍然必要。（`direct-exceptions` 已随 D-027 退役。）
- 设计文档“构建与检查”一节应注明这一前提。
