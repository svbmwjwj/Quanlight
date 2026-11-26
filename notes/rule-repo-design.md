---
created: 2026-11-26
updated: 2026-11-26
---

# quanlight：自建 Quantumult X 分流规则库设计

## 背景与目标

本项目建一个自己的 Quantumult X 分流规则库，命名为 Quanlight，取红绿灯的信号灯与圈 X 的 Quan 组合而成（用户，D-001）。GitHub 仓库名首字母大写，为 `Quanlight`；所有链接写小写 `quanlight`（用户，D-017）；本地目录、本机数据目录与 Python 包名保持小写（Claude，D-017）。此前直接订阅他人加工的列表，遇到三个问题：规则类型选得过宽，会误伤其他流量；直连与代理的冲突只能靠订阅顺序间接处理；上游的取舍与本人需求不一致时会悄悄影响分流。

iOS 与 macOS 都用代理托底：只为中国大陆常用的地址写直连规则，未命中的流量全部走代理（用户，D-026）。两类设备订阅同一组直连列表，配置模板分开。境外服务只保留 APNs 一个包，其余由代理托底（用户，D-027）。

规则库的目标：

- 准确：国内应用不误走代理；被封锁的境外服务不被直连规则吞掉（Claude）。
- 够用：覆盖本人常用的国内应用与场景，其余国内流量由大陆 IP 回退兜底（用户，D-029）。
- 可控：规则、例外与取舍都写成仓库里可审阅的文件，每条注明来源与理由。
- 可验证：每次构建自动检查反向误伤与回归，异常时不发布。

取舍只看规则是否科学、完善，不以规则条数或设备内存占用为约束（用户，D-003）。

## 阶段

1. 搭建规则库骨架：仓库结构、清单格式、构建与检查流程、发布方式，以及验证匹配语义的探针列表（已完成）。
2. 共用白名单：直连列表与 APNs 包，先在 iOS 上验证（用户，D-026）。
3. macOS 配置模板（用户，D-026）。

## 非目标

- 不自行采集域名：不做 DNS 探测或爬虫，域名来自可信的公开数据，必要时人工核实（Claude）。
- 不做广告拦截列表：现有配置中的拦截规则保持原样（Claude）。
- 不生成完整配置文件：仓库只发布规则列表，节点、策略组、重写、MITM 仍在本机配置里（Claude）。
- 不收录个人域名：仓库公开，个人服务、机场域名等例外留在本机配置的 `[filter_local]`（Claude）。
- 不维护境外服务包：除 APNs 外，境外服务都由 `final` 的代理托底，不拆分策略（用户，D-027）。

## 规则类型的选用

Quantumult X 远程列表可用的规则类型以官方 `sample.conf` 为准：`host`、`host-suffix`、`host-wildcard`、`host-keyword`、`ip-cidr`、`ip6-cidr`、`ip-asn`、`geoip`、`user-agent`；不支持正则主机规则，不使用 `no-resolve`（Claude，D-004）。

主机类规则匹配的是应用请求的主机名，不匹配 DNS 解析链上的 CNAME 目标（Claude，D-019）。

每条规则选能覆盖目标流量的最窄类型（用户：不能用最宽的类型简单粗暴地解决；具体标准 Claude，D-009）：

| 类型 | 何时使用 | 禁止的情形 |
|---|---|---|
| `host` | 共享域名下的单个主机 | 无 |
| `host-suffix` | 整个可注册域名或子区归该服务独有 | 共享平台与公共 CDN 的域名 |
| `host-wildcard` | 主机名有固定模式，上一级域名是共享的 | 通配到可注册域名一级 |
| `host-keyword` | 默认不用 | 常见单词或品牌片段 |
| `ip-cidr`、`ip6-cidr` | 有可核实的网段 | 远超实际使用范围的网段 |
| `ip-asn`、`geoip`、`user-agent` | 不使用 | 全部情形 |

补充约束（Claude，D-009）：

- `host-wildcard`：`*.example.com` 不匹配裸域名 `example.com`（Claude，D-019）；`*` 能否跨多级尚未验证（待调研）。
- `ip-cidr`、`ip6-cidr`：IP 规则在域名解析之后匹配，任何解析到这些网段的域名都会被命中。
- `geoip`：大陆网段改用 gaoyifan/china-operator-ip 生成的 `ip-cidr`，不依赖 Quantumult X 内置的地理库（Claude，D-006）。

## 仓库结构

本地开发目录为 `~/Developer/quanlight`；含节点订阅链接的个人配置放在 `~/.config/quanlight/configs/`，不进仓库（用户）。仓库放在本人 GitHub 账号下（用户）。

```
quanlight/
  bundles/                  # 清单：apns.toml 与 china.toml
  tests/
    samples.toml            # 样本主机与 IP 的期望去向
    test_*.py               # 构建器自身的单元测试
  src/quanlight/            # 构建器
  probe/                    # 匹配语义探针列表的模板
  .github/workflows/
    build.yml               # 每日与推送 main 时构建、检查；手动发布
  templates/                # 去除隐私信息的 iOS 与 macOS 配置模板
  notes/                    # 设计文档与决策日志
  pyproject.toml
  uv.lock
  LICENSE                   # MIT
  NOTICE                    # 数据来源与许可
  README.md                 # 订阅说明与 [filter_remote] 片段
```

构建器用 Python 编写，依赖用 `uv` 管理，测试用 pytest；清单用 TOML，标准库 `tomllib` 即可读取（Claude）。

## 清单格式

每个清单输出一个列表（Claude）：

- `apns.toml`：手写的 `[[rule]]`，见“APNs 包”。
- `china.toml`：以 `[[upstream]]` 声明直连数据源（D-029），另可手写补充与排除。

```toml
name = "china"
description = "Mainland China domains and IP ranges"
order = 20                  # 订阅顺序，数字小的在前

[[upstream]]                # 每个常用应用一个 v2fly 文件
kind = "v2fly"
file = "tencent"
apps = "WeChat, QQ"

[[upstream]]
kind = "dnsmasq-apple-china"

[[upstream]]
kind = "china-operator-ip"

[[rule]]                    # 上游未收录、经人工核实的直连条目
type = "host-suffix"
value = "example.cn"
source = "manual"
reason = "..."

[[exclude]]                 # 从上游数据中剔除的条目
value = "example.com"
reason = "blocked overseas service, listed by a China dataset"

[[keep]]                    # 反向检查命中但确认应直连的条目
value = "example.net"
reason = "..."
```

字段（Claude）：

- `[[rule]]`：`type`、`value`、`source` 必填；`source` 取值有 `official:<网址>`、`observed`、`manual`；`manual` 与 `observed` 须写 `reason`。
- `[[exclude]]`：按值精确剔除上游条目，须写 `reason`。
- `[[keep]]`：反向检查的豁免，须写 `reason`。
- `[[upstream]]`：`kind = "v2fly"` 时 `file` 与 `apps` 必填，`apps` 写这个文件服务于哪些常用应用。
- `skip_includes`：`kind = "v2fly"` 时可选，列出展开时跳过的 include 子文件，用于剔除只服务境外的国际站与海外业务；所列文件须确实被引用（用户：不要国际站；字段 Claude）。
- 包级 `order` 决定订阅顺序。

## 直连数据

直连数据每次构建从上游同步，不冻结进清单（Claude）。上游变化经 Actions 摘要呈现，发布前由人审阅（D-020）；只用到几个公司文件，每次差异通常只有几行。

数据源按本人常用场景选取（用户：应用名单，D-029；文件对应 Claude）：

| 常用应用 | 数据源 |
|---|---|
| 微信、QQ | v2fly `tencent` |
| 小红书 | v2fly `xiaohongshu` |
| 支付宝、淘宝 | v2fly `alibaba` |
| 云闪付 | v2fly `unionpay` |
| 中国银行、招商银行 | v2fly `boc`、`cmb` |
| 京东、美团、抖音、滴滴 | v2fly `jd`、`meituan`、`douyin`、`didi` |
| 12306 与其他 .cn 站点 | 手写 `host-suffix, cn` |
| iCloud 中国区、App Store | dnsmasq-china-list `apple.china.conf` |
| 其余国内流量 | gaoyifan/china-operator-ip 大陆网段（D-006） |

- v2fly 文件按下表映射；多个文件重复的条目去重（Claude）。
- `apple.china.conf` 每行 `server=/<域名>/<DNS>` 生成 `host-suffix, <域名>`（Claude）。
- 大陆网段：`china.txt`、`china6.txt` 生成 `ip-cidr` 与 `ip6-cidr`（D-006）。
- 新增常用应用时，在 `china.toml` 加一个 `[[upstream]]`，并在样本里补一条（Claude）。

v2fly 条目的导入映射（Claude）：

| v2fly 写法 | 导入为 |
|---|---|
| 无前缀或 `domain:` | `host-suffix` |
| `full:` | `host` |
| `keyword:` | 不导入，写进构建报告 |
| `regexp:` | 丢弃并计数（D-004） |
| `include:` | 递归展开 |
| `@!cn` | 不导入 |
| `@ads` | 不导入 |

任一数据源下载失败、格式无法解析或条目数较上一版骤减一半以上时，构建失败（Claude）。

## APNs 包

APNs 单独成包，排在直连列表之前，强制走代理（用户，D-008、D-027）。Telegram 等应用的推送依赖它；直连时这类通知收不到，所以不交给托底，用显式规则先截住（用户，D-027）。节点中断时全部推送一起中断，这是已接受的取舍（用户，D-008）。

- `host-suffix, push.apple.com`：这个子区只用于推送（Claude）。它与直连列表中可能出现的 Apple 域名同属主机规则，按类型优先与加载顺序先命中 APNs（D-019）。
- IP 网段：Apple 只公布了整个 `17.0.0.0/8`，过宽。社区列表常用 `17.249.0.0/16`、`17.252.0.0/16`、`17.57.144.0/22`、`17.188.128.0/18`、`17.188.20.0/23`，来源未核实；核实前不收录（待调研）。推送是否会以纯 IP 连接、该 IP 是否落在大陆网段，也待真机确认（待调研）。

## 订阅与产物

产物为 `apns.list` 与 `china.list`，两类设备共用；README 生成可直接粘贴的 `[filter_remote]` 片段，每行带 `force-policy`（Claude）：

```
[filter_remote]
<base>/apns.list, tag=quanlight-apns, force-policy=<代理策略>, update-interval=-1, enabled=true
<base>/china.list, tag=quanlight-china, force-policy=direct, update-interval=-1, enabled=true
FILTER_LAN, tag=LAN, force-policy=direct, enabled=true

[filter_local]
<个人例外>
final, <代理策略>
```

列表第三列写包名，订阅时被 `force-policy` 覆盖；未设置 `force-policy` 时规则会指向不存在的策略，README 中明确提示（Claude）。

未命中任何主机规则的域名，由配置 `[dns]` 中的境内解析器解析后再匹配 IP 规则：落在大陆网段的直连，其余落到 `final` 走代理（Claude）。被污染的域名通常解析到境外地址，仍会走代理，由代理端重新解析（Claude）。

## 构建与检查

1. 读取：加载清单，同步 `[[upstream]]` 数据（Claude）。
2. 校验：检查字段完整与类型约束；应用 `[[exclude]]`，去重（Claude）。
3. 反向检查数据集：下载 v2fly `geolocation-!cn`（去掉带 `@cn` 的条目），以及 Telegram 官方网段、GitHub `api.github.com/meta` 与 Google `goog.json`（Claude，D-027）。它们只用于检查，不进入产物；构建报告记录各数据集的版本。
4. 反向误伤检查：按订阅顺序模拟匹配，检查数据集中的境外域名与网段都不得落到直连（Claude）。
   - 域名覆盖的判定：`host` 为完全相等；`host-suffix` 为相等或以 `.<值>` 结尾；`host-wildcard` 按通配符匹配。
   - IP 覆盖的判定：大陆网段与境外网段有任何重叠。
   - 命中的条目须在 `china.toml` 中用 `[[exclude]]` 剔除或用 `[[keep]]` 豁免，否则失败。首次构建的命中数量未知（待调研）。
5. 样本测试：`tests/samples.toml` 逐条写明主机或 IP 及期望去向，按同一模拟器判定（Claude）。样本包括每个常用应用至少一条主机应直连（含 iCloud 中国区与 App Store），Google、Telegram、Claude、X 应落到 `final`，`courier.push.apple.com` 应命中 APNs。
6. 生成：三列格式；文件头注释写数据来源与上游版本，不写生成时间，内容无变化时不产生新提交（Claude）。
7. 发布：全部检查通过后，用 `GITHUB_TOKEN`（`contents: write`）推送到 `release` 分支，并刷新 jsDelivr 缓存（Claude）。

任一步骤失败，整次构建失败，发布分支保留上一版，由 GitHub 默认的失败邮件通知（Claude）。

模拟器按真机探针确认的语义实现：先按规则类型，同类型内按订阅顺序，排在前面的列表先命中；主机规则都未命中时才按订阅顺序匹配 IP 规则，再落到 `final`（Claude，D-019）。模拟的列表只有 `[filter_remote]` 中的两个包，`final` 视为代理。

主机规则类型的顺序为 `host`、`host-suffix`、`host-wildcard`、`host-keyword`；其中 `host` 先于 `host-suffix` 已由探针确认，后三者之间的先后暂按社区说法，尚未实测（Claude，待调研）。

## 匹配语义探针

第 1 阶段生成一组探针列表，在真机上验证以下问题（Claude）：

- `[filter_local]` 与 `[filter_remote]` 的先后。
- 同一列表与不同列表之间，`host`、`host-suffix`、`host-wildcard` 冲突时谁先命中。
- “分流匹配优化”开关对上述结果的影响。
- `host-wildcard` 中 `*` 的语义。
- 主机规则是否匹配 CNAME 目标。

做法：用几个可控的测试主机名，分别写进去向不同的规则，在 Quantumult X 的请求记录里看实际命中的规则。结果写进决策日志，并据此调整模拟器（Claude）。

## 真机验证

发布前在 iOS 上验证（Claude）：

- 国内应用：在请求记录中查找命中 `final` 的国内域名，重点看微信、支付宝、银行、运营商一键登录与 12306；漏掉的补进 `china.toml` 的 `[[rule]]`，`source = "observed"`。
- 推送：确认 Telegram 通知可达，且推送连接命中 APNs 包。

## 发布与订阅

- 分支：`main` 放清单、源码与测试；`release` 只放产物，每次发布强制覆盖为单个提交（Claude）。
- 订阅地址：GitHub `https://raw.githubusercontent.com/svbmwjwj/quanlight/release/<文件>` 为主（Claude，D-015）。
- 境内备用：`ghfast.top` 代理的 GitHub 地址，实测在大陆网络下可直连；jsDelivr 的 `fastly`、`cdn` 两个节点也列出，能否稳定直连待真机确认（用户：须有境内可用的备用链接；具体地址 Claude，D-015）。第三方代理能看到并改动所转发的内容，这是已知风险。
- 发布说明同时给出 GitHub 版与境内版的 `[filter_remote]` 片段（Claude，D-015）。
- 个人配置直接订阅本仓库发布的列表，不再订阅他人加工的列表（用户，D-014）。
- 模板：仓库的 `templates/` 提供去除私人订阅、密钥、节点检测脚本、MITM 证书与个人域名的 iOS、macOS 配置模板；本人的实际配置只放在 `~/.config/quanlight/configs/`（用户，D-016）。
- 更新：自动流程只检测各来源的变化并试构建；发布在真机检测或探针之后由人工触发，不设固定周期；配置中的规则集不设置自动更新时间（用户，D-020）。
  - 检测：`build.yml` 在每天北京时间 02:00 与推送 `main` 时运行测试、构建与检查，并在 Actions 摘要中列出产物相对 `release` 分支的变化，不发布；此时令牌只有读权限（Claude）。
  - 发布：在 Actions 页面对 `main` 手动运行 `build` 并勾选 `publish`，检查通过后由单独的任务强制推送 `release` 并刷新 jsDelivr；读取 `release` 失败时不推送（Claude）。
  - 自动更新：省略 `update-interval` 时，Quantumult X 对所有远程资源每 86400 秒自动同步一次，负数才关闭自动同步[^2]；因此模板、本人配置与发布说明片段的 `[filter_remote]` 都写 `update-interval=-1`，`[server_remote]`、`[rewrite_remote]` 不变（用户，D-023）。
- 许可证：构建代码与产物均为 MIT；NOTICE 列出 dnsmasq-china-list、v2fly（MIT，保留其版权声明）与 gaoyifan/china-operator-ip 等来源（Claude，D-013）。

## macOS

macOS 订阅同一组列表，只在配置模板上与 iOS 不同，第 3 阶段再定（用户，D-026）。

## 待定事项

- [x] 仓库名：`quanlight`（D-001）。
- [x] iOS 内存：不作为约束（D-003）。
- [x] 大陆 IP 数据源：gaoyifan/china-operator-ip（D-006）。
- [x] iOS 产物的许可证：MIT（D-013）。
- [x] Quantumult X 的匹配语义：本地先于远程、`host` 先于 `host-suffix`、同类型按顺序、通配符不匹配裸域名、主机规则不匹配 CNAME 目标（D-019）。
- [x] 两类设备都用代理托底（D-026）；境外服务包只留 APNs（D-027）；直连数据按常用场景整理（D-029）。
- [ ] 反向检查首次命中的数量与处理方式（待调研）。
- [ ] APNs 实际使用的 IP 网段，以及推送是否以纯 IP 连接（待调研）。
- [ ] “分流匹配优化”开关的影响，以及 `host-suffix`、`host-wildcard`、`host-keyword` 之间的优先级（待调研）。
- [ ] jsDelivr 与 GitHub 地址在大陆直连的可用性（待调研）。

[^1]: 官方 `sample.conf` 第 276～277 行只说明 `host-keyword, .` 会跳过未命中域名的 DNS 查询，且纯 IP 请求不被主机类规则匹配；类型优先级出自 limbopro.com/archives/30471.html，未经官方证实。
[^2]: 官方 `sample.conf`（v1.5.5 build 914）第 117～118 行，https://raw.githubusercontent.com/crossutility/Quantumult-X/master/sample.conf
