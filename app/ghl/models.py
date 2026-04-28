from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class LeadSource(BaseModel):
    """Источник лида — Calendly / Typeform / Site form / etc."""

    name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class Lead(BaseModel):
    """Унифицированная модель лида до отправки в GHL."""

    email: EmailStr | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    source: str
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    scheduled_at: datetime | None = None
    monetary_value: float | None = None

    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts) or (self.email or self.phone or "Unknown")
