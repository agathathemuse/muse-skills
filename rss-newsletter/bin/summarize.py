#!/usr/bin/env python3
"""summarize.py — write newsletter takes via an off-meter one-shot model call.

The heavy reading (20 full article texts) and take drafting can be moved off
the worker's metered usage onto a free-tier model call. The worker only
curates from short RSS summaries and reviews the finished takes — the part
that genuinely needs its judgment.

Requires: editions/YYYY-MM-DD.enriched.json from enrich.py, and a one-shot
CLI that takes a prompt as its final argument and prints the model's reply
to stdout. opencode's free tier works well:
    ~/bin/opencode-ask --model opencode/muse-spark-1.3-contributor-free "prompt"
Set NEWSLETTER_SUMMARIZE_CMD to your command prefix, or pass --cmd.

Usage:
    python summarize.py editions/2026-09-27.json [--max 25]
           [--cmd "~/bin/opencode-ask --model opencode/muse-spark-1.3-contributor-free"]
           [--fetch-dir fetch]

Writes editions/2026-09-27.takes.json:
    {"<story url>": "<2-3 sentence take>"}

Exit code 0 on success (all takes present and non-empty), 1 on any failure —
the caller (daily worker) falls back to writing takes itself.
"""

import json
import os
import re
import shlex
import subprocess
import sys

TEXT_CHARS = 1500  # article text per story fed to the model
DEFAULT_CMD = os.environ.get(
    "NEWSLETTER_SUMMARIZE_CMD",
    os.path.expanduser("~/bin/opencode-ask") +
    " --model opencode/muse-spark-1.3-contributor-free")

INSTRUCTIONS = """You are writing summaries for a curated daily newsletter. \
For each story below, write a take of 2 to 3 sentences: what happened, the key \
detail or number, and why it matters. Each take must stand alone — some readers \
(e.g. on a Kindle) cannot easily open links, so the take must satisfy someone \
who never taps through. Voice: plain, direct, a little dry wit. Never write \
titles in the "word word *italic word*" pattern. Never invent details not \
present in the article text or RSS summary.

Output ONLY a JSON object mapping each story's number (as a string) to its take. \
No markdown fences, no commentary, no extra keys. Example: {"1": "Take one here.", "2": "Take two here."}
"""


def build_digest(ed, enr, fetch_items, max_n):
    stories = [st for sec in ed.get("sections", []) for st in sec.get("stories", [])][:max_n]
    fetch_by_link = {it.get("link"): it for it in fetch_items}
    blocks = []
    index_to_url = {}
    for i, st in enumerate(stories, 1):
        url = st.get("url", "")
        index_to_url[str(i)] = url
        e = enr.get(url, {})
        if e.get("status") == "ok" and e.get("text"):
            body = e["text"][:TEXT_CHARS].replace("\n", " ")
        else:
            f = fetch_by_link.get(url, {})
            body = "RSS SUMMARY ONLY (full article unavailable): " + (f.get("summary") or "no summary")
        blocks.append(
            f"[{i}] {st.get('title', '')} ({st.get('source', '')})\n"
            f"URL: {url}\nTEXT: {body}\n")
    return index_to_url, "\n".join(blocks)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)
    edition_path = args[0]
    max_n = 30
    cmd = DEFAULT_CMD
    fetch_dir = None
    i = 0
    argv = sys.argv[1:]
    while i < len(argv):
        a = argv[i]
        if a.startswith("--max="):
            max_n = int(a.split("=", 1)[1])
        elif a.startswith("--cmd="):
            cmd = a.split("=", 1)[1]
        elif a.startswith("--fetch-dir="):
            fetch_dir = a.split("=", 1)[1]
        i += 1
    if fetch_dir is None:
        # default: sibling "fetch/" of the editions dir's parent (…/editions, …/fetch)
        fetch_dir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(edition_path))), "fetch")

    with open(edition_path) as f:
        ed = json.load(f)
    date = ed.get("date", "unknown")
    enr_path = os.path.splitext(edition_path)[0] + ".enriched.json"
    with open(enr_path) as f:
        enr = json.load(f)
    fetch_items = []
    fetch_path = os.path.join(fetch_dir, f"{date}.json")
    if os.path.exists(fetch_path):
        with open(fetch_path) as f:
            fetch_items = json.load(f).get("items", [])

    index_to_url, digest = build_digest(ed, enr, fetch_items, max_n)
    n = len(index_to_url)
    if n == 0:
        print("no stories found", file=sys.stderr)
        sys.exit(1)

    prompt = INSTRUCTIONS + "\nSTORIES:\n" + digest
    print(f"sending {n} stories ({len(prompt)} chars) to one-shot model…", flush=True)
    try:
        r = subprocess.run(shlex.split(cmd) + [prompt],
                           capture_output=True, text=True, timeout=600)
    except Exception as e:
        print(f"one-shot call failed: {e}", file=sys.stderr)
        sys.exit(1)
    if r.returncode != 0:
        print(f"one-shot rc={r.returncode}: {(r.stderr or '')[:300]}", file=sys.stderr)
        sys.exit(1)

    raw = (r.stdout or "").strip()
    # strip markdown fences if the model added them despite instructions
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        print(f"no JSON object in model output: {raw[:300]}", file=sys.stderr)
        sys.exit(1)
    try:
        takes = json.loads(m.group(0))
    except ValueError as e:
        print(f"JSON parse failed: {e}: {raw[:300]}", file=sys.stderr)
        sys.exit(1)

    missing = [k for k in index_to_url if not (takes.get(k) or "").strip()]
    if missing:
        print(f"missing/empty takes for stories: {missing}", file=sys.stderr)
        sys.exit(1)

    out = {index_to_url[k]: takes[k].strip() for k in index_to_url}
    takes_path = os.path.splitext(edition_path)[0] + ".takes.json"
    with open(takes_path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {takes_path} ({len(out)} takes)")


if __name__ == "__main__":
    main()
