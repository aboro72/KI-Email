# Übergabe: Firmenrecherche für Deutschland und Kleinunternehmen

## Umgesetzt

- Bearbeitbare Kriterien unter `/crm/research-settings`, verlinkt in CRM, Firmenliste und Firmendetails.
- Speicherung in der Datenbank und Auditprotokoll; geschützt durch `CRM_MANAGE` und bestehende CSRF-Prüfung.
- Suchbegriffe für Kleinbetriebe und alle vier Angebote: AboroDesk, AboroLMS, CloudShare, Helpdesk.
- Standortprüfung über Website/Impressum; Deutschland fest, unbekannte Standorte werden übersprungen.
- Ausschluss von Hersteller-Domains und Hinweisen auf eigene Softwareprodukte. Kein pauschaler Ausschluss von Microsoft-Partnern.
- Produktpassung aus Websitebelegen statt aus KI-Vertriebstexten; produktbezogene KI-Gesprächsentwürfe statt generellem LMS-Verkauf.
- Ergebnislink- und Relevanzfilter sowie Prüfung öffentlicher Website-Adressen und Weiterleitungen.
- Handelsregister-Einzelprüfung über offizielle Portale und explizit als unbestätigt bezeichnete Indexsuche in Firmendetails. Kein automatischer Registerimport.

## Tests und Serverstand

- Lokal: 27 Tests erfolgreich; darunter acht neue Tests für Kriterien, Speicherung, Impressum, Konkurrenzfilter, Kleinbetriebe und unpassende Suchtreffer.
- Server 212.44.166.238: Anwendung und Worker aktualisiert; bestehender 12-Stunden-Suchtimer bleibt aktiv. Kriterienseite mit Anmeldung geladen, Standards gespeichert und aus MongoDB wieder gelesen; ungültiger Score abgelehnt, anonymer Zugriff abgelehnt.
- Backup vor Deployment: `/var/backups/aborodesk/mongodb/20261001T083331Z/aborodesk.archive.gz`.
- Vorversion der geänderten Bestandsdateien: `/opt/aborodesk/deploy/rollback-prospects-20261001/`. Neue Dateien bei einem Rollback separat beachten.
- Live-Suchprobe ohne CRM-Schreibvorgänge: Suchmaschinen lieferten teilweise sachfremde Treffer. Deshalb zusätzlicher Titel-/Domain-Relevanzfilter. Suchqualität ist weiterhin abhängig von öffentlichen Suchmaschinen; keine Erfolgsgarantie pro Lauf.
- Der anschließende Prüflauf fand reale Ingenieurbüros und bestätigte die Standortprüfung. Ein bloßer Betriebstyp wird inzwischen mit 20 Punkten nur als Kandidat zur manuellen Prüfung gewertet, damit Kleinbetriebe ohne technische Website-Begriffe nicht pauschal herausfallen.
- Abschließender Live-Test: `projekt55.de` erfüllte die Standortprüfung und erhielt CloudShare mit 20 Punkten (beobachten). Acht neue Tests auf dem Server erfolgreich; Anwendung, Worker und Suchtimer aktiv.
- Bestehende Firmen und alte Leads bleiben erhalten. Keine pauschale Bereinigung und kein automatischer Versand.

## Grenzen / nächster Schritt

1. Erste Suchläufe prüfen und Suchbegriffe auf die tatsächlich gewünschten Branchen/Regionen abstimmen. Eigene Suchanfragen und Ausschlüsse bleiben editierbar.
2. Die Standort- und Wettbewerbsfilter sind Heuristiken: unklare Firmen werden konservativ übersprungen; Mischanbieter können fälschlich ausgeschlossen werden. Keine amtliche Verifikation oder KI-bestätigte Kaufabsicht behaupten.
3. Handelsregister: noch offen sind der freigegebene Import einzelner Auszüge und strukturierte Register-/Adressfelder. Automatischer Register-Massenimport wurde bewusst nicht gebaut: [Portal-Nutzungsordnung](https://www.handelsregister.de/rp_web/information/welcome.xhtml), Punkt 3.
4. Optional lizenzierte Such-/Firmendatenquelle, genauere Branchengewichtung, Auswertungsansicht für übersprungene Kandidaten, Ausschluss einzelner Produkte bei Mischanbietern und kleinere produktbezogene Kampagnen.
5. GitHub-Push am 01.10.2026 erneut mit HTTP 403 abgelehnt: Konto `ML-PIT` hat keine Schreibberechtigung für `aboro72/KI-Email`. Implementierung lokal in Commit `d4b2a63` gesichert und unabhängig davon auf den Server übertragen. GitHub enthält diese Änderungen noch nicht. Zum Weiterarbeiten zu Hause liegt zusätzlich eine Git-Sicherung `KI-Email-2026-10-01.bundle` im SSH-Benutzerverzeichnis auf dem Server (vollständiger master-Verlauf, einschließlich Übergabe).

Details und Bedienung: [Produkt-Recherche-Kriterien](produkt-recherche-kriterien.md). Keine Passwörter oder API-Schlüssel in dieser Übergabe.
