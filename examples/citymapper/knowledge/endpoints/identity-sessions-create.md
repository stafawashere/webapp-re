---
id: identity-sessions-create
goal: Sign up or log in
method: POST
url: https://citymapper.com/api/1/identity/sessions
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

Sign up or log in

## Request

```
POST https://citymapper.com/api/1/identity/sessions
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

auth_provider, email, password, access_token, source_page, has_seen_marketing_opt_out, has_opted_out_of_marketing, is_interested_in_pass

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
   "url": "https://citymapper.com/api/1/identity/sessions",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
