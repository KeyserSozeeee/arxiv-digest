import re
from typing import Dict, List


def _split_sentences(text: str) -> List[str]:
    text = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _keywords(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    tokens = [t for t in text.split() if 4 <= len(t) <= 20]
    stop = {
        "this", "that", "with", "from", "have", "were", "their", "there", "which", "using",
        "results", "paper", "study", "show", "shows", "shown", "based", "approach", "method",
        "methods", "model", "models", "data", "analysis", "system", "systems", "also", "into",
        "between", "over", "under", "both", "such", "these", "those", "than", "then", "when",
        "where", "while", "within", "without", "via", "per", "new", "novel", "work"
    }
    tokens = [t for t in tokens if t not in stop]
    freq = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    return [k for k, _ in sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:6]]


def score_relevance(title: str, abstract: str, categories: List[str], include_keywords: List[str]) -> float:
    hay = (title + " " + abstract).lower()
    score = 0.0

    for kw in include_keywords:
        if kw.lower() in hay:
            score += 2.0

    cat_boost = {
        "quant-ph": 1.0,
        "gr-qc": 1.0,
        "astro-ph": 0.8,
        "math-ph": 0.8,
        "hep-ex": 0.6,
        "cond-mat": 0.6,
        "nucl-th": 0.6,
        "nucl-ex": 0.5,
        "physics": 0.5,
        "math": 0.5,
        "stat": 0.4,
        "q-bio": 0.4,
        "econ": 0.3,
        "cs": 0.7,
    }
    for c in categories:
        score += cat_boost.get(c, 0.3)

    return max(0.0, min(10.0, score))


def summarize_paper_free(paper_id: str, title: str, abstract: str, categories: List[str], include_keywords: List[str]) -> Dict:
    sents = _split_sentences(abstract)
    tldr = " ".join(sents[:2]) if sents else abstract.strip()
    kws = _keywords(title + " " + abstract)

    relevance = score_relevance(title, abstract, categories, include_keywords)
    novelty = 5.0
    why = "Selected based on your categories/keywords match (rule-based)."

    return {
        "paper_id": paper_id,
        "model": "free-heuristic",
        "relevance": float(relevance),
        "novelty": float(novelty),
        "tldr": tldr[:600],
        "why": why,
        "keywords": kws,
    }