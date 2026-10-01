# KI-gestützte Vertragsverwaltung – Stand 01.10.2026

## Umgesetzt

- Optionales Modul, schaltbar über `CONTRACTS_ENABLED`.
- Eigene Rechte für Lesen, Verwalten und KI-Prüfungen.
- Vertragsstammdaten mit Vertragspartner, CRM-Firma, Verantwortlichem, Laufzeit, Status und Verlängerung.
- Automatische Berechnung der Kündigungsfrist aus Enddatum und Kündigungsfrist in Tagen.
- Vertragserinnerungen und automatische Benachrichtigungen durch den vorhandenen Worker.
- Vertragsdokumente in einem eigenen, nicht öffentlichen CloudShare-Unterordner; Download und geschütztes Online-Office.
- Textübernahme aus TXT, Markdown, CSV, RTF und DOCX als Grundlage für die KI-Prüfung.
- KI-Prüfung im Hintergrund mit Zusammenfassung, Risiken, Pflichten, erkannten Fristen und Empfehlungen.
- Human-in-the-loop: KI-Ergebnisse ändern keine Verträge oder Erinnerungen automatisch.
- Vertragsdaten sind in die zentrale Suche aufgenommen.
- Dashboard-Schnellzugriffe sind pro Benutzer auf maximal sechs Bereiche konfigurierbar.
- Hauptnavigation ist nach Arbeit, Kunden/Service, Dokumenten und System gruppiert.

## Serverkonfiguration

```text
CONTRACTS_ENABLED=true
CONTRACTS_CLOUDSHARE_FOLDER_ID=<ID des Ordners „AboroDesk Verträge“>
```

Die CloudShare-Zugangsdaten bleiben identisch mit der allgemeinen Dateiablage. Der separate Ordner verhindert, dass Personen mit Zugriff auf die allgemeine Dateiablage automatisch Vertragsdateien sehen. Das Modul benötigt den AboroDesk-Worker für KI-Prüfungen und Erinnerungen.

## Rechte

- `CONTRACT_VIEW`: Vertragsliste und Verträge lesen sowie Dokumente herunterladen.
- `CONTRACT_MANAGE`: Verträge, Fristen und Dokumente bearbeiten und Online-Office öffnen.
- `CONTRACT_AI`: KI-Prüfung anfordern.

## Bewusste Grenzen

- Die KI-Ausgabe ist keine Rechtsberatung.
- Erkannte Fristen werden nur angezeigt und nicht automatisch gespeichert.
- PDF-Texterkennung ist noch nicht enthalten; relevante Inhalte können manuell als Prüftext hinterlegt werden.
- Vertragsdateien sind geschützt und versionierbar, aber noch kein revisionssicheres Archiv nach GoBD-Anforderungen.

## Sinnvolle nächste Erweiterungen

1. PDF-Textextraktion und optional OCR für gescannte Dokumente.
2. Freigabeprozess mit Vier-Augen-Prinzip und nachvollziehbaren Zuständen.
3. Vertragsvorlagen und Dokumenterzeugung mit Platzhaltern.
4. Versionierte Stammdatenänderungen und vollständiger Vertrags-Auditbericht.
5. Kalendersynchronisation für bestätigte Fristen.
6. Elektronische Signatur über einen separat konfigurierbaren Anbieter.

## Prüfung

Die lokale Testsuite umfasst nun 76 Tests. Sie prüft unter anderem Rechte, Modulabschaltung, Fristberechnung, Erinnerungen, getrennte Dokumentzuordnung, Upload/Download, KI-Warteschlange und persönliche Schnellzugriffe.
