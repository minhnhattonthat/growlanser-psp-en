# Graphics-text survey (phase 1, static sweep IN PROGRESS)

As on PS1, most UI art is already English (menu buttons, battle labels, MOVE/SPELL/ITEM/STATUS, CONGRATULATION,
NOW PLAYING, CV MESSAGE...). Dialogue, names, menus' item/spell names and place names are font text (text.md).
Tools: `tools/datadat.py` (DATA.DAT -> plain BMP/PNG files, `x FILE OUTDIR GLOB`), `tools/rawgfx.py` (raw 4/8bpp strips
by offset), `tools/gfxsweep.py` (sector archive -> deduped sheets; from the PS1 repo, untested here).

## Japanese graphics to redraw (phase 8)
| # | Element | Source (verified how) | Format | PS1 twin |
|---|---|---|---|---|
| P1 | Affinity labels 急所 半減 / 弱点 無効 / 普通 吸収 | MSYS.DAT ~0x9600-0xA800, x 192-255 (rendered `rawgfx --bpp 4 --stride 128`) | 4bpp, 256 px rows | G2 |
| P2 | Element icons 炎 風 聖 / 冷 雷 闇 / 地 物 精 | MSYS.DAT, rows under P1 | 4bpp | G3 |
| P3 | Affinity labels again, higher-res row in a sprite sheet (same six words) | DATA.DAT `MESWDA3E.bmp` y~118-134 (BMP viewed zoomed) | 8bpp BMP 256x256 | - |
| P4 | Appendix room labels "GLチップスカード入れ" + "(非売品)" (OMAKE/1), "VISUALビューモード" (OMAKE/2) | MSYS.DAT ~0x70000-0x84000 (rendered 8bpp, 256 px rows) | 8bpp | G4 |
| P5 | Credits: cast lines role／actor in Japanese over a romanized actor line; opening/ending song titles in 「」; a few JP staff entries | DATA.DAT `staff/stf01..08.bmp` and the `b` variants (512x512, stf08 256x256) | 8bpp BMP | G5 |
| P6 | Card binder margin label "のりしろ" (x2) | DATA.DAT `chips/chips01.bmp` (zoomed) | 8bpp BMP | - |
| P7 | Face-plate names: art is English but spelled PLAYER, ELIOTTE, RUISE, RICHART...; one "ダミー 3" plate and ダミー NN dummy cells (unused, guess) | DATA.DAT `chr_face.bmp`, `chr_face_frd.bmp` | 8bpp BMP | - |
| P8 | Title logo subtitle グローランサー under "GROWLANSER" | GLB.DAT `B99_02_A`: the whole 480x272 title (marble, logo, subtitle, English blurb, menu words, © line) is one baked image; decoded entry = the 12 title textures in RAM byte for byte, palette = title CLUT (`tools/gedump.py` at frame 650 -> work/qa/ge_title; `tools/glb.py`) | GLB RLE, 8bpp 4x3 swizzled 128 px tiles | G1 |
| P11 | Magic-class tutorial picture of a status screen: equipment ウィザードロッド / 厚手の服 / ミラーピアス, the element+affinity grid (炎 風 聖 / 冷 雷 闇 / 地 物 精 with 急所 半減 弱点 普通 吸収 無効) | GLB.DAT `B08_01B` (front layer, over `B08_01A`), zoomed work/x/b08b.png | GLB 8bpp | G7 |
| P12 | Big 仮 ("placeholder") stamp over a portrait close-up | GLB.DAT `V49` (same art as `V41` without the stamp); guess: unused placeholder, confirm on screen in phase 8 | GLB 8bpp | - |
| P9 | Movies: "GROWLANSER" logo with the katakana subtitle グローランサー, twice per movie (~51 s over clouds, ~105 s at the end) | `USRDIR/op1.pmf`, `op2.pmf` (ffmpeg 1 frame / 3 s, work/pmf/op{1,2}_all.png); two cuts of the opening | PSMF H.264 | G8 |
| P10 | XMB and save icons: logo with the subtitle グローランサー (+ tiny English blurb) | `PSP_GAME/ICON0.PNG`, `PIC0.PNG`, `USRDIR/GR_SAVE_ICON0.PNG`, `GR_SAVE_PIC1.PNG` (+ the GR_SAVE_* copies in DATA.DAT and DATA_BOOT.DAT); PARAM.SFO title グローランサー (text, `sfo.py`) | PNG | - |

P7 spellings conflict with the glossary (Elliot, Luise, Richard: PS1 D9); redrawing them to glossary spellings is the
default (non-blocking question in status.md).

## Swept, no Japanese
- DATA.DAT BMPs: MESWDA0a, STICN02a, autoall, spot, test_gr256, visual1-5 (gallery thumbnails), yuko00-02,
  chips/chips02-12 and chips/{a,b,c,d}/* cards (art + logo), effect/*.bmp, F0000/F5000 (portraits).
- MSYS.DAT 0x0-0x30000 (4bpp: UI labels, monster sprites, magic icons apart from P1/P2), 0x30000-0x42800 (8bpp world
  map, English script labels), 0x4B000-0x2B2000 (8bpp: GL chips title "GL CHIPS CHARACTER CARD COLLECTION", appendix
  room apart from P4, portraits).

- DATA.DAT `name_a..d.bmp` (name-entry backgrounds), `bind.dat` (27 RIFF/AT3 sounds, BE offset/size table).
- GLB.DAT (1119 records, format in `tools/glb.py`; all decode to exact size, PNGs in work/gfx/glb): all B*, O*, V*
  (except P11, P12), LOGO (blank), END_A/END_B/STAFF00 (sky), E00_A; B99_01_A = GAMEOVER + "STAND AGAIN... PRESS
  START button." (English), B99_03_A/04_A = "Please Change DISC 1/2" (English, PS1 leftover). V57 = world map with
  Latin place names (check spellings against the glossary in phase 8). Low-confidence: V03 (scattered papers).

## Still to sweep (phase 1 not done until these are rows above or listed here as clean)
- GLB.DAT T*/F*/D* map backgrounds: sheets work/gfx/glbsheets (69, 4x4 at half scale; full PNGs work/gfx/glb).
- MAP.DAT (1408 entries, smaller than PS1's: map art moved to GLB): `gfxsweep.py` sheets work/gfx/map128 (8bpp 128 px,
  53), map256 (8bpp 256 px, 79), map4 (4bpp 256 px, 79); 872 entries < 8 sectors skipped. Not reviewed yet.
- MAGD.BIN, NEFF.BIN, UPD.UPD (PS1: no text), DATA.DAT `.ani` (likely scripts).
- Review brief for these sheets: work/gfx/codex_brief.md (codex hit its usage limit until 2026-11-26: review by hand).

Also clean: `PIC1.PNG` (marble background), `USRDIR/logo.bmp` (ATLUS logo).
