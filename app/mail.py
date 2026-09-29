"""Einfache IMAP-/SMTP-Grundlage.

Die Funktionen testen zunächst nur die Verbindung. Sie senden keine E-Mail
und kopieren keine Passwörter in Logs. Der echte Synchronisationsjob folgt,
wenn die Konten im Admin-Bereich eingerichtet werden können.
"""

from email import policy
from email.message import EmailMessage as MIMEMessage
from email.parser import BytesParser
from email.utils import formatdate, make_msgid, parsedate_to_datetime
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


def send_email(host: str, port: int, username: str, password: str, sender: str, recipient: str, subject: str, body: str, in_reply_to: str | None = None, cc: str = "", bcc: str = "", html_body: str | None = None, attachments: list[dict] | None = None) -> None:
    message = MIMEMessage()
    message["From"] = sender
    message["To"] = recipient
    if cc:
        message["Cc"] = cc
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    for attachment in attachments or []:
        message.add_attachment(attachment["content"], maintype=attachment["maintype"], subtype=attachment["subtype"], filename=attachment["filename"])
    with smtplib.SMTP(host, port, timeout=30) as connection:
        connection.starttls()
        connection.login(username, password)
        connection.send_message(message, to_addrs=[item.strip() for item in f"{recipient},{cc},{bcc}".split(",") if item.strip()])


def fetch_imap_messages(host: str, port: int, username: str, password: str) -> list[dict]:
    """Liest Nachrichten aus INBOX, ohne sie auf dem Server zu verändern."""
    messages = []
    with imaplib.IMAP4_SSL(host, port, timeout=30) as connection:
        connection.login(username, password)
        connection.select("INBOX", readonly=True)
        status, data = connection.uid("search", None, "ALL")
        if status != "OK":
            raise RuntimeError("IMAP-Suche fehlgeschlagen")
        for uid in data[0].split():
            status, parts = connection.uid("fetch", uid, "(RFC822)")
            if status != "OK":
                continue
            raw = next((part[1] for part in parts if isinstance(part, tuple)), None)
            if not raw:
                continue
            message = BytesParser(policy=policy.default).parsebytes(raw)
            body = message.get_body(preferencelist=("plain", "html"))
            messages.append({
                "external_id": message.get("Message-ID") or f"imap:{username}:{uid.decode()}",
                "sender": str(message.get("From", "")),
                "subject": str(message.get("Subject", "")),
                "body": body.get_content() if body else "",
                "received_at": _parse_date(message.get("Date")),
            })
        connection.logout()
    return messages


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
