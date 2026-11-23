# Debug tool: scene warp (phase 2)

RAM addresses (user RAM 0x08800000+, module at 0x08804000: RAM = 0x08804000 + vaddr). The engine is the PS1 one
(`../growlanser-en/docs/re/debug.md`); PS1 equivalents in brackets. Found from the map table (PS1 bytes searched in
BOOT.BIN), its lookup's callers, and RAM dumps (`tools/pspdbg.py dump`) at the title, scene 0 and scene 18.

## Scenes and maps (verified: warps land, RAM dumps)
- Scene id N = 0-379 (PS1 0-279, same ids for the same scenes); SCEN.DAT entries N (small), N+380 (script + text),
  N+760. Entry N lands at 0x08B94F38, entry N+380 right after it (0x08B95310 for scene 0, 0x08B9556C for scene 18):
  **u32 0x08C8E4A0** (also 0x08C57A94) points at the loaded N+380 entry.
- Save block **0x08C8EAB4** [0x80196A70]: +0x30E u16 loaded scene (0xFFFF none) [+0x2B4], +0x310 second copy
  [+0x2B6], +0x314 / +0x315 map area / sub [+0x2BA / +0x2BB].
- Scene request: u16 **0x08C8D244** and **0x08C8F2E8** [0x80113D62 / 66].
- Map lookup **0x0882BF70(area, sub)** over the table at 0x089253CC (u8 area, u8 sub, u16 MAP.DAT id, 0x713 rows;
  BOOT.BIN file 0x12148C, PS1 0x5BE rows) stores the map id at u16 0x08C8F2B6 [gp+0x4BA]. Area/sub copies at
  0x08C8CE99 / 0x08C8F2EA.
- New Game: title menu result s0 (0x088062AC; 1 = LOAD -> 0x088065C8, 2 -> 0x08806648, 0 = START falls through) ->
  0x088062E4: sub 5 -> save+0x315, -1 -> 0x08C8EE3E, area 2 -> save+0x314, zero both request halfwords
  (0x08806320, 0x08806328 = jal delay slot), map lookup (2, 5). A second (2, 5) site is 0x08809050 (not used).
- Title: no save -> the cursor starts on LOAD; down, up, up = START (`tools/routes/boot.txt`). Title drawn by f600,
  but presses before ~f700 can be dropped. APPENDIX loads clear data through the system dialog ("no save data" without
  one); a clear-save fixture is still to make (phase 8, `credits` ends on the clear-data save prompt).

## Game over (open)
- `kill F` holds hero HP 1 and AT 0 (HUD shows HP 1), but the tutorial battle (dbg 6 -> 0) was still won (Circle
  every 66 frames) or stalled on Tippi's dialogue (Circle stopped); dbg 6 -> 2 / 5 start in the field away from the
  enemy. Next: a battle that starts in contact, or the enemy's record (battle RAM dump work/qa/ram_bt).

## Event VM (verified: breakpoint + jump lands on the tutorial status lesson)
- Script pointer **u32 0x08C8EE6C** [gp+0x428]; the dispatcher at **0x08833B2C** `lbu t0, (s1)` reads the op
  (pointer in s1), stores ptr+1, current op -> 0x08C8F2B8, then `sltiu 0xFF` and a jump table at 0x08915A6C
  (PSP has up to 0xFF ops; PS1 0xD6). Call stack of pointers at 0x08C8F2F8 indexed by byte 0x08C8C910.
- The dispatcher only runs while a script runs: a message waiting for Circle does not reach it. A plain poke of
  0x08C8EE6C between frames is untested (the first try used a wrong base); warp.py's `jump` sets a breakpoint on
  0x08833B2C (tapping Circle until it hits) and sets s1. PS1 `jump 281:0x1A6A` (tutorial status, op 76 area 85 sub 6) = PSP `scene 1 jump 0x20BA`
  (12 bytes of the PS1 script matched in entry 381).

## Units (verified on the field menu: HP 26/26, LV 1, AT 12, DF 7, MV 99)
- Hero unit record 0x08C5888C: +0x19 LV, +0x1A AT, +0x1C DF, +0x38 HP u16, +0x3A max HP, +0x3C MP, +0x3E max MP
  (PS1 has HP at +0x30). Record stride and the other units: not mapped yet (phase 8 stress saves).

## Inventory (session 16, from a RAM dump of the gear_items screen: work/qa/ram_items; save.py --stress)
- u16 item-id lists (-1 = empty), u32 pointers at 0x08958BF8: weapon 0x08CEA15A (112 slots), armor 0x08CEA23A (52),
  accessory 0x08CEA2A2 (48), goods 0x08CEA302 (144), key 0x08CEA422 (356). Counts u16 x5 at 0x08CEA6EA.
- Quantity: byte at 0x08CE9ED0 + 2 * id, ids 0-324 (high byte 0x80 = owned, 0x81 seen on an equipped M2 "E1x7").
- Game id = items.json entry for entries <= 93, else entry + 3 (as PS1). Name-read ranges: weapons 0-109, armor
  110-152, accessories 153-178 + 277-288 (M2 sits in the accessory list), goods 179-245, key 246-276; 289+ = dummies.
- Stress saves: `save.py make work/saves/stress_full --warp st_vac07 --stress --set hero_lv=99 ...` then
  `tools/debug/stressrun.py --sav work/saves/stress_full --out work/qa/stress` (cases items/status/spell/equip/save).

## Money (verified: write breakpoint on the menu's copy, save -> load round trip)
- ELM **u32 0x08C5AD94** (block 0x08C5AD90; New Game zeroes its first 4 bytes at 0x0880632C). The field menu copies it to
  0x08CDF410 for display (0x08879470 -> 0x08865620); poking the copy is lost.

## Saves (tools/debug/save.py, verified: make + check round trip, values shown in the loaded game's field menu)
- One folder `PSP/SAVEDATA/ULJM05423GR_DATA` (DATA.DAT 495376 B, ICON0, PIC1, PARAM.SFO), 15 pages of slots inside.
  DATA.DAT is sceSavedata-encrypted (flat byte histogram, incompressible), so no file editing: save.py pokes RAM and
  saves through the field menu (Triangle -> SYSTEM -> SAVE -> slot 1 -> OK = Up, Circle); the game writes its own
  checksum. `--sav DIR` needs DIR to hold the `ULJM05423GR_DATA` folder (psp.seed_saves keeps the basename).
- Title with a save: cursor on LOAD; Circle, slot 1 Circle, OK = Up, Circle -> field (~f1500).
- `check` boots cold with the save, loads slot 1, asserts a scene is loaded and every `--expect` reads back.

## Ending and credits (warps `ending`, `credits`)
- Scene 11 area 81 sub 0 lands at f872; mashing Circle runs the ending, the staff roll and "fin" (~f28800), then the
  clear-data save prompt. Cast pages (f21000-f23400, shot every 300) draw Japanese character names with romaji under
  them; the staff pages after them are already English. Settle P5 vs P13 there in phase 8.

## Text coverage (phase 8 session 13: tools/strings.py, tools/debug/textlog.py, tools/debug/cover.py)
- Printer entry 0x088748A0: **t3 points at the code pointer** (the printer keeps it in s4: `lw a1,(s4); lhu s0,(a1)`,
  writes it back as it goes), so *t3 = the next code; a call resuming after a wait/page code starts mid-string.
- `build/strings.tsv` (`tools/strings.py`): id -> hash of the build's words (PS1 key: h*31+w up to FFFE/FFFF); no
  cstr pools, no unref. `warp.py --textlog` logs `TEXT <hash>` per distinct string printed (breakpoint, no Lua).
- `cover.py` (host mode, like PS1): warp `newgame`, stage strings in free RAM 0x09A00000, at each printer call that
  is not a staged continuation point *t3 at the next staged string; the VM dispatcher breakpoint sends every op back
  to the message op (LOOP), so mashing Circle walks the whole list (~20 frames a string, a 2000-string chunk ~10 min).
  Voice codes `{v:}` stall (no voice bank in the host): left out of the staged copy. `{FB00}...{FFFA}` (animated
  face, dev-menu strings) and a few others stall: the run ends after STALL frames and the next run starts after it
  (`tools/debug/cover_ids.py` lists them). Proves the printer read every string, not how it looks in its own scene.

## Developers' check menu (scene 18, verified on screen)
Same as PS1 (`ダンジョンマン`, `チェック項目を選んで下さい`), 15 items (the list wraps): 0-11 as PS1 (Luise magic + M2
gear, encounters off, misc, full check = story points, FC check, dungeons, event battles, event quick check, face
graphics, units, parameters, name/territory), then 12 追加コマンドテスト, 13 石原チェック用, 14 ＳＥチェック. Warp with
`scene 18 area 2 sub 1`; `tools/debug/scenes.txt` drives it by menu index.

## Tool (tools/debug/warp.py)
Cold boot; at frame 1 the New Game code is patched in RAM (area/sub immediates, the two zeroing stores NOPed), the
request halfwords are rewritten every 4 frames, Circle picks START, and landing is tested on RAM (save block scene and
area/sub). No disc 2 on PSP: every PS1 disc 2 story point runs from the same boot. Each `--all` entry saves
work/states/<name>.ppst after it lands.
