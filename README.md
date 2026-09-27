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

## Planned

(none yet — suggest one)

## Using a skill

Point your Muse at the skill directory (or paste the `SKILL.md`). It contains
everything needed: the workflow, the helper scripts, and the operating rules.
