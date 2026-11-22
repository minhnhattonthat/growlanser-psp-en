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
