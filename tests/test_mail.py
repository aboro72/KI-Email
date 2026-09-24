from app import mail


def test_connection_helpers_do_not_send_messages(monkeypatch):
    calls = []

    class FakeImap:
        def __init__(self, host, port, timeout):
            calls.append(("imap", host, port, timeout))
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def login(self, username, password):
            calls.append(("imap-login", username, password))
        def logout(self):
            calls.append(("imap-logout",))

    class FakeSmtp:
        def __init__(self, host, port, timeout):
            calls.append(("smtp", host, port, timeout))
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def starttls(self):
            calls.append(("starttls",))
        def login(self, username, password):
            calls.append(("smtp-login", username, password))
        def quit(self):
            calls.append(("quit",))

    monkeypatch.setattr(mail.imaplib, "IMAP4_SSL", FakeImap)
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSmtp)
    mail.test_imap_connection("imap.test", 993, "user", "secret")
    mail.test_smtp_connection("smtp.test", 587, "user", "secret")
    assert ("imap-login", "user", "secret") in calls
    assert ("smtp-login", "user", "secret") in calls
    assert not any(call[0] == "sendmail" for call in calls)
