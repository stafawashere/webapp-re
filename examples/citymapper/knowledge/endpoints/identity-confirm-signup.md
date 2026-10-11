---
id: identity-confirm-signup
goal: Reset a password or confirm an e-mail
method: POST
url: https://citymapper.com/api/1/identity/confirm_sign_up/{token}
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

Reset a password or confirm an e-mail

## Request

```
POST https://citymapper.com/api/1/identity/confirm_sign_up/{token}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

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
   "url": "https://citymapper.com/api/1/identity/confirm_sign_up/{token}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
