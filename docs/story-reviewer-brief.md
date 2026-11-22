# Story reviewer brief - Growlanser (PS1)

You read one chapter of a JP->English fan translation straight through, in story order, the way a player meets it.
Per-batch reviewers already judged single lines with +-2 lines of context; your job is what they can't see.
Read-only: no edits, no git, no subagents. Return the report as your final message; the controller saves it.

## Inputs (paths in your dispatch)
- Chapter file `work/qa/story/chapters/cNN[_P].txt`: every scene line of the chapter part, `>> id | - | JP` then the
  English on the next line. `¶` = page break, `{n}` shown as a space, voice codes removed. Speakers are not stored in
  the script; infer them from context and each scene's name list. Read ALL of it, in passes (Read with offset/limit,
  ~250 lines a pass: a whole-file Read returns a stub), before judging. Some scenes hold several branches or NPC
  variants in a row; don't read alternatives as one sequence.
- `docs/synopsis.md` (plot, who is who, late reveals, scene ids), `docs/style-reference.md` (voice per character),
  `glossary.md` (rulings at the top: honorifics kept, -sama etc.). Read each in parts too.

## Judge, across the whole chapter
- Continuity: each line follows from the one before; setups, callbacks and references back are kept; who knows what
  stays coherent; nothing gives a later reveal away early (synopsis §4).
- Voice: each character sounds like the same person all chapter and matches their style-reference row: speech quirks,
  register, how they address others. Name the line where a voice drifts or goes neutral.
- Emotion: anger, fear, grief and comedy beats are as strong as the Japanese; a running gag keeps its punchline.
- Names and terms match glossary.md exactly; no suffix glued onto a variable ("1th"). A name drawn from a `{s:XXXX}`
  variable never takes an honorific (glossary rule): "-san" dropped after one is the ruling, not a finding.
- Choice lines (`・...`) carry no final period, like the JP.
- Skip system-message wording (Obtained/Received, "is now accompanying", Found a/'Item'): one global polish item.
- Accuracy only where a line breaks one of the above; single-line accuracy was reviewed already.
- Line breaks and box fit are already checked by tools: ignore wrapping.

## Report (keep it compact: one line per finding, no preamble)
### Critical (continuity break, reveal given away, wrong speaker)
### Important (voice drift or flattened, emotional beat lost, setup or callback dropped, joke dead)
### Minor (deferred to the polish pass)
Each: `id - JP gist - problem - suggested EN` (the full replacement English for that id, `{n}`/`¶` not needed).
### Assessment
`ok` (no Critical/Important) | `issue` - one sentence why.
