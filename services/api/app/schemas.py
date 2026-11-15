"""Pydantic v2 request/response contracts for TARANG API v1."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    map_mode: Literal["indoor", "outdoor"]


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    map_mode: str
    created_at: datetime


class FloorplanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    file_path: str
    width_px: int
    height_px: int
    scale_m_per_px: float | None


class DeviceRegister(BaseModel):
    id: UUID
    platform: Literal["android", "windows", "web", "other"]
    model: str = Field(min_length=1, max_length=128)
    os_version: str = Field(min_length=1, max_length=64)
    app_version: str = Field(min_length=1, max_length=64)
    capability_json: dict[str, Any] = Field(default_factory=dict)


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: str
    model: str
    os_version: str
    app_version: str
    capability_json: dict[str, Any]


class SessionCreate(BaseModel):
    id: UUID | None = None
    project_id: UUID
    device_id: UUID
    settings_json: dict[str, Any] = Field(default_factory=dict)


class SessionPatch(BaseModel):
    status: Literal["active", "paused", "completed"] | None = None
    ended_at: datetime | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    device_id: str
    started_at: datetime
    ended_at: datetime | None
    settings_json: dict[str, Any]
    status: str


class IndoorLocation(BaseModel):
    kind: Literal["indoor"]
    floorplan_id: UUID
    x_norm: float = Field(ge=0.0, le=1.0)
    y_norm: float = Field(ge=0.0, le=1.0)


class OutdoorLocation(BaseModel):
    kind: Literal["outdoor"]
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    gps_accuracy_m: float | None = Field(default=None, ge=0.0)


class UnknownLocation(BaseModel):
    kind: Literal["unknown"]


LocationPayload = Annotated[
    IndoorLocation | OutdoorLocation | UnknownLocation,
    Field(discriminator="kind"),
]


class CanonicalObservationIn(BaseModel):
    schema_version: Literal[1]
    id: UUID
    session_id: UUID
    device_id: UUID
    kind: Literal["wifi", "cellular"]
    technology: Literal[
        "wifi_2_4ghz",
        "wifi_5ghz",
        "wifi_6ghz",
        "wifi_unknown",
        "lte",
        "nr",
        "wcdma",
        "gsm",
        "unknown",
    ]
    source: Literal["android_wifi", "android_telephony", "windows_netsh", "windows_wlanapi"]
    observed_at: datetime
    recorded_at: datetime
    freshness_ms: int | None = Field(default=None, ge=0)
    location: LocationPayload
    metrics: dict[str, Any]
    network: dict[str, Any]
    flags: list[str] = Field(default_factory=list)


class BatchIngestRequest(BaseModel):
    batch_id: UUID
    device_id: UUID
    observations: list[dict[str, Any]] = Field(min_length=1, max_length=500)


class ItemOutcome(BaseModel):
    id: str | None
    status: Literal["accepted", "duplicate", "rejected"]
    reason: str | None = None


class BatchIngestResponse(BaseModel):
    batch_id: str
    accepted_count: int
    duplicate_count: int
    rejected_count: int
    outcomes: list[ItemOutcome]
