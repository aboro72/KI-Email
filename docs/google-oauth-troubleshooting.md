# Gmail-OAuth: Fehler 403 `access_denied`

## Ursache

Die Google-App steht auf **Testing**. In diesem Zustand dürfen nur E-Mail-Adressen aus der Liste **Test users / Testnutzer** die App verwenden.

## Lösung

1. Google Cloud Console öffnen: https://console.cloud.google.com/
2. Das richtige Projekt auswählen.
3. Zu **Google Auth Platform** bzw. **APIs & Dienste → OAuth-Zustimmungsbildschirm** gehen.
4. Den Bereich **Audience / Zielgruppe** öffnen.
5. Bei **Test users / Testnutzer** auf **Add users / Nutzer hinzufügen** klicken.
6. Diese Adresse eintragen:

   `andreas.borowczak@googlemail.com`

7. Speichern.
8. Die Anmeldung im Browser erneut starten.

Die Adresse muss exakt stimmen. Ein Tippfehler oder eine andere Google-Adresse reicht aus, damit Google wieder `access_denied` meldet.

## Wichtig für Tests

Im Testmodus dürfen nur freigegebene Testnutzer zugreifen. Google weist außerdem darauf hin, dass Autorisierungen für externe Test-Apps mit sensiblen Gmail-Berechtigungen zeitlich begrenzt sein können. Für den privaten Entwicklungstest ist das normal. Für eine spätere Nutzung mit vielen Benutzern muss die OAuth-App vorbereitet und gegebenenfalls von Google geprüft werden.

## Wenn die Adresse schon eingetragen ist

- Prüfen, ob in Google Cloud wirklich das richtige Projekt geöffnet ist.
- Im Google-Konto aus- und wieder einloggen.
- Den OAuth-Vorgang neu über `http://localhost:8000/admin` starten.
- Prüfen, dass die Gmail-Adresse nicht nur als Projektbenutzer, sondern als OAuth-Testnutzer eingetragen ist.

## Fehler `InvalidGrantError`

Der Google-Code ist nur einmal verwendbar und läuft schnell ab. Starte den Vorgang immer neu über das Admin-Dashboard. Die Callback-Seite darf nicht aktualisiert werden. Verwende beim gesamten Test immer dieselbe Adresse, am einfachsten:

`http://localhost:8000/admin`

Wenn der Fehler trotzdem wiederkommt, muss der OAuth-Vorgang in einem neuen Browser-Tab komplett neu gestartet werden. Ein bereits verwendeter Code kann nicht erneut eingelöst werden. Die Anwendung zeigt im Fehlerfall nun zusätzlich Googles kurze, nicht geheime Fehlermeldung an.

## Fehler `InsecureTransportError`

Dieser Fehler ist beim lokalen Test mit `http://localhost` erwartbar, wenn die OAuth-Bibliothek HTTP nicht als lokale Ausnahme kennt. Die Anwendung aktiviert diese Ausnahme jetzt automatisch nur für `localhost` und `127.0.0.1`. Für eine echte Veröffentlichung muss HTTPS eingerichtet werden.

## Fehler `Missing code verifier`

Google verwendet beim OAuth-Login PKCE. Die Anwendung speichert den kurzlebigen PKCE-Verifier jetzt im signierten OAuth-State und verwendet ihn beim Rücksprung. Nach dem Update muss ein komplett neuer Login gestartet werden; eine alte Google-Callback-Seite kann nicht wiederverwendet werden.
