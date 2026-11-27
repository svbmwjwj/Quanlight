# Quanlight lists

Built from https://github.com/svbmwjwj/quanlight. Mainland China domains and networks connect directly;
everything else falls through to `final` and goes through your proxy.

`hello world ：）` is the proxy policy in the author's profile; replace it with yours. Every line needs its `force-policy`;
without it the rules point at a policy that does not exist.

## Base URLs

- GitHub: `https://raw.githubusercontent.com/svbmwjwj/quanlight/release`
- Mainland China (GitHub proxy, third party): `https://ghfast.top/https://raw.githubusercontent.com/svbmwjwj/quanlight/release`
- jsDelivr (Fastly): `https://fastly.jsdelivr.net/gh/svbmwjwj/quanlight@release`
- jsDelivr: `https://cdn.jsdelivr.net/gh/svbmwjwj/quanlight@release`

## Subscribe from GitHub

```
[filter_remote]
https://raw.githubusercontent.com/svbmwjwj/quanlight/release/apns.list, tag=apns, force-policy=hello world ：）, update-interval=-1, opt-parser=false, enabled=true
https://raw.githubusercontent.com/svbmwjwj/quanlight/release/china.list, tag=china, force-policy=direct, update-interval=-1, opt-parser=false, enabled=true
FILTER_LAN, tag=LAN, force-policy=direct, enabled=true

[filter_local]
# personal exceptions go here
final, hello world ：）
```

## Subscribe from mainland China

```
[filter_remote]
https://ghfast.top/https://raw.githubusercontent.com/svbmwjwj/quanlight/release/apns.list, tag=apns, force-policy=hello world ：）, update-interval=-1, opt-parser=false, enabled=true
https://ghfast.top/https://raw.githubusercontent.com/svbmwjwj/quanlight/release/china.list, tag=china, force-policy=direct, update-interval=-1, opt-parser=false, enabled=true
FILTER_LAN, tag=LAN, force-policy=direct, enabled=true

[filter_local]
# personal exceptions go here
final, hello world ：）
```
