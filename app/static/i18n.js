(() => {
  "use strict";
  const language = window.ABORODESK_LANGUAGE || "de";
  document.documentElement.lang = language;
  if (language !== "en") return;

  const translations = {
    "Dashboard":"Dashboard", "Arbeit":"Work", "Posteingang":"Inbox", "Neue E-Mail":"New email",
    "Aufgaben":"Tasks", "Meine Aufgaben":"My tasks", "Projektplanung":"Project planning",
    "Kunden & Service":"Customers & service", "CRM-Übersicht":"CRM overview", "Firmen":"Companies",
    "Kontakte":"Contacts", "Leads":"Leads", "Helpdesk":"Help desk", "Wissensbasis":"Knowledge base",
    "Marketing":"Marketing", "Dokumente":"Documents", "Dateiablage":"File storage", "Verträge":"Contracts",
    "Suche":"Search", "System":"System", "Administration":"Administration", "Benutzer":"Users",
    "Rollen & Rechte":"Roles & permissions", "E-Mail-Konten":"Email accounts", "Hilfe":"Help", "Abmelden":"Sign out",
    "Anmelden":"Sign in", "E-Mail-Adresse":"Email address", "Passwort":"Password", "Zurück":"Back",
    "Speichern":"Save", "Änderungen speichern":"Save changes", "Löschen":"Delete", "Bearbeiten":"Edit",
    "Abbrechen":"Cancel", "Öffnen":"Open", "Schließen":"Close", "Erledigt":"Done", "Aktualisieren":"Refresh",
    "Filtern":"Filter", "Alle Status":"All statuses", "Status":"Status", "Priorität":"Priority",
    "Niedrig":"Low", "Normal":"Normal", "Hoch":"High", "Kritisch":"Critical", "Entwurf":"Draft",
    "Aktiv":"Active", "Gekündigt":"Terminated", "Beendet":"Ended", "Archiviert":"Archived",
    "Arbeitsübersicht":"Work overview", "Das Wichtigste für deinen Arbeitstag auf einen Blick.":"The most important items for your workday at a glance.",
    "System bereit":"System ready", "Ungelesene E-Mails":"Unread emails", "Offene Entwürfe":"Open drafts",
    "Versendete E-Mails":"Sent emails", "Offene Aufgaben":"Open tasks", "Mein Schnellzugriff":"My shortcuts",
    "Nur deine ausgewählten Bereiche werden hier angezeigt.":"Only the areas you selected are shown here.",
    "Anpassen":"Customize", "Höchstens 6 Bereiche auswählen":"Select up to 6 areas", "Auswahl speichern":"Save selection",
    "Noch kein Schnellzugriff ausgewählt. Über „Anpassen“ kannst du Bereiche hinzufügen.":"No shortcuts selected yet. Use “Customize” to add areas.",
    "Versand-Sicherheitsgate":"Sending safety gate", "KI-Vorschlag ≠ Versand":"AI suggestion ≠ sending",
    "Die KI erstellt Vorschläge. Der Versand erfolgt erst nach deiner ausdrücklichen Freigabe.":"AI creates suggestions. Messages are sent only after your explicit approval.",
    "Entwürfe":"Drafts", "Prüfen und freigeben":"Review and approve", "Freigegeben":"Approved", "Senden":"Send",
    "Noch keine Entwürfe vorhanden.":"No drafts yet.", "Benachrichtigungen":"Notifications",
    "Letzte Systemaktionen":"Recent system activity", "Noch keine Aktionen protokolliert.":"No activity recorded yet.",
    "Globale Sprache / Global language":"Global language", "Die Auswahl gilt für alle Benutzer dieser Installation.":"This selection applies to all users of this installation.",
    "Sprache / Language":"Language", "Sprache speichern / Save language":"Save language", "Nur Admin":"Admins only",
    "Systemverwaltung":"System administration", "Wähle den Bereich, den du verwalten möchtest.":"Choose the area you want to manage.",
    "Konten und Rollen zuweisen":"Assign accounts and roles", "Rechte und Module steuern":"Manage permissions and modules",
    "IMAP und SMTP verwalten":"Manage IMAP and SMTP", "Anwendung betriebsbereit":"Application ready",
    "Schnellzugriff":"Shortcuts", "klar getrennt":"clearly separated", "Benutzer verwalten":"Manage users",
    "Optionales Modul":"Optional module", "Vertragsverwaltung":"Contract management",
    "Verträge, Dokumente, Fristen und KI-Prüfhinweise an einem Ort.":"Contracts, documents, deadlines and AI review notes in one place.",
    "Vertrag anlegen":"Create contract", "Verträge suchen":"Search contracts", "Titel, Nummer oder Vertragspartner":"Title, number or contracting party",
    "Keine passenden Verträge gefunden.":"No matching contracts found.", "Kundenvertrag":"Customer contract",
    "Lieferantenvertrag":"Supplier contract", "Wartung / Service":"Maintenance / service", "Lizenz":"Licence",
    "Miete":"Lease", "Personal":"Employment", "Sonstiges":"Other", "Neuer Vertrag":"New contract",
    "Vertrag bearbeiten":"Edit contract", "Titel":"Title", "Vertragsnummer":"Contract number", "CRM-Firma":"CRM company",
    "Keine Zuordnung":"No assignment", "Vertragspartner":"Contracting party", "Vertragsart":"Contract type",
    "Verantwortlich":"Responsible person", "Beginn":"Start", "Ende":"End", "Kündigungsfrist in Tagen":"Notice period in days",
    "Verlängerung in Monaten":"Renewal in months", "Automatische Verlängerung laut Vertrag":"Automatic renewal according to contract",
    "Beschreibung":"Description", "Text für KI-Prüfung":"Text for AI review",
    "Optional: Vertragstext einfügen. Bei DOCX/TXT wird der Text beim Upload automatisch übernommen.":"Optional: paste the contract text. DOCX/TXT text is imported automatically on upload.",
    "Die KI-Prüfung ist eine Arbeitshilfe und keine Rechtsberatung. Ergebnisse müssen immer von einer Person geprüft werden.":"The AI review is a work aid, not legal advice. A person must always review the results.",
    "Vertragspartner erfasst":"Contracting party recorded", "Kein Vertragspartner erfasst":"No contracting party recorded",
    "Alle Verträge":"All contracts", "Vertragsbeginn":"Contract start", "Vertragsende":"Contract end",
    "Kündigung spätestens":"Cancel no later than", "Nicht berechnet":"Not calculated", "Offen":"Open",
    "geschützt":"protected", "Datei":"File", "Hochladen":"Upload", "Download":"Download", "Office":"Office",
    "Noch keine Vertragsdokumente.":"No contract documents yet.",
    "Vertragsdateien liegen in einem eigenen CloudShare-Bereich und sind von der allgemeinen Dateiablage getrennt.":"Contract files are stored in a dedicated CloudShare area, separate from general file storage.",
    "Fristen & Erinnerungen":"Deadlines & reminders", "Noch keine Fristen.":"No deadlines yet.",
    "Erinnerung hinzufügen":"Add reminder", "Fällig am":"Due on", "Erinnern am":"Remind on",
    "KI-gestützte Vertragsprüfung":"AI-assisted contract review", "Unverbindliche Prüfhilfe – keine Rechtsberatung und keine automatische Änderung.":"Non-binding review aid – no legal advice and no automatic changes.",
    "Prüfung starten":"Start review", "Die KI-Prüfung läuft im Hintergrund. Du kannst die Seite später neu laden.":"The AI review is running in the background. You can reload the page later.",
    "Zusammenfassung":"Summary", "Prüfpunkte / Risiken":"Review points / risks", "Pflichten":"Obligations",
    "Erkannte Fristen":"Detected deadlines", "Empfehlungen":"Recommendations", "Datum prüfen":"Check date",
    "Keine eindeutigen Hinweise erkannt.":"No clear findings detected.", "Keine eindeutigen Pflichten erkannt.":"No clear obligations detected.",
    "Keine eindeutigen Fristen erkannt.":"No clear deadlines detected.", "Keine zusätzlichen Empfehlungen.":"No additional recommendations.",
    "Noch keine KI-Prüfung angefordert. Grundlage ist der gespeicherte Prüftext.":"No AI review requested yet. The saved review text is used as its basis.",
    "E-Mail und KI":"Email and AI", "Postfach aktualisieren":"Refresh mailbox", "Nachrichten durchsuchen":"Search messages",
    "Absender, Betreff oder Inhalt suchen":"Search sender, subject or content", "Nur ungelesen":"Unread only",
    "Alle Prioritäten":"All priorities", "Nachrichten":"Messages", "Ungelesene zuerst":"Unread first",
    "Antworten":"Reply", "Weiterleiten":"Forward", "Papierkorb":"Trash", "Wiederherstellen":"Restore",
    "Neue Nachricht":"New message", "Von":"From", "An":"To", "Betreff":"Subject", "Nachricht":"Message",
    "Anhänge":"Attachments", "Aktivitäten":"Activities", "Firma anlegen":"Create company", "Kontakt anlegen":"Create contact",
    "Lead anlegen":"Create lead", "Suchkriterien":"Search criteria", "Recherche":"Research", "Recherche erneut starten":"Restart research",
    "Firma löschen":"Delete company", "Kampagnen":"Campaigns", "Kampagne anlegen":"Create campaign",
    "Tickets":"Tickets", "Ticket anlegen":"Create ticket", "Wissensartikel":"Knowledge articles",
    "Artikel anlegen":"Create article", "Projekt anlegen":"Create project", "Projekte":"Projects", "Projekt & Team":"Project & team",
    "Backlog":"Backlog", "Geplant":"Planned", "In Arbeit":"In progress", "Prüfung":"Review",
    "Gemeinsame Dateiablage":"Shared file storage", "Datei hochladen":"Upload file", "Herunterladen":"Download",
    "In Office bearbeiten":"Edit in Office", "Versionen":"Versions", "Version wiederherstellen":"Restore version",
    "Erste Schritte":"Getting started", "Häufige Fragen":"Frequently asked questions", "Serverbetrieb":"Server operations",
    "Anleitungen & Antworten":"Guides & answers", "Aufgaben, Benachrichtigungen und Suche":"Tasks, notifications and search",
    "Aufgabe anlegen":"Create task", "Fälligkeitsdatum":"Due date", "Aufgabe erledigen":"Complete task",
    "Zentrale Suche":"Global search", "Suchbegriff":"Search term", "Keine Ergebnisse gefunden.":"No results found.",
    "Aktion nicht möglich":"Action not possible", "Erneut versuchen":"Try again", "Liste aktualisieren":"Refresh list"
  };
  Object.assign(translations, window.ABORODESK_TRANSLATIONS || {});

  const replacements = [
    [/^Guten Tag,\s*/i, "Hello, "], [/^Noch keine\s+/i, "No "], [/^Zurück zu\s+/i, "Back to "],
    [/\bDatei\(en\)\b/g, "file(s)"], [/\bNachricht\(en\)\b/g, "message(s)"],
    [/\bfällig\b/gi, "due"], [/\bErinnerung\b/g, "Reminder"], [/\bgeprüft\b/g, "reviewed"],
    [/\bEnde\s+(\d{4}-\d{2}-\d{2})/g, "Ends $1"]
  ];

  function translateText(value) {
    const leading = value.match(/^\s*/)[0], trailing = value.match(/\s*$/)[0];
    const core = value.trim();
    if (!core) return value;
    let translated = translations[core] || core;
    if (translated === core) replacements.forEach(([pattern, replacement]) => { translated = translated.replace(pattern, replacement); });
    return leading + translated + trailing;
  }

  function translate(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        return node.parentElement && !["SCRIPT", "STYLE", "CODE", "PRE"].includes(node.parentElement.tagName) && node.nodeValue.trim()
          ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => { node.nodeValue = translateText(node.nodeValue); });
    root.querySelectorAll("[placeholder]").forEach(element => { element.placeholder = translations[element.placeholder] || element.placeholder; });
    root.querySelectorAll("[title]").forEach(element => { element.title = translations[element.title] || element.title; });
  }

  const start = () => translate(document.body);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
