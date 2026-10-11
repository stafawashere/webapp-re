# Citymapper example

This is everything webapp-re produced for citymapper.com in one run on 2026-10-10. It's here so you
can see what each stage writes before pointing the plugin at a site of your own, and because the
result is useful on its own. The program is a Python CLI for journeys, live departures and line
status in any of Citymapper's 115 regions, and the `/citymapper` plugin lets Claude Code call it.

The whole run was done signed out of Citymapper, so nothing in this folder came from an account.
[HOW-IT-WAS-BUILT.md](HOW-IT-WAS-BUILT.md) walks through each stage, the command behind it and what
it left on disk.

## Running the program

You need [uv](https://docs.astral.sh/uv/). From the repo root:

```bash
cd examples/citymapper/program
uv run citymapper help
uv run citymapper plan-journey --city nyc --from "Times Square" --to "Brooklyn Bridge"
uv run citymapper --format table get-line-status --city london
uv run citymapper find-nearby --city paris --near "Chatelet" --mode metro
```

Every command prints JSON unless you put `--format table` before the command name. `--city` takes
a slug (`nyc`), a region id (`us-nyc`) or a city name, and places can be text or `lat,lng`. The
program waits at least 3 seconds between requests and stops on a 429 or a challenge page, so a
journey with place lookups takes a few seconds.

## Using it from Claude Code

Load the site plugin straight from your clone:

```bash
claude --plugin-dir examples/citymapper/plugin
```

Then ask in plain words ("when's the next 6 train from Astor Place", "is the Bakerloo line running")
or run `/citymapper:citymapper help` for the command list. `/citymapper:menu` opens a menu of every
command with its fields, and it needs the webapp-re plugin's `plugin/menu/` folder from this repo,
which the clone already has.

## What works and what doesn't

The plan has 57 commands, 40 reads and 17 writes. 29 of them were checked against the live site and
2 only run locally (`help` and `adopt-session`). The other 26 are built and tested offline, but
weren't checked live, for these reasons:

| Waiting on | Commands |
|---|---|
| Your own Citymapper session | 12, such as saved places, favourites and profile edits |
| Your approval, because they create public links | `share-journey`, `create-go-link` |
| A Citymapper Pass session that only the app holds | 6 Pass and payment commands |
| Nothing, Citymapper retired the endpoints | `plan-vehicle-hire`, `get-shared-eta`, `get-weather`, `get-transit-score` |
| A shared link to open | `open-trip-link`, `open-go-link` |

For the account commands you sign in on citymapper.com yourself and pipe your Cookie header into
`uv run citymapper adopt-session --stdin`. The program keeps it in a local `.env` with mode 600. Any
command that changes data prints a dry run first and only sends with `--yes --confirm <value>` from
that dry run. Writes that were built but never sent are listed in
[PENDING-APPROVALS.md](PENDING-APPROVALS.md).

10 of the program's 502 tests fail right now, all in `program/tests/test_writes.py`, because
`save-place` sends a `geocode` request the tests don't expect. Live data also changes under the
program, so a command that passed on 2026-10-10 can break when Citymapper changes a response.

## What's in the folder

| Path | Holds |
|---|---|
| `scope/` | Every page, capability and endpoint the read-only walk found |
| `plan/` | The commands, their inputs and outputs, and the build order |
| `knowledge/` | One Markdown note per endpoint with how many times it was verified, plus noise and quirk patterns |
| `openapi/` | An OpenAPI spec rendered from the verified endpoints |
| `program/` | The Python client and CLI, with its tests |
| `plugin/` | The generated `/citymapper` plugin |
| `menu/` | Hints for the command menu |
| `optimize/` | The audit: every finding, its verdict, what was fixed and the numbers before and after |
| `research/` | The endpoint inventory pulled from Citymapper's JavaScript, the region list and capture summaries |
| `docs/` | Design notes, decisions and what went wrong along the way |
| `tools/` | Small scripts written during the run |

Citymapper's own JavaScript bundles aren't included. `research/bundle/api-inventory.md` lists what
was pulled from them. This isn't Citymapper's official API and isn't affiliated with Citymapper.
