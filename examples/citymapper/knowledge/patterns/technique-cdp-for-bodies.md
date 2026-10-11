---
id: technique-cdp-for-bodies
kind: technique
title: Use the CDP driver for bodies on citymapper.com
seen: 1
first_seen: 2026-10-10
last_seen: 2026-10-10
runs: [run-2026-10-10-082844]
---

## Lesson

The webapp bundle binds fetch at module load (isomorphic fetch), so the injected capture hook records nothing; the Claude in Chrome extension blocks long and base64-like outputs, and posting to a localhost sink triggers the browser's local-network permission. cdp_capture.py on a separate Brave instance (dedicated profile, port 9222) captures every body and passes Cloudflare.

## Action next time

Capture with scripts/cdp_capture.py; use the extension only for navigation, DOM reads and request URLs.

## Sightings
- 2026-10-10 run-2026-10-10-082844
