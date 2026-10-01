"""Lesbare Darstellung bestehender Recherchetexte, ohne Daten umzuschreiben."""
import json
import re

from markupsafe import Markup, escape


def inline_text(value):
    # Quelltexte sind nicht vertrauenswürdig. Nur selbst erzeugte Tags zulassen.
    text = str(escape(value))
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)
    return text


def text_blocks(value):
    output, paragraph, items = [], [], []
    def flush():
        if paragraph:
            output.append("<p>" + "<br>".join(inline_text(line) for line in paragraph) + "</p>")
            paragraph.clear()
        if items:
            output.append("<ul>" + "".join("<li>" + inline_text(item) + "</li>" for item in items) + "</ul>")
            items.clear()
    for line in value.splitlines():
        line = line.strip()
        bullet = re.match(r"^(?:[-*•]\s+|\d+[.)]\s+)(.*)", line)
        heading = re.match(r"^#{1,6}\s+(.+)", line)
        if not line:
            flush()
        elif heading:
            flush()
            output.append("<h4>" + inline_text(heading.group(1)) + "</h4>")
        elif bullet:
            if paragraph:
                flush()
            items.append(bullet.group(1))
        else:
            if items:
                flush()
            paragraph.append(line)
    flush()
    return Markup("".join(output))


def present_research(notes, product_fit_json):
    fits = []
    try:
        raw = json.loads(product_fit_json or "[]")
    except (TypeError, ValueError):
        raw = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                score = max(0, min(100, int(item.get("score", 0))))
            except (TypeError, ValueError, OverflowError):
                continue
            matches = item.get("matches", [])
            fits.append({"label": str(item.get("label") or item.get("product") or "Produkt"), "score": score,
                         "priority": "Sehr gute Passung" if score >= 70 else "Interessant" if score >= 45 else "Beobachten" if score >= 20 else "Nicht priorisiert",
                         "matches": [v for v in matches if isinstance(v, str)] if isinstance(matches, list) else []})
    fits.sort(key=lambda item: item["score"], reverse=True)
    sections, lines = [], []
    title = "Zusammenfassung und Notizen"
    labels = {"produkt-fit": "Produktbewertungen", "produktbewertungen": "Produktbewertungen", "beobachtungen": "Beobachtungen", "gesprächshypothese": "Gesprächshypothese", "zusammenfassung": "Zusammenfassung"}
    def flush():
        content = "\n".join(lines).strip()
        if content and not (fits and title == "Produktbewertungen"):
            sections.append({"title": title, "html": text_blocks(content)})
        lines.clear()
    for line in (notes or "").splitlines():
        candidate = re.sub(r"^#{1,6}\s*", "", line.strip()).strip("* :").lower()
        if candidate in labels:
            flush()
            title = labels[candidate]
        else:
            lines.append(line)
    flush()
    return {"sections": sections, "fits": fits}
