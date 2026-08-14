# JX SOURCE LAB — AGENT RULES

This workspace is **source archaeology**, NOT novel writing.

Highest rule: **Lore/story evidence first. Cross-source coherence second. Reconstruction third. Inference labeled. Fiction forbidden.**

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
Every extracted/reconstructed claim must retain source type, path/URL reference, record/task/key, locator where practical, source hash where practical, and parser/extractor version. Build/edition metadata is useful when known but is not required for promotion unless it changes a story/lore interpretation. No usable provenance = not promotable.

## 5. Lore target and build policy
The target canon is the **latest coherent Kiếm Thế lore supported by the combined research corpus**, not preservation of one pristine launch-era build.

The supplied client/server may be community-modified or feature-extended. This does not lower their usefulness for story reconstruction when story-bearing data remains consistent with the wider lore corpus.

Do not spend research time identifying exact client/server version, origin or modification history unless a concrete narrative contradiction requires it. Record version/build values when cheaply available, but treat them as metadata rather than a hard gate.

Existing client/server differences may remain `EDITION_DRIFT`. Only drift that materially changes a load-bearing story claim, character identity, motive, event order, reveal, outcome, sect lore, named martial art, named item or location meaning requires narrative arbitration.

## 6. Quest reconstruction
Correct order:
`task id → dependency/condition → giver/turn-in → task body → dialogue → objective → map → item/script refs → completion effect → next task → causal reconstruction`.
Never: `task title → guessed plot`.
Separate player action, NPC statement, implementation fact, official lore and unknown.

## 7. Client / PAK forensics
Before extraction: inventory archives → search source for loader/package APIs → identify header/index/compression/encryption from evidence → write READ-ONLY extractor → test copied samples → extract text/config first → assets later. Hashing is useful for provenance but do not perform expensive archive/version archaeology unless it contributes to story recovery or source integrity.

## 8. Generated data
Prefer deterministic parsers. Generated artifacts state generator, input scope, timestamp and schema version. Fix parser and regenerate; do not hand-edit generated facts.

## 9. Database
SQLite is a derived index, never higher authority than raw/official evidence. Rows must trace to source records.

## 10. Codex execution
Batch reads → inspect representative samples → implement parser → run small scope → compare generated output to raw → fix → expand. Avoid parse-everything-first.
Prioritize work that resolves central story causality, lore concordance, named characters/factions/skills/items/locations and major arc outcomes over low-value build/version forensics.

## 11. Stop conditions
Ask user only for genuine decisions: destructive action, unavailable archive key/password, a **material narrative conflict** between credible sources that changes canon interpretation, or source-ownership/redistribution decision. Missing story info is NOT a reason to invent; mark UNKNOWN and continue. Exact build/edition identity alone is NOT a user-decision blocker.

## 12. Promotion gate
Promote material to a future novel repo after provenance, central-story reconstruction, contradiction handling and confidence review are sufficient for the affected lore. Non-narrative implementation drift and non-central UNKNOWNs do not block promotion. Future novel continuity can never override a later better-supported source correction.

## 13. Usage-efficient model recommendation
At the end of every work report or handoff, if a next step remains, recommend the most usage-efficient suitable model among GPT-5.6 Sol, Terra, and Luna, together with the lowest sufficient reasoning level. Base the recommendation on the actual complexity and risk of the next step, not on the current model. Give one primary recommendation and a brief reason; do not recommend a more expensive model or reasoning level unless it is materially needed for correctness or safety.
