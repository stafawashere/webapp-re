---
id: quirk-searchpost-form-json
kind: quirk
title: searchpost sends JSON under a form content type
seen: 1
first_seen: 2026-10-10
last_seen: 2026-10-10
runs: [run-2026-10-10-082844]
---

## Lesson

POST https://citymapper.com/api/4/searchpost carries a JSON body with Content-Type application/x-www-form-urlencoded; charset=UTF-8 plus Citymapper-Client: Web Search and Citymapper-Region: <region_id>.

## Action next time

Replay with the same content type and headers; do not switch to application/json without testing.

## Sightings
- 2026-10-10 run-2026-10-10-082844
