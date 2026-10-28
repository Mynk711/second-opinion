import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Project root = the folder above src/. Using it makes every path absolute,
# so scripts work no matter which folder you run them from.
ROOT = Path(__file__).resolve().parent.parent


class SECConfig(BaseModel):
    request_delay_seconds: float = Field(ge=0.1)  # below 0.1s would break SEC's rate limit
    timeout_seconds: int = Field(gt=0)


class DataConfig(BaseModel):
    raw_dir: Path
    processed_dir: Path


class DownloadConfig(BaseModel):
    form: str
    filings_per_company: int = Field(ge=1, le=10)
    tickers: list[str]


class Settings(BaseModel):
    sec: SECConfig
    data: DataConfig
    download: DownloadConfig
    sec_user_agent: str  # comes from .env, not from config.yaml


def load_settings(path=ROOT / "config.yaml"):
    load_dotenv(ROOT / ".env")
    values = yaml.safe_load(path.read_text())
    settings = Settings(**values, sec_user_agent=os.environ["SEC_USER_AGENT"])

    # Turn relative data paths into absolute ones under the project root
    settings.data.raw_dir = ROOT / settings.data.raw_dir
    settings.data.processed_dir = ROOT / settings.data.processed_dir
    return settings


settings = load_settings()