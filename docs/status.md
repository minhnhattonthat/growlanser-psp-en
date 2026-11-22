# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 8. QA in the emulator: next (phase 7 done in session 11: English build green, buffers moved, fitting
  ported, romdiff gate).
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
  Session 8 (phase 5 done, docs/windows.md): width gate. `tools/stress.py` (rulers) + `build.py --qa-file F --out X`
  (a ruler's pool shrinks its other markers to ids: insert.marker short / Encoder.squeeze). Measured on PSP = PS1
  budgets: dialogue 24 cells x 3 lines, choices 24 after the bullet (6 rows), name tag 144 px, help + descriptions
  24 x 3, item names / config labels / values 8 cells, field-menu bubble 12 cells, sys.0069 slices as PS1; spells,
  skills, classes, units, growth graph = JP lower bounds; captions guess. Wait codes left a 6 px gap: vwf.asm
  CONT_RA1 = 0x0886AAB4 (fixed, work/qa/s3c/wait). Torture line legible (work/qa/s4/tort). `tools/fit.py` +
  tests/test_fit.py ported (PSP: start rule after waits too). D12 (keep the 24-cell box: PS1 English fits as is).
  New warp entry gear_spell (spell list; empty: Luise not in party there).
  Session 9 (phase 6): `tools/prefill.py --write` copied the PS1 English into 28,326 strings ("src": "ps1"; PS1 and
  PSP scene numbers shift after ~s121, e.g. PSP s200 = PS1 s159: `scene_map` picks the matching PS1 scene);
  `tools/fit.py` 0 errors. Ported from PS1: `tools/batches.py` (exe -> boot pools; split adds a `## PS1 reference`
  part to build/terms_bNNN.txt: `near` = most similar PS1 line + English, `ctx` = translated neighbours),
  `tools/tl_run.py` (codex pipeline; + `psp-scenes` = synopsis section 6 for PSP-only scenes), termscan.py,
  newterms.py, docs/translator-brief.md (PSP header + PS1 reference), reviewer-brief.md, story-reviewer-brief.md,
  synopsis.md (PS1 scene ids). `insert.needs_english`. Batches: work/tl/b001.. (`batches.py split --size 3500`).
  work/tl/termscan.tsv: new PSP names to rule (メルフィ 178, アメリア 145, ジャスティン 113, デュンケルス 88, ラミィ 46,
  ユリィ 21, コリン 14, 『るいせちゃんのお部屋』).
  codex exec hit its usage limit (until 2026-11-26): D13 = translator/reviewer subagents instead. On PSP 目 is
  `{s:012A}` (GLYPH_VARS, + {s:012E} 爪, {s:0047} 教授). tbl 04C2 = 噂 (was 哮), 07ED = 哮; jp fields updated.
  Check rules added: no honorific after a {s:} variable (PS1 dropped 90/90); boot.save raw newline = `{lf}` in
  batches, no VWF lint for boot.save. `tools/svars.py > build/svars.txt` (what each {s:XXXX} draws: regenerate
  after names merge). Review = reviewer subagents on `tl_run.py pairs bNNN` files; Minors -> docs/polish.md;
  merged batches get work/tl/bNNN.done. All 67 batches (7,321 strings) translated by 17 translator subagents,
  reviewed by 13 reviewer subagents (every Critical/Important fixed), merged: 0 strings need English, fit.py 0
  errors, `batches.py check` (all shipped English) 0 problems. ~170 Minors in docs/polish.md (polish pass before
  release, incl. sweeps: American spelling, 様 -> Lord/Lady before {s:} names, Portable Mana Pillar case).
  Session 10 (phase 6 review fixes, H:\translation\.harness\reviews\growlanser-psp-en-phase6.md): synopsis
  section 6 written (PSP-only Darkfall arc, from a skim of the English, not line by line: the phase 9 story pass
  must read the 43 PSP-only scenes in order against it and correct it); 45 voice/register items moved out of
  polish.md and fixed (polish batch work/tl/p001, merged through the wrapper; hard {p} kept before voice codes);
  3 British spellings; batches.py check 28 min -> 23 s and now in check.py (+ tests/test_batches.py);
  tools/show.py (strings by id). Review Minor 2 (様 -> Lord/Lady sweep vs PS1 precedent) still open: get a ruling
  into decisions.md before the polish pass. Lint gap seen: nothing flags an English line with fewer {p} than the
  JP before a voice code (wrapper drops the page break); worth a batches.py rule.
  Phase 7 so far: BOOT tables relocated into a string heap (`insert.heap_tables`, getters repointed, verified in game
  on the marker build). docs/re/text.md "Phase 7" has the MSYS and scene buffer findings.
  Session 11 (phase 7 done; docs/re/text.md "Phase 7", docs/windows.md): `python -X utf8 build.py` builds the full
  English ISO. Scene pair buffer and MSYS buffer moved to a grown BSS (phdr[1] memsz -> 0x08DD2000; scene 0x08DB2000
  0xF800, MSYS 0x08DC2000 0x10000; `insert.move_buffers`, 14 pinned sites incl. one hidden base+0x16000 read, scene
  bound 0xB000 -> 0xF800). SCEN text sections grow their entries (dat.pack moves them; `check_scen_fit`). MSYS
  groups 6 (items) / 7 (magic + skills) appended to MSYS.DAT when grown, BOOT sector tables updated
  (`msys_groups`). Build gates: `stale_refs` (no code left building an old buffer address), romdiff of BOOT.BIN vs
  the declared write ranges. Fitting ported from PS1: tag_pad, popup_width asm hook (popup 0x08871B30), caption
  centre, title_lead, name-entry slots. Verified: smoke (English first dialogue), warps menu/gear_items (English
  item description from the moved MSYS group, Square help)/name_entry/ending, scene 186 (largest pair, text ends
  0xBE04 > old 0xB000) byte-identical in the new buffer (RAM dump work/qa/p7_s186ram), `warp.py --all` on the
  English build: see work/qa/p7_warp_en/summary.tsv. tests: test_move_buffers, test_msys_groups, test_fitting.
- **Next (phase 8, QA in the emulator):** tour every changed scene with the debug tool, contact sheets, visual-QA
  verdicts (`qa_gate.py`), graphics text (P1-P13 in docs/re/graphics.md), inkbox on choice/centred boxes, stress
  saves, `textcover.py`. Measure on screen: battle UI (unit / class names, battle messages: bt_tutorial lands before
  the battle starts), captions (scen010.0114, scen014.0003: Encoder.centre bias is PS1's), spell list with Luise in
  the party, place popup (popup_width), shops, save screen. boot.save English has real "\n" (system dialog).
  {s:FFED} in scen188.0058 (alpha waves?) to check in game. Raw `warp.py --scene "scene 186"` lands on a black
  map (original too): give story scenes their area/sub in scenes.txt when touring them. Saves made with the JP game
  may hold scene-buffer pointers (copy at 0x08808004 from 0x08B7EF38): test loading a JP save on the English build.
  Phase 8 warp additions still open: game over (docs/re/debug.md "Game over"), clear-save fixture for APPENDIX,
  shops, stress saves (inventory lists, other unit records). Credits: cast pages with Japanese names at f21000-23400
  of the `credits` warp (settle P5 vs P13 there).
- **Open bugs:** Signed EBOOT untested on real hardware (tag 0 instead of the original key).
- **Waiting on the user:** (non-blocking) face-plate art spells ELIOTTE/RUISE/RICHART (DATA.DAT chr_face*.bmp);
  default = redraw to the glossary spellings (Elliot, Luise, Richard) per D9.
