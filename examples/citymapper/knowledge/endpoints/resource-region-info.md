---
id: resource-region-info
goal: Get one city's configuration (modes, brands, bounding box, timezone)
method: GET
url: https://citymapper.com/resource/region-info/{region_id}
surface: rest
operation: 
operation_id: 
status: verified
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 3
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401]
---

## Goal

Get one city's configuration (modes, brands, bounding box, timezone)

## Request

```
GET https://citymapper.com/resource/region-info/{region_id}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"$": "region_id, region_name, region_slug, bounding_box, default_place, nearby_modes[], offline_maps[], timezone, region_is_launched, web_enabled, api_enabled, core_brand_ids, default_cycle_brand_id, distance_units, clock, ondemand"}

## Success signal

unknown

## Failure signals

unknown

## Notes

observed live in the 2026-10-10 scope walk. JSON region config; landing.js calls it with the cm_region cookie value.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/resource/region-info/{region_id}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay region-info-1: HTTP 200, keys present
- 2026-10-10 run-2026-10-10-090401 pass: replay region-info-2: HTTP 200, keys present
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-city (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
