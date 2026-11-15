"""Validate TARANG canonical sample fixtures against observation.schema.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "packages" / "contracts" / "observation.schema.json"
SAMPLES_PATH = ROOT / "samples" / "canonical_observations.json"

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")

REQUIRED_KEYS = {
    "schema_version",
    "id",
    "session_id",
    "device_id",
    "kind",
    "technology",
    "source",
    "observed_at",
    "recorded_at",
    "location",
    "metrics",
    "network",
    "freshness_ms",
    "flags",
}


def validate_observation_structural(obs: dict) -> list[str]:
    """Zero-dependency structural validation matching observation.schema.json."""
    errors: list[str] = []
    missing = REQUIRED_KEYS - set(obs.keys())
    if missing:
        errors.append(f"Missing keys: {sorted(missing)}")
    if obs.get("schema_version") != 1:
        errors.append(f"Invalid schema_version: {obs.get('schema_version')}")
    for key in ("id", "session_id", "device_id"):
        val = obs.get(key)
        if not isinstance(val, str) or not UUID_RE.match(val):
            errors.append(f"Invalid UUID for {key}: {val!r}")
    for key in ("observed_at", "recorded_at"):
        val = obs.get(key)
        if not isinstance(val, str) or not UTC_RE.match(val):
            errors.append(f"Invalid UTC timestamp for {key}: {val!r}")
    if obs.get("kind") not in ("wifi", "cellular"):
        errors.append(f"Invalid kind: {obs.get('kind')!r}")
    loc = obs.get("location")
    if not isinstance(loc, dict):
        errors.append("location must be an object")
    else:
        lkind = loc.get("kind")
        if lkind == "indoor":
            if not UUID_RE.match(str(loc.get("floorplan_id", ""))):
                errors.append("indoor location requires valid floorplan_id UUID")
            for coord in ("x_norm", "y_norm"):
                v = loc.get(coord)
                if not isinstance(v, (int, float)) or not (0.0 <= v <= 1.0):
                    errors.append(f"indoor {coord} must be in [0, 1], got {v!r}")
        elif lkind == "outdoor":
            lat, lon = loc.get("lat"), loc.get("lon")
            if not isinstance(lat, (int, float)) or not (-90.0 <= lat <= 90.0):
                errors.append(f"outdoor lat out of range: {lat!r}")
            if not isinstance(lon, (int, float)) or not (-180.0 <= lon <= 180.0):
                errors.append(f"outdoor lon out of range: {lon!r}")
        elif lkind != "unknown":
            errors.append(f"Invalid location.kind: {lkind!r}")
    return errors


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    samples = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))

    try:
        import jsonschema  # type: ignore

        for idx, item in enumerate(samples):
            jsonschema.validate(instance=item, schema=schema)
            print(f"[jsonschema] sample[{idx}] ({item['kind']} / {item['source']}) OK")
    except ImportError:
        for idx, item in enumerate(samples):
            errs = validate_observation_structural(item)
            if errs:
                print(f"[structural] sample[{idx}] FAILED: {errs}", file=sys.stderr)
                return 1
            print(f"[structural] sample[{idx}] ({item['kind']} / {item['source']}) OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
