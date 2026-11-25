[![License: CC0](https://img.shields.io/badge/license-CC0_1.0-lightgrey.svg?style=plastic)](https://creativecommons.org/publicdomain/zero/1.0/)
![Hack The Planet](https://img.shields.io/badge/hack-the--planet-black?style=plastic&logo=Debian&logoColor=white)
![Built With Love](https://img.shields.io/badge/built%20with-%E2%9D%A4%20by%20DeuZa-red?style=plastic)

![GitHub release](https://img.shields.io/github/v/release/deuza/IAnalyze?label=release&style=plastic)
[![GitHub last commit](https://img.shields.io/github/last-commit/deuza/IAnalyze?style=plastic)](https://github.com/deuza/IAnalyze/commits/main)
![GitHub commit activity](https://img.shields.io/github/commit-activity/t/deuza/IAnalyze?style=plastic)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/deuza/IAnalyze?style=plastic)

# IAnalyze

Version française : [README.fr.md](README.fr.md)

IAnalyze prepares the analysis of a chess game by an LLM *(called the analyst in the rest of this document)*.

It adds the Stockfish evaluations to it: one line per ply, and behind each weak move the best move and its continuation.\
Its script, `ianalyze.py`, gathers the PGN, the statistics of the Lichess explorer, the catalog of openings and the Stockfish evaluations, then writes two files: a zip archive and the prompt that goes with it.

The idea comes from the program [Lucas Chess](https://lucaschess.pythonanywhere.com/), whose analysis prompt fits in a few lines followed by the game.

*The script produces no analysis: it gives the analyst reliable figures, and the prompt makes it stick to them.*

```bash
./ianalyze.py my-game.pgn
```

```text
analysis-my-game-20261125-142017.zip
analysis-my-game-20261125-142017.prompt.txt
```

You paste the content of the prompt.txt file into a new conversation with Claude, you attach the zip file, and you get back an annotated PGN and a summary.

**IAnalyze is made for Claude:**\
With a free account, or for another LLM, the `--prompt-only` option writes a short prompt that carries the game and the Stockfish evaluations, to be pasted alone, without an attachment: see section 7.

An additional tool, `verify-analysis.py`, checks the PGN that the LLM returned to you: see section 8.

Platforms: Debian and macOS (Homebrew).\
Python 3.10 or more recent, and python-chess, which the script installs by itself in a dedicated virtual environment.

The documentation fits in four files:

- this README, to install IAnalyze and analyze a game
- [EXAMPLES.md](EXAMPLES.md), the quick reference: every command, every option, and what the terminal shows
- [TECHNICAL.md](TECHNICAL.md), for how the script works, its use from another program, and the detail of the files produced
- [TESTS.md](TESTS.md), to run the tests and know what each one checks

## Contents

- [1. Overview](#1-overview)
- [2. Requirements and installation](#2-requirements-and-installation)
- [3. Usage](#3-usage)
- [4. Common options](#4-common-options)
- [5. Result](#5-result)
- [6. Analysis prompt](#6-analysis-prompt)
- [7. Choosing an LLM](#7-choosing-an-llm)
- [8. Checking the returned PGN](#8-checking-the-returned-pgn)
- [9. Sources and links](#9-sources-and-links)
- [Licenses](#licenses)

---

## 1. Overview

The script gathers and formats:

- **the PGN** of the game, read from a local file or downloaded from Lichess
- **the statistics of the Lichess explorer**, position by position, to locate the exit from theory
- **the Stockfish evaluation** of each move, computed on your machine

The whole chain takes three steps:

1. `./ianalyze.py my-game.pgn`

   The script collects, computes, and writes two files: `analysis-<game>-<date>.zip` and `analysis-<game>-<date>.prompt.txt`.

2. In a new conversation with an LLM, you paste the content of the prompt and you attach the archive.

   If the LLM does not open zip files, unzip the archive and send it all its files (see section 6).

3. The LLM returns an annotated PGN and a summary.

   It explains, it does not compute: the evaluations come from Stockfish, the theory comes from the explorer and the catalog.

The prompt is drawn from the template `prompt-template.txt`, kept next to the script.\
It always describes the summary that this version of the script has just written: the two cannot diverge.

The files of the repository:

| File | Role |
|---|---|
| `ianalyze.py` | the script, in a single file |
| `prompt-template.txt` | the template from which the prompt of each game is drawn (section 6) |
| `prompt-only-template.txt` | the template of the short prompt of `--prompt-only` (section 7) |
| `verify-analysis.py` | the additional tool that checks the PGN returned by the LLM (section 8) |
| [`EXAMPLES.md`](EXAMPLES.md) | the quick reference: commands, options and outputs |
| [`TECHNICAL.md`](TECHNICAL.md) | the technical documentation |
| [`TESTS.md`](TESTS.md) | the tests: how to run them, what each one checks |
| [`CHANGELOG.md`](CHANGELOG.md) | the history of the versions |
| [`README.fr.md`](README.fr.md) | the French version of this README |
| [`EXAMPLES.fr.md`](EXAMPLES.fr.md) | the French version of EXAMPLES.md |
| [`TESTS.fr.md`](TESTS.fr.md) | the French version of TESTS.md |
| [`LICENSE`](LICENSE) | the license of the code (see Licenses) |
| `test-app.sh`, `test.pgn` | the test suite and its test game, described in [TESTS.md](TESTS.md) |
| `example-games/` | the games and files of the examples of [EXAMPLES.md](EXAMPLES.md), among them a real anonymized game for a first try |

## 2. Requirements and installation

Everything is installed in your home directory, on Debian as on macOS.

Only the installation of the Debian packages requires root rights.

**1. The packages**

On Debian, as root:

```bash
apt install git python3-venv stockfish
```

On macOS, with Homebrew, whose Python already provides the venv module:

```bash
brew install git python stockfish
```

**2. The repository**, under the account of the player:

```bash
git clone https://github.com/deuza/IAnalyze.git
```

```bash
cd IAnalyze
```

**3. The virtual environment and the catalog**, under the same account:

```bash
./ianalyze.py --install-venv
```

```bash
./ianalyze.py --install-catalog
```

Each player of the machine repeats steps 2 and 3 under their own account: nothing is shared, nothing needs to be copied.

### What these two commands do

**`--install-venv`** creates a dedicated virtual environment and installs python-chess in it, which Debian does not package.\
The script then restarts in it by itself: you keep calling it with the system's Python.

**`--install-catalog`** downloads the catalog of the named openings of Lichess, kept locally.\
Run it again from time to time to update it.

**Stockfish is mandatory**: its evaluation is part of every collection.

### Default locations

The same on both platforms, except for the engine.

Everything the script creates for itself stays in the folder of the application: deleting this folder leaves nothing behind, except your token.

The `local/` folder only keeps what the script can rebuild by itself, the virtual environment and the catalog: emptying it brings the application back to a fresh state without touching your settings.

| | Location |
|---|---|
| `--venv` | `local/venv`, in the folder of the application |
| `--catalog` | `local/`, in the folder of the application |
| settings | `settings.ini`, at the root of the folder of the application, like any other settings file named by `--settings` |
| token | `~/.lichess_token` |
| `--stockfish`, Debian | `/usr/games/stockfish` |
| `--stockfish`, macOS | the binary found in the PATH, otherwise `/opt/homebrew/bin/stockfish` |

Up to version 4.0.2, the virtual environment and the catalog were kept in `~/.local/share/IAnalyze`, the settings in `~/.config/IAnalyze`.

The script no longer reads them there: run `--install-venv` and `--install-catalog` again, then delete these two directories. Your settings are asked again on the first run in a terminal.

### Lichess token

The Lichess explorer requires a personal access token.

Once logged in to Lichess, create it on <https://lichess.org/account/oauth/token>, without ticking any permission.\
The script reads it from `~/.lichess_token`, a file that contains only the token and that only you can read.

Create the empty file, close its access, then paste the token into it:

```bash
touch ~/.lichess_token
```

```bash
chmod 600 ~/.lichess_token
```

```bash
vi ~/.lichess_token
```

*Use `nano` if you do not know `vi`, or the editor of your choice.*

In this order, the token is never in a file that others can read.\
The script never displays it, writes it in none of the files it produces, and does not receive it on the command line.\
It warns you if the file can be read by anyone other than you.

Without a token, run the script with `--no-explorer`.

### Personal settings

Your username, your usual time control and your rating are kept in `settings.ini`, at the root of the folder of the application.

The script asks for them only once, on the first run in a terminal.

```ini
[player]
usernames = MyUsername, OtherUsername
time_control = 15+10
rating = 1300
```

You can edit this file by hand, or delete it with `--purge-settings`: your answers will then be asked again.

**The rating** is a number of approximate Elo points, from 100 to 3500, or "unknown".

It is passed on to the analyst, who adapts the explanations to it. Without it, the Elo of your tag in the game is used.

**The time control** is written `15+10` for real time, minutes per player then increment in seconds, and `14 days` for correspondence with a fixed delay.

**Another player** of the same machine keeps their settings in a file of their own, named by `--settings`: `--settings player2.ini`. The option takes a file name ending in `.ini`, kept in the folder of the application next to `settings.ini`, never a path. In a terminal, a name whose file does not exist yet is created only after confirmation, so that a typo does not start a new file.

**For a single run** that leaves your settings aside, the game of a friend for example, `--no-settings` neither reads nor writes any settings file.

The other forms of correspondence, the optional key `annotator` and the way the script rewrites this file are described in [TECHNICAL.md](TECHNICAL.md), section 6.

## 3. Usage

```bash
./ianalyze.py SOURCE [options]
```

SOURCE accepts three forms:

```bash
./ianalyze.py my-game.pgn                        # local PGN
./ianalyze.py https://lichess.org/<identifier>   # Lichess URL
./ianalyze.py <identifier>                       # identifier
```

The identifier is the string of 8 characters that follows `lichess.org/` in the address of the game, or 12 in the address of the game seen from one side.

**The PGN must contain a single game, whole, in standard chess, written in English notation**: K, Q, R, B, N.

**Lichess is the reference source of IAnalyze**: the script downloads a game from it by its address or its identifier, and its explorer provides the opening statistics.

The exports of these sites and programs have been tried, and go through as they are:

| Source | Particularity of its export |
|---|---|
| Lichess | none. With the analysis of the site, its comments, its variations and its clocks are read too |
| Chess.com | none |
| chess-mail.com | long notation (`Ng1f3`), result written twice at the end of the file: the second one is ignored, and the log says so |
| ajedrezmail.org | one move per line |
| Lucas Chess | durations and clocks in comments |

A game from each one is in the `example-games` directory, anonymized. Lichess has two: `game-lichess-org.pgn`, the plain export, and `commented-game.pgn`, the export with the analysis of the site.

The script refuses rather than analyze wrongly:

- a file that gathers several games: isolate the one to analyze in a separate file
- a game that does not start from the initial position, that is, one that carries a FEN tag: to study a position, load it into an analysis board
- a game written in French notation (R, D, T, F, C) or in figurines: without this refusal, "Cf3" would be read "f3", a pawn move, and the analysis would be about another game than yours
- a damaged PGN: brace or parenthesis never closed, free text outside the braces

The error message names what is refused. The forms of address accepted and the detail of these checks are in [TECHNICAL.md](TECHNICAL.md), section 4.

### The questions of the script

Before the collection, the script asks you a few questions.\
*Enter keeps the suggested value.*

- **On the very first run only**: your username, your usual time control and your rating, kept in the settings file.
- **Your side**, if it cannot be deduced from the White or Black tags thanks to your usernames.

  The empty tags are then filled in, and the PGN given is kept as `game-original.pgn`.

- **The time control of the game**, if the TimeControl tag does not give it: real time, correspondence or unknown.

  Enter keeps your usual time control. Only whole numbers are accepted, another answer makes the question come again.

- **Four context questions**: scope, goal, particular context, comments to include in the final PGN.

The script writes the time control passed on to the analyst by itself, always in the same way:

```text
rapid, 15 minutes + 10 seconds per move
correspondence, 14 days per move
correspondence, clock of 5 days + 36 hours per move, maximum of 20 days
```

An answer is 255 characters at most.\
A player name or a username can contain neither a quote, nor a backslash, nor a square bracket, nor a brace: it goes into a tag of the PGN, which these signs would make unreadable.

A refused answer is asked again.

To run a collection without answering anything, add `--no-questions`.\
The prompt then tells the LLM that your answers were not collected, and it asks you for them itself before analyzing.

The script does not ask its questions either when it is not run by hand in a terminal, from another program for example: see [TECHNICAL.md](TECHNICAL.md), section 5.

## 4. Common options

A few options are enough for most uses:

| Option | Effect |
|---|---|
| `--no-explorer` | no opening statistics: neither token nor catalog is needed |
| `--no-questions` | no question: the LLM will ask them itself |
| `--prompt-only` | a short prompt to be pasted alone, without an archive, for a free account or an LLM that does not open zip files (section 7) |
| `--keep-folder` | keeps the unzipped folder next to the archive |
| `--output-dir DIR` | writes the files into the directory DIR |
| `--database masters` | queries the masters database instead of the one of all the Lichess players |
| `--depth D` | search depth of Stockfish, 18 by default: the greater it is, the longer the computation |
| `--stockfish-moves N` | limits the engine to the first N moves |
| `--usernames LIST` | your usernames, for this collection only |
| `--settings NAME` | another settings file, by its name, in the folder of the application: one profile per player |
| `--no-settings` | neither reads nor writes any settings file, for this run only |

```bash
./ianalyze.py my-game.pgn --no-explorer --output-dir ~/analyses
```

All the options are in [EXAMPLES.md](EXAMPLES.md), each one with its command and what the terminal shows.\
`./ianalyze.py --help` gives a summary of them.

## 5. Result

Archive: `analysis-<label>-<YYYYMMDD-HHMMSS>.zip`, the label being the name of the PGN without extension, or the Lichess identifier.\
A folder or an archive of the same name adds a suffix -2, -3...

On failure, the working folder is kept as it is for diagnosis.

The label is sanitized (see [TECHNICAL.md](TECHNICAL.md), section 11): the log then announces it with "Folder name sanitized: ..."

Content:

| File | Content |
|---|---|
| `summary.md` | the summary, which the analyst reads first |
| `game.pgn` | the PGN, headers filled in if need be |
| `game-original.pgn` | the PGN given, if headers were missing |
| `context.md` | the answers to the startup questions |
| `explorer/NNN-<uci>.json` | one raw answer per ply queried |
| `stockfish/evaluations.json` | the complete evaluations of the engine, whole variations |
| `collection.json` | exact parameters of the collection, without the token. `pgn_encoding` and `pgn_remarks` say how the PGN was decoded, `prompt_written` names the prompt |

Next to the archive, and not inside it:

```text
analysis-<label>-<YYYYMMDD-HHMMSS>.prompt.txt
```

It is the analysis prompt of this game, to be pasted into the conversation.\
The log gives its path; standard output only carries the path of the archive.

With `--prompt-only`, there is no archive: standard output carries the path of the prompt.

The content of each of these files is detailed in [TECHNICAL.md](TECHNICAL.md), section 10.

## 6. Analysis prompt

The data is not enough: the analyst must be told what to do with it.\
This text lives in the template `prompt-template.txt`, which you can edit freely, without touching the script.

At each collection, the script draws the prompt of the game from it: it fills in the values and keeps only the passages that apply.

To write your own template, the list of the markers, the values and the conditions is in [TECHNICAL.md](TECHNICAL.md), section 12.

The prompt follows what the collection really did. Without the explorer, it asks for neither frequency nor most played move.\
With `--stockfish-moves`, it says how far the engine evaluated. With `--multipv 1`, it does not announce three moves per position.

The prompt is pasted as a message, in a new conversation, with the archive as an attachment.\
It is valid for one game: pasting it in each conversation is what guarantees that it matches the archive.

Not every LLM opens a zip file, and not every LLM runs code.

The prompt provides for both cases:

- **The LLM does not accept the archive**: unzip it and send it **all** its files, attached or pasted.

  `--keep-folder` leaves the unzipped folder next to the archive.

  The prompt asks the analyst to use all the files, not only the summary: the `.json` files carry the whole variations of the engine and all the moves known to the explorer, which `summary.md` summarizes.

  If it receives only some of them, it must say which ones are missing and ask you to send them.

- **The LLM runs code**: it builds the PGN with python-chess and proves its legality.
- **The LLM does not run code**: it writes the PGN itself, says so, and lets you open the file to confirm.

## 7. Choosing an LLM

**Go for Claude**: this is the advice of this repository, and it comes from the trials described below.

With the zip, Claude is the only one that returned a PGN usable as it is.\
With the short prompt, with a subscription as with a free account, it returned the cleanest PGNs, and its explanations are the ones that best stood the check on the board.

IAnalyze was developed with it by the author, who uses it to analyze their games.\
Two routes lead to an analysis, and it is the first choice on both:

| Route | What you send | What the LLM needs | What you get back |
|---|---|---|---|
| The zip and the prompt | the archive as an attachment, the prompt pasted | to open a zip file, run code, return a file | a PGN file built with python-chess, based on all the data |
| `--prompt-only` | a single pasted text, without an attachment | a plain conversation | the annotated PGN in a code block |

**With a free account, take `--prompt-only` and Claude. Choose the model `Sonnet 5.5` with the effort `Max`.**\
This is the combination that gave the best result without paying anything.

These trials were run with version 4.0, whose prompts were in French. The English prompts of version 5.0.0 have not been through them again.

### With the zip and the prompt

This is the whole chain: you attach the zip, you paste the prompt, the LLM returns a PGN file.\
It then has all the data: the summary, the three best moves of the engine at each position, the statistics of the explorer.

This chain requires an LLM that can:

- Open a zip archive
- Run code and install python-chess there, to build the PGN and prove its legality
- Return a file to download

In the trials, only Claude carried it through correctly.

Two tips if you try it with another LLM:

- Some refuse a `.pgn` file as an attachment: rename it to `.txt`, or switch to `--prompt-only`.
- If the LLM announces a file that you cannot find, ask it for the PGN in a code block.

### With `--prompt-only`

For a free account, or for an LLM that does not open zip files, refuses some attachments or does not run code, the script writes a short prompt:

```bash
./ianalyze.py my-game.pgn --prompt-only
```

You paste this single text into the conversation, without attaching anything.\
The LLM returns the annotated PGN in a code block, which you save into a `.pgn` file yourself.

What you should know about this mode:

- The prompt weighs about 4 KB for `game-lichess-org.pgn`, 39 plies, and 11 KB for `commented-game.pgn`, 49 plies: each weak move adds its best move and its continuation
- It carries neither the summary nor the `.json` files: the LLM only has the game, the table of the engine and, with the explorer, a sentence on the opening
- No archive is written, the prompt is the only file produced
- The five answers tried returned the whole game, every move commented, without a single invented evaluation

To check the returned PGN with `verify-analysis.py --prompt-only` (section 8), add `--keep-folder` to the collection: the checker needs the evaluations that were used for the prompt.

### Trust the figures, check the stories

This is what the two series of trials have in common.

**The figures hold.** No LLM invented an evaluation, with the zip as with the short prompt.\
What comes from the table of the engine is copied faithfully: the losses, the best moves, their continuations.

**The stories are fragile.**\
What the LLM deduces from the position on its own can be wrong: a sacrifice that is not one, a hanging piece that nobody points out, a mate in one that is a mate in two.

When a comment surprises you, set up the pieces and look.\
The script `verify-analysis.py` checks the form of the PGN and the figures quoted, it does not judge what is told.

### Trials run

Two series, a single trial per LLM and per plan, one game per series.

**This is not a benchmark.**\
A single trial says nothing about the consistency of a model. But the two series point the same way, and the advice of this section rests on nothing else than what was seen.

#### November 20, 2026, with the zip and the prompt

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

The free plan of Claude also announces file creation and code execution, on other models than the one of this trial, according to [its pricing page](https://claude.com/pricing), read on November 20, 2026 and again on November 25, 2026.

It has not been tried with the zip file.

#### November 21, 2026, with `--prompt-seul`, now `--prompt-only`

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
- **Asking for three errors makes one up.** The player had made only two. ChatGPT, Gemini and Copilot presented a third one, Claude answered both times that there were only two. The short prompt has since given the real number of weak moves of the player (see [TECHNICAL.md](TECHNICAL.md), section 12).
- **The checker would have seen almost nothing.** In `--prompt-only` mode, it checks the tags, the main line and the figures quoted. The continuations written in the text, the HTML tags and the false stories go through: rereading them is up to you.

## 8. Checking the returned PGN

`verify-analysis.py` is an additional tool, independent of the collection: it checks what the LLM returned to you.

An LLM can return a PGN that looks right and is not: an illegal move in a variation, an arranged figure, a blunder passed over in silence.\
`verify-analysis.py` compares the returned PGN with the archive that the LLM received, and gives the same report for each LLM tried.

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip llm-annotated.pgn
```

Copy the conversation into a text file to have the positions and the evaluations it quotes checked too:

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip llm-annotated.pgn --summary llm-conversation.txt --name "Model name"
```

If the LLM returned no PGN, put a dash instead of the file:

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip - --summary llm-conversation.txt
```

For a PGN obtained with the short prompt of `--prompt-only`, add the same option, and give the working folder kept by `--keep-folder`:

```bash
./ianalyze.py my-game.pgn --prompt-only --keep-folder
```

```bash
./verify-analysis.py analysis-my-game-20261125-142017 llm-annotated.pgn --prompt-only
```

The short prompt asks for less than the full prompt. With this option, the checks that it does not ask for are skipped: lines of 79 characters, overview before the first move, NAGs, `%`, em dash, suffix notation, Annotator and PlyCount tags, length of the variations, number of FEN. What remains: the reading, the main line, the braces, the tags copied, the end marker, the mistakes and blunders commented on, the evaluations quoted and the variations.

If you agreed on a scope with the LLM, the first 20 moves for example, the script reads it in your answer to the startup question and expects no comment beyond it.\
When the scope was set in the conversation, give it:

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip llm-annotated.pgn --scope 20
```

The script accepts the zip or its unzipped folder, and restarts by itself in the virtual environment of IAnalyze, at its default location.\
A folder that holds several collections is refused: give the one of the collection that the LLM received.

It has no `--venv` option. If your environment is elsewhere, run it with the Python of that environment: `~/venv/chess/bin/python3 verify-analysis.py ...`

### What is checked

| Check | Flaws found |
|---|---|
| Reading | file outside UTF-8, illegal move in the game or in a variation, blank line in the body of the game |
| Main line | different from the original game |
| Format | line of more than 79 characters, opening or closing brace in a comment, `%`, em dash, suffix notation, tags missing or out of order, end marker |
| Commented moves | mistake or blunder of Stockfish left without a comment within the agreed scope, position NAG contrary to the evaluation of the engine |
| Evaluations | figure or mate quoted that exists nowhere in the data of the engine |
| Variations | variation written inside a comment, hence not playable, illegal or too long variation |
| Conversation | FEN invalid or foreign to the game, em dash |

Two of these flaws come from real PGNs of LLMs and deserve an explanation:

- **The blank line in the body of the game.** python-chess sees the end of the game there and does not read what follows. The script finds it wherever it is, even if it only hides a variation or the end marker, then goes on with its checks on the file once the line is removed.
- **The variation written between braces.** It is only text, SCID does not replay it. The script replays it itself to say whether it is legal and whether it comes from a line of the engine.

### Reading the report

| Marker | Meaning |
|---|---|
| `OK` | compliant |
| `FAIL` | contrary to a mandatory instruction of the prompt |
| `WARNING` | to be looked at closely, without being necessarily wrong |
| `INFO` | measure given to compare the LLMs with one another |

Exit code: 0 without `FAIL`, 1 with at least one `FAIL`, 2 if a file cannot be read or if the archive is not an IAnalyze one.\
With the code 2, no check took place.

### What the script does not do

It does not judge the quality of the commentary. A wrong but well-formed explanation goes through: an LLM can put a queen on the wrong square in a sentence without any check seeing it.\
This reading stays yours.

Three limits to know:

- An evaluation rounded to one decimal is accepted: "+0.35" quoted as "+0.4" or "+0.3" does not count as invented
- A number written without a sign, "7.77", is not taken for an evaluation: the script would confuse it with a duration or a rating. An invented figure written this way thus goes through
- The script finds a figure that exists nowhere, not a real figure given to the wrong move

## 9. Sources and links

What the script queries:

- Personal access token: <https://lichess.org/account/oauth/token>, once logged in to Lichess
- Explorer, database of all players: `https://explorer.lichess.org/lichess`
- Explorer, masters database: `https://explorer.lichess.org/masters`
- Catalog of openings: [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings), files `a.tsv` to `e.tsv`. They are the ones that the server of the explorer loads too.

What it relies on:

- [python-chess](https://python-chess.readthedocs.io/en/latest/), the library that reads the PGN and drives the engine
- [Stockfish](https://stockfishchess.org/), the engine, and [its UCI options](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html), among them Threads, Hash and MultiPV
- [PGN specification](https://www.saremba.de/chessgml/standards/pgn/pgn-complete.htm), Steven J. Edwards, 1994

Where the time controls come from:

- Categories of real time: [Speed.scala](https://raw.githubusercontent.com/lichess-org/scalachess/master/core/src/main/scala/Speed.scala), in [scalachess](https://github.com/lichess-org/scalachess), the rules library of Lichess
- Correspondence, ICCF: [ICCF Rules, in force since January 1, 2026](https://webfiles.iccf.com/rules/2026/2026%20ICCF%20Rules%2C%20260311.pdf), section 2.4 (PDF)
- Correspondence, clock: [rules of chess-mail.com](https://www.chess-mail.com/index.php?page=reg)

Conventions of the repository:

- [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) for `CHANGELOG.md`
- [Semantic Versioning](https://semver.org/) for the version numbers

---

## Licenses

- Catalog of the openings of Lichess (chess-openings): CC0. It is downloaded at installation, not distributed with this repository.
- python-chess, installed in the virtual environment: GPL-3.0-or-later.
- Stockfish, installed by your system: GPL-3.0.
- All the content of this repository is under the [CC0](LICENSE) license: do whatever you want with it :)

[![CC0](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/cc-zero.svg)](https://creativecommons.org/publicdomain/zero/1.0/)

<p align="center">With ❤️ by <a href="https://github.com/deuza">DeuZa</a></p>
