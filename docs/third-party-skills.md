# Third-party skills

Two skills in the plugin come from other repositories. Both are MIT licensed, and each folder
carries the upstream LICENSE file next to its SKILL.md.

| Skill | Source | Commit | License | Changes |
|---|---|---|---|---|
| `web-api-reverse-engineering` | github.com/vicentereig/engineering, path `plugins/engineering-skills/skills/web-api-reverse-engineering` | `9d8f5647bf15b6691aec0871a3a934ee7966dd48` | MIT, Copyright (c) 2026 Vicente Reig | SKILL.md unmodified. `INSTALL-NOTE.txt` and `LICENSE` added |
| `js-reverse` | github.com/zhaoxuya520/ai-fullstack-delivery-workflow, path `workflows/reverse-pentest/reverse-skill-private/skills/js-reverse` | `ab96b897d719941219ab3b3badb47cd6fda3e0eb` | MIT, Copyright (c) 2026 zhaoxuya520 (the LICENSE in `reverse-skill-private/`, the nearest one above the skill) | One section replaced, see below. `LICENSE` added |

I cloned each repository into an empty directory with git hooks off and read every file before
copying the skill folder in. Nothing from the clones was run.

## web-api-reverse-engineering

Chrome automation plus traffic capture to map undocumented endpoints, handle pagination, session
cookies and CDN quirks, and emit OpenAPI 3.1. The scope stage borrows its discovery-notes
vocabulary and the engineer stage uses it for the spec. It suggests `bd` (beads) commands, which
are optional, so `INSTALL-NOTE.txt` says to skip them when beads is not installed.

## js-reverse

It covers the client side, finding signature and encryption logic in frontend code, tracing runtime
behaviour, and rebuilding the browser environment in Node. Its text is Chinese. The reverse and
engineer stages load it only when a request carries a value computed by client code.

The upstream section "按需自举 (On-Demand Bootstrap)" was removed. Its steps were to:

- write `jshookmcp` (`@jshookmcp/jshook`, launched through `npx`) into the Claude MCP config,
- register and start an `anything-analyzer` local HTTP MCP, cloning that project and installing
  it with pnpm,
- install Node.js 22 through `winget`,
- run `scripts/bootstrap-reverse.ps1`.

Each of those changes the machine outside the skill folder, and the script is Windows PowerShell. The
replacement section, "Local install note", records the source and the cut, and maps the skill's
`js-reverse_*` and `jshookmcp` tool names to tools that are usually there instead: the Claude in
Chrome tools (`read_network_requests`, `javascript_tool`, `read_console_messages`) or a CDP
driver such as `scripts/cdp_capture.py`.

## Installing them separately

They are bundled, so nothing extra is needed. To use the upstream versions instead, fetch the
paths above at the listed commits and replace the two folders under `plugin/skills/`, keeping
the folder names so the stage skills still find them.
