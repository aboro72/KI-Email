"""Findet öffentlich auffindbare Firmen und reiht sie zur CRM-KI-Recherche ein."""

from __future__ import annotations

import os
import re
import sys
import base64
from html.parser import HTMLParser
from html import unescape
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select

from app.db import Base, SessionLocal, engine, initialize_persistence
from app.jobs import enqueue
from app.models import Company
from app.prospect_scoring import score_products
from app.prospect_criteria import DEFAULTS, load_criteria, exclusion_reason, germany_evidence, website_evidence

DEFAULT_QUERIES = DEFAULTS["queries"]
BLOCKED_HOSTS = {
    "google.com", "google.de", "googleusercontent.com", "bing.com", "duckduckgo.com",
    "facebook.com", "instagram.com", "linkedin.com", "youtube.com", "wikipedia.org",
    "destatis.de", "unternehmensregister.de", "dasoertliche.de", "11880.com",
    "gelbeseiten.de", "yelp.de", "tripadvisor.de", "kununu.com", "xing.com",
    "indeed.com", "stepstone.de", "northdata.de", "firmenwissen.de", "werliefertwas.de",
    "wlw.de", "meinestadt.de", "news.bbc.co.uk", "bbc.com", "bbc.co.uk",
    "tiktok.com", "dailymotion.com", "soundcloud.com", "pinterest.com", "zhihu.com",
    "kleinanzeigen.de", "duden.de", "reddit.com", "firmania.de",
    "defirmenkataloge.com",
}
MAX_PAGE_BYTES = 300_000
MIN_PRODUCT_SCORE = 20


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.in_heading = False
        self.entries = []
        self.active_href = ""
        self.active_text = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "h2":
            self.in_heading = True
        if tag.lower() == "a":
            attributes = dict(attrs)
            href = attributes.get("href", "")
            if href and (self.in_heading or "result__a" in attributes.get("class", "").split()):
                self.links.append(href)
                self.active_href = href
                self.active_text = ""

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.active_href:
            self.entries.append((self.active_href, self.active_text))
            self.active_href = ""
        if tag.lower() == "h2":
            self.in_heading = False

    def handle_data(self, data):
        if self.active_href:
            self.active_text += data + " "


def relevant_result(query, title, url):
    words = re.findall(r"[a-zäöüß]+", query.lower().split(" -")[0])
    stems = [word[:7] for word in words if len(word) >= 5 and word not in {"deutschland", "kleine", "kleines", "unternehmen", "online"}]
    evidence = unescape(title + " " + url).lower()
    return bool(stems) and any(stem in evidence for stem in stems)


def search(query: str, limit: int) -> list[str]:
    results = []
    for search_url in ("https://html.duckduckgo.com/html/?kl=de-de&q=" + quote_plus(query), "https://www.bing.com/search?cc=de&mkt=de-DE&q=" + quote_plus(query)):
        request = Request(search_url, headers={"User-Agent": "Mozilla/5.0 AboroDesk-ProspectResearch/1.0"})
        try:
            with urlopen(request, timeout=20) as response:
                html = response.read(1_500_000).decode("utf-8", errors="ignore")
        except Exception:
            continue
        parser = LinkParser()
        parser.feed(html)
        for href, title in parser.entries:
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
            if not relevant_result(query, title, target):
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


def page_product_fit(url: str, config=None) -> tuple[int, list[str]]:
    """Prüft die Startseite vor dem CRM-Eintrag gegen die Produktkriterien."""
    config = config or DEFAULTS
    reason = exclusion_reason(url, "", config)
    if reason:
        raise ValueError(reason)
    text, legal_text, final_url = website_evidence(url)
    reason = exclusion_reason(final_url, text, config)
    if reason:
        raise ValueError(reason)
    if not germany_evidence(legal_text or text):
        raise ValueError("Deutscher Firmensitz nicht belegt")
    reason = exclusion_reason(final_url, text + " " + legal_text, config)
    if reason:
        raise ValueError(reason)
    fits = score_products(text)
    best = int(fits[0]["score"]) if fits else 0
    labels = [str(item["label"]) for item in fits if int(item["score"]) >= config["min_score"]]
    return best, labels


def main() -> int:
    Base.metadata.create_all(engine)
    initialize_persistence()
    with SessionLocal() as settings_db:
        config = load_criteria(settings_db)
    max_per_query = config["per_query"]
    dry_run = os.getenv("PROSPECT_DISCOVERY_DRY_RUN", "0") == "1"
    candidates: list[tuple[str, str]] = []
    for product, queries in config["queries"].items():
        for query in queries:
            try:
                market_query = query if "deutschland" in query.lower() else query + " Deutschland"
                urls = search(market_query + " -Softwarehersteller -Microsoft -SAP", max_per_query)
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
                best_score, matching_products = page_product_fit(url, config)
            except Exception as exc:
                print(f"SKIP {domain}: {str(exc) if isinstance(exc, ValueError) else type(exc).__name__}")
                continue
            if best_score < config["min_score"]:
                print(f"SKIP {domain}: kein ausreichender Produkt-Fit")
                continue
            seen.add(domain)
            if dry_run:
                print(f"DRY-RUN {name} {url}")
                continue
            company = Company(name=name, domain=domain, website=url, source_url=url, research_status="pending", notes=f"Automatische Websuche; deutscher Firmensitz im Impressum geprüft. Passende Angebote: {', '.join(matching_products)}. Vor Kontaktaufnahme und Registerabgleich prüfen.")
            db.add(company)
            db.flush()
            enqueue(db, "crm.company_research", {"company_id": company.id})
            known_domains.add(domain)
            created += 1
        print(f"Neue CRM-Kandidaten: {created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
