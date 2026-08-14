# PAK Structure Report

- Generator: `scripts/jxlab.py`
- Schema version: `1.0`
- Generated (UTC): `2026-08-14T06:42:14.271634+00:00`
- Input scope: `client` = `client`, `server` = `server`, `official_pages` = `official-pages`, `private_input` = `private-input`
- Parser version: `jxlab pak-structure/0.2`
- Archive payload extracted: **False**

- Archives inspected: **67**

## Layout statuses

- `standard_index_layout`: 65
- `variant_or_trailing_layout`: 2

## Observed method nibbles

- `0x00000000`: 5,940
- `0x10000000`: 27,520
- `0x20000000`: 471,450

## Fragment flag

- `false`: 477,390
- `true`: 27,520

## Variant archives

- `client/pak/image21168.pak`: variant_or_trailing_layout; tail 1486 vs expected 1472 bytes
- `client/pak/update2021.pak`: variant_or_trailing_layout; tail 25157 vs expected 24960 bytes

## Evidence boundary

- The 16-byte index, 27-bit stored-size mask, fragment flag, and high-nibble method mask are confirmed by `XPackFile::ReadElemFile` disassembly.
- Method `0x20000000` maps to `ucl_nrv2b_decompress_safe_8` in `XPackFile::ExtractRead`; output is accepted only when the decoded length equals the index expanded size.
- Variant archives are recorded and not force-parsed.
