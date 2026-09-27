#!/usr/bin/env python3
"""Fetch RSS/Atom feeds, keep recent items, dedupe, emit JSON.

Usage: fetch.py [--feeds feeds.json] [--days N] [--out DIR]
feeds.json: [{"name": "...", "url": "...", "topics": ["..."]}, ...]
Writes fetch/YYYY-MM-DD.json under --out. Stdlib only.
"""
import argparse, concurrent.futures, datetime, html, json, os, re, time
import urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

UA = {"User-Agent": "Mozilla/5.0 (RSSNewsletterSkill/1.0)"}

def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return html.unescape(re.sub(r"\s+", " ", s)).strip()

def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        return parsedate_to_datetime(s)
    except Exception:
        pass
    try:  # ISO 8601
        iso = s.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        return None

def text(el, names):
    for n in names:
        c = el.find(n)
        if c is not None and c.text and c.text.strip():
            return c.text.strip()
    return ""

def fetch_feed(feed):
    name, url = feed["name"], feed["url"]
    raw = None
    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                raw = r.read(8_000_000)
            break
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    if raw is None:
        return name, url, [], f"fetch error: {last_err}"
    try:
        root = ET.fromstring(raw)
    except Exception:
        # Tolerant fallback: truncate to the last complete </item> or </entry>
        # (some feeds ship malformed trailing XML, e.g. unclosed CDATA).
        txt = raw.decode("utf-8", "replace")
        cut = max(txt.rfind("</item>"), txt.rfind("</entry>"))
        if cut == -1:
            return name, url, [], "parse error: malformed XML"
        tail = "</channel></rss>" if "</item>" in txt[max(0, cut-7):cut+7] else "</feed>"
        try:
            root = ET.fromstring((txt[:cut] + tail).encode("utf-8"))
        except Exception as e:
            return name, url, [], f"parse error: {e} (tolerant retry failed)"
    items = []
    tag = root.tag.lower()
    if tag.endswith("rss") or root.find("channel") is not None:
        for it in root.findall("./channel/item"):
            link = text(it, ["link"]) or ""
            if not link:
                g = it.find("guid")
                if g is not None and g.text and g.text.strip().startswith("http"):
                    link = g.text.strip()
            items.append({
                "title": strip_tags(text(it, ["title"])),
                "link": link,
                "published": parse_date(text(it, ["pubDate", "{http://purl.org/dc/elements/1.1/}date"])),
                "summary": strip_tags(text(it, ["description"]))[:600],
                "source": name,
            })
    elif tag.endswith("feed"):  # Atom
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for en in root.findall("a:entry", ns) or root.findall("entry"):
            link = ""
            for l in en.findall("a:link", ns) or en.findall("link"):
                href = (l.get("href") or "").strip()
                rel = l.get("rel", "alternate")
                if href and rel in ("alternate", None):
                    link = href
                    break
            items.append({
                "title": strip_tags(text(en, ["a:title", "title"])),
                "link": link,
                "published": parse_date(text(en, ["a:published", "a:updated", "published", "updated"])),
                "summary": strip_tags(text(en, ["a:summary", "summary", "a:content", "content"]))[:600],
                "source": name,
            })
    else:
        return name, url, [], f"unknown format: {root.tag}"
    return name, url, items, None

def norm_link(link):
    link = (link or "").strip().lower()
    link = re.sub(r"[?#].*$", "", link).rstrip("/")
    return link

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feeds", default="feeds.json", help="path to feeds.json")
    ap.add_argument("--days", type=float, default=1.5)
    ap.add_argument("--out", default="fetch")
    args = ap.parse_args()

    with open(args.feeds) as f:
        feeds = json.load(f)

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=args.days)
    all_items, errors, seen = [], [], set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(fetch_feed, feeds))

    for name, url, items, err in results:
        if err:
            errors.append({"feed": name, "error": err})
            continue
        kept = 0
        for it in items:
            if not it["title"] or not it["link"]:
                continue
            nl = norm_link(it["link"])
            if nl in seen:
                continue
            seen.add(nl)
            pub = it["published"]
            if pub is not None and pub < cutoff:
                continue
            it["published"] = pub.isoformat() if pub else None
            all_items.append(it)
            kept += 1
        print(f"{name}: {len(items)} items, {kept} recent", flush=True)

    all_items.sort(key=lambda i: i["published"] or "", reverse=True)
    os.makedirs(args.out, exist_ok=True)
    day = datetime.datetime.now().strftime("%Y-%m-%d")
    out = os.path.join(args.out, f"{day}.json")
    payload = {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "window_days": args.days,
        "item_count": len(all_items),
        "errors": errors,
        "items": all_items,
    }
    with open(out, "w") as f:
        json.dump(payload, f, indent=1)
    print(f"WROTE {out} ({len(all_items)} items, {len(errors)} feed errors)")

if __name__ == "__main__":
    main()
