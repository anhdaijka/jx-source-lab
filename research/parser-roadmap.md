# Minimum Parser Roadmap

- Status: implemented for Research Release 1.0; canonical outputs are under `generated/records/` and summarized by `generated/reports/domain-corpus-report.json`.
- Scope: raw `server/` first; client data is a comparison source until edition alignment is established.
- Rule: every emitted record must retain source root, path, row/line locator, source hash where available, parser version, encoding decision, and evidence class.

## 1. Tasks and dependencies

Start with tabular rows in `server/gameserver/setting/task/task_def.txt` and objective tables such as `server/gameserver/setting/task/linktask/entity_killnpc.txt`. Parse headers and data rows without interpreting titles or descriptions as plot. Follow references only when a field/validated script locator explicitly links task IDs, NPC IDs, item IDs, or map IDs.

Next, inspect task/mission Lua in `server/gameserver/script/task/` and `server/Gamecenter/script/mission/` for calls that read/write task state. Emit implementation edges separately from player action, dialogue, or causal reconstruction.

## 2. Dialogue and localization

Begin with the key/value table shape visible in `server/Gamecenter/l10n/vi-vi/stringtable_core.txt`; compare same keys with `zh-cn` and `zh-tw` only as edition/language evidence. Add dialogue only where a script or data record references an explicit localization key or literal. Do not use generic UI strings as quest dialogue.

## 3. NPCs

Parse the tab-separated schema in `server/gameserver/setting/npc/npc.txt`, retaining `Id`, names, description, resource path, and script parameters as implementation fields. Treat `server/gameserver/setting/npc/dialognpc.txt` as a separate candidate relationship source requiring its own header/encoding validation.

## 4. Sects, routes, and skills

Parse XML structurally from `server/gameserver/setting/faction/faction.xml`, preserving faction and route IDs. Parse `server/gameserver/setting/fightskill/skill.txt` as a header-driven table and link skill fields such as `SkillId`, `FactionLimit`, and `RouteLimit` only after type/empty-value rules are documented.

## 5. Items

Build a family-aware TSV parser beginning with `server/gameserver/setting/item/001/equip/general/armor.txt`. Preserve file-relative item-family provenance because object IDs may not be globally unique without category/genre/detail fields. Defer normalization of property columns until the base-row parser has validation fixtures.

## 6. Maps, locations, and features

Start with `server/gameserver/setting/map/maplist.txt`; emit map identity, template/resource/info-file references, type, level, and domain as raw fields. Add transport, waypoint, NPC-area, and trap relationships only from explicit tables under `setting/map/` and relevant `map_info/` paths.

## Cross-cutting implementation order

1. Implement one reusable encoding detector and TSV reader that preserves raw bytes and reports malformed rows.
2. Add fixture-based parsers for the six representative files above; compare header/row counts against raw input.
3. Emit one record family at a time to `generated/records/` using the existing schemas, with no cross-source merge by default.
4. Add explicit reference resolvers and an unresolved-reference ledger; unresolved IDs remain `UNKNOWN`.
5. Only after server extraction is stable, compare corresponding client and PAK-derived data and record mismatches as `EDITION_DRIFT`.

## Completion evidence

- Task archive: 439 Task roots, 631 Sub roots, and 5,547 validated task/reference edges.
- Dialogue/localization: literal dialog NPC records, task phase dialogue, and 1,366 `vi-vi` localization records kept as distinct families.
- NPC: 5,728 records with class-name ambiguity retained rather than silently merged.
- Faction/route/skill: 13 factions, 25 composite-key routes, 1,980 skill rows, and fully resolved explicit route-skill edges.
- Items: 28,786 records from 58 whitelisted definition tables; binary/NUL and non-definition `.txt` files are skipped with reasons.
- Map/features: 1,057 maps, runtime-proven transfer/category/protection/station/revive tables, and whitelisted map-info spawns.
- SQLite: `database/work/jx-source-lab.sqlite3` is regenerated from JSONL sources and validated with complete entity/edge lineage.
