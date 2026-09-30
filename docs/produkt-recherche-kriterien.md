# Produktübergreifende Firmenrecherche

Die automatische Recherche bewertet Firmen nicht nur für AboroDesk, sondern getrennt für alle vier Produkte:

- AboroDesk: E-Mail-Arbeitsplatz, CRM, Aufgaben, Marketing und Automatisierung
- ABoroLMS: Kurse, Lernpfade, Prüfungen und Zertifikate
- CloudShare: sicherer Dokumenten- und Dateiaustausch
- HelpDesk: Tickets, Support, SLA und Eskalationen

Eine Firma kann mehrere passende Produkte erhalten. Das CRM soll deshalb nicht nur einen Gesamtwert, sondern eine Produktbewertung mit Treffern, Begründung und nächster Aktion speichern.

## Produkt-Fit

| Produkt | Gute Signale auf der Webseite | Typische Zielkunden |
|---|---|---|
| AboroDesk | CRM, Kundenkommunikation, Aufgaben, Automatisierung, Vertrieb, Workflows | KMU, Dienstleister, Agenturen, Unternehmen mit vielen E-Mails und Kundenprozessen |
| ABoroLMS | Weiterbildung, Schulungen, Kurse, Prüfungen, Zertifikate, E-Learning | Akademien, Bildungsträger, Verbände, interne Unternehmensakademien |
| CloudShare | Dateifreigabe, Dokumentenaustausch, Kunden-/Partnerportal, Zugriffsrechte | Beratungen, Ingenieurbüros, IT-Dienstleister, Firmen mit sensiblen externen Dokumenten |
| HelpDesk | Ticketsystem, IT-Support, Kundensupport, SLA, Eskalation, Serviceverträge | IT-Dienstleister, Softwarehäuser, technische Servicebetriebe, Supportteams |

## Bewertung

Jedes Signal erhöht den Produktwert. Kernbegriffe zählen stärker als allgemeine Begriffe; zusätzliche Hinweise wie SLA, Zertifikate, Zugriffsrechte oder Kundenportal erhöhen die Priorität. Die KI muss immer die gefundenen Textstellen bzw. Begriffe nennen und darf keine nicht belegten Funktionen oder Bedürfnisse erfinden.

Prioritäten:

- 70–100: sehr guter Kandidat
- 45–69: interessant, manuell prüfen
- 20–44: beobachten
- 0–19: zunächst nicht priorisieren

## CRM-Ablauf

1. Firma öffentlich recherchieren
2. Dublette über Domain und normalisierte Firmenbezeichnung prüfen
3. Firma mit `research_status=pending` eintragen
4. Produkt-Fit für alle vier Produkte berechnen
5. KI-Zusammenfassung, Begründung und nächste Aktion speichern
6. Bei mindestens einem starken Produkt-Fit einen Lead vorschlagen
7. Vor jeder Kontaktaufnahme menschliche Prüfung verlangen

ABoroOffice wird in dieser Recherche nicht als Zielprodukt verwendet.
