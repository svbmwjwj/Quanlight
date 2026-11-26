---
id: D-015
created: 2026-11-26
updated: 2026-11-26
type: decide
source: user
status: active
supersedes:
doc: notes/rule-repo-design.md
---

# GitHub 订阅为主，境内另备链接

## 决定

订阅地址以 GitHub raw 为主；境内备用链接用 `ghfast.top` 代理的 GitHub 地址，同时列出 jsDelivr 的 `fastly`、`cdn` 两个节点。发布说明同时给出两套订阅片段。

## 备选

- 只用 jsDelivr：在大陆直连的稳定性未经验证。
- 自建境内镜像（如 Gitee、对象存储）：需要另开账号并维护同步，暂不做。

## 缘由

用户要求除 GitHub 外另备境内可用的链接。具体地址由 Claude 选定：`ghfast.top` 在大陆网络下实测可直连；第三方代理能看到并改动所转发的内容，这一风险写进 README。
