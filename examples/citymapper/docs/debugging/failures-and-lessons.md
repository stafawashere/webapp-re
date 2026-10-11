# Failures and lessons

## L1. The page capture hook records nothing

Attempt: inject `assets/capture-hook.js` (wraps `window.fetch` and `XMLHttpRequest`) on `/webapp`,
then type in the Start box.
Result: `__reCaptureDump()` returned `[]` although `read_network_requests` listed
`POST /api/4/searchpost`.
Root cause (INFERENCE, consistent with the bundle's `http.js`): the bundle's fetch polyfill keeps a
reference to the original `fetch` taken at module load, so a later wrapper is never called.
Workaround tried: patch `Response.prototype.json` and `.text`, which every response passes through.
That captured bodies.
Lesson: on citymapper.com use the CDP driver for bodies (KB pattern `technique-cdp-for-bodies`).

## L2. Extension output filter

Returning captured bodies through `javascript_tool` cut off after about 1,500 characters with
`[TRUNCATED]`, and a 6,000-character test string came back as `[BLOCKED: Base64 encoded data]`.
Lesson: the extension is fine for short structured probes, not for bodies.

## L3. Localhost sink hung

Attempt: `tools/capture_sink.py` on `127.0.0.1:8765` with CORS and
`Access-Control-Allow-Private-Network`, and an in-page `fetch` POST to it.
Result: `Runtime.evaluate timed out after 45000ms`; the sink received nothing.
Root cause (INFERENCE): Brave held the request behind its local-network access permission prompt,
which is a browser permission I did not grant.
Status: the sink script remains in `tools/` unused. Do not retry without your permission for that
prompt.

## L4. `open -na "Google Chrome"` failed

`Unable to find application named 'Google Chrome'`. Your browser with the Claude extension is Brave
(`/Applications/Brave Browser.app`). CDP works the same on Brave 152.

## L5. close-run refused on batch console logs

Covered in [D6](../decisions/decisions.md#d6-capture-console-logs-live-under-varcapturesbatch-logs).

## L6. A background run started with `&` is not tracked

Batch 2 was first started with a trailing `&` inside a foreground call, so no completion notice
would arrive. It was killed after one page and restarted with `run_in_background`.

## L7. Typing before the page is ready

Typing into Start immediately after navigation was lost (the box was empty); clicking the field again
after load worked. The "Find a bus or line" box ignored a `ref` click and needed a coordinate click.

## L8. Journey click selects first, opens second

The first click on a result row highlights the route on the map; a second click opens
`/trip/signature?...`.

## L9. Replay failures that were my inputs

Seven of the round 1 replay failures were wrong inputs, not endpoint failures: a station id sent to
`placeresolve`, `walk1` checked for `journeys` instead of `routes`, `trip-meta` without its html
flag, `nearby2` without `brand_ids` (answers 500), a wrong NY Penn id, `everythingmap` with
`size=500` (400 "Unknown tile size"; only `small` and `large`). Fixed in round 2;
`tools/engineer/kb_verify_replays.py` lists them in `INPUT_MISTAKES` so they are not recorded against
the endpoints. Lesson: read the bundle's call site for every parameter before a replay.

## L10. Provenance regex missed digits in names

The first gate missed `WALK_V1` and `NEARBY_V2` because the name pattern had no digits. Found when
the positive control planted a defect it did not catch. Fixed the regex; `ORIGIN` moved to
`endpoints.py` as a host constant.

## L11. `get-journey-times` ContractBroken

One `journeytimes` entry lacked `time` in the full live check. See
[D13](../decisions/decisions.md#d13-get-journey-times-time-is-nullable).

## L12. `whoami` sent nothing when signed out

It returned signed out from the missing cookie without asking the site, so the live check counted 0
requests and could not credit the finding. It now always calls `identity/user_data` and maps
`SessionExpired` to `signed_in: false`.

## L13. Four source bugs found by the offline tests

The test agent wrote tests from the plan's schemas and the site facts and reported four suspected
bugs. All four were real and fixed in `src`, and each fix was broken and restored to watch its test
go red (`6 failed` then `16 passed`; `1 failed` then `2 passed`; `1 failed` then `1 passed`;
`1 failed` then `4 passed`).

1. `Request.describe()` returned `body: null` for bodyless writes; the dry-run schema says object.
   Six strict xfails covered it and were removed once they XPASSed. Fix: `{}`.
2. The bus parser ignored `services[].next_departures`, so London bus stops showed only
   `no live times`. Fix: timetabled rows with `time`.
3. Departures sorted by whether `seconds_away` exists, not by `is_live`. Fix: `departure_order`.
4. `add_favourite` read `stop["kind"]`, which `stopinfo` does not have, so every bus stop became a
   station (`target_type` 2). Fix: derive from `departure_api`.

## L14. Checker argument forms

`check_scope.py` takes the file (`scope/scope.json`), `check_plan.py` takes the site root (`.`).
Passing the other form fails with a usage line or `IsADirectoryError`.

## L15. A security fix broke a public read

F16 refused every cross-host redirect. Offline tests could not see that `/api/1/resources`
redirects off citymapper.com; only the live check did (`get-legal` exit 14). Lesson: after a
transport change, run the full live check before calling the change done. Fix in
[D20](../decisions/decisions.md#d20-cross-host-redirects-only-without-credentials).

## L16. Phase 1 `uv run` wrote bytecode into the program

The phase 1 live baseline ran the CLI without `PYTHONDONTWRITEBYTECODE=1`, which left 90
`__pycache__` files, the only change outside the run directory. Set the variable for every
program call in a read-only phase.

## L17. An agent run left files under `program/var/`

During wave 1 something ran the live check with a root of `program/` and zero runs, leaving an
empty verify log and a two-entry readiness file at 09:46. No request was sent. Removed; the test
suite does not recreate them.

## L18. Large workflow arguments

The apply wave arguments were 48 KB. Instead of pasting them, a generated wrapper script in the
scratchpad embedded them and called `optimize-apply.js` through `workflow({scriptPath})`.
