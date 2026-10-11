# System overview

How citymapper.com is put together, as observed on 2026-10-10. Facts are from CDP captures and the
browser walk unless marked INFERENCE (from the bundle) or UNRESOLVED.

## Hosts

| Host | Role | Evidence |
|---|---|---|
| `citymapper.com` | Server-rendered pages (Django, some Next.js SSR routes) and the JSON API under `/api/<version>/`, `/geocode`, `/resource/...` | captures |
| `global-api.citymapper.com/resourceproxy/` | City illustrations on `/cities` | captures (noise) |
| `turnstile-api.citymapper.com/web/1/` | Citymapper Pass payment service ("turnstile"), not Cloudflare Turnstile | bundle only, INFERENCE |
| `maps.googleapis.com` | Google Maps JS for the map, with an embedded browser key | page scripts (noise) |

All of `citymapper.com` sits behind Cloudflare (`server: cloudflare`, `cf-ray`, `__cf_bm` cookie). API
responses carry `x-version` (for example `f83ef6f:480`, a backend build id) and `cf-cache-status:
DYNAMIC`. The HTML carried `x-served-by: old` on 2026-10-10.

## Front end

- `/webapp`, `/directions`, city, nearby, stop, line and status pages render a React SPA from
  `/static/components/bundle-<hash>.js` (webpack, minified, no public source map: the `.map` URL
  answers 403 AccessDenied from S3). The bundle keeps `__REACT_HOT_LOADER__.register(..., "/__w/web/web/src/...")`
  strings, which name every module and made the offline inventory possible.
- The home page uses a separate React bundle, `/static/components/landing-<hash>.js`.
- Every server-rendered page sets `window.citymapper.*` globals before the bundle runs: `region`,
  `regions`, `citiesInRegions`, `brands`, `regionId`, `apiUrl` (`/api/`), `frontendProxyDir`
  (`/api/resourceproxy/`), `STACK` (`production`), `cityMeta`, `landingpage`,
  `static_config_localization`. These are the only source of the region catalogue
  ([findings](../research/findings.md#regions-and-cities)).
- The client API class `CitymapperAPI` (`src/api/src/citymapper-api.js`) is built with
  `hostname: ""` and prefix `/api`, so calls are same-origin. Every call uses
  `credentials: "include"` and sets `Content-Type: application/json; charset=utf-8`, even on GET. No
  static headers are added in the browser. INFERENCE from the bundle, consistent with the wire
  headers captured.

## The region model

Every API call is scoped by `region_id` (for example `us-nyc`, `uk-london`, `fr-paris`). The client
takes it from `store.region.region_id`, which the server sets from the URL's `{region_slug}`. On
pages without a slug the server falls back to the `cm_region` cookie (INFERENCE; the city switcher
writes `cm_region` and reloads). The program will always pass `region_id` explicitly, so no cookie
state matters.

A region's config (from `window.citymapper.region` or `GET /resource/region-info/{region_id}`) gives
the program what it needs to form requests: `nearby_modes[]` (mode slug, `mode_id`,
`request_brand_ids`, `kind_ids`), `bounding_box`, `default_place`, `timezone`, `core_brand_ids`,
`distance_units`, and feature flags. Brands (`window.citymapper.brands`) carry `departure_apis`,
which picks the departures endpoint for a stop.

## Request flow per page

```
/{region}                 -> /api/1/identity/user_data (403 signed out), /api/2/message,
                             /api/1/routestatus, /api/2/routeinfo?route_ids=...
/directions?...           -> /api/7/journeys, /api/7/walk (limit 2), /api/6/cycle, /api/2/taxi
                             in parallel, two /api/4/searchpost (names), then
                             POST /api/1/journeytimes every 30 s
/trip/signature?...       -> GET <same url>&meta_only=true (head tags), /api/1/journeytimes;
                             a cold load also POSTs /api/1/refreshjourneys (INFERENCE)
/{region}/{mode}/{type}   -> /api/3/nearby?brand_ids|kinds&mode_id&location&limit=50&extended=1
/{region}/{mode}/{type}/{alias}
                          -> /api/3/stopinfo?ids=<alias>, then the brand's departures API
                             (/api/1/departures, /api/2/metrodepartures or /api/1/raildepartures),
                             and /api/2/nearby (jQuery)
/{region}/{mode}/{line}   -> /api/1/routeinfo?route=<alias>&extended=1
/{region}/status          -> /api/1/routestatus, /api/2/routeinfo?route_ids=...
/                         -> /resource/region-info/{cm_region}, /resource/brand-directory
every page                -> POST /api/2/logevents (analytics, noise)
```

Feature-level detail is in [feature-flows.md](feature-flows.md).

## Auth

Optional. The session is a Django `sessionid` cookie; signed-in state is detected only by
`GET /api/1/identity/user_data` returning 200. Sign-in is e-mail magic link, Google Identity Services
or the Facebook SDK, each posting to `/api/1/identity/sessions` (INFERENCE from the bundle; the
dialog was opened, nothing submitted). Other cookies seen: `csrftoken`, `uid`, `uid_set`,
`cm_region`, `_locale`, `__cf_bm`. Request headers used by the client: `Citymapper-Region`,
`Citymapper-Client` (`Web Search` on search, `Web` on analytics), `User-Device` (from the `uid`
cookie, analytics only). Detail and risks in
[risks-and-open-questions.md](../knowledge/risks-and-open-questions.md#account).

## What is not there

No GraphQL, no websockets or SSE (0 frames in every capture), no service worker, no request
signing or nonce, no captcha or bot challenge observed, no rate-limit headers.
