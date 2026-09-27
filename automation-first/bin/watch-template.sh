#!/usr/bin/env bash
# Token-free watcher template. Polls a source on a schedule and wakes the agent
# ONLY when something new appears. Zero LLM tokens on empty polls.
#
# Setup: fill in the CONFIG section, chmod +x, schedule it (cron or your
# platform's hook runner), and adapt the WAKE line to whatever your scheduler
# listens for.
set -euo pipefail

# ---------------- CONFIG ----------------
NAME="my-watch"   # unique name; state + log files derive from it

# Command that prints the source data as JSON on stdout.
FETCH_JSON_CMD='curl -s -m 20 "https://example.com/api/items"'

# python3 snippet: reads that JSON on stdin, prints one stable id per line.
IDS_PY='import json,sys; [print(r["id"]) for r in json.load(sys.stdin)["items"]]'

# python3 snippet: reads JSON on stdin, new ids on argv; prints the wake payload.
PAYLOAD_PY='
import json,sys
new_ids=set(sys.argv[1:])
items=json.load(sys.stdin)["items"]
out=[r for r in items if str(r["id"]) in new_ids]
print(json.dumps(out))
'
# -------------- END CONFIG --------------

STATE_FILE="$HOME/hooks/state/${NAME}.seen"
LOG_FILE="$HOME/hooks/logs/${NAME}.log"
mkdir -p "$(dirname "$STATE_FILE")" "$(dirname "$LOG_FILE")"
touch "$STATE_FILE"

raw="$(eval "$FETCH_JSON_CMD" 2>/dev/null)"
if [ -z "$raw" ]; then
  echo "$(date -Is) [$NAME] fetch failed" >> "$LOG_FILE"
  exit 0   # stay quiet; next poll retries
fi

current="$(printf '%s' "$raw" | python3 -c "$IDS_PY" 2>/dev/null)"
[ -z "$current" ] && exit 0

new=()
while IFS= read -r id; do
  [ -n "$id" ] && ! grep -qxF "$id" "$STATE_FILE" 2>/dev/null && new+=("$id")
done <<< "$current"

if [ "${#new[@]}" -eq 0 ]; then
  exit 0   # nothing new: absolute silence, no tokens spent
fi

payload="$(printf '%s' "$raw" | python3 -c "$PAYLOAD_PY" "${new[@]}")"
printf '%s\n' "${new[@]}" >> "$STATE_FILE"

# WAKE: adapt this to your scheduler. Convention used here: print a WAKE line
# with the reason, then the payload. A cron worker can check for it; a hook
# runner can wake an agent turn on it.
echo "WAKE: new items for ${NAME}"
printf '%s\n' "$payload"
exit 0
