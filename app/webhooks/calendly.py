"""Calendly v2 webhook handler.

Регистрация подписки: https://developer.calendly.com/api-docs/webhook-subscriptions
Подпись: заголовок `Calendly-Webhook-Signature: t=...,v1=...` (HMAC-SHA256).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.automations.stages import ingest_lead
from app.config import get_settings
from app.ghl.models import Lead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/calendly", tags=["webhooks"])


def _verify_signature(body: bytes, header: str | None, signing_key: str) -> None:
    if not signing_key:
        return  # подпись не настроена — пропускаем (для dev)
    if not header:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Calendly signature")
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed signature header")
    payload = f"{timestamp}.".encode() + body
    expected = hmac.new(signing_key.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad Calendly signature")


def _split_name(full: str | None) -> tuple[str | None, str | None]:
    if not full:
        return None, None
    parts = full.strip().split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _build_lead(payload: dict[str, Any], event_type: str) -> Lead:
    invitee = payload.get("payload", {})
    scheduled = invitee.get("scheduled_event", {})
    questions = invitee.get("questions_and_answers", []) or []
    custom = {q.get("question", f"q{i}"): q.get("answer") for i, q in enumerate(questions)}

    first, last = _split_name(invitee.get("name"))
    return Lead(
        email=invitee.get("email"),
        full_name=invitee.get("name"),
        first_name=first,
        last_name=last,
        source=f"calendly:{scheduled.get('name', 'event')}",
        tags=["calendly", event_type.split(".")[-1]],
        custom_fields=custom,
        notes=f"Calendly event: {scheduled.get('name')} @ {scheduled.get('start_time')}",
        scheduled_at=_parse_dt(scheduled.get("start_time")),
    )


@router.post("")
async def calendly_webhook(
    request: Request,
    calendly_signature: str | None = Header(default=None, alias="Calendly-Webhook-Signature"),
) -> dict[str, Any]:
    body = await request.body()
    settings = get_settings()
    _verify_signature(body, calendly_signature, settings.calendly_signing_key)

    payload = await request.json()
    event_type = payload.get("event", "invitee.created")  # invitee.created | invitee.canceled
    event_key = f"calendly.{event_type}"

    lead = _build_lead(payload, event_type)
    if not lead.email:
        logger.warning("Calendly webhook без email, пропускаю")
        return {"ok": False, "reason": "no email"}

    result = await ingest_lead(lead, event_key)
    return {"ok": True, **result}
