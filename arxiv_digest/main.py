import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import feedparser
import yaml

from arxiv_digest.summarize_free import summarize_paper_free

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


def normalize_entry(entry: dict) -> Dict:
    abs_url = (entry.get("link") or "").strip()
    title = " ".join((entry.get("title") or "").split())
    published = entry.get("published") or entry.get("updated") or ""
    abstract = " ".join((entry.get("summary") or "").split())

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
        "abstract": abstract,
        "abs_url": abs_url,
        "pdf_url": pdf_url,
    }


def main() -> None:
    cfg = load_config()
    categories: List[str] = cfg.get("feeds", [])
    max_items = int(cfg.get("max_items_per_feed", 50))
    include_keywords = cfg.get("include_keywords", [])
    threshold = float(cfg.get("threshold", 3.5))

    seen = load_seen()
    collected: List[Dict] = []

    for cat in categories:
        feed = feedparser.parse(rss_url(cat))
        entries = getattr(feed, "entries", [])[:max_items]

        for e in entries:
            item = normalize_entry(e)
            if not item["id"]:
                continue
            if item["id"] in seen:
                continue

            seen.add(item["id"])
            item["categories"] = [cat]
            collected.append(item)

    # De-dupe cross-lists by paper id (abs url)
    deduped: Dict[str, Dict] = {}
    for item in collected:
        pid = item["id"]
        if pid not in deduped:
            deduped[pid] = item
        else:
            deduped[pid]["categories"].extend(item["categories"])

    papers = list(deduped.values())
    papers.sort(key=lambda x: x.get("published", ""), reverse=True)

    scored: List[Dict] = []
    for p in papers:
        s = summarize_paper_free(
            paper_id=p["id"],
            title=p["title"],
            abstract=p["abstract"],
            categories=list(sorted(set(p["categories"]))),
            include_keywords=include_keywords,
        )
        p.update({
            "relevance": s["relevance"],
            "novelty": s["novelty"],
            "tldr": s["tldr"],
            "why": s["why"],
            "keywords": s["keywords"],
        })
        scored.append(p)

    interesting = [p for p in scored if p["relevance"] >= threshold]
    interesting.sort(key=lambda x: (x["relevance"], x["novelty"]), reverse=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n=== arXiv Digest (FREE) — {now} ===")
    print(f"New papers since last run: {len(papers)}")
    print(f"Interesting (score ≥ {threshold}): {len(interesting)}\n")

    for p in interesting[:50]:
        authors = ", ".join(p["authors"][:6]) + (" et al." if len(p["authors"]) > 6 else "")
        print(f"- {p['title']}")
        print(f"  Score: {p['relevance']:.1f}")
        print(f"  TL;DR: {p['tldr']}")
        print(f"  Why:   {p['why']}")
        print(f"  Keywords: {', '.join(p['keywords'])}")
        print(f"  Authors: {authors or 'N/A'}")
        print(f"  Categories: {', '.join(sorted(set(p['categories'])))}")
        print(f"  Abstract: {p['abs_url']}")
        print(f"  PDF:      {p['pdf_url']}\n")

    save_seen(seen)


if __name__ == "__main__":
    main()