#!/usr/bin/env python3
"""
Polls a list of RSS feeds and writes the latest items to feeds.json.
GitHub Actions runs this automatically (see .github/workflows/poll.yml).

The ONLY part you edit is the FEEDS block below. Each source is one line:
    ("Source name", "https://example.com/feed"),
Keep the parentheses, quotes, and trailing comma. A line starting with #
is switched off. Group sources under a section name in quotes.

Substack blocks GitHub's servers (403), so Substack feeds are routed through
the AllOrigins proxy automatically. Any feed whose URL contains a domain in
PROXY_DOMAINS gets proxied; everything else is fetched directly.
"""
import json
import gzip
import zlib
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import feedparser

FEEDS = {
    "Substack": [
        ("Dr. Aaron Judkins",        "https://aaronjudkins.substack.com/feed"),
        ("Stranger Theology",        "https://strangertheology.substack.com/feed"),
        ("Humble Theology",          "https://humbletheology.muddamalle.com/feed"),
        ("The News Block",           "https://thenewsblock.substack.com/feed"),
        ("Giants, Gods & Dragons",   "https://gilberthouse.substack.com/feed"),
        ("Predictable",              "https://predictable.substack.com/feed"),
        ("Mind Over Markets",        "https://mindovermarkets.substack.com/feed"),
        # ("Prophecy Watchers",      "https://prophecywatchers.substack.com/feed"),
    ],
    "Right Lane": [
        ("Daily Wire",     "https://www.dailywire.com/feeds/rss.xml"),
        ("The Federalist", "https://thefederalist.com/feed/"),
        ("The Blaze",      "https://www.theblaze.com/feeds/feed.rss"),
        ("Just the News",  "https://justthenews.com/rss.xml"),
    ],
    "General News": [
        ("Fox News - Latest",   "https://moxie.foxnews.com/google-publisher/latest.xml"),
        ("Fox News - World",    "https://moxie.foxnews.com/google-publisher/world.xml"),
        ("Fox News - Politics", "https://moxie.foxnews.com/google-publisher/politics.xml"),
        ("Fox News - Science",  "https://moxie.foxnews.com/google-publisher/science.xml"),
        ("Fox News - Sports",   "https://moxie.foxnews.com/google-publisher/sports.xml"),
        ("Fox News - Tech",     "https://moxie.foxnews.com/google-publisher/tech.xml"),
        ("NBC News",            "https://feeds.nbcnews.com/nbcnews/public/news"),
    ],
    "Crypto": [
        ("Cointelegraph",     "https://cointelegraph.com/rss"),
        ("Decrypt",           "https://decrypt.co/feed"),
        ("CoinGape",          "https://coingape.com/feed"),
        ("Coinpedia",         "https://coinpedia.org/news/feed"),
        ("Crypto Briefing",   "https://cryptobriefing.com/feed"),
        ("CryptoPotato",      "https://cryptopotato.com/feed"),
        ("CoinDesk",          "https://www.coindesk.com/arc/outboundfeeds/rss"),
        ("The Block",         "https://www.theblock.co/rss.xml"),
        ("Bitcoin Magazine",  "https://bitcoinmagazine.com/feed"),
        ("NewsBTC",           "https://www.newsbtc.com/feed/"),
        ("Disruption Banking","https://www.disruptionbanking.com/feed/"),
        ("24/7 Wall St",      "https://247wallst.com/feed/"),
        # CCN feeds removed - their XML has a malformed entity that won't parse.
    ],
    "Bears": [
        ("Windy City Gridiron", "https://www.windycitygridiron.com/rss/index.xml"),
        ("Chicago Bears HQ",    "https://feeds.feedburner.com/ChicagoBearsHQ-news-updates"),
        ("SB Nation NFL",       "https://www.sbnation.com/rss/nfl/index.xml"),
        ("PFF",                 "https://www.pff.com/feed"),
        ("PFF - Bears (team 6)","https://www.pff.com/feed/teams/6"),
        ("ChicagoBears.com",    "https://www.chicagobears.com/rss/news"),
        ("All CHGO",            "https://allchgo.com/feed/"),
    ],
    "Notre Dame": [
        ("One Foot Down",           "https://www.onefootdown.com/rss/index.xml"),
        ("ND Podcast (Simplecast)", "https://feeds.simplecast.com/PiDvYqUW"),
        ("ND Podcast (Libsyn)",     "https://rss.libsyn.com/shows/99576/destinations/521650.xml"),
    ],
    "Fantasy": [
        ("RotoViz", "https://www.rotoviz.com/feed/"),
    ],
}

ITEMS_PER_FEED = 8

# Feeds whose host contains any of these get routed through AllOrigins,
# because the host blocks GitHub's datacenter IPs with a 403.
PROXY_DOMAINS = ("substack.com",)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def needs_proxy(url):
    return any(dom in url for dom in PROXY_DOMAINS)


def proxied(url):
    return "https://api.allorigins.win/raw?url=" + urllib.parse.quote(url, safe="")


def fetch_bytes(url):
    """Fetch with a browser UA, decompress gzip/deflate. Returns bytes."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
    if "gzip" in enc:
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    elif "deflate" in enc:
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw


def get_feed(url):
    """Fetch + parse one feed, using the proxy when required, with one retry."""
    target = proxied(url) if needs_proxy(url) else url
    last_err = None
    for attempt in range(2):
        try:
            data = fetch_bytes(target)
            d = feedparser.parse(data)
            if d.entries or not d.bozo:
                return d
            last_err = d.bozo_exception
        except Exception as ex:
            last_err = ex
        time.sleep(2)
    # Final fallback: let feedparser fetch the original directly.
    d = feedparser.parse(url)
    if not d.entries and last_err and not d.bozo:
        d.bozo = 1
        d.bozo_exception = last_err
    return d


def iso_date(entry):
    if entry.get("published_parsed"):
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
    return ""


out = {"generated_utc": datetime.now(timezone.utc).isoformat(), "sections": {}}

for section, sources in FEEDS.items():
    out["sections"][section] = []
    for name, url in sources:
        record = {"source": name, "feed": url, "posts": [], "error": ""}
        try:
            d = get_feed(url)
            if d.bozo and not d.entries:
                record["error"] = "could not parse feed (%s)" % d.bozo_exception
            for e in d.entries[:ITEMS_PER_FEED]:
                record["posts"].append({
                    "title": e.get("title", ""),
                    "url": e.get("link", ""),
                    "pubDate": e.get("published", ""),
                    "pubDate_iso": iso_date(e),
                })
        except Exception as ex:
            record["error"] = str(ex)
        out["sections"][section].append(record)

with open("feeds.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print("wrote feeds.json")
