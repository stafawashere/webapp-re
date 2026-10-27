# Capture

Two browser paths and a fallback, one rule: capture inside a window that contains exactly one action.

## Choosing a path

| Need | Path |
|---|---|
| The user's real browser, real sign-in, no setup | chrome-devtools |
| Full response bodies, cold load included | chrome-devtools |
| Scope walk across many pages | chrome-devtools |
| Real wire headers, including `Cookie` | CDP driver |
| Script search inside V8 without refetching bundles | CDP driver |
| chrome-devtools not configured or not connecting | Claude in Chrome, only after asking |

A site-specific skill can fix the path for its site.

## chrome-devtools

The `chrome-devtools` MCP server attaches to the user's running browser over DevTools with
`--autoConnect`. The browser asks the user to approve each new connection, once per session.
Load the tools in one ToolSearch call: `mcp__chrome-devtools__list_pages`, `new_page`,
`navigate_page`, `close_page`, `take_snapshot`, `click`, `fill`, `press_key`, `wait_for`,
`evaluate_script`, `list_network_requests`, `get_network_request`, `list_console_messages`. If none
match, the server is not configured or the user declined the prompt; say so and ask.

Work in a page this process opened with `new_page` and `background: true`, never in one of the
user's. Page-scoped tools need its `pageId`.

What each tool gives:

- `new_page` with a `url` records from the first request, so the cold load is inside the window.
- `list_network_requests` with `resourceTypes: ["document", "xhr", "fetch"]` is the endpoint map,
  about 100 tokens a page. `pageSize` pages through long lists. `includePreservedRequests: true`
  reaches the last three navigations.
- `get_network_request` gives headers and bodies for one `reqid`. Always pass `responseFilePath`
  (and `requestFilePath` for a POST) under `<site-root>/var/captures/<run-id>/`, which is
  gitignored, then read only the
  fields needed. Inline bodies cost thousands of tokens; a saved one costs a few hundred.
- `take_snapshot` with `filePath` saves the accessibility tree (about 7,700 tokens inline on
  Hacker News, about 30 saved). Grep the file for the `uid` to click.
- `evaluate_script` returns one value cheaply. Use it for framework probes and counts, not for
  dumping page state.
- `list_console_messages` shows client errors that explain a failed action.

Saving files only works inside the server's `--workspace`. An "Access denied" error means the
path is outside it.

`get_network_request` does show a `Cookie` request header (verified on GitHub), and `Set-Cookie`
in the response headers. Both print their values inline in the tool result, and
`responseFilePath` only moves the body, so the values enter the transcript. Do not call it on
requests whose cookies you would not want in the transcript, and never copy header or cookie
values into notes, findings or chat; names only. The headers also add about 1,500 tokens when the
site sends a large `Content-Security-Policy`. For the wire headers of a request that must stay
out of the transcript, use the CDP driver. Cookie adoption for the program is the user's step.

Other measured behavior:

- `new_page`, `navigate_page` and `close_page` all append the tab list, which also prints the
  URLs of the user's other tabs (one showed an OAuth `state` value). In-page navigation through
  `scope-probe.js` avoids it; see the walk procedure.
- `new_page` with `isolatedContext` starts signed out (GitHub redirected to `/login`) and still
  prints every tab. Do not use it for a signed-in walk.
- In-page `performance` entries keep 250 resources by default and some sites call
  `clearResourceTimings`, so page-side capture misses calls unless the timing hook in the walk
  procedure runs before load.
- `evaluate_script` with `filePath` replies in about 25 tokens whatever the result size, and
  `sourcePath` keeps a long script out of the call. Both paths must sit under the server's
  `--workspace`.

- `new_page` and `navigate_page` append the list of every open tab to their reply (about 450
  tokens with 13 tabs). Navigate less, and do not re-navigate to a URL just to refresh a request.
- `new_page` with `background: true` can still leave the new page marked `[selected]`. Pass
  `pageId` on every page-scoped call anyway.
- `take_snapshot` rewrites the `filePath` extension to `.txt`. Use the path from the reply.
- `list_network_requests` also lists requests from the user's other browser extensions
  (`chrome-extension://` URLs). Filter them out.
- A request answered with `304` still returns its cached body to `responseFilePath`, but a
  revisit to the same URL gives `304`s, not fresh bodies. Open a different page that fires the
  call, or reload with `ignoreCache: true`, when the first response is needed.

`${CLAUDE_PLUGIN_ROOT}/assets/capture-hook.js` is not needed for a scope walk. The reverse fast
path installs it after load (`format: "script"`), then reads it through `reverse-capture.js`, and
the Claude in Chrome fallback uses it because `read_network_requests` gives no bodies.

Reverse fast path, measured on hn.algolia.com, goal "search stories by keyword", 2026-10-27:

| | step-by-step | fast path |
|---|---|---|
| tool tokens, whole run | 8,312 | 1,818 plus about 650 to read the fast path |
| browser tool tokens | 2,199 | 1,147 |
| tool calls | 23, 5 failed | 10, 0 failed |
| wall time | 159 s | about 55 s |
| search key in transcript | yes, `list_network_requests` URL | no, `REDACTED` |
| ablation | hand-written, 21 elements | `reverse-ablate.js`, 21 elements plus minimal check |

Two protocol facts from that run: a cross-origin API that answers `Access-Control-Allow-Origin: *`
rejects `credentials: "include"`, so the ablation falls back to `same-origin`; and a server-side
cache makes a repeated identical request look stable, so volatile keys are also filtered by name
(`time`, `ms`, `server`, `params`, ids of the request). On GitHub `/search` the results sit
three levels down beside a per-request timer, so the comparison runs on leaf paths, and `accept`
is ablated like any other header because it switches the route between HTML and JSON.

## CDP driver

`${CLAUDE_PLUGIN_ROOT}/scripts/cdp_capture.py` attaches to a Chromium already listening on a debugging port. It never
launches one through Playwright, because automation launch switches set `navigator.webdriver`.
Start the browser yourself, on a dedicated profile the user signs into by hand:

```bash
open -na "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir="$HOME/.webapp-re-profile"
uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/cdp_capture.py --root <site-root> --run <run-id> --label <slug> --url <url> --seconds 12
```

Facts measured on Chromium that cost a run when forgotten:

- **A browser-level auto-attached session delivers no Network events.** Create the tab as
  `about:blank`, attach to it explicitly with `Target.attachToTarget` and `flatten: true`, enable
  `Network` on that session, and navigate last. Navigating last also puts the cold load inside
  the window.
- **Fetch bodies on `Network.loadingFinished`**, never on `responseReceived`. The body is only
  stored by then.
- **Three `getResponseBody` errors mean three things.** "No resource with given identifier" is
  an unknown request id, "evicted from inspector cache" is buffer overflow, "No data found" is a
  request with no retained body. Log against the request id, do not raise.
- **`Request.postData` can be absent while `hasPostData` is true.** Call
  `Network.getRequestPostData` for every candidate.
- **Only `requestWillBeSentExtraInfo` carries the wire headers**, `Cookie` included. Join it to
  `requestWillBeSent` by request id in both directions, the order is not guaranteed.
- **Bound every CDP call.** A reply from a detached session never arrives.
- **A browser with no page target fails to attach** with a message about download behaviour or
  browser contexts. Open a tab first.
- **A fresh tab and a warmed page send different bodies** for the same operation. Compare field
  names before calling anything truncated.

Etiquette: close only targets this process created, disconnect rather than close the browser,
no `Fetch` domain on a passive capture (it can wedge the page and disables the cache), attach
for the shortest window the goal needs, since `Runtime.enable` is a detection surface.

## Websockets and server-sent events

CDP sees `webSocketFrameSent` and `webSocketFrameReceived` with opcode and payload. Reading a
frame is not decoding it. Binary MQTT, protobuf or compressed dialects stay "readable, not
decoded" in the finding until someone decodes them. `EventSource` traffic shows up as
`eventSourceMessageReceived`.

## Noise

Filter before reading candidates. Generic sources that are almost never the answer:

| Pattern | What it is |
|---|---|
| `/collect`, `/g/collect`, `google-analytics`, `googletagmanager` | Google Analytics and GTM |
| `/track`, `/t`, `/i`, `/batch`, `/v1/m`, `/e` on analytics hosts | Segment, Mixpanel, Amplitude, PostHog |
| `sentry.io`, `/envelope/`, `/api/<n>/store/` | Sentry |
| `datadoghq`, `/rum`, `browser-intake` | Datadog RUM |
| `hotjar`, `fullstory`, `clarity.ms`, `/rs/`, `/rec/` | Session replay |
| `doubleclick`, `facebook.com/tr`, `bat.bing.com`, `ads` | Ad pixels |
| `logging`, `telemetry`, `beacon`, `sendBeacon` calls | First-party telemetry |
| `.js`, `.css`, `.woff2`, images, `manifest.json` | Static assets |
| `/__nextjs_original-stack-frame`, `/_next/static/`, `/sockjs-node` | Dev and build artefacts |
| `chrome-extension://` | The user's other browser extensions, seen by `list_network_requests` |
| `/_private/browser/rum` (its URL carries a key; never copy it) | GitHub Datadog RUM |
| `/notifications/indicator`, `/github-copilot/chat`, `/in-product-messaging/` | GitHub shell polling and banners |

Each site adds its own rows as `noise` patterns in its knowledge base. A source that survives
the filter and proves irrelevant twice gets one.
