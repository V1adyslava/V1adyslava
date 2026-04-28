from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ghl_api_token: str = Field(default="", alias="GHL_API_TOKEN")
    ghl_location_id: str = Field(default="", alias="GHL_LOCATION_ID")
    ghl_pipeline_id: str = Field(default="", alias="GHL_PIPELINE_ID")
    ghl_api_base: str = Field(default="https://services.leadconnectorhq.com")
    ghl_api_version: str = Field(default="2021-07-28")

    ghl_stage_new: str = Field(default="", alias="GHL_STAGE_NEW")
    ghl_stage_booked: str = Field(default="", alias="GHL_STAGE_BOOKED")
    ghl_stage_no_show: str = Field(default="", alias="GHL_STAGE_NO_SHOW")
    ghl_stage_qualified: str = Field(default="", alias="GHL_STAGE_QUALIFIED")
    ghl_stage_won: str = Field(default="", alias="GHL_STAGE_WON")
    ghl_stage_lost: str = Field(default="", alias="GHL_STAGE_LOST")

    calendly_signing_key: str = Field(default="", alias="CALENDLY_WEBHOOK_SIGNING_KEY")
    typeform_secret: str = Field(default="", alias="TYPEFORM_WEBHOOK_SECRET")
    site_form_token: str = Field(default="", alias="SITE_FORM_TOKEN")

    export_dir: Path = Field(default=Path("./exports"), alias="EXPORT_DIR")

    def stage_for(self, key: str) -> str:
        mapping = {
            "new": self.ghl_stage_new,
            "booked": self.ghl_stage_booked,
            "no_show": self.ghl_stage_no_show,
            "qualified": self.ghl_stage_qualified,
            "won": self.ghl_stage_won,
            "lost": self.ghl_stage_lost,
        }
        return mapping.get(key, "")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
