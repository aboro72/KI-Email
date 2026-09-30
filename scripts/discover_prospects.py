"""Findet öffentlich auffindbare Firmen und reiht sie zur CRM-KI-Recherche ein."""

from __future__ import annotations

import os
import re
import sys
import base64
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select

from app.db import Base, SessionLocal, engine, initialize_persistence
from app.jobs import enqueue
from app.models import Company
from app.prospect_scoring import score_products

DEFAULT_QUERIES = {
    "aborodesk": ["KMU Kundenservice CRM Automatisierung Deutschland", "Dienstleister Kundenkommunikation Support Team Deutschland"],
    "aborolms": ["Weiterbildungsanbieter Online Kurse Prüfungen Zertifikate Deutschland", "Akademie E-Learning Schulungen Unternehmen Deutschland"],
    "cloudshare": ["Unternehmen sicherer Dokumentenaustausch Kunden Partner Deutschland", "Ingenieurbüro Kundenportal Dateifreigabe Deutschland"],
    "helpdesk": ["IT Dienstleister Ticketsystem SLA Support Deutschland", "Softwarehaus Kundensupport Helpdesk Serviceverträge Deutschland"],
}
BLOCKED_HOSTS = {
    "google.com", "google.de", "googleusercontent.com", "bing.com", "duckduckgo.com",
    "facebook.com", "instagram.com", "linkedin.com", "youtube.com", "wikipedia.org",
    "destatis.de", "unternehmensregister.de", "dasoertliche.de", "11880.com",
    "gelbeseiten.de", "yelp.de", "tripadvisor.de", "kununu.com", "xing.com",
    "indeed.com", "stepstone.de", "northdata.de", "firmenwissen.de", "werliefertwas.de",
    "wlw.de", "meinestadt.de", "news.bbc.co.uk", "bbc.com", "bbc.co.uk",
}
MAX_PAGE_BYTES = 300_000
MIN_PRODUCT_SCORE = 20


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href", "")
            if href:
                self.links.append(href)


def search(query: str, limit: int) -> list[str]:
    results = []
    for search_url in ("https://html.duckduckgo.com/html/?q=" + quote_plus(query), "https://www.bing.com/search?q=" + quote_plus(query)):
        request = Request(search_url, headers={"User-Agent": "Mozilla/5.0 AboroDesk-ProspectResearch/1.0"})
        with urlopen(request, timeout=20) as response:
            html = response.read(1_500_000).decode("utf-8", errors="ignore")
        parser = LinkParser()
        parser.feed(html)
        for href in parser.links:
            target = parse_qs(urlparse("https:" + href).query).get("uddg", [""])[0] if href.startswith("//duckduckgo.com/l/?") else href
            if "bing.com/ck/a" in target:
                encoded = parse_qs(urlparse(target).query).get("u", [""])[0]
                if encoded.startswith("a1"):
                    try:
                        target = base64.urlsafe_b64decode(encoded[2:] + "===").decode("utf-8", errors="ignore")
                    except Exception:
                        target = ""
            parsed = urlparse(target)
            host = (parsed.hostname or "").lower().removeprefix("www.")
            if parsed.scheme not in {"http", "https"} or not host or any(host == blocked or host.endswith("." + blocked) for blocked in BLOCKED_HOSTS):
                continue
            normalized = f"https://{host}/"
            if normalized not in results:
                results.append(normalized)
            if len(results) >= limit:
                return results
        if results:
            break
    return results


def domain_name(url: str) -> tuple[str, str]:
    host = (urlparse(url).hostname or "").removeprefix("www.")
    name = re.sub(r"[-_.]+", " ", host.split(".")[0]).strip().title() or host
    return name[:240], host[:255]


def visible_text(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", html, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def page_product_fit(url: str) -> tuple[int, list[str]]:
    """Prüft die Startseite vor dem CRM-Eintrag gegen die Produktkriterien."""
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 AboroDesk-ProspectResearch/1.0"})
    with urlopen(request, timeout=10) as response:
        html = response.read(MAX_PAGE_BYTES).decode("utf-8", errors="ignore")
    fits = score_products(visible_text(html))
    best = int(fits[0]["score"]) if fits else 0
    labels = [str(item["label"]) for item in fits if int(item["score"]) >= MIN_PRODUCT_SCORE]
    return best, labels


def main() -> int:
    Base.metadata.create_all(engine)
    initialize_persistence()
    max_per_query = max(1, int(os.getenv("PROSPECTS_PER_QUERY", "5")))
    dry_run = os.getenv("PROSPECT_DISCOVERY_DRY_RUN", "0") == "1"
    candidates: list[tuple[str, str]] = []
    for product, queries in DEFAULT_QUERIES.items():
        for query in queries:
            try:
                urls = search(query, max_per_query)
                print(f"{product}: {query} -> {len(urls)} Treffer")
                candidates.extend((product, url) for url in urls)
            except Exception as exc:
                print(f"WARNUNG Suche fehlgeschlagen ({product}): {type(exc).__name__}", file=sys.stderr)
    with SessionLocal() as db:
        known_domains = {item.lower() for item in db.scalars(select(Company.domain)).all() if item}
        seen = set()
        created = 0
        for product, url in candidates:
            name, domain = domain_name(url)
            if domain in seen or domain in known_domains or domain == "aborosoft.com":
                continue
            try:
                best_score, matching_products = page_product_fit(url)
            except Exception as exc:
                print(f"SKIP {domain}: Website nicht prüfbar ({type(exc).__name__})")
                continue
            if best_score < MIN_PRODUCT_SCORE:
                print(f"SKIP {domain}: kein ausreichender Produkt-Fit")
                continue
            seen.add(domain)
            if dry_run:
                print(f"DRY-RUN {name} {url}")
                continue
            company = Company(name=name, domain=domain, website=url, source_url="Automatische Websuche", research_status="pending", notes=f"Automatisch als Recherche-Kandidat gefunden ({', '.join(matching_products)}); vor Kontaktaufnahme prüfen.")
            db.add(company)
            db.flush()
            enqueue(db, "crm.company_research", {"company_id": company.id})
            known_domains.add(domain)
            created += 1
        print(f"Neue CRM-Kandidaten: {created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
