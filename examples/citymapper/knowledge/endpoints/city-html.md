---
id: city-html
goal: List every supported city and region
method: GET
url: https://citymapper.com/{region_slug}
surface: html
operation: 
operation_id: 
status: verified
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 2
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401]
---

## Goal

List every supported city and region

## Request

```
GET https://citymapper.com/{region_slug}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"window.citymapper.region": "region_id, region_name, region_slug, bounding_box, default_place, nearby_modes[], timezone, core_brand_ids, distance_units, feature flags", "window.citymapper.regions": "[[region, distance_km]] x115", "window.citymapper.citiesInRegions": "{city_slug: {city_name, city_id, region_id, default_place, show_in_city_switcher}} x252", "window.citymapper.brands": "{brand_id: {..., departure_apis}}", "window.citymapper.apiUrl": "/api/"}

## Success signal

unknown

## Failure signals

unknown

## Notes

observed live in the 2026-10-10 scope walk. 2 MB to 15 MB of HTML; the one source of the region list.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/{region_slug}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay city-html-1: HTTP 200, marker found
- 2026-10-10 run-2026-10-10-090401 pass: replay city-html-2: HTTP 200, marker found
