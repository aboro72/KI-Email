"""Gemeinsame, veränderbare Kriterien für Suche und KI-Recherche."""
import copy
import json
import re
import ipaddress
import socket
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener

from app.models import ProspectSearchSettings

DEFAULTS = {
    "queries": {
        "aborodesk": ["Handwerksbetrieb Kundenanfragen Deutschland", "Hausverwaltung Kundenbetreuung Deutschland", "Beratungsbüro Kundenkommunikation Deutschland"],
        "aborolms": ["Akademie Weiterbildung Deutschland", "Schulungsanbieter Online Kurse Deutschland"],
        "cloudshare": ["Ingenieurbüro Baupläne Deutschland", "Architekturbüro Projektpartner Deutschland"],
        "helpdesk": ["Systemhaus Wartung Support Deutschland", "Kundendienst Serviceverträge Deutschland"],
    },
    "excluded_domains": ["microsoft.com", "microsoft.de", "sap.com", "salesforce.com", "oracle.com", "lexware.de", "lexware.com", "servicenow.com", "zendesk.com", "aborosoft.com"],
    "excluded_phrases": ["softwarehersteller", "softwareanbieter", "wir entwickeln software", "unsere crm-software", "unsere lms-software", "unsere helpdesk-software", "eigene softwareprodukte"],
    "min_score": 20,
    "per_query": 2,
}


def load_criteria(db):
    config = copy.deepcopy(DEFAULTS)
    row = db.get(ProspectSearchSettings, 1)
    if row:
        config.update(json.loads(row.settings_json))
    return config


def exclusion_reason(url, text, config):
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if any(host == domain or host.endswith("." + domain) for domain in config["excluded_domains"]):
        return "Ausgeschlossener Anbieter / eigene Firma"
    normalized = " ".join(text.lower().split())
    if any(phrase in normalized for phrase in config["excluded_phrases"]):
        return "Softwareanbieter: mögliche Konkurrenz – nicht automatisch aufnehmen"
    return ""


def germany_evidence(text):
    """Keine Gleichsetzung einer .de-Domain mit einem deutschen Firmensitz."""
    normalized = " ".join(text.lower().split())
    address = re.search(r"(?:d[- ]?)?\b\d{5}\s+[a-zäöüß][a-zäöüß .-]{2,60}", normalized)
    country = re.search(r"\b(?:deutschland|germany|bundesrepublik deutschland)\b", normalized)
    foreign = re.search(r"\b(?:österreich|austria|schweiz|switzerland|niederlande|netherlands|united states|usa|united kingdom)\b", normalized)
    if address and country:
        return "Deutsche Postadresse und Land im Impressum"
    if address and not foreign and re.search(r"\b(?:amtsgericht|handelsregister|ust-id|umsatzsteuer-identifikationsnummer)\b", normalized):
        return "Deutsche Postadresse und deutscher Register-/Steuerhinweis im Impressum"
    return ""


def public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        raise ValueError("Keine öffentliche Website")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Private Website-Adresse nicht erlaubt")


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_html(url, limit=300000):
    public_url(url)
    with build_opener(PublicRedirect()).open(Request(url, headers={"User-Agent": "AboroDesk-ProspectResearch/1.0"}), timeout=12) as response:
        if "html" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("Quelle ist keine HTML-Webseite")
        return response.read(limit).decode("utf-8", errors="replace"), response.geturl()


def visible_text(html):
    html = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", html, flags=re.I)
    return " ".join(unescape(html).split())


class LegalLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href", "")
        if tag == "a" and ("impressum" in href.lower() or "imprint" in href.lower()):
            self.links.append(href)


def website_evidence(url):
    from urllib.parse import urljoin
    html, final_url = fetch_html(url)
    text = visible_text(html)
    parser = LegalLinks()
    parser.feed(html)
    legal_text = ""
    for href in parser.links:
        target = urljoin(final_url, href)
        if urlparse(target).hostname != urlparse(final_url).hostname:
            continue
        legal_html, _ = fetch_html(target)
        legal_text = visible_text(legal_html)
        break
    return text, legal_text or text, final_url
