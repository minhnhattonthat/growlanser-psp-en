Growlanser (PSP) - English translation patch v{VERSION}
======================================================

Unofficial fan translation of Growlanser (PSP, Atlus, 2009; ULJM-05423).
This zip holds only the patch: no game data. You need your own dump of the Japanese UMD (Redump).
Do not share patched ISOs.

What is translated
------------------
Everything the game shows as text: all dialogue (including the PSP-only Darkfall arc, fairy and My Town extras and
the endings), menus, items, spells, skills, help, title screen, chapter and battle cards, status graphics, appendix
rooms and the credits roll. The name-entry keyboard keeps the game's kana and full-width Latin grids (use the Latin
grid for English names). Voice acting stays Japanese.

How to patch
------------
Use xdelta3 (or Delta Patcher, https://github.com/marco-calautti/DeltaPatcher):

    xdelta3 -d -s "Growlanser (Japan).iso" "Growlanser (Japan).xdelta" "Growlanser [EN].iso"

Required file (Redump) and result
---------------------------------
{FILES}
Notes
-----
- Tested in PPSSPP. Start from a cold boot: a savestate made on the Japanese game keeps the old code and font.
  Saves carry over.
- v1.0.1: v1.0 left real hardware less free memory than the original game (black screen on a PS Vita, issue #1);
  the memory layout now matches the original. Still unconfirmed on real PSP / Vita hardware: reports welcome.
- Bugs: https://github.com/minhnhattonthat/growlanser-psp-en/issues (a save or savestate helps).

Credits
-------
Translation, tools and hacking: minhnhattonthat, made with extensive AI assistance (Claude by Anthropic). Script
shared with the PS1 translation (growlanser-en).
Growlanser is (c) Atlus. This project is not affiliated with them.
