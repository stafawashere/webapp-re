# Sessions

Append-only ledger, one entry per closed run, newest last.

## run-2026-10-10-082844

- closed 2026-10-10, browser claude-in-chrome + cdp (separate Brave profile), live requests 260
- touched: blog, cities-html, city-html, city-vote, createshorturl, createtripurl, cycle, departures-bus, departures-metro, departures-rail, eta, everythingmap, findtransport, geocode, getshorturl, gettrip, identity-confirm-signup, identity-delete-journey, identity-favorites-create, identity-favorites-delete, identity-favorites-list, identity-magiclink, identity-password-reset, identity-places-create, identity-places-delete, identity-places-list, identity-places-update, identity-save-journey, identity-sessions-create, identity-sessions-delete, identity-update-user, identity-user-data, journeys, journeytimes, message, nearby2, nearby3, news-html, noise-logevents, noise-third-party, placeresolve, quirk-departure-api-per-brand, quirk-line-url-redirect, quirk-searchpost-form-json, refreshjourneys, resource-brand-directory, resource-region-info, resources, routeinfo1, routeinfo2, routepaths, routestatus, schedules, searchpost, stopinfo, surface-embedded-region-config, taxi, technique-cdp-for-bodies, transitscore, traveltime, trip-meta, turnstile-addpaymentmethod, turnstile-deleteallpaymentmethods, turnstile-deletepaymentmethod, turnstile-sessionttl, turnstile-setdefaultpaymentmethod, turnstile-userinfo, vehiclehire, vehiclelocations, walk1, walk7, weather
- takeaway: Citymapper's web API is public and unsigned: journeys, search, nearby, stop departures, lines and status are same-origin JSON under /api/<v>/ scoped by region_id; region and city catalogue is inlined in page HTML; the account surface exists but you are signed out.
- still open: account surface unverified (signed out); 15 bundle-only endpoints to replay in engineer

## run-2026-10-10-090401

- closed 2026-10-10, browser none for engineer replays (httpx); CDP Brave profile from scope stage, live requests 152
- touched: blog, cities-html, city-html, cycle, departures-bus, departures-metro, departures-rail, eta, everythingmap, findtransport, geocode, identity-user-data, journeys, journeytimes, message, nearby2, nearby3, news-html, placeresolve, quirk-journeytimes-missing-time, quirk-slug-links-404, refreshjourneys, resource-brand-directory, resource-region-info, resources, routeinfo1, routeinfo2, routepaths, routestatus, schedules, searchpost, stopinfo, taxi, transitscore, traveltime, trip-meta, vehiclehire, vehiclelocations, walk1, walk7, weather
- takeaway: London bus stops return timetable times in services[].next_departures when no live seconds exist; stopinfo has no kind field, so stop type comes from sharing_urls[0].departure_api
- still open: 26 hypothesis findings need the user's signed-in session (identity, Pass) or a public slug (gettrip, getshorturl)

## run-2026-10-10-113603

- closed 2026-10-10, browser none (program over httpx), live requests 40
- touched: cities-html, cycle, everythingmap, findtransport, geocode, identity-user-data, journeys, journeytimes, message, nearby3, news-html, placeresolve, refreshjourneys, resource-brand-directory, resources, routeinfo1, routeinfo2, routepaths, routestatus, schedules, searchpost, stopinfo, taxi, traveltime, vehiclelocations, walk7
- takeaway: /api/1/resources redirects to another host; the program follows cross-host redirects only for requests without cookies, CSRF or Pass headers
- still open: 26 hypothesis findings still need the user's session or a public slug
