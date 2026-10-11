# Documentation

Durable project knowledge for the Citymapper reverse-engineering workspace. Start here, then follow
the links. The workspace layout is in the top-level [README](../README.md).

## Status on 2026-10-10

| Stage | State | Evidence |
|---|---|---|
| 1 scope | done | `check_scope.py`: `scope: 18 pages, 53 capabilities, 68 endpoints, 24 entities, 14 caveats, 6 open_questions; 0 problems`; `kb.py stats`: `findings: 65 (65 hypothesis)`; `kb.py close-run --run run-2026-10-10-082844` wrote the ledger (live requests recorded as 260, an estimate that counts each page load's own XHRs) |
| 2 plan | done | `check_plan.py`: `plan: 57 commands, 8 build steps, 58 open steps, budget 116 requests; 0 problems`; 3 capabilities not planned with reasons |
| 3 engineer | done | `pytest`: `372 passed in 0.56s`; provenance `provenance violations: 0` (3 of 3 controls caught); live check `32 of 33` then `4 of 4` twice; readiness 29 verified live, 3 awaiting approval, 2 local, 23 blocked; `check_plan.py`: `plan: 57 commands, 8 build steps, 22 open steps, budget 44 requests; 0 problems`; KB `findings: 65 (4 dead, 26 hypothesis, 35 verified)` |
| 4 optimize audit | done | `findings.json: 38 findings (34 confirmed, 1 plausible, 3 refuted); 0 problems`; [report](../optimize/run-2026-10-10-092702/report.md) |
| 5 optimize apply | done | 35 findings fixed; `502 passed in 1.12s`; provenance 0 violations; live `32 of 33` then `1 of 1` after the redirect fix; [result](../optimize/run-2026-10-10-092702/result.md) |
| 6 integrate-menu | done | `build_menu.py check`: `31 ready, 29 verified live, 2 unverified, 24 blocked, 0 planned, 35/65 endpoints verified`, no warnings; section installed; menu shown |

Stage 1 in one paragraph: the walk ran signed out, because you have no Citymapper session in your
browser (`GET /api/1/identity/user_data` answers 403). Navigation, the DOM and request URLs came from
Claude in Chrome in your Brave. Response bodies came from the skill's CDP driver against a separate
Brave instance on a dedicated profile, because the web bundle binds `fetch` at load (the page hook
records nothing) and the extension filters long outputs. A background agent read the 2.7 MB webapp
bundle and the 3.4 MB landing bundle offline and listed 68 API entries. The result: every transit
feature (journeys, search, nearby, stop departures, lines, status, line search) is an unsigned
same-origin JSON call under `/api/<version>/`, scoped by an explicit `region_id`; the list of 115
regions and 252 cities is inlined in every server-rendered page; a web account exists (e-mail magic
link, Google, Facebook) but was not signed into.

## Map

| Topic | Document |
|---|---|
| What the brief asks for and the limits on it | [requirements/requirements-and-constraints.md](requirements/requirements-and-constraints.md) |
| How citymapper.com is built and how a request flows | [architecture/system-overview.md](architecture/system-overview.md) |
| Each feature traced from page to endpoint to response | [architecture/feature-flows.md](architecture/feature-flows.md) |
| The planned program: command tiers, city and place inputs, writes | [architecture/program-design.md](architecture/program-design.md) |
| How stage 1 gathered facts and how far to trust each source | [research/methodology.md](research/methodology.md) |
| Endpoint, region and response-shape findings | [research/findings.md](research/findings.md) |
| Decisions and their reasons | [decisions/decisions.md](decisions/decisions.md) |
| What failed and what replaced it | [debugging/failures-and-lessons.md](debugging/failures-and-lessons.md) |
| Workspace files, scope, plan and engineer tools | [implementation/workspace-and-tooling.md](implementation/workspace-and-tooling.md) |
| The built program: modules, errors, writes, gates, readiness | [implementation/program.md](implementation/program.md) |
| Risks, blockers and open questions | [knowledge/risks-and-open-questions.md](knowledge/risks-and-open-questions.md) |
| Terms used across these documents | [knowledge/glossary.md](knowledge/glossary.md) |

The machine-readable sources of truth are [scope/scope.json](../scope/scope.json) (built by
`tools/scope/build_scope.py` from `tools/scope/scope_data.py`), the knowledge base under
[knowledge/](../knowledge/INDEX.md), and the bundle inventory
[research/bundle/api-inventory.json](../research/bundle/api-inventory.json).
