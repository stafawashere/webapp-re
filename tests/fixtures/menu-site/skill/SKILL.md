---
name: menusite
description: "Read the user's own menusite account through a local program. Commands: help, list-items, get-item, save-item, brand-new. Use when the user runs /menusite."
argument-hint: "<command> [options]"
---

# menusite

Request: $ARGUMENTS

## Commands

| Command | Kind | Status | Does |
|---|---|---|---|
| `help` | read | local | List commands |
| `list-items` | read | verified live | List items |
| `get-item` | read | built, not verified (needs approval) | Return one item |
| `save-item` | write | verified live | Save an item |
| `brand-new` | read | verified live | A command added after the hints were written |

## Errors

| Exit | Class | What to tell the user |
|---|---|---|
| 10 | SessionExpired | Adopt the session again. |
