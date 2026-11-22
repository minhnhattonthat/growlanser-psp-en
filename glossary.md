# Glossary - Growlanser (PSP)

Inherited from the PS1 translation (`../growlanser-en/glossary.md`, decision D9): its spellings are binding here.
PSP-only terms get added to each table as they turn up. The font notes below describe the PS1 font; the PSP font
set is decided in phase 5.

Binding for every translator and reviewer. Agents propose additions in reports; only the controller edits this file.
The tables are lint-enforced (`tools/batches.py`): a JP form in the line needs one of the EN forms (`/` separates
alternatives); an Avoid spelling fails.

## Rulings (asked of the user once; options and reasons in docs/decisions.md)
- Honorifics: kept, hyphenated (Tippi-chan, Luise-san). Kinship and role terms are translated, not kept:
  お兄ちゃん "Big Brother" (Luise to the hero; "big bro" never), お母さん "Mother"/"Mom", マスター "Master".
  Name order: Western (given name first).
- Romanisation source: no official English Growlanser I exists (D2): names follow the established fan spellings
  (growlanser.net, fan wiki), else the natural English/European form the katakana spells (リシャール Richard,
  ヴェンツェル Wenzel), else Hepburn without macrons. Recorded as D9.
- Credits: English.
- Register: fantasy-medieval setting, natural modern English. No thee/thou; royalty and knights speak formally,
  soldiers and mercenaries plainly, Tippi cheekily. Sound effects: plain words with asterisks, `*thud*`.
- Abbreviations: full names and terms everywhere, prefer engine changes over shortening.
- The player names the hero; his name is the variable `{s:0000}` (other `{s:XXXX}` are other drawn names). Copy
  every `{s:XXXX}` exactly; a possessive `'s` after it is fine, no other suffix ("1st", "-kun" glued on).

## Style rules
- Punctuation map: 「」 -> "...", 『』 -> '...' (titles, quoted terms), ‥‥ / ・・・ -> ..., ！？ -> ?!, ～ -> drop or
  stretch the word ("Heyyy"), ★ -> drop (no glyph; ♪ and ♥ exist), （…） -> (...).
- Font: ASCII letters and punctuation plus é … — ♪ ♥. No `# @ \ ^ \` { | }` (braces only in control codes).
- Voices: docs/style-reference.md.

## Characters
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| ティピ | Tippi | | homunculus fairy made by Sandra; cheeky, calls the hero アンタ "you" | Tipi |
| ルイセ | Luise | | Sandra's daughter, the hero's adoptive sister; shy, calls him お兄ちゃん | Ruise / Louise |
| サンドラ | Sandra | | Court Magician of Rolandia, the hero's adoptive mother; calm, polite | |
| ウォレス | Wallace | | one-eyed former mercenary captain | |
| アリオスト | Ariost | | half-Featherian researcher who dreams of flight | |
| エリオット | Elliot | | boy who looks exactly like Richard | Eliotte |
| ゼノス | Xenos | | swordsman, Karen's brother | Zenos |
| カレン | Karen | | healer, Xenos's sister | |
| ミーシャ | Misha | | Magic Academy student | |
| ジュリアン | Julian | | Burnstein officer | Jurian |
| ジュリア | Julia | | | |
| アルカディウス | Alcadius | | King of Rolandia | Arcadius |
| レティシア | Leticia | | Princess of Rolandia | |
| アンジェラ | Angela | | Queen Mother of Rolandia | |
| ステラ | Stella | | Featherian queen | |
| オスカー | Oscar | | Imperial Knight; full name Oscar Reeves (オスカー・リーヴス) | |
| リーヴス | Reeves | | | |
| アーネスト | Ernest | | Imperial Knight; full name Ernest Lyell | |
| ライエル | Lyell | | | |
| リシャール | Richard | | Burnstein Imperial Knight master, later king | Richart / Richar |
| ガムラン | Gamlan | | | |
| ベルナード | Bernard | | general | |
| ブロンソン | Bronson | | general | |
| ウェーバー | Weber | | general | |
| ヴェンツェル | Wenzel | | | Venzern / Ventzel |
| シエラ | Sierra | | | |
| ベルガー | Berger | | | |
| ブラッドレー | Bradley | | Magic Academy vice-headmaster | |
| マクスウェル | Maxwell | | Magic Academy headmaster | |
| アイリーン | Irene | | | |
| エレナ | Elena | | | |
| レダ | Leda | | | |
| オズワルド | Oswald | | | |
| ユング | Jung | | | |
| ゲーヴ | Gev | | | |
| ゲヴェル | Gevel | | | |
| グレンガル | Grengal | | | |
| ラルフ | Ralph | | | |
| ニック | Nick | | | |
| ダグラス | Douglas | | | |
| ジーナ | Gina | | | |
| 仮面騎士 | Masked Knight | | | |

## Places
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| ローランディア | Rolandia | | kingdom | |
| バーンシュタイン | Burnstein | | kingdom | Burnshutain |
| ランザック | Ranzak | | kingdom | Ranzack |
| ローザリア | Rosaria | | royal capital of Rolandia (王都ローザリア "the royal capital, Rosaria") | |
| デリス | Delis | | village | |
| ブローニュ | Boulogne | | village | |
| メディス | Medis | | village | |
| ラシェル | Rachelle | | town | |
| グランシル | Grancil | | town | |
| コムスプリングス | Comsprings | | town | |
| ガルアオス | Garuaos | | prison | |
| ヴァルミエ | Valmier | | mining town | |
| クレイン | Crane | | village | |
| シュッツベルグ | Schutzberg | | | |
| ガラシールズ | Galashiels | | | |
| ラージン | Rajin | | fort (ラージン砦 Fort Rajin) | |
| フェザーランド | Featherland | | | |
| オリビエ | Olivier | | lake (オリビエ湖 Lake Olivier) | |
| 魔法学院 | Magic Academy | | | |
| 時空制御塔 | Space-Time Control Tower | | | |

## Items / skills / terms
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| グローシアン | Growsian | | people born under an eclipse with great magic power | Growshian |
| グローシュ | Grosh | | the magic energy Growsians draw on | |
| フェザリアン | Featherian | | winged people | |
| ホムンクルス | homunculus | | (pl. homunculi) | |
| インペリアル・ナイト | Imperial Knight | | Burnstein's elite knights | |
| 宮廷魔術師 | Court Magician | | | |
| 送魔線 | mana line | | lines that carry magic power between towns; 送魔線技師 "mana line engineer" | |
| 闘技大会 | tournament | | | |
| 全周囲攻撃 | Whirlwind Attack | | skill: strikes every adjacent enemy (fits the 96 px skill list) | All-Around Attack |
| 傭兵 | mercenary | | | |
| エルム | Elm | | currency ("75 Elm") | |

## Terms pass before wave 1 (codex proposal from tools/termscan.py, controller-checked 2026-11-18)
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| パワーストーン | Power Stone | | | |
| インペリアル・ナイツ | Imperial Knights | | the order | |
| シャドー・ナイツ | Shadow Knights | | | |
| ナイト・マスター | Knight Master | | | |
| マスタークラス | Master Class | | tournament rank | |
| ビギナークラス | Beginner Class | | | |
| ジュニアクラス | Junior Class | | | |
| ノーマルクラス | Normal Class | | | |
| エキスパート | Expert | | Expert Class rank | |
| エクセレントクラス | Excellent Class | | | |
| グレートクラス | Great Class | | | |
| ヒーロークラス | Hero Class | | | |
| チャンピオンクラス | Champion Class | | | |
| レジェンドクラス | Legend Class | | | |
| フレッシュマン | Freshman | | | |
| コロシアム | Coliseum | | | |
| フリーバトル | Free Battle | | | |
| クリアノ | Kuriano | | herb (クリアノ草 Kuriano Herb) | |
| ブレーム | Brehm | | volcano (ブレーム火山 Brehm Volcano) | Blame |
| アルト | Alto | | | |
| ダンジョンマン | Dungeon Man | | | |
| グレッグ | Greg | | | |
| アイテムショップ・ココ | Coco's Item Shop | | | |
| プロミス・ペンダント | Promise Pendant | | | |
| バーバラ | Barbara | | | |
| ノストリッジ | Nostridge | | | |
| マホガク定食 | Academy Special | | | |
| 魔水晶鉱山～概略～ | The Magic Crystal Mine: An Overview | | book title | |
| 大戦の謎 | Mysteries of the Great War | | book title | |
| 古代遺跡とその出土品 | Ancient Ruins and Their Artifacts | | book title | |
| 水晶鉱山調査隊派遣記録 | Crystal Mine Expedition Dispatch Records | | book title | |
| 迷いの森遺跡調査報告 | Lost Forest Ruins Survey Report | | book title | |
| 聖なる土 | Holy Soil | | | |
| スターロード | Star Road | | | |
| ＬＬＭ魔法教室 | LLM Magic School | | | |
| 地震雲 | earthquake cloud | | | |
| バズロック | Bazrock | | | |
| マジックジャマー | Magic Jammer | | | |
| ニコラ | Nicola | | | |
| プロキンス | Prokins | | | |
| 三国大陸 | Three Kingdoms Continent | | | |
| 回復薬 | healing potion | | | |
| 秘伝書 | Secret Manual | | | |
| マホガク | Academy | | students' slang for the Magic Academy | |
| マーナ | Marna | | | |
| マジックタイム | Magic Time | | | |
| アダル | Adal | | | |
| ハウエル | Howell | | | |
| ワイワイランド | Waiwai Land | | | |
| ワクワクランド | Wakuwaku Land | | | |
| 賢者の石 | Sage's Stone | | item name fits 96 px | Philosopher's Stone |
| フライシェベルグ | Fleischeberg | | | |
| ヘルブリンディ | Helblindi | | | |
| マジックロック | Magic Lock | | | |
| シビレ玉 | Paralysis Orb | | | |
| フレッシュゴーレム | Flesh Golem | | | |
| 魔法の眼 | Magic Eye | | | |
| グローランサー | Growlanser | | | |
| 謎の洞窟探索記 | Exploring the Mysterious Cave | | book title | |
| 透明化薬 | Invisibility Potion | | | |
| 温泉通行許可証 | Spa Pass | | item name fits 96 px | |
| ゼメキス | Zemekis | | | |
| ジョニー・カルテット | Johnny Quartet | | | |
| カラジューム | Caladium | | | |
| ムスカリ | Muscari | | | |
| グローランド | Growland | | | |
| ラファガ | Rafaga | | | |
| エンジェルリング | Angel Ring | | | |

## Terms from translator reports, waves 0-1 (tools/newterms.py, controller-picked 2026-11-18; conflicts: majority or item-table spelling)
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| アルヴィース | Alviss | | legendary great sage | Alvis |
| リーヴェイグ | Liveig | | berserker; his magic sword | Riveig |
| ズフタフ | Dubthach | | | Zufutafu |
| スキマ屋 | Nook Shop | | shop chain | Sukima |
| 南大通り商店街 | South Avenue Shopping District | | | South Main Street |
| バイト店員 | Part-Time Clerk | | | |
| 学食の親父 | Cafeteria Owner | | | Cafeteria Cook |
| 特別研究室フロア | Special Research Labs | | Academy floor B1 (elevator: "B1 Special Research Labs") | |
| 薬剤研究フロア | Pharmaceutical Research | | Academy floor 6F (elevator: "6F Pharmaceutical Research") | |
| 重要図書閲覧室 | Restricted Reading Room | | Academy library | |
| 月の満ち欠けと時空の歪み | Phases of the Moon and Distortions in Space-Time | | book title | Lunar Phases |
| デカゲル | Big Gel | | enemy | Giant Gel |
| 身代わり人形 | Substitute Doll | | | |
| エネルギー供給機 | Energy Supply Unit | | | |
| オスカー・リーヴス | Oscar Reeves | | | |
| オルトロス | Orthros | | | |
| カダーオ | Kadao | | | |
| ギンナル | Ginnar | | | |
| クレスト武器店 | Crest Weapons | | shop | |
| クローディア | Claudia | | | |
| グローシュ波動 | Grosh wave | | | |
| ゲンドゥール島 | Gendul Island | | | |
| ゲヴェル融合体 | Gevel Fusion | | | |
| シャドー・ナイト | Shadow Knight | | | |
| シュテーム山 | Mount Shutem | | | |
| スヴァンニ | Svanni | | | |
| ソフィー | Sophie | | | |
| ダニー・グレイズ | Danny Glaze | | | |
| ノラン | Nolan | | | |
| ニコラ・Ｃ | Nicola C. | | professor | |
| プロキンス・Ａ | Prokins A. | | professor | |
| マクスウェル・Ｊ | Maxwell J. | | professor | |
| ブレーム火山 | Brehm Volcano | | | |
| ラウリン | Laurin | | | |
| ローザリア警備隊 | Rosaria Guard | | | |
| ヴァルタム | Valtam | | | |
| ヴィンダル | Vindar | | | |
| ヴェルダン | Verdan | | | |
| 世界樹 | World Tree | | | |
| 仮面兵士 | Masked Soldier | | | |
| 学院長 | Headmaster | | 副学院長 = Vice Headmaster | |
| 封魔祭 | Demon Sealing Festival | | | |
| 建国祭 / 建国記念祭 | Founding Festival | | | |
| 戦乙女 | Valkyrie | | | |
| 第一近衛騎士団 | First Royal Guard | | | |
| 迷いの森 | Lost Forest | | | |
| 滝の洞窟 / 滝洞窟 | Waterfall Cave | | | |
| 黒ヴェンツェル | Dark Wenzel | | | |
| 魔法技術管理法 | Magical Technology Control Act | | | |
| 肉の城 | Castle of Flesh | | | |
| ＧＬカード | GL Card | | | |

## Terms from translator reports, wave 2 (tools/newterms.py conflicts, controller-picked 2026-11-18: majority or table spelling)
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| グランバス | Granbas | | legendary king of Grancil | Granbus |
| 時空制御装置 | space-time control device | | capitalised only as a heading | space-time control unit, spacetime |
| 歪み率 | distortion level | | | distortion rate |
| 歪み計 | distortion gauge | | | distortion meter |
| 工作兵 | Saboteur | | | Sapper |
| 援軍要請の書簡 | Reinforcement Request Letter | | key item | Call for Troops Letter |
| 反省室 | Reflection Room | | | reflection chamber |
| 集魔柱 | mana collection pillar | | | magic-gathering pillar |
| 眼帯の男 | Eyepatched Man | | speaker tag | Man with Eyepatch |
| 大きなコイン | Large Coin | | | Big Coin |
| マジックタイム停止装置 | Magic Time Stopper | | | |
| 魔導技師 | Magitech Engineer | | names and units tables | Magic Engineer |
| モンスター使い | Monster Tamer | | | monster handler |
- 目 as `{s:0127}` (names-table kanji, renders "Eye"): English drops the code and writes the word (`batches.GLYPH_VARS`).

## PSP-only terms (terms pass 2026-11-22, tools/termscan.py; agent picks under D9, romanisation rule above)
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| メルフィ | Melfie | | PSP-only character (hospitalised, later released; works with Luise against Dunkels) | Melfi / Merfie |
| アメリア | Amelia | | PSP-only, Magic Academy researcher | |
| ジャスティン | Justin | | PSP-only | |
| デュンケルス | Dunkels | | the Darkness entity (闇); German dunkel | Dunkelz |
| ラミィ | Lamie | | PSP bonus fairy chat partner, airy drawn-out speech (～です～), calls the hero ご主人様 "Master" | Lamy / Rami |
| ユリィ | Yurie | | PSP bonus fairy chat partner | Yuri / Yuly |
| コリン | Colin | | PSP bonus fairy chat partner | Corin |
| るいせちゃんのお部屋 | Luise-chan's Room | | door plate in child's hiragana: keep the childish feel | |

## Decisions from earlier batches
- 秘石 (in dialogue) = Power Stone, like パワーストーン; the item 秘石制御装置 stays "Gem Control Unit" (96 px item cap).
- Case-only variants (Magic Crystal / magic crystal, Multipurpose Hall) follow normal English capitalisation: proper
  names and item names capitalised, common nouns in running text lower case.
