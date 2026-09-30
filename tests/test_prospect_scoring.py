from app.prospect_scoring import score_products


def test_company_can_match_multiple_products():
    results = score_products("IT-Support und Kundensupport mit Ticketsystem, SLA, Eskalationen, Serviceverträge und sicherem Dokumentenaustausch für Kunden")
    by_product = {item["product"]: item for item in results}
    assert by_product["helpdesk"]["score"] >= 70
    assert by_product["cloudshare"]["score"] >= 20


def test_lms_signals_prioritize_learning_product():
    results = score_products("Akademie für berufliche Weiterbildung mit Online-Kursen, Prüfungen und Zertifikaten")
    assert results[0]["product"] == "aborolms"
    assert results[0]["priority"] == "sehr_gut"
