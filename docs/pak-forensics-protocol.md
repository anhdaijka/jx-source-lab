# PAK / Client Archive Forensics Protocol

## A — Inventory
Record path, size, SHA-256, extension, header bytes, timestamp. Do not unpack yet.

## B — Source-code archaeology
Search for `.pak`, `PakFile`, `PackFile`, `LoadPack`, package/archive APIs, file-index tables, compression libraries, crypto/key references and virtual filesystem code. Prefer actual loader code over format guessing.

## C — Extractor requirements
Read-only input; output to `extracted/`; safe path traversal handling; no overwrite unless enabled; archive+entry provenance; preserve bytes; hash output.

## D — Extraction order
text/config/localization/script → catalogs/indexes → UI data → item/skill/NPC/map metadata → images → audio/video only if needed.

## E — Asset catalog
Index source archive, internal path, hash, file type/dimensions and candidate NPC/item/skill/map relation. Do not publicly redistribute originals by default.
