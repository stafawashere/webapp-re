# Capture

Two browser paths, one rule: capture inside a window that contains exactly one action.

## Choosing a path

| Need | Path |
|---|---|
| The user's real Chrome, real sign-in, no setup | Claude in Chrome |
| Full response bodies for every request, cold load included | CDP driver |
| Real wire headers, including `Cookie` | CDP driver |
| Script search inside V8 without refetching bundles | CDP driver |
| Scope walk across many pages | Claude in Chrome |

A site-specific skill can fix the path for its site.

## Claude in Chrome

Read the `anthropic-skills:chrome-browser` skill first, then load the tools in one ToolSearch
call: `tabs_context_mcp`, `tabs_create_mcp`, `navigate`, `computer`, `read_page`, `find`,
`get_page_text`, `javascript_tool`, `read_network_requests`, `read_console_messages`,
`tabs_close_mcp`. Work in a new tab, never in one of the user's.

What each tool gives:

- `read_network_requests` lists method, URL and status for the tab. It is the endpoint map. It
  does not give bodies.
- `javascript_tool` evaluates in the page. Inject `${CLAUDE_PLUGIN_ROOT}/assets/capture-hook.js` once per document to
  wrap `fetch` and `XMLHttpRequest`; it keeps the last 200 calls in `window.__reCapture` with
  request bodies, response bodies truncated to 64 KB, and request header names. Read it back
  with `window.__reCaptureDump({ match: "/api/" })`, which returns shapes by default and values
  only with `{ values: true }`.
- The hook cannot see the cold load, because it is installed after the document runs. Trigger
  the action after injecting, or reload a single-page app route through its own router.
- `read_page` and `get_page_text` read the DOM without any request to the API.

Cookie values are invisible to `document.cookie` when HttpOnly, which is correct. Never try to
extract them through the extension. Cookie adoption for the program is the user's step.

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

Each site adds its own rows as `noise` patterns in its knowledge base. A source that survives
the filter and proves irrelevant twice gets one.
