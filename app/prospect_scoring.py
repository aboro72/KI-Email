"""Produktübergreifende Bewertung öffentlich recherchierter Firmen."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ProductProfile:
    key: str
    label: str
    keywords: tuple[str, ...]
    bonus_keywords: tuple[str, ...]


PRODUCT_PROFILES = (
    ProductProfile(
        "aborodesk",
        "AboroDesk",
        ("crm", "kundenservice", "kundenkommunikation", "aufgaben", "automatisierung", "e-mail", "email", "vertrieb"),
        ("kundenportal", "wiedervorlage", "workflow", "mehrere standorte", "serviceprozess"),
    ),
    ProductProfile(
        "aborolms",
        "ABoroLMS",
        ("lms", "learning management", "weiterbildung", "schulung", "schulungen", "kurse", "prüfung", "prüfungen", "zertifikat", "zertifikate", "zertifikaten", "akademie"),
        ("lernplattform", "teilnehmer", "lernende", "trainer", "prüfer", "online-kurse", "online", "e-learning"),
    ),
    ProductProfile(
        "cloudshare",
        "CloudShare",
        ("dateiaustausch", "dokumentenaustausch", "dateifreigabe", "cloud", "kundenportal", "partnerportal", "große dateien"),
        ("zugriffsrechte", "sensible dokumente", "externe partner", "mehrere standorte", "versionschaos", "sicher teilen", "sicherem dokumentenaustausch"),
    ),
    ProductProfile(
        "helpdesk",
        "HelpDesk",
        ("helpdesk", "ticketsystem", "ticket", "it-support", "kundensupport", "support-team", "kundenservice", "serviceanfragen"),
        ("sla", "eskalation", "eskalationen", "reaktionszeit", "lösungszeit", "serviceverträge", "technische hotline", "wissensdatenbank"),
    ),
)


def _contains(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)", text) is not None


def score_products(text: str) -> list[dict[str, object]]:
    """Gibt je Produkt Score, Treffer und eine verständliche Einordnung zurück."""
    normalized = " ".join(text.lower().split())
    results = []
    for profile in PRODUCT_PROFILES:
        matches = [item for item in profile.keywords if _contains(normalized, item)]
        bonus = [item for item in profile.bonus_keywords if _contains(normalized, item)]
        score = min(100, len(matches) * 15 + len(bonus) * 10)
        if score >= 70:
            priority = "sehr_gut"
        elif score >= 45:
            priority = "interessant"
        elif score >= 20:
            priority = "beobachten"
        else:
            priority = "nicht_priorisieren"
        results.append({"product": profile.key, "label": profile.label, "score": score, "priority": priority, "matches": matches + bonus})
    return sorted(results, key=lambda item: int(item["score"]), reverse=True)
