#!/bin/sh
# Rebuilds img/banner-light.png and img/banner-dark.png from tools/banner/banner.html.
# macOS only: it compiles render.swift (an offscreen WebKit snapshot) with the Xcode command
# line tools. usage: sh tools/banner/regenerate.sh [OUT_DIR]
set -eu

here=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(cd -- "$here/../.." && pwd)
out="${1:-$root/img}"
build="${TMPDIR:-/tmp}/banner-render"
binary="$build/render_html"

mkdir -p "$build" "$out"

if [ ! -x "$binary" ] || [ "$here/render.swift" -nt "$binary" ]; then
   swiftc -O -o "$binary" "$here/render.swift"
fi

for theme in light dark; do
   "$binary" --input "$here/banner.html" --out "$out/banner-$theme.png" \
      --width 900 --height 300 --scale 2 --theme "$theme" \
      --read-root "$root"
done
