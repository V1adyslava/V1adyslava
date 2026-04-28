"""Typeform webhook handler.

Подпись: заголовок `Typeform-Signature: sha256=<base64>`.
Доки: https://www.typeform.com/developers/webhooks/secure-your-webhooks/
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.automations.stages import ingest_lead
from app.config import get_settings
from app.ghl.models import Lead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/typeform", tags=["webhooks"])


def _verify_signature(body: bytes, header: str | None, secret: str) -> None:
    if not secret:
        return
    if not header or not header.startswith("sha256="):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Typeform signature")
    expected = base64.b64encode(
        hmac.new(secret.encode(), body, hashlib.sha256).digest()
    ).decode()
    received = header.split("=", 1)[1]
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad Typeform signature")


def _extract_answers(form_response: dict[str, Any]) -> dict[str, Any]:
    """Typeform answers -> {field_ref_or_title: value}."""
    fields = {f["id"]: f for f in form_response.get("definition", {}).get("fields", [])}
    out: dict[str, Any] = {}
    for ans in form_response.get("answers", []) or []:
        field = ans.get("field", {})
        key = field.get("ref") or fields.get(field.get("id"), {}).get("title") or field.get("id")
        ans_type = ans.get("type")
        value = ans.get(ans_type) if ans_type else None
        if isinstance(value, dict):
            value = value.get("label") or value.get("labels") or value
        out[key] = value
    return out


def _build_lead(payload: dict[str, Any]) -> Lead:
    fr = payload.get("form_response", {})
    form_title = fr.get("definition", {}).get("title", "typeform")
    hidden = fr.get("hidden", {}) or {}
    answers = _extract_answers(fr)

    email = answers.get("email") or hidden.get("email")
    phone = answers.get("phone") or answers.get("phone_number") or hidden.get("phone")
    name = answers.get("name") or hidden.get("name")

    first, last = (None, None)
    if isinstance(name, str) and " " in name:
        first, last = name.split(" ", 1)
    elif isinstance(name, str):
        first = name

    custom = {**hidden, **{f"tf_{k}": v for k, v in answers.items()}}

    return Lead(
        email=email,
        phone=phone if isinstance(phone, str) else None,
        first_name=first,
        last_name=last,
        full_name=name if isinstance(name, str) else None,
        source=f"typeform:{form_title}",
        tags=["typeform", form_title.lower().replace(" ", "_")],
        custom_fields=custom,
        notes=f"Typeform submission: {form_title}",
    )


@router.post("")
async def typeform_webhook(
    request: Request,
    typeform_signature: str | None = Header(default=None, alias="Typeform-Signature"),
) -> dict[str, Any]:
    body = await request.body()
    settings = get_settings()
    _verify_signature(body, typeform_signature, settings.typeform_secret)

    payload = await request.json()
    lead = _build_lead(payload)
    if not (lead.email or lead.phone):
        logger.warning("Typeform webhook без email/phone, пропускаю")
        return {"ok": False, "reason": "no email/phone"}

    result = await ingest_lead(lead, "typeform.form_response")
    return {"ok": True, **result}
