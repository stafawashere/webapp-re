# Identify and ablate

## The three ladders

Cheapest first. Do not skip to the expensive one.

**Capture.** Read the candidate table, then the bodies. The right call is the one whose response
carries the state that just changed, or a success envelope naming the feature. Record every
rejected candidate in the run notes with the reason. A rejected candidate that keeps coming back
is a `noise` pattern.

**Framework state.** Name an operation without firing it. What to look for:

| Stack | Where operations live |
|---|---|
| React | `__reactFiber$*` / `__reactProps$*` keys on DOM nodes. Walk `fiber.return`, read `memoizedProps` and `memoizedState`. |
| Relay | Compiled artifacts carry `params.id` or `params.cacheID`, `params.name`, `operationKind`, argument names, root field. |
| Apollo | `window.__APOLLO_CLIENT__.cache.extract()`, `queryManager.queries`, persisted query hashes in `extensions.persistedQuery.sha256Hash`. |
| Next.js | `__NEXT_DATA__` script, `/_next/data/<build>/<route>.json`, server actions posting `Next-Action` headers. |
| Nuxt, Remix, SvelteKit | `__NUXT__`, `__remixContext`, `__sveltekit_*` inline payloads. |
| Redux, Zustand, MobX | Store on `window` or reachable from a provider fiber. |

A toolkit script that reads one of these and returns names, ids and argument lists is worth
saving the first time it works.

**Bundle.** Search the loaded scripts for the feature's vocabulary: the visible label, the route,
an operation name, a root field. Over CDP, `Debugger.searchInContent` runs inside V8 against
every parsed script with nothing refetched. Through the extension, fetch each script URL from
`performance.getEntriesByType("resource")` with `cache: "force-cache"` and search the text in the
page. Load the feature's UI first, because lazy chunks only exist after they load.

## Identification bar

One observation is a guess. Two matching observations with different inputs, or one observation
plus a passing replay, is an identification.

## Ablation

The browser sends far more than the server checks. Ablation finds the minimum, which is what the
program should send and what the finding should call required. It also tells you which values
need a bootstrap step.

Procedure, one read endpoint at a time, in the page context or from the program with adopted
cookies:

1. Replay the full observed request. It must pass. If not, the replay is wrong, stop here.
2. Remove one header. Replay. Record pass or fail and the failure body.
3. Restore it, move to the next. Same for each cookie, each body field, each query parameter.
4. Remove every element marked optional at once. Replay. It must still pass, which catches
   pairs where either one suffices.
5. For each required element, record where its value comes from: a cookie, a meta tag, an inline
   bootstrap JSON, a previous response, a constant in a bundle, a computed signature.

Budget it. Thirty-eight elements is thirty-nine requests. Pace them at the site's measured safe
rate or slower, see [pacing-and-safety.md](pacing-and-safety.md). Never ablate a write. Ablate
the read that shares its headers, and assume the write needs at least the same.

Record the result in the finding as two lists, `required` and `ignored`, with the date. It is
common for only one to three of roughly forty headers and fields sent to be validated: most of
what a browser sends is not checked.

## Values computed by client code

If an element is required and its value is not a cookie, a constant or a previous response, it
is computed. Signs: changes on every request, length fixed and hex or base64, named `sign`,
`signature`, `x-s`, `x-t`, `nonce`, `_token`, `bogus`, `acw`, `__zp`. Load the **js-reverse**
skill: set an XHR breakpoint on the URL fragment, read the call stack at the pause, find the
function that writes the field, and rebuild it in Node or Python from page evidence only.
