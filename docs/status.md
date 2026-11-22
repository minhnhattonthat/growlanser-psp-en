# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 2. Debug tool next (phase 1 recon done session 3, 2026-11-22). No build yet.
- **Done (session 1):** Step 0 setup: hooks (`core.hooksPath tools/hooks`, check = `tools/check.py`, failing test
  blocks a commit: tested), guard hook blocks the sed canary, rom.sha1, AGENTS.md, decisions D1-D9 (PS1 project is
  the reference: its glossary copied to glossary.md, style-reference.md copied), PPSSPPHeadless boots the original ISO
  to title and first dialogue (`tools/routes/boot.txt`, smoke ok, savestate work/states/first_dialogue.ppst).
  Windowed PPSSPP v1.20.4 in tools/ppsspp (portable memstick, D3D11).
  Recon (docs/re/text.md, verified): same engine as PS1. BOOT.BIN = decrypted module. Encoding/font identical to PS1
  plus 0x6B new glyphs (font 0x836 x 18 B at BOOT.BIN 0x1230D8). SCEN.DAT 1140 entries, scenes 380-759, 31,914
  strings. MSYS text 0x42800-0x4A81C (3 sections). 10 module string tables tile BOOT.BIN 0x12C4A4-0x1331F8, getters
  at RAM 0x08876534-0x08876B50 mapped. Tools: datadat.py, elfrefs.py, getters.py, pspdbg.py (RAM dump over the
  WebSocket), dat/scen/gltext/rawgfx/gfxsweep from the PS1 repo.
  Graphics survey (docs/re/graphics.md): DATA.DAT BMPs and MSYS.DAT swept; P1-P10 listed.
  ISO PNGs, logo.bmp and both movies swept (P9, P10).
  Session 2: GLB.DAT decoded (`tools/glb.py`, RLE + palette + swizzled tiles, verified vs RAM); title source found
  (P8 = GLB B99_02_A, via `tools/gedump.py` GE frame capture); new P11 (tutorial status picture, GLB B08_01B), P12
  (仮 stamp, V49); GLB B/O/V, bind.dat, name_*.bmp clean. `pspdbg.py dump` also writes vram.bin.
  Session 3: static graphics sweep finished (graphics.md): `tools/textfind.py` (glyph-row screener + crop sheets)
  over GLB maps and MAP.DAT; new P13 = MAP.DAT 1325 PS1-style credits + kana atlas ("プレイヤー／"); GLB maps,
  rest of MAP.DAT, MAGD/NEFF (= PS1 files), .ani, the 30 MAP.DAT kana runs: clean. UPD.UPD compressed: re-check on
  screen in phase 8 (graphics.md "Re-check on screen").
- **Next (phase 2):** debug tool: PPSSPP has no Lua, poke RAM over the WebSocket with tools/pspdbg.py; port the PS1
  scene ids (PSP scene N = SCEN entry N+380, PS1 warp notes ../growlanser-en/docs/re/debug.md). Scene list should
  include the credits (to settle P5 vs P13 with gedump.py), title, game over, appendix room, tutorial (P11).
- **Open bugs:** none.
- **Waiting on the user:** (non-blocking) face-plate art spells ELIOTTE/RUISE/RICHART (DATA.DAT chr_face*.bmp);
  default = redraw to the glossary spellings (Elliot, Luise, Richard) per D9.
