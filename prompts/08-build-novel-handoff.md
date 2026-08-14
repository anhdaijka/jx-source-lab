# Codex task — build curated source-story novel handoff

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

Do not treat remaining `CENTRAL_TOLERABLE`, `NON_CENTRAL`, implementation-only `EDITION_DRIFT`, custom-feature differences, bounded-not-found research gaps, or unknown exact client/server version as blockers.

## Goal
Produce one compact, writer-facing, provenance-aware **SOURCE-SIDE GAME STORY BIBLE** for one-time import into `anhdaijka/kiem-the-novel/source-canon/`.

The handoff must answer, as completely as the evidence safely allows:

> What actually happens in the latest coherent Kiếm Thế lore; who does what and why; which plot threads persist across arcs; what each important character/faction knows and does over time; where mysteries are set up and paid off; and which martial arts/items/locations matter — without forcing the novel repo to reopen raw source archaeology during normal writing work?

This is still SOURCE CANON, NOT novel canon.

This task is:
- NOT a novel outline;
- NOT episode/chapter planning;
- NOT protagonist adaptation;
- NOT Tiêu Phùng design;
- NOT prose;
- NOT permission to invent missing game material.

## Core boundary: reconstruct deeply, do not adapt
The Lab SHOULD do deep source-side synthesis when evidence supports it, including:
- causal story structure;
- long-running plot threads;
- source-backed character trajectories;
- faction trajectories;
- source relationships and their changes;
- source knowledge/reveal timing;
- mystery setup/reinforcement/reveal/payoff structure;
- named martial, item and location relevance;
- political/Wulin consequences.

The Lab MUST NOT decide:
- who the novel protagonist is;
- whether the game player becomes Tiêu Phùng;
- novel-only personality arcs;
- novel-only romance;
- novel POV structure;
- episode/chapter boundaries;
- which game events are compressed/reordered/expanded for fiction;
- invented connective scenes;
- novel martial progression/training design;
- novel-specific foreshadowing or secrets.

Those belong to `kiem-the-novel` after import and NovelOS adoption.

## Design principles
1. **Source-story bible, not raw export.** Make the game story understandable without carrying the whole Lab.
2. **Curated, not exhaustive.** Do not copy the entire Research Release.
3. **Story usefulness first.** Prefer load-bearing lore and reusable world/Wulin context over low-value implementation detail.
4. **Traceable.** Every load-bearing claim must remain traceable back to Lab evidence or a reconciled official/research claim.
5. **Preserve uncertainty.** Tolerated gaps remain explicitly labeled; do not smooth them into certainty.
6. **No raw proprietary payloads.** Never include raw `client/`, `server/`, `.pak`, binaries, bulk extracted assets, private-input packages or full proprietary source files.
7. **No version archaeology requirement.** Exact client/server build identity is metadata only unless a MATERIAL narrative issue depends on it.
8. **No fiction.** Do not repair a source gap with novel invention.
9. **No novel assumptions.** Do not map the game player to Tiêu Phùng or any future novel protagonist here.
10. **One-way handoff.** The novel repo must not depend on this Lab repo at runtime and must not require automatic sync.
11. **Do not reconstruct twice.** If a source-side thread/trajectory/knowledge transition can be safely derived now from persisted evidence, encode it now so the novel repo does not have to rediscover it later.

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
│   ├── plot-thread-index.json
│   ├── mystery-payoff-map.json
│   └── dossiers/
│       └── <one source-only dossier per promoted main-story arc>
│
├── characters/
│   ├── character-index.json
│   └── trajectories/
│       └── <one source trajectory per important recurring character>
│
├── factions/
│   ├── faction-index.json
│   └── trajectories/
│       └── <one source trajectory per important faction/organization when useful>
│
├── relationships/
│   └── source-relationship-map.json
│
├── knowledge/
│   └── source-knowledge-timeline.json
│
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
- count of promoted important characters and character trajectories;
- count of promoted plot threads;
- count of promoted mysteries/payoffs;
- count of unresolved `CENTRAL_BLOCKER` (must be 0);
- count of unresolved MATERIAL narrative conflicts (must be 0 unless already resolved by persisted user decision);
- counts of `CENTRAL_TOLERABLE` and `NON_CENTRAL` unresolved questions;
- file list with SHA-256 hashes for every handoff artifact;
- explicit statement that raw proprietary source/client/server/PAK/private-input payloads are excluded.

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
- clear note that exact client/server build/version identity is not a promotion requirement under current policy;
- a lookup convention explaining how handoff claim/entity/thread IDs can be traced back into Lab research/corpus artifacts.

Do not embed raw evidence payloads just to make provenance self-contained.

## C. Game-story projection
The handoff's `game-story/` is the highest-priority part.

### `master-chronology.md`
Produce a concise source-only chronological reconstruction covering the promoted main story from beginning through the latest coherent supported lore.

For each major phase/arc, preserve:
- chronology/level range when known;
- whether the phase branches or converges;
- major characters/factions involved;
- initiating problem;
- causal progression;
- important reveal/climax;
- outcome and downstream consequence;
- references to the full source dossier;
- plot-thread IDs that enter, advance, converge, resolve or remain open here.

Do not turn it into chapter planning or literary narration.

### `causal-spine.json`
Represent the load-bearing causal chain in a machine-readable form.
Each node/edge should make clear:
- event/claim ID;
- predecessor/cause;
- resulting event/consequence;
- involved entities;
- evidence/confidence status;
- arc/dossier/evidence reference;
- related plot-thread IDs;
- whether the edge is direct evidence, cross-source reconstruction or strong bounded inference.

Only include causal edges supported strongly enough for promotion. Unknown optional transitions may remain absent or explicitly marked.

### `arc-index.json`
List promoted story arcs with:
- stable arc ID;
- names/aliases;
- chronology or level range;
- branch/convergence role when applicable;
- dossier path;
- principal characters/factions;
- status/confidence;
- central unresolved count;
- active plot-thread IDs;
- mystery/reveal IDs;
- important martial/item/location references.

### `plot-thread-index.json`
This is a SOURCE-SIDE thread map, not a novel plot plan.

Create stable thread IDs for load-bearing game-story threads that persist across more than one beat/arc or carry important strategic meaning.

Each thread should include where supported:
- thread ID and canonical label;
- type, e.g. political, Wulin, factional, personal, identity, war, mystery, artifact, sect conflict;
- first source-backed setup;
- major developments in source order;
- participating characters/factions;
- intersections with other threads;
- reversals/reframes;
- source-backed payoff/resolution if any;
- downstream residue if the thread remains relevant after local payoff;
- status: `OPEN_IN_SOURCE`, `LOCALLY_RESOLVED`, `RESOLVED`, `TOLERATED_UNKNOWN` as appropriate;
- evidence/confidence references.

Do not create a thread merely because it would make a better novel. It must exist in source/reconstruction evidence.

### `mystery-payoff-map.json`
Create stable mystery/reveal IDs for source-backed questions whose timing matters.

For each important mystery, preserve where evidenced:
- mystery/question;
- initial setup event;
- reinforcement/clues;
- what the player knows or is told at each relevant stage;
- what important NPCs/factions know, suspect or conceal when evidence supports it;
- false belief/misinformation if source-backed;
- reveal trigger;
- reveal content;
- local payoff;
- downstream consequence/residue;
- final status;
- arc/thread references;
- evidence/confidence references.

This map must distinguish:
- `SETUP`;
- `CLUE`;
- `SUSPICION`;
- `REVEAL`;
- `PAYOFF`;
- `RESIDUE`.

Do not manufacture clue chains from task ordering alone.

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
- active/resolved plot-thread IDs;
- mystery/payoff IDs;
- claim/evidence references;
- remaining tolerated unknowns;
- material contradiction status.

Do not embellish for readability beyond faithful source summarization.

## D. Character projection and source trajectories
Create compact writer-facing records only for characters that matter to promoted story, recurring Wulin/world continuity, major mysteries, faction trajectories or important martial context.

### `character-index.json`
Each important character should include:
- stable entity ID;
- canonical name + CN/VI aliases;
- source-backed role;
- affiliations;
- first/major/latest relevant appearances;
- trajectory file path if recurring;
- related plot-thread IDs;
- related mystery/reveal IDs;
- known martial association if evidenced;
- source references/confidence.

### `characters/trajectories/<character>.json|md`
This is a SOURCE TRAJECTORY, not a novel character arc.

For each important recurring character, preserve where evidenced:
- initial source state/role;
- affiliation and allegiance changes;
- major decisions/actions;
- source-backed goals/motives and changes in them;
- major relationship changes;
- major knowledge/reveal changes;
- important martial/item/location associations;
- appearances by arc in chronological order;
- consequences suffered/caused;
- latest source-backed state;
- unresolved identity/motive/status questions;
- claim/evidence references for load-bearing transitions.

Do not invent inner emotional growth, trauma, romance, redemption, thematic lesson or personality traits unless source evidence actually states/supports them.

## E. Faction/organization projection and trajectories
### `faction-index.json`
Include important factions, organizations, powers and great sects relevant to promoted story.

For each preserve:
- stable ID and aliases;
- institutional role;
- goals/interests when evidenced;
- allies/enemies/rivals when evidenced;
- major representatives/masters;
- story-relevant locations;
- related arcs/threads;
- source references/confidence.

### `factions/trajectories/<faction>.json|md`
Where useful, encode source-side faction change over time:
- starting position;
- strategic objective;
- major interventions;
- alliances/conflicts;
- political/Wulin changes;
- losses/gains;
- leadership or allegiance changes;
- involvement in major reveals/conflicts;
- resulting state after each major arc;
- latest source-backed state;
- evidence references.

This exists to preserve faction scale and agency. Do not reduce great sects/factions to task-giver lists.

## F. Source relationship map
Create `relationships/source-relationship-map.json` for load-bearing, recurring or plot-relevant relationships only.

Relationships are directional when evidence warrants it.

For each relationship edge/event preserve where supported:
- source entity → target entity;
- relationship type, e.g. kinship, master-disciple, sect affiliation, alliance, rivalry, enmity, command, trust, suspicion, protection, debt, pursuit, political cooperation;
- initial evidenced state;
- important changes over time;
- change-trigger event/arc;
- final/latest source-backed state;
- evidence/confidence references.

Do not infer romance, affection, betrayal, hatred or intimacy merely from co-occurrence or task adjacency.

If two directions materially differ, store both directions separately.

## G. Source knowledge timeline
Create `knowledge/source-knowledge-timeline.json` only for knowledge states that matter to major causality, mystery, allegiance, betrayal, reveal or payoff.

Use explicit statuses where helpful:
- `KNOWS`
- `BELIEVES`
- `SUSPECTS`
- `HEARD_RUMOR`
- `MISINFORMED`
- `UNKNOWN`

For important reveal/knowledge events preserve:
- event/reveal ID;
- entity whose knowledge changes;
- prior state when evidenced;
- new state;
- information/claim learned or believed;
- source event causing the change;
- arc/thread/mystery references;
- evidence/confidence.

Do not attempt to model every NPC. Include only source-backed states whose timing could matter to coherent adaptation.

Do not infer that a character knows something merely because the player knows it.

## H. Sect and martial-arts projection
Create writer-facing martial records from the promoted skill/sect corpus.

Prioritize:
- all 12 sects and their routes;
- named skills/techniques relevant to characters or story;
- route identity;
- weapon/body method where evidenced;
- element/Ngũ Hành relation where evidenced;
- lineage/sect association;
- notable master/character association;
- source-backed mechanical or descriptive properties useful for consistent adaptation;
- story relevance when the skill/route actually appears or matters;
- source record IDs/locators.

Do not dump every technical skill entry if it has no plausible story use. Preserve links/IDs so deeper Lab lookup remains possible.

Do not convert numerical mechanics directly into prose claims such as exact power ranking unless source evidence supports that interpretation.

If source supports a martial hierarchy, reputation comparison, transmission relationship or recognizable counterplay, preserve it explicitly.

## I. Important items and locations
### Important items
Include only items materially useful to story/lore/worldbuilding, such as:
- quest-critical objects;
- named weapons/manuals/medicine/tokens/treasures;
- notable sect or martial materials;
- recurring lore objects;
- items that influence a promoted arc, relationship, mystery or faction objective.

For each item preserve provenance, associated entities/arcs/threads and source-backed story role.
Do not include tens of thousands of unrelated inventory entries.

### Important locations
Include locations important to:
- main story;
- sect identity;
- major conflict/reveal;
- travel/causal continuity;
- recurring Wulin memory;
- faction control or political consequence where source-backed.

Preserve names/aliases, map IDs where useful, associated factions/events/threads, and source references.

## J. Concordance
Build only concordance useful for future adaptation and source lookup.

### `cn-vi-names.json`
Canonical Chinese ↔ Vietnamese names and known variants for important story entities.

### `entity-aliases.json`
Stable entity IDs with spelling/transliteration/localization aliases to prevent duplicate identities in the novel repo.

### `task-story-map.json`
Map source task/task-family IDs to promoted story arc/beat/thread IDs where supported.

The map should preserve known ID reuse/variant hazards such as `ID_REUSE_VARIANT` instead of collapsing records with the same apparent ID.

This exists for forensic lookup; task IDs must never become the story structure by themselves.

## K. Unresolved projection
Preserve uncertainty instead of hiding it.

### `central-tolerable.json`
Questions that affect interpretation but do not prevent coherent adaptation. Explain:
- what is unknown;
- why it matters;
- why promotion remains safe;
- which arcs/threads/entities it may affect;
- what must NOT be asserted as fact.

### `non-central.json`
Optional, side-content, micro-task, implementation or bounded-not-found gaps that do not affect the main causal spine.

Do not spend extra research merely to reduce this count before handoff.

### `material-conflicts.json`
Must normally be empty at promotion time.
If a MATERIAL conflict was resolved by explicit user canon choice, keep an audit record with:
- conflicting claims;
- sources;
- user decision reference;
- promoted interpretation.

Never silently erase a past material conflict.

## L. Cross-file integrity requirements
The handoff is a connected story model, not independent summaries.

Where IDs exist, cross-link consistently:
- arc IDs;
- event/claim IDs;
- plot-thread IDs;
- mystery/reveal IDs;
- character IDs;
- faction/sect IDs;
- item/location/martial IDs.

At minimum verify:
- chronology references valid dossiers/arcs;
- causal spine references valid events/arcs;
- plot threads reference valid arcs/entities;
- mystery/payoff map references valid events/entities;
- character/faction trajectories reference valid arcs/threads;
- relationship and knowledge maps reference valid entity IDs;
- concordance aliases do not create duplicate canonical entities.

Prefer stable source-side IDs that can survive later import into `source-canon/`.

## M. Build tooling
Prefer a deterministic script such as:

`scripts/build_novel_handoff.py`

if the handoff can be generated reliably from persisted Lab artifacts.

Requirements:
- use only persisted inputs;
- do not read chat history;
- be idempotent/reproducible where practical;
- generate hashes/manifest automatically;
- reject or exclude prohibited raw/binary/private-input paths;
- fail if promotion prerequisites are not satisfied;
- avoid rebuilding expensive unrelated corpora;
- reuse existing reconciliation/dossier artifacts rather than re-researching the game;
- support focused regeneration when only a handoff projection changes.

If existing project tooling provides a cleaner mechanism, extend it instead of adding unnecessary parallel infrastructure.

Add focused tests/validation only where they materially protect handoff integrity.

## N. Handoff validation
Before declaring success, validate at minimum:

1. `NOVEL_PROMOTION_READY` prerequisite was persisted before generation;
2. S3/S4/S5 persisted states satisfy promotion policy;
3. all manifest-listed files exist and hashes match;
4. JSON/JSONL artifacts parse;
5. all dossier/index/thread/trajectory/relationship/knowledge references resolve;
6. all load-bearing story claims retain provenance/evidence references;
7. no `CENTRAL_BLOCKER` remains;
8. no unresolved MATERIAL narrative conflict remains;
9. mystery/payoff entries do not promote unsupported guesses into reveals;
10. relationship and knowledge maps contain no unsupported inference presented as fact;
11. task ID reuse/variant hazards are preserved rather than silently merged;
12. no raw `client/`, `server/`, `.pak`, executable, archive, private-input package or bulk proprietary extracted payload appears in the handoff;
13. handoff size/content is curated rather than a wholesale copy of Research Release;
14. no novel prose, adaptation decision, episode plan or Tiêu Phùng mapping was introduced;
15. no broad research was restarted merely to fill `NON_CENTRAL` or tolerated gaps.

## O. Persist and verify
Use minimum necessary repo operations:

`batch reads → build/update handoff tooling → generate story-bible handoff → validate → persist → re-read persisted state → final report`.

Do not create many commits for individual generated files if one bounded atomic commit is sufficient.

After persistence, verify the actual committed/persisted handoff state rather than assuming generation succeeded.

## Final report
Report concisely:

1. handoff status: `NOVEL_HANDOFF_READY` or `NOVEL_HANDOFF_BLOCKED`;
2. source Lab commit used;
3. number of promoted story dossiers/arcs;
4. number of plot threads and mystery/payoff records;
5. number of important character/faction trajectories;
6. main handoff artifact paths;
7. remaining `CENTRAL_TOLERABLE` / `NON_CENTRAL` counts;
8. confirmation that `CENTRAL_BLOCKER = 0` and unresolved MATERIAL conflicts = 0;
9. confirmation that raw proprietary/private-input payloads were excluded;
10. validation/test result;
11. exact next step for `kiem-the-novel`: curated import into `source-canon/` followed by Source Promotion → Source Coverage → Game Story Reconstruction gates, then the NovelOS user-decision gate before any adaptation/series architecture.

Once `NOVEL_HANDOFF_READY` is verified, STOP Lab research by default. Do not continue broad source archaeology merely because more data exists. Reopen Lab only for a concrete unresolved story question, a later source correction, or a failed novel-side source gate.
