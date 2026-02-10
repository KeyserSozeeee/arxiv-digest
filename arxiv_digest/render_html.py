from datetime import datetime
from html import escape
from typing import List, Dict


def render_digest_html(items: List[Dict], generated_at_utc: str) -> str:
    rows = []
    for p in items:
        title = escape(p["title"])
        abs_url = escape(p["abs_url"])
        pdf_url = escape(p["pdf_url"])
        cats = ", ".join(sorted(set(p.get("categories", []))))
        cats = escape(cats)
        authors = ", ".join(p.get("authors", [])[:8])
        authors = escape(authors)
        tldr = escape(p.get("tldr", ""))
        why = escape(p.get("why", ""))
        score = float(p.get("relevance", 0.0))

        rows.append(f"""
        <div style="padding:14px 0;border-bottom:1px solid #e5e7eb;">
          <div style="font-size:16px;font-weight:700;line-height:1.25;margin:0 0 6px 0;">
            <a href="{abs_url}" style="color:#111827;text-decoration:none;">{title}</a>
          </div>
          <div style="font-size:13px;color:#374151;margin:0 0 8px 0;">
            <b>Score:</b> {score:.1f} &nbsp;|&nbsp;
            <b>Categories:</b> {cats} &nbsp;|&nbsp;
            <b>Authors:</b> {authors}
          </div>
          <div style="font-size:14px;color:#111827;margin:0 0 6px 0;"><b>TL;DR:</b> {tldr}</div>
          <div style="font-size:14px;color:#111827;margin:0 0 10px 0;"><b>Why:</b> {why}</div>
          <div style="font-size:13px;">
            <a href="{abs_url}">Abstract</a> &nbsp;|&nbsp; <a href="{pdf_url}">PDF</a>
          </div>
        </div>
        """)

    body = "\n".join(rows) if rows else "<p>No new interesting papers today.</p>"

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
</head>
<body style="font-family:Segoe UI, Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color:#111827;">
  <div style="margin-bottom:16px;">
    <h2 style="margin:0 0 6px 0;">Daily arXiv Digest</h2>
    <div style="color:#6b7280;font-size:13px;">Generated: {escape(generated_at_utc)} UTC</div>
  </div>
  {body}
</body>
</html>"""