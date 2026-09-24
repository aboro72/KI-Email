# Technische Analyse und Phase-1-Entscheidung

## Architektur

Das System startet als modularer Monolith: FastAPI mit klar getrennten Modulen für Auth, Mail, Accounts, KI, Security, Audit sowie später Marketing und Leads. Das hält den Betriebsaufwand niedrig; Redis/Worker werden ergänzt, sobald Synchronisation und Recherche als Hintergrundjobs benötigt werden. SQLAlchemy 2 abstrahiert SQLite in der Entwicklung und PostgreSQL in Produktion. Die Phase-1-Oberfläche ist serverseitig responsiv und die API bleibt für eine spätere React-/Next.js-Oberfläche vorbereitet.

## Datenmodell und Sicherheit

Phase 1 enthält User, Role, Permission, AuditLog und Draft. Geplant sind zusätzlich EmailAccount, EmailMessage, EmailThread, Attachment, Contact, Company, CalendarEvent, SupportCase, AIProvider, AIModel, AIRequest, PromptTemplate, Lead, LeadSource, MarketingCampaign, MarketingRecipient, SpamRule, Whitelist, Blacklist, UserSetting und ProviderSetting. Passwörter werden mit Argon2id gehasht, Sessions liegen in HttpOnly-Cookies, Secrets werden verschlüsselt gespeichert. Rollen und Berechtigungen werden ausschließlich serverseitig geprüft.

## Provider und Bedrock

Alle KI-Anbieter implementieren später `generate`, `classify`, `summarize`, `translate`, `extract_structured_data`, `health_check`, `list_models` und `estimate_cost`. Die Bedrock-Integration nutzt `bedrock-runtime.Converse`, weil AWS diese Schnittstelle als einheitlichen Weg für unterstützte Message-Modelle dokumentiert. Modell-ID und Region bleiben Konfiguration. Der Modellkatalog wird zur Laufzeit abgefragt und nach Converse-Fähigkeit, Textunterstützung, Sprache, Kontext, Kosten und Geschwindigkeit bewertet. Nova Lite ist die initiale Empfehlung für kostengünstige Klassifikation, Zusammenfassung und Standardentwürfe, falls sie in der gewählten Region verfügbar ist; ansonsten wird ein verfügbares Modell gewählt oder eine klare Konfigurationsmeldung angezeigt.

## Human-in-the-loop

Der Ablauf lautet `RECEIVE_EMAIL -> ANALYZE -> AI_GENERATE -> DRAFT -> USER_REVIEW -> USER_APPROVAL -> EMAIL_SEND`. Der KI-Service erhält keine `EMAIL_SEND`-Berechtigung. Der Versandservice akzeptiert KI-Entwürfe nur mit `approved_by_user_id`, `approved_at` und einer unveränderten Inhaltsrevision. Ohne diese Felder lehnt der Server den Versand ab.

## Phasen

Phase 1: Architektur, Schema-Grundlage, Login, Rollen/Rechte, Dashboard und Versand-Gate. Danach folgen IMAP/SMTP, OAuth, Provider, KI-Funktionen, Spam/Phishing, Termine, Support, Leads, Marketing und Security-Härtung.

## Phase 2 in einfachen Worten

Ein E-Mail-Konto wird wie ein verschlossener Briefkasten behandelt. Der Administrator trägt Server, Benutzername und Passwort ein. Das Passwort wird sofort verschlüsselt. Die Webseite zeigt es später nicht wieder an. IMAP liest später Nachrichten aus dem Briefkasten; SMTP wird später für den Versand genutzt. Der Verbindungstest prüft nur, ob die Zugangsdaten funktionieren. Er verschickt absichtlich keine Nachricht.
