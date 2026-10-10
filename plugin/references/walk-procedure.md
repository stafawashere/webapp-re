# Walk procedure

## Order

1. **Landing and shell.** Load the signed-in home. Read the accessibility tree with `read_page`
   (filter `interactive`) to list the global navigation, account menu, search, notifications and
   footer links. These are the breadth-first frontier.
2. **Hook.** Inject `capture-hook.js` with `javascript_tool` on every new document. In a single-page
   app one injection survives route changes; after a full navigation, inject again. Confirm with
   the returned `{ installed: true }`.
3. **Breadth.** Visit each frontier entry once. For each page record: URL pattern (ids replaced by
   `{name}`), title, purpose in one line, the controls on it, and the requests it fired.
4. **Depth.** For each section: open one item of every detail type, page through every list
   once (next page, infinite scroll, load more), apply one search, one filter and one sort, open
   every tab and dialog that does not commit anything.
5. **Settings and account.** Read every settings page. Each toggle or field is a capability with
   `mutates: true`, not exercised.
6. **Write paths, observed safely.** For each state-changing control, open it and stop before the
   commit. Many forms reveal their endpoint through validation calls, autosave drafts or bundle
   strings without submitting. Record what is visible; mark the endpoint `unknown` otherwise.

## After every step

- `read_network_requests` for the tab, filtered past the noise list.
- `window.__reCaptureDump({ match: "<api prefix>" })` for request header names, query keys and
  response shapes. Ask for `{ values: true }` only for a specific request whose body shape is
  ambiguous, and never copy values into the scope.
- Note new cookies by name only, through the request headers' names and any `Set-Cookie` names
  visible in response headers.

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

Run these with `javascript_tool`. Each returns names and counts, never values.

```js
({
   next: Boolean(document.getElementById("__NEXT_DATA__")),
   nuxt: Boolean(window.__NUXT__),
   apollo: Boolean(window.__APOLLO_CLIENT__),
   reactRoot: Boolean(document.querySelector("[data-reactroot], #root, #__next")),
   webpackChunks: Object.keys(window).filter((key) => key.startsWith("webpackChunk")),
   serviceWorker: Boolean(navigator.serviceWorker && navigator.serviceWorker.controller),
   csrfMeta: Array.from(document.querySelectorAll("meta")).map((meta) => meta.name).filter((name) => /csrf|xsrf|token/i.test(name)),
   scripts: performance.getEntriesByType("resource").filter((entry) => entry.initiatorType === "script").length,
   sockets: performance.getEntriesByType("resource").filter((entry) => /^wss?:/.test(entry.name)).length,
   innerWidth: window.innerWidth,
})
```

## Stopping

Stop and ask the user when: a login wall or challenge appears, a page needs an action that would
change state to go further, the walk passes 150 pages, or the site shows a rate-limit warning.
