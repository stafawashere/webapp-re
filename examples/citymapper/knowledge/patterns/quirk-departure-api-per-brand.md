---
id: quirk-departure-api-per-brand
kind: quirk
title: Departures endpoint depends on the stop's brand
seen: 1
first_seen: 2026-10-10
last_seen: 2026-10-10
runs: [run-2026-10-10-082844]
---

## Lesson

Bus and ferry stops use /api/1/departures (stops[].services[].live_departures_seconds), metro stations /api/2/metrodepartures (sections[].departure_groupings[].departures[] with time_seconds or scheduled_time), commuter rail /api/1/raildepartures (departures[] with expected_departure_time). stopinfo's sharing_urls[].departure_api names the right one.

## Action next time

Call stopinfo first and dispatch on departure_api.

## Sightings
- 2026-10-10 run-2026-10-10-082844
