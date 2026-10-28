# Methodology

How stage 1 gathered its facts, and how far each source can be trusted.

## Claude in Chrome (your Brave)

- One new tab in a new tab group, closed at the end of the stage. Viewport 1600 wide.
- Used for: navigation, the accessibility tree and DOM (links, controls, the sign-in dialog), and
  `read_network_requests`, which lists method, full URL and status. Query strings in that list are
  complete except values the extension redacts (`brand_ids=REDACTED`, `route=REDACTED`).
- Not usable for bodies: the injected capture hook recorded nothing (the bundle binds `fetch` at
  load), and the extension's output filter truncates long strings and blocks anything that looks like
  base64 or cookie data. See [failures L1 and L2](../debugging/failures-and-lessons.md).
- UI actions taken: typing in the Start box, Arrive with hour 10 then Set, selecting and opening a
  journey, typing `M15` in Find a bus or line and opening the line, picking a Google place, clicking
  the map, opening and closing the sign-in dialog.

## CDP driver on a separate browser

- `~/.claude/skills/webapp-re/scripts/cdp_capture.py` against a second Brave instance started with
  `open -na "Brave Browser" --args --remote-debugging-port=9222 --user-data-dir=$HOME/.webapp-re-profile`.
  Google Chrome is not installed; the user's "Chrome" is Brave. The profile is signed out of
  everything and separate from your browser.
- One capture window per page load: the driver opens `about:blank`, attaches, enables Network,
  navigates, drains for 15 to 20 s, writes every matching request with headers, wire headers and the
  body (credential header values redacted at the writer) to
  `var/captures/run-2026-10-10-082844-<label>.jsonl`, and closes its tab.
- Driven by `tools/scope/capture_batch.sh` with a 7 s pause between page loads; four batches plus
  one single capture (27 page loads). Console logs are in `var/captures/batch-logs/`.
- Trust: these are exact wire facts for a signed-out browser on 2026-10-10.

## Bundle reading (background agent)

- Bundles fetched once with curl: `bundle-45b8a6a14381cc356acc.js` (2,696,410 bytes),
  `landing-45b8a6a14381cc356acc.js` (3,401,500 bytes), `/static/locales/en.json` (50,222 bytes). The
  source map URL answered 403.
- A general-purpose subagent, with no network access to the site, read them and wrote
  `research/bundle/api-inventory.json` (68 entries, each with a verbatim evidence snippet under 300
  characters checked against the bundle) and `api-inventory.md` (router table, auth, region handling,
  signing, landing calls). Trust: INFERENCE. Where a capture exists the two agree (paths, query keys,
  headers, departure API split); 15 entries have no live observation yet.

## Page HTML

The city, stop, line and cities pages embed region data as `window.citymapper.<name> = <json>` lines.
Parsed from the captured HTML into `research/regions.json` (115 regions, 252 cities). The full
region config objects for New York and London were parsed too but are not kept here.

## Summaries

`tools/scope/summarize_capture.py` prints each captured API call as method, status, path, query,
header names, request body, interesting response headers and the response shape (key paths, types,
counts, one short example). Saved output: `research/cap-directions-nyc.txt`.

## What was deliberately not done

No sign-in, no form submission, no share or send-to-phone, no Meet Me Somewhere link creation, no
star (favourite) clicks, no city vote, no use of the official developer API, no request
interception.
