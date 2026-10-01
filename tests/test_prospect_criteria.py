import copy
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import ProspectSearchSettings
from app.prospect_criteria import DEFAULTS, exclusion_reason, germany_evidence, load_criteria, website_evidence
from app.prospect_scoring import score_products
from scripts.discover_prospects import LinkParser, page_product_fit, relevant_result


def test_germany_needs_address_not_just_domain_or_keyword():
    assert not germany_evidence("Wir liefern nach Deutschland")
    assert not germany_evidence("12345 New York USA")
    assert germany_evidence("Impressum Musterstraße 1, 12345 Berlin Deutschland")
    assert germany_evidence("Impressum Musterstraße 1, 12345 Berlin Amtsgericht Berlin HRB 123")


def test_competitor_not_software_customer():
    assert exclusion_reason("https://office.microsoft.com", "", DEFAULTS)
    assert exclusion_reason("https://example.de", "Wir entwickeln Software und unsere CRM-Software", DEFAULTS)
    assert not exclusion_reason("https://systemhaus.de", "Microsoft Partner für Wartung und IT-Support", DEFAULTS)
    custom = copy.deepcopy(DEFAULTS)
    custom["excluded_phrases"].append("eigene lernplattform")
    assert exclusion_reason("https://example.de", "Unsere eigene Lernplattform", custom)


def test_small_business_fit():
    assert score_products("Ingenieurbüro")[0]["score"] == 20
    assert score_products("Hausverwaltung")[0]["product"] == "aborodesk"
    scores = score_products("Handwerksbetrieb: Kundenanfragen, Angebotserstellung und Terminvereinbarung")
    assert scores[0]["product"] == "aborodesk"
    assert scores[0]["score"] >= 20
    scores = score_products("Architekturbüro Planungsbüro Baupläne")
    assert scores[0]["product"] == "cloudshare"


def test_search_settings_persist():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        assert load_criteria(db)["queries"]["aborodesk"]
        custom = copy.deepcopy(DEFAULTS)
        custom["queries"]["aborodesk"] = ["Handwerk Berlin"]
        db.add(ProspectSearchSettings(id=1, settings_json=json.dumps(custom)))
        db.commit()
    with Session(engine) as db:
        assert load_criteria(db)["queries"]["aborodesk"] == ["Handwerk Berlin"]
        assert DEFAULTS["queries"]["aborodesk"] != ["Handwerk Berlin"]


def test_only_result_links():
    parser = LinkParser()
    parser.feed('<a href="https://irrelevant.de">Menu</a><h2><a href="https://firma.de">Firma</a></h2><a class="result__a" href="https://betrieb.de">Betrieb</a>')
    assert parser.links == ["https://firma.de", "https://betrieb.de"]
    assert parser.entries == [("https://firma.de", "Firma "), ("https://betrieb.de", "Betrieb ")]


def test_irrelevant_search_response():
    assert not relevant_result("Handwerksbetrieb Kundenanfragen Deutschland -Microsoft", "Pinterest", "https://pinterest.com")
    assert not relevant_result("Handwerksbetrieb Berlin", "Mehrwertsteuerrechner", "https://rechner.de")
    assert relevant_result("Ingenieurbüro Baupläne Deutschland", "Planungsbüro und Ingenieurbüro", "https://firma.de")


def test_impressum_and_redirect_host(monkeypatch):
    from app import prospect_criteria
    pages = {
        "https://firma.de": ('<a href="/impressum">Impressum</a> Handwerksbetrieb Kundenanfragen', "https://www.firma.de/"),
        "https://www.firma.de/impressum": ("12345 Berlin Deutschland", "https://www.firma.de/impressum"),
    }
    monkeypatch.setattr(prospect_criteria, "fetch_html", lambda url: pages[url])
    text, legal, url = website_evidence("https://firma.de")
    assert germany_evidence(legal)
    assert url == "https://www.firma.de/"


def test_discovery_rejects_foreign_site(monkeypatch):
    import pytest
    from scripts import discover_prospects
    monkeypatch.setattr(discover_prospects, "website_evidence", lambda url: ("Handwerksbetrieb Kundenanfragen", "Wien Österreich", url))
    with pytest.raises(ValueError, match="Firmensitz"):
        page_product_fit("https://example.de")
