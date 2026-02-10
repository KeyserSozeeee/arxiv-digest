import json
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

from .storage import get_summary, put_summary

load_dotenv()
client = OpenAI()

MODEL = "gpt-5-mini"  # good quality/cost baseline


SYSTEM = """You summarize arXiv papers from title+abstract only.
Be precise, avoid hype, and do not invent details.
Return ONLY valid JSON with these keys:
tldr: string (1-2 sentences),
why: string (1-2 sentences, why it matters),
relevance: number 0-10 (to a general technical reader),
novelty: number 0-10 (how new/interesting),
keywords: array of 3-7 short strings
"""

def summarize_paper(paper_id: str, title: str, abstract: str) -> dict:
    cached = get_summary(paper_id)
    if cached:
        return cached

    inp = f"TITLE: {title}\n\nABSTRACT: {abstract}"

    resp = client.responses.create(
        model=MODEL,
        instructions=SYSTEM,
        input=inp,
    )

    text = resp.output_text.strip()
    data = json.loads(text)

    created_at = datetime.now(timezone.utc).isoformat()
    put_summary(
        paper_id=paper_id,
        model=MODEL,
        relevance=float(data["relevance"]),
        novelty=float(data["novelty"]),
        tldr=data["tldr"].strip(),
        why=data["why"].strip(),
        created_at=created_at,
    )

    # Return a normalized payload (includes cache fields)
    return {
        "paper_id": paper_id,
        "model": MODEL,
        "relevance": float(data["relevance"]),
        "novelty": float(data["novelty"]),
        "tldr": data["tldr"].strip(),
        "why": data["why"].strip(),
        "created_at": created_at,
        "keywords": data.get("keywords", []),
    }