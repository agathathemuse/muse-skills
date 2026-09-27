#!/usr/bin/env python3
"""Build newsletter HTML pages from a curated edition JSON.

Usage: build.py editions/2026-09-26.json [--editions-dir editions] [--site-dir site/news]
Writes <site-dir>/<date>/index.html and rebuilds <site-dir>/index.html (archive).
"""
import argparse
import html as htmllib, json, os, sys
from datetime import datetime

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{desc}">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&family=Outfit:wght@300..700&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box}}
  body{{background:#fdfdfb;color:#1c1c1f;font-family:'Outfit',system-ui,sans-serif;
       font-weight:300;margin:0;padding:0;line-height:1.7}}
  .wrap{{max-width:720px;margin:0 auto;padding:3.5rem 1.5rem 4rem}}
  .eyebrow{{font-size:.75rem;letter-spacing:.22em;text-transform:uppercase;
           color:#9a9aa2;margin-bottom:2.5rem;text-align:center}}
  .eyebrow a{{color:#9a9aa2;text-decoration:none}}
  .eyebrow a:hover{{color:#4a5aa8}}
  h1{{font-family:'Fraunces',serif;font-weight:500;font-size:clamp(2.4rem,8vw,3.6rem);
     line-height:1.05;margin:0 0 .6rem;letter-spacing:-.01em}}
  .tagline{{color:#6d6d76;font-size:1.1rem;margin:0 0 2.5rem}}
  section{{margin-bottom:2.6rem}}
  h2{{font-family:'Fraunces',serif;font-weight:500;font-size:1.5rem;margin:0 0 1rem;
     padding-bottom:.4rem;border-bottom:1px solid #eceae4}}
  .story{{background:#fff;border:1px solid #eceae4;border-radius:14px;
       padding:1.05rem 1.25rem;margin-bottom:.8rem}}
  .story a.t{{font-weight:500;font-size:1.02rem;color:#1c1c1f;text-decoration:none;line-height:1.45}}
  .story a.t:hover{{color:#4a5aa8}}
  .story .take{{margin:.35rem 0 0;color:#3d3d44;font-size:.95rem}}
  .story .src{{font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;color:#a5a5ad;margin-top:.45rem}}
  .ed{{display:flex;justify-content:space-between;align-items:baseline;
      padding:1rem 0;border-bottom:1px solid #eceae4}}
  .ed a{{font-family:'Fraunces',serif;font-size:1.15rem;color:#1c1c1f;text-decoration:none}}
  .ed a:hover{{color:#4a5aa8}}
  .ed .n{{color:#9a9aa2;font-size:.9rem}}
  footer{{margin-top:4rem;padding-top:1.5rem;border-top:1px solid #eceae4;
         color:#a5a5ad;font-size:.82rem;text-align:center}}
  footer a{{color:#a5a5ad}}
</style>
</head>
<body>
<div class="wrap">
  <p class="eyebrow"><a href="/muse/">lukehurd.com/muse</a></p>
"""

FOOT = """
  <footer>Curated by {curator} · {count} · <a href="{archive}">all editions</a></footer>
</div>
</body>
</html>
"""

def esc(s):
    return htmllib.escape(s or "")

# ---- Kindle (e-ink-first) rendering --------------------------------------
# Amazon's converter mangles complex CSS, so this stays deliberately plain:
# system serif, no web fonts, no flexbox, no background colors, simple block
# layout. Compact on purpose — generous spacing means one story per e-ink
# page. Text is left-aligned (justified text stretches awkwardly on e-ink).
# Links are kept but every story's take is written to stand alone, so tapping
# is optional, not required: the Kindle browser is painful on desktop sites.
KINDLE_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body{{font-family:Georgia,'Times New Roman',serif;color:#111111;
        line-height:1.5;margin:0;padding:.8em;text-align:left}}
  h1{{font-size:1.3em;line-height:1.2;margin:0 0 .1em}}
  .date{{color:#555555;margin:0 0 1em;font-size:.85em}}
  h2{{font-size:.95em;margin:1.1em 0 .35em;padding-bottom:.15em;
      border-bottom:1px solid #999999;text-transform:uppercase;
      letter-spacing:.06em}}
  .story{{margin:0 0 .9em}}
  .story .t{{font-weight:bold;font-size:.98em;line-height:1.35;margin:0}}
  .story .t a{{color:#111111;text-decoration:none}}
  .story .take{{margin:.2em 0;font-size:.92em}}
  .story .meta{{font-size:.78em;color:#555555;margin:0}}
  .story .meta a{{color:#1a4a8a}}
  footer{{margin-top:1.8em;border-top:1px solid #999999;padding-top:.6em;
         color:#555555;font-size:.8em}}
</style>
</head>
<body>
"""

def kindle_page(ed, args):
    date = ed["date"]
    dt = datetime.strptime(date, "%Y-%m-%d")
    datestr = dt.strftime("%A, %B %-d, %Y")
    total = sum(len(s["stories"]) for s in ed["sections"])
    parts = [KINDLE_HEAD.format(title=f"{args.title} {date}")]
    parts.append(f"  <h1>{esc(args.title)}</h1>\n"
                 f"  <p class=\"date\">{datestr} · {total} stories, curated by {esc(args.curator)}</p>\n")
    for sec in ed["sections"]:
        parts.append(f"  <h2>{esc(sec['name'])}</h2>\n")
        for st in sec["stories"]:
            parts.append(
                '  <div class="story">\n'
                f'    <p class="t"><a href="{esc(st["url"])}">{esc(st["title"])}</a></p>\n'
                f'    <p class="take">{esc(st["take"])}</p>\n'
                f'    <p class="meta">{esc(st["source"])} · <a href="{esc(st["url"])}">Read &rarr;</a></p>\n'
                '  </div>\n')
    parts.append(f"  <footer>Curated by {esc(args.curator)} · {total} stories · {esc(args.title)} {date}</footer>\n</body>\n</html>\n")
    return "".join(parts)

def edition_page(ed, args):
    date = ed["date"]
    dt = datetime.strptime(date, "%Y-%m-%d")
    datestr = dt.strftime("%A, %B %-d, %Y")
    total = sum(len(s["stories"]) for s in ed["sections"])
    head = HEAD.replace('href="/muse/"', f'href="{args.home_link}"', 1)
    parts = [head.format(
        title=f"Daily Tech Brief — {datestr}",
        desc=f"Curated tech news for {datestr}: AI, programming, gadgets, AR and more.")]
    parts.append(f"  <h1>Daily Tech Brief</h1>\n  <p class=\"tagline\">{datestr} · {total} stories, curated by Agatha</p>\n")
    for sec in ed["sections"]:
        parts.append(f"  <section>\n    <h2>{esc(sec['name'])}</h2>\n")
        for st in sec["stories"]:
            parts.append(
                '    <div class="story">\n'
                f'      <a class="t" href="{esc(st["url"])}">{esc(st["title"])}</a>\n'
                f'      <p class="take">{esc(st["take"])}</p>\n'
                f'      <div class="src">{esc(st["source"])}</div>\n'
                '    </div>\n')
        parts.append("  </section>\n")
    parts.append(foot(args, f"{total} stories"))
    return "".join(parts)

def archive_page(editions, args):
    head = HEAD.replace('href="/muse/"', f'href="{args.home_link}"', 1)
    parts = [head.format(title="Daily Tech Brief — Archive",
                         desc="Every edition of the daily tech news brief.")]
    parts.append("  <h1>Daily Tech Brief</h1>\n"
                 "  <p class=\"tagline\">Every edition, newest first.</p>\n  <section>\n")
    for date, total in editions:
        dt = datetime.strptime(date, "%Y-%m-%d")
        datestr = dt.strftime("%A, %B %-d, %Y")
        parts.append(
            f'    <div class="ed"><a href="{args.archive_path.rstrip("/")}/{date}/">{datestr}</a>'
            f'<span class="n">{total} stories</span></div>\n')
    parts.append("  </section>\n" + foot(args, f"{len(editions)} editions"))
    return "".join(parts)

def foot(args, count):
    return FOOT.format(curator=args.curator, archive=args.archive_path, count=count)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edition", help="curated edition JSON")
    ap.add_argument("--editions-dir", default="editions")
    ap.add_argument("--site-dir", default=os.path.join("site", "news"))
    ap.add_argument("--home-link", default="/",
                    help="link rendered in the page eyebrow (your site root)")
    ap.add_argument("--archive-path", default="/news/",
                    help="URL path of the archive index, for the footer link")
    ap.add_argument("--curator", default="your Muse",
                    help="name shown in the footer ('Curated by ...')")
    ap.add_argument("--title", default="Daily Brief",
                    help="newsletter title used in page <title> and the Kindle edition")
    ap.add_argument("--kindle", action="store_true",
                    help="print the e-ink-first Kindle HTML to stdout instead of "
                         "building the site (redirect it to a file and email it "
                         "as an attachment to the send-to-kindle address)")
    args = ap.parse_args()

    with open(args.edition) as f:
        ed = json.load(f)
    date = ed["date"]

    if args.kindle:
        # Print ONLY the Kindle HTML to stdout (the caller redirects it).
        sys.stdout.write(kindle_page(ed, args))
        return

    # Write edition page
    dest = os.path.join(args.site_dir, date)
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "index.html"), "w") as f:
        f.write(edition_page(ed, args))
    print("wrote", os.path.join(dest, "index.html"))

    # Rebuild archive from all edition JSONs
    editions = []
    for fn in sorted(os.listdir(args.editions_dir), reverse=True):
        if not fn.endswith(".json"):
            continue
        if fn.endswith(".enriched.json") or fn.endswith(".takes.json"):
            continue  # sidecars from enrich.py / summarize.py, not editions
        with open(os.path.join(args.editions_dir, fn)) as f:
            e = json.load(f)
        editions.append((e["date"], sum(len(s["stories"]) for s in e["sections"])))
    os.makedirs(args.site_dir, exist_ok=True)
    with open(os.path.join(args.site_dir, "index.html"), "w") as f:
        f.write(archive_page(editions, args))
    print("wrote", os.path.join(args.site_dir, "index.html"), f"({len(editions)} editions)")

if __name__ == "__main__":
    main()
