---
created: 2026-11-26
updated: 2026-11-26
---

# quanlight 第 1 阶段实现计划

执行方式：逐个任务实现，可用 superpowers:subagent-driven-development 或 superpowers:executing-plans；步骤用 `- [ ]` 跟踪。

## 概要

- 目标：建成规则库骨架，从 TOML 清单构建 iOS 黑名单列表，完成误伤检查、样本测试与探针，经 GitHub Actions 每日发布；用 `apns` 与 `telegram` 两个包跑通全流程。
- 架构：`src/quanlight/` 下按职责分模块：清单模型、匹配器、v2fly 导入、上游与检查数据、检查、产物渲染、命令行。纯函数负责解析与判断，网络访问只在 `fetch.py` 与命令行入口。
- 技术栈：Python 3.13，`uv` 管理依赖，pytest；只用标准库，`tomllib` 读 TOML，`ipaddress` 判断网段，`fnmatch` 处理通配符。
- 设计文档：`notes/rule-repo-design.md`，执行时与本计划一起读。
- 第 2 阶段（其余服务包）的计划在探针结果出来后另写。

## 全局约束

- 规则类型只用 `host`、`host-suffix`、`host-wildcard`、`host-keyword`、`ip-cidr`、`ip6-cidr`、`ip-asn`；不输出 `user-agent`、`geoip`、正则，不加 `no-resolve`（D-004）。
- 产物每行三列：`<type>, <value>, <bundle-name>`，与官方 `sample.conf` 写法一致。
- 主机名一律小写并去掉末尾的点后再比较与输出。
- 产物不含生成时间；同样的输入必须产出字节相同的文件。
- 任一上游或检查数据下载失败、解析为空、检查不通过，命令以非零状态退出，不写入产物。
- 源码、注释、提交信息、README、NOTICE 用英文；`notes/` 用中文。
- 许可证：代码与产物均为 MIT（D-013）。
- 不做全局安装；依赖只装在项目的 `.venv`。

## 需要重点审查的输入

以下情形设计文档没有明说，但最容易出错，测试已分别落到对应任务：

1. 大小写与末尾的点：清单或数据集里出现 `Telegram.ORG.` 时，应与 `telegram.org` 视为同一主机（任务 2、3）。
2. IPv4 与 IPv6 混合比较：判断网段重叠时，不同版本的网段应视为不重叠，而不是抛出异常（任务 3）。
3. 上游返回空内容或 HTML 错误页：Telegram 网段解析为零条时，构建应失败，而不是发布一个没有 IP 规则的列表（任务 5）。
4. v2fly 的 `include:` 循环引用或引用不存在的文件：应报出文件名并失败，而不是无限递归或静默跳过（任务 4）。
5. 后缀与相似域名：`host-suffix, telegram.org` 不能命中 `nottelegram.org`，只能命中它自己和以 `.telegram.org` 结尾的主机（任务 3）。

## 文件结构

```
pyproject.toml, uv.lock, LICENSE, NOTICE, README.md, .gitignore
src/quanlight/
  model.py        # Rule、Bundle 数据类与常量
  manifest.py     # 读取、校验、写出 TOML 清单
  match.py        # 单条规则匹配与按顺序路由
  v2fly.py        # v2fly 数据展开、导入映射、差异对比
  sources.py      # 上游与检查数据的解析（纯函数）
  fetch.py        # 网络下载与上游提交哈希
  check.py        # 直连例外、误伤检查、交叉检查
  emit.py         # 列表、README 片段、探针列表的渲染
  cli.py          # 命令行入口：build、import-v2fly、diff-v2fly、probe
bundles/apns.toml, bundles/telegram.toml
tests/samples.toml
tests/fixtures/   # 小型 v2fly、dnsmasq、gaoyifan、Telegram 网段样例
tests/test_*.py
.github/workflows/build.yml, .github/workflows/upstream-diff.yml
```

## 任务 1：项目骨架

**文件：** 新建 `pyproject.toml`、`src/quanlight/__init__.py`、`tests/test_smoke.py`、`LICENSE`、`.gitignore`（补充 `.venv/`、`dist/`、`.cache/`）。

**接口：** 产出包名 `quanlight`，命令行入口 `quanlight = "quanlight.cli:main"`。

- [ ] 步骤 1：`git init -b main`；`uv init --package --python 3.13`，`uv add --dev pytest`。
- [ ] 步骤 2：写 `tests/test_smoke.py`，断言 `import quanlight` 成功且 `quanlight.__version__ == "0.1.0"`。
- [ ] 步骤 3：运行 `uv run pytest`，期望 1 passed。
- [ ] 步骤 4：`LICENSE` 写 MIT 全文，版权人填本人 GitHub 账号名。
- [ ] 步骤 5：提交 `chore: scaffold quanlight package`。

## 任务 2：清单模型、读取与校验

**文件：** 新建 `src/quanlight/model.py`、`src/quanlight/manifest.py`、`tests/test_manifest.py`。

**接口：**

- `RULE_TYPES = ("host", "host-suffix", "host-wildcard", "host-keyword", "ip-cidr", "ip6-cidr", "ip-asn")`
- `ROLES = ("core", "dependency", "cn-exception")`
- `@dataclass(frozen=True) class Rule`：`type: str`、`value: str`、`role: str`、`source: str`、`reason: str | None = None`、`breadth: str | None = None`、`review_by: date | None = None`、`exempt: tuple[str, ...] = ()`、`asn_verified: str | None = None`
- `@dataclass(frozen=True) class Bundle`：`name: str`、`description: str`、`order: int`、`rules: tuple[Rule, ...]`、`upstream: tuple[str, ...] = ()`、`uses: tuple[str, ...] = ()`、`v2fly_exclude: tuple[str, ...] = ()`
- `normalize_host(value: str) -> str`：小写、去末尾点。
- `load_bundle(path: Path) -> Bundle`；`load_bundles(directory: Path) -> list[Bundle]`，按 `order` 再按 `name` 排序。
- `validate_bundle(bundle: Bundle, today: date) -> list[str]`，返回错误信息列表，空列表表示通过。
- `dump_bundle(bundle: Bundle) -> str`，写出可被 `load_bundle` 读回的 TOML 文本。

- [ ] 步骤 1：写测试：
  - `test_load_normalizes_host`：清单值 `Telegram.ORG.` 读入后为 `telegram.org`。
  - `test_validate_rejects_unknown_type`：`type = "user-agent"` 报错。
  - `test_validate_requires_reason`：`host-keyword`、`ip-asn`、`breadth = "broad"`、非空 `exempt` 缺 `reason` 时各报一条错。
  - `test_validate_broad_requires_review_by`：`breadth = "broad"` 缺 `review_by` 报错；`review_by` 早于 `today` 报错。
  - `test_validate_asn_requires_verification`：`ip-asn` 缺 `asn_verified` 报错。
  - `test_validate_rejects_bad_values`：`ip-cidr` 值不是 IPv4 网段、`ip6-cidr` 值不是 IPv6 网段、`host-suffix` 值含空格或 `*` 时报错。
  - `test_dump_roundtrip`：`load_bundle` 读回 `dump_bundle` 的输出，与原对象相等。
- [ ] 步骤 2：运行 `uv run pytest tests/test_manifest.py`，期望全部失败。
- [ ] 步骤 3：实现上述接口。清单中 `[[rule]]` 对应 `rules`，`[[upstream]]` 的 `kind` 收集进 `upstream`。
- [ ] 步骤 4：运行同一命令，期望全部通过。
- [ ] 步骤 5：提交 `feat: bundle manifest model and validation`。

## 任务 3：匹配器

**文件：** 新建 `src/quanlight/match.py`、`tests/test_match.py`。

**接口：**

- `rule_matches_host(rule: Rule, host: str) -> bool`：只对主机类规则返回真；`host` 相等，`host-suffix` 相等或以 `.<值>` 结尾，`host-wildcard` 用 `fnmatch.fnmatchcase`，`host-keyword` 为子串。
- `rule_matches_ip(rule: Rule, ip: IPv4Address | IPv6Address) -> bool`：`ip-cidr`、`ip6-cidr` 判断包含；`ip-asn` 恒为假，因为没有 ASN 数据。
- `networks_overlap(a: IPv4Network | IPv6Network, b: IPv4Network | IPv6Network) -> bool`：版本不同返回假。
- `@dataclass(frozen=True) class RuleList`：`name: str`、`policy: str`、`rules: tuple[Rule, ...]`。
- `route(lists: Sequence[RuleList], host: str | None, ip: IPAddress | None, final: str) -> str`：返回命中列表的 `policy`。先按顺序用全部列表的主机类规则匹配 `host`；都未命中且给了 `ip`，再按顺序匹配 IP 类规则；仍未命中返回 `final`。这是设计文档中“暂按”的语义，探针结果出来后可能调整。

- [ ] 步骤 1：写测试：
  - `test_suffix_boundary`：`host-suffix, telegram.org` 命中 `telegram.org` 与 `web.telegram.org`，不命中 `nottelegram.org`。
  - `test_host_exact`：`host, a.example.com` 不命中 `b.a.example.com`。
  - `test_wildcard`：`host-wildcard, *.ingest.sentry.io` 命中 `o1.ingest.sentry.io`，不命中 `ingest.sentry.io`。
  - `test_case_and_trailing_dot`：`route` 传入 `Web.Telegram.Org.` 时与小写形式结果相同。
  - `test_overlap_mixed_versions`：`networks_overlap(ip_network("1.0.0.0/8"), ip_network("::/0"))` 为假且不抛异常。
  - `test_route_order_and_ip_fallback`：两个列表都能命中时返回排在前面的策略；主机未命中、IP 落在第二个列表网段内时返回第二个列表的策略；都未命中返回 `final`。
- [ ] 步骤 2：运行 `uv run pytest tests/test_match.py`，期望失败。
- [ ] 步骤 3：实现接口。
- [ ] 步骤 4：运行同一命令，期望通过。
- [ ] 步骤 5：提交 `feat: rule matcher and ordered routing`。

## 任务 4：v2fly 展开、导入与差异

**文件：** 新建 `src/quanlight/v2fly.py`、`tests/test_v2fly.py`、`tests/fixtures/v2fly/`（自建的小型数据文件，含 `include:`、`full:`、`keyword:`、`regexp:`、`@cn`、`@ads`、循环引用的样例）。

**接口：**

- `@dataclass(frozen=True) class Entry`：`kind: str`（`domain`、`full`、`keyword`、`regexp`）、`value: str`、`attrs: frozenset[str]`、`file: str`。
- `expand(data_dir: Path, name: str, exclude: Iterable[str] = ()) -> list[Entry]`：递归展开 `include:`，支持 `include:x @attr` 与 `@-attr` 过滤，跳过 `exclude` 中的文件；循环引用或文件不存在时抛出 `V2flyError`，信息里包含文件名。
- `@dataclass class ImportResult`：`rules: list[Rule]`、`skipped: list[tuple[Entry, str]]`（条目与原因）。
- `to_rules(entries: Iterable[Entry], source: str) -> ImportResult`，按设计文档的映射表：`domain` 转为 `host-suffix`；`full` 转为 `host`；`keyword` 跳过，原因 `keyword-needs-review`；`regexp` 跳过，原因 `regexp-unsupported`；带 `@ads` 的跳过，原因 `ads`；带 `@cn` 的 `role` 设为 `cn-exception`，其余为 `core`。
- `diff(bundle: Bundle, imported: ImportResult) -> tuple[list[Rule], list[Rule]]`：只比较 `source` 以 `v2fly:` 开头的规则，返回（上游新增，清单中有而上游已无）。

- [ ] 步骤 1：写测试：
  - `test_expand_include_with_attr_filter`：`include:svc @cn` 只带入带 `@cn` 的条目。
  - `test_expand_exclude`：`exclude=["youtube"]` 时不展开 `include:youtube`。
  - `test_expand_cycle_and_missing`：循环引用与缺失文件都抛 `V2flyError`，信息含文件名。
  - `test_to_rules_mapping`：逐项核对上述映射。
  - `test_diff`：清单比上游多一条、少一条时分别返回。
- [ ] 步骤 2：运行 `uv run pytest tests/test_v2fly.py`，期望失败。
- [ ] 步骤 3：实现接口。
- [ ] 步骤 4：运行同一命令，期望通过。
- [ ] 步骤 5：提交 `feat: v2fly expansion, import mapping and diff`。

## 任务 5：上游与检查数据

**文件：** 新建 `src/quanlight/sources.py`、`src/quanlight/fetch.py`、`tests/test_sources.py`、`tests/fixtures/` 下的样例文件。

**接口：**

- `parse_telegram_cidr(text: str, bundle: str) -> list[Rule]`：每行一个网段，IPv4 生成 `ip-cidr`，IPv6 生成 `ip6-cidr`，`source` 为 `official:https://core.telegram.org/resources/cidr.txt`；没有任何有效网段或出现无法解析的行时抛 `SourceError`。
- `parse_dnsmasq(text: str) -> set[str]`：提取 `server=/<domain>/...` 中的域名并规范化；结果为空时抛 `SourceError`。
- `parse_cidr_list(text: str) -> list[IPv4Network | IPv6Network]`：用于 gaoyifan 的 `china.txt` 与 `china6.txt`；结果为空时抛 `SourceError`。
- `UPSTREAM_KINDS: dict[str, str]`：`{"telegram-cidr": "https://core.telegram.org/resources/cidr.txt"}`。
- `CHECK_SOURCES`：三项，分别为 dnsmasq-china-list 的 `accelerated-domains.china.conf`、gaoyifan 的 `ip-lists` 分支 `china.txt` 与 `china6.txt`、v2fly 仓库（用于展开 `geolocation-cn`）。每项写明原始文件地址与 GitHub 仓库及分支。
- `fetch_text(url: str, retries: int = 3) -> str`：失败抛 `FetchError`。
- `fetch_commit(repo: str, branch: str) -> str`：调用 `https://api.github.com/repos/{repo}/commits/{branch}`，返回提交哈希；有 `GITHUB_TOKEN` 环境变量时带上认证头。
- `fetch_v2fly_data(dest: Path) -> Path`：下载 v2fly 仓库的 tarball 并解压，返回 `data/` 目录。

- [ ] 步骤 1：写测试（只测纯函数，不联网）：
  - `test_telegram_cidr_parses_both_versions`：样例中的 IPv4 与 IPv6 网段分别生成对应类型。
  - `test_telegram_cidr_rejects_html_and_empty`：输入为 HTML 错误页或空字符串时抛 `SourceError`。
  - `test_dnsmasq_parse`：大小写与末尾点被规范化，注释行被忽略。
  - `test_cidr_list_rejects_empty`。
- [ ] 步骤 2：运行 `uv run pytest tests/test_sources.py`，期望失败。
- [ ] 步骤 3：实现接口；`fetch.py` 只用 `urllib.request` 与 `tarfile`。
- [ ] 步骤 4：运行同一命令，期望通过。
- [ ] 步骤 5：提交 `feat: upstream and check-data sources`。

## 任务 6：检查

**文件：** 新建 `src/quanlight/check.py`、`tests/test_check.py`。

**接口：**

- `proxy_rules(bundle: Bundle) -> list[Rule]`：去掉 `cn-exception` 后的规则。
- `direct_exceptions(bundles: Sequence[Bundle]) -> list[Rule]`：被任一包的代理主机规则覆盖的 `cn-exception` 条目，去重、排序。“覆盖”指例外的值本身会被该代理规则命中。
- `build_ios_lists(bundles: Sequence[Bundle], exceptions: list[Rule]) -> list[RuleList]`：第一个为 `RuleList("direct-exceptions", "direct", ...)`，其后每个包一个 `RuleList(name, name, proxy_rules)`，按 `order` 排序。
- `@dataclass(frozen=True) class Misfire`：`bundle: str`、`rule: Rule`、`target: str`（被误伤的国内域名或网段）。
- `find_misfires(lists: Sequence[RuleList], cn_domains: Iterable[str], cn_networks: Iterable[IPNetwork]) -> list[Misfire]`：
  - 域名：对每个国内域名调用 `route(lists, host, None, final="direct")`，结果不是 `direct` 即为误伤，找出命中的规则。
  - 网段：代理列表中每条 `ip-cidr`、`ip6-cidr` 与大陆网段 `networks_overlap` 即为误伤。
  - 被规则自身 `exempt` 列出的目标不计。
- `cross_check(bundles: Sequence[Bundle]) -> list[str]`：
  - 不同包之间出现完全相同的 `(type, value)` 时报错。
  - 包 A 的规则命中包 B 某条主机规则的值、且 A 排在 B 之后时报错，即“更具体的包在前”。
- `overdue_broad(bundles: Sequence[Bundle], today: date) -> list[Rule]`。

- [ ] 步骤 1：写测试：
  - `test_direct_exceptions_only_when_covered`：落在 `google.com` 代理后缀下的 `cn-exception` 生成例外；不被任何代理规则覆盖的不生成。
  - `test_misfire_domain_and_exempt`：代理 `host-suffix, example.cn` 遇到国内域名 `a.example.cn` 报一条误伤；加上 `exempt = ["a.example.cn"]` 后不报。
  - `test_misfire_cleared_by_exception`：国内域名被 `direct-exceptions` 先行命中时不报。
  - `test_misfire_ip_overlap`：代理网段与大陆网段重叠时报错，IPv6 与 IPv4 不互相比较。
  - `test_cross_check_duplicate_and_order`：完全重复报错；更具体的包排在后面报错，调换 `order` 后通过。
- [ ] 步骤 2：运行 `uv run pytest tests/test_check.py`，期望失败。
- [ ] 步骤 3：实现接口。
- [ ] 步骤 4：运行同一命令，期望通过。
- [ ] 步骤 5：提交 `feat: direct exceptions, misfire and cross checks`。

## 任务 7：产物渲染

**文件：** 新建 `src/quanlight/emit.py`、`tests/test_emit.py`、`NOTICE`。

**接口：**

- `render_list(name: str, rules: Sequence[Rule], provenance: Mapping[str, str]) -> str`：
  - 文件头为若干 `# ` 注释行，写 `quanlight <name>`、规则条数、`provenance` 中每个数据来源及其版本。
  - 正文每行 `<type>, <value>, <name>`，按类型顺序（主机类在前、IP 类在后）再按值排序，去重，以换行结尾。
- `render_filter_remote(bundles: Sequence[Bundle], base_url: str) -> str`：生成设计文档“订阅与产物”一节的 `[filter_remote]` 片段。`direct-exceptions` 在最前，`force-policy=direct`；各包按 `order`，`force-policy=<proxy-policy>` 占位；最后一行 `FILTER_LAN`。
- `NOTICE`：英文，列出 v2fly/domain-list-community（MIT，附其版权声明）、Telegram 官方网段地址，并说明检查用的 dnsmasq-china-list、gaoyifan/china-operator-ip 不进入产物。

- [ ] 步骤 1：写测试：
  - `test_render_list_deterministic`：同一输入渲染两次结果相同；输出不含当天日期字符串。
  - `test_render_list_order_and_dedupe`：主机类在 IP 类之前，重复规则只出现一次。
  - `test_render_filter_remote`：第一行是 `direct-exceptions`，带 `force-policy=direct`；包按 `order` 排列；最后一行以 `FILTER_LAN` 开头。
- [ ] 步骤 2：运行 `uv run pytest tests/test_emit.py`，期望失败。
- [ ] 步骤 3：实现接口并写 `NOTICE`。
- [ ] 步骤 4：运行同一命令，期望通过。
- [ ] 步骤 5：提交 `feat: list and subscription snippet rendering`。

## 任务 8：构建命令与样本测试

**文件：** 新建 `src/quanlight/cli.py`、`tests/samples.toml`、`tests/test_build.py`。

**接口：**

- `main(argv: list[str] | None = None) -> int`，子命令 `build`、`import-v2fly`、`diff-v2fly`、`probe`；本任务实现 `build` 与 `import-v2fly`。
- `build(bundles_dir: Path, out_dir: Path, *, today: date, data: CheckData, upstream: Mapping[str, str]) -> BuildReport`：
  - 依次执行：校验、`[[upstream]]` 合并、直连例外、交叉检查、误伤检查、过期 `broad` 检查、样本测试、渲染。
  - 有任何错误时不写 `out_dir`，返回的 `BuildReport.errors` 非空。
  - 成功时写出 `out_dir/ios/<name>.list`、`out_dir/ios/direct-exceptions.list`、`out_dir/README.md`（订阅片段）、`out_dir/NOTICE`、`out_dir/LICENSE`。
- `@dataclass class CheckData`：`cn_domains: set[str]`、`cn_networks: list[IPNetwork]`、`provenance: dict[str, str]`。命令行入口负责下载并填充，测试直接构造。
- `@dataclass class BuildReport`：`errors: list[str]`、`warnings: list[str]`、`broad: list[Rule]`、`counts: dict[str, int]`；`to_markdown() -> str` 用于写入 `$GITHUB_STEP_SUMMARY`。
- `tests/samples.toml` 格式：每个 `[[sample]]` 有 `host` 或 `ip` 其一，以及 `expect`（`direct` 或包名）。
- 命令行 `quanlight build --out dist`：失败时返回 1。
- 命令行 `quanlight import-v2fly <file> --bundle <name> [--exclude x]`：用 `fetch_v2fly_data` 取得 v2fly 数据并展开 `<file>`，输出 `dump_bundle` 文本到标准输出，跳过的条目及原因输出到标准错误。

- [ ] 步骤 1：写测试（全部用 `tests/fixtures`，不联网）：
  - `test_build_writes_lists`：合法的两个包构建成功，产物文件齐全。
  - `test_build_fails_without_writing`：注入一条误伤后 `errors` 非空，`out_dir` 不存在。
  - `test_samples_mismatch_fails`：样本期望与模拟结果不符时报错，信息包含该样本。
  - `test_upstream_empty_fails`：`upstream` 中 Telegram 网段内容为空时构建失败。
- [ ] 步骤 2：运行 `uv run pytest tests/test_build.py`，期望失败。
- [ ] 步骤 3：实现 `build`、`CheckData`、`BuildReport` 与两个子命令。
- [ ] 步骤 4：运行 `uv run pytest`，期望全部通过。
- [ ] 步骤 5：提交 `feat: build command with sample tests`。

## 任务 9：首批两个服务包

**文件：** 新建 `bundles/apns.toml`、`bundles/telegram.toml`；修改 `tests/samples.toml`。

**内容：**

- `apns.toml`：`order = 10`；只有一条 `host-suffix, push.apple.com`，`role = "core"`，`source = "manual"`。不收录 `akadns.net` 子区与 17.x 网段（设计文档“APNs 包”一节）。
- `telegram.toml`：`order = 40`；用 `quanlight import-v2fly telegram --bundle telegram` 生成初稿，逐条确认每个 `host-suffix` 属 Telegram 独有；加 `[[upstream]] kind = "telegram-cidr"`。
- 样本：
  - `courier.push.apple.com` 期望 `apns`；`api.apple.com` 期望 `direct`。
  - `web.telegram.org`、`t.me` 期望 `telegram`；`91.108.4.1` 期望 `telegram`。
  - `www.taobao.com`、`weixin.qq.com`、`api.bilibili.com` 期望 `direct`。

- [ ] 步骤 1：生成并人工核对两个清单。
- [ ] 步骤 2：联网运行 `uv run quanlight build --out dist`，期望退出码 0，`dist/ios/` 下有 `apns.list`、`telegram.list`、`direct-exceptions.list`。
- [ ] 步骤 3：检查 `dist/ios/telegram.list` 含 `ip-cidr, 91.108.4.0/22, telegram` 与 `ip6-cidr, 2001:67c:4e8::/48, telegram`。
- [ ] 步骤 4：再运行一次构建，用 `diff -r` 比较两次产物，期望无差异。
- [ ] 步骤 5：提交 `feat: add apns and telegram bundles`。

## 任务 10：匹配语义探针

**文件：** 修改 `src/quanlight/emit.py`、`src/quanlight/cli.py`；新建 `tests/test_probe.py`、`probe/README.md`（英文操作说明）。

**接口：**

- `render_probe(case: str) -> dict[str, str]`：返回文件名到内容的映射；命令行 `quanlight probe --out dist/probe` 写出全部探针文件。
- 探针用公开、稳定、可在 Safari 打开的主机，以 `force-policy=reject` 与 `direct` 的差异判定命中结果。每个用例输出两个列表文件与一段 `[filter_remote]` 片段：

| 用例 | 列表一（排在前面） | 列表二（排在后面） | 要回答的问题 |
|---|---|---|---|
| `order` | `host-suffix, example.com`，reject | `host-suffix, example.com`，direct | 同类型时是否按订阅顺序 |
| `type` | `host-suffix, example.com`，reject | `host, www.example.com`，direct | `host` 是否优先于排在前面的 `host-suffix` |
| `local` | 本机 `[filter_local]` 写 `host, www.example.com, direct` | `host, www.example.com`，reject | 本地是否先于远程 |
| `wildcard` | `host-wildcard, *.example.com`，reject | 无 | `*` 是否匹配 `www.example.com` 与 `example.com` |
| `cname` | `host, <某 CNAME 目标>`，reject | 无 | 主机规则是否匹配 CNAME 目标 |

  `cname` 用例的主机由执行者用 `dig` 选一个 CNAME 链稳定的公开站点，写进 `probe/README.md`。每个用例在“分流匹配优化”开启与关闭时各测一次。

- [ ] 步骤 1：写 `test_probe_outputs`：每个用例都生成两个列表文件与片段，片段中两行的 `force-policy` 分别为 `reject` 与 `direct`。
- [ ] 步骤 2：运行测试，期望失败。
- [ ] 步骤 3：实现并写 `probe/README.md`，说明导入方式、在 Quantumult X 请求记录里看什么、结果记录表格。
- [ ] 步骤 4：运行测试，期望通过；运行 `uv run quanlight probe --out dist/probe` 并检查产物。
- [ ] 步骤 5：提交 `feat: rule-matching probe lists`。

## 任务 11：持续集成与发布

**文件：** 新建 `.github/workflows/build.yml`、`.github/workflows/upstream-diff.yml`、`README.md`；修改 `src/quanlight/cli.py`（实现 `diff-v2fly`）。

**接口：**

- 命令行 `quanlight diff-v2fly --bundles bundles`：对每个声明了 v2fly 来源的包重新导入，输出 Markdown 差异表到标准输出；有差异时返回 0，只报告，不失败。
- `build.yml`：
  - 触发：`schedule` 为 `0 18 * * *`（北京时间 02:00）、推送到 `main`、`workflow_dispatch`。
  - 权限：`contents: write`。
  - 步骤：`astral-sh/setup-uv`；`uv run pytest`；`uv run quanlight build --out dist`，并把报告写入 `$GITHUB_STEP_SUMMARY`；把 `dist/` 以单个提交强制推送到 `release` 分支，内容无变化时跳过推送；对每个产物请求 `https://purge.jsdelivr.net/gh/<owner>/quanlight@release/<path>`。
- `upstream-diff.yml`：每周一 `0 1 * * 1`，运行 `diff-v2fly` 并写入 `$GITHUB_STEP_SUMMARY`。
- `README.md`：英文，说明项目用途、两种配置的分工、订阅地址（jsDelivr 与 `raw.githubusercontent.com` 备用）、`[filter_remote]` 片段的获取位置、如何新增服务包。

- [ ] 步骤 1：为 `diff-v2fly` 写 `test_diff_v2fly_reports_changes`，用 fixtures 断言输出含新增与删除的条目，退出码为 0。
- [ ] 步骤 2：实现并运行 `uv run pytest`，期望全部通过。
- [ ] 步骤 3：写两个工作流与 README；用 `uv run quanlight build --out dist` 在本地再验证一次。
- [ ] 步骤 4：提交 `ci: daily build, release branch and upstream diff`。
- [ ] 步骤 5：创建公开仓库并推送。这一步对外公开，执行前须征得本人同意：`gh repo create quanlight --public --source . --push`。
- [ ] 步骤 6：在 GitHub 手动触发一次 `build`，期望成功；`release` 分支出现产物；用 `curl -sI` 访问 jsDelivr 与 `raw.githubusercontent.com` 上的 `ios/telegram.list`，期望返回 200。

## 第 1 阶段完成标准

- `uv run pytest` 全部通过；本地与 Actions 上的构建都成功，两次构建产物相同。
- `release` 分支上可订阅 `apns`、`telegram` 与 `direct-exceptions` 三个列表。
- 本人在真机上按 `probe/README.md` 完成探针，结果写成决策日志；据此决定是否调整 `route` 的语义，然后编写第 2 阶段计划。
