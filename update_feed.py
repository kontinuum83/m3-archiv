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


def key(title):
    """A cím egyszerűsített alakja: kisbetű, írásjelek nélkül. Így a
    "Família Kft. – 196." és a "Família Kft. 196." ugyanannak számít."""
    return re.sub(r"[\W_]+", " ", title.lower()).strip()


def dedupe(items):
    """Ugyanaz a műsor csak egyszer maradjon meg (az első, vagyis a legújabb)."""
    seen, out = set(), []
    for i in items:
        k = key(i["title"])
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out


def main():
    old = json.loads(FEED.read_text("utf-8")) if FEED.exists() else {"items": []}
    old_items = dedupe(old["items"])
    by_key = {key(i["title"]): i for i in old_items}
    changed = len(old_items) != len(old["items"])

    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0 (M3 archiv sajat app)"})
    root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())

    today = datetime.date.today().isoformat()
    new = []
    for it in root.iter("item"):
        title = clean(it.findtext("title"))
        url = (it.findtext("link") or "").strip()
        if not title or not url:
            continue
        k = key(title)
        if k in by_key:
            # Már ismert műsor: csak a linkjét frissítjük (az ?id= linkek változnak).
            if by_key[k]["url"] != url:
                by_key[k]["url"] = url
                changed = True
            continue
        item = {
            "title": title,
            "url": url,
            "desc": clean(it.findtext("description"), 180),
            "first_seen": today,
            "type": "sorozat" if "series=" in url else "műsor",
        }
        new.append(item)
        by_key[k] = item

    if not new and not changed:
        print("Nincs új műsor.")
        return
    data = {"updated": today, "items": (new + old_items)[:MAX_ITEMS]}
    FEED.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    print(f"{len(new)} új műsor hozzáadva, {len(old['items']) - len(old_items)} duplikátum törölve.")


if __name__ == "__main__":
    main()
