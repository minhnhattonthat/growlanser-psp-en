# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 5. Engine spike and marker build in progress (VWF + marker build working; width gate left), session 7.
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
  Session 4 (phase 2, docs/re/debug.md): `tools/debug/warp.py` (RAM pokes over the WebSocket: New Game code patched,
  scene request held, landing asserted on the save block; `jump 0xOFF` sets the event VM at a breakpoint; `kill F`)
  + `tools/debug/scenes.txt` (80 entries: title/config/load/appendix, new game, dev check menu + its 15 items, 15
  story points, 16 event quick checks, 14 event battles, 5 dungeons, ending, credits, tutorial status P11, field
  menu + gear screens): `warp.py --all --out work/qa/warp` = 80/80 land (work/qa/warp/summary.tsv, finals*.png
  checked by eye), states in work/states/<name>.ppst. `tools/debug/save.py` (saves are encrypted: RAM edits +
  in-game save; make + check round trip verified for money/LV/HP, work/saves/edit1). No disc 2 on PSP.
  Session 5 (phase 3, docs/re/build.md): `build.py` (+ `--identity`) with `pack()` in dat.py / datadat.py / glb.py
  for SCEN, MAP, MAGD, DATA, DATA_BOOT, GLB; identity ISO SHA-1 = rom.sha1 (tests/test_identity.py, in check).
  Relocation proven in game: all six grown and moved to the image end -> smoke + 6 warps identical to the original.
  warp.py `--all --iso X` now keeps states in the out dir (work/states = original ISO only).
  Session 6 (phase 4, docs/re/text.md "Script files"): `tools/extract.py` (+ `--check`, from the PS1 repo, with
  `textsec.py`) -> script/scen (309), script/msys (3), script/boot (10 module tables + save.json/kbd.json in-place
  cstr pools): 36,283 strings, all rebuild byte-identical (tests/test_extract.py, in check; ranges tile).
  `tbl/jp.tbl` = PS1 table + PSP glyphs 0x7CB-0x835 (`tools/fontmatch.py ... 0x1230D8`, 5 fixed by eye).
  28,401/35,972 PSP jp strings equal a translated PS1 jp exactly: prefill those in phase 6.
  Session 7 (phase 5, docs/re/build.md "EBOOT", text.md "Printer and the English VWF"): `tools/sign.py` (sign_np
  under WSL, tag 0) -> signed EBOOT boots. `asm/vwf.asm` = PS1 VWF port (pair codes, font/en12.txt, `tools/enfont.py`
  copied), hooks pinned in `tools/insert.py` HOOKS; PRX R_MIPS_26 rule (`tools/prxrel.py`) enforced by insert.armips.
  `build.py --mode jp|marker|en [--qa ID=TEXT]`: jp = byte-identical ISO; marker = every string "[id] The quick..."
  at the JP word count (in place, no relocation) -> boots, smoke ok, 10 warps land (work/qa/mk), dialogue/choices/
  menus draw English (work/qa/mk_dlg). tests/test_insert.py. D10 (keyboard grids + default names stay JP), D11 (VWF).
  Recon tools: `tools/mips.py` (func/calls/gp refs on a RAM dump), `tools/debug/trace.py` (breakpoint call tracer).
- **Next (phase 5, rest):** (1) width gate: copy PS1 `tools/stress.py` + `tools/fit.py` (BUDGETS) + docs/windows.md
  model; `--qa` needs a file option and in-place room: let SCEN entries grow (dat.pack moves them; RAM scene buffer
  size unknown on PSP: find it) and for BOOT tables shrink the other markers of that pool when an override is longer.
  Measure every variant of PS1 windows.md on PSP (dialogue cells per line: box looked 24 cells/288 px?, name tag,
  choices, help, descriptions, item/spell/skill/class/unit names, config, place popup, captions, sys.0069 slots).
  (2) name-tag pad (PS1 insert.Encoder.tag_pad), popup width hook (PS1 popup_width, find PSP 0x8006BA48 twin),
  caption centring; CONT_RA1/2 only if a "We  lcome" gap shows. (3) glyph torture line in the dialogue box.
  (4) marker tour wider: battle UI (bt_*), shops, save screen, credits; anything still Japanese = unextracted text.
  Phase 7 later: grown pools need relocation (BOOT tables -> free kanji cells 0x11C-0x69F like PS1 Heap; MSYS
  growth; SCEN slot size); dictionary / MSYS packing only if RAM limits demand it (PS1 needed both).
  Phase 8 warp additions still open: game over (docs/re/debug.md "Game over"), clear-save fixture for APPENDIX,
  shops, stress saves (inventory lists, other unit records). Credits: cast pages with Japanese names at f21000-23400
  of the `credits` warp (settle P5 vs P13 there).
- **Open bugs:** name tag shows 2 codes only ("0." for scen000.0001 marker: tag width = code count, needs tag_pad).
  Signed EBOOT untested on real hardware (tag 0 instead of the original key).
- **Waiting on the user:** (non-blocking) face-plate art spells ELIOTTE/RUISE/RICHART (DATA.DAT chr_face*.bmp);
  default = redraw to the glossary spellings (Elliot, Luise, Richard) per D9.
