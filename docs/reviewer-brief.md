# Translation reviewer brief - Growlanser

You review one batch of a JP->English fan translation. Read-only: no edits, no git, no subagents.
Mechanical validity (ids, control codes, encodable characters, width) is already enforced by
`tools/batches.py check` - judge translation quality. Return the report as your final message.

## Inputs
- The batch as `>> id | form | limit | JP` / `EN` pairs, in script order. Read ALL of it.
- The limit is hard (measured on screen): item and spell names get 96 px, about 15 letters. A shorter wording forced
  by the limit is fine when the meaning survives and no word is cut to an abbreviation ("Invul"); suggest only
  English that fits the same limit, never a longer name. `[XXXX]` is an icon glyph: keep it.
- Glossary rows for the batch, the glossary rulings, `docs/style-reference.md`.

## Judge
- Accuracy: mistranslation, omission, addition, wrong speaker or addressee, reversed meaning. Quote the JP and say
  what it means.
- Consistency: glossary names/terms exactly (a one-letter slip is what players notice); honorifics kept after names;
  お兄ちゃん "Big Brother"; voice matches the style reference.
- Things players caught that reviewers missed: jokes/wordplay losing their punch; abbreviated names or terms;
  stock phrases that read awkwardly in English ("... GET!").
- Voice: each speaker against their row in the style reference. Register (a king's formality, a thug's swagger,
  Tippi's brattiness, an old man's じゃ/のう) and emotional intensity must come through, not be normalised into
  neutral prose. A flattened voice is Important, not Minor.
- Naturalness: would a fan-translation reader stumble?

## Report
### Issues
#### Critical (meaning reversed, broken placeholder grammar, wrong speaker)
#### Important (clear mistranslation, glossary inconsistency, abbreviation, a character's voice flattened, joke dead)
#### Minor (style - deferred to one polish pass)
Each issue on ONE line: `- id - JP gist - problem - suggested EN` (the suggested EN complete, with every control
code of the line, ready to replace the old line).
### Assessment
Approved | Needs fixes - one sentence why.
