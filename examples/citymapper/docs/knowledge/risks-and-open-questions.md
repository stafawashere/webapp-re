# Risks and open questions

## Account

FACT: a web account exists. The "Sign up or log in" dialog offers e-mail, Facebook and Google; you are
signed out (`identity/user_data` 403). Decision [D2](../decisions/decisions.md#d2-no-sign-in): no
sign-in.

Identity endpoints from the bundle (INFERENCE): `GET /api/1/identity/user_data`;
`POST|DELETE /api/1/identity/sessions`; `POST /api/1/identity/magiclink/create`;
`POST /api/1/identity/update_user`; `GET|POST /api/1/identity/places`,
`PUT|DELETE /api/1/identity/places/{place_id}`; `GET|POST /api/1/identity/favorites`,
`DELETE /api/1/identity/favorites/{id}`; `POST /api/1/identity/documents/SavedJourney`,
`DELETE /api/1/identity/documents/SavedJourney/{document_id}`; password reset and confirm sign-up.

What it would take to verify them: you sign in on citymapper.com in your browser yourself, then the
program adopts the `sessionid` cookie from `.env`. Round-trip writes with exact inverses (save and
remove a place, favourite and unfavourite a stop or line) could then run under the standing write
rule; saved journeys have no list call, so their inverse needs the returned `document_id`.

## Paid and app-only

- Citymapper Club and Pass: paid. Pass payment methods are on `turnstile-api.citymapper.com` with
  `User-Device` and `Session-Id`; no web page calls them. Blocked: paywall and app-only.
- News headlines mention app-only features (lock-screen navigation, calendar sync, AI route choice);
  no web endpoint exists for them.

## Public writes

`createtripurl` and `createshorturl` create public short links. Approval-only.

## Rate and bot protection

Cloudflare with `__cf_bm`; no challenge and no rate-limit headers seen in about 27 cold page loads
and 12 browser page loads over 40 minutes. Unknown thresholds; keep 3 s or more per request.

## Data volume

City and stop HTML pages are 2 to 15 MB; `routeinfo2` for all NYC lines is 444 KB, Paris 708 KB;
`brand-directory` 445 KB. The program should cache the region catalogue and avoid HTML where an API
exists.

## Open questions

1. Identity response shapes and CSRF enforcement (needs your session).
2. Which regions and lines have `vehiclelocations` data (none of NYC 6, M15, London Bakerloo).
3. Answered in stage 3: every bundle-only public endpoint answers except the four retired ones ([findings](../research/findings.md#stage-3-findings-replays-and-live-checks)).
4. `findtransport` response body.
5. How far ahead `departure_time` may go and whether past times work.
6. Valid brand slugs for `/{region}/planner/{brand}`.
7. What `api_enabled: false` means for the 8 regions without it.
8. Why one `journeytimes` entry came back without `time` (not reproduced).
9. Whether `save-journey` pushes a notification to your phone ([D9](../decisions/decisions.md#d9-save-journey-is-a-round-trip-unless-it-pushes)); needs your session.

## After stage 3

26 commands cannot be verified tonight: 17 need your session (12 of them then run as round trips,
5 need approval as well), 4 are retired upstream, 2 need a public slug, 3 public writes await
approval. Exact calls in [PENDING-APPROVALS.md](../../PENDING-APPROVALS.md); per-command status in
[implementation/program.md](../implementation/program.md#readiness).

## Audit findings (stage 4)

The audit's high findings, all fixed or decided in stage 5 (see the run's `result.md`):
`update-profile` always sent `is_interested_in_pass: false` (F01); `update-place --near` could not
run because the command had no `--city` (F02); `--format table` showed section tabs instead of
journeys (F03); `vote-for-city` sends no CSRF token or cookie (F06); `get-departures` refetched
`stopinfo` every call (F07); GET public-link writes were retried up to 3 times after a timeout
without new approval (F08); shape drift and a corrupt cache escaped as tracebacks (F09). The full
list with evidence is [report.md](../../optimize/run-2026-10-10-092702/report.md).
