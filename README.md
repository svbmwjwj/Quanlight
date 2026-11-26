# Quanlight

Quantumult X filter lists for a proxy-fallback setup: mainland China domains
and networks connect directly, and everything else falls through to `final`
and goes through your proxy.

The direct list is rebuilt from public datasets on every build, and every
build checks that no overseas domain or network in the reverse-check data is
routed directly before anything is published.

## Lists

- `apns.list`: Apple Push Notification service. Subscribe it first and force
  it through the proxy; push notifications for apps such as Telegram fail
  when it connects directly.
- `china.list`: mainland China domains and networks, forced to `direct`.
  Built from dnsmasq-china-list (`accelerated-domains.china.conf`), v2fly
  `geolocation-cn` and gaoyifan/china-operator-ip.

iOS and macOS subscribe to the same lists.

## Subscribe

Lists are published at the root of the `release` branch. Use the GitHub link
where it is reachable and a mainland-friendly mirror otherwise; all serve the
same files:

| Mirror | Base URL |
|---|---|
| GitHub | `https://raw.githubusercontent.com/svbmwjwj/quanlight/release` |
| Mainland China (ghfast.top, a third-party GitHub proxy) | `https://ghfast.top/https://raw.githubusercontent.com/svbmwjwj/quanlight/release` |
| jsDelivr (Fastly) | `https://fastly.jsdelivr.net/gh/svbmwjwj/quanlight@release` |
| jsDelivr | `https://cdn.jsdelivr.net/gh/svbmwjwj/quanlight@release` |

A third-party proxy can see and alter what it serves; prefer GitHub or
jsDelivr when they work for you.

```
[filter_remote]
https://raw.githubusercontent.com/svbmwjwj/quanlight/release/apns.list, tag=quanlight-apns, force-policy=<proxy-policy>, update-interval=-1, opt-parser=false, enabled=true
https://raw.githubusercontent.com/svbmwjwj/quanlight/release/china.list, tag=quanlight-china, force-policy=direct, update-interval=-1, opt-parser=false, enabled=true
FILTER_LAN, tag=LAN, force-policy=direct, enabled=true

[filter_local]
# personal exceptions go here
final, <proxy-policy>
```

Keep `apns.list` above `china.list`. Every line needs its `force-policy`:
replace `<proxy-policy>` with your own policy name, otherwise the rules point
at a policy that does not exist. `update-interval=-1` turns off automatic
syncing; update the lists by hand after a release. The release branch's
`README.md` has the same snippet for GitHub and the mainland mirror.

Domains that match no rule are resolved by the `[dns]` servers in your
profile; addresses inside mainland networks connect directly and the rest go
through `final`.

## Templates

`templates/` holds ready-to-adapt profiles with every private value replaced by
a `<...>` placeholder:

- `templates/ios_whitelist.conf`: iOS profile on the quanlight lists.
- `templates/macos_whitelist.conf`: macOS profile on the same lists.

## Build locally

```
uv run pytest
uv run quanlight build --out dist
```

The build downloads the direct data and the reverse-check data (v2fly
`geolocation-!cn` without `@cn` entries, Telegram, GitHub and Google
networks). It fails without writing anything when a manifest is invalid, a
data source cannot be downloaded or parsed, an overseas entry falls to the
direct list, or a sample in `tests/samples.toml` routes differently than
expected. Pass `--previous <dir>` with the previous release to also fail when
a data source shrinks by more than half.

## Adjust the direct list

Edit `bundles/china.toml`:

- `[[rule]]`: a direct entry the datasets miss, with `type`, `value`,
  `source` (`official:<url>`, `observed` or `manual`) and a `reason`.
- `[[exclude]]`: drop every upstream entry with this value, with a `reason`.
- `[[keep]]`: accept reverse-check hits caused by the direct rule with this
  value, with a `reason`.

## Licence

Code and lists: MIT. Data sources are listed in `NOTICE`.
