# Build and repack (phase 3)

`build.py` copies the dump and swaps files in with `tools/iso9660.py` patch (a file that outgrows its sectors moves
to the end of the image, directory record repointed). Every archive goes through its `pack(orig, {entry: bytes})`:

| File | Packer | Layout rule (verified: `pack(d, {}) == d`, tests/test_identity.py) |
|---|---|---|
| SCEN.DAT, MAP.DAT, MAGD.BIN | `dat.pack` | (u16 sector, u16 count) records; entries back to back from the first used sector, padded to 2048. Header area kept. MAP.DAT records 1332+ are (0, 0) out of sequence: kept as is. u16 sector field caps a file at 128 MB (SCEN 62 MB). |
| DATA.DAT, DATA_BOOT.DAT | `datadat.pack` | 0x20-byte records, BE offsets; payloads back to back with **no alignment** (original has odd offsets). Directory block (0xCD filler, stray bytes after the terminator) kept. |
| GLB.DAT | `glb.pack` | 14-byte records, BE offset at +10; payloads back to back, no alignment, file end unaligned. Directory block kept. |

- **Identity (verified):** `build.py --identity` repacks all six with no edits -> SHA-1 = rom.sha1 (5 s). Test:
  `tests/test_identity.py` (also a grown-entry check per archive).
- **Relocation in game (verified 2026-11-22):** a test image with every dat entry padded by 2 sectors and the first
  DATA/DATA_BOOT/GLB entry grown by 4098 bytes (all six files moved to the image end, every later offset shifted)
  boots to the first dialogue identical to the original (`emu.py --smoke`), and the warps bt_oswald1, dn_glocian,
  dbg_face, ending, gear_status, title_load land with identical final frames (ending: credits scroll a few px apart,
  load timing). So the game opens these files by name (ISO directory) and reads the archive headers: entries may grow.
- Not packed yet: MSYS.DAT (flat file, text sections at 0x42800-0x4A81C: phase 4 rewrites them in place or grows the
  file), UPD.UPD (compressed, format unknown), BOOT.BIN/EBOOT.BIN (EBOOT shipped as is until code changes; then
  patch BOOT.BIN and re-sign: needs a signing tool (sign_np or similar), phase 5).
