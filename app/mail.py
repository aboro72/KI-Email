"""Einfache IMAP-/SMTP-Grundlage.

Die Funktionen testen zunächst nur die Verbindung. Sie senden keine E-Mail
und kopieren keine Passwörter in Logs. Der echte Synchronisationsjob folgt,
wenn die Konten im Admin-Bereich eingerichtet werden können.
"""

import imaplib
import smtplib


def test_imap_connection(host: str, port: int, username: str, password: str) -> None:
    """Verbindet sich sicher per IMAPS und meldet Fehler an die Oberfläche."""
    with imaplib.IMAP4_SSL(host, port, timeout=15) as connection:
        connection.login(username, password)
        connection.logout()


def test_smtp_connection(host: str, port: int, username: str, password: str) -> None:
    """Testet SMTP mit TLS. Diese Funktion verschickt absichtlich nichts."""
    with smtplib.SMTP(host, port, timeout=15) as connection:
        connection.starttls()
        connection.login(username, password)
        connection.quit()
