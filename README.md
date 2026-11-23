# Growlanser English translation

Unofficial English fan translation of **Growlanser** (PSP, Atlus, 2009): the source text and tools
that build the patch.

**Just want to play?** Download the patch from [Releases](../../releases) and follow its README. This repository holds
no game data you can play; you need your own dump of the Japanese game.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate
helps most.

## Translation status

| Part | Status |
|---|---|
| Dialogue / story (every scene, PSP-only Darkfall arc, endings, fairy and My Town extras) | Translated |
| Menus, items, spells, skills, help, system messages | Translated |
| Title screen, chapter and battle cards, status graphics, appendix rooms, credits roll | Translated |
| Name entry | Keyboard keeps the game's kana and full-width Latin grids (each key is one character code); use the Latin grid for English names |
| Voice acting, songs | Japanese audio (not subtitled beyond the text boxes the game already shows) |

Known issues: tested in PPSSPP only; the re-signed EBOOT is untested on real hardware. See [Issues](../../issues).

## What's here

| Path | What it is |
|---|---|
| `script/` | Every text block: original Japanese and English. Translation fixes go here. |
| `glossary.md` | Binding names, terms and style rules. |
| `tools/` | Python build chain: extract, insert, lint, release. |
| `tests/` | pytest suite (ROM-dependent tests skip when the ROM is absent). |
| `docs/re/` | Reverse-engineering notes. |
| `docs/decisions.md`, `docs/status.md` | Rulings with their reasons; current progress and open bugs. |
| `docs/fonts.md` | Fonts used and their licences. |
| `AGENTS.md` | Instructions for coding agents (`CLAUDE.md` points to it). |
| `.codex/agents/`, `.opencode/agents/` | Subagent types (translator, reviewer, visual QA, playtester, graphics) for Codex and opencode; Claude Code gets them from the plugin. |

## Build your own patched ROM

Needs Python 3.12+ and your own dump of the Japanese game.

```sh
git clone https://github.com/minhnhattonthat/growlanser-psp-en
cd growlanser-psp-en
# copy your dump to: rom/Growlanser (Japan).iso
#   (1293516800 bytes, SHA-1 db0c5dffe259ccb032e70f401c599d67189eaead; the build refuses any other dump, see rom.sha1)
python -X utf8 build.py                                # -> build/growlanser_en.iso
python -X utf8 tools/check.py                          # tests + text lint
```

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

## Licence

Tools and English translation: MIT. The original Japanese text in `script/` is Atlus's and is included only so
the translation can be checked against it. Growlanser is (c) Atlus; this project is not affiliated with them.
Do not share patched ROMs.

The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.
