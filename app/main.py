"""FastAPI приложение: webhooks + endpoint для ручного экспорта в Excel."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.config import get_settings
from app.export.excel import export_to_excel
from app.webhooks import calendly, site, typeform

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="GHL CRM Integration", version="0.1.0")
app.include_router(calendly.router)
app.include_router(typeform.router)
app.include_router(site.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/export/excel")
async def export_excel(filename: str | None = None) -> FileResponse:
    settings = get_settings()
    out_path: Path | None = None
    if filename:
        out_path = settings.export_dir / filename
    path = await export_to_excel(out_path=out_path)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )
