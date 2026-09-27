# Real-world example: a Muse's inbox watcher (annotated)
# Originally written for the Hatch hook runtime; runtime-specific calls are marked.
# Generic equivalents: log() -> append to a log file; silent() -> exit 0 quietly;
# wake(reason, payload) -> emit WAKE + payload for the scheduler.

#!/usr/bin/env bash
# Poll Agatha's Muse-visitor inbox for new introduction tickets.
# Cheap by design: plain bash + ssh, zero LLM tokens. Wakes a worker
# agent ONLY when a ticket appears that hasn't been seen before.
set -euo pipefail
source "$HATCH_HOOK_RUNTIME"

STATE_FILE="$HOME/hooks/state/muse-inbox.seen"
mkdir -p "$(dirname "$STATE_FILE")"
touch "$STATE_FILE"

raw="$(/home/hatch/bin/muse-inbox --json 2>/tmp/muse-inbox-hook.err)"
if [ -z "$raw" ]; then
  log "muse-inbox fetch failed: $(head -c 200 /tmp/muse-inbox-hook.err 2>/dev/null)"
  silent "inbox fetch failed"
  exit 0
fi

current="$(printf '%s' "$raw" | python3 -c 'import json,sys; [print(r["ticket"]) for r in json.load(sys.stdin)]')"

new_tickets=()
while IFS= read -r t; do
  [ -z "$t" ] && continue
  if ! grep -qxF "$t" "$STATE_FILE" 2>/dev/null; then
    new_tickets+=("$t")
  fi
done <<< "$current"

if [ "${#new_tickets[@]}" -eq 0 ]; then
  silent "no new introductions"
  exit 0
fi

payload="$(printf '%s' "$raw" | python3 -c '
import json,sys
new_ids=set(sys.argv[1:])
items=json.load(sys.stdin)
out=[{"ticket":r["ticket"],"muse_name":r.get("muse_name"),"serves":r.get("serves"),"received_at":r.get("received_at")} for r in items if r["ticket"] in new_ids]
print(json.dumps({"tickets":out}))
' "${new_tickets[@]}")"

# Don't pollute real state during dry runs.
if [ "${HATCH_HOOK_DRY_RUN:-0}" != "1" ]; then
  printf '%s\n' "${new_tickets[@]}" >> "$STATE_FILE"
fi

log "new introduction tickets: ${new_tickets[*]}"
wake "new muse introduction" "$payload"
exit 0
