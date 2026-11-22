# Style reference - Growlanser

Voices and approved example pairs. Every translator and reviewer matches these. A line any speaker could have said
is a mistake: carry the JP markers into English devices.

## Voices
| Character | JP markers | English devices |
|---|---|---|
| Tippi (fairy, homunculus) | アタシ, アンタ, コイツ, ～っ, ぅ stretches, ★/♪, むか～っ, キック threats | cheeky, bratty, fast: "Hmph!", "Hey, you!", "Ugh, this guy!", stretched words ("Meanyyy"), exclamation-heavy; calls the hero "you" / "this guy"; calls Sandra "Master" |
| Luise (sister) | わたし, お兄ちゃん, ～ね, ～よね？, gentle ‥‥ | shy, sweet, a little hesitant: "Um...", "...right, Big Brother?"; never rude |
| Sandra (mother, Court Magician) | 私, です/ます, ～なさい, formal | calm, measured, motherly but formal; full sentences, no contractions in serious lines |
| Wallace (ex-mercenary) | 俺, ～だ, ～ぜ, terse | gruff, laconic veteran: short sentences, dry humour, "kid" |
| Kings, queens, Imperial Knights | 余 / わたくし, ～である, ～したまえ | formal, courtly ("We", "Very well", "You have our thanks"), no slang |
| Soldiers, thugs, bandits | 俺, ～ぜ, ～だろ, ～しやがって, ねぇ | rough: contractions, "ain't", "ya", "damn", clipped grammar |
| Old men | わし, ～じゃ, ～のう | "eh?", "my boy", "back in my day", slow cadence |
| Feminine speech | ～わ, ～かしら, ～のよ | "I wonder...", "you know", "dear"; soft, not camp |

## Example pairs (scene 0, approved pilot)
| id | JP | EN |
|---|---|---|
| scen000.0007 | こっちだよ、お兄ちゃん！ | Over here, Big Brother! |
| scen000.0013 | {v:0017}それより、マスター。{n}そろそろアタシのこと紹介して欲しいんだけど。 | {v:0017}More importantly, Master, isn't it about time you introduced me? |
| scen000.0015 | {v:001B}ティピだよ★{n}よろしくぅ♪{p}{v:0062}それで、アンタの名前はなんていうの？ | {v:001B}I'm Tippi! Nice to meet ya♪{p}{v:0062}So, what's YOUR name? |
| scen000.0016 | {v:0063}言いにくい名前ねぇ‥‥。 | {v:0063}What a mouthful of a name... |
| scen000.0022 | {v:001F}なに、コイツ！{n}感じ悪～い！ | {v:001F}What's with this guy?! How ruuude! |
| scen000.0025 | {FB00}{v:0020}あはは‥‥。 | {FB00}{v:0020}Ahaha... |
| scen000.0026 | {v:0021}ティピって妖精の格好してて、かわいいよね？{n}お兄ちゃん？ | {v:0021}Tippi looks like a fairy. She's cute, isn't she, Big Brother? |
| scen000.0032 | {v:0025}何だとぉ！{n}またキックして欲しいの？ | {v:0025}Whaaat?! You want another kick?! |
| scen000.0036 | {v:002A}甘えてはいけませんよ。{n}実の子供だからこそ、手加減せずに指導しますからね。 | {v:002A}Don't get too comfortable. Precisely because you are my own child, I will not go easy on you. |
| scen000.0037 | ‥‥{v:002B}はぁい‥‥。 | ...{v:002B}Yes, Mother... |
| scen000.0047 | 　{n}　７５エルムを受け取った！ | Received 75 Elm! |
| scen000.0058 | {v:0009}ごめんなさい、マスター！{n}調子に乗りすぎましたぁ！ | {v:0009}I'm sorry, Master! I got carried awaaay! |

Corrected example (flattened voice, rejected): scen000.0022 "Who is this person? He seems unpleasant." - accurate
but Tippi never sounds like that; use the line above.

## Layout
- Write each entry as running English; the wrapper (`tools/batches.py`) breaks lines by pixel width and splits
  dialogue pages every 3 lines. Keep the JP `{p}` page breaks where a new beat or voice clip starts (each `{v:XXXX}`
  starts its own page or line, as in the JP). Add `{n}` only for a deliberate break (a list, a poem, a pause).
- Choices: one short line after the bullet: `・Ignore Tippi`. ~40 characters at most.
- System messages ("Received 75 Elm!") drop the JP indent spaces.
