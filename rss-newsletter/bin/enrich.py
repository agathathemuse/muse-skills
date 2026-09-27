#!/usr/bin/env python3
"""enrich.py — best-effort article text extraction for the newsletter pipeline.

For each story URL in an edition JSON file, tries to download the article
and extract its main text with trafilatura (the same class of "reader mode"
extraction Firefox uses). Feed excerpts are usually 65-230 characters — this
is what gives the curator real material to write takes from. Polite by
design: a real browser user agent, a pause between requests, per-domain
spacing, and a disk cache so a URL is only ever fetched once.

Requires: pip install trafilatura (run in a venv — unlike fetch.py/build.py,
this script is NOT stdlib-only).

Usage:
    python enrich.py editions/2026-09-27.json [--max 25] [--refresh]

Writes editions/2026-09-27.enriched.json:
    {"<url>": {"status": "ok|blocked|failed", "chars": N, "text": "..."}}

Sites that block bots or sit behind paywalls come back as blocked/failed —
the curator falls back to the RSS summary for those. One failure never
stops the run. Note: trafilatura's own fetch_url ignores proxy env vars in
some environments; this script fetches with stdlib urllib (proxy-aware) and
uses trafilatura only for extract().
"""

import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from urllib.parse import urlparse

from trafilatura import extract

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "enrich")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0.0.0 Safari/537.36")
PAUSE_SECS = 1.5          # between any two requests
DOMAIN_GAP_SECS = 5.0     # per-domain minimum spacing
TIMEOUT = 25
MAX_BYTES = 3_000_000     # cap download size per article
MAX_CHARS = 12000         # cap stored text per article


def fetch_html(url):
    """Plain urllib fetch (proxy-aware). Returns html str or None."""
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        if r.status != 200:
            return None
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "html" not in ctype and "text" not in ctype:
            return None
        raw = r.read(MAX_BYTES)
    # detect charset simply
    charset = "utf-8"
    m = re.search(rb"charset=([\w-]+)", raw[:2000])
    if m:
        charset = m.group(1).decode("ascii", "ignore")
    return raw.decode(charset, "replace")


def cache_paths(url):
    h = hashlib.sha1(url.encode()).hexdigest()
    return (os.path.join(CACHE_DIR, h + ".json"), h)


def load_cached(url):
    p, _ = cache_paths(url)
    if os.path.exists(p):
        try:
            with open(p) as f:
                return json.load(f)
        except (OSError, ValueError):
            return None
    return None


def save_cached(url, record):
    p, _ = cache_paths(url)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(p, "w") as f:
        json.dump(record, f)


def enrich_url(url, last_domain_hit):
    """Returns (record, updated last_domain_hit)."""
    domain = urlparse(url).netloc.lower()
    now = time.time()
    wait = DOMAIN_GAP_SECS - (now - last_domain_hit.get(domain, 0))
    if wait > 0:
        time.sleep(wait)
    try:
        html = fetch_html(url)
    except Exception as e:  # network-level failure (HTTPError, URLError, timeout…)
        return {"status": "blocked", "error": f"fetch: {type(e).__name__}: {e}",
                "chars": 0, "text": ""}, last_domain_hit
    last_domain_hit[domain] = time.time()
    if not html:
        return {"status": "blocked", "error": "empty response (likely bot-blocked)",
                "chars": 0, "text": ""}, last_domain_hit
    try:
        text = extract(html, include_comments=False, favor_precision=True) or ""
    except Exception as e:
        return {"status": "failed", "error": f"extract: {type(e).__name__}",
                "chars": 0, "text": ""}, last_domain_hit
    text = text.strip()
    if len(text) < 300:
        return {"status": "blocked", "error": "no article body extracted",
                "chars": len(text), "text": ""}, last_domain_hit
    return {"status": "ok", "chars": len(text), "text": text[:MAX_CHARS]}, last_domain_hit


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)
    edition_path = args[0]
    max_n = 30
    refresh = False
    for a in sys.argv[1:]:
        if a.startswith("--max"):
            max_n = int(a.split("=")[1])
        if a == "--refresh":
            refresh = True

    with open(edition_path) as f:
        ed = json.load(f)

    stories = [st for sec in ed.get("sections", []) for st in sec.get("stories", [])]
    urls = []
    seen = set()
    for st in stories:
        u = st.get("url")
        if u and u not in seen:
            seen.add(u)
            urls.append(u)
    urls = urls[:max_n]

    out_path = os.path.splitext(edition_path)[0] + ".enriched.json"
    results = {}
    if os.path.exists(out_path) and not refresh:
        with open(out_path) as f:
            results = json.load(f)

    last_domain_hit = {}
    ok = blocked = failed = cached = 0
    for i, url in enumerate(urls):
        if url in results and not refresh:
            cached += 1
            continue
        if i > 0:
            time.sleep(PAUSE_SECS)
        rec, last_domain_hit = enrich_url(url, last_domain_hit)
        results[url] = rec
        if rec["status"] == "ok":
            ok += 1
            save_cached(url, rec)
        elif rec["status"] == "blocked":
            blocked += 1
        else:
            failed += 1
        print(f"[{i+1}/{len(urls)}] {rec['status']:7s} {rec['chars']:6d} chars  {url[:70]}",
              flush=True)

    with open(out_path, "w") as f:
        json.dump(results, f, indent=1)
    print(f"\nwrote {out_path}")
    print(f"ok={ok} blocked={blocked} failed={failed} cached={cached} "
          f"of {len(urls)} urls")


if __name__ == "__main__":
    main()
