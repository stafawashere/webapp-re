# Knowledge base

Written for the next session, which has none of this one's context. Write URLs in full, name the
run, date every claim.

## Four stores, four jobs

| Store | Answers | Written by |
|---|---|---|
| `knowledge/endpoints/` | What the call is | `kb.py record-finding`, `kb.py verify` |
| `knowledge/patterns/` | What not to do again, what worked | `kb.py record-pattern` |
| `toolkit/js/` | How the call was found | by hand, once a script ran twice |
| `knowledge/sessions.md` | Why the run went the way it did | `kb.py close-run` |

Mixing them is the failure mode. Endpoint files carry conclusions, the ledger carries reasoning.

## Request contract

Front matter, written and maintained by `kb.py`:

| Field | Meaning |
|---|---|
| `id` | Slug from the goal. Stable across runs. |
| `goal` | The user's goal in their own words. |
| `method`, `url` | Observed. Full URL, query string included, ids replaced by `{name}` only when the shape is known. |
| `surface` | `rest`, `graphql`, `rpc`, `websocket`, `sse`, `html`, `unknown`. `record-finding --surface` also takes `api`, `json` and `http` as `rest`, `gql` as `graphql` and `ws` as `websocket`. |
| `operation` | GraphQL operation name, RPC method, or empty. |
| `operation_id` | Persisted query hash or doc id. Rotates. |
| `status` | `hypothesis`, `verified`, `stale`, `dead`. |
| `required_headers`, `required_cookies` | Names only, from ablation when done. |
| `first_seen`, `last_seen`, `last_verified` | Dates. |
| `verify_count`, `fail_count` | Replay tally. |
| `runs` | Run ids that touched it. |

Body sections: Goal, Request, Headers and where each value comes from, Cookies, Request body
(field names and value shapes), Response trimmed to what answers the goal, Success signal,
Failure signals, Notes (what distinguished it from rejected candidates), Replay template (one
fenced json block with method, url, headers by name, body template), Verification history
(append only).

## Status ladder

```
hypothesis  contract written, never replayed
verified    replayed and passed; verify_count >= 2 is the bar for building on it
stale       replayed and failed; needs re-derivation, and the failure body says where to start
dead        removed upstream; kept as history, never deleted
```

`record-finding` refuses `--status verified`. Only `verify` promotes. A changed URL or operation id
resets the tallies, because it is a different contract.

## Redaction

Names yes, values no. Cookie values, bearer tokens, CSRF values, session ids, auth headers, and
anything the user typed or received from other people (messages, captions, other users' names)
never reach `knowledge/`, `toolkit/`, `var/logs/`, or the reply. Record `len=42` instead.

Capture files under `var/captures/` may keep response bodies, because later runs re-read them,
but credential values are redacted at the writer and nothing from a body is copied out. The one
exception is the file `reverse-export.js` writes for `replay.py`: it holds the live request,
headers included, so `replay.py --consume` deletes it after the replay.

Every `kb.py` command that takes `--site` reads `KB_SITE` (and `KB_SLUG` for the slug) from the
environment when the flag is left out, so a run can export them once.

`kb.py scan-secrets` looks for cookie assignments, bearer tokens, JWTs and long high-entropy
values under `knowledge/`, `toolkit/` and `var/logs/`, and `close-run` refuses to close while it
finds one.

## What counts as growth

| Artifact | Grows when |
|---|---|
| A finding | A new goal gets a contract, or a contract gets a replay result |
| A pattern | A dead end, noise source or quirk cost time and would cost it again |
| A toolkit script | A page script answered something a later run will ask again |
| The ledger | A run closed, even with a partial answer |

Not growth: restating the goal in a new file, an unreplayed hypothesis presented as an answer, a
pattern whose action is "be careful", hand edits to `INDEX.md`.

A pattern seen three times is a candidate for promotion into the site skill's references.

## End-of-run audit

Answer briefly in the reply: which findings changed and to what status, which patterns were added
or bumped, which scripts were saved, whether `close-run` ran, what is still unknown, whether any
finding is now ready to build on (verified twice), and how many live requests the run cost.
