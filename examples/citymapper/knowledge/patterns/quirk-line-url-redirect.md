---
id: quirk-line-url-redirect
kind: quirk
title: Line URLs and bike docks
seen: 1
first_seen: 2026-10-10
last_seen: 2026-10-10
runs: [run-2026-10-10-082844]
---

## Lesson

routes[].url is /{region}/l/{alias}, which redirects to /{region}/{mode}/{alias}; bike docks have no page (/nyc/bike/docks/<id> answers 404).

## Action next time

Use routeinfo with route=<alias>; read dock availability from nearby.

## Sightings
- 2026-10-10 run-2026-10-10-082844
