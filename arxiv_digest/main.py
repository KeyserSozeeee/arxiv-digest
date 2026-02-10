import json
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import yaml

STATE_FILE = Path("seen.json")


def load_config() -> dict:
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seen() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_seen(seen: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(sorted(seen), indent=2), encoding="utf-8")


def rss_url(category: str) -> str:
    return f"https://rss.arxiv.org/rss/{category}"


def normalize_entry(entry: dict) -> dict:
    abs_url = (entry.get("link") or "").strip()
    title = " ".join((entry.get("title") or "").split())
    published = entry.get("published") or entry.get("updated") or ""
    summary = " ".join((entry.get("summary") or "").split())

    authors = []
    if "authors" in entry:
        authors = [a.get("name", "").strip() for a in entry["authors"] if a.get("name")]

    pdf_url = abs_url.replace("/abs/", "/pdf/")
    if abs_url and not pdf_url.endswith(".pdf"):
        pdf_url += ".pdf"

    return {
        "id": abs_url,
        "title": title,
        "authors": authors,
        "published": published,
        "summary": summary,
        "abs_url": abs_url,
        "pdf_url": pdf_url,
    }


def main():
    cfg = load_config()
    categories = cfg.get("feeds", [])
    max_items = int(cfg.get("max_items_per_feed", 50))

    seen = load_seen()
    new_items: list[dict] = []

    for cat in categories:
        url = rss_url(cat)
        feed = feedparser.parse(url)

        if getattr(feed, "bozo", 0):
            print(f"[WARN] Feed parse issue for {cat}: {getattr(feed, 'bozo_exception', '')}")

        entries = getattr(feed, "entries", [])[:max_items]
        for e in entries:
            item = normalize_entry(e)
            if not item["id"]:
                continue
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            item["category"] = cat
            new_items.append(item)

    # De-dupe across categories (cross-lists) by abs URL
    deduped: dict[str, dict] = {}
    for it in new_items:
        if it["id"] not in deduped:
            deduped[it["id"]] = it
        else:
            prev = deduped[it["id"]]
            prev_cats = setAWAIT = set([prev.get("category")] + prev.get("categories", []))
            prev_cats.add(it.get("category"))
            prev["categories"] = sorted(c for c in prev_cats if c)

    final_items = list(deduped.values())
    final_items.sort(key=lambda x: x.get("published", ""), reverse=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n=== arXiv Digest (new since last run) — {now} ===")
    print(f"New unique papers: {len(final_items)}\n")

    for it in final_items[:200]:
        cats = it.get("categories") or [it.get("category")]
        authors = ", ".join(it["authors"][:6]) + (" et al." if len(it["authors"]) > 6 else "")
        print(f"- {it['title']}")
        print(f"  Authors: {authors or 'N/A'}")
        print(f"  Categories: {', '.join(cats)}")
        print(f"  Abstract: {it['abs_url']}")
        print(f"  PDF:      {it['pdf_url']}\n")

    save_seen(seen)


if __name__ == "__main__":
    main()