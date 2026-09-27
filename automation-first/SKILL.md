---
name: "automation-first"
description: "Prefer scripts and classic automation over LLM calls for routine work: classify what needs judgment vs what doesn't, build token-free watcher hooks that wake the agent only on change, and reserve the LLM for reasoning it's actually better at. Use whenever setting up recurring work, polling, or background checks."
---

# automation-first

## Purpose
The LLM is the most expensive part of the system — every turn costs tokens and
compute whether anything happened or not. Scripts are free. This skill is the
standing policy: **routine work goes in scripts; judgment work goes to the LLM.**
A Muse that polls an endpoint with a full agent turn every 15 minutes is burning
money to learn that nothing changed.

## Why it matters
Concrete wins from running this way:
- A 15-minute inbox poll as an agent turn costs thousands of tokens a day to
  report "nothing new". As a bash script it costs zero — the agent wakes only
  when a message actually arrives.
- Fetching, parsing, deduping, deploying files, reformatting data: all free in
  bash/python, all wasteful as LLM turns.
- It also makes behavior deterministic: a script diffs the same way every time,
  where an LLM re-reading a feed might notice different things per poll.

## Workflow

### 1. Classify: judgment vs routine
For each piece of recurring work, ask: does this need *reasoning*, or just *execution*?

Needs the LLM (judgment): deciding which articles are worthwhile, drafting a
reply's tone, summarizing with nuance, choosing what matters to the human.
Don't script these — the reasoning is the value. (Example: don't build a
heuristic scorer to curate articles; fetch the pile with a script and let the
LLM curate.)

Doesn't need the LLM (routine): polling on a schedule, fetching feeds or APIs,
parsing, deduping against seen-ids, deploying files, sending email, checking
"did anything change", reformatting between formats. Script all of it.

### 2. Script the routine
Write it in bash or python (stdlib preferred — no installs to rot). Rules:
- **Idempotent**: safe to run twice; running it twice changes nothing.
- **Quiet on no-op**: no output, no wake, no tokens when nothing happened.
  Log to a file for debugging, never to the agent's context.
- **State in files, not in memory**: seen-ids, watermarks, last-run timestamps
  live in a state dir (e.g. `~/hooks/state/<name>.seen`). Agent memory is not
  a database.
- **Fail plainly**: on fetch/parse failure, log one line and exit 0. The next
  poll retries. Only wake the agent if failures persist and a decision is needed.

### 3. Wake only on change
The script's schedule does the waiting; the agent does the thinking. Pattern:
1. Script runs on a schedule (cron, hook runner).
2. It diffs current state against the state file.
3. Nothing new → exit 0 silently. Something new → emit the new items and a
   wake signal, and let the scheduler start an agent turn with that payload.
4. The agent turn handles *only* the judgment part, then goes quiet again.

`bin/watch-template.sh` is a ready-made watcher implementing this: configure
the fetch command and the id-extraction snippet, schedule it, adapt the WAKE
line to your scheduler. `references/` has a real-world example (a Muse inbox
watcher) with the moving parts annotated.

(These now live in the dedicated `watch-hook` skill — see it for the full
contract, scheduling, and testing workflow.)

### 4. Keep extracting
Whenever you catch an agent turn doing something a diff, a fetch, or a file
move could do, pull it out into a script. Automation is a ratchet, not a project.

## Operating Rules
1. **Default to scripting.** "Keep an eye on X" means a watcher script, never a
   recurring agent turn.
2. Never spend a turn on a question a diff can answer: "anything new?", "did it
   change?", "is it still up?"
3. Reserve the LLM for what it's better at: relevance, taste, tone, triage —
   the calls a script would get wrong.
4. Cost-check the automation itself: if the scripted version would be long and
   fragile and the task happens rarely, one LLM turn is cheaper than building
   the machine. Automate the frequent; hand-do the rare.
5. Review script output before acting on it the first few runs; trust it after.
