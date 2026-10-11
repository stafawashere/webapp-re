# How the Citymapper example was built

webapp-re got from an empty folder to a working Citymapper program and plugin in five stages. Each
section below names the stage and the command that runs it, then says what it did and what it left
behind.

The run happened on 2026-10-10 as one long session. I gave Claude Code a brief that said which site to
use and what it wasn't allowed to do, and it took citymapper.com through every stage in order. It
started at 08:21 and finished the optimize stage a little after 11:36, with the menu after that. You
can repeat it by running the stage commands below one at a time, though the site may have changed
since.

The run never signed in to Citymapper, because signing in could have
created an account. And it never sent anything that changes data on the site. Every change it wanted
to make was written down for approval instead.

## The idea in one paragraph

Citymapper's website gets its data the same way most modern sites do. The page you see asks
Citymapper's servers for small pieces of data in the background, like "journeys from here to there"
or "next trains at this stop". Together those requests make up an API that Citymapper doesn't
document. webapp-re watches those requests, works out which one does which job, checks that it can repeat each one on its
own, and then builds a program that makes those same requests for you.

## Stage 1: scope

```
/webapp-re:scope citymapper.com
```

Scope is a read-only tour of the site. It opened Citymapper in a browser tab and visited the pages a
person would: the city page, directions, nearby stops, line pages, service status, news, and the same
pages for London and Paris. For each page it recorded which background requests fired.

Seeing a request's address isn't enough, because you also need the answer it got back. Citymapper's
page hides those answers from the usual browser hooks, so the stage started a second, separate
browser profile that was signed out of everything and read the full responses from there.

At the same time, a second agent downloaded Citymapper's JavaScript once and searched the copy for
every API address the site knows about, including ones that only show up when you're signed in.
That turned up 68 entries, and the search itself sent no requests.

Analytics, ad pixels and other background chatter were filtered out as noise, and a few
Citymapper-specific noise sources were saved so later runs skip them too.

What it produced:

- `scope/scope.md` and `scope/scope.json`, the inventory: 18 pages, 53 things you can do on the site,
  68 endpoints, and 6 open questions.
- `research/regions.json`, the list of 115 regions and 252 cities, which turned out to be sitting
  inside every page.
- `knowledge/`, one note per endpoint, all marked as unconfirmed guesses for now.

The scope checker's last line was
`scope: 18 pages, 53 capabilities, 68 endpoints, 24 entities, 14 caveats, 6 open_questions; 0 problems`.

## Stage 2: plan

```
/webapp-re:plan citymapper
```

Plan turns the inventory into a list of commands a person would want, without touching the site. For
each command it decides the name, the inputs, what comes back, which endpoints it depends on, and
whether it only reads or also changes something.

It came out with 57 commands: 40 that only read and 17 that change something. They're grouped and
ordered so the basics get built first. City lookup comes first, then journeys, then departures, then
disruptions, then account features. Three things on the site were left out on purpose with a reason
written down: signing in, signing up and password reset, because the brief forbade them, and
Citymapper's own telemetry.

What it produced: `plan/plan.md` and `plan/plan.json`. The plan checker reported
`plan: 57 commands, 8 build steps` and `0 problems`.

## Stage 3: engineer

```
/webapp-re:engineer citymapper
```

Engineer builds the program, and before that it checks every endpoint scope found.

First it replayed each endpoint outside the browser to see whether it works on its own. The first
round sent 59 requests and 48 worked. Some of the failures came from wrong inputs, like a bad id, so
a second round of 29 requests retried with corrected inputs and 26 worked. Four endpoints answered "This API is no longer supported" or "Page Not
Found" in two different regions, twice each, so they were marked as retired by Citymapper. An endpoint
only counts as verified after it passes twice. A command that depends on an endpoint that isn't
verified can still be built, but it's never reported as verified.

Then it wrote the program itself, in `program/`. It's a Python library with a command-line tool on top.
It handles the boring parts the same way for every command. It waits at least 3 seconds between
requests, turns a city name into the region id Citymapper wants, caches things that rarely change, and
gives each kind of failure its own exit code and message.

A second agent wrote tests that run against made-up data, with no internet. Those tests found 4 bugs in the
first version, such as London bus times being ignored, and all four were fixed. Then every command
that can run signed out was run once against the live site, and its answer was checked for the right
shape and sensible values, never for exact values, since live data changes. 32 of 33 checks passed on
the first try. The one failure was a journey time that was sometimes missing, which the program now
allows for.

Commands that change data were built but not sent. Each one has a dry run that shows exactly what it
would send, and those are collected in `PENDING-APPROVALS.md`.

What it produced:

- `program/`, the library, the `citymapper` command and 372 offline tests at that point.
- `openapi/citymapper.openapi.yaml`, a standard API description with 35 paths.
- `plugin/`, the `/citymapper` plugin for Claude Code. Its main skill explains every command and its
  status, and a small launcher script runs the program.
- `knowledge/` updated, with each endpoint's verify count and date.

## Stage 4: optimize

```
/webapp-re:optimize citymapper
```

Optimize is a second opinion on what engineer built. It runs an audit that changes nothing, then
applies the fixes that are accepted.

In the audit, seven reviewers each looked at one area: speed, stability, coverage, correctness,
safety, how clear the plugin's instructions are, and anything else. Each could report at most 6 problems and had to
point at the exact line and show evidence. Then two separate checkers tried to prove each problem
wrong. The audit made 7 live requests out of a budget of 20.

It ended with 38 findings. 34 were confirmed, 1 was likely but couldn't be fully reproduced, and 3 were
thrown out as duplicates. Another 13 never made it in because of the 6-per-reviewer cap. The most
serious were bugs that would hurt someone using it, like a profile edit that quietly turned off a
setting, or a share-link write that could be sent 3 times if the network timed out.

In the apply step, all 35 kept findings were fixed in two waves. Every fix came with a test that was
shown to fail before the fix and pass after. Then every check from engineer ran again, and the live
check found one new problem with the legal pages, which was fixed and rechecked.

The numbers that moved: offline tests went from 372 to 502, `help` got faster (median 153 ms down to
95 ms), and writes now need `--confirm` with a value from the dry run you approved.

What it produced: `optimize/run-2026-10-10-092702/`, with `report.md` for the audit and `result.md`
for what was fixed and how.

## Stage 5: integrate-menu

```
/webapp-re:integrate-menu citymapper
```

The last stage gives the plugin a menu. It reads the plan and the program's status file and builds a
page that lists every command by group, with its fields and a line you can copy. A small hints file
fills in good example values, like a dropdown of all 115 regions.

What it produced: `menu/hints.json`, the city list in `var/public/regions.json`, and a menu section in
the plugin's instructions. The menu lists all 57 commands with each one's status.

## Where it ended up

The run ended with 29 commands verified against the live site and 2 that only run locally. The other
26 are built and tested but wait on something the run couldn't do on its own. [README.md](README.md) lists what each of those is
waiting on.

Across the whole run it sent about 461 requests to Citymapper: an estimated 260 during the scope tour
(`knowledge/sessions.md`), 152 during engineer (`docs/research/findings.md`) and 49 during optimize.
None came back as a 429 or a challenge page, and nothing that changes data was sent.

`docs/` has the longer version: the 23 decisions made along the way and why, and 18 things that went
wrong and how they were handled.
