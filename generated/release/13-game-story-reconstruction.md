# Game Story Reconstruction — Evidence Graph

This artifact is a structured reconstruction of implementation evidence, not a novel narrative and not authorization to adapt it as fiction.

- Task roots: **439**
- Subtask roots: **631**
- Explicit graph edges: **861**
- Config-classified main tasks: **424**
- Configured non-main tasks: **15**

## Promotable relations

- `manages_sub`: explicit `<Managed><Sub refer=...>` relation in a Task XML record.
- `accepts_next_sub`: explicit `TaskAct:AskAccept` with a `referid` parameter.
- `requires_finished_sub`: explicit `TaskCond:IsRefFinished` with a `referid` parameter.

## Evidence limits

- XML task names and text are raw-build content, not automatically launch-era producer canon.
- A missing edge means `UNKNOWN`; adjacency, numeric IDs, and task titles are never used to invent links.
- One logical task ID occurs in two archive entries; both records are preserved independently.
- Internet-package summaries remain `LEGACY_LEAD`; verified underlying Kingsoft/Xoyo/VNG pages are tracked separately in `research/reconciliation/lore-concordance.json`.

- Source-only causal dossiers are generated under `research/reconstruction/game-story-dossiers/`; no player-to-novel-character adaptation is performed.

## Longest explicit chains (identifiers only)

- `task:000000000000000D:entry:f66eae4a`: 77 subtask nodes; termination `no_explicit_next`
- `task:000000000000000E:entry:f350f967`: 72 subtask nodes; termination `no_explicit_next`
- `task:000000000000000E:entry:f350f967`: 71 subtask nodes; termination `no_explicit_next`
- `task:000000000000000E:entry:f350f967`: 70 subtask nodes; termination `no_explicit_next`
- `task:000000000000000E:entry:f350f967`: 69 subtask nodes; termination `no_explicit_next`
- `task:000000000000000E:entry:f350f967`: 68 subtask nodes; termination `no_explicit_next`
- `task:000000000000000F:entry:cc5a3074`: 67 subtask nodes; termination `no_explicit_next`
- `task:000000000000000F:entry:cc5a3074`: 66 subtask nodes; termination `no_explicit_next`
- `task:000000000000000F:entry:cc5a3074`: 65 subtask nodes; termination `no_explicit_next`
- `task:000000000000000F:entry:cc5a3074`: 64 subtask nodes; termination `no_explicit_next`
- `task:000000000000000F:entry:cc5a3074`: 63 subtask nodes; termination `no_explicit_next`
- `task:0000000000000011:entry:be6247a5`: 62 subtask nodes; termination `no_explicit_next`
- `task:0000000000000011:entry:be6247a5`: 61 subtask nodes; termination `no_explicit_next`
- `task:0000000000000011:entry:be6247a5`: 60 subtask nodes; termination `no_explicit_next`
- `task:0000000000000011:entry:be6247a5`: 59 subtask nodes; termination `no_explicit_next`
- `task:0000000000000011:entry:be6247a5`: 58 subtask nodes; termination `no_explicit_next`
- `task:0000000000000011:entry:be6247a5`: 57 subtask nodes; termination `no_explicit_next`
- `task:0000000000000010:entry:bd780c88`: 56 subtask nodes; termination `no_explicit_next`
- `task:0000000000000010:entry:bd780c88`: 55 subtask nodes; termination `no_explicit_next`
- `task:0000000000000010:entry:bd780c88`: 54 subtask nodes; termination `no_explicit_next`
