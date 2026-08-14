# Codex task — reconcile internet research with JX Source Lab

Use this after the independent internet-research package has been copied somewhere under `private-input/` (recommended: `private-input/internet-research/`).

## User-confirmed policy
- The local client/server may be community-modified or feature-extended. Story content is believed to be unchanged.
- Exact client/server version identity is not important unless a concrete story contradiction depends on it.
- Canon target is the **latest coherent Kiếm Thế lore** supported by both the Lab corpus and the independent research corpus.
- Do not optimize for launch-era purity or spend time on non-narrative version archaeology.

## Start
1. Read `AGENTS.md`, `docs/source-authority.md`, `docs/reconstruction-protocol.md`, `docs/promotion-gates.md` and the existing Research Release 1.0 state.
2. Run `git status`, then update from `origin/main` with a safe fast-forward pull if needed. Never overwrite local raw source roots.
3. Locate the independent research package under `private-input/`. If multiple candidates exist, use the package containing evidence/source ledgers, chronology and arc research rather than asking the user unless ambiguity affects correctness.

## Objective
Turn the internet-research package into corroborating narrative evidence and reconcile it with the existing raw client/server corpus. The outcome should answer:

> Do we now have enough evidence-backed game story to promote a source corpus for the novel, and exactly which central story gaps still matter?

This is still source reconstruction, not novel writing.

## Work
### A. Audit the research package
- Inventory its files and identify its evidence ledger, source-critical notes, chronology, arc files and unresolved/HOLD records.
- Treat package summaries as research claims, not automatic facts.
- Preserve every supplied URL/citation/locator.
- For load-bearing claims, verify first-party Kingsoft/Xoyo/VNG/archive references when practical.
- Classify verified evidence using the existing evidence classes. Community/fan pages remain leads unless independently corroborated.

### B. Normalize only useful claims
Create a compact machine-readable claim set for claims that affect:
- main-story chronology and causal spine;
- character identity, motive, allegiance, relationship or reveal;
- faction goals and political stakes;
- major conflict/climax/outcome/consequence;
- named martial arts, sect routes, important items or important locations;
- player origin / major mystery / later payoff.

Do not spend time normalizing trivia that will not affect story reconstruction.

### C. Reconcile with Lab evidence
For each load-bearing research claim, search existing task/dialogue/NPC/sect/skill/item/location/reference-edge corpora for support, contradiction or absence.

Use statuses such as:
- `CROSS_SOURCE_CONFIRMED`
- `RAW_SUPPORTED`
- `OFFICIAL_SUPPORTED`
- `STRONG`
- `INFERENCE`
- `UNKNOWN`
- `CONFLICT`
- `EDITION_DRIFT`

For drift/conflict, add narrative impact:
- `NONE`
- `POSSIBLE`
- `MATERIAL`

Do not investigate exact build provenance for `NONE` drift.

### D. Target the real weak zones
Prioritize targeted reconstruction of gaps already identified by research, especially if still unresolved after reconciliation:
- pre-50 / Binh Qua Trung Nguyên causal chain;
- level 50–80 story chain;
- level 100 `瞒天过海`;
- player-origin / parents / Du Long Giác and other load-bearing mystery payoffs.

Use the existing Lab corpus to trace likely task families by task name, Chinese/Vietnamese concordance, NPC, dialogue, item, map and dependency edges.

Do NOT attempt to reduce every existing UNKNOWN to zero. Classify unresolved questions by centrality:
- `CENTRAL_BLOCKER`
- `CENTRAL_TOLERABLE`
- `NON_CENTRAL`

Only `CENTRAL_BLOCKER` prevents promotion.

### E. Produce game-story dossiers
Produce/update source-only GAME STORY DOSSIERS for the main story arcs. Each dossier should contain:
- arc identity / level or chronology range;
- premise;
- involved characters and factions;
- evidenced goals/motives;
- ordered causal events;
- what the player learns and when;
- major conflict/reveal/climax/resolution;
- political/Wulin consequences;
- important named martial arts/items/locations when evidenced;
- claim → evidence references;
- remaining central UNKNOWNs;
- any MATERIAL contradiction/drift.

Do not adapt the player into Tiêu Phùng and do not outline novel chapters here.

## Minimal persistence
Prefer reusing existing structures. Add only the minimum necessary new research artifacts. A reasonable shape is:

- `research/reconciliation/internet-research-claims.jsonl`
- `research/reconciliation/lore-concordance.json`
- `research/reconstruction/game-story-dossiers/`
- updated `research/unresolved-questions.json`
- updated confidence/release artifacts as required by existing generators

If existing schemas/generators can represent this cleanly, extend them rather than creating parallel duplicate systems.

## Validation and promotion decision
Regenerate/validate the affected Research Release artifacts. Do not rebuild expensive unrelated corpora unless dependencies require it.

At the end, report:
1. what internet research materially added;
2. which major claims are now cross-source confirmed;
3. which CENTRAL_BLOCKER questions remain;
4. any MATERIAL narrative conflicts;
5. whether S3, S4 and S5 pass under the current policy;
6. one explicit result: `NOVEL_PROMOTION_READY` or `NOVEL_PROMOTION_NOT_READY`.

`NOVEL_PROMOTION_READY` does NOT mean write prose in this Lab. It means a curated source-canon package may now be prepared for `kiem-the-novel`.

Do not ask the user about exact build/version identity. Ask only if credible sources create a MATERIAL narrative conflict that cannot be resolved without a canon choice, or if a destructive/ownership decision is required.
