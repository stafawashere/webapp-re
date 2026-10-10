# Menu hints

`<root>/menu/hints.json` tells the shared menu builder how to present a site's commands. Every
key is optional. Without the file, every command shows under Other with inputs derived from its
schema. Hints only shape presentation; which commands exist, their status and their inputs always
come from the program, the plan, the knowledge base and the site skill.

## Top level

| Key | Type | Effect |
|---|---|---|
| `subtitle` | string | Line under `/<slug>` in the header. Defaults to the origins in `site.json` |
| `footnote` | string | Muted line under the metrics, before the sync time |
| `icon` | string | Tabler outline icon class for the header tile, such as `ti-school` |
| `accent` | string | Tint for the header tile: `violet`, `aqua`, `blue`, `orange`, `green`, `red`, `yellow`, `magenta` |
| `program_command` | string | CLI entry point when it differs from the slug |
| `groups` | list | `{key, title, icon, commands: [names in display order]}`. Commands in no group go under Other |
| `global_fields` | list | Fields added to every runnable command, such as an output format. Same keys as a field hint plus `name`. A command's own input of the same name wins |
| `datalists` | object | Named suggestion lists for `list` fields, read from a JSON file in the site root |
| `option_sources` | object | Named option sets for `options_from`, read from a JSON file in the site root |
| `commands` | object | Per-command hints, keyed by command name |

## Datalists

```json
"schools": {
   "source": ["var/cache/schools.json", "var/public/schools.json"],
   "value": "domain",
   "label": "name",
   "require": "rank",
   "sort": "rank",
   "limit": 99,
   "include": ["usc.edu"]
}
```

`source` is a path relative to the site root, or a list tried in order; the file must hold a JSON
list of objects. Rows without `value` are skipped, rows without `require` are left out, the rest
are sorted by `sort` and cut at `limit`, then `include` adds named rows that exist in the file. A
missing file gives an empty list and a warning, not a failure, because caches come and go.

## Option sources

```json
"citizenships": {
   "source": "var/cache/scholarships.json",
   "path": "eligibility.citizenships",
   "labels": {"us-citizen": "US citizen"}
}
```

Collects every distinct value at the dotted `path` across the rows, flattening lists, and sorts
them. `labels` renames values for display; the value sent on the command line is unchanged. The
builder also provides `@commands`, the names of the commands that are built right now.

## Command hints

| Key | Effect |
|---|---|
| `summary` | Replaces the program's purpose line in the menu |
| `note` | The "Good to know" text. Defaults to the plan's notes |
| `cost` | Replaces the cost line derived from the plan's `requests` and `pagination` |
| `spends` | `true` marks the command as spending energy, credits or keys. The plan's confirmation text mentioning "spend" does the same |
| `fields` | Field hints keyed by input name |

## Field hints

| Key | Effect |
|---|---|
| `control` | `select`, `toggle`, `text`, `number`, `date` or `datalist` |
| `label` | Label above the control. Defaults to the input name in sentence case |
| `hint` | Small text under the control. Defaults to the schema description; `""` hides it |
| `placeholder` | Placeholder text, ideally a real example value |
| `options` | `[[value, label], ...]` for a select. `""` as a value means the flag is left out |
| `options_from` | Name of an option source or `@commands`; adds an `any_label` entry first unless the field is required |
| `list` | Name of a datalist; makes the field a text box with suggestions |
| `pick` | Name of the list command that yields this value; the menu offers a button that copies it |
| `when` | `[other_field, value]`: show the field only when that field has that value |
| `required` | Overrides the schema's required list |
| `warn` | Shows the hint in the warning color, for flags that expose sensitive data |

The confirmation input `yes` is never offered, whatever the hints say: the menu copies commands
for Claude to run, and a write still needs the user's approval in chat.

## Derived controls

Without a hint, a boolean is a toggle, an enum is a select, an integer `limit` is a select of
common sizes, other numbers are number boxes, a string whose description says "ISO date" or whose
name ends in `_date`, `_after` or `_before` is a date picker, and anything else is a text box.

## When hints take effect

The builder fingerprints `hints.json` and every file named in `source`, so an edit to either
shows on the next `/<slug> menu` with no other step. The inline mode (`/<slug> menu inline`)
keeps only the first 25 entries of each datalist; the page keeps them all.
