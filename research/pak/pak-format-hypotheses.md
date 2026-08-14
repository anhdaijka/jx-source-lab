# PACK Format Findings and Remaining Hypotheses

## Scope

This ledger records byte-level observations for the archives currently present in `client/` and `server/`. It does not assume all archives share one layout.

## Verified direct observations

- `server/gameserver/pak/task_publish.pak` and `client/pak/task_publish.pak` are byte-identical according to SHA-256 `ac48ad39a653007f9244a0f0abf0ab5944c638533114eea4fb7830b29c8bce3f`.
- At byte offset `0x00`, `task_publish.pak` begins with ASCII `PACK`.
- Little-endian values at offsets `0x04`, `0x08`, and `0x0C` are respectively `1074`, `0x2254E3`, and `32`.
- File size minus `0x2254E3` is exactly `1074 * 16`, establishing a 16-byte trailing index for this archive.
- All 1,074 task archive index records describe ranges contained between byte `32` and the index offset. Sorted stored ranges are contiguous and cover that entire payload area.
- The accompanying `.pak.txt` listing contains 1,129 unique IDs, while the binary index contains 1,074 unique IDs. Their ID sets differ, and only three binary index records match any listing row on both size fields. The listing is therefore not an exact manifest for the present archive bytes (`EDITION_DRIFT`).
- Across the current inventory, 65 of 67 archives match the observed 32-byte-header plus trailing `count * 16` layout. `client/pak/image21168.pak` and `client/pak/update2021.pak` do not and must be treated as variants.
- `server/gameserver/engined.pdb` contains `XPackFile.cpp`, `XPackIndexInfo`, `XPACK_METHOD_NONE`, `XPACK_METHOD_UCL`, and UCL NRV2B/NRV2D/NRV2E decompressor symbols. `server/gameserver/engine.dll` contains `CreatePackFileShell` and the UCL library identification string.
- The matching debug pair is `server/gameserver/engined.dll` (SHA-256 `c6aaa6be3020c232c73842e810bf3a9d37180ddcb91a7670147a425845c4f20e`) and `server/gameserver/engined.pdb` (SHA-256 `cd96a1e262bb789d5064d2bb063a8f11eed0c20a63de9bd878ac5e0fc6c0942c`).
- `XPackFile::ReadElemFile` disassembly confirms stored size as `packed & 0x07FFFFFF`, fragment flag as `packed & 0x10000000`, and method as `packed & 0xF0000000`.
- `XPackFile::ExtractRead` compares method with `0x20000000` and calls `_ucl_nrv2b_decompress_safe_8`. Output is accepted only when decoded length equals the expanded-size field.
- A copied `client/pak/aspaksc.pak` sample (SHA-256 `0fdfbd63d31dc06679aff12806ed9a0369fab4eb7714b7f52ee926ad3b7b0be1`) was decoded without executing a game binary. Entry `80e93cfb` produced 49,528 bytes with SHA-256 `599d514db95b8ca62f2364324b27f08a695fbb5a2859803077fdeecfa923099f`; entry `ee1a9540` produced 4,232 bytes with SHA-256 `602d764a198e6670104e4db135ed7b37a96e13bfa5d0d882043b51056d53da99`. Both begin with valid Lua-text signatures.

## Confirmed standard-layout semantics

- Header field at `0x04` is the number of 16-byte index records.
- Header field at `0x08` is the trailing index offset.
- Header field at `0x0C` is the payload/header start offset.
- Each standard index record is four little-endian 32-bit values: element ID, payload offset, expanded size, and a packed method/size field.
- The low 27 bits of the fourth value are stored payload size.
- Bit `0x10000000` is the fragment flag; the high nibble is the method field used by the engine.
- Method `0x00000000` is stored/uncompressed. Method `0x20000000` is UCL NRV2B `safe_8`.

## Unresolved

- Fragment payload framing for entries with flag `0x10000000`.
- Semantics of header bytes `0x10..0x1F`.
- Structure of the two variant archives and the meaning of non-contiguous payload regions in update/map packages.
- CRC algorithm and whether companion-listing CRC values describe the current archive generation.
- Whether entry IDs are computed path hashes; no hash algorithm is assigned yet.

## Safety and licensing boundary

The extractor is read-only and output-bounded. It refuses fragment and variant layouts, does not overwrite extracted payloads, and writes local payloads only below ignored `generated/extracted/`. The Python compatibility implementation was authored for this lab from observed engine behavior and published algorithm semantics; upstream UCL source itself is GPL and is not vendored here. Public distribution of proprietary payloads remains out of scope.
