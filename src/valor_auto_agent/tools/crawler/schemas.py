from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Source = Literal["olx", "standvirtual"]
Fuel = Literal["gasolina", "diesel", "hibrido", "eletrico", "gpl", "outro"]
Transmission = Literal["manual", "automatica", "outro"]


class Filters(BaseModel):
    brand: str | None = None
    model: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    price_min: int | None = None
    price_max: int | None = None
    km_max: int | None = None
    fuel: Fuel | None = None
    transmission: Transmission | None = None
    location: str | None = None


class Listing(BaseModel):
    source: Source
    external_id: str
    title: str
    price_eur: int | None = None
    year: int | None = None
    km: int | None = None
    fuel: Fuel | None = None
    transmission: Transmission | None = None
    location: str | None = None
    url: str
    image_url: str | None = None
    posted_at: datetime | None = None
    raw: dict = Field(default_factory=dict)
