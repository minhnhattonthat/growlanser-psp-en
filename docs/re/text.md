# Text: encoding, font, containers (PSP, ULJM-05423)

The PSP remake keeps the PS1 text system almost unchanged (PS1 notes: `../growlanser-en/docs/re/text.md`). Verified
facts below say how; anything marked (guess) is not yet checked.

## Disc layout (verified: `tools/iso9660.py list`, work/isolist.txt)
- `PSP_GAME/SYSDIR/EBOOT.BIN` is the encrypted (~PSP) module; **`SYSDIR/BOOT.BIN` is the same module decrypted**:
  byte-identical to the PPSSPP dump (`DumpFileTypes = 7`, `ULJM05423_EBOOT.BIN`, 1934992 B) over BOOT.BIN's 1934652
  bytes (the dump has 340 trailing bytes more). Work from BOOT.BIN; ship a re-signed EBOOT (platform-psp.md).
- `USRDIR/gr_data1/`: SCEN.DAT (scenes), MSYS.DAT (system graphics + description text), MAP.DAT (sector archive,
  1408 entries), MAGD.BIN (64 entries), UPD.UPD, NEFF.BIN, GLB.DAT (big graphics archive, 14-byte records
  `name[10] + u32 BE`), DATA.DAT (named archive, `tools/datadat.py`: BMP/PNG/AT3/VAG/.ani), VOICE.DAT (782 MB).
  `USRDIR/DATA_BOOT.DAT` = small DATA.DAT-format subset. `op1.pmf`/`op2.pmf` = movies. TMP.DAT is all zero (guess:
  scratch file).
- PARAM.SFO: DISC_ID ULJM05423, DISC_VERSION 1.01, TITLE グローランサー (128-byte slot).

## Module (verified: ELF headers, RAM dump work/qa/ram_d1 via `tools/pspdbg.py dump`)
- BOOT.BIN is a relocatable PRX (e_type 0xFFA0). .text vaddr 0x24 @ file 0xC4 (size 0x10E550); .rodata vaddr
  0x10F0D0 @ 0x10F170; .data vaddr 0x11D3C0 @ 0x11D480. So file = vaddr + 0xA0 (text/rodata), vaddr + 0xC0 (data).
- Loads at **0x08804000** (module "Model" in `hle.module.list`): RAM = 0x08804000 + vaddr.
- HI16/LO16 pairs in the file are relative to the **data segment** start (vaddr 0x11D3C0), not to 0: a `lui 0x0001`
  becomes `lui 0x0893` after loading. `tools/elfrefs.py` reports raw values; add 0x11D3C0 for data targets.

## Encoding (verified: SCEN.DAT decoded with the PS1 table reads as natural Japanese, scene 380 = PS1 scene 280)
- Same as PS1: u16 LE words, < 0xF000 = glyph index; FFFE end, FFFF empty/name, FFFC {n}, FFFD {p}; F600 {s:}, F700,
  F800 {v:} take one argument word; F4xx = dictionary; other Fxxx = command + parameter byte. Codec `tools/gltext.py`
  (copied from the PS1 repo), table `tbl/jp.tbl` (PS1 table + PSP glyphs 0x7CB-0x835, phase 4).
- Font: **BOOT.BIN 0x1230D8** (vaddr 0x123018, RAM 0x08927018; pointer to it kept at RAM 0x08CDE890), 12x12 1bpp,
  18 bytes/glyph, **0x836 glyphs** (ends exactly where the dict pool starts). Glyphs 0x000-0x7CA are the PS1 font
  (PS1 glyph bytes found at the same index offsets); **0x7CB-0x835 are new** (kanji used by PSP-only text: 90 unknown
  codes in SCEN.DAT, most frequent 01BE (PS1 flourish), 07F3, 07D4, 07E2...). Phase 4: render 0x7CB+ and extend the
  table into `tbl/jp.tbl`.

## SCEN.DAT (verified: `tools/scen.py` survey -> work/scen_survey.txt)
- Same archive (`tools/dat.py`): u32 count = **1140** (380 x 3; PS1 840 = 280 x 3), (u16 sector, u16 count) each.
- Scene entries **380-759** (380 scene ids; PS1 had 280): header 25 x u32, word 0 = 0x64, word 22 = text section
  offset; section = u32 size, u16 offsets, strings. 309 entries have text: **31,914 strings** (PS1 25,557). Entries
  0-379 and 760+ are other data. Every section ends inside its entry (no non-zero tail).
- PS1 quirks to re-check in phase 4: unreferenced choice lines after their question, offsets 2 bytes into a string.

## MSYS.DAT text (verified: section headers parsed, PS1 strings found inside)
- Three sections in the SCEN section format, tiling **0x42800-0x4A81C**, zero to 0x4B000 (free: 0x150 bytes after the
  first section, 0x7E4 after the last):
  items 0x42800 (size 0x56B0, 290 strings; PS1 268), magic 0x48000 (0xDBC, 35), skills 0x48DBC (0x1A60, 224; PS1 173).
- Read at run time through 0x08853C34(a0 = 1, a1 = section) (guess: returns the loaded MSYS text block); the
  description getters at 0x0887680C.. call it with bounds 0x40, 0x64, 0x172, 0x26 (+0xC0), 0x26 (+0x10C), 0x33 (+0x158).

## Module string tables (verified: getters disassembled, `tools/getters.py work/qa/ram_d1/ram.bin 08876200 08876B50`)
Getter form as PS1: `if i < count: return base + 2 * table[i]` (u16 word offsets), else sys entry 0. The PSP puts
each **pool first and its table right after it**; together they tile **BOOT.BIN 0x12C4A4-0x1331F8** with no gaps
(the font ends at 0x12C4A4; the sys table ends at 0x1331F8, data follows directly: no free space here).

| table | pool (file) | offset table (file) | count | getter (RAM) | notes |
|---|---|---|---|---|---|
| dict | 0x12C4A4 | 0x12D640 | 0x100 | 0x08876938 | F4xx dictionary |
| places | 0x12D840 | 0x12D954 | 0x14 | 0x0887675C | slot 6 -> RAM buffer (renamable town) |
| help | 0x12D97C | 0x12E018 | 0x24 | 0x08876984 | |
| items | 0x12E060 | 0x12F2A0 | 0x172 | 0x08876678 | PS1 0x168 |
| skills | 0x12F584 | 0x12FA5C | 0x64 | 0x08876710 | PS1 0x40 |
| magic | 0x12FB28 | 0x12FD6C | 0x40 | 0x088766C4 | |
| classes | 0x12FDEC | 0x130310 | 0x11D | 0x0887662C | PS1 0xFE |
| units | 0x13054C | 0x131540 | 0x167 | 0x088765B0 | slots 0, 0x10, 0x134 -> RAM buffers |
| names | 0x131810 | 0x131EBC | 0x167 | 0x08876534 | slots 0, 0x10, 0x134 -> RAM buffers |
| sys | 0x13218C | 0x133068 | 0xC8 | 0x088763CC | PS1 0xC5 |

- Code reaches the pools only through these getters as far as checked: no u32 pointer to any pool or table exists in
  BOOT.BIN or in the RAM dump, and the lui/addiu scan finds only the getter references (0x72788-0x72B48 in vaddr).
  Phase 5: grow the pools by re-pointing the getters' lui/addiu pairs (keep the PRX relocation entries valid) to a new
  block (end of .data / a new segment; free space TBD).

## Other text
- BOOT.BIN Shift-JIS: name-entry keyboard grids at 0x1137D0-0x113A45 (hiragana, katakana, full-width Latin, digits,
  symbols; 10 cells per row). PS1 ruling D14 kept the grids; decide in phase 5.
- BOOT.BIN UTF-8 (save/load messages for the system save utility, 21 strings, 0x117A80-0x1193E0): "グローランサー",
  "セーブデータ", Memory Stick errors, "%dKB" free-space prompts, save/load cancelled/failed, "AUTO SAVEをOFFにします。";
  plus Shift-JIS format strings 0x1172E4 (voice not found, debug) and 0x117408 (save title `グローランサー［%s］　%s：%s：%s　%s`).
  "NEW RAINBOW ISLANDS\nハーディガーディ大冒険!!" at 0x118C34 (guess: another game's title in a library/advert list).
- MAP.DAT: 30 kana-like runs, checked (session 3): tile data (ざぶぷェ複..., こここ...), no font text. UPD.UPD: 1 hit
  (noise; the file is compressed).
- GLB.DAT kana-like hits are image data (checked a sample: decodes as noise).

## Printer and the English VWF (phase 5, verified: disassembly of a RAM dump, `tools/debug/trace.py`, marker build)
The PSP code is a recompile of the PS1 printer (PS1 notes: `../growlanser-en/docs/re/text.md` "Text drawing"):
- Printer **0x088748A0** (frame 0x80; s6 column, s5 row), called from the print wrapper 0x08868480 (frame 0x30, ra at
  +0x20; returns to 0x08868504) and 0x08875830. Glyph routines (read the font via pointer 0x08CDE890): 0x08876C14
  normal (y = row*16+2, x = col*12 texels), jal at 0x0887501C (row s5) and 0x088750F8 (row s5+1); 0x0887705C double
  (y = row*16+6), jal at 0x08874CE0. Each is followed by jal WAIT 0x0886BF54 and s6 += 1 / 2. Canvas struct
  0x08CDE894 = PS1 layout (base1, stride1, split col, -, base2, stride2), u16 text colour at +0x20, shadow colour 5.
- Message display 0x08868788 calls the wrapper from 12 sites. **Typewriter** flag = byte 0x08CD1B63 (PS1 gp+0x87E):
  tests at 0x08869BCC / 0x08869DCC branch to the typewriter blocks (0x0886A8C0 / 0x0886A93C: 0x0886A9B8 prints the
  first code, then 0x08869FC4 prints one code per frame into a 1x1-column window at the cursor; trace: a0 = 0, 1,
  2...). Otherwise the page path (wrapper call 0x08869E90 after 0x08869DCC; twin 0x08869C5C after 0x08869BCC, guess).
- **Pre-parser** 0x088673D8: loop head 0x088675D4 (`lhu a1, (s2)`, s2 += 2), column s1 += 1 at 0x088677F4 (+2 at
  0x08867A58), extent: min col s16 0x08CCD5D4, max start col s16 0x08CD1BBC, max row 0x08CD1B24; page print width =
  max - min + 1.
- `asm/vwf.asm` (port of the PS1 one, without dictionary / MSYS packing / popup width yet): glyph calls -> vwf_std /
  vwf_big (they set s6 = ceil(x/12) themselves; the s6 steps become nops, WAIT stays), both typewriter tests nop'd
  (page at once), pre-parser steps -> vwf_measure, printer entry -> vwf_newstr (continuation return addresses
  CONT_RA1/2 still 0 = every print is a new string; PS1 needed them for "We  lcome" gaps after a first-code print;
  not seen in the PSP marker tour so far). Code + en font in font cells 0x6A0+ (RAM 0x0892E7B8, ends 0x0892F6D8).
- Marker build (work/qa/mk, mk_dlg): dialogue pages (multi-line, wait continuations), choice menu (dbgmenu), field
  menu, item list, status, config all draw English pairs. Name tag shows "0." for a 2-code tag (PS1 tag_pad needed).

## Script files (phase 4, verified: `tools/extract.py --check` rebuilds every pool byte-identical; tests/test_extract.py)
`python -X utf8 tools/extract.py` writes script/*.json (never overwrites; `--force` only files with no English):
- `scen/sNNN.json` (309 files, N = SCEN entry - 380), `msys/{items,magic,skills}.json`: form "section" (entry, at, pad,
  refs = one "i" or "i+delta" per offset slot in slot order).
- `boot/<table>.json` (dict, places, help, items, skills, magic, classes, units, names, sys): form "table" (table, base,
  fill = zero words between pool and table, refs). The skills table holds 0x66 words (getter bound 0x64).
- `boot/save.json` (17 UTF-8/SJIS save-utility strings + the SJIS save title), `boot/kbd.json` (30 name-entry rows):
  form "cstr", in place: at, size (slot incl. NUL fill), enc. The English save-library messages at 0x119190-0x119250
  (same set, other PSP system language) can be copied. Debug printf (0x1172E4), full-width digits 0x1177A0 and the
  other-game title 0x118C34 are left out.
- Entry: id, jp (terminator excluded), en, term (end = FFFE, null = FFFF), unref (no pointer). 36,283 strings, 4,523
  unref. Unmapped glyphs only the PS1 ones (icons, flourish 01BE, blanks) and 07ED (true 哮; 04C2 = PS1 哮).
- 28,401 of 35,972 non-empty PSP jp strings equal a translated PS1 jp string exactly (scen 26,670/33,777).
