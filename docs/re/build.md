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
  file), UPD.UPD (compressed, format unknown).

## EBOOT (phase 5, verified)
- Code patches go into BOOT.BIN (plain PRX); `tools/sign.py` re-signs it with sign_np -elf (source tools/sign_np/src,
  GPLv3, built under WSL once: command in sign.py) into EBOOT.BIN; build.py ships both. The original ~PSP tag
  0xC0CB167C is an old key sign_np can't make; tag 0 (0xD91609F0) is used. Proof: a BOOT.BIN with the font inverted,
  signed into EBOOT.BIN only (original BOOT.BIN left), showed inverted glyphs at the first dialogue (work/qa/signspike).
  Issue #1: v1.0 black-screens on a Vita (status.md "Open bugs"). sign_np (patched: optional devkit hex arg) is given
  the original's devkit_version 0x03090510 (`sign.DEVKIT`) so the ~PSP header differs only in tag and keys.
- Memory: the module's grown BSS (`insert.move_buffers`) is paid back from the newlib heap (sce_newlib_heap_kb_size
  0x08958D44, allocated right after the module), so the heap still ends at 0x09D4B000 and the user RAM above it is
  as the original left it. PPSSPP HLEs the codec modules and has slack there that real hardware may not.
- PRX relocations (`tools/prxrel.py`, 65,523 entries): the loader adds the base 0x08804000 at each. A patched word at
  an R_MIPS_26 site (every original j/jal) must stay a j/jal with a module-relative target (asm macros CALL_REL /
  JUMP_REL), any other word there is corrupted at load; `insert.armips` enforces it. New code in the free font cells
  uses absolute RAM addresses (module base is fixed; no new relocation entries).
- Modes: `build.py --mode jp` = text re-encoded, shipped EBOOT, ISO byte-identical to rom.sha1 (verified);
  `--mode marker` / default en: armips + signed EBOOT.
