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
8. Research Release 1.0
9. Only then seed a separate novel repository

## Research Release 1.0 target
`generated/release/` should eventually contain source manifest, edition matrix, main/side task graph, dialogue/NPC/sect/skill/item/location/feature corpora, client asset index, game-story reconstruction, unresolved questions, edition-drift ledger and confidence report.

Do not publicly redistribute proprietary/raw game files unless you have determined you may do so. Keeping them local and ignored is the default.
