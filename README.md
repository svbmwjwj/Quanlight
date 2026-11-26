# Quanlight

Quantumult X filter lists built from reviewed, per-service manifests.

Each rule is chosen with the narrowest Quantumult X rule type that covers the
service, and every build checks that no proxy rule captures mainland China
domains or networks before anything is published.

## Profiles

- iOS (blacklist): only the services you subscribe to go through a proxy;
  everything else connects directly. One list per service, plus a shared
  Apple Push Notification list.
- macOS (whitelist): planned; only confirmed mainland services connect
  directly.

## Subscribe

Lists are published on the `release` branch. Use the GitHub link where it is
reachable and a mainland-friendly mirror otherwise; all serve the same files:

| Mirror | Base URL |
|---|---|
| GitHub | `https://raw.githubusercontent.com/svbmwjwj/quanlight/release` |
| Mainland China (ghfast.top, a third-party GitHub proxy) | `https://ghfast.top/https://raw.githubusercontent.com/svbmwjwj/quanlight/release` |
| jsDelivr (Fastly) | `https://fastly.jsdelivr.net/gh/svbmwjwj/quanlight@release` |
| jsDelivr | `https://cdn.jsdelivr.net/gh/svbmwjwj/quanlight@release` |

Append `/ios/<name>.list` to a base URL. A third-party proxy can see and
alter what it serves; prefer GitHub or jsDelivr when they work for you.

The release branch's `README.md` contains a ready-to-paste `[filter_remote]`
snippet in the correct order. Every line needs a `force-policy`: replace
`<proxy-policy>` with your own policy name, otherwise the rules point at a
policy that does not exist. End `[filter_local]` with `final, direct`.

## Templates

`templates/` holds ready-to-adapt profiles with every private value replaced by
a `<...>` placeholder:

- `templates/ios_blacklist.conf`: blacklist mode on quanlight lists.
- `templates/macos_whitelist.conf`: whitelist mode; uses third-party direct lists until
  quanlight's macOS lists exist.

## Build locally

```
uv run pytest
uv run quanlight build --out dist
```

The build downloads official upstream data (Telegram networks) and the check
data (dnsmasq-china-list, v2fly `geolocation-cn`, gaoyifan/china-operator-ip).
It fails without writing anything when a manifest is invalid, a proxy rule
mis-routes mainland traffic, or a sample in `tests/samples.toml` routes
differently than expected.

## Add a service

1. Draft a manifest from v2fly, then review every rule type by hand:

   ```
   uv run quanlight import-v2fly <v2fly-file> --bundle <name> --order <n> > bundles/<name>.toml
   ```

2. Keep `host-suffix` for domains the service owns; use `host` or
   `host-wildcard` on shared domains. `host-keyword`, `ip-asn`, broad shared
   domains and exemptions need a `reason`.
3. Add samples to `tests/samples.toml` and run the build.

## Licence

Code and lists: MIT. Data sources are listed in `NOTICE`.
