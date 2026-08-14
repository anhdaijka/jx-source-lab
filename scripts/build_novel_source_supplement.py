#!/usr/bin/env python3
"""Build the bounded source-recognition supplement for kiem-the-novel."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "novel-source-supplement"
GENERATOR = "scripts/build_novel_source_supplement.py"
SCHEMA_VERSION = "1.0"

INPUTS = {
    "items": ROOT / "generated/records/items/item-records.jsonl",
    "features": ROOT / "generated/records/features/feature-records.jsonl",
    "dialogue": ROOT / "generated/records/dialogue/dialognpc-records.jsonl",
    "localization": ROOT / "generated/records/dialogue/localization-records.jsonl",
    "npcs": ROOT / "generated/records/npcs/npc-records.jsonl",
    "baseline_handoff_manifest": ROOT / "generated/novel-handoff/handoff-manifest.json",
    "release_validation": ROOT / "generated/reports/release-validation-report.json",
}

WEAPON_GROUPS = {
    ("equip/general/meleeweapon.txt", "1"): "TRIỀN_THỦ",
    ("equip/general/meleeweapon.txt", "2"): "KIẾM",
    ("equip/general/meleeweapon.txt", "3"): "ĐAO",
    ("equip/general/meleeweapon.txt", "4"): "CÔN",
    ("equip/general/meleeweapon.txt", "5"): "THƯƠNG",
    ("equip/general/meleeweapon.txt", "6"): "CHÙY",
    ("equip/general/meleeweapon.txt", "7"): "NHUYỄN_KIẾM",
    ("equip/general/rangeweapon.txt", "1"): "PHI_TIÊU",
    ("equip/general/rangeweapon.txt", "2"): "PHI_ĐAO",
    ("equip/general/rangeweapon.txt", "3"): "TỤ_TIỄN",
}

SYSTEM_DEFINITIONS = [
    {
        "system_id": "SYS-GUILD-COMMUNITY",
        "name": "Bang hội và liên minh",
        "priority": 1,
        "source_scope": "The game directly exposes player guild presence and guild-linked representatives.",
        "narrative_causality_status": "UNKNOWN",
        "evidence_refs": [
            ("dialogue", "dialognpc:335"),
            ("features", "map-spawn:linanfu:line:203"),
        ],
    },
    {
        "system_id": "SYS-TEAM-FORMATION",
        "name": "Tổ đội",
        "priority": 1,
        "source_scope": "Vietnamese implementation strings directly establish voluntary team formation.",
        "narrative_causality_status": "IMPLEMENTATION_ONLY",
        "evidence_refs": [
            ("localization", "vi-vi:core:G_ScriptFuns_4"),
            ("localization", "vi-vi:core:MSG_TEAM_SEND_INVITE"),
        ],
    },
    {
        "system_id": "SYS-MILITARY-CAMPS",
        "name": "Quân doanh và đời sống quân trại",
        "priority": 2,
        "source_scope": "Camp locations and human-facing dialogue establish weapons work, separation and battlefield pressure.",
        "narrative_causality_status": "NOT_LINKED_TO_MAIN_STORY_BY_THIS_SUPPLEMENT",
        "evidence_refs": [
            ("dialogue", "dialognpc:65"),
            ("dialogue", "dialognpc:448"),
            ("features", "map-transfer:line:467"),
        ],
    },
    {
        "system_id": "SYS-SONG-JIN-BATTLEFIELD",
        "name": "Chiến trường Tống–Kim",
        "priority": 2,
        "source_scope": "Direct map/NPC/dialogue evidence establishes a recurring Song–Jin battlefield frame.",
        "narrative_causality_status": "MAIN_STORY_RELATION_REQUIRES_SEPARATE_SOURCE_MAPPING",
        "evidence_refs": [
            ("dialogue", "dialognpc:263"),
            ("features", "map-spawn:global_songjin_baomingdian:line:2"),
        ],
    },
    {
        "system_id": "SYS-BAI-HU-TANG",
        "name": "Bạch Hổ Đường",
        "priority": 4,
        "source_scope": "Direct NPC/map presence establishes Bạch Hổ Đường as a recognizable game activity space.",
        "narrative_causality_status": "UNKNOWN",
        "evidence_refs": [
            ("features", "map-spawn:linanfu:line:67"),
            ("npcs", "npc:7261"),
        ],
    },
    {
        "system_id": "SYS-XOYO-VALLEY",
        "name": "Tiêu Dao Cốc",
        "priority": 4,
        "source_scope": "Direct dialogue and NPC/map presence establish Tiêu Dao Cốc and its activity-facing cast.",
        "narrative_causality_status": "UNKNOWN",
        "evidence_refs": [
            ("dialogue", "dialognpc:64"),
            ("features", "map-spawn:dariluojusuo:line:6"),
            ("npcs", "npc:3234"),
        ],
    },
    {
        "system_id": "SYS-WULIN-LEAGUE",
        "name": "Võ Lâm Liên Đấu",
        "priority": 4,
        "source_scope": "Direct map representatives establish organized Wulin competition presence.",
        "narrative_causality_status": "IMPLEMENTATION_ONLY",
        "evidence_refs": [
            ("features", "map-spawn:linanfu:line:185"),
        ],
    },
    {
        "system_id": "SYS-MOUNTED-TRAVEL",
        "name": "Thú cưỡi và mạng trạm dịch",
        "priority": 3,
        "source_scope": "Mount catalog records and station configuration establish mounted travel and connected hubs.",
        "narrative_causality_status": "IMPLEMENTATION_ONLY",
        "evidence_refs": [
            ("dialogue", "dialognpc:33"),
            ("features", "travel_station:line:4"),
        ],
    },
    {
        "system_id": "SYS-WULIN-MASTER-ENCOUNTERS",
        "name": "Võ Lâm Cao Thủ",
        "priority": 4,
        "source_scope": "A direct map-spawn record establishes named high-level encounter presence only.",
        "narrative_causality_status": "LOW_CONTEXT_SOURCE_PRESENCE",
        "evidence_refs": [
            ("features", "map-spawn:yuanshisenlin_2:line:7"),
        ],
    },
]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def write_json(relative: str, value: dict) -> None:
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def project_item(row: dict) -> dict:
    return {
        "record_key": row["record_key"],
        "name": row.get("name", ""),
        "description": row.get("description", ""),
        "item_id": row.get("item_id", {}),
        "family": row.get("family", ""),
        "class_name": row.get("class_name", ""),
        "source_row_sha256": row.get("source_row_sha256", ""),
        "source_records": row.get("source_records", []),
    }


def project_evidence(row: dict) -> dict:
    projected = {
        "record_kind": row.get("record_kind"),
        "record_id": row.get("dialogue_id") or row.get("localization_id") or row.get("feature_id") or row.get("record_key"),
        "name": row.get("name", ""),
        "source_records": row.get("source_records", []),
    }
    if row.get("text"):
        projected["text"] = row["text"]
    if row.get("value"):
        projected["value"] = row["value"]
    if row.get("map_name"):
        projected["map_name"] = row["map_name"]
    if row.get("description"):
        projected["description"] = row["description"]
    raw = row.get("raw_fields", {})
    context = {
        key: raw[key]
        for key in ("MapName", "FromMap chú thích", "ToMap chú thích", "NpcName", "Title")
        if raw.get(key)
    }
    if context:
        projected["source_context"] = context
    return projected


def build() -> dict:
    if OUT.resolve().parent != (ROOT / "generated").resolve() or OUT.name != "novel-source-supplement":
        raise RuntimeError(f"Refusing to clean unexpected output path: {OUT}")
    if OUT.exists():
        shutil.rmtree(OUT)

    source_commit = git_head()
    items = load_jsonl(INPUTS["items"])
    features = load_jsonl(INPUTS["features"])
    dialogue = load_jsonl(INPUTS["dialogue"])
    localization = load_jsonl(INPUTS["localization"])
    npcs = load_jsonl(INPUTS["npcs"])

    weapon_rows = []
    for row in items:
        key = (row.get("family"), str(row.get("item_id", {}).get("ParticularType", "")))
        if key not in WEAPON_GROUPS:
            continue
        level = int(row.get("item_id", {}).get("Level", "0") or 0)
        if level not in {1, 5, 10} and key != ("equip/general/meleeweapon.txt", "7"):
            continue
        projected = project_item(row)
        projected.update({
            "catalog_group": WEAPON_GROUPS[key],
            "catalog_level": level,
            "source_status": "VERIFIED_DIRECT_RAW_SERVER",
            "narrative_importance_status": "UNKNOWN",
            "ownership_status": "UNKNOWN",
            "special_property_status": "UNKNOWN",
        })
        weapon_rows.append(projected)
    weapon_rows.sort(key=lambda row: (row["catalog_group"], row["catalog_level"], row["record_key"]))

    manual_groups: dict[str, list[dict]] = defaultdict(list)
    manual_pattern = re.compile(r"^Mật tịch (.+) \(([^)]+)\)$")
    for row in items:
        if row.get("family") != "equip/general/book.txt":
            continue
        match = manual_pattern.match(row.get("name", ""))
        if not match:
            continue
        manual_groups[match.group(1)].append({
            **project_item(row),
            "catalog_stage": match.group(2),
        })
    manuals = [
        {
            "route_name": route_name,
            "source_status": "VERIFIED_DIRECT_RAW_SERVER",
            "physical_manual_catalog_presence": True,
            "transmission_or_owner_status": "UNKNOWN",
            "narrative_power_status": "UNKNOWN",
            "variants": sorted(rows, key=lambda row: row["record_key"]),
        }
        for route_name, rows in sorted(manual_groups.items())
    ]

    mounts_by_kind: dict[str, list[dict]] = defaultdict(list)
    excluded_mount_markers = re.compile(r"Hoạt động đua top tài phú|Lỗi Không Dùng|^Tọa Kỵ$")
    for row in items:
        if row.get("class_name") != "horse":
            continue
        kind = row.get("kind", "").strip()
        if not kind or excluded_mount_markers.search(kind):
            continue
        mounts_by_kind[kind].append(project_item(row))
    mounts = [
        {
            "catalog_family": kind,
            "source_status": "VERIFIED_DIRECT_RAW_SERVER",
            "narrative_species_status": "UNKNOWN",
            "narrative_ability_status": "UNKNOWN",
            "wuxia_fit_status": "REQUIRES_ADAPTATION_REVIEW",
            "variants": sorted(rows, key=lambda row: row["record_key"]),
        }
        for kind, rows in sorted(mounts_by_kind.items())
    ]

    mantle_rows = []
    for row in items:
        if row.get("family") != "equip/general/mantle.txt":
            continue
        locator = row.get("source_records", [{}])[0].get("locator", "")
        match = re.fullmatch(r"line:(\d+)", locator)
        if not match or not 2 <= int(match.group(1)) <= 11:
            continue
        projected = project_item(row)
        projected.update({
            "source_status": "VERIFIED_DIRECT_RAW_SERVER",
            "reputation_or_rank_meaning_status": "GAMEPLAY_CATALOG_ONLY",
            "narrative_importance_status": "UNKNOWN",
        })
        mantle_rows.append(projected)

    indexes = {
        "items": {row["record_key"]: row for row in items},
        "features": {row["feature_id"]: row for row in features},
        "dialogue": {row["dialogue_id"]: row for row in dialogue},
        "localization": {row["localization_id"]: row for row in localization},
        "npcs": {row["record_key"]: row for row in npcs},
    }
    systems = []
    for definition in SYSTEM_DEFINITIONS:
        evidence = []
        for dataset, record_id in definition["evidence_refs"]:
            if record_id not in indexes[dataset]:
                raise KeyError(f"Missing curated evidence reference: {dataset}:{record_id}")
            evidence.append(project_evidence(indexes[dataset][record_id]))
        systems.append({
            **{key: value for key, value in definition.items() if key != "evidence_refs"},
            "existence_status": "VERIFIED_DIRECT_RAW_SERVER",
            "adaptation_status": "SOURCE_CANDIDATE_NOT_NOVEL_CANON",
            "evidence": evidence,
            "unsupported_without_further_evidence": [
                "mandatory participation",
                "novel causal role",
                "exact in-world rules",
                "main-story ownership",
                "game UI or accounting as prose texture",
            ],
        })

    write_json("catalog/weapons.json", {
        "schema_version": SCHEMA_VERSION,
        "status": "SOURCE_RECOGNITION_CANDIDATES",
        "count": len(weapon_rows),
        "selection_rule": "For each general weapon catalog group, retain levels 1, 5 and 10; retain the sole soft-sword row. Game levels do not become novel power ranks.",
        "weapons": weapon_rows,
    })
    write_json("catalog/route-manuals.json", {
        "schema_version": SCHEMA_VERSION,
        "status": "SOURCE_RECOGNITION_CANDIDATES",
        "count": len(manuals),
        "selection_rule": "Group every exact 'Mật tịch <route> (<stage>)' catalog record by the 24 source route names.",
        "manual_families": manuals,
    })
    write_json("catalog/mounts-and-mantles.json", {
        "schema_version": SCHEMA_VERSION,
        "status": "SOURCE_RECOGNITION_CANDIDATES",
        "mount_family_count": len(mounts),
        "mantle_count": len(mantle_rows),
        "selection_rule": "Mounts are grouped by direct catalog kind with event-leaderboard/error/generic placeholders excluded; mantles retain the ten base progression names before element/gender duplication.",
        "mounts": mounts,
        "mantles": mantle_rows,
    })
    write_json("systems/optional-system-candidates.json", {
        "schema_version": SCHEMA_VERSION,
        "status": "SOURCE_RECOGNITION_CANDIDATES",
        "count": len(systems),
        "curation_rule": "Retain only exact names, direct presence and bounded human-facing texture. Exclude funds, appointments, logs, registry paperwork, bookkeeping, UI procedure and reward-loop detail.",
        "systems": systems,
    })

    input_records = []
    for name, path in INPUTS.items():
        input_records.append({
            "name": name,
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        })
    write_json("provenance.json", {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_repository": "anhdaijka/jx-source-lab",
        "source_lab_commit": source_commit,
        "baseline_novel_handoff_manifest_sha256": sha256(INPUTS["baseline_handoff_manifest"]),
        "input_artifacts": input_records,
        "new_broad_source_research_performed": False,
        "raw_proprietary_payloads_excluded": True,
        "curation_scope": "Existing generated item, feature, dialogue, localization and NPC records only.",
        "source_truth_guard": "Catalog or system presence does not establish novel use, ownership, rarity, story causality, motive, outcome or power.",
    })

    payloads = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "supplement-manifest.json":
            payloads.append({
                "path": path.relative_to(OUT).as_posix(),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            })
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "handoff_status": "NOVEL_SOURCE_SUPPLEMENT_READY",
        "promotion_status": "SOURCE_RECOGNITION_SUPPLEMENT_READY",
        "source_repository": "anhdaijka/jx-source-lab",
        "source_lab_commit": source_commit,
        "baseline_novel_handoff_manifest_sha256": sha256(INPUTS["baseline_handoff_manifest"]),
        "scope": "BOUNDED_RECOGNITION_CATALOG_AND_OPTIONAL_SYSTEM_PRESENCE",
        "counts": {
            "weapon_candidates": len(weapon_rows),
            "route_manual_families": len(manuals),
            "mount_families": len(mounts),
            "mantle_candidates": len(mantle_rows),
            "optional_system_candidates": len(systems),
            "promoted_story_claims": 0,
        },
        "uncertainty": {
            "narrative_role_default": "UNKNOWN",
            "adaptation_status_default": "SOURCE_CANDIDATE_NOT_NOVEL_CANON",
            "implementation_only_records_preserved": True,
        },
        "excluded": [
            "raw client/server/PAK payloads",
            "bulk item and asset catalogs",
            "private-input and archives",
            "UI accounting, guild funds, appointments, logs and registry procedure",
            "invented story causality, ownership, rarity, motives, rewards or outcomes",
        ],
        "raw_proprietary_payloads_excluded": True,
        "one_way_import_contract": True,
        "runtime_dependency_on_lab": False,
        "files": payloads,
        "manifest_self_hash_note": "The manifest cannot recursively hash itself; every payload artifact is hashed above.",
    }
    write_json("supplement-manifest.json", manifest)
    return manifest


def main() -> None:
    manifest = build()
    print(json.dumps({
        "status": manifest["handoff_status"],
        "source_lab_commit": manifest["source_lab_commit"],
        "counts": manifest["counts"],
        "payload_files": len(manifest["files"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
