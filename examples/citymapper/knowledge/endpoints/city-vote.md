---
id: city-vote
goal: Vote for a new city
method: POST
url: https://citymapper.com/cities/vote_submit/
surface: rest
operation: 
operation_id: 
status: hypothesis
required_headers: [x-csrftoken, content-type]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 
verify_count: 0
fail_count: 0
runs: [run-2026-10-10-082844]
---

## Goal

Vote for a new city

## Request

```
POST https://citymapper.com/cities/vote_submit/
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

city_slug, email

## Response, trimmed

{}

## Success signal

unknown

## Failure signals

unknown

## Notes

read from the bundle only, not observed live.

## Replay template

```json
{
   "method": "POST",
   "url": "https://citymapper.com/cities/vote_submit/",
   "headers": [
      "x-csrftoken",
      "content-type"
   ],
   "body": null
}
```

## Verification history
