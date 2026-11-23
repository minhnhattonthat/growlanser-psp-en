# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 9. Release done (session 20): release/Growlanser_PSP_EN_v1.0.zip built and verified by
  `tools/release.py` (every gate green, build 77cc9485); published 2026-11-23 on the user's request
  as GitHub release v1.0 (repo public since 2026-11-23; D18).
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
  Session 12 (phase 7 review fixes, H:\translation\.harness\reviews\growlanser-psp-en-phase7.md, both Importants):
  `tests/test_insert.py::test_en_build` runs the whole English build in check.py (~20 s); `insert.log_writes` logs
  each BOOT.BIN stage's writes (pools, heap_tables, move_buffers, msys_groups, armips) inside that stage's own ranges
  and `romdiff.check` gets the log (orig bytes, overwrites, overlaps); MSYS.DAT identical outside groups 6/7; SCEN
  edits only 380-759 (+ test: non-text entries identical after repack); `build.check_leaves` (disc: other files
  identical, only patched files move, no extent overlap). Review Minors 3-8 open (listed in the review file; 7 and 8
  are phase 8 checks: JP save on the EN build, longest name/item/place in battle messages, shops, place popup).
- **Phase 8 progress (sessions 12-13):** build e1c9255757b8ac0decb97d6512e3638b33bf050a (= build/growlanser_en.iso),
  copied to work/qa/tourbuild.iso (tours run on the copy: build.py can't overwrite an ISO an emulator holds).
  - **Tour gate: done.** `warp.py --all --iso work/qa/tourbuild.iso --out work/qa/tour` (81/81 landed; summary.tsv
    only has the 59 rows of the session-13 rerun, the first 22 landed in session 12's tour.log). `qa_gate.py init
    work/qa/manifest.tsv work/qa/tour --build work/qa/tourbuild.iso`; verdicts work/qa/verdicts/s12_main + s13_a..d
    (read by the controller, no subagents: crop sheets `sheet.py "DIR/f*.png" --from 1500 --crop 0,150,480,122
    --changed 0.06` in work/qa/crops, zoom on tags/boxes). `qa_gate.py check work/qa/manifest.tsv work/qa/verdicts`:
    111 sheets, 0 without verdict, 0 not ok. Notes: credits cast pages + 'リンクシンク' = P5/P13; affinity grid
    (equip/status) = P1/P2; tut_status picture = P11; face plates RUISE/ARIOST = P7; battle unit box ok (bt_bernard).
    The clear-save SAVE screen is reached at the end of the `credits` warp (fixture for APPENDIX: save there).
  - **Text coverage: done.** `tools/strings.py` -> build/strings.tsv; `tools/debug/cover.py --iso
    work/qa/tourbuild.iso --out work/qa/cov --jobs 4` (24 min; docs/re/debug.md "Text coverage": host mode on the
    newgame warp, printer + VM breakpoints); `textcover.py work/qa/cov build/strings.tsv`: 31404/31404 shown, exit 0
    (strings.tsv copy in work/qa/cov). Rerun after every build that changes text. 40 strings stalled in the host
    (drawn, never closed; work/qa/cov/stalls.tsv, `tools/debug/cover_ids.py`): mostly {FB00}..{FFFA} animated-face
    lines (dev menu scen018/379, scen325 x8); check a few in their own scene (scen112.0096, scen328.0044,
    scen071.0013, scen210.0017 have no FB00). `warp.py --textlog` logs strings per warp too.
  - **Graphics text (session 14): mostly done.** `tools/gfx.py` (`apply` from build.py in --mode en; `preview DIR`
    = original | English PNGs) computes every edit from the original files: P8 title (GLB B99_02_A subtitle ->
    marble; `glb.encode`), P10 ICON0/PIC0/GR_SAVE_ICON0/GR_SAVE_PIC1 (ISO + DATA.DAT + DATA_BOOT.DAT copies) + SFO
    TITLE "Growlanser", P12 V49 = V41, P1/P2 `statusgfx.py` (MSYS 0x9100, = PS1), P3 MESWDA3E.bmp labels (this is
    what the status screen draws), P11 tutorial GLB B08_01B (items + grid), P4 `appendixgfx.py` (MSYS 0x71000),
    P5 `tools/credits.py` (staff/stf01-07(b).bmp as one 256x7168 roll: 46 cast roles + song lines; P13 MAP.DAT
    pages are not drawn on PSP), P6 chips01.bmp GLUE. D15/D16. **DATA.DAT/DATA_BOOT.DAT entries must keep their
    size** (shorter PNG -> black staff roll; asserted in gfx.apply, tests/test_gfx.py). Verified in game on build
    2e1da691: title (work/qa/g1 smoke), gear_status grid (work/qa/gfx_status), tut_status (work/qa/gfx_tut f001800),
    credits roll English (work/qa/gfx_cred f018600-f025000), smoke ok. Not yet seen in game: appendix room (OMAKE),
    card binder, XMB/save icons (save screen at the end of the credits warp shows GR_SAVE_PIC1?).
  - **Session 15.** P7 done: `gfx.face_plates` (chr_face.bmp + chr_face_frd.bmp, DATA.DAT and DATA_BOOT.DAT): the
    13 misspelt plates -> ELLIOT/LUISE/JULIAN/RICHARD/DUMMY with letters cut from the sheet's own plates (D drawn),
    the 24 visible ダミー portrait cells -> DUMMY (5x7). Preview checked; in game the status header draws the edited
    sheet (work/qa/p7_plates/final.png, PLAYER plate; the renamed plates need those party members: check in the
    stress saves). Build 34fa210e, check ok.
    P9: `tools/pmflogo.py build` -> work/pmf/en/op{1,2}.pmf: fmvlogo.py mask/fill ported, the logo GOPs re-encoded
    with x264 (CQP per GOP) and their slices put back into the original AUs (slice headers rewritten for the GOP's
    own SPS/PPS: pic_init_qp changes per GOP; AU bytes pooled per GOP, only PTS packets pin an AU start; filler
    NAL padding). ffmpeg decodes both with 0 errors, same frame count, frames outside the 14 edited GOPs identical,
    subtitle gone in every sampled frame (work/pmf/en/*.png). **But PPSSPP's attract movie (idle at the title ~f3400)
    corrupts from the first edited GOP (~f6300) and returns to the title at f6600** (work/qa/pmf_idle vs
    pmf_idle_jp, --shots 6150..6650). So `gfx.apply` does not ship it. Suspects: PPSSPP/sceMpeg wants each AU at its
    original size/position (try: per-AU sizes kept, only GOPs where x264 fits every AU, or freeze frames), or the
    filler NAL / zero padding, or x264 SPS-independent features (check with a GOP re-encoded from unedited frames).
  - **Session 16** (build **b273cde9**, commits 3f916e2, 8a4b916). P9 shipped: pmflogo keeps every AU at its
    original offset+size (one QP per GOP; tiny all-skip AUs kept as is); PPSSPP plays op1 (attract) and op2 clean,
    subtitle gone (work/qa/pmf_full, docs/re/graphics.md). P7: the status/field-menu plates are drawn from
    DATA.DAT **MESWDA0a.bmp** (x 72, y 12k), not chr_face: now edited too; LUISE plate seen in game
    (work/qa/stress/stress_full_status). `tools/inkqa.py` + `inkcheck.py` ported (PSP colours +-3, one-line popups
    only, SKIP tut_status): old tour 0 off-centre (bubbles 7/5, 5/5; popups ev_battle003 14/14, ev_delis 23/24).
    Inventory mapped (docs/re/debug.md "Inventory"); `save.py make --stress` -> work/saves/stress_full (st_vac07,
    every list full, ELM 999999, qty 99, hero 99/999); `tools/debug/stressrun.py` cases items/status/spell/equip/save
    -> work/qa/stress/stress_full_*/sheet*.png (on b273cde9). Seen ok by eye: items (names fit, qty draws 1 digit
    "x9" as PS1), status + Luise spell list (3-line descriptions fit). Not yet viewed: equip, spell, save sheets.
    **Left running at hand-back:** `warp.py --all --iso work/qa/tourbuild.iso --out work/qa/tour` (log
    work/qa/tour3.log, b273cde9) and `warp.py --all --iso work/qa/inkbuild.iso --out work/qa/ink20 --shot-every 20
    --no-sheet` (log work/qa/ink20.log, d414384e: centring is unchanged by the plate edit). Check for stray
    warp.py / PPSSPPHeadless before starting new tours; rerun if a log ends early.
  - **Session 17** (build **6769d381** = build/ = work/qa/tourbuild.iso = work/qa/stressbuild.iso, commit 1756838).
    Fixes: boot.items.0282 "Portable Pillar[0107]" drew a stray 柱 -> "Portable Pillar II" (the improved model, per its
    description; [0107] in batches.GLYPH_VARS); time-skip/objective captions ending ‥‥ ("One month later...") were
    3/13 px off-centre in the title popup (frame = ceil(W/12)*12 + 5, text at left) -> `insert.POPUP_IDS` gets
    title_lead (now 7/9, work/qa/ink21). Tours are deterministic (same build -> byte-identical sheets).
    - Stress gate: work/qa/stress/manifest.tsv, verdicts work/qa/stress/verdicts/s17.tsv (27 ok, full-res review
      sheets work/qa/stress_rv; JP compares work/qa/stress_jp: save list, status scroll, ACCESORIES header are the
      original's). Was green on 22107175; a re-run on 6769d381 was started (work/qa/stress/run.log).
    - Ink gate: `tools/inkqa.py work/qa/ink20/*` exit 0 (credits/ending frames <= f3400 replaced by 6769d381 shots;
      two per-shot SKIPs with reasons in inkqa.SKIP).
    - Tour gate: tour3 (b273cde9) in work/qa/tour, manifest inited on it, all 63 changed sheets got verdicts
      (work/qa/verdicts/s17_tour.tsv; changes were the title tile + plates). **tour4 on 6769d381 running** at
      hand-back (`warp.py --all --iso work/qa/tourbuild.iso --out work/qa/tour4`, log work/qa/tour4.log).
  - **Session 18** (build **a38240ae** = build/ = work/qa/tourbuild.iso = stressbuild.iso = vrbuild.iso; commits
    6a47f36, 1da87b0). Clear-save fixture (`save.py make work/saves/clear --clear work/states/credits.ppst`;
    `warp.py --scene title_appendix --sav work/saves/clear`): APPENDIX room reached. **Bug fixed:** VISUAL ROOM list
    titles (msys.skills.0057-0094, PS1-style "Title -- line") wrapped mid-word in a 16-cell box: now "Title{n}~line~"
    as the JP (polish batch work/tl/p002), fit.py budget 16 x 2 (measured), all 38 seen in game (work/qa/apx_vis3).
    P4 OMAKE/2 VISUAL ROOM label English in game; OMAKE/1 GL CARDS + P6 binder locked (cards not collected, flags not
    found: docs/re/debug.md "Appendix"). New warp `gameover` (kill now lowers HP once; GAMEOVER English original).
    P10 save icon English in a save written by the EN build (work/saves/en_vac07, work/qa/save_icon_en.png). JP save
    (work/saves/stress_full) loads on the EN build (save.py check --iso; money read back). WSL could not start
    (HCS no resources): tools/sign.py caches the signed EBOOT by ELF sha1 (text-only builds skip WSL).
    - Tour gate: tour5 on a38240ae (82/82 landed, incl. gameover) copied into work/qa/tour, manifest re-inited,
      26 changed sheets reviewed (work/qa/verdicts/s18_tour.tsv): `qa_gate.py check` 113 sheets, 0 missing, 0 not ok.
  - **Session 19 (phase 8 done, build a38240ae).** Coverage: chunk 2 rerun (`cover.py --only 2 --reruns 25`, 12
    runs, log work/qa/cov_c02.log) done; `textcover.py work/qa/cov build/strings.tsv`: 31404/31404, exit 0. Stress
    gate: run + manifest on a38240ae, `qa_gate.py check work/qa/stress/manifest.tsv work/qa/stress/verdicts` 27
    sheets, 0 missing/not ok/changed. Tour gate `check work/qa/manifest.tsv work/qa/verdicts` 113 sheets exit 0.
    Smoke ok (work/qa/smoke). GL CARDS (P4 OMAKE/1) + binder (P6): still locked in game; using GL Chips from ITEM
    does nothing (docs/re/debug.md "Appendix"); both edits checked in `gfx.py preview` only: accepted gap.
  - **Session 20 (phase 9 done).** Story pass: `tools/story.py` -> 47 chapter files work/qa/story/chapters ('='
    pair as PS1, '*' new); worker read every '*' line of c01-c15/c18/c19 and c16_1 in full; reviewer subagents read
    c11, c16_2-6, c17_1-2 whole (work/qa/story/reports/). Verdicts s20_a/s20_b.tsv: 47 ok, `qa_gate check` exit 0.
    Important fixed: scen084.0081 (Melfie's parents were the team leaders), scen157.0061 ("original world" vs Old
    World), scen176.0230 (Justin "you lot"). Polish pass: batch work/tl/s20fix (spec s20fix.spec.tsv, 171 lines
    merged); docs/polish.md 0 open (fixed or waived with reason). D17: 様 after a name var dropped as PS1; drawn
    common nouns stay capitalised. README filled; docs/release-readme.txt; tools/release.py (PS1 port: build, check,
    smoke, leftover JP, every qa_gate, textcover, polish, README, debug off, xdelta -B, re-apply, zip) exit 0:
    zip = xdelta (4876212 B) + README.txt; base SHA-1 db0c5dff..., patched SHA-1 77cc9485f8f3....
    Not redone after the 171 text edits: tour sheets/coverage (edits are fit-linted by check.py; ids unchanged).
- **Next (after release):**
  1. Publishing (repo public, `gh release create`) only when the user asks (D8; pipeline.md §Publish).
  2. Player bug reports via GitHub issues (AGENTS.md).
  3. Optional: re-tour the scenes touched by s20fix (s040, s041, s084, s157, s16x-s18x, s325-s333) for a visual check.
  4. Gaps left (non-blocking, never reached in game): shops (handler not found: boot.sys.0169 "Buy & Equip" etc.
     unmeasured), GL CARDS / binder, other units' max stats, singular qty, UPD.UPD on screen, captions scen010.0114
     / scen014.0003 (mid-scene), place popup, battle messages.
- **Open bugs:** Signed EBOOT untested on real hardware (tag 0 instead of the original key).
- **Waiting on the user:** (non-blocking) face-plate art spelled ELIOTTE/RUISE/RICHART: redrawn to the glossary
  spellings (Elliot, Luise, Richard) per D9 (session 15); say if the original art spellings should stay.
