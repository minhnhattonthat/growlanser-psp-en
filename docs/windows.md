# Window data (width gate, phase 5)

Budgets for the fit lint (`tools/fit.py`, `BUDGETS`; test `tests/test_fit.py`) and the translators. Measured = read
off a zoomed shot of a ruler line (`tools/stress.py` + `build.py --mode marker --qa-file F --out X`, every ruler
character 6 px; the other strings of a ruler's pool shrink to their id so it fits in place); lower bound = the
pool's longest JP string shows in that field, so it is at least that wide; guess = not measured yet (the lint warns,
test_fit fails on warnings too). Font: `font/en12.txt` (VWF, pairs, advance = width + 1). Screen 480x272; the
printer's cell is 12 px, as on PS1.

**Every variant measured so far matches the PS1 budgets** (`../growlanser-en/docs/windows.md`): the PSP printer is a
recompile with the same window sizes, so PS1 English fits as is (D12).

**Engine rule (verified, docs/re/text.md):** the printer auto-wraps when its column s6 = ceil(x / 12) reaches the
window width W before a code is drawn, so a line fits a W-cell window when every code (a letter pair) starts at
x <= 12 * (W - 1). After a wait code the pen continues (vwf.asm CONT_RA1 = 0x0886AAB4, the message display's only
print-wrapper call; without it a 6 px gap) and the same start rule holds, with pairs re-aligned at the wait
(work/qa/s3c/wait: 25 chars, wait, wrap after 47). The lint treats any auto-wrap as an error (wrap by hand with {n}).

| Variant | Pools / ids | Budget per line | Lines per page | Status | Proof |
|---|---|---|---|---|---|
| Dialogue box | scen messages (term end) | 24 cells: every pair starts at x <= 276, total <= 288 px; text at x 92 | 3 | measured | work/qa/s2r (scen000.0186 ruler wraps after 48 chars; 3 lines, page dot right of line 3) |
| Dialogue with portrait | scen | same box (the portrait stands over the right side, above the box) | 3 | measured | work/qa/s4/ev_battle001 f003900 |
| Script menu / choice window | scen018 menu lines, choice lines after "・" | 24 cells after the bullet column | 6 rows visible | measured | work/qa/s3/dbgmenu (scen018.0002-0005 rulers: prompt 2 lines + 2 choices, each wraps after 48) |
| Name tag | scene speaker names (term null), boot.names | 144 px (12 cells) visible; frame = 12 px x code count, longer text wraps inside the 12-cell canvas and shows garbled | 1 | measured | work/qa/s2r (scen000.0003 24-char ruler whole, 0004 36-char garbled), work/qa/s4/ev_battle001 final (boot.names.0084) |
| Help box (bottom of menus) | boot.help | 24 cells (288 px) | 3 | measured | work/qa/s3/title_config (boot.help.0021 5-line ruler: wraps after 48, 3 lines shown) |
| Descriptions | msys.items / magic / skills | 24 cells, same help box (Square in the item list) | 3 | measured | work/qa/s3/help_square (msys.items.0030 4-line ruler: wraps after 48, 3 shown) |
| Item names (item list, equip / status slots) | boot.items | 8 cells (96 px) | 1 | measured | work/qa/s3/gear_items (boot.items.0030 / 0196 wrap after "A234567890B23456" = 16 chars) |
| Spell names | boot.magic | 8 cells | 1 | lower bound | JP max 8 cells; spell list empty in the warps (Luise not in the party: gear_spell) |
| Skill names | boot.skills | 8 cells | 1 | lower bound | JP max 8 cells |
| Class names | boot.classes | 11 cells | 1 | lower bound | JP max 11 cells; not seen yet |
| Unit names | boot.units | 144 px clip | 1 | lower bound | JP max 12 cells; battle UI not reached yet (bt_tutorial lands before the battle starts) |
| Config labels | boot.sys.0121 (one label per line) | 8 cells (96 px) | 9 lines (7 rows visible, scrolls) | measured | work/qa/s3/title_config (each label wraps after 16 chars) |
| Config values | boot.sys.0122-0133 | 8 cells (96 px) | 1 | measured | work/qa/s3/title_config (values wrap after 16 chars) |
| Field-menu bubble | boot.sys.0062-0067 | 12 cells (144 px); frame = 12 px x code count (PS1 popup_width hook: phase 7) | 1 | measured | work/qa/s3/menu (sys.0062 ruler: 24 chars, then clipped) |
| Place names | boot.places, scene place / event titles | 12 cells, same popup routine as the bubble | 1 | measured (bubble) | the PS1 place popup and field-menu bubble share the routine; a place popup itself not shot yet |
| Scene caption | scen "　text　" (scen010.0114, scen014.0003) | frame 12 px x code count; centring = PS1 Encoder.centre (phase 7) | 1 | guess | not reached by a warp yet (ev_battle001 runs past scen014's start) |
| Name-entry labels | boot.sys.0069 | one line cut into slices: title 60 px, blank 12, 5 labels x 24 px (PS1 insert.SLOTS) | 1 | measured | work/qa/s4/name_entry (ruler: "A234567890" title, "3456" "7890" "C234" "5678" "90D2" labels) |
| Growth graph | boot.sys.0102 caption, 0103 legend | caption 24 cells x 3; legend 4 cells per label, 7 lines | 3 / 7 | lower bound | as PS1; screen not reached |
| Other system text | boot.sys (rest) | 24 cells (guess) | 3 | guess | battle messages, shop, inn: phase 8 tour |
| Save-utility messages | boot.save | PSP system dialog (system font, not the VWF) | - | n/a | phase 8 (copy the English save-library strings, docs/re/text.md) |
| Double-size text | glyph call 0x08874CE0 | ? | ? | never seen on screen | vwf_big handles it |

Glyph torture line (every ASCII glyph the font has, é … — ♪ ♥, single/double/triple spaces, WWWWMMMM, iiiill) in the
dialogue box: work/qa/s4/tort, all legible, spaces distinct. The font has no `# @ \ ^ \` |`, and `{ }` are control
syntax: EnCodec rejects them.

Phase 7 (fitting, ports from the PS1 insert.py): name-tag pad (frame = code count: Encoder.tag_pad), popup width
(frame = VWF pixel width: PS1 asm popup_width; find the PSP twin of 0x8006BA48), caption centring, name-entry SLOTS.
