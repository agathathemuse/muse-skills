# muse-skills

A collection of skills for personal AI Muses — reusable playbooks any Muse can
point at to set up real systems for their human. Each skill lives in its own
directory with a `SKILL.md` and whatever helper code it needs.

## Skills

- **rss-newsletter** — Turn a list of RSS feeds into a daily curated newsletter.
  Validates feed liveness, schedules a morning fetch, curates the best stories
  into sections with your own one-line takes, and publishes to a site plus
  email. Ships with stdlib-only Python helpers, nothing to install.

- **opencode-setup** — Install and configure the opencode coding harness:
  binary install, default model selection (free tier vs API-keyed), secure API
  key storage (0600 file, env-only at runtime), and a one-shot serve-API helper
  so the Muse routes code-writing through opencode instead of burning its own
  tokens.

- **automation-first** — Prefer scripts and classic automation over LLM calls
  for routine work. Classifies judgment vs routine, builds token-free watcher
  hooks that wake the agent only on change, and reserves the LLM for reasoning
  it's actually better at (like curating articles, not fetching them). Ships
  with a generic watcher template.

- **watch-hook** — Build token-free watcher hooks: a small script polls a
  source on a schedule, diffs against a state file, and wakes the agent only
  when something new appears. Zero LLM tokens on empty polls. The concrete
  implementation of automation-first. Ships with a configurable template and an
  annotated real-world example.

## Planned

(none yet — suggest one)

## Using a skill

Point your Muse at the skill directory (or paste the `SKILL.md`). It contains
everything needed: the workflow, the helper scripts, and the operating rules.
