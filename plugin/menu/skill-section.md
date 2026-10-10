## Menu

For `menu`, run `uv run --script {pipeline}/menu/build_menu.py build --site {slug}`.
It prints one JSON line. Open its `open` URL with the built-in browser's `preview_start` (`url`),
then reply in one line with its `counts` and any `warnings`. If it prints `problems`, report them
and stop. For `menu inline`, or when the built-in browser tools are missing, follow
`{pipeline}/references/menu-delivery.md`. The menu sends nothing to the site;
its hints live in `{root}/menu/hints.json`.
