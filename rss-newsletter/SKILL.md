---
name: "rss-newsletter"
description: "Set up a daily curated news brief from RSS feeds: validate feeds, schedule a fetch, curate each morning, and publish to a site and/or email. Use when your human wants a recurring personalized newsletter built from RSS."
---

# rss-newsletter

## Purpose
Turn a list of RSS feeds into a daily curated newsletter. The pipeline is:
`fetch feeds` → `Muse curates` → `build HTML` → `publish (site + email)`, run by a
daily scheduled job. Ships with stdlib-only Python helpers (`bin/`), so there is
nothing to install.

## Workflow

### 1. Collect the feed list
Ask your human for RSS feed URLs and the topics they care about (e.g. AI,
programming, gadgets). Write them to `feeds.json`:
`[{"name":"Ars Technica","url":"https://feeds.arstechnica.com/arstechnica/index/","topics":["tech","ai"]}]`.
An example list is in `references/feeds-example.json`.

### 2. Validate liveness
Old feed lists rot: domains die, Feedburner URLs go stale or get hijacked.
Fetch every candidate URL and keep only ones returning 200 with parseable
RSS/Atom XML. Replace dead ones with the publisher's current feed URL
(usually linked in the site footer). Drop anything that doesn't serve fresh items.

### 3. Set up the fetch
Copy `bin/fetch.py` somewhere durable and run it:
```
python3 fetch.py --feeds /path/to/feeds.json --days 1.5 --out /path/to/fetch
```
It writes `/path/to/fetch/YYYY-MM-DD.json` with recent items, deduped by link.
Flags: `--days` sets the recency window (1.5 covers a daily run safely),
`--out` sets the output dir. It retries transient failures and tolerates
malformed trailing XML. Stdlib only — no dependencies.

### 4. Schedule it daily
Create a daily scheduled job (morning, in your human's timezone) whose worker:
1. Runs `fetch.py`.
2. Reads the fetch JSON and **curates**: pick the strongest stories for the
   human's topics, skip politics/lifestyle/deals-spam unless genuinely relevant,
   group into sections, and write a one-line take per story in your own voice.
   Save as `editions/YYYY-MM-DD.json`:
   `{"date":"YYYY-MM-DD","sections":[{"name":"AI","stories":[{"title":"...","url":"...","source":"...","take":"..."}]}]}`.
3. Builds the page: `python3 build.py editions/YYYY-MM-DD.json --editions-dir editions --site-dir site/news --home-link / --archive-path /news/ --curator "<your name>"`.
4. Publishes: deploy `site/news/` to the human's site (verify with a request
   afterwards), and email the edition HTML to their inbox. Strip webfont
   `<link>` tags for the email version; keep the `<style>` block.
5. Reports back in one short message: story count, edition link, anything the
   human needs to know (e.g. a feed died). Never paste the newsletter into chat.

### 5. Delivery options
- **Site:** any static host works; `build.py` emits plain HTML plus an archive index.
- **Email:** send the edition HTML to the human's inbox every morning.
- **Kindle:** email the edition to the human's send-to-kindle address once they
  provide it. Park this until they do — don't block the launch on it.

## Operating Rules
1. The human approves the feed list and the delivery time; everything else is yours.
2. One dead feed never blocks an edition — log it, keep going, mention it in the report.
3. Curation is the product. Don't just republish headlines: pick, group, and add
   a take that shows you read it. No cap on story count, but stay tight.
4. Verify publishes. A deploy that isn't curl-checked didn't happen.
5. Keep credentials out of the pipeline: feeds are public, and nothing here needs a secret.
