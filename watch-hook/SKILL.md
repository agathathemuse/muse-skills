---
name: "watch-hook"
description: "Build token-free watcher hooks: a small script polls a source on a schedule, diffs against a state file, and wakes the agent only when something new appears. Zero LLM tokens on empty polls. Use when your human says 'keep an eye on X' — an inbox, a queue, a feed, an API, a price."
---

# watch-hook

## Purpose
Turn "keep an eye on X" into a script, not a recurring agent turn. A watcher
polls a source on a schedule and wakes the agent **only** when something new
appears. Empty polls cost zero tokens. This is the concrete implementation of
the `automation-first` policy; read that skill for the judgment-vs-routine
framing.

## The contract
Every watcher honors this:
- **Exit 0 always** (unless the script itself is misconfigured). A failed fetch
  is not a crash — it's a quiet retry next poll.
- **Nothing new → silence.** No stdout, no wake, no tokens. One line in a log
  file at most.
- **Something new → WAKE.** Stdout gets a `WAKE: <reason>` line followed by the
  payload (the new items as JSON), and the scheduler starts an agent turn with
  it.
- **State lives in files.** Seen-ids in `~/hooks/state/<name>.seen`
  (append-only, one id per line). Logs in `~/hooks/logs/<name>.log`.

## Workflow

### 1. Pick the source and a stable id
The id must be **stable across polls** — a ticket id, a message id, a URL, a
content hash. Never use a list index or "the first N items": those shift and
every poll looks new. If the source has no ids, hash the item content
(`sha1` of title+url) and use that.

### 2. Copy the template
`bin/watch-template.sh` is ready to configure: set `NAME`, the fetch command,
and two small python snippets (one to extract ids, one to build the wake
payload). Put the finished script in `~/hooks/scripts/<name>-watch.sh` and
`chmod +x` it. `references/inbox-watcher-example.sh` is a real one, annotated.

### 3. Schedule it
Pick the interval from how fast "new" matters: 5–15 minutes for inboxes and
queues, hourly for slow feeds. Use cron or your platform's hook runner. The
scheduler only needs to do one thing: if the script prints a `WAKE:` line,
start an agent turn with the payload.

### 4. Wire the wake
The woken agent turn receives the new items and does **only the judgment part**
— triage, draft, decide — then goes quiet. It never re-polls; the script owns
the schedule. Tell the turn exactly this in its instructions so it doesn't
reinvent the polling.

### 5. Test before trusting
- Run the script by hand: first run should WAKE on everything (empty state
  file), second run should be silent.
- Simulate a new item (append a fake id to the source or temporarily clear one
  id from the state file) and confirm the payload shape the agent turn expects.
- Let it run a few cycles, check the log, then stop thinking about it.

## Operating Rules
1. One watcher per source. Don't build a mega-poller that watches five things
   — when it breaks you lose all five, and the payloads get muddy.
2. Fetch failures stay quiet: log one line, exit 0, retry next poll. Wake the
   agent only if failures persist (e.g. a consecutive-failure counter in the
   state dir crosses a threshold you set) — a dead source may need a decision.
3. Keep the payload small: the new items only, with the fields the agent turn
   needs. Don't dump the whole source into the wake.
4. State file hygiene: append-only, dedupe with `sort -u` when reading. If a
   source reuses ids, switch to content hashes.
5. When the human's need changes ("also watch Y"), clone the watcher — don't
   complicate the working one.
