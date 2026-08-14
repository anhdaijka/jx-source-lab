# JX SOURCE LAB — AGENT RULES

This workspace is **source archaeology**, NOT novel writing.

Highest rule: **Raw evidence first. Official evidence second. Reconstruction third. Inference labeled. Fiction forbidden.**

## 1. Source safety
Treat `client/`, `server/`, `official-pages/`, `private-input/` and original archives as READ-ONLY evidence.
Do not modify/delete/rename/repack originals, execute unknown game binaries, or upload raw proprietary assets without explicit authorization.
Derived writes belong only in `generated/`, `research/`, `database/work/`, `manifests/`, or tooling folders.

## 2. No novelization
Do not write novel prose/specs/arcs in this lab. Never invent causal links, motives, culprits, relationships, dialogue, item purposes, route meanings, locations or outcomes. Insufficient evidence = `UNKNOWN`.
**Task title = identifier/lead, not enough evidence for a micro-event.**

## 3. Evidence classes
`RAW_SERVER`, `RAW_CLIENT`, `OFFICIAL_KINGSOFT_XOYO`, `OFFICIAL_VNG`, `OFFICIAL_ARCHIVE`, `CROSS_SOURCE_CONFIRMED`, `INFERENCE`, `UNKNOWN`, `EDITION_DRIFT`, `LEGACY_LEAD`.
Never silently promote inference/unknown/drift/legacy lead into fact.

## 4. Provenance
Every extracted/reconstructed claim must retain source type, path/URL reference, edition/build if known, record/task/key, locator where practical, source hash where practical, and parser/extractor version. No provenance = not promotable.

## 5. Editions
Raw private/later builds prove what **that build contains**, not automatically launch-era producer canon. Record origin/build/version/language/date/modified status/encoding/hash where possible. Conflicts = `EDITION_DRIFT`.

## 6. Quest reconstruction
Correct order:
`task id → dependency/condition → giver/turn-in → task body → dialogue → objective → map → item/script refs → completion effect → next task → causal reconstruction`.
Never: `task title → guessed plot`.
Separate player action, NPC statement, implementation fact, official lore and unknown.

## 7. Client / PAK forensics
Before extraction: inventory + hash archives → search source for loader/package APIs → identify header/index/compression/encryption from evidence → write READ-ONLY extractor → test copied samples → extract text/config first → assets later. Do not brute-force what source code can explain.

## 8. Generated data
Prefer deterministic parsers. Generated artifacts state generator, input scope, timestamp and schema version. Fix parser and regenerate; do not hand-edit generated facts.

## 9. Database
SQLite is a derived index, never higher authority than raw/official evidence. Rows must trace to source records.

## 10. Codex execution
Batch reads → inspect representative samples → implement parser → run small scope → compare generated output to raw → fix → expand. Avoid parse-everything-first.

## 11. Stop conditions
Ask user only for genuine decisions: edition/build identity, destructive action, unavailable archive key/password, authoritative edition conflict changing interpretation, or source-ownership/redistribution decision. Missing story info is NOT a reason to invent; mark UNKNOWN and continue.

## 12. Promotion gate
Promote material to a future novel repo only after provenance, edition status, contradiction log and confidence review exist. Future novel continuity can never override a later higher-authority source correction.
