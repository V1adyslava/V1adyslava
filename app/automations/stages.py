"""Логика автоматизаций по смене стадий в воронке GHL.

Маппинг событий из источников -> стадия в GHL.
Меняйте таблицу EVENT_TO_STAGE под свою воронку, не залезая в код вебхуков.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import Settings, get_settings
from app.ghl.client import GHLClient
from app.ghl.models import Lead

logger = logging.getLogger(__name__)


# Ключи событий, которые шлют вебхуки. Значения — ключи из Settings.stage_for().
EVENT_TO_STAGE: dict[str, str] = {
    # Calendly
    "calendly.invitee.created": "booked",
    "calendly.invitee.canceled": "no_show",
    # Typeform
    "typeform.form_response": "qualified",
    # Site forms
    "site.form_submitted": "new",
    # Manual
    "manual.won": "won",
    "manual.lost": "lost",
}


@dataclass
class StageDecision:
    stage_id: str
    stage_key: str
    status: str = "open"  # open | won | lost | abandoned

    @property
    def is_valid(self) -> bool:
        return bool(self.stage_id)


def decide_stage(event: str, settings: Settings | None = None) -> StageDecision:
    settings = settings or get_settings()
    stage_key = EVENT_TO_STAGE.get(event, "new")
    stage_id = settings.stage_for(stage_key)
    status = "open"
    if stage_key == "won":
        status = "won"
    elif stage_key == "lost":
        status = "lost"
    elif stage_key == "no_show":
        status = "abandoned"
    return StageDecision(stage_id=stage_id, stage_key=stage_key, status=status)


async def ingest_lead(
    lead: Lead,
    event: str,
    client: GHLClient | None = None,
    settings: Settings | None = None,
) -> dict[str, str]:
    """Главная точка входа из вебхуков.

    1. upsert контакта в GHL
    2. определяет стадию для события
    3. создаёт opportunity или двигает существующую
    4. опционально оставляет note
    """
    settings = settings or get_settings()
    client = client or GHLClient(settings)
    decision = decide_stage(event, settings)

    contact = await client.upsert_contact(lead)
    contact_id = contact.get("id") or contact.get("_id") or contact.get("contactId")
    if not contact_id:
        raise RuntimeError(f"GHL upsert не вернул contact id: {contact!r}")

    if lead.notes:
        try:
            await client.add_note(contact_id, lead.notes)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось добавить note: %s", exc)

    opportunity_id: str | None = None
    if decision.is_valid and settings.ghl_pipeline_id:
        existing = await client.search_opportunities(
            contact_id=contact_id,
            pipeline_id=settings.ghl_pipeline_id,
        )
        if existing:
            opportunity_id = existing[0].get("id") or existing[0].get("_id")
            if opportunity_id:
                await client.update_opportunity_stage(
                    opportunity_id,
                    decision.stage_id,
                    status=decision.status,
                )
        else:
            opp = await client.create_opportunity(
                contact_id=contact_id,
                name=f"{lead.display_name()} — {lead.source}",
                stage_id=decision.stage_id,
                monetary_value=lead.monetary_value,
                status=decision.status,
            )
            opportunity_id = opp.get("id") or opp.get("_id")
    else:
        logger.info(
            "Stage не настроен для события %s (key=%s) или не задан pipeline — пропускаю opportunity",
            event,
            decision.stage_key,
        )

    return {
        "contact_id": contact_id,
        "opportunity_id": opportunity_id or "",
        "stage_key": decision.stage_key,
    }
