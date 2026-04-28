"""Generic webhook для форм с сайтов (Tilda, WordPress, кастом).

Аутентификация: заголовок `X-Site-Token` должен совпасть с SITE_FORM_TOKEN.
Принимает как JSON, так и application/x-www-form-urlencoded / multipart.

Минимальный payload:
    {"email": "...", "name": "...", "phone": "...", "source": "landing_a"}

Любые дополнительные поля попадут в custom_fields.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.automations.stages import ingest_lead
from app.config import get_settings
from app.ghl.models import Lead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/site", tags=["webhooks"])

KNOWN_KEYS = {"email", "phone", "name", "first_name", "last_name", "source", "notes"}


def _check_token(token: str | None, expected: str) -> None:
    if not expected:
        return
    if not token or not token == expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad site token")


async def _read_payload(request: Request) -> dict[str, Any]:
    ctype = (request.headers.get("content-type") or "").lower()
    if "application/json" in ctype:
        return await request.json()
    form = await request.form()
    return {k: v for k, v in form.multi_items()}


def _build_lead(data: dict[str, Any]) -> Lead:
    name = data.get("name") or data.get("full_name")
    first = data.get("first_name")
    last = data.get("last_name")
    if name and not (first or last):
        parts = str(name).strip().split(maxsplit=1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else None

    custom = {k: v for k, v in data.items() if k not in KNOWN_KEYS}
    source = data.get("source") or "site"

    return Lead(
        email=data.get("email") or None,
        phone=data.get("phone") or None,
        first_name=first,
        last_name=last,
        full_name=name if isinstance(name, str) else None,
        source=f"site:{source}",
        tags=["site", str(source)],
        custom_fields=custom,
        notes=data.get("notes"),
    )


@router.post("")
async def site_webhook(
    request: Request,
    x_site_token: str | None = Header(default=None, alias="X-Site-Token"),
) -> dict[str, Any]:
    settings = get_settings()
    _check_token(x_site_token, settings.site_form_token)

    data = await _read_payload(request)
    lead = _build_lead(data)
    if not (lead.email or lead.phone):
        logger.warning("Site webhook без email/phone, пропускаю")
        return {"ok": False, "reason": "no email/phone"}

    result = await ingest_lead(lead, "site.form_submitted")
    return {"ok": True, **result}
