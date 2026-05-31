#!/usr/bin/env python3
"""
Polls a list of RSS feeds and writes the latest items to feeds.json.
GitHub Actions runs this automatically (see .github/workflows/poll.yml).

The ONLY part you edit is the FEEDS block below. Each source is one line:
    ("Source name", "https://example.com/feed"),
Keep the parentheses, quotes, and trailing comma. A line starting with #
is switched off. Group sources under a section name in quotes.
"""
import json
import feedparser
from datetime import datetime, timezone

FEEDS = {
    "Substack": [
        ("Dr. Aaron Judkins",        "https://aaronjudkins.substack.com/feed"),
        ("Stranger Theology",        "https://strangertheology.substack.com/feed"),
        ("Humble Theology",          "https://humbletheology.muddamalle.com/feed"),
        ("The News Block",           "https://thenewsblock.substack.com/feed"),
        ("Giants, Gods & Dragons",   "https://gilberthouse.substack.com/feed"),
        ("Predictable",              "https://predictable.substack.com/feed"),
        ("Mind Over Markets",        "https://mindovermarkets.substack.com/feed"),
        # Prophecy Watchers was in the source list but no feed URL was pulled.
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
        ("CNN - US",            "http://rss.cnn.com/rss/edition_us.rss"),
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
        ("CCN - Crypto",      "https://www.ccn.com/rss-feeds/crypto/"),
        ("CCN - Crypto News", "https://www.ccn.com/news/crypto-news/feeds/"),
        ("CCN - Analysis",    "https://www.ccn.com/analysis/crypto-analysis/feeds/"),
        ("CCN - Technology",  "https://www.ccn.com/rss-feeds/technology/"),
        ("Disruption Banking","https://www.disruptionbanking.com/feed/"),
        ("24/7 Wall St",      "https://247wallst.com/feed/"),
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
        ("One Foot Down",       "https://www.onefootdown.com/rss/index.xml"),
        # Podcast (audio) feeds - episodes, not articles:
        ("ND Podcast (Simplecast)", "https://feeds.simplecast.com/PiDvYqUW"),
        ("ND Podcast (Libsyn)",     "https://rss.libsyn.com/shows/99576/destinations/521650.xml"),
    ],
    "Fantasy": [
        ("RotoViz", "https://www.rotoviz.com/feed/"),
    ],
}

ITEMS_PER_FEED = 8   # how many recent posts to keep per source


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
            d = feedparser.parse(url)
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
