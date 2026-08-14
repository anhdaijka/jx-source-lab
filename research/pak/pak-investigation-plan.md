# PAK Investigation Plan

- Status: completed for Research Release 1.0 text/config-first scope.
- Generator: manual S0 evidence review
- Schema version: `1.0`
- Input scope: `client/`, `server/`
- Archive inventory: `generated/reports/pak-reference-report.json`
- Loader/reference inventory: `generated/reports/pak-reference-report.md`

## Established evidence

- 67 files with configured archive extensions were found: 56 in `client/` and 11 in `server/`.
- Archive paths, sizes, first 32 bytes, and SHA-256 values are recorded in the PAK reference JSON report.
- Every sampled archive record in that report begins with header bytes `50 41 43 4B` (`PACK`). This is a byte-level observation only; it does not establish the complete format, index layout, compression, or encryption.
- `client/package.ini`, `client/tppackage.ini`, `server/gameserver/package.ini`, and `server/Gamecenter/package.ini` declare package loading lists.
- Text listings such as `server/gameserver/pak/script.pak.txt` and `server/Gamecenter/pak/setting.pak.txt` are candidate package-index evidence. Their relationship to the binary archive must be verified record by record.
- The matched `engined.dll`/`engined.pdb` pair provides verified loader implementation evidence through named disassembly; no game binary was executed.
- `XPackFile::ReadElemFile` confirms the 27-bit stored-size mask and fragment flag. `XPackFile::ExtractRead` maps method `0x20000000` to `ucl_nrv2b_decompress_safe_8` and requires exact output length.
- Structural inspection found 65 archives matching the 32-byte-header plus trailing `count * 16` index layout and two variant/trailing layouts that must not be force-parsed.
- `task_publish.pak.txt` is not an exact manifest for the present `task_publish.pak` bytes; its ID set and size fields materially differ (`EDITION_DRIFT`).

## Unknowns

- Exact producer names/semantics for header bytes beyond the structurally validated count, index-offset, and header-size candidates.
- Entry naming/hash and path normalization rules.
- Fragment payload framing for flag `0x10000000`.
- Structure of the two variant/trailing-layout archives and non-contiguous payload regions.
- Whether companion `.pak.txt` listings other than the disproven task listing describe the exact archive generation present here.

## Completed execution

1. Archive inventory and hashes recorded for all 67 configured archives.
2. Loader semantics recovered from the matched PDB/DLL pair without executing it.
3. Bounded standard-layout inspector and UCL NRV2B `safe_8` decoder implemented.
4. Copied sample validation passed exact size, full input consumption, output hash, and Lua signature checks.
5. Exact companion listings are path sources; drifted listings remain lead-only.
6. Text/config archives were decoded first. Client image/audio/update entries are structurally indexed and deliberately deferred.
7. Fragment and variant layouts remain explicit `UNKNOWN`, never force-parsed.

## Stop conditions

- Ask for a decision if an archive key/password is required but absent from available evidence.
- Record `EDITION_DRIFT` instead of choosing a format when incompatible package/index evidence is found.
- Do not execute `Game.exe` or any unknown binary during this investigation.
