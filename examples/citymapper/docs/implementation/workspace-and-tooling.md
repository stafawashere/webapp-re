# Workspace and tooling

Files written in stage 1 and how to rerun them. All paths are relative to `apps/citymapper`.

## Scope tools

| File | What it does | Rerun |
|---|---|---|
| `tools/scope/capture_batch.sh` | Reads `<label> <url>` lines and runs one `cdp_capture.py` window per line with a 7 s pause (`PAUSE_SECONDS`, `WINDOW_SECONDS` override) and a filter for `/api/`, `/geocode` and site pages | `tools/scope/capture_batch.sh run-2026-10-10-082844 research/captures-batch1.txt > var/captures/batch-logs/<name>.log 2>&1` in the background; needs the CDP Brave on port 9222 |
| `tools/scope/summarize_capture.py` | Prints each captured call: method, status, path, query, header names, body, response headers, response shape (maps keyed by ids collapse to `{id}`) | `python3 tools/scope/summarize_capture.py var/captures/<file>.jsonl --match /api/ --depth 5` |
| `tools/scope/scope_data.py` | All scope facts as Python data (site, pages, capabilities, endpoints, entities, auth, pagination, caveats, open questions) | edit, then build |
| `tools/scope/build_scope.py` | Writes `scope/scope.json` and `scope/scope.md` | `cd tools/scope && python3 build_scope.py` |
| `tools/scope/record_findings.py` | Records each non-noise endpoint as a KB finding with status hypothesis; skips existing findings so verified ones are never reset | `cd tools/scope && python3 record_findings.py <run-id>` |
| `tools/capture_sink.py` | Loopback sink for page captures; unused ([L3](../debugging/failures-and-lessons.md#l3-localhost-sink-hung)) | none |

Check: `uv run --script plugin/scripts/check_scope.py scope/scope.json`.

## Plan tool

`tools/plan/build_plan.py` holds every command (name, purpose, kind, capabilities, input and output
JSON schemas, dependencies with the current KB finding state, request cost, open steps, live policy,
tier, confirmation rule) and the not-planned list. It reads `scope/scope.json` and
`knowledge/endpoints/*.md` (status and verify_count), refuses to write if a scope capability has no
command and no reason, and writes `plan/plan.json` and `plan/plan.md`. Rerun after any KB verify so
dependency states are current: `python3 tools/plan/build_plan.py`, then
`uv run --script plugin/scripts/check_plan.py .`.

## Research files

| File | Content |
|---|---|
| `research/bundle/bundle.js`, `landing.js`, `en.json` | Bundles and UI strings as downloaded 2026-10-10 (hash `45b8a6a14381cc356acc`) |
| `research/bundle/api-methods.txt` | First rough extraction of call-site contexts |
| `research/bundle/api-inventory.json`, `.md` | Subagent's inventory: 68 entries with evidence, router, auth, region handling |
| `research/regions.json` | 115 regions and 252 cities from the page HTML |
| `research/region-us-nyc.json`, `research/region-uk-london.json` | Full region config objects |
| `research/cap-directions-nyc.txt`, `research/cap-batch1-a.txt` | Capture summaries |
| `research/captures-batch1.txt` to `captures-batch3.txt` | URL lists for the capture batches |

## Captures

`var/captures/run-2026-10-10-082844-<label>.jsonl`, one per page load: `directions-nyc`, `city-nyc`,
`nearby-nyc-subway`, `nearby-nyc-bus`, `nearby-nyc-bike`, `line-nyc-subway-6`, `status-nyc`,
`cities`, `city-london`, `stop-nyc-subway`, `stop-nyc-bus`, `nearby-nyc-rail`, `nearby-nyc-ferry`,
`directions-london`, `city-paris`, `nearby-paris-metro`, `meet`, `home`, `stop-nyc-rail`,
`stop-nyc-ferry`, `stop-nyc-bike`, `line-london-bakerloo`, `stop-paris-metro`,
`directions-paris-depart`, `news`. Each record has `url`, `method`, `status`, `request_headers`,
`wire_headers` (cookie values redacted), `post_data`, `response_headers`, `response_body`. These are
the fixtures source for stage 3.

## Knowledge base

`knowledge/endpoints/<endpoint id>.md` (65), `knowledge/patterns/` (7), `knowledge/sessions.md`
(ledger), `knowledge/CHANGELOG.md`, `knowledge/INDEX.md` (generated). Commands go through
`uv run --script plugin/scripts/kb.py <command> --root .`.

## Browser state left running

The second Brave instance (`--user-data-dir=$HOME/.webapp-re-profile`, port 9222) is still open for
later stages. Your own Brave tab group from this run was closed.

## Engineer tools

| File | What it does | Rerun |
|---|---|---|
| `tools/engineer/replay.py` | Replays each planned endpoint once from httpx with no cookies, paced 3.5 s x 1.2 to 1.4; `--round 2` runs the corrected inputs; stops on a 429 or challenge | `uv run --script tools/engineer/replay.py [--round 2]` in the background |
| `tools/engineer/kb_verify_replays.py` | Records replay results as `kb.py verify`, skipping `INPUT_MISTAKES` and marking `RETIRED` endpoints | `python3 tools/engineer/kb_verify_replays.py <run-id> <replay logs>` |
| `tools/engineer/kb_verify_live.py` | Credits each passing live-check command's primary finding | `python3 tools/engineer/kb_verify_live.py <run-id> var/logs/verify-*.json` |
| `tools/engineer/pending_approvals.py` | Dry-runs every write and writes `PENDING-APPROVALS.md`; updates readiness for writes | `python3 tools/engineer/pending_approvals.py` |
| `tools/engineer/render_openapi.py` | Writes `openapi/citymapper.openapi.yaml` from the KB and `endpoints.py` | `uv run --with pyyaml python tools/engineer/render_openapi.py` |
| `tools/engineer/render_skill.py` | Writes `plugin/skills/citymapper/SKILL.md` from the plan and readiness, keeping any menu section | `python3 tools/engineer/render_skill.py` |

The program itself, its gates and readiness are in [program.md](program.md). Replay captures are
`var/captures/replay-2026-10-10-085509.jsonl` and `replay-2026-10-10-090058.jsonl`; live-check logs
are `var/logs/verify-*.json`; the program's request log is `var/logs/requests-<date>.jsonl`
(method, template, status, time; no values).

## Menu

| File | What it does |
|---|---|
| `menu/hints.json` | Groups, labels, pickers and example values for the `/citymapper menu` widget |
| `tools/menu/export_regions.py` | Writes `var/public/regions.json` from the catalogue cache for the city datalist; `python3 tools/menu/export_regions.py` |
| `var/menu/` | The builder's cached page, fingerprints and server port (written by `build_menu.py`) |

`uv run --script plugin/menu/build_menu.py check --site citymapper` checks the
hints; `build` serves the page. The menu sends nothing to citymapper.com.
