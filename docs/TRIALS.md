# IAnalyze, the trials of the LLMs

Version française : [TRIALS.fr.md](TRIALS.fr.md)

The advice of the README, section [Choosing an LLM](../README.md#4-choosing-an-llm), rests on these trials. Each one sent the same game to several LLMs, with the zip and the full prompt, or with the short prompt of `--prompt-only`.

## Contents

- [How the trials were run](#how-the-trials-were-run)
- [20 November 2026, with the zip and the prompt](#20-november-2026-with-the-zip-and-the-prompt)
- [21 November 2026, with `--prompt-seul`, now `--prompt-only`](#21-november-2026-with---prompt-seul-now---prompt-only)
- [25 November 2026, with the zip and the English prompt](#25-november-2026-with-the-zip-and-the-english-prompt)
- [26 November 2026, the two routes, with the English prompts](#26-november-2026-the-two-routes-with-the-english-prompts)
- [27 November 2026, the two routes, with the prompts as released](#27-november-2026-the-two-routes-with-the-prompts-as-released)

---

## How the trials were run

Four series and a trial on its own, a single trial per LLM, per plan and per route, one game each time.

The first two series of trials were run with version 4.0, whose prompts were in French. The English prompts of version 5.0.0 went through a trial of their own, then a third series, on 25 and 26 November 2026, and a fourth with the prompts as released, on 27 November 2026, which point the same way.

**This is not a benchmark.**\
A single trial says nothing about the consistency of a model. But the series point the same way, and the advice of the README rests on nothing else than what was seen.

**The other LLMs were only tried on their free plans.**\
ChatGPT, Gemini and Copilot were never tried on a paid plan. Their paid models may well be more precise, as Claude was on its subscription on 21 and 27 November 2026, but these trials cannot say so.

**How each answer is judged.**\
Each PGN returned goes through `verify-analysis.py`, against the working folder of its collection. Its stories are then checked on the board, one by one, with python-chess: only facts count, captures, checks, attacks, defenses, material, squares, clocks, figures of the database, never opinions. The errors quoted in the tables were rechecked this way. **The lists are not exhaustive.**

**What all the answers share.**\
The fourteen answers of the short prompt, over three series, quote no evaluation that the table does not hold. Thirteen returned the whole game, every move commented; on 27 November 2026, Gemini changed a move and commented on 39 plies out of 49.

## 20 November 2026, with the zip and the prompt

A game of 49 plies, the same zip and the same prompt for all, the one of version 4.0.0, before the instructions and the option `--prompt-seul`, now `--prompt-only`, that these trials led to add.

| LLM, as it names itself | Plan | PGN returned | Report of `verify-analysis.py` |
|---|---|---|---|
| Claude Opus 5.5 (Anthropic) | subscription | yes, built with python-chess | no failure: 24 mistakes and blunders commented on out of 24, 27 playable variations |
| GPT-6 (OpenAI) | free | yes, written by hand, python-chess could not be installed | 3 failures: a blank line stops the reading, the 25 variations are inside the comments, a NAG contradicts the engine |
| M365 Copilot (Microsoft) | free | yes, the game without any comment | 3 failures: it says it found only three files in the archive, and comments on nothing |
| Gemini (Google), version not noted | free | no | it announces a file that does not exist, then loses the thread of the conversation |

What this series shows:

- **The data holds everywhere.** None of the four invented an evaluation, and all give the same three main errors, with the right losses.
- **Building the PGN is what separates them.** Only the LLM that built its file with python-chess returned a PGN usable as it is.
- **The substance can be good under a faulty form.** The 25 variations written by hand by GPT-6 were all legal and drawn from the lines of the engine.
- **The game was recorded as won in a lost position.** Two LLMs out of four told the story of a deserved win, hence the line added to the summary (see [TECHNICAL.md](TECHNICAL.md), section 10).

The free plan of Claude also announces file creation and code execution, on other models than the one of this trial, according to [its pricing page](https://claude.com/pricing), read on 20 November 2026 and again on 25 November 2026.

It was tried with the zip file on 27 November 2026, below.

## 21 November 2026, with `--prompt-seul`, now `--prompt-only`

A game of 39 plies, won by the player, and the same short prompt pasted alone into five conversations. It is `example-games/game-lichess-org.pgn`.\
The table of the engine marks ten weak moves in it, two of them by the player.

The five answers share the essentials:

- The main line is copied without a single move changed
- The 39 plies are commented on, all the mistakes and blunders of the table included
- 126 evaluations are quoted in the PGNs, all taken from the table

What separates them:

| LLM | Plan | Form of the PGN | On the board |
|---|---|---|---|
| Claude Sonnet 5.5 (Anthropic) | subscription | compliant: code block, tags intact, 10 playable continuations out of 10 | no error found |
| Claude Sonnet 5.5 (Anthropic), effort Max | free | compliant, likewise | one error: an escape square announced for the king while it is attacked |
| ChatGPT (OpenAI), version not noted | free | the continuations are written inside the comments, none is playable. Ten suffixes `?!` or `??` added to the moves, five HTML tags in the comments | a sacrifice that is not one, the wrong knight named on a capture, a mate in one announced for a mate in two |
| Gemini (Google), version not noted | free | 7 playable continuations out of 10. It speaks of the player in the third person, then writes twice "erreur de ma part", my mistake, in their place | the same false sacrifice, the color of the bishops swapped on three moves, a file announced as open that is not |
| Copilot (Microsoft), version not noted | free | no code block: the Site tag is returned as an HTML link. 10 playable continuations out of 10 | the same false sacrifice, and a hanging knight that nothing points out |

The errors of the last column were checked one by one on the position, with python-chess. **The list is not exhaustive.**

What this series shows:

- **The short prompt does the job.** Without an attachment and without code execution, the five answers are readable and their figures are right. This is better than what the whole chain had given the day before with the three other LLMs.
- **Claude is ahead on both plans.** Its two PGNs are compliant, and its explanations are the ones that best resist the check: no error found on one side, a single one on the other. The free account almost matches the subscription, twice as long: 1968 words of comments against 943.
- **The same trap caught three LLMs out of four.** A bishop takes a pawn on h7 with check, defended by its queen: the king cannot take it back. ChatGPT, Gemini and Copilot speak of a sacrifice. Claude writes, in the trial of the free account, "ici il n'y a aucun sacrifice, le pion tombe gratuitement": there is no sacrifice here, the pawn falls for free. The trials were run in French.
- **Asking for three errors makes one up.** The player had made only two. ChatGPT, Gemini and Copilot presented a third one, Claude answered both times that there were only two. Both prompts now give the real number of weak moves of the player (see [TECHNICAL.md](TECHNICAL.md), section 12).
- **The checker would have seen almost nothing.** In `--prompt-only` mode, it checks the tags, the main line and the figures quoted. The continuations written in the text, the HTML tags and the false stories go through: rereading them is up to you.

## 25 November 2026, with the zip and the English prompt

A single trial, the first of the English prompts of version 5.0.0, before their release.\
A correspondence game of 39 plies, won by the player, sent with its zip to GPT-6 (OpenAI), on the free plan.

- It announced case B, python-chess could not be installed, and wrote its PGN by hand. The figures of its answer are all right.
- `verify-analysis.py` ends on 2 failures: a variation placed after the move that it should replace, `( 19... Kg8 20. Qh7# )` after 19.Qh5+, is illegal there, and python-chess stops reading the main line at ply 37 out of 39. Without this variation, the PGN passes with no failure.
- Its three costliest errors were those of the opponent, and `$7`, forced move, sat on the check instead of the reply.
- It put `$6` on seven moves that the engine does not classify.

These four points led to the last changes of version 5.0.0: the prompts say where a variation starts, where `$7` goes and whose errors to give, and the checker lists such NAGs as other opinions.

The prompts changed once more on 27 November 2026, after these trials: the notes of the player are kept, the commands of a site left out, the game of the short prompt stands in a code block, and the review keeps to the agreed scope.\
These last instructions went through the series of 27 November 2026, below.

## 26 November 2026, the two routes, with the English prompts

A correspondence game of 54 plies, lost by the player, mated on move 27, and the English prompts of version 5.0.0, before their release.\
The usage limits of the free plans did not allow both routes: ChatGPT, Gemini and Copilot only received the short prompt, and Claude, on the subscription, both.

The game was collected once per route, two hours apart. The evaluations of Stockfish vary from one run to another: the table of the short prompt marks 12 mistakes and blunders, 7 of them by the player, and the archive 11.

| LLM | Plan, route | Report of `verify-analysis.py` | On the board |
|---|---|---|---|
| Claude Sonnet 5.5 (Anthropic), effort Max | subscription, zip | no failure, no warning: the 11 mistakes and blunders commented on, 17 playable variations, the 59 evaluations quoted all found | no error found |
| Claude Sonnet 5.5 (Anthropic), effort Max | subscription, `--prompt-only` | no failure: code block, tags intact, the 54 plies commented on, 19 playable variations, the 91 evaluations quoted all found | no error found |
| Gemini (Google), version not noted | free, `--prompt-only` | no failure: code block, tags intact, the 54 plies commented on, 18 playable variations, the 56 evaluations quoted all found | the colors of the bishops confused twice, a fianchetto prepared with no bishop left, the queenside said developed with the c1 bishop still at home |
| ChatGPT (OpenAI), version not noted | free, `--prompt-only` | 1 failure: the 19 variations are written inside the comments, none is playable. Twelve suffixes `?` or `??` added to the moves | a piece down announced as level material, a check that is not one, a recapture said to be forced while the other rook could take |
| Copilot (Microsoft), version not noted | free, `--prompt-only` | 1 failure: the Site tag returned as an HTML link. No code block, 18 playable variations | a piece down announced twice as level material, three moves said to be forced while others were legal |

The errors of the last column were checked one by one on the position, with python-chess. **The list is not exhaustive.**

What this series shows:

- **The English prompts do the job.** Three of the five answers quote evaluations, 206 in all, every one found in the data of the engine; ChatGPT and Copilot quote none. Each answer comments on every mistake and blunder of its table.
- **The errors of the player, and only theirs.** The five reviews give three errors of the player, none of the opponent. With the zip, Claude even set aside the two costliest by the figures, 21.Qb1 and 22.Kh2, played in a position already lost, and said why.
- **Where a variation starts is understood.** The 91 variations of the five answers, those of ChatGPT included, are legal and drawn from the lines of the engine, and none repeats the moves played.
- **The free plans keep their faults of 21 November.** ChatGPT still writes the variations inside the comments and adds suffixes to the moves, Copilot still gives no code block and turns the Site tag into a link. Gemini passes the checker, not the check on the board.
- **Claude checks itself.** With the short prompt, it says it replayed its variations with python-chess and checked its explanations with Stockfish, which the prompt does not ask for. It comments on each move there, in 2178 words; with the zip, on 18 moves, as the full prompt asks, in 1062 words.
- **The checker does not judge the stories.** Gemini passes it with no failure, and four errors on the board.

## 27 November 2026, the two routes, with the prompts as released

The game is [`example-games/player-notes.pgn`](../example-games/player-notes.pgn), 49 plies, scored 1-0 in a position lost for the player: `commented-game.pgn` without the analysis of Lichess, its clocks kept, and three notes of the player added.\
They test the last instructions: one quotes a percentage, "I was 80% sure", one calls 9.Nb5 the best move of the game, a blunder for the engine, and one is in French, "Ici je pensais gagner une pièce", here I thought I was winning a piece.

The game was collected once per route: the table of the zip marks 22 mistakes and blunders, that of the short prompt 23.\
The zip went to Claude on both plans, the short prompt to all five.

| LLM | Plan, route | Report of `verify-analysis.py` | Notes and clocks | On the board |
|---|---|---|---|---|
| Claude Sonnet 5.5 (Anthropic), effort Max | subscription, zip | no failure, no warning: the 22 mistakes and blunders commented on, 23 playable variations, the 62 evaluations quoted all found | the three notes kept, the percentage written "80 percent", the clocks left out; at 9.Nb5, "Stockfish disagrees" | one error, in the final summary: 9.axb4 called "a free bishop", while the a6 knight defends it |
| Claude Sonnet 5.5 (Anthropic), effort High | free, zip | no failure, no warning: the 22 mistakes and blunders commented on, 23 playable variations, the 33 evaluations quoted all found. The quota ran out before the final summary | the three notes kept, the percentage written "80 percent", the clocks left out; the note of 9.Nb5 refuted on the board, the French note quoted, then translated | 9.axb4 "a clean piece", while it wins a bishop for a pawn; after 11.Ne4, "a piece down for the rest of the game", while material is level again after 23...Bxb8 |
| Claude Sonnet 5.5 (Anthropic), effort Max | subscription, `--prompt-only` | no failure: the 49 plies commented on, 31 playable variations, the 113 evaluations quoted all found | the three notes kept as written, the clocks left out; "Stockfish disagrees with your note" at 9.Nb5 and 11.Ne4 | no error found |
| Claude Sonnet 5.5 (Anthropic), effort Max | free, `--prompt-only` | no failure: the 49 plies commented on, 31 playable variations, the 54 evaluations quoted all found | the three notes kept as written, the clocks left out; at 9.Nb5, "the table has a different view" | 3.g4 "before a single piece is developed", while Nf3 is out; 4.Nfd2 "leaves your h-pawn loose", while Rh1 defends it; the bishop of 8...Bb4 "free", twice |
| ChatGPT (OpenAI), version not noted | free, `--prompt-only` | no failure: the 49 plies commented on, 28 playable variations | none of the three notes kept as written: two paraphrased, the one of 9.Nb5 dropped; the clocks left out | 12...e3 "a passed pawn", while the e2 pawn stands in front of it; 13.O-O "connecting your rooks", with Bc1 and Qd1 between them; 16...gxf4 "opening the f-file", while it opens the g-file; 23.Nxb8 "a rook won", while it wins the exchange; level material called an advantage for Black |
| Gemini (Google), version not noted | free, `--prompt-only` | 1 failure: 22...Qd7 changed into 22...Qe7. 39 plies commented on, the 20 variations written inside the comments | none of the three notes kept, the clocks left out | 8...Bb4 "a pin", while no piece is pinned; 24...Nxg2 "recaptures", after a move that took nothing; level material at the end called a large advantage for Black |
| Copilot (Microsoft), version not noted | free, `--prompt-only` | 5 failures: the copy of its answer holds the whole PGN on one line, tags included. Put back on separate lines: no failure, the 49 plies commented on, 15 playable variations | the three notes kept, with their clocks | 4.Nfd2 "attacks the bishop", which nothing attacks; 12...e3 "a passed pawn"; 21.Nxa7 attacking the rooks, which nothing attacks |

The errors of the last column were checked one by one on the position, with python-chess. **The list is not exhaustive.**

What this series shows:

- **The notes of the player get through Claude and Copilot.** Claude keeps them in its four answers, ahead of its own comment, and contradicts the note of 9.Nb5, three times in the name of the engine, once on the board. With the zip, it writes the percentage in words and translates the French note after quoting it. Copilot keeps them too, ChatGPT paraphrases two and drops the third, Gemini keeps none. The checker counts them, "0 kept out of 3" for ChatGPT, without a failure.
- **The clocks are left out, except by Copilot**, which keeps the three that stood with the notes.
- **A move changed, for the first time in these trials.** Gemini returns 22...Qe7 instead of 22...Qd7. The game stays legal to the end: only the checker sees it.
- **The zip goes through on a free plan.** Claude returned a complete PGN, with its overview, its 22 mistakes and blunders commented on and its 23 variations. The quota of tokens ran out before the final summary: it is full again after about six hours, according to the author, so a player in no hurry can get the whole analysis without paying.
- **Claude is ahead again.** Its four answers hold their figures, and with the zip on the subscription its clocks, database figures, material and FEN are all right. With the short prompt on the subscription, no error is found on the board. The other three call the bishop of 8...Bb4 free at some point, while the a6 knight defends it: taking it costs a pawn.
- **ChatGPT changed its form, not its stories.** For the first time, its variations stand outside the comments, all playable, and the checker finds no failure. Its stories keep their errors, two of them shared: the e3 pawn called passed, with Copilot, and level material called an advantage for Black, with Gemini.
- **The checker does not judge the stories.** ChatGPT passes it with no failure, and five errors on the board in the table.
