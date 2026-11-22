# Visual-QA reviewer brief - Growlanser (PSP, ULJM-05423)

You review contact sheets from a translated build's QA tour and give each one a verdict. Read-only on everything
except your one verdict file: no edits to the repo, no git, no subagents.

## Inputs (in your dispatch)
- A chunk file: one `id<TAB>path` line per sheet. Read every sheet in it; none may be skipped.
- Your verdict file: `work/qa/verdicts/<chunk>.tsv`.
- Optional: the original ISO's sheets (`work/qa/warp/<same warp name>/sheet.png`) and `glossary.md` (read it in parts:
  offset/limit, long reads come back as a stub).

## How to look
- Each sheet is one warp (tools/debug/scenes.txt name = the folder name): a cold boot, the warp, then the route.
  The first tiles are the boot and the title; judge the tiles after the warp landed.
- Read each sheet whole first. Where text is small, zoom into it with
  `python -X utf8 $SKILL/scripts/sheet.py SHEET.png --crop x,y,w,h --zoom 3 --out <scratch>.png` and read that
  (`$SKILL` = output of `python tools/skill.py`). Single frames are the `fNNNNNN.png` files beside the sheet.
- When something looks wrong, open the same id from `work/qa/warp/` (`sheet.py EN.png --compare JP.png`). If the
  original shows the same thing, it is the game's own behaviour: `ok`, with a note.
- Zoom into every Yes/No prompt, selection box, menu row and speech bubble: a few pixels of misalignment don't show
  at sheet scale. To measure one: `python -X utf8 $SKILL/scripts/inkbox.py SHOT.png x,y,w,h`.

## Judge
An `issue` is any of:
- Japanese still visible (except the rows listed below);
- text overflowing a box, clipped by a frame, or running off screen;
- text off-centre where the original centres it: an option in its selection box or cursor brackets, a label, a bubble;
- garbage tiles, wrong or missing glyphs, a strike or stray pixels across letters;
- broken line breaks: a word split mid-line, a page ending mid-sentence, a one-word last line;
- an empty box where text belongs;
- a name that differs from `glossary.md`.

Standing non-bugs, `ok` (the controller adds the game's own below):
- text still typing out, a box mid-fade or mid-scroll, a cursor caught mid-blink;
- a popup or caption box mid-open: the box and its text are scaled narrower, so a texel column drops out of a
  letter ("morth" for "month", "Dels'lage" for "Delis Village"); compare the box width with a later frame;
- a map or scene still loading after a warp;
- anything identical in the original's sheet.
- Japanese drawn as graphics that docs/re/graphics.md lists as P1-P13 (title, status pictures, credits, kana
  keyboard, face plates, 仮 stamp...): tracked there for the graphics step, not a tour issue. Note them anyway.
- The keyboard grids and default names stay Japanese (decision D10).
- The developers' check menu (scene 18, warps named dbg*, st_*, ev_*, bt_*, dg_*) lists entries in Japanese only
  where the script keeps them (insert.KEEP_JP): note them, `ok`.
- The name entry keyboard uses full-width letters (12 px each): known, `ok`.
- Text prints a page at a time (no typewriter): by design.

## Verdicts
Write your verdict file once you have read every sheet, one line per id in the chunk:
`id<TAB>ok|issue<TAB>what and where` (for an issue: which tile, which text, what is wrong).
Then return a short summary: counts, and the issues one per line.
