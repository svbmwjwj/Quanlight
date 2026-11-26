# Rule-matching probes

Quantumult X does not document how it orders rules across `[filter_local]`,
remote lists and rule types. These probes answer that on a real device; the
build's routing model (`src/quanlight/match.py`) is adjusted to the results.

## Run

1. Generate the files, or use the published copies under `probe/` on the
   `release` branch:

   ```
   uv run quanlight probe --out dist/probe --base-url <release base url>
   ```

2. For one case at a time, copy the lines of `probe-<case>.conf` into the
   matching sections of a test profile, then update the remote resources.
3. Open each listed host in Safari and look up the request in Quantumult X's
   request log. `reject` means the first list (or the rule under test) won;
   `direct` means the other one did.
4. Repeat every case with "Filter Match Optimization" on and off.
5. Remove the probe lines afterwards.

## Cases

| Case | Question | Hosts |
|---|---|---|
| order | Same rule type in two lists: does the earlier list win? | www.example.com |
| type | Does `host` win over an earlier `host-suffix`? | www.example.com |
| local | Does `[filter_local]` win over a remote list? | www.example.com |
| wildcard | Does `*.example.com` match `www.example.com` and the bare `example.com`? | both |
| cname | Do host rules match a CNAME target (`www.microsoft.com-c-3.edgekey.net`)? | www.microsoft.com |

## Record

| Case | Optimization on | Optimization off |
|---|---|---|
| order | | |
| type | | |
| local | | |
| wildcard (www / bare) | | |
| cname | | |
