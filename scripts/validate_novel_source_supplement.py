#!/usr/bin/env python3
"""Validate the bounded source-recognition supplement."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "novel-source-supplement"
REPORT = ROOT / "generated/reports/novel-source-supplement-validation-report.json"
EXPECTED_COUNTS = {
    "weapon_candidates": 28,
    "route_manual_families": 24,
    "mount_families": 22,
    "mantle_candidates": 10,
    "optional_system_candidates": 9,
    "promoted_story_claims": 0,
}
EXPECTED_FILES = {
    "catalog/weapons.json",
    "catalog/route-manuals.json",
    "catalog/mounts-and-mantles.json",
    "systems/optional-system-candidates.json",
    "provenance.json",
}
PROHIBITED_SUFFIXES = {".pak", ".exe", ".dll", ".zip", ".rar", ".7z", ".bin", ".spr", ".png", ".jpg", ".wav"}
PROHIBITED_ADAPTATION_NAMES = {"Tiêu Phùng", "Hạ Nương", "Tĩnh Xuyên", "Ân Đồng"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> dict:
    errors: list[str] = []
    checks: dict[str, int] = {}
    manifest_path = OUT / "supplement-manifest.json"
    if not manifest_path.is_file():
        return {"status": "NOVEL_SOURCE_SUPPLEMENT_BLOCKED", "checks": {}, "errors": ["Missing supplement manifest"]}
    manifest = load(manifest_path)
    checks["manifest_parsed"] = 1
    if manifest.get("handoff_status") != "NOVEL_SOURCE_SUPPLEMENT_READY":
        errors.append("Supplement is not ready")
    if manifest.get("promotion_status") != "SOURCE_RECOGNITION_SUPPLEMENT_READY":
        errors.append("Supplement has the wrong promotion state")
    if manifest.get("counts") != EXPECTED_COUNTS:
        errors.append(f"Unexpected curated counts: {manifest.get('counts')}")
    if not manifest.get("raw_proprietary_payloads_excluded") or not manifest.get("one_way_import_contract"):
        errors.append("Raw-payload/one-way contract is not explicit")
    if manifest.get("runtime_dependency_on_lab") is not False:
        errors.append("Supplement retains a Lab runtime dependency")

    listed = {row["path"]: row for row in manifest.get("files", [])}
    actual = {
        path.relative_to(OUT).as_posix(): path
        for path in OUT.rglob("*")
        if path.is_file() and path.name != "supplement-manifest.json"
    }
    if set(listed) != EXPECTED_FILES or set(actual) != EXPECTED_FILES:
        errors.append("Manifest or output contains an unexpected payload set")
    for relative, path in actual.items():
        if path.suffix.lower() != ".json" or path.suffix.lower() in PROHIBITED_SUFFIXES:
            errors.append(f"Prohibited payload type: {relative}")
        if listed.get(relative, {}).get("sha256") != sha256(path):
            errors.append(f"Hash mismatch: {relative}")
        if listed.get(relative, {}).get("bytes") != path.stat().st_size:
            errors.append(f"Byte count mismatch: {relative}")
        text = path.read_text(encoding="utf-8")
        if any(name in text for name in PROHIBITED_ADAPTATION_NAMES):
            errors.append(f"Adaptation character leaked into source supplement: {relative}")
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON {relative}: {exc}")
    checks["payload_hashes_checked"] = len(actual)

    weapons = load(OUT / "catalog/weapons.json")
    manuals = load(OUT / "catalog/route-manuals.json")
    mounts = load(OUT / "catalog/mounts-and-mantles.json")
    systems = load(OUT / "systems/optional-system-candidates.json")
    provenance = load(OUT / "provenance.json")
    if weapons.get("count") != 28 or len(weapons.get("weapons", [])) != 28:
        errors.append("Weapon curation count is not 28")
    if manuals.get("count") != 24 or len(manuals.get("manual_families", [])) != 24:
        errors.append("Route-manual family count is not 24")
    if any(len(row.get("variants", [])) != 5 for row in manuals.get("manual_families", [])):
        errors.append("A route-manual family does not preserve all five catalog stages")
    if mounts.get("mount_family_count") != 22 or len(mounts.get("mounts", [])) != 22:
        errors.append("Mount family count is not 22")
    if mounts.get("mantle_count") != 10 or len(mounts.get("mantles", [])) != 10:
        errors.append("Mantle count is not 10")
    if systems.get("count") != 9 or len(systems.get("systems", [])) != 9:
        errors.append("Optional-system candidate count is not 9")
    if "Exclude funds, appointments, logs, registry paperwork, bookkeeping" not in systems.get("curation_rule", ""):
        errors.append("Administrative-prose exclusion is missing")
    if any(row.get("adaptation_status") != "SOURCE_CANDIDATE_NOT_NOVEL_CANON" for row in systems.get("systems", [])):
        errors.append("A system candidate was silently promoted to novel canon")
    if provenance.get("new_broad_source_research_performed") is not False:
        errors.append("Provenance does not preserve the bounded research scope")
    if provenance.get("raw_proprietary_payloads_excluded") is not True:
        errors.append("Provenance does not exclude raw payloads")
    checks["semantic_catalogs_checked"] = 4

    total_bytes = sum(path.stat().st_size for path in OUT.rglob("*") if path.is_file())
    return {
        "status": "NOVEL_SOURCE_SUPPLEMENT_READY" if not errors else "NOVEL_SOURCE_SUPPLEMENT_BLOCKED",
        "checks": checks,
        "metrics": {**EXPECTED_COUNTS, "payload_files": len(actual), "total_bytes": total_bytes},
        "errors": errors,
    }


def main() -> None:
    result = validate()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not result["errors"] else 1)


if __name__ == "__main__":
    main()
