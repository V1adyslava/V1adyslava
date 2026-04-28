"""Клиент GoHighLevel API v2 (LeadConnector).

Документация: https://highlevel.stoplight.io/docs/integrations/
Используем Bearer-токен Private Integration.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.ghl.models import Lead

logger = logging.getLogger(__name__)


class GHLError(RuntimeError):
    pass


class GHLClient:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings()
        self._client = client

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.ghl_api_token}",
            "Version": self.settings.ghl_api_version,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.settings.ghl_api_base}{path}"
        close_after = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=30.0)
            close_after = True
        try:
            resp = await client.request(method, url, headers=self._headers, **kwargs)
            if resp.status_code >= 400:
                logger.error("GHL %s %s -> %s: %s", method, path, resp.status_code, resp.text)
                raise GHLError(f"GHL {method} {path} failed: {resp.status_code} {resp.text}")
            if not resp.content:
                return {}
            return resp.json()
        finally:
            if close_after:
                await client.aclose()

    # ---------- Contacts ----------

    async def upsert_contact(self, lead: Lead) -> dict[str, Any]:
        """Создать или обновить контакт. GHL дедуплицирует по email/phone в локации."""
        payload: dict[str, Any] = {
            "locationId": self.settings.ghl_location_id,
            "source": lead.source,
            "tags": lead.tags,
        }
        if lead.email:
            payload["email"] = lead.email
        if lead.phone:
            payload["phone"] = lead.phone
        if lead.first_name:
            payload["firstName"] = lead.first_name
        if lead.last_name:
            payload["lastName"] = lead.last_name
        if lead.full_name and not (lead.first_name or lead.last_name):
            payload["name"] = lead.full_name
        if lead.custom_fields:
            payload["customFields"] = [
                {"key": k, "field_value": v} for k, v in lead.custom_fields.items()
            ]

        data = await self._request("POST", "/contacts/upsert", json=payload)
        return data.get("contact", data)

    async def get_contact(self, contact_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/contacts/{contact_id}")
        return data.get("contact", data)

    async def add_note(self, contact_id: str, body: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/contacts/{contact_id}/notes",
            json={"body": body},
        )

    async def add_tags(self, contact_id: str, tags: list[str]) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/contacts/{contact_id}/tags",
            json={"tags": tags},
        )

    # ---------- Opportunities (сделки в воронке) ----------

    async def create_opportunity(
        self,
        contact_id: str,
        name: str,
        stage_id: str,
        monetary_value: float | None = None,
        status: str = "open",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "locationId": self.settings.ghl_location_id,
            "pipelineId": self.settings.ghl_pipeline_id,
            "pipelineStageId": stage_id,
            "name": name,
            "status": status,
            "contactId": contact_id,
        }
        if monetary_value is not None:
            payload["monetaryValue"] = monetary_value
        data = await self._request("POST", "/opportunities/", json=payload)
        return data.get("opportunity", data)

    async def update_opportunity_stage(
        self,
        opportunity_id: str,
        stage_id: str,
        status: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"pipelineStageId": stage_id}
        if status:
            payload["status"] = status
        data = await self._request("PUT", f"/opportunities/{opportunity_id}", json=payload)
        return data.get("opportunity", data)

    async def search_opportunities(
        self,
        contact_id: str | None = None,
        pipeline_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "location_id": self.settings.ghl_location_id,
            "limit": limit,
        }
        if contact_id:
            params["contact_id"] = contact_id
        if pipeline_id:
            params["pipeline_id"] = pipeline_id
        data = await self._request("GET", "/opportunities/search", params=params)
        return data.get("opportunities", [])

    # ---------- Pipelines ----------

    async def list_pipelines(self) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            "/opportunities/pipelines",
            params={"locationId": self.settings.ghl_location_id},
        )
        return data.get("pipelines", [])
