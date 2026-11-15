"""TARANG FastAPI v1 application."""

from __future__ import annotations

import csv
import io
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db import Base, engine, get_db
from app.models import (
    CellObservation,
    Device,
    Floorplan,
    Observation,
    Project,
    SurveySession,
    SyncBatch,
    WifiObservation,
    utc_now,
)
from app.schemas import (
    BatchIngestRequest,
    BatchIngestResponse,
    CanonicalObservationIn,
    DeviceOut,
    DeviceRegister,
    FloorplanOut,
    ItemOutcome,
    ProjectCreate,
    ProjectOut,
    SessionCreate,
    SessionOut,
    SessionPatch,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="TARANG API",
    version="1.0.0",
    description="Telecommunication Analysis, Radio-frequency Assessment, Network Geomapping",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.post("/api/v1/projects", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    proj = Project(id=str(uuid.uuid4()), name=payload.name, map_mode=payload.map_mode)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@app.get("/api/v1/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())))


@app.get("/api/v1/projects/{project_id}/sessions", response_model=list[SessionOut])
def list_project_sessions(project_id: str, db: Session = Depends(get_db)) -> list[SurveySession]:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return list(
        db.scalars(
            select(SurveySession)
            .where(SurveySession.project_id == project_id)
            .order_by(SurveySession.started_at.desc())
        )
    )


@app.post("/api/v1/projects/{project_id}/floorplans", response_model=FloorplanOut, status_code=201)
async def upload_floorplan(
    project_id: str,
    width_px: int = Form(..., ge=1),
    height_px: int = Form(..., ge=1),
    scale_m_per_px: float | None = Form(default=None, gt=0.0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Floorplan:
    proj = db.get(Project, project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if file.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(status_code=400, detail="Floorplan must be PNG or JPEG")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    fp_id = str(uuid.uuid4())
    ext = ".png" if file.content_type == "image/png" else ".jpg"
    dest = settings.upload_dir / f"{fp_id}{ext}"
    dest.write_bytes(await file.read())

    fp = Floorplan(
        id=fp_id,
        project_id=project_id,
        file_path=str(dest),
        width_px=width_px,
        height_px=height_px,
        scale_m_per_px=scale_m_per_px,
    )
    db.add(fp)
    db.commit()
    db.refresh(fp)
    return fp


@app.post("/api/v1/devices/register", response_model=DeviceOut, status_code=201)
def register_device(payload: DeviceRegister, db: Session = Depends(get_db)) -> Device:
    dev_id = str(payload.id)
    existing = db.get(Device, dev_id)
    if existing is not None:
        existing.platform = payload.platform
        existing.model = payload.model
        existing.os_version = payload.os_version
        existing.app_version = payload.app_version
        existing.capability_json = payload.capability_json
        db.commit()
        db.refresh(existing)
        return existing

    dev = Device(
        id=dev_id,
        platform=payload.platform,
        model=payload.model,
        os_version=payload.os_version,
        app_version=payload.app_version,
        capability_json=payload.capability_json,
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    return dev


@app.post("/api/v1/sessions", response_model=SessionOut, status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)) -> SurveySession:
    if db.get(Project, str(payload.project_id)) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if db.get(Device, str(payload.device_id)) is None:
        raise HTTPException(status_code=404, detail="Device not found")

    sess = SurveySession(
        id=str(payload.id or uuid.uuid4()),
        project_id=str(payload.project_id),
        device_id=str(payload.device_id),
        settings_json=payload.settings_json,
        status="active",
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


@app.patch("/api/v1/sessions/{session_id}", response_model=SessionOut)
def update_session(session_id: str, payload: SessionPatch, db: Session = Depends(get_db)) -> SurveySession:
    sess = db.get(SurveySession, session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.status is not None:
        sess.status = payload.status
        if payload.status == "completed" and sess.ended_at is None:
            sess.ended_at = utc_now()
    if payload.ended_at is not None:
        sess.ended_at = payload.ended_at
    db.commit()
    db.refresh(sess)
    return sess


@app.post("/api/v1/observations/batch", response_model=BatchIngestResponse)
def ingest_batch(payload: BatchIngestRequest, db: Session = Depends(get_db)) -> BatchIngestResponse:
    outcomes: list[ItemOutcome] = []
    accepted = 0
    duplicates = 0
    rejected = 0

    validated_items: list[tuple[int, CanonicalObservationIn]] = []
    for idx, raw_item in enumerate(payload.observations):
        raw_id = str(raw_item.get("id")) if isinstance(raw_item, dict) and raw_item.get("id") else None
        try:
            obs_in = CanonicalObservationIn.model_validate(raw_item)
            validated_items.append((idx, obs_in))
        except ValidationError as exc:
            rejected += 1
            outcomes.append(ItemOutcome(id=raw_id, status="rejected", reason=exc.errors()[0]["msg"]))

    candidate_ids = [str(item.id) for _, item in validated_items]
    existing_ids: set[str] = set()
    if candidate_ids:
        existing_ids = set(
            db.scalars(select(Observation.id).where(Observation.id.in_(candidate_ids)))
        )

    session_ids = {str(item.session_id) for _, item in validated_items}
    valid_sessions: set[str] = set()
    if session_ids:
        valid_sessions = set(
            db.scalars(select(SurveySession.id).where(SurveySession.id.in_(session_ids)))
        )

    seen_in_batch: set[str] = set()
    item_outcomes: dict[int, ItemOutcome] = {}

    for idx, obs_in in validated_items:
        obs_id = str(obs_in.id)
        if obs_id in existing_ids or obs_id in seen_in_batch:
            duplicates += 1
            item_outcomes[idx] = ItemOutcome(id=obs_id, status="duplicate", reason="Already ingested")
            continue
        if str(obs_in.session_id) not in valid_sessions:
            rejected += 1
            item_outcomes[idx] = ItemOutcome(id=obs_id, status="rejected", reason="Unknown session_id")
            continue

        seen_in_batch.add(obs_id)
        loc = obs_in.location
        obs_row = Observation(
            id=obs_id,
            schema_version=obs_in.schema_version,
            session_id=str(obs_in.session_id),
            device_id=str(obs_in.device_id),
            observed_at=obs_in.observed_at,
            recorded_at=obs_in.recorded_at,
            kind=obs_in.kind,
            technology=obs_in.technology,
            source=obs_in.source,
            location_kind=loc.kind,
            lat=loc.lat if loc.kind == "outdoor" else None,
            lon=loc.lon if loc.kind == "outdoor" else None,
            gps_accuracy_m=loc.gps_accuracy_m if loc.kind == "outdoor" else None,
            floorplan_id=str(loc.floorplan_id) if loc.kind == "indoor" else None,
            x_norm=loc.x_norm if loc.kind == "indoor" else None,
            y_norm=loc.y_norm if loc.kind == "indoor" else None,
            freshness_ms=obs_in.freshness_ms,
            flags_json=obs_in.flags,
        )

        if obs_in.kind == "wifi":
            obs_row.wifi_detail = WifiObservation(
                observation_id=obs_id,
                ssid=obs_in.network.get("ssid"),
                bssid_hash=obs_in.network.get("bssid_hash"),
                frequency_mhz=obs_in.metrics.get("frequency_mhz"),
                channel=obs_in.metrics.get("channel"),
                rssi_dbm=obs_in.metrics.get("rssi_dbm"),
                quality_percent=obs_in.metrics.get("quality_percent"),
                channel_width_mhz=obs_in.metrics.get("channel_width_mhz"),
                rx_link_mbps=obs_in.metrics.get("rx_link_mbps"),
                tx_link_mbps=obs_in.metrics.get("tx_link_mbps"),
                is_connected=bool(obs_in.network.get("is_connected", False)),
            )
        else:
            obs_row.cell_detail = CellObservation(
                observation_id=obs_id,
                operator_name=obs_in.network.get("operator_name"),
                mcc_mnc=obs_in.network.get("mcc_mnc"),
                subscription_slot=obs_in.network.get("subscription_slot"),
                is_registered=bool(obs_in.metrics.get("is_registered", False)),
                rsrp_dbm=obs_in.metrics.get("rsrp_dbm"),
                rsrq_db=obs_in.metrics.get("rsrq_db"),
                sinr_db=obs_in.metrics.get("sinr_db"),
                pci=obs_in.metrics.get("pci"),
                tac=obs_in.metrics.get("tac"),
            )

        db.add(obs_row)
        accepted += 1
        item_outcomes[idx] = ItemOutcome(id=obs_id, status="accepted")

    # Preserve input order for outcomes
    ordered_outcomes: list[ItemOutcome] = []
    rej_iter = iter(outcomes)
    for i in range(len(payload.observations)):
        if i in item_outcomes:
            ordered_outcomes.append(item_outcomes[i])
        else:
            ordered_outcomes.append(next(rej_iter))

    batch_id_str = str(payload.batch_id)
    if db.get(SyncBatch, batch_id_str) is None:
        db.add(
            SyncBatch(
                batch_id=batch_id_str,
                device_id=str(payload.device_id),
                accepted_count=accepted,
                duplicate_count=duplicates,
                rejected_count=rejected,
            )
        )
    db.commit()

    return BatchIngestResponse(
        batch_id=batch_id_str,
        accepted_count=accepted,
        duplicate_count=duplicates,
        rejected_count=rejected,
        outcomes=ordered_outcomes,
    )


def _serialize_observation(obs: Observation) -> dict[str, Any]:
    if obs.location_kind == "indoor":
        loc = {"kind": "indoor", "floorplan_id": obs.floorplan_id, "x_norm": obs.x_norm, "y_norm": obs.y_norm}
    elif obs.location_kind == "outdoor":
        loc = {"kind": "outdoor", "lat": obs.lat, "lon": obs.lon, "gps_accuracy_m": obs.gps_accuracy_m}
    else:
        loc = {"kind": "unknown"}

    if obs.kind == "wifi" and obs.wifi_detail is not None:
        w = obs.wifi_detail
        metrics = {
            "rssi_dbm": w.rssi_dbm,
            "quality_percent": w.quality_percent,
            "frequency_mhz": w.frequency_mhz,
            "channel": w.channel,
            "channel_width_mhz": w.channel_width_mhz,
            "rx_link_mbps": w.rx_link_mbps,
            "tx_link_mbps": w.tx_link_mbps,
        }
        network = {"ssid": w.ssid, "bssid_hash": w.bssid_hash, "is_connected": w.is_connected}
    elif obs.cell_detail is not None:
        c = obs.cell_detail
        metrics = {
            "rsrp_dbm": c.rsrp_dbm,
            "rsrq_db": c.rsrq_db,
            "sinr_db": c.sinr_db,
            "pci": c.pci,
            "tac": c.tac,
            "is_registered": c.is_registered,
        }
        network = {
            "operator_name": c.operator_name,
            "mcc_mnc": c.mcc_mnc,
            "subscription_slot": c.subscription_slot,
        }
    else:
        metrics = {}
        network = {}

    return {
        "schema_version": obs.schema_version,
        "id": obs.id,
        "session_id": obs.session_id,
        "device_id": obs.device_id,
        "kind": obs.kind,
        "technology": obs.technology,
        "source": obs.source,
        "observed_at": obs.observed_at.isoformat(),
        "recorded_at": obs.recorded_at.isoformat(),
        "freshness_ms": obs.freshness_ms,
        "location": loc,
        "metrics": metrics,
        "network": network,
        "flags": obs.flags_json,
    }


@app.get("/api/v1/sessions/{session_id}/observations")
def get_session_observations(
    session_id: str,
    kind: str | None = Query(default=None),
    technology: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if db.get(SurveySession, session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stmt = (
        select(Observation)
        .options(joinedload(Observation.wifi_detail), joinedload(Observation.cell_detail))
        .where(Observation.session_id == session_id)
    )
    count_stmt = select(func.count(Observation.id)).where(Observation.session_id == session_id)
    if kind:
        stmt = stmt.where(Observation.kind == kind)
        count_stmt = count_stmt.where(Observation.kind == kind)
    if technology:
        stmt = stmt.where(Observation.technology == technology)
        count_stmt = count_stmt.where(Observation.technology == technology)

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(Observation.observed_at.asc()).offset(offset).limit(limit)).all()
    return {
        "session_id": session_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_serialize_observation(r) for r in rows],
    }


@app.get("/api/v1/projects/{project_id}/summary")
def project_summary(project_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    proj = db.get(Project, project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")

    session_ids = list(db.scalars(select(SurveySession.id).where(SurveySession.project_id == project_id)))
    if not session_ids:
        return {"project_id": project_id, "total_observations": 0, "by_kind": {}, "by_technology": {}}

    total = db.scalar(select(func.count(Observation.id)).where(Observation.session_id.in_(session_ids))) or 0
    kind_rows = db.execute(
        select(Observation.kind, func.count(Observation.id))
        .where(Observation.session_id.in_(session_ids))
        .group_by(Observation.kind)
    ).all()
    tech_rows = db.execute(
        select(Observation.technology, func.count(Observation.id))
        .where(Observation.session_id.in_(session_ids))
        .group_by(Observation.technology)
    ).all()

    return {
        "project_id": project_id,
        "session_count": len(session_ids),
        "total_observations": total,
        "by_kind": dict(kind_rows),
        "by_technology": dict(tech_rows),
    }


@app.get("/api/v1/projects/{project_id}/export")
def export_project_csv(
    project_id: str,
    format: str = Query(default="csv"),
    redact: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    if format != "csv":
        raise HTTPException(status_code=400, detail="Only format=csv is supported in v1")
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    session_ids = list(db.scalars(select(SurveySession.id).where(SurveySession.project_id == project_id)))
    rows: list[Observation] = []
    if session_ids:
        rows = list(
            db.scalars(
                select(Observation)
                .options(joinedload(Observation.wifi_detail), joinedload(Observation.cell_detail))
                .where(Observation.session_id.in_(session_ids))
                .order_by(Observation.observed_at.asc())
            )
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "session_id",
            "kind",
            "technology",
            "source",
            "observed_at_utc",
            "recorded_at_utc",
            "freshness_ms",
            "location_kind",
            "lat",
            "lon",
            "gps_accuracy_m",
            "x_norm",
            "y_norm",
            "rssi_dbm",
            "quality_percent",
            "rsrp_dbm",
            "rsrq_db",
            "sinr_db",
            "ssid",
            "flags",
        ]
    )
    for r in rows:
        w = r.wifi_detail
        c = r.cell_detail
        ssid_val = "<REDACTED>" if (redact and w and w.ssid) else (w.ssid if w else None)
        writer.writerow(
            [
                r.id,
                r.session_id,
                r.kind,
                r.technology,
                r.source,
                r.observed_at.isoformat(),
                r.recorded_at.isoformat(),
                r.freshness_ms,
                r.location_kind,
                r.lat,
                r.lon,
                r.gps_accuracy_m,
                r.x_norm,
                r.y_norm,
                w.rssi_dbm if w else None,
                w.quality_percent if w else None,
                c.rsrp_dbm if c else None,
                c.rsrq_db if c else None,
                c.sinr_db if c else None,
                ssid_val,
                ",".join(r.flags_json),
            ]
        )

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="tarang_{project_id}.csv"'},
    )
