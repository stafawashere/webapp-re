---
id: quirk-slug-links-404
kind: quirk
title: gettrip and getshorturl answer 404 for unknown slugs
seen: 1
first_seen: 2026-10-10
last_seen: 2026-10-10
runs: [run-2026-10-10-090401]
---

## Lesson

GET /api/1/gettrip?slug=zzzz-no-such-slug and GET /api/1/getshorturl?slug=zzzz-no-such-slug both answered 404 on 2026-10-10. No public trip or go slug was found in the bundles or captures, so the success shape is unobserved.

## Action next time

Verify open-trip-link and open-go-link only with a slug from an approved share-journey or create-go-link.

## Sightings
- 2026-10-10 run-2026-10-10-090401
