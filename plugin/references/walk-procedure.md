# Walk procedure

## Order

1. **Landing and shell.** Load the signed-in home and probe it. The probe's link groups, folded
   by `walk_summary.py` into the frontier, are the breadth-first frontier. Use `take_snapshot`
   with a `filePath` only when a menu or dialog needs a `uid` to open.
2. **Breadth.** Visit each frontier entry once. For each page record: URL pattern (ids replaced by
   `{name}`), title, purpose in one line, the controls on it, and the requests it fired.
3. **Depth.** For each section: open one item of every detail type, page through every list
   once (next page, infinite scroll, load more), apply one search, one filter and one sort, open
   every tab and dialog that does not commit anything.
4. **Settings and account.** Read every settings page. Each toggle or field is a capability with
   `mutates: true`, not exercised.
5. **Write paths, observed safely.** For each state-changing control, open it and stop before the
   commit. Many forms reveal their endpoint through validation calls, autosave drafts or bundle
   strings without submitting. Record what is visible; mark the endpoint `unknown` otherwise.

## Capture, per page

Measured on a GitHub walk (2026-10-27, 9 pages): the old loop of `navigate_page`,
`list_network_requests` and `get_network_request` cost 11,766 browser-tool tokens; this loop cost
2,413 for 11 pages and a pagination check.

1. **First page.** `navigate_page` with this `initScript`, which keeps every resource-timing entry
   (Chrome keeps 250 by default, and GitHub loads about 300 and calls `clearResourceTimings`):

   ```js
   window.__wreTiming={clears:0,full:0};performance.setResourceTimingBufferSize(5000);performance.clearResourceTimings=()=>{__wreTiming.clears++};performance.onresourcetimingbufferfull=()=>{__wreTiming.full++};
   ```

2. **Probe.** `evaluate_script` with `sourcePath` `${CLAUDE_PLUGIN_ROOT}/assets/scope-probe.js`, `filePath`
   `<capture-dir>/<nn>.json` and `waitForStableDom: false`. The reply is about 30 tokens. The
   file holds call patterns (ids as `{id}`, query keys without values), noise counts, link
   groups, pagination links, form methods and field names, CSRF input and meta names,
   JS-visible cookie names, framework flags, and for up to four new same-origin GET calls a
   refetch giving response header names and the JSON shape. It scrolls once to fire lazy loads.
   It never prints a value.
3. **Queue the rest.** One `evaluate_script` sets
   `sessionStorage.setItem("__wreQueue", JSON.stringify([...paths]))` after the first probe. Each
   later probe call takes the next path, moves there by Turbo or an in-page link click (the
   timing hook survives), and probes it: one call per page, no tab list.
4. **Full reloads.** When a probe returns "Execution context was destroyed", the site reloaded
   the page. Call the probe again with the same `filePath`: it sees the pending path, probes the
   landed page without moving, and reinstalls the hook. `timing.truncated: true` in that file
   means the load filled the default buffer; probe that page again after a `navigate_page` with
   the hook.
5. **Pagination.** `evaluate_script` of `${CLAUDE_PLUGIN_ROOT}/assets/scope-paginate.js` clicks the next link or
   load-more button and returns the requests it fired, about 120 tokens.
6. **Summarize.** `walk_summary.py <capture-dir>` prints one line per page and endpoint, the
   noise list (generic rules plus any same-origin call seen on half the pages, at least 3), the
   frontier ordered pagination, detail, nav, and writes `walk.json`. `--endpoint <pattern>`
   prints one endpoint's header names and shape.

Render verdict: a page with at most two non-noise calls is server-rendered, and its `document`
rows become `html` endpoints. An API-driven site has its shapes in the probe files already.

Fall back to `list_network_requests` only to check a page the probe seems to miss. Do not call
`get_network_request` during a scope: it prints `Cookie` and `Set-Cookie` values into the
transcript and costs 2,000 to 3,500 tokens even with `responseFilePath`.

Coverage by default: open one item of every detail kind the frontier lists, and run the
pagination script once on every list that shows a next link or load-more control.

## What to look for, per category

| Category | Where |
|---|---|
| Auth | Login redirects, cookie names, `Authorization` header presence, token refresh calls, CSRF meta tags or cookies, SSO hosts |
| Pagination | Query keys like `page`, `offset`, `cursor`, `after`, `before`, response fields like `next`, `has_next_page`, `end_cursor`, `Link` headers |
| Multiplexed APIs | One path with many operation names: GraphQL `operationName`, persisted query hashes, RPC method fields |
| Realtime | `WebSocket` and `EventSource` constructors in `performance` entries, `wss://` hosts |
| Rate limiting | `x-ratelimit-*`, `retry-after` header names, 429s, slowdowns |
| Anti-bot | Challenge scripts or cookies (Cloudflare `cf_clearance`, Akamai `_abck`, PerimeterX `_px`, DataDome `datadome`), fingerprint scripts, CAPTCHA widgets |
| Signing | Header or body values that change on every request with a fixed length, named `sign`, `signature`, `nonce`, `x-s`, `x-t` |
| Obfuscation | Bundle style (webpack, Vite), source maps present or not, string-array decoders, `eval` packers |
| Client framework | `__NEXT_DATA__`, `__NUXT__`, React fiber keys, `__APOLLO_CLIENT__`, Relay artifacts |

## Framework probes

`scope-probe.js` returns the framework flags (Next, Nuxt, Apollo, Turbo, React root, webpack
chunks, service worker, embedded JSON script ids) and the CSRF meta and hidden-input names, so
no separate probe call is needed.

## Stopping

Stop and ask the user when: a login wall or challenge appears, a page needs an action that would
change state to go further, the walk passes 150 pages, or the site shows a rate-limit warning.
