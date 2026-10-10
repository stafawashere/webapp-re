# Failure classification

## Body first

HTTP status is the transport's opinion. The application's opinion is in the body, and on many
private APIs every failure arrives as 200. A client that branches on status alone ships silent
degradation: an empty list, a null root, a login page parsed as zero results.

Classify every response in this order:

1. **Transport.** Connection error, timeout, TLS failure. Retryable with backoff.
2. **Content type.** Expected JSON and got HTML: a login page, a challenge page, a maintenance
   page, or a CDN block. Look for the login form action, a challenge script, `cf-chl`, `_abck`,
   `px-captcha`, `datadome`. Never parse it as data.
3. **Error envelope.** `errors[]` (GraphQL), `error`, `status: "fail"`, `success: false`,
   `ok: false`, `message` with a code, `code != 0`. The field and the values belong in the
   finding.
4. **Null or empty where data is expected.** A null root field under 200 can mean wrong path,
   wrong operation id, rotated persisted query, or no permission. It is never "no results"
   until a replay with known-non-empty input says so.
5. **Status code**, last, for what the body did not settle: 401 and 403 are auth or a missing
   token header, 404 is a wrong shape or a removed endpoint, 429 is rate limiting.

Each class maps to one exception type in the generated program, so a caller can tell "signed
out" from "throttled" from "the endpoint changed" without reading text.

| Class | Program exception | Retry |
|---|---|---|
| transport | `TransportError` | yes, bounded, with backoff |
| signed out, login page | `SessionExpired` | no, ask the user to refresh cookies |
| challenge, captcha, checkpoint | `ChallengeRequired` | never |
| rate limited | `RateLimited` | not automatically, surface it |
| error envelope, known code | `ApiError` with the code | no |
| null root, shape changed | `ContractBroken` | no, rerun discovery |
| permission | `NotPermitted` | no |

## Symptom table

| Symptom | Likely cause | Next move |
|---|---|---|
| No request after the UI action | Client-only state, a websocket frame, or a request fired on load | Check frames, then confirm the load is inside the window |
| Fifty candidates, none obviously right | Filter too wide, window held several actions | One action per window, default filter |
| Endpoint found, response opaque | Persisted query, field names absent | Search bundles for the operation name |
| 403 on replay, 200 in the browser | A token header is missing | Re-read the live wire headers. Never guess a value. |
| 200, error envelope | The normal failure shape | Record the field and value in the finding |
| 200, null root, no error | Wrong path or operation id | Compare URL and id with the finding exactly |
| A stored contract stops passing | Operation id or build hash rotated | Mark stale, rediscover |
| HTML where JSON was expected | Signed out or challenged | Stop, ask the user |
| 429 or challenge page | Rate limited or flagged | Stop now, tell the user, no retry |
| Feature missing from the DOM | Narrow viewport layout | Check `window.innerWidth`, ask the user to widen |
| Works in a warmed page, fails fresh | A bootstrap token from the document is needed | Find it in the HTML or inline JSON, record its source |

Every row that fires is also a `kb.py record-pattern` call, so the specific instance is kept.
Every one of them ends in a recorded fact or an explicit "unknown", never in a guess presented as
a finding.
