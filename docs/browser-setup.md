# Browser setup

The scope and reverse stages work in your own browser, signed in as you, through the
[chrome-devtools MCP server](https://github.com/ChromeDevTools/chrome-devtools-mcp). It attaches
to the browser you already have open, so there's no second profile to sign into.

## Adding the server

```bash
claude mcp add --scope user chrome-devtools -- npx -y chrome-devtools-mcp@latest \
   --autoConnect \
   --workspace "$HOME/dev" \
   --no-category-emulation --no-category-performance --no-category-memory \
   --screenshotFormat jpeg --screenshotMaxWidth 1024 \
   --no-usage-statistics --no-performance-crux
```

| Flag | Why |
|---|---|
| `--autoConnect` | Attaches to the browser that's already running instead of starting a fresh one, so your sign-ins are there |
| `--userDataDir <profile folder>` | Only if your browser isn't Chrome. `--autoConnect` looks for Chrome, so another Chromium browser needs its profile folder named here. For Helium on a Mac that's `"$HOME/Library/Application Support/net.imput.helium"` |
| `--workspace` | Files the tools save (`filePath`, `responseFilePath`, `sourcePath`) have to sit under this folder, or the call fails with "Access denied". It needs to cover `$WEBAPP_RE_HOME` and the plugin |
| `--no-category-emulation`, `--no-category-performance`, `--no-category-memory` | None of the stages use these tools, and leaving them out makes the tool list about a fifth smaller |
| `--screenshotFormat jpeg`, `--screenshotMaxWidth 1024` | Smaller screenshots, for the rare time one is taken |
| `--no-usage-statistics`, `--no-performance-crux` | Turns off the server's usage reporting and its CrUX lookups |

Don't use `--slim`. It keeps only three tools and drops the network tools the stages need.

The browser asks you to allow remote debugging the first time a session connects. Click Allow
yourself. If the tools are missing or you said no, the stages tell you and ask before falling
back to anything else.

## What the stages use, and what they avoid

Some of the server's tools print more than you'd expect, so the stages stick to a few calls.

| Tool | Used for | Watch out |
|---|---|---|
| `new_page` with `background: true` | The stage's own tab. Every later call passes its `pageId` | Its reply lists the URLs of all your open tabs |
| `navigate_page` | Once per walk, with a small `initScript` | Same tab list |
| `evaluate_script` with `sourcePath` and `filePath` | All the page scripts in `plugin/assets/`. The reply is a couple of dozen tokens however big the result is | Both paths have to be under `--workspace` |
| `take_snapshot` with `filePath` | Only when a menu or dialog needs an element id to click | Inline it can run to thousands of tokens |
| `list_network_requests` | Checking a page the probe seems to have missed | Prints full query strings, API keys included, so the reverse fast path never calls it |
| `get_network_request` | Rarely, with `responseFilePath` | Prints `Cookie` and `Set-Cookie` values in its reply, so a scope never calls it |

`new_page` with `isolatedContext` isn't used either. It opens signed out, and the reply still
lists every tab.

## When it isn't enough

| Need | Use |
|---|---|
| The real wire headers, `Cookie` included, without printing them | `cdp_capture.py` against a separate Chromium started with `--remote-debugging-port`, see [capture.md](../plugin/references/capture.md) |
| Searching the page's scripts, or XHR and text breakpoints | The same CDP driver |
| chrome-devtools isn't installed or won't connect | Claude in Chrome with `capture-hook.js`, once you've said it's fine |
