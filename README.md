# JX Source Lab

Read-only research/forensics workspace for reconstructing **actual Kiếm Thế / JX game data and story evidence** before any novel adaptation.

## Prime directive
**Source first → reconstruction second → adaptation later. Never invent missing game facts.**

This is NOT the novel repository. Use it to inventory server/client files, extract tasks/dialogue/NPCs/sects/skills/items/maps/features/assets, investigate `.pak` archives safely, build a structured corpus, reconstruct game story with provenance, and record UNKNOWN / EDITION DRIFT instead of filling gaps with fiction.

## Local layout
```text
jx-source-lab/
├── client/              # copy game client here
├── server/              # copy server/source here
├── official-pages/      # optional saved Kingsoft/Xoyo/VNG pages
├── private-input/       # optional old notes/dumps; lead-only
├── scripts/ schemas/ database/ docs/ prompts/ queries/
├── generated/ research/ manifests/
└── AGENTS.md
```

Raw source folders are ignored by Git by default.

## Requirements
Python 3.11+ recommended. Initial tooling uses only the Python standard library.

## Research Release 1.1 pipeline
The complete local pipeline remains standard-library only:

```powershell
python .\scripts\jxlab.py inventory --hash
python .\scripts\jxlab.py find-pak-refs --hash
python .\scripts\jxlab.py inspect-pak-structure
python .\scripts\jxlab.py parse-task-catalog
python .\scripts\jxlab.py inspect-task-publish-index
python .\scripts\jxcorpus.py
python .\scripts\build_asset_index.py
python .\scripts\build_database.py
python .\scripts\reconcile_internet_research.py
python .\scripts\build_research.py
python .\scripts\build_release.py
python .\scripts\validate_release.py --verify-source-hashes
python -m unittest discover -s tests -v
```

`generated/release/` contains the 16 release deliverables. Local decoded PAK
samples are written only below ignored `generated/extracted/`; the release
contains metadata, hashes, and derived text records rather than proprietary
binary payloads. Fragment entries and unsupported archive variants remain
explicitly `UNKNOWN` instead of being guessed.

Release 1.1 also reconciles the 33-file independent research package into 25
provenance-bearing claims and 14 source-only game-story dossiers. The generated
concordance records S3/S4/S5 gates and the explicit novel-promotion decision;
it does not contain novel prose or silently promote unresolved claims.

The dedicated `research/reconstruction/level-50-89-mainline.json` artifact
records the validated 12-family/77-inline-subtask post-50 order. It explicitly
blocks all 77 unrelated same-ID standalone joins and keeps the bounded Internet
search ledger separate from raw wrapper evidence.

## First run
```powershell
python .\scripts\jxlab.py inventory
python .\scripts\jxlab.py find-pak-refs
python .\scripts\jxlab.py text-candidates
```
Or `./run-lab.ps1 inventory`.

Open the whole folder in Codex and paste `prompts/00-first-codex-session.md`.

## Research phases
1. Inventory & provenance
2. Schema discovery
3. PAK format archaeology
4. Deterministic extraction/parsers
5. SQLite corpus
6. Game-story reconstruction
7. Source-confidence audit
8. Research Release 1.1
9. Only then seed a separate novel repository

## Research Release 1.1 target
`generated/release/` contains the source manifest, edition matrix, main/side task graph, dialogue/NPC/sect/skill/item/location/feature corpora, client asset index, game-story reconstruction, internet-research concordance, source-only dossiers, unresolved questions, edition-drift ledger and confidence report.

Do not publicly redistribute proprietary/raw game files unless you have determined you may do so. Keeping them local and ignored is the default.
