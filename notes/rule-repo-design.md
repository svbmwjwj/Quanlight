---
created: 2026-11-26
updated: 2026-11-26
---

# quanlight：自建 Quantumult X 分流规则库设计

## 背景与目标

本项目建一个自己的 Quantumult X 分流规则库，命名为 Quanlight，取红绿灯的信号灯与圈 X 的 Quan 组合而成（用户，D-001）。GitHub 仓库名首字母大写，为 `Quanlight`；所有链接写小写 `quanlight`（用户，D-017）；本地目录、本机数据目录与 Python 包名保持小写（Claude，D-017）。此前直接订阅他人加工的列表，遇到三个问题：规则类型选得过宽，会误伤其他流量；直连与代理的冲突只能靠订阅顺序间接处理；上游的取舍与本人需求不一致时会悄悄影响分流。

两类设备的需求不同，分成两套配置（用户，D-007）：

- iOS 用黑名单：只为确定在用的境外服务写代理规则，未命中的流量全部直连。
- macOS 用白名单：只为确认属于中国大陆的服务写直连规则，未命中的流量全部代理。

规则库的目标：

- 准确：每条规则按 Quantumult X 的规则类型科学选用，只覆盖目标流量，不误伤其他服务（用户，D-009）。
- 完整：服务包同时收录服务本身与它依赖的第三方部分，否则依赖的部分会走错出口。
- 可控：规则、例外与取舍都写成仓库里可审阅的文件，每条注明来源与理由。
- 可验证：每次构建自动检查误伤与回归，异常时不发布。

取舍只看规则是否科学、完善，不以规则条数或设备内存占用为约束（用户，D-003）。

## 阶段

1. 搭建规则库骨架：仓库结构、清单格式、构建与检查流程、发布方式，以及验证匹配语义的探针列表（用户；探针 Claude，D-010）。
2. iOS 黑名单：推送服务包与首批服务包（用户，D-010）。
3. macOS 白名单：大陆直连列表，沿用“macOS 白名单”一节的已有结论（用户，D-010）。

本文档详细设计第 1、2 阶段；第 3 阶段只保留已有结论，开工前再细化（Claude）。

## 非目标

- 不自行采集域名：不做 DNS 探测或爬虫，域名来自官方公布与可信的公开数据，必要时人工核实（Claude）。
- 不做广告拦截列表：现有配置中的拦截规则保持原样（Claude）。
- 不生成完整配置文件：仓库只发布规则列表，节点、策略组、重写、MITM 仍在本机配置里（Claude）。
- 不收录个人域名：仓库公开，个人服务、机场域名等例外留在本机配置的 `[filter_local]`（Claude）。

## 规则类型的选用

Quantumult X 远程列表可用的规则类型以官方 `sample.conf` 为准：`host`、`host-suffix`、`host-wildcard`、`host-keyword`、`ip-cidr`、`ip6-cidr`、`ip-asn`、`geoip`、`user-agent`；不支持正则主机规则，不使用 `no-resolve`（Claude，D-004）。

主机类规则匹配的是应用请求的主机名，不是 DNS 解析链上的 CNAME 目标（Claude，待调研）。因此 v2fly 中只作为 CNAME 目标出现的主机名，如 `courier-push-apple.com.akadns.net`，对 Quantumult X 无效，不收录。

每条规则选能覆盖目标流量的最窄类型（用户：不能用最宽的类型简单粗暴地解决；具体标准 Claude，D-009）：

| 类型 | 何时使用 | 禁止的情形 |
|---|---|---|
| `host` | 第三方或共享域名下的单个主机 | 无 |
| `host-suffix` | 整个可注册域名或子区归该服务独有 | 共享平台与公共 CDN 的域名 |
| `host-wildcard` | 主机名有固定模式，上一级域名是共享的 | 通配到可注册域名一级 |
| `host-keyword` | 默认不用，见下文 | 常见单词或品牌片段 |
| `ip-cidr`、`ip6-cidr` | 服务会用纯 IP 连接，且有官方或可核实的网段 | 远超服务实际使用范围的网段 |
| `ip-asn` | ASN 只属于该服务，见下文 | 云厂商、CDN 与运营商的 ASN |
| `user-agent` | 不使用 | 全部情形 |

各类型的补充约束（Claude，D-009）：

- `host-suffix`：共享平台的例子有 `akadns.net`、`akamaized.net`、`cloudfront.net`、`amazonaws.com`。
- `host-wildcard`：`*` 能否跨多级、是否匹配裸域名，官方没有说明，用前先经探针验证（待调研）。
- `host-keyword`：只有当关键词在检查数据集中零命中，且无法用前三种主机规则表达时才允许，并须在清单里写明理由。
- `ip-cidr`、`ip6-cidr`：IP 规则在域名解析之后匹配，任何解析到这些网段的域名都会被命中，所以网段必须专属于该服务。
- `ip-asn`：必须在清单里记录归属核实的来源与日期，如 bgp.tools 的查询结果；检查数据集无法校验 ASN 的覆盖范围。
- `user-agent`：优先级低于主机规则，且容易误配。

旧配置中的反例，作为检查样本：

- `host-suffix, akadns.net`：Akamai 全球共用的解析域名，过宽；APNs 由 `push.apple.com` 覆盖即可（Claude）。
- `host-keyword, sentry` 与 `host-keyword, sift`：会命中任何含这些字母串的主机名（Claude）。
- `ip-cidr, 17.0.0.0/8`：Apple 全部地址，会把 iCloud、App Store 一起代理（Claude）。

## 共享服务的收录宽度

遥测、身份验证、客服组件等常用多租户 SaaS，例如 Sentry、Persona、Intercom，多个应用共用同一域名（Claude）：

- 优先收专属部分：Auth0 收租户主机 `anthropic.auth0.com`；Sentry 收该服务的上报主机。
- 无法确定专属部分时，可整域收录，但清单条目必须标 `breadth = "broad"` 并写明理由与复核日期。
- 构建报告列出全部 `broad` 条目，复核日期过期时构建失败。
- 这类误伤只会把其他应用的同类请求送去代理，不会让它们打不开；检查数据集查不出，靠 `broad` 标记与复核兜底。

被多个已订阅服务共用的依赖，单独成为共享包，例如 `shared-persona`，策略由本机配置指定；只被一个服务使用的依赖放进该服务的包（Claude）。

## 仓库结构

本地开发目录为 `~/Developer/quanlight`；含节点订阅链接的个人配置放在 `~/.config/quanlight/configs/`，不进仓库（用户）。仓库放在本人 GitHub 账号下（用户）。

```
quanlight/
  bundles/                  # 服务包清单，每个服务一个 TOML 文件
  tests/
    samples.toml            # 样本主机与 IP 的期望去向
    test_*.py               # 构建器自身的单元测试
  src/quanlight/            # 构建器
  probe/                    # 匹配语义探针列表的模板
  .github/workflows/
    build.yml               # 每日与推送 main 时构建、检查、发布
    upstream-diff.yml       # 每周对比参考数据，生成差异报告
  templates/                # 去除隐私信息的 iOS 与 macOS 配置模板
  notes/                    # 设计文档与决策日志
  pyproject.toml
  uv.lock
  LICENSE                   # MIT
  NOTICE                    # 数据来源与许可
  README.md                 # 订阅说明与 [filter_remote] 片段
```

构建器用 Python 编写，依赖用 `uv` 管理，测试用 pytest；清单用 TOML，标准库 `tomllib` 即可读取（Claude）。

## 服务包清单格式

```toml
name = "telegram"
description = "Telegram clients and web"
order = 40                  # 订阅顺序，数字小的在前

[[rule]]
type = "host-suffix"
value = "telegram.org"
role = "core"
source = "v2fly:telegram"

[[rule]]
type = "host-suffix"
value = "sentry.io"
role = "dependency"
source = "legacy:macos-claude"
breadth = "broad"
reason = "Anthropic's Sentry ingest host not yet observed"
review_by = "2027-02-28"

[[upstream]]
kind = "telegram-cidr"      # 官方网段，每次构建同步
```

字段（Claude）：

- `type`、`value`：必填，取值见“规则类型的选用”。
- `role`：`core` 为服务本身；`dependency` 为衍生依赖；`cn-exception` 为同一服务在大陆的节点，生成直连例外。
- `source`：来源标识，取值有 `v2fly:<文件>`、`official:<网址>`、`legacy:<旧配置>`、`observed`、`manual`。
- `reason`：`host-keyword`、`ip-asn`、`breadth = "broad"` 与 `exempt` 条目必填。
- `breadth`、`review_by`：整域收录共享服务时必填。
- `exempt`：豁免某条误伤，填被误伤的国内域名或网段。
- `asn_verified`：`ip-asn` 必填，记录归属核实的来源与日期。
- 包级 `order` 决定订阅顺序；包级 `uses` 列出依赖的共享包名，用于 README 生成订阅片段。

## 参考数据的导入

清单是唯一的事实来源（Claude）：

- 冻结：v2fly 等参考数据由导入工具一次性写进 TOML，构建时不读取；上游变化不会自动进入产物。
- 差异报告：每周对比一次参考数据与清单，新增和删除的条目写成 Actions 摘要，由人审阅后再改清单。
- 例外：`[[upstream]]` 只用于官方公布、语义稳定的数据，例如 Telegram 官方网段，每次构建同步。

v2fly 条目的导入映射（Claude）：

| v2fly 写法 | 导入为 |
|---|---|
| 无前缀或 `domain:` | 默认 `host-suffix`；该域名不归服务独有时，人工改为 `host` 或 `host-wildcard` |
| `full:` | `host` |
| `keyword:` | 不导入，写进导入报告，需要时人工按 `host-keyword` 的约束补写 |
| `regexp:` | 丢弃并计数（D-004） |
| `include:` | 递归展开；每个包可声明排除的文件，例如 `google` 包排除 `include:youtube` |
| `@cn` | 标为 `cn-exception`；`domain:` 生成 `host-suffix` 例外，`full:` 生成 `host` 例外 |
| `@ads` | 不导入 |

## iOS 黑名单

### 服务包

- `apns`：Apple 推送服务，单独成包，不与任何应用绑定（用户，D-008）。所有应用的推送都会经过它，节点中断时全部推送一起中断，这是已接受的取舍（用户）。
- 首批服务包一个产品一个包，便于分别指定策略（用户：服务范围；拆分粒度 Claude，D-012）：
  - `google`：含 Gmail、Google Play；不含 YouTube（用户，D-012）。
  - `youtube`：单独成包（用户，D-012）。
  - `telegram`、`twitter`、`github`、`linkedin`：沿用旧 `iOS.conf` 中已启用订阅的范围（用户，D-012）。
  - `claude`：尽可能完整，以 macOS 配置中整理的 Claude 规则为起点，补充 v2fly `anthropic` 文件（用户，D-012）。
  - `rainbow`、`phantom`、`kraken`：两个钱包与一个交易所（用户，D-012；选择依据见私密笔记）。
  - `uniswap`、`etherscan`、`hyperliquid`、`arweave`、`ipfs`：旧配置中手写的链上服务（用户，D-012）。
  - 币安不收录（用户，D-012；原因见私密笔记）。

首批服务包以已有规则与公开资料起步，暂不做真机观测；某个服务出现漏判，或需要收窄 `broad` 条目时，再用真机配合 WebDriverAgent 观测（Claude）。

### Claude 包

起点是 macOS 配置中按用途分组的约 30 条规则，导入时按“规则类型的选用”重新选类型（Claude）：

- 核心：`anthropic.com`、`claude.ai`、`claude.com` 等独有域名用 `host-suffix`。
- CDN：`servd-anthropic-website.b-cdn.net` 等共享 CDN 上的专属主机用 `host`。
- 登录：Auth0 租户主机 `anthropic.auth0.com` 用 `host`。
- 身份验证：`maps.googleapis.com` 用 `host`；它被 `google` 包的 `googleapis.com` 覆盖，因此 `claude` 包须排在 `google` 包之前。Persona 的 `withpersona.com` 为多租户平台，按 `broad` 收录。
- 遥测与风控：
  - 三条关键词规则改写：`sift` 改为 Sift 的独有域名，`datadog` 保留已有主机 `browser-intake-us5-datadoghq.com`，`sentry` 并入 `sentry.io`。
  - `sentry.io`、`statsigapi.net`、`intercom.io` 无法确定专属主机时按 `broad` 收录。
- IP：Anthropic 网段 `160.79.104.0/21`、`2607:6bc0::/32`；ASN 399358 须记录归属核实来源。

### APNs 包

- `host-suffix, push.apple.com`：这个子区只用于推送（Claude）。
- IP 网段：Apple 只公布了整个 `17.0.0.0/8`，过宽。社区列表常用 `17.249.0.0/16`、`17.252.0.0/16`、`17.57.144.0/22`、`17.188.128.0/18`、`17.188.20.0/23`，来源未核实，也未确认不含 iCloud 等其他服务的地址；核实前不收录（待调研）。

### 大陆节点例外

v2fly 把部分境外服务的大陆节点标为 `@cn`，例如 `google` 文件经 `include:` 展开后有 126 条。在“默认直连”下它们应当直连，但会被同一服务更宽的代理后缀先命中（Claude）。

处理方式：落在任一代理条目之下的 `cn-exception` 条目，生成到 `ios-direct-exceptions.list`，订阅时排在所有服务包前面（Claude）。这依赖“排在前面的规则先命中”或“`host` 优先于 `host-suffix`”，两者都待探针验证。

### 订阅与产物

每个服务包输出一个列表，文件名为 `ios/<包名>.list`，另有 `ios/direct-exceptions.list`。README 生成可直接粘贴的 `[filter_remote]` 片段，按包的 `order` 排序，每行带 `force-policy`（Claude）：

```
[filter_remote]
<base>/ios/direct-exceptions.list, tag=quanlight-direct, force-policy=direct, enabled=true
<base>/ios/apns.list, tag=quanlight-apns, force-policy=<代理策略>, enabled=true
<base>/ios/claude.list, tag=quanlight-claude, force-policy=ai, enabled=true
<base>/ios/google.list, tag=quanlight-google, force-policy=<代理策略>, enabled=true
...
FILTER_LAN, tag=LAN, force-policy=direct, enabled=true

[filter_local]
<个人例外>
final, direct
```

列表第三列写包名，订阅时被 `force-policy` 覆盖；未设置 `force-policy` 时规则会指向不存在的策略，README 中明确提示（Claude）。

各服务包之间不允许完全相同的条目；包含关系允许，但更具体的包必须排在前面，构建时检查（Claude）。

## 构建与检查

1. 读取：加载全部清单，同步 `[[upstream]]` 数据（Claude）。
2. 校验：检查字段完整与类型约束；`breadth = "broad"` 条目的复核日期过期则失败（Claude）。
3. 检查数据集：下载 dnsmasq-china-list、v2fly `geolocation-cn` 与 gaoyifan/china-operator-ip。它们只用于检查，不进入产物；构建报告记录各数据集的提交哈希（Claude）。
4. 误伤检查：按订阅顺序模拟匹配，检查数据集中的每个国内域名与网段都必须落到直连（Claude）。
   - 域名覆盖的判定：`host` 为完全相等；`host-suffix` 为相等或以 `.<值>` 结尾；`host-wildcard` 按通配符匹配；`host-keyword` 为包含子串。
   - IP 覆盖的判定：代理网段与大陆网段有任何重叠。
   - `ip-asn` 不参与 IP 判定，只在报告中列出。
   - 被 `cn-exception` 先行命中而落到直连的，不算误伤；其余误伤须在清单中用 `exempt` 豁免，否则失败。
5. 交叉检查：包间的完全重复与包含关系，以及顺序是否满足“更具体的包在前”（Claude）。
6. 样本测试：`tests/samples.toml` 逐条写明主机或 IP 及期望命中的列表，按同一模拟器判定（Claude）。初始样本取自本次讨论的实测，包括淘宝、微信、B 站应直连，Google、Telegram、Claude 应走对应的包。
7. 生成：三列格式；文件头注释写数据来源与上游版本，不写生成时间，内容无变化时不产生新提交（Claude）。
8. 发布：全部检查通过后，用 `GITHUB_TOKEN`（`contents: write`）推送到 `release` 分支，并刷新 jsDelivr 缓存（Claude）。

任一步骤失败，整次构建失败，发布分支保留上一版，由 GitHub 默认的失败邮件通知（Claude）。

模拟器暂按“`[filter_local]` 先于 `[filter_remote]`，远程列表按订阅顺序逐条匹配”实现；主机名未命中时才解析 IP 再匹配 IP 规则（Claude）。社区另有“按规则类型分优先级”的说法[^1]，两种语义下例外都排在最前，结论一致；真机探针验证后再定是否调整模拟器（待调研）。

## 匹配语义探针

第 1 阶段生成一组探针列表，在真机上验证以下问题（Claude）：

- `[filter_local]` 与 `[filter_remote]` 的先后。
- 同一列表与不同列表之间，`host`、`host-suffix`、`host-wildcard` 冲突时谁先命中。
- “分流匹配优化”开关对上述结果的影响。
- `host-wildcard` 中 `*` 的语义。
- 主机规则是否匹配 CNAME 目标。

做法：用几个可控的测试主机名，分别写进去向不同的规则，在 Quantumult X 的请求记录里看实际命中的规则。结果写进决策日志，并据此调整模拟器（Claude）。

## 发布与订阅

- 分支：`main` 放清单、源码与测试；`release` 只放产物，每次构建强制覆盖为单个提交（Claude）。
- 订阅地址：GitHub `https://raw.githubusercontent.com/svbmwjwj/quanlight/release/<文件>` 为主（Claude，D-015）。
- 境内备用：`ghfast.top` 代理的 GitHub 地址，实测在大陆网络下可直连；jsDelivr 的 `fastly`、`cdn` 两个节点也列出，能否稳定直连待真机确认（用户：须有境内可用的备用链接；具体地址 Claude，D-015）。第三方代理能看到并改动所转发的内容，这是已知风险。
- 发布说明同时给出 GitHub 版与境内版的 `[filter_remote]` 片段（Claude，D-015）。
- 个人配置直接订阅本仓库发布的列表，不再订阅他人加工的列表；第 2 阶段的服务包建成前，尚未覆盖的服务暂时保留原有订阅（用户：直接引用自己的规则集；过渡安排 Claude，D-014）。
- 模板：仓库的 `templates/` 提供去除私人订阅、密钥、节点检测脚本、MITM 证书与个人域名的 iOS、macOS 配置模板；本人的实际配置只放在 `~/.config/quanlight/configs/`（用户，D-016）。
- 更新：每日构建一次；清单改动推送到 `main` 时也触发（Claude）。
- 许可证：构建代码与产物均为 MIT；NOTICE 列出 v2fly（MIT，保留其版权声明）与 Telegram 官方网段等来源（Claude，D-013）。

## macOS 白名单

第 3 阶段再细化，目前已有的结论如下：

- 直连数据：dnsmasq-china-list、v2fly `geolocation-cn`，以及境外服务的大陆节点（Claude）。
- 大陆 IP：gaoyifan/china-operator-ip（Claude，D-006）。
- 订阅顺序：窄的例外在前、宽的列表在后；域名规则在前、IP 规则在后（Claude）。
- 未命中的域名是否先查 DNS，以及是否需要代理列表，开工前再定（待定）。D-002 的前提是单一白名单配置，已随 D-007 失效。
- 若使用 gfwlist，相关产物的许可证需重新判断（待调研）。

## 待定事项

- [x] 仓库名：`quanlight`（D-001）。
- [x] iOS 内存：不作为约束（D-003）。
- [x] 大陆 IP 数据源：gaoyifan/china-operator-ip（D-006）。
- [x] iOS 首批服务包的范围（D-012）。
- [x] iOS 产物的许可证：MIT（D-013）。
- [ ] APNs 实际使用的 IP 网段（待调研）。
- [ ] Quantumult X 的匹配语义、`host-wildcard` 语义、CNAME 是否参与匹配，由探针验证（待调研）。
- [ ] jsDelivr 与 GitHub 地址在大陆直连的可用性（待调研）。
- [ ] macOS 未命中的域名是否先查 DNS（待定）。

[^1]: 官方 `sample.conf` 第 276～277 行只说明 `host-keyword, .` 会跳过未命中域名的 DNS 查询，且纯 IP 请求不被主机类规则匹配；类型优先级出自 limbopro.com/archives/30471.html，未经官方证实。
