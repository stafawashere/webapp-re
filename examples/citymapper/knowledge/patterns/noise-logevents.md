---
id: noise-logevents
kind: noise
title: POST /api/2/logevents is first-party telemetry
seen: 1
first_seen: 2026-10-10
last_seen: 2026-10-10
runs: [run-2026-10-10-082844]
---

## Lesson

Every page fires POST https://citymapper.com/api/2/logevents with a text/plain body starting 'U <user agent>' and headers citymapper-client: Web, citymapper-region and user-device; the answer is 13 bytes. It carries analytics only.

## Action next time

Filter it out of captures; never call it from the program.

## Sightings
- 2026-10-10 run-2026-10-10-082844
