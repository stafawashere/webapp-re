# Pacing and account safety

Automation that hammers a site gets the user's account restricted. Pacing belongs in the program,
never in its callers, and its defaults are conservative.

## Defaults until measured

- One request in flight at a time.
- At least 3 seconds between requests to the same origin, with 20 to 40 percent jitter.
- Discovery runs stay far below that. A replay is one request, not a loop.
- No automatic retry of anything but transport errors, at most twice, with exponential backoff
  starting at 5 seconds.
- A 429, a challenge page or a checkpoint stops the whole client, not just the call.

## Measuring a site's safe rate

Only when the user asks for more throughput. Read-only endpoint, the user's own data, a fixed
budget stated before starting. Start at one request per 5 seconds, halve the interval every 50
clean requests, stop at the first 429, challenge, or latency rise above twice the baseline, and
record the last clean rate as a `pacing` pattern with the date, IP class and request count. That
number is evidence for one account, one day, one network. Say so.

As a rough data point, a large social site tolerated about 0.35 requests per second sustained
with zero throttling over about 650 requests, while its own web client ran near 4.5. Treat that
as an order of magnitude, not a default for any other site.

## Browser parity

The safest client looks like the site's own: the same companion requests, the same headers, the
same order, human timing, the same session lifetime. Every departure from parity is a decision
the user makes, and the program exposes it as configuration rather than hardcoding it.

## Session handling

Adopt cookies the user copied from their own signed-in browser. Never automate a password login
unless the user asks for it as a separate feature, and even then never store the password. Keep
cookie material in the site's `.env` (mode 600) or a session file outside version control, load it
through the environment or a file path, never through `argv`, and redact it in every log.
