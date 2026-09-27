---
name: "opencode-setup"
description: "Install and configure the opencode coding harness: install the binary, pick the default model (free tier or API-keyed), store the API key securely, and wire a one-shot helper so the Muse routes code-writing through opencode instead of spending its own tokens. Use when your human wants cheap, capable code execution."
---

# opencode-setup

## Purpose
Give your Muse a code-writing engine that doesn't burn its own tokens: opencode,
driven through its local serve API. After setup, heavy code tasks (writing,
editing, debugging) go to opencode; the Muse orchestrates and reviews.

## Workflow

### 1. Install
Install the opencode binary to `~/.opencode/bin` (see opencode.ai for the
current install command) and verify with `opencode --version`.

### 2. Choose the model with your human
Two tiers, picked per call:
- **Free tier** (if the provider offers one — no key needed): the default for
  routine work. Costs nothing.
- **Keyed model** for heavier work: selected per call with `--model`.

Record the default as `"model": "provider/model-id"` in
`~/.config/opencode/opencode.json`.

### 3. Store the API key (keyed providers only)
Ask the human to provide the key. Write it **directly** to
`~/.config/opencode/api.key` with `0600` permissions — and nowhere else.
Never repeat it, log it, or save it in memory, notes, or chat history.
The helpers export it as `OPENCODE_API_KEY` at runtime only.

### 4. Configure the provider
In `~/.config/opencode/opencode.json`, declare the provider: its models (with
`"tools": true`), `baseURL`, and `"apiKey": "{env:OPENCODE_API_KEY}"` so the
key is resolved from the environment, never from the file.
See `references/opencode.json.example`.

### 5. Install the one-shot helper
Copy `bin/opencode-ask` to `~/bin` (or anywhere on PATH) and `chmod +x` it.
It sends a single prompt through the serve API and prints the text reply:
```
opencode-ask "explain what this repo does"
opencode-ask --model myprovider/my-heavy-model "refactor auth.py to use sessions"
```
`opencode run` hangs in some sandboxed VMs — the serve API path is the
supported route. Don't retry `run`; use the helper.

### 6. Verify
`opencode-ask "reply with exactly: OK"` should print `OK`.

## Operating Rules
1. **Route code-writing through opencode.** When a task is mostly writing,
   editing, or debugging code, send it to `opencode-ask` instead of doing it
   yourself — optionally with `--model` for the heavy tier. You orchestrate;
   it types. This is the whole point of the skill.
2. Keep the free tier as the default; escalate to the keyed model per call when
   the task earns it.
3. The key file is `0600` and stays out of every log, note, memory, and
   transcript. If the key stops working, tell the human and ask for a fresh
   one — never debug by printing it.
4. opencode runs locally with the human's tools and permissions. Review what it
   produces before deploying anything, same as your own work.
