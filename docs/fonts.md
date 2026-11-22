# Fonts

Every font or glyph sheet the build reads ends up inside the released patch, so its licence must allow that. One row
per file; a font with no known licence doesn't go into a release.

| File | Source (URL, version) | Licence | Redistributable in a patch | Used for | Changes made |
|---|---|---|---|---|---|
| font/en12.txt | drawn for the PS1 project (`../growlanser-en`, 2026-11-18), copied | MIT, same as repo | yes | all English text (VWF, asm/vwf.asm) | - |
| fonts/LiberationSans-Regular.ttf | Liberation Fonts 2.1.5 (`https://github.com/liberationfonts/liberation-fonts`), licence `fonts/OFL-Liberation.txt` | SIL OFL 1.1 | yes: the patch holds rendered pixels only | English cast roles and "Link Sync" in the staff roll (`tools/credits.py`, 15 px) | none |
