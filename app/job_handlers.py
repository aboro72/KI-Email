"""Registrierung der produktiven Modul-Handler für den Worker."""

from app.jobs import register_handler


def _sync_account(db, payload):
    from app.main import sync_account
    from app.models import EmailAccount
    account = db.get(EmailAccount, int(payload["account_id"]))
    if account:
        sync_account(account, db)


def _research_company(db, payload):
    from app.main import research_company_background
    research_company_background(int(payload["company_id"]))


def _analyze_ticket(db, payload):
    from app.bedrock import assist_ticket
    from app.models import KnowledgeArticle, Ticket
    from sqlalchemy import select
    ticket = db.get(Ticket, int(payload["ticket_id"]))
    if not ticket:
        return
    articles = db.scalars(select(KnowledgeArticle).where(KnowledgeArticle.status == "published").limit(5)).all()
    context = "\n\n".join(f"{item.product}: {item.title}\n{item.summary}\n{item.content[:1200]}" for item in articles)
    result = assist_ticket(ticket.subject, ticket.description, context)
    ticket.ai_summary = result["summary"]
    ticket.ai_reply_draft = result["reply_draft"]
    ticket.ai_research_suggestion = result["research_suggestion"]
    ticket.ai_confidence = result["confidence"]
    ticket.support_level = max(1, min(int(result["support_level"] or 1), 3))
    if result["priority"] in {"niedrig", "normal", "hoch", "kritisch"}:
        ticket.priority = result["priority"]
    db.commit()


register_handler("email.sync_account", _sync_account)
register_handler("crm.company_research", _research_company)
register_handler("helpdesk.ai_analysis", _analyze_ticket)
