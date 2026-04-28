"""Выгрузка контактов и сделок (opportunities) из GHL в .xlsx."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from app.config import Settings, get_settings
from app.ghl.client import GHLClient

logger = logging.getLogger(__name__)


OPPORTUNITY_COLUMNS = [
    ("Opportunity ID", "id"),
    ("Name", "name"),
    ("Status", "status"),
    ("Stage", "pipelineStageId"),
    ("Pipeline", "pipelineId"),
    ("Monetary Value", "monetaryValue"),
    ("Contact ID", "contactId"),
    ("Contact Name", "contact.name"),
    ("Contact Email", "contact.email"),
    ("Contact Phone", "contact.phone"),
    ("Source", "source"),
    ("Created", "createdAt"),
    ("Updated", "updatedAt"),
]


def _dig(d: dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _stage_name_lookup(pipelines: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in pipelines:
        for st in p.get("stages", []) or []:
            sid = st.get("id") or st.get("_id")
            if sid:
                out[sid] = st.get("name", sid)
    return out


def _pipeline_name_lookup(pipelines: list[dict[str, Any]]) -> dict[str, str]:
    return {p.get("id") or p.get("_id"): p.get("name", "") for p in pipelines if p.get("id") or p.get("_id")}


async def fetch_all(client: GHLClient) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pipelines = await client.list_pipelines()
    opps = await client.search_opportunities(limit=100)
    return pipelines, opps


def write_workbook(
    path: Path,
    opportunities: list[dict[str, Any]],
    pipelines: list[dict[str, Any]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    stage_names = _stage_name_lookup(pipelines)
    pipeline_names = _pipeline_name_lookup(pipelines)

    # --- Sheet 1: Opportunities ---
    ws = wb.active
    ws.title = "Opportunities"
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="2E5984")
    for col_idx, (title, _) in enumerate(OPPORTUNITY_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.font = header_font
        cell.fill = header_fill

    for row_idx, opp in enumerate(opportunities, start=2):
        for col_idx, (_, key) in enumerate(OPPORTUNITY_COLUMNS, start=1):
            value = _dig(opp, key)
            if key == "pipelineStageId" and value:
                value = stage_names.get(value, value)
            elif key == "pipelineId" and value:
                value = pipeline_names.get(value, value)
            ws.cell(row=row_idx, column=col_idx, value=value)

    for col_idx, (title, _) in enumerate(OPPORTUNITY_COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = max(14, len(title) + 2)
    ws.freeze_panes = "A2"

    # --- Sheet 2: By stage ---
    summary = wb.create_sheet("By Stage")
    summary.cell(row=1, column=1, value="Pipeline").font = header_font
    summary.cell(row=1, column=2, value="Stage").font = header_font
    summary.cell(row=1, column=3, value="Count").font = header_font
    for col in (1, 2, 3):
        summary.cell(row=1, column=col).fill = header_fill

    counts: dict[tuple[str, str], int] = {}
    for opp in opportunities:
        sid = opp.get("pipelineStageId")
        pid = opp.get("pipelineId")
        key = (pipeline_names.get(pid, pid or ""), stage_names.get(sid, sid or ""))
        counts[key] = counts.get(key, 0) + 1

    for row_idx, ((pname, sname), count) in enumerate(sorted(counts.items()), start=2):
        summary.cell(row=row_idx, column=1, value=pname)
        summary.cell(row=row_idx, column=2, value=sname)
        summary.cell(row=row_idx, column=3, value=count)
    summary.column_dimensions["A"].width = 24
    summary.column_dimensions["B"].width = 24
    summary.column_dimensions["C"].width = 10

    wb.save(path)
    return path


async def export_to_excel(
    settings: Settings | None = None,
    out_path: Path | None = None,
) -> Path:
    settings = settings or get_settings()
    if not settings.ghl_api_token:
        raise RuntimeError("GHL_API_TOKEN не задан в .env")

    out_path = out_path or settings.export_dir / f"crm-export-{datetime.utcnow():%Y%m%d-%H%M%S}.xlsx"

    async with httpx.AsyncClient(timeout=60.0) as http:
        client = GHLClient(settings, client=http)
        pipelines, opps = await fetch_all(client)

    return write_workbook(out_path, opps, pipelines)
