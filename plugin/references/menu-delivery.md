# Menu delivery

How `/<slug>:menu` reaches the user when the default path in the site skill's `## Menu` section
does not apply. Read this only on those paths. `<pipeline>` below is the webapp-re plugin directory, the parent of the `references/` folder this file is in.

## What build prints

`build_menu.py build --site <slug>` prints one line of JSON and nothing else:

| Key | Holds |
|---|---|
| `open` | The page's URL on 127.0.0.1 (default) or its `file://` URL (`--file`) |
| `inline` | The widget file or files to join for `show_widget` (`--inline`) |
| `chars` | The size of the inline widget in characters (`--inline`) |
| `counts` | Ready, verified live, unverified, blocked, planned, and verified endpoints |
| `warnings` | Present only when there are some; say each in plain words |
| `problems` | Present only when there are some; report them and stop |

The builder fingerprints every input (the program's source tree, the plan, the knowledge base,
the site skill, the hints and their option sources, and the shared menu files). When nothing
changed it reuses the last page, and the program's `help` runs again only after the program
changed. `--force` rebuilds and reruns `help` anyway. The page server listens on 127.0.0.1 only,
serves the current page file on every request, and exits after 15 minutes without a request.

## Order of paths

1. **Built-in browser** (the `preview_start` tool is present): the default in the site skill.
   One Bash call, one `preview_start` with the `open` URL, one line of reply.
2. **Inline, on request or without the built-in browser** (`/<slug>:menu inline`, or the
   visualize tools are present and the built-in browser is not):
   1. Run `uv run --script <pipeline>/menu/build_menu.py build --site <slug> --inline`.
   2. Load the visualize tools with ToolSearch if they are deferred, and call `read_me` with the
      `interactive` module once per session, silently.
   3. `cat` every file in `inline`, in one message with one call per file, and join them in order
      with nothing added between.
   4. Call `show_widget` with the joined text, unchanged, as `widget_code` and `<slug>_menu` as
      `title`, then reply in one line with the counts and any warnings.

   The inline widget leaves out the returned fields, endpoints, notes and open steps, keeps the
   first 25 entries of each datalist, and clips long texts. It passes through the model twice, so
   it costs tokens and time in proportion to its size, which `chars` reports.
3. **Neither tool**: give the user the `open` URL to open in any browser on this Mac. It works
   while the page server runs. With `--file` the builder prints the page's `file://` URL instead.

Never edit the built files under `var/menu/`. Never add `sendPrompt` to the widget: its buttons
copy commands to the clipboard and fall back to showing the text for manual copying.
