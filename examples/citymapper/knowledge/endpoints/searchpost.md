---
id: searchpost
goal: Plan a transit journey
method: POST
url: https://citymapper.com/api/4/searchpost
surface: rest
operation: 
operation_id: 
status: verified
required_headers: [accept, citymapper-client, citymapper-region, content-type, origin, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 5
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401, run-2026-10-10-113603]
---

## Goal

Plan a transit journey

## Request

```
POST https://citymapper.com/api/4/searchpost
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

query, region_id, location, is_refinement, refinement_data, search_providers, powersearch, partner

## Response, trimmed

{"results[]": "id, name, result_type (heading or item), type (station, place, ...), coords, address, brands, lines, route_icon_names, source, place_details_available, search_providers", "included_search_providers[]": "id, name", "query": "str"}

## Success signal

unknown

## Failure signals

unknown

## Notes

observed live in the 2026-10-10 scope walk. Content-Type application/x-www-form-urlencoded with a JSON body; Citymapper-Client: Web Search; Citymapper-Region: <region_id>.

## Replay template

```json
{
   "method": "POST",
   "url": "https://citymapper.com/api/4/searchpost",
   "headers": [
      "accept",
      "citymapper-client",
      "citymapper-region",
      "content-type",
      "origin",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay search-1: HTTP 200, 9 results items
- 2026-10-10 run-2026-10-10-090401 pass: replay search-2: HTTP 200, 9 results items
- 2026-10-10 run-2026-10-10-090401 pass: replay search-3: HTTP 200, 3 results items
- 2026-10-10 run-2026-10-10-090401 pass: program live check search-places (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check search-places (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
