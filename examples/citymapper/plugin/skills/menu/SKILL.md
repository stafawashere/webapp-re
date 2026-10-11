---
name: menu
description: "Open the interactive citymapper.com command menu in the built-in browser. Shortcut for /citymapper:citymapper menu."
argument-hint: "[inline]"
disable-model-invocation: true
---

# citymapper menu

Arguments: $ARGUMENTS. With `inline`, take the `menu inline` path below.

For `menu`, run `uv run --script ${CLAUDE_PLUGIN_ROOT}/../../../plugin/menu/build_menu.py build --site ${CLAUDE_PLUGIN_ROOT}/..`.
It prints one JSON line. Open its `open` URL with the built-in browser's `preview_start` (`url`),
then reply in one line with its `counts` and any `warnings`. If it prints `problems`, report them
and stop. For `menu inline`, or when the built-in browser tools are missing, follow
`${CLAUDE_PLUGIN_ROOT}/../../../plugin/references/menu-delivery.md`. The menu sends nothing to the site;
its hints live in `${CLAUDE_PLUGIN_ROOT}/../menu/hints.json`.
