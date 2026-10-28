# Changelog

The version in `plugin/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` moves
with each release, which is how `claude plugin update webapp-re` knows there's something new. The
first release used a date as its version. From 2.0.0 on it's semantic versioning.

## 2.2.0 (2026-10-27)

### Update alert

When a newer webapp-re is tagged on GitHub, the first session you start says so in one line,
along with the command to update. A `SessionStart` hook runs `update_check.py check`, which reads
the installed version from `plugin.json` and compares it with the highest `vX.Y.Z` tag of the
repository. It asks api.github.com at most once a day and caches the answer in the plugin's data
folder. The request gives up after 2 seconds, and when it fails (offline, rate limited, a reply it
can't read) the hook prints nothing and doesn't try again until the next day. A local build that's ahead of the latest tag stays quiet too. Set
`WEBAPP_RE_NO_UPDATE_CHECK=1` to turn the check off. `update_check.py status` shows the installed
and latest versions, how old the cached answer is and whether the check is off.

### Other changes

- `plugin.json` has a `repository` field, and the check reads its tags from there, so a fork
  checks its own releases.
- The `plugin.json` description now lists all seven stages. It had left out `upgrade`.

## 2.1.0 (2026-10-27)

### New `upgrade` stage

`/webapp-re:upgrade <site or all>` brings a site built by an older webapp-re up to the installed
version without asking anything along the way. `upgrade_check.py audit` runs the current checkers
against the site and maps each failure to the stage that fixes it, so only those stages run. A site
that already names the installed version and passes every check costs one script call. When
anything did run, or the version moved, it also runs `optimize --auto` to catch method changes no
script checks for. `upgrade_check.py stamp` then writes the version into `site.json`, and it refuses
while any check still fails. No live writes are sent, and a login wall or challenge stops the live
part of that site. `--dry-run` prints the audit and stops.

### Other changes

- `kb.py init` records `webapp_re_version` in a new site's `site.json`, so a later upgrade knows
  where it started.
- The site layout documents `var/upgrade/`, which keeps the audit from before and after the last
  upgrade run.

## 2.0.0 (2026-10-27)

This is a major version because the default browser changed. If you used the plugin with Claude
in Chrome, you'll need the chrome-devtools MCP server set up (see below) before the scope and
reverse stages work as documented. Otherwise this release is mostly about cost. A scope walk and a reverse run used to spend most of their
tokens on browser tool output: tab lists, network listings, whole response bodies printed into the
conversation. Now the browser does the repetitive work itself and hands back a short summary, or
writes the result to a file and replies in a couple of dozen tokens.

### The browser is now driven through chrome-devtools

Before, the default was the Claude in Chrome extension. Now it's the
[chrome-devtools MCP server](https://github.com/ChromeDevTools/chrome-devtools-mcp) attached to
the browser you're already signed into. Setup is in [docs/browser-setup.md](docs/browser-setup.md).

Why it changed:

- `new_page` with a URL starts recording from the first request, so calls made while the
  page loads are captured. With the extension those were easy to miss.
- `get_network_request` and `evaluate_script` can write their output to a file instead of the
  conversation. A saved response body costs a few hundred tokens to read in part, where an inline
  one cost thousands.
- Full request and response bodies come straight from the browser, so the page hook is no longer
  needed for a scope walk.

What stays the same: Claude in Chrome still works, but only as a fallback and only after you say
so. `cdp_capture.py` is still the tool for real wire headers (including `Cookie`) and for
searching inside the page's scripts.

Things worth knowing, all measured and written down in `plugin/references/capture.md`:

- Every page tool appends the list of all your open tabs to its reply. One of those URLs showed an
  OAuth `state` value. The scope walk now moves between pages from inside the page, so it skips
  that list.
- `get_network_request` prints `Cookie` and `Set-Cookie` values inline. The skills avoid it on
  requests whose cookies shouldn't land in the transcript and use the CDP driver instead.
- File saves only work under the server's `--workspace` folder.
- `--slim` mode dropped the network tools when this was tested, so the setup doc leaves it off.

### Scope walks run one small script per page

`plugin/assets/scope-probe.js` replaces the old loop of navigate, list requests, read requests. One
`evaluate_script` call per page:

1. moves to the next page in a queue kept in `sessionStorage`, through the site's own router or a
   link click, so there's no full navigation and no tab list,
2. records the API calls the page made (ids turned into `{id}`, query keys without values), links
   grouped by section, pagination links, forms and their field names, CSRF names, cookie names the
   page can see, and which framework it runs,
3. refetches up to four new same-origin GET calls to get their response header names and JSON
   shape,
4. saves all of that to a file and replies in about 30 tokens.

It never returns a value, only names, patterns and shapes. The first page load carries a short
timing hook so a site that calls `clearResourceTimings` (GitHub does) can't wipe the record before
the probe reads it.

`scope-paginate.js` checks one list's next page. `plugin/scripts/walk_summary.py` folds the probe
files into `walk.json`: pages visited, pages still to visit, the noise list, and whether the site
renders on the server or the client. An interrupted walk resumes from that file. With
`--draft-scope` it also writes a starting `scope.json` holding pages, endpoints, header names and
response shapes, so only capabilities, auth, caveats and open questions are left to write by hand.

On a GitHub walk the old loop cost 11,766 browser-tool tokens for 9 pages. The probe cost 2,413
for 11 pages plus a pagination check.

### Plan and engineer read the scope in slices

A finished `scope.json` runs from 40 to 240 KB on real sites, and the plan and engineer stages used
to read it whole. `plugin/scripts/scope_query.py` prints a one-line-per-item index (7 to 14 percent
of the file), then opens one item with `--id`, one section with `--section`, or finds ids with
`--grep`. Both stages now read it that way. The plan stage also reads only the "Status ladder"
section of `knowledge-base.md` instead of the whole reverse skill.

### Reverse has a fast path

When the goal is a read the page fires after one click or keystroke (a search box, a filter, a
"load more"), the reverse stage now runs three page scripts in a row:

- `reverse-capture.js` ranks every call the action made and marks the best one as the target.
  Anything with a secret-looking name (keys, tokens, signatures) shows as `REDACTED`, and headers
  show as names only.
- `reverse-ablate.js` drops each query parameter, header and top-level body field one at a time,
  350 ms apart, and reports which ones the request needs, which change the result, and which are
  ignored. That's the first verify pass, in one call.
- `reverse-export.js` saves the minimal request to a file, and `plugin/scripts/replay.py` sends it
  from outside the browser with a different input (`--set q=other`). That's the second,
  independent verify pass. `--consume` deletes the file afterwards because it holds live values.

Measured on hn.algolia.com, goal "search stories by keyword":

| | step by step | fast path |
|---|---|---|
| tool tokens, whole run | 8,312 | 1,818, plus about 650 to read the fast path |
| tool calls | 23, 5 failed | 10, 0 failed |
| wall time | 159 s | about 55 s |
| search key in the transcript | yes | no |

Requests made only while the page loads, writes, and requests with computed signatures still go
the long way.

Two things that run turned up. An API that answers `Access-Control-Allow-Origin: *` rejects a
request sent with `credentials: "include"`, so the ablation falls back to `same-origin`. And a
server-side cache makes a repeated request look stable when it isn't, so fields that change on
every response (timers, server names, request ids) are filtered out by name before comparing.

### Smaller changes

- `capture-hook.js` keeps request header values, so the ablation can resend a request exactly. They
  sit on a hidden property, and a dump never prints them.
- `kb.py` reads `KB_SITE` and `KB_SLUG` from the environment when `--site` is left out, so a run
  can export them once instead of repeating the flag on every call.
- `kb.py record-finding --surface` accepts `api`, `json` and `http` as `rest`, `gql` as `graphql`
  and `ws` as `websocket`, instead of rejecting the call.
- `shape.py` takes the file as a plain argument as well as `--file`.
- The scope skill keeps the run id from `kb.py new-run`, uses it for the capture folder, and passes
  it to `close-run`.
- `js-reverse` maps its tool names to the chrome-devtools tools, which share most of them without
  the `js-reverse_` prefix.

### Not covered yet

The page scripts, `walk_summary.py`, `scope_query.py` and `replay.py` have no test fixtures. They
were checked by live runs on GitHub and hn.algolia.com, and those captures hold account data, so
they stay out of the repo. The fast path has only been measured on one site.

## 2026.10.10 (first release)

First public release: the pipeline plugin with its `reverse`, `scope`, `plan`, `engineer`,
`optimize` and `integrate-menu` stages, the per-site knowledge base, the site plugin generator,
the scope, plan and optimize checkers, the menu builder and its tests, and the Citymapper
workspace under `examples/` as a worked example of a full run.
