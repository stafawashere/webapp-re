---
id: turnstile-userinfo
goal: Manage Citymapper Pass payment methods
method: POST
url: https://turnstile-api.citymapper.com/web/1/userinfo
surface: rest
operation: 
operation_id: 
status: hypothesis
required_headers: [user-device, session-id, content-type]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 
verify_count: 0
fail_count: 0
runs: [run-2026-10-10-082844]
---

## Goal

Manage Citymapper Pass payment methods

## Request

```
POST https://turnstile-api.citymapper.com/web/1/userinfo
```

## Headers that matter

Names in front matter. Where each value comes from (bundle, INFERENCE, not verified): the web bundle sets `Session-Id`
from the `sessionid` cookie and `User-Device` from the `uid` cookie. Scope records Pass as out of
reach without the app and an account, so whether a web `sessionid` is accepted here is a
hypothesis. The program sends it only with the explicit `--use-web-session-id` opt-in and never
forwards the citymapper.com cookie jar to this host (optimize run-2026-10-10-092702, F19).

## Cookies that gate it

unknown

## Request body

payment_provider_id

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
   "url": "https://turnstile-api.citymapper.com/web/1/userinfo",
   "headers": [
      "user-device",
      "session-id",
      "content-type"
   ],
   "body": null
}
```

## Verification history
