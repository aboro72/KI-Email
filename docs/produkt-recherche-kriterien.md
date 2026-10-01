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
| HelpDesk | Ticketsystem, IT-Support, Kundensupport, SLA, Eskalation, Serviceverträge | IT-Systemhäuser ohne konkurrierende Eigenprodukte, technische Servicebetriebe, Supportteams |

## Bewertung

Jedes Signal erhöht den Produktwert. Kernbegriffe zählen stärker als allgemeine Begriffe; zusätzliche Hinweise wie SLA, Zertifikate, Zugriffsrechte oder Kundenportal erhöhen die Priorität. Die KI muss immer die gefundenen Textstellen bzw. Begriffe nennen und darf keine nicht belegten Funktionen oder Bedürfnisse erfinden.

Prioritäten:

- 70–100: sehr guter Kandidat
- 45–69: interessant, manuell prüfen
- 20–44: beobachten
- 0–19: zunächst nicht priorisieren

## CRM-Ablauf

1. Firma öffentlich recherchieren
2. Dublette über Domain prüfen (Firmenname und Konzernzugehörigkeit weiterhin manuell prüfen)
3. Firma mit `research_status=pending` eintragen
4. Produkt-Fit für alle vier Produkte berechnen
5. KI-Zusammenfassung, Begründung und nächste Aktion speichern
6. KI-Gesprächsentwurf zum passenden Produkt als Lead speichern, sofern die KI einen Entwurf liefert
7. Vor jeder Kontaktaufnahme menschliche Prüfung verlangen

ABoroOffice wird in dieser Recherche nicht als Zielprodukt verwendet.

## Automatische Kandidatensuche

Der Server führt zusätzlich automatisch eine öffentliche Websuche für alle vier Produkte aus. Pro Suchlauf werden passende neue Domains als CRM-Firmen mit `research_status=pending` angelegt und an den Hintergrund-Worker übergeben. Der Worker ruft die öffentliche Website ab, erstellt die KI-Zusammenfassung und berechnet anschließend den Produkt-Fit für AboroDesk, ABoroLMS, CloudShare und HelpDesk.

Der Suchlauf ist als `aborodesk-prospect-discovery.timer` eingerichtet:

- Start 15 Minuten nach dem Serverstart
- danach standardmäßig alle 12 Stunden
- standardmäßig zwei Treffer je Suchanfrage, in der Kriterienseite einstellbar (1–10)
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

## Anpassung vom 01.10.2026: Deutschland und kleine Betriebe

Unter **CRM → Suchkriterien** (`/crm/research-settings`) lassen sich Suchanfragen pro Produkt, ausgeschlossene Domains und Formulierungen, Mindestscore sowie Trefferzahl bearbeiten. Eine Suchanfrage pro Zeile; ein leerer Produktbereich deaktiviert dessen Suche. Die Einstellungen liegen in MongoDB/SQL in `prospect_search_settings`, nicht in einem Benutzerbrowser. Änderungen gelten für den nächsten Suchlauf und werden im Auditprotokoll dokumentiert. Deutschland bleibt fest vorgegeben. Zugriff benötigt `CRM_MANAGE`.

- Keine Mindestgröße: Handwerk, Hausverwaltungen, Beratungs-, Ingenieur- und Architekturbüros sowie kleine Akademien und Systemhäuser werden berücksichtigt.
- Ein belegter kleiner Betriebstyp (z. B. Ingenieurbüro oder Hausverwaltung) reicht für 20 Punkte und damit die niedrigste Prüfpriorität. Das ist eine Gesprächshypothese, kein belegter Softwarebedarf; zusätzliche Aufgaben-/Prozesssignale erhöhen die Wertung.
- AboroDesk, AboroLMS, CloudShare und Helpdesk sind gleichwertige Angebote; keine pauschale LMS-Priorisierung mehr.
- Neue Kandidaten brauchen Hinweise auf eine deutsche Postadresse und Land bzw. deutsche Register-/Steuerangaben im Impressum. `.de` allein genügt nicht. Nicht belegbare Standorte werden übersprungen, nicht geraten. Das ist eine konservative Heuristik, kein amtlicher Sitznachweis.
- Microsoft, SAP, Lexware und weitere Hersteller sind in den Standard-Domainausschlüssen enthalten. Hinweise auf eigene Softwareprodukte führen ebenfalls zum Überspringen. Ein Microsoft-Partner oder Softwareanwender wird nicht allein durch die Erwähnung von Microsoft ausgeschlossen. Ausschlüsse sind manuell veränderbar; Grenzfälle können falsch ausgeschlossen werden.
- Produktwerte werden nur aus Websitebelegen berechnet, nicht aus dem eigenen KI-Verkaufstext. Ein Score beweist weder Kaufinteresse noch vorhandenen Bedarf.
- Suchmaschinen liefern manchmal sachfremde Antworten. Nur Ergebnislinks mit Bezug zu Suchbegriffen werden geprüft; Medien, Verzeichnisse und soziale Plattformen bleiben ausgeschlossen. Websites werden vor Aufnahme geprüft. Wenn Suchmaschinen blockieren oder keine belastbaren Treffer liefern, kann ein Lauf ohne neue Firmen enden.
- Bestehende Firmen werden nicht pauschal gelöscht. Bei erneuter Recherche greifen Hersteller- und Standortfilter; alte Entwürfe bleiben erhalten und müssen vor Nutzung geprüft werden.

## Handelsregister: Einzelprüfung statt Massenimport

In den Firmendetails gibt es Links zur offiziellen Handelsregister-/Unternehmensregistersuche und eine gezielte Suchmaschinenabfrage nach indexierten Handelsregistereinträgen für den Firmennamen. Ein Indexfund ist **kein verifizierter Registerauszug**. Name, Sitz, Registergericht, Registernummer und Quellenlink können anschließend als CRM-Aktivität dokumentiert werden.

Es gibt **keinen automatischen Handelsregister-Massenimport** und noch keinen automatischen Abruf oder Import amtlicher Auszüge. Die [Nutzungsordnung des Registerportals](https://www.handelsregister.de/rp_web/information/welcome.xhtml) untersagt systematische Abrufe zum Aufbau eigener Voll- oder Teilregister (Punkt 3). Einzelrecherchen sind vorgesehen; die dort genannte Obergrenze von 60 Abrufen pro Stunde stellt keine Erlaubnis für einen systematischen Firmenimport dar. Ein nicht vorhandener Registereintrag schließt einen Kleinbetrieb nicht aus.

Nächste optionale Schritte: Import eines vom Benutzer für eine konkrete Firma bereitgestellten Auszugs mit Prüffreigabe; geeigneter lizenzierter Firmen-/Suchdatenanbieter für reproduzierbare automatische Recherche; strukturierte Adress- und Registerfelder im CRM. Datenschutz und Zulässigkeit der späteren Kontaktaufnahme müssen getrennt geprüft werden.
