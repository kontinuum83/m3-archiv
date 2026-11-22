"""Letölti az M3 hírcsatornáját (RSS), és a feed.json fájlhoz adja az új műsorokat.
Minden új műsor megkapja a mai dátumot (first_seen), így az app feltöltési sorrendben tudja mutatni őket.
A GitHub Actions futtatja automatikusan, naponta többször."""
import datetime
import html
import json
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://nemzetiarchivum.hu/m3/rss"
FEED = pathlib.Path("feed.json")
MAX_ITEMS = 1000


def clean(text, limit=None):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def main():
    old = json.loads(FEED.read_text("utf-8")) if FEED.exists() else {"items": []}
    known = {(i["url"], i["title"]) for i in old["items"]}

    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0 (M3 archiv sajat app)"})
    root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())

    today = datetime.date.today().isoformat()
    new = []
    for it in root.iter("item"):
        title = clean(it.findtext("title"))
        url = (it.findtext("link") or "").strip()
        if not title or not url or (url, title) in known:
            continue
        new.append({
            "title": title,
            "url": url,
            "desc": clean(it.findtext("description"), 180),
            "first_seen": today,
            "type": "sorozat" if "series=" in url else "műsor",
        })
        known.add((url, title))

    if not new:
        print("Nincs új műsor.")
        return
    data = {"updated": today, "items": (new + old["items"])[:MAX_ITEMS]}
    FEED.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    print(f"{len(new)} új műsor hozzáadva.")


if __name__ == "__main__":
    main()
