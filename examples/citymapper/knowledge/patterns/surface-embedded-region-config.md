---
id: surface-embedded-region-config
kind: surface
title: City pages embed the region and city catalogue
seen: 1
first_seen: 2026-10-10
last_seen: 2026-10-10
runs: [run-2026-10-10-082844]
---

## Lesson

Every server-rendered page (for example https://citymapper.com/nyc) sets window.citymapper.regions (115 [region, distance_km] pairs), window.citymapper.citiesInRegions (252 cities keyed by slug), window.citymapper.region (the current region with nearby_modes, feature flags, bounding box, timezone), window.citymapper.brands and window.citymapper.apiUrl '/api/'. No API call serves the region list.

## Action next time

Parse these window.citymapper assignments from the HTML of a city page to list cities and resolve region ids; one GET per region.

## Sightings
- 2026-10-10 run-2026-10-10-082844
