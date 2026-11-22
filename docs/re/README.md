# Reverse-engineering notes

One file per subsystem. Mark every finding with how far it is proven: **verified** (and how) or **guess** (and why).
Addresses are for the dump in `rom.sha1` (BOOT.BIN file offsets unless a note says RAM or vaddr).
The PS1 version's notes (`../growlanser-en/docs/re/`) describe the same engine and are a good first guess.

| File | Covers | State |
|---|---|---|
| text.md | disc layout, module layout/relocation, encoding, font, SCEN/MSYS sections, module string tables and getters, SJIS/UTF-8 system strings | verified except MSYS loader and MAP.DAT text (guess) |
| debug.md | scene warp (save block, scene request, New Game patch), event VM + jump, hero record, money, saves, check menu | verified except game over (open) |
| graphics.md | graphics-text survey (Japanese drawn as images) | static sweep in progress: DATA.DAT and MSYS.DAT done; MAP.DAT, GLB.DAT, PNGs, movies to do |
