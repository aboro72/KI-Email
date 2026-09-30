"""Kleine, modulare Automatisierungsbasis.

Die Engine kennt nur Ereignisse, Bedingungen und registrierte Aktionen. Module
wie CRM, Helpdesk und Marketing können später eigene Aktionen registrieren,
ohne voneinander abhängig zu werden. Versand- und KI-Aktionen bleiben bewusst
manuell freigabepflichtig, solange das nicht ausdrücklich anders konfiguriert ist.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AutomationRule, AutomationRun

Action = Callable[[Session, Mapping[str, object], Mapping[str, object]], Mapping[str, object] | None]
_ACTIONS: dict[str, Action] = {}


def register_action(name: str, action: Action) -> None:
    """Registriert eine Aktion; Modulnamen sollten z. B. ``crm.create_task`` sein."""
    if not name or not callable(action):
        raise ValueError("Eine Aktion benötigt einen Namen und eine aufrufbare Funktion.")
    _ACTIONS[name] = action


def _matches(conditions: Mapping[str, object], event: Mapping[str, object]) -> bool:
    """Bewusst einfache v1-Bedingungen: Feld muss exakt übereinstimmen."""
    return all(event.get(key) == expected for key, expected in conditions.items())


def emit_event(db: Session, event_name: str, payload: Mapping[str, object], *, dry_run: bool = False) -> list[AutomationRun]:
    """Führt passende aktive Regeln aus und protokolliert jeden Lauf."""
    rules = db.scalars(select(AutomationRule).where(AutomationRule.event_name == event_name, AutomationRule.is_active.is_(True))).all()
    runs: list[AutomationRun] = []
    for rule in rules:
        run: AutomationRun | None = None
        try:
            conditions = json.loads(rule.conditions_json or "{}")
            actions = json.loads(rule.actions_json or "[]")
            if not isinstance(conditions, dict) or not _matches(conditions, payload):
                continue
            run = AutomationRun(rule_id=rule.id, event_name=event_name, event_json=json.dumps(dict(payload), default=str), status="queued")
            db.add(run)
            db.flush()
            result: dict[str, object] = {"actions": []}
            if not dry_run:
                for action_config in actions:
                    action_name = action_config if isinstance(action_config, str) else action_config.get("name")
                    if not isinstance(action_name, str) or action_name not in _ACTIONS:
                        raise ValueError(f"Unbekannte Automationsaktion: {action_name}")
                    action_payload = action_config if isinstance(action_config, dict) else {}
                    output = _ACTIONS[action_name](db, payload, action_payload) or {}
                    result["actions"].append({"name": action_name, "result": dict(output)})
            run.status = "dry_run" if dry_run else "completed"
            run.result_json = json.dumps(result, default=str)
            run.finished_at = datetime.now(timezone.utc)
        except Exception as exc:
            if run is None:
                run = AutomationRun(rule_id=rule.id, event_name=event_name, event_json=json.dumps(dict(payload), default=str))
                db.add(run)
                db.flush()
            run.status = "failed"
            run.error = str(exc)[:1000]
            run.finished_at = datetime.now(timezone.utc)
        runs.append(run)
    if runs and not dry_run:
        db.commit()
    return runs
