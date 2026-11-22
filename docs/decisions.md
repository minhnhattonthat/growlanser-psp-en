# Decisions

The user's rulings on scope, style and trade-offs, newest last. Read before asking the user anything; if a later
decision replaces one, mark the old one "replaced by D<n>" instead of deleting it. Binding term spellings live in
`glossary.md`; this file holds the why.

D1-D9 came pre-answered in the owner's one-shot run brief (Orca coordinator), 2026-11-22.

| # | Date | Question | Options offered | Decision and reason |
|---|---|---|---|---|
| D1 | 2026-11-22 | Honorifics and name order | keep (-san), drop; JP or Western order | Keep honorifics; Western order (given name first). Owner's standing default. |
| D2 | 2026-11-22 | Romanization source for names | official art, earlier patch, Hepburn | Official English names where they exist, else an earlier fan patch, else Hepburn without macrons. G1 PSP has no official English release, so the "earlier patch" is the owner's own PS1 translation (`../growlanser-en`, glossary.md there): its spellings are binding here (D9). |
| D3 | 2026-11-22 | Credits | stay Japanese, translate | English. |
| D4 | 2026-11-22 | Abbreviations | engine work first (default), abbreviate | Engine work first (skill default); abbreviate only as a flagged last resort. |
| D5 | 2026-11-22 | Graphics text left in Japanese | none (default), list | Translate all of it (titles, menus, banners, cards); keep the Japanese logo only if it has no official English version. |
| D6 | 2026-11-22 | Specs and plans | need approval, pre-approved | Pre-approved: keep going through every checkpoint, report at the end. |
| D7 | 2026-11-22 | Existing saves / memory cards | user supplies, none | None provided; build the debug tool as usual. |
| D8 | 2026-11-22 | Publishing | - | Never run `gh release create` or change repo visibility; the run ends at a built, verified release zip. Commit and push to main at each phase end. |
| D9 | 2026-11-22 | Per-game override: reference project | - | The PS1 version's finished translation (`../growlanser-en`) is the reference: reuse its glossary, rulings (its D9-D18 where they apply) and English lines where the PSP Japanese is the same text. New PSP-only text is translated fresh in the same style. |
| D10 | 2026-11-22 | Name-entry keyboard + default names (agent default under D9) | romanize keys / pairs, keep JP | Same as PS1 D14/D17/D18: the key grids boot.sys.0070-0099 and the full-width defaults ＰＬＡＹＥＲ (names/units 0000), ＭＹ ＣＩＴＹ (names/units 0014) stay Japanese (insert.KEEP_JP): one code per key/cell, pairs break input (marker build showed the grid split into pairs). Labels (sys.0069) get English in fixed slices in phase 7. |
| D11 | 2026-11-22 | English engine (agent default under D4/D9) | half-width font, digraph tiles, VWF | Port of the PS1 VWF (asm/vwf.asm: pair codes, font/en12.txt) - same engine, already proven there; typewriter replaced by page-at-once printing as on PS1. |
| D12 | 2026-11-22 | Dialogue box width on the wider PSP screen (agent default under D9, pre-approved run) | keep the engine's 24 cells (288 px), widen the window to ~32 cells | Keep 24 cells: every PSP window measured equals the PS1 one (docs/windows.md), so the PS1 English (28,401 identical lines) fits unchanged and reads the same; widening means a window-size hunt per box for no gain in meaning. Revisit only if PSP-only text cannot fit. |
