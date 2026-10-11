#!/bin/zsh
# Runs CDP capture windows one after another with a pause between page loads.
# Usage: tools/scope/capture_batch.sh <run-id> <list-file>
# Each line of the list file: <label> <url>

set -u
SITE_ROOT="${0:A:h:h:h}"
RUN_ID="$1"
LIST_FILE="$2"
PAUSE_SECONDS="${PAUSE_SECONDS:-7}"
WINDOW_SECONDS="${WINDOW_SECONDS:-15}"

cd "$SITE_ROOT"

while read -r label url; do
   if [[ -z "$label" || "$label" == \#* ]]; then
      continue
   fi

   echo "### $label $url"
   timeout 120 uv run --script "$HOME/dev/webapp-re/plugin/scripts/cdp_capture.py" \
      --root . --run "$RUN_ID" --label "$label" --url "$url" \
      --seconds "$WINDOW_SECONDS" --filter "/api/|/geocode|citymapper.com/[a-z]" 2>&1 | grep -vE "googleapis|gstatic|typekit|static-img|/static/"

   sleep "$PAUSE_SECONDS"
done < "$LIST_FILE"

echo "batch done"
