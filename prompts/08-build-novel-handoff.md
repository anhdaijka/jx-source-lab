# Codex task — build curated novel handoff

Use this only after `prompts/07-reconcile-internet-research.md` has been completed and its result has been persisted.

## Hard precondition
Before doing any handoff work, read:
- `AGENTS.md`
- `docs/source-authority.md`
- `docs/reconstruction-protocol.md`
- `docs/promotion-gates.md`
- the persisted outputs/state produced by prompt 07
- the current Research Release / confidence / unresolved-question artifacts relevant to story promotion

Then verify all of the following from persisted repo state, not chat memory:

- S3 story reconstruction is PASS or equivalent under the current lore-first policy;
- S4 cross-source lore validation is PASS or equivalent;
- S5 research release is PASS or equivalent;
- unresolved `CENTRAL_BLOCKER` count is zero;
- unresolved MATERIAL narrative conflicts count is zero, unless an explicit user canon decision has already been persisted;
- the final reconciliation result is exactly `NOVEL_PROMOTION_READY` or an equivalent persisted promotion-ready state.

If these conditions are not satisfied:
- DO NOT build a novel handoff;
- DO NOT copy partial story material into a handoff directory;
- report the exact persisted blocker(s) and stop at that integrity boundary.

Do not treat remaining `CENTRAL_TOLERABLE`, `NON_CENTRAL`, implementation-only `EDITION_DRIFT`, custom-feature differences, or unknown exact client/server version as blockers.

## Goal
Produce one compact, writer-facing, provenance-aware projection of the finalized JX Source Lab story/lore corpus for one-time import into `anhdaijka/kiem-the-novel/source-canon/`.

The handoff must answer:

> What game truth does the novel repo need in order to adapt the latest coherent Kiếm Thế lore without reopening raw source archaeology during normal writing work?

This is a source-canon handoff, NOT a novel outline, NOT adaptation planning, and NOT prose.

## Design principles
1. **Curated, not exhaustive.** Do not copy the entire Research Release.
2. **Story usefulness first.** Include material needed to reconstruct main story, characters, factions, sects, martial arts, important items, important locations and chronology.
3. **Traceable.** Every load-bearing claim must remain traceable back to Lab evidence or a reconciled official/research claim.
4. **No raw proprietary payloads.** Never include raw `client/`, `server/`, `.pak`, binaries, bulk extracted assets, private-input packages or full proprietary source files.
5. **No version archaeology requirement.** Exact client/server build identity is metadata only unless a MATERIAL narrative issue depends on it.
6. **No fiction.** Do not repair a source gap with novel invention.
7. **No novel assumptions.** Do not map the game player to Tiêu Phùng or any future novel protagonist here.
8. **One-way handoff.** The novel repo must not depend on this Lab repo at runtime and must not require automatic sync.

## Target output
Create or regenerate:

```text
generated/novel-handoff/
├── handoff-manifest.json
├── provenance.json
├── confidence-summary.json
│
├── game-story/
│   ├── master-chronology.md
│   ├── causal-spine.json
│   ├── arc-index.json
│   └── dossiers/
│       └── <one source-only dossier per promoted main-story arc>
│
├── characters/
├── factions/
├── sects/
├── martial-arts/
├── important-items/
├── important-locations/
│
├── concordance/
│   ├── cn-vi-names.json
│   ├── entity-aliases.json
│   └── task-story-map.json
│
└── unresolved/
    ├── central-tolerable.json
    ├── non-central.json
    └── material-conflicts.json
```

You may adjust filenames slightly to reuse strong existing schemas, but preserve these semantic groups. Do not create a parallel duplicate information system if the repo already has a better canonical representation.

## A. Handoff manifest
`handoff-manifest.json` must include at minimum:

- handoff schema version;
- source repository: `anhdaijka/jx-source-lab`;
- current source commit SHA;
- generation timestamp;
- canon target: `LATEST_COHERENT_KIEM_THE_LORE`;
- promotion status: `NOVEL_PROMOTION_READY`;
- S3/S4/S5 gate states;
- count of promoted main-story arcs/dossiers;
- count of unresolved `CENTRAL_BLOCKER` (must be 0);
- count of unresolved MATERIAL narrative conflicts (must be 0 unless already resolved by persisted user decision);
- counts of `CENTRAL_TOLERABLE` and `NON_CENTRAL` unresolved questions;
- file list with SHA-256 hashes for every handoff artifact;
- explicit statement that raw proprietary source/client/server/PAK payloads are excluded.

The manifest is the import contract for `kiem-the-novel`.

## B. Provenance
`provenance.json` should record enough information for later forensic lookup without forcing the novel repo to carry the full Lab corpus.

Include:
- Lab source commit;
- relevant Research Release identifier/state if one exists;
- reconciliation artifact identifiers/paths;
- source classes represented (`RAW_CLIENT`, `RAW_SERVER`, `OFFICIAL_KINGSOFT_XOYO`, `OFFICIAL_VNG`, `OFFICIAL_ARCHIVE`, etc.);
- known story-relevant limitations;
- important persisted user canon decisions if any;
- clear note that exact client/server build/version identity is not a promotion requirement under current policy.

Do not embed raw evidence payloads just to make provenance self-contained.

## C. Game-story projection
The handoff's `game-story/` is the most important part.

### `master-chronology.md`
Produce a concise source-only chronological reconstruction covering the promoted main story from beginning through the latest coherent supported lore.

For each major phase/arc, preserve:
- chronology/level range when known;
- major characters/factions involved;
- initiating problem;
- causal progression;
- important reveal/climax;
- outcome and downstream consequence;
- references to the full source dossier.

Do not turn it into chapter planning or literary narration.

### `causal-spine.json`
Represent the load-bearing causal chain in a machine-readable form.
Each node/edge should make clear:
- event/claim ID;
- predecessor/cause;
- resulting event/consequence;
- involved entities;
- evidence/confidence status;
- dossier/evidence reference.

Only include causal edges supported strongly enough for promotion. Unknown optional transitions may remain absent or explicitly marked.

### `arc-index.json`
List promoted story arcs with:
- stable arc ID;
- names/aliases;
- chronology or level range;
- dossier path;
- principal characters/factions;
- status/confidence;
- central unresolved count;
- important martial/item/location references.

### Dossiers
Reuse or project the final source-only GAME STORY DOSSIERS produced during reconstruction/reconciliation.
Every dossier must preserve:
- premise;
- characters;
- factions and evidenced goals;
- ordered causal events;
- what the player learns and when;
- conflict/reveal/climax/resolution;
- political/Wulin consequences;
- named martial arts, important items and important locations where evidenced;
- claim/evidence references;
- remaining tolerated unknowns;
- material contradiction status.

Do not embellish for readability beyond faithful source summarization.

## D. Character/faction/sect projection
Create compact writer-facing records only for entities that matter to promoted story or recurring Wulin/world continuity.

### Characters
Prefer one structured record per important character containing:
- canonical name + CN/VI aliases;
- source-backed role;
- affiliations;
- relationships relevant to game story;
- motives/goals where evidenced;
- major appearances/events;
- known martial association if evidenced;
- knowledge/reveal relevance where important;
- source references/confidence;
- unresolved identity/motive issues if any.

Do not invent personality traits merely because they would help a novel.

### Factions / sects
Include:
- identity and aliases;
- institutional role;
- alliances/enemies when evidenced;
- story goals/actions;
- major masters/representatives;
- story-relevant locations;
- sect routes and named martial arts where supported;
- major story consequences;
- source references/confidence.

This projection should help the novel preserve faction scale and Wulin identity without carrying every low-level faction config record.

## E. Martial arts projection
Create writer-facing martial records from the promoted skill/sect corpus.

Prioritize:
- 12 sects and their routes;
- named skills/techniques relevant to characters or story;
- route identity;
- weapon/body method where evidenced;
- element/Ngũ Hành relation where evidenced;
- lineage/sect association;
- source-backed mechanical or descriptive properties useful for consistent adaptation;
- source record IDs/locators.

Do not dump every technical skill entry if it has no plausible story use. Preserve links/IDs so deeper Lab lookup remains possible.

Do not convert numerical mechanics directly into prose claims such as exact power ranking unless source evidence supports that interpretation.

## F. Important items and locations
### Important items
Include only items that are materially useful to story/lore/worldbuilding, such as:
- quest-critical objects;
- named weapons/manuals/medicine/tokens/treasures;
- notable sect or martial materials;
- recurring lore objects;
- items that influence a promoted arc.

For each item preserve provenance and story role. Do not include tens of thousands of unrelated inventory entries.

### Important locations
Include locations important to:
- main story;
- sect identity;
- major conflict/reveal;
- travel/causal continuity;
- recurring Wulin memory.

Preserve names/aliases, map IDs where useful, associated factions/events, and source references.

## G. Concordance
Build only concordance useful for future adaptation and source lookup.

### `cn-vi-names.json`
Canonical Chinese ↔ Vietnamese names and known variants for important story entities.

### `entity-aliases.json`
Stable entity IDs with spelling/transliteration/localization aliases to prevent duplicate identities in the novel repo.

### `task-story-map.json`
Map source task/task-family IDs to promoted story arc/beat IDs where supported.
This exists for forensic lookup; task IDs must never become the story structure by themselves.

## H. Unresolved projection
Preserve uncertainty instead of hiding it.

### `central-tolerable.json`
Questions that affect interpretation but do not prevent coherent adaptation. Explain why promotion remains safe.

### `non-central.json`
Optional, side-content or implementation gaps that do not affect the main causal spine.

### `material-conflicts.json`
Must normally be empty at promotion time.
If a MATERIAL conflict was resolved by explicit user canon choice, keep an audit record with:
- conflicting claims;
- sources;
- user decision reference;
- promoted interpretation.

Never silently erase a past material conflict.

## I. Build tooling
Prefer a deterministic script such as:

`scripts/build_novel_handoff.py`

if the handoff can be generated reliably from persisted Lab artifacts.

Requirements:
- use only persisted inputs;
- do not read chat history;
- be idempotent/reproducible where practical;
- generate hashes/manifest automatically;
- reject or exclude prohibited raw/binary paths;
- fail if promotion prerequisites are not satisfied;
- avoid rebuilding expensive unrelated corpora.

If existing project tooling provides a cleaner mechanism, extend it instead of adding unnecessary parallel infrastructure.

Add focused tests/validation only where they materially protect handoff integrity.

## J. Handoff validation
Before declaring success, validate at minimum:

1. `NOVEL_PROMOTION_READY` prerequisite was persisted before generation;
2. all manifest-listed files exist and hashes match;
3. JSON/JSONL artifacts parse;
4. all dossier/index references resolve;
5. all load-bearing story claims retain provenance/evidence references;
6. no `CENTRAL_BLOCKER` remains;
7. no unresolved MATERIAL narrative conflict remains;
8. no raw `client/`, `server/`, `.pak`, executable, archive or bulk proprietary extracted payload appears in the handoff;
9. handoff size/content is curated rather than a wholesale copy of Research Release;
10. no novel prose, adaptation decision or Tiêu Phùng mapping was introduced.

## K. Persist and verify
Use minimum necessary repo operations:

`batch reads → build/update handoff tooling → generate handoff → validate → persist → re-read persisted state → final report`.

Do not create many commits for individual generated files if one bounded atomic commit is sufficient.

After persistence, verify the actual committed/persisted handoff state rather than assuming generation succeeded.

## Final report
Report concisely:

1. handoff status: `NOVEL_HANDOFF_READY` or `NOVEL_HANDOFF_BLOCKED`;
2. source Lab commit used;
3. number of promoted story dossiers/arcs;
4. main handoff artifact paths;
5. remaining `CENTRAL_TOLERABLE` / `NON_CENTRAL` counts;
6. confirmation that `CENTRAL_BLOCKER = 0` and unresolved MATERIAL conflicts = 0;
7. confirmation that raw proprietary payloads were excluded;
8. validation/test result;
9. exact next step for `kiem-the-novel`: curated import into `source-canon/` followed by Source Promotion → Source Coverage → Game Story Reconstruction gates.

Once `NOVEL_HANDOFF_READY` is verified, STOP Lab research by default. Do not continue broad source archaeology merely because more data exists. Reopen Lab only for a concrete unresolved story question, a later source correction, or a failed novel-side source gate.
