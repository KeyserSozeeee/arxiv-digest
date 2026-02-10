import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import feedparser
import yaml

from arxiv_digest.summarize_free import summarize_paper_free
from arxiv_digest.render_html import render_digest_html
from arxiv_digest.emailer import send_email

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

    # Flags
    email_mode = "--email" in sys.argv
    ignore_seen = "--ignore-seen" in sys.argv  # testing: treat everything as new

    # Safety caps so emails don't get enormous
    email_cap = int(cfg.get("email_cap", 150))     # max papers included in email
    print_cap = int(cfg.get("print_cap", 50))      # max papers printed to console

    seen = set() if ignore_seen else load_seen()
    collected: List[Dict] = []

    for cat in categories:
        feed = feedparser.parse(rss_url(cat))

        if getattr(feed, "bozo", 0):
            print(f"[WARN] RSS parse issue for {cat}: {getattr(feed, 'bozo_exception', '')}")

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

    # De-dupe cross-lists
    deduped: Dict[str, Dict] = {}
    for item in collected:
        pid = item["id"]
        if pid not in deduped:
            deduped[pid] = item
        else:
            deduped[pid]["categories"].extend(item["categories"])

    papers = list(deduped.values())
    papers.sort(key=lambda x: x.get("published", ""), reverse=True)

    # Add free TL;DR/keywords for each (no filtering)
    for p in papers:
        cats = sorted(set(p["categories"]))
        s = summarize_paper_free(
            paper_id=p["id"],
            title=p["title"],
            abstract=p["abstract"],
            categories=cats,
            include_keywords=include_keywords,
        )
        p.update(
            {
                "relevance": s["relevance"],  # still computed; no longer used for filtering
                "novelty": s["novelty"],
                "tldr": s["tldr"],
                "why": s["why"],
                "keywords": s["keywords"],
            }
        )
        p["categories"] = cats

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n=== arXiv Digest (FREE) — {now} ===")
    print(f"New papers since last run: {len(papers)}\n")

    for p in papers[:print_cap]:
        authors = ", ".join(p["authors"][:6]) + (" et al." if len(p["authors"]) > 6 else "")
        print(f"- {p['title']}")
        print(f"  Categories: {', '.join(p['categories'])}")
        print(f"  Authors: {authors or 'N/A'}")
        print(f"  TL;DR: {p['tldr']}")
        print(f"  Abstract: {p['abs_url']}")
        print(f"  PDF:      {p['pdf_url']}\n")

    if email_mode:
        subject = f"arXiv Daily Digest — {len(papers)} new papers"
        html = render_digest_html(papers[:email_cap], generated_at_utc=now.replace(" UTC", ""))
        send_email(subject, html)
        print("[INFO] Email sent.")

    if not ignore_seen:
        save_seen(seen)


if __name__ == "__main__":
    main()