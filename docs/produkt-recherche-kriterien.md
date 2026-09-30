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

## Automatische Kandidatensuche

Der Server führt zusätzlich automatisch eine öffentliche Websuche für alle vier Produkte aus. Pro Suchlauf werden passende neue Domains als CRM-Firmen mit `research_status=pending` angelegt und an den Hintergrund-Worker übergeben. Der Worker ruft die öffentliche Website ab, erstellt die KI-Zusammenfassung und berechnet anschließend den Produkt-Fit für AboroDesk, ABoroLMS, CloudShare und HelpDesk.

Der Suchlauf ist als `aborodesk-prospect-discovery.timer` eingerichtet:

- Start 15 Minuten nach dem Serverstart
- danach standardmäßig alle 12 Stunden
- maximal zwei Treffer je Suchanfrage, damit das CRM nicht unkontrolliert wächst
- Dubletten werden über Domain und vorhandene CRM-Firmen vermieden
- kein automatischer E-Mail-Versand; jeder Kandidat bleibt vor Kontaktaufnahme prüfpflichtig

Manueller Testlauf auf dem Server:

```bash
sudo systemctl start aborodesk-prospect-discovery.service
sudo journalctl -u aborodesk-prospect-discovery.service -n 100 --no-pager
```

Status prüfen:

```bash
sudo systemctl status aborodesk-prospect-discovery.timer
sudo systemctl list-timers aborodesk-prospect-discovery.timer
```
