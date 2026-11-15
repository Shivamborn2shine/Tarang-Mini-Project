"""SQLAlchemy 2 ORM models matching PRD Section 8."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("map_mode IN ('indoor', 'outdoor')", name="ck_projects_map_mode"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    map_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    floorplans: Mapped[list[Floorplan]] = relationship(back_populates="project", cascade="all, delete-orphan")
    sessions: Mapped[list[SurveySession]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Floorplan(Base):
    __tablename__ = "floorplans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    width_px: Mapped[int] = mapped_column(Integer, nullable=False)
    height_px: Mapped[int] = mapped_column(Integer, nullable=False)
    scale_m_per_px: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    project: Mapped[Project] = relationship(back_populates="floorplans")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    os_version: Mapped[str] = mapped_column(String(64), nullable=False)
    app_version: Mapped[str] = mapped_column(String(64), nullable=False)
    capability_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SurveySession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)

    project: Mapped[Project] = relationship(back_populates="sessions")


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (
        CheckConstraint("kind IN ('wifi', 'cellular')", name="ck_obs_kind"),
        CheckConstraint("location_kind IN ('indoor', 'outdoor', 'unknown')", name="ck_obs_loc_kind"),
        CheckConstraint("x_norm IS NULL OR (x_norm >= 0.0 AND x_norm <= 1.0)", name="ck_obs_x_norm"),
        CheckConstraint("y_norm IS NULL OR (y_norm >= 0.0 AND y_norm <= 1.0)", name="ck_obs_y_norm"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    technology: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    location_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    floorplan_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    x_norm: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_norm: Mapped[float | None] = mapped_column(Float, nullable=True)
    freshness_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flags_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    wifi_detail: Mapped[WifiObservation | None] = relationship(
        back_populates="observation", uselist=False, cascade="all, delete-orphan"
    )
    cell_detail: Mapped[CellObservation | None] = relationship(
        back_populates="observation", uselist=False, cascade="all, delete-orphan"
    )


class WifiObservation(Base):
    __tablename__ = "wifi_observations"

    observation_id: Mapped[str] = mapped_column(
        ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True
    )
    ssid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bssid_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    frequency_mhz: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channel: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rssi_dbm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channel_width_mhz: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rx_link_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    tx_link_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    observation: Mapped[Observation] = relationship(back_populates="wifi_detail")


class CellObservation(Base):
    __tablename__ = "cell_observations"

    observation_id: Mapped[str] = mapped_column(
        ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True
    )
    operator_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mcc_mnc: Mapped[str | None] = mapped_column(String(16), nullable=True)
    subscription_slot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rsrp_dbm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rsrq_db: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sinr_db: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pci: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tac: Mapped[int | None] = mapped_column(Integer, nullable=True)

    observation: Mapped[Observation] = relationship(back_populates="cell_detail")


class SyncBatch(Base):
    __tablename__ = "sync_batches"

    batch_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
