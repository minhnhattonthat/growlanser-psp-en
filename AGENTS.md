# Growlanser (PSP, Atlus 2009, ULJM-05423) English translation

Skill: translate-retro-game (Claude Code: plugin, enabled in .claude/settings.json; other agents: `~/.claude/plugins/marketplaces/retro-translation/skills/translate-retro-game/SKILL.md`; `$SKILL` = that directory, `python tools/skill.py` prints it). Read it before ROM, text or QA work.
Reference: the finished PS1 translation of the same game at `../growlanser-en` (same SCEN/MSYS/MAP.DAT family, glossary, script/*.json with jp+en). Reuse its names, terms and lines where the Japanese matches.

## Commands (run from repo root)
- Build:    `python -X utf8 build.py` -> build/growlanser_en.iso (checks the dump against `rom.sha1` first); `--identity` = repack with no edits, exit 1 unless SHA-1 = rom.sha1 (notes `docs/re/build.md`)
- Check:    `python -X utf8 tools/check.py` (tests + lint; the pre-commit hook runs this)
- Smoke:    `python -X utf8 $SKILL/scripts/emu.py build/growlanser_en.iso --out work/qa/smoke --route tools/routes/boot.txt --smoke --sheet` (original: `"rom/Growlanser (Japan).iso"`; boot.txt reaches the first dialogue box, ~2000 frames, 17 s)
- Warp:     `python -X utf8 tools/debug/warp.py --scene <name> --out work/qa/warp` (scenes: `tools/debug/scenes.txt`; `--all` regenerates every entry + `work/states/<name>.ppst`; PPSSPP has no Lua: RAM pokes over the WebSocket via `$SKILL/scripts/psp.py`; never ask the user to play to a scene; notes `docs/re/debug.md`)
- Saves:    `python -X utf8 tools/debug/save.py make work/saves/<name> --warp <scene> --set money=N` / `save.py check work/saves/<name> --expect ...` (saves are encrypted: edits go through RAM and an in-game save; use with `--sav work/saves/<name>`)
- Release:  `python -X utf8 tools/release.py` (xdelta3 -B + verify; never publish without the user) (phase 9)
- Clean:    `python -X utf8 tools/clean.py`

## Paths
- Original ISO: `rom/Growlanser (Japan).iso` (gitignored; SHA-1 in `rom.sha1`, checked by `tools/check_rom.py`).
- Emulators: QA uses PPSSPPHeadless (QA fork, one per machine in `%LOCALAPPDATA%\translate-retro-game\ppsspp-headless\`, `fetch_emu.py ppsspp-headless`); `tools/ppsspp/` = stock PPSSPP v1.20.4 windowed (github.com/hrydgard/ppsspp/releases/tag/v1.20.4; gitignored) for people and the EBOOT dump. Savestates: `work/states/`.
- ISO tools: `tools/iso9660.py` (list/extract/patch in place). Unpacked files: `work/iso/`.
- Text: `script/` (format TBD in phase 4). Tables: `tbl/`. Glossary: `glossary.md`. RE notes index: `docs/re/README.md`. Fonts and their licences: `docs/fonts.md`.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- Subagents: dispatch the agent types (translator, reviewer, visual-qa, playtester, graphics) shipped by the plugin as `translate-retro-game:<type>` (Claude Code), `.codex/agents/` (Codex) or `.opencode/agents/` (opencode), never general-purpose.
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md`.
- Hooks: `git config core.hooksPath tools/hooks` once per clone.
- PSP buttons: circle = OK, cross = cancel. EBOOT.BIN is encrypted: patch the PPSSPP-dumped ELF, then re-sign (never ship the plain ELF).

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.
