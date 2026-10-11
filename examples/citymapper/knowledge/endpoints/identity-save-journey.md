---
id: identity-save-journey
goal: Send a journey to your phone (save it to the account)
method: POST
url: https://citymapper.com/api/1/identity/documents/SavedJourney
surface: rest
operation: 
operation_id: 
status: hypothesis
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 
verify_count: 0
fail_count: 0
runs: [run-2026-10-10-082844]
---

## Goal

Send a journey to your phone (save it to the account)

## Request

```
POST https://citymapper.com/api/1/identity/documents/SavedJourney
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

document_data

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
   "url": "https://citymapper.com/api/1/identity/documents/SavedJourney",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
