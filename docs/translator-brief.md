# Translator brief - Growlanser (PSP, Atlus 2009)

You translate part of the Japanese script of Growlanser (the 2009 PSP remake of the 1999 PS1 game) into English for a
fan patch. A finished PS1 fan translation exists: every PSP line whose Japanese equals a PS1 line already carries
that English, so your batches hold the PSP-only lines (new scenes, events, reworded lines). Tactical fantasy RPG with a
visual-novel story: a 17-year-old foundling (named by the player, `{s:0000}`), raised by the Court Magician Sandra
with her daughter Luise and the fairy Tippi, leaves the royal capital and is drawn into a war between kingdoms and
an ancient threat. Tone: earnest fantasy drama with comic banter (mostly Tippi).

## Read first
1. `docs/style-reference.md` - character voices and approved example pairs. Match this voice.
2. The batch's term list (`build/terms_<batch>.txt`): binding glossary rows, translated game-table names
   (reference), and the cast (speaker names) of each scene in the batch. Full table: `glossary.md`.
3. `docs/synopsis.md` - plot and late reveals. Don't give a reveal away early. Section 6 covers the PSP-only scenes.
4. The term list's `## PS1 reference` part: for a batch line, `near <id>` is the most similar PS1 line with its
   approved English (a reworded line): reuse its wording wherever the Japanese is unchanged and change only what
   differs. `ctx <id>` lines are the already-translated neighbours of a run of batch lines: continue them in voice
   and wording.
5. `build/svars.txt`: what each `{s:XXXX}` draws (`{s:XXXX}<TAB>JP<TAB>English`); grep it for the codes in a line.
6. For a PSP-only scene with little context, read its `script/scen/sNNN.json` (the id's `scenNNN` part): every line
   in order, with `en` where it is already translated.

Read every file in parts (offset/limit, ~150 lines a call): whole-file reads above ~4 KB come back as a stub.

## Input: `work/tl/<batch>.tsv`
`id<TAB>speaker<TAB>form<TAB>limit<TAB>Japanese`. form: dlg (dialogue box), choice (a choice line, starts with ・),
name (speaker/character name tag), desc (help or item/spell description box), menu (short menu/system string).
Speaker is not known per line: use the scene cast, the voice and the neighbours to tell who talks. ` / ` in the JP
is a JP line break (ignore it; English is re-wrapped). Lines are in script order: use neighbours for context; some
lines are fragments of one sentence split by effects - make the pieces read in sequence.

## Output: `work/tl/<batch>.out.tsv`
`id<TAB>English`, every input id exactly once, same order. Plain text: straight quotes, `...`, `--`; no tabs inside
the English, no Japanese or fullwidth characters, no `\uXXXX`, no `\n`. The font also has é … — ♪ ♥, nothing else
outside ASCII, and none of `# @ \ ^ \` | ~` or braces outside control codes.

## Control codes `{...}`
Copy every code except `{n}` exactly, the same number of times: `{v:XXXX}` voice clip, `{s:XXXX}` a drawn name,
`{FCxx}` portrait change, `{FBxx}`, `{FExx}` timing pauses, `{FFxx}` colour/effects (`{FFEF}`..`{FFF1}` wraps a
highlighted term: keep the highlight on the English term). Exception: `{s:012A}` 目 (eye), `{s:012E}` 爪 (nail) and `{s:0047}` 教授 (学院{s:0047}会 = faculty council) are kanji, not a
name: drop it and write the English word. Keep each code at the same point of the utterance:
voice clips and portrait codes at the start of the beat they voice. `{p}` = new page: keep the JP's page breaks
(the wrapper adds more if a page runs long). `{n}` = forced line break: drop the JP ones; add one only for a
deliberate layout (list, poem). Exception: in menu and name strings (form menu/name) the JP shows its `{n}` and
each one separates rows of a list: keep every `{n}` there, one row per JP row. Length: dialogue is wrapped automatically, 3 lines (~46 chars each) a page; names,
menus and choices are one line with the limit in the batch (choices ~40 chars after the bullet).

## Validate
Run `python -X utf8 tools/batches.py check <batch>` from the repo root and fix every reported id until it prints OK.
`python -X utf8 tools/batches.py wrap ID "English"` shows the layout of one line.

## Style
- Faithful: keep the information and order of ideas; adapt idiom, not meaning. Don't add details the Japanese
  doesn't state; don't summarise or skip. Adapt wordplay so the joke still lands (no translator notes).
- Keep the speaker audible (style reference). Old men's じゃ/のう/わし, rough men's ぜ/ねぇ/やがる, feminine
  かしら/わよ/のね, Tippi's brattiness, royal formality must turn into English devices, never neutral prose.
- Names and terms exactly as in the glossary. Never abbreviate. If a line can't fit its limit without losing
  meaning, keep the meaning and report it as `LONG: id`.
- Honorifics kept after names (Tippi-chan, Luise-san); お兄ちゃん "Big Brother", お母さん "Mother", マスター "Master".
- Punctuation: 「」 -> "...", 『』 -> '...', ‥‥ -> ..., ！？ -> ?!, ★ -> drop, ～ -> drop or stretch the word.
- No suffix glued to a name variable except a possessive 's; no a/an right before `{s:XXXX}`. Honorifics after a
  name variable are dropped (`{s:0001}ちゃん` -> `{s:0001}`; the PS1 lines do the same).
- Some `{s:XXXX}` draw common nouns from the names table ({s:005C} Soldier, {s:00AE} Citizen, {s:003C} Patient): they
  render capitalised and can't take a plural "s" - build the sentence around the word as it is.
- Notes from earlier batches: boot.save strings show a raw line break as `{lf}`: keep one per JP `{lf}`. In names
  tables, use the item/skill names already in build/terms_<batch>.txt; terms the glossary lacks: report them.

## Consistency
Never edit `glossary.md`. For a recurring name or term not in it, pick a form, use it consistently, and report it.

## Report
Files written and entry count; then any lines: `NEW TERM: jp -> en`, `UNSURE: id - note`, `LONG: id - note`.
