---
id: quirk-journeytimes-missing-time
kind: quirk
title: journeytimes sometimes omits time
seen: 1
first_seen: 2026-10-10
last_seen: 2026-10-10
runs: [run-2026-10-10-090401]
---

## Lesson

POST /api/1/journeytimes answered an entry without 'time' once on 2026-10-10 for a NYC depart-at plan; immediate re-probes with the same kind of plan returned time on every entry. Entries keep their request order.

## Action next time

Treat time as nullable per entry and report an error field instead of failing the whole call.

## Sightings
- 2026-10-10 run-2026-10-10-090401
