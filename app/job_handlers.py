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


def _analyze_contract(db, payload):
    import json
    from datetime import datetime, timezone
    from app.bedrock import analyze_contract
    from app.models import Contract, Notification

    contract = db.get(Contract, int(payload["contract_id"]))
    if not contract:
        return
    requester_id = int(payload.get("requested_by_user_id") or contract.owner_user_id)
    if contract.contract_type == "personal":
        from app.models import User
        from app.personnel_access import can_read_personnel, has
        requester = db.get(User, requester_id)
        if not requester or not requester.is_active or not can_read_personnel(requester) or not all(
                has(requester, p) for p in ("CONTRACT_VIEW", "CONTRACT_AI")):
            contract.ai_status = "not_requested"
            db.commit()
            return
    contract.ai_status = "running"
    contract.ai_error = ""
    db.commit()
    try:
        metadata = (
            f"Vertragspartner: {contract.counterparty}; Typ: {contract.contract_type}; "
            f"Beginn: {contract.start_date}; Ende: {contract.end_date}; "
            f"Kündigungsfrist: {contract.cancellation_deadline}"
        )
        result = analyze_contract(contract.title, metadata, contract.analysis_text)
        contract.ai_result_json = json.dumps(result, ensure_ascii=False)
        contract.ai_status = "completed"
        contract.ai_analyzed_at = datetime.now(timezone.utc)
        requester_id = int(payload.get("requested_by_user_id") or contract.owner_user_id)
        db.add(Notification(user_id=requester_id, title="Vertragsprüfung abgeschlossen",
                            message="Details im geschützten Personalbereich." if contract.contract_type == "personal" else contract.title,
                            url=f"/contracts/{contract.id}"))
        db.commit()
    except Exception as exc:
        db.rollback()
        contract = db.get(Contract, int(payload["contract_id"]))
        if contract:
            contract.ai_status = "failed"
            contract.ai_error = str(exc)[:1000]
            db.commit()
        raise


register_handler("email.sync_account", _sync_account)
register_handler("crm.company_research", _research_company)
register_handler("helpdesk.ai_analysis", _analyze_ticket)
register_handler("contracts.ai_analysis", _analyze_contract)
