[![License: CC0](https://img.shields.io/badge/license-CC0_1.0-lightgrey.svg?style=plastic)](https://creativecommons.org/publicdomain/zero/1.0/)
![Hack The Planet](https://img.shields.io/badge/hack-the--planet-black?style=plastic&logo=Debian&logoColor=white)
![Built With Love](https://img.shields.io/badge/built%20with-%E2%9D%A4%20by%20DeuZa-red?style=plastic)

![GitHub release](https://img.shields.io/github/v/release/deuza/IAnalyze?label=release&style=plastic)
[![GitHub last commit](https://img.shields.io/github/last-commit/deuza/IAnalyze?style=plastic)](https://github.com/deuza/IAnalyze/commits/main)
![GitHub commit activity](https://img.shields.io/github/commit-activity/t/deuza/IAnalyze?style=plastic)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/deuza/IAnalyze?style=plastic)

# IAnalyze

Version française : [README.fr.md](README.fr.md)

IAnalyze prepares the analysis of one of your chess games by an LLM *(called the analyst in the rest of this document)*, Claude above all.

You give it a game, it gathers the figures: the Stockfish evaluation of each move, computed on your machine, with the best move and its continuation behind each weak move, the statistics of the Lichess explorer and the name of the opening.\
It writes them into a zip archive, with the prompt that goes with it.

```bash
./ianalyze.py my-game.pgn
```

```text
analysis-my-game-20261125-142017.zip
analysis-my-game-20261125-142017.prompt.txt
```

You paste the content of the prompt.txt file into a new conversation with Claude, you attach the zip file, and you get back your game, annotated move by move, and a summary of your errors.\
The LLM explains, it does not compute: the evaluations come from Stockfish, the theory comes from the explorer and the catalog.

*The script produces no analysis: it gives the analyst reliable figures, and the prompt makes it stick to them.*

The idea comes from the program [Lucas Chess](https://lucaschess.pythonanywhere.com/), whose analysis prompt fits in a few lines followed by the game.

**IAnalyze is made for Claude:**\
With a free account, or for another LLM, the `--prompt-only` option writes a short prompt that carries the game and the Stockfish evaluations, to be pasted alone, without an attachment: see section 4.

An additional tool, `verify-analysis.py`, checks the PGN that the LLM returned to you: see section 5.

The script, its messages, the archive and the prompt are in English since version 5.0.0, and the analysis is asked for in English.

## Contents

- [1. Installation](#1-installation)
   - [Lichess token](#lichess-token)
   - [What the installation does](#what-the-installation-does)
- [2. Analyzing a game](#2-analyzing-a-game)
   - [The game](#the-game)
   - [The questions of the script](#the-questions-of-the-script)
   - [Your settings](#your-settings)
   - [What you get](#what-you-get)
   - [Sending it to the analyst](#sending-it-to-the-analyst)
- [3. Common options](#3-common-options)
- [4. Choosing an LLM](#4-choosing-an-llm)
   - [With the zip and the prompt](#with-the-zip-and-the-prompt)
   - [With `--prompt-only`](#with---prompt-only)
   - [Trust the figures, check the stories](#trust-the-figures-check-the-stories)
- [5. Checking the returned PGN](#5-checking-the-returned-pgn)
   - [Reading the report](#reading-the-report)
   - [What it does not judge](#what-it-does-not-judge)
- [6. Going further](#6-going-further)
- [Licenses](#licenses)

---

## 1. Installation

Debian or macOS, with Python 3.10 or more recent.

On Debian, the packages are installed as root:

```bash
apt install git python3-venv stockfish
```

On macOS, with Homebrew, whose Python already provides the venv module:

```bash
brew install git python stockfish
```

Then, under your own account:

```bash
git clone https://github.com/deuza/IAnalyze.git
cd IAnalyze
./ianalyze.py --install-venv
./ianalyze.py --install-catalog
```

Each player of the machine repeats these four commands under their own account: nothing is shared, nothing needs to be copied.\
All that remains is the Lichess token, below.

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

Without a token, run the script with `--no-explorer`.\
If Lichess refuses the token, wrong, expired or revoked, the script stops at the first request, before the engine: create a new one, or run again with `--no-explorer`.

### What the installation does

**`--install-venv`** creates a dedicated virtual environment and installs python-chess in it, the library that reads the games, which Debian does not package.\
The script then restarts in it by itself: you keep calling it with the system's Python.

**`--install-catalog`** downloads the catalog of the named openings of Lichess, kept locally.\
Run it again from time to time to update it.

**Stockfish is mandatory**: its evaluation is part of every collection.

Everything the script creates for itself stays in the folder of the application: deleting this folder leaves nothing behind, except your token.\
The `local/` folder only keeps what the script can rebuild by itself, the virtual environment and the catalog: emptying it brings the application back to a fresh state without touching your settings.

The exact locations, and those of the versions before 5.0.0, are in [docs/TECHNICAL.md](docs/TECHNICAL.md#2-files-of-the-repository), section 2.\
The machines on which the whole test suite passed, a Raspberry Pi 4 and an Apple M1 among them, are listed in [docs/TESTS.md](docs/TESTS.md#1-running-the-tests).

## 2. Analyzing a game

### The game

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

The error message names what is refused. The forms of address accepted and the detail of these checks are in [docs/TECHNICAL.md](docs/TECHNICAL.md#4-the-game-its-source-and-its-checks), section 4.

### The questions of the script

Before the collection, the script asks you a few questions.\
*Enter keeps the suggested value.*

- **On the very first run only**: your username (or several, separated by commas), your usual time control and your rating, kept in the settings file.
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

To run a collection without answering anything, add `--no-questions`.\
The prompt then tells the LLM that your answers were not collected, and it asks you for them itself before analyzing.

The limits of an answer, and what changes when the script is not run by hand in a terminal, are in [docs/TECHNICAL.md](docs/TECHNICAL.md#5-startup-questions-and-terminal), section 5.

### Your settings

Your username, your usual time control and your rating are kept in `settings.ini`, at the root of the folder of the application.

The script asks for them only once, on the first run in a terminal.

```ini
[player]
usernames = MyUsername, OtherUsername
time_control = 15+10
rating = 1300
```

You can edit this file by hand, or delete it with `--purge-settings`: your answers will then be asked again.

**The usernames**, one or several separated by commas, are looked up in the White and Black tags of the game, ignoring case, to deduce your side: each one as the whole name or as a run of its words, never as a part of a word.\
`Max` is found in `Max Power`, not in `Maxime` nor in `Max_Power`: write each of your usernames whole.

**The rating** is a number of approximate Elo points, from 100 to 3500, or "unknown".

It is passed on to the analyst, who adapts the explanations to it. Without it, the Elo of your tag in the game is used.

**The time control** is written `15+10` for real time, minutes per player then increment in seconds, and `14 days` for correspondence with a fixed delay.

**Another player** of the same machine keeps their settings in a file of their own, named by `--settings`: `--settings player2.ini`. The option takes a file name ending in `.ini` and not starting with a dot, kept in the folder of the application next to `settings.ini`, never a path. In a terminal, a name whose file does not exist yet is created only after confirmation, so that a typo does not start a new file.

**For a single run** that leaves your settings aside, the game of a friend for example, `--no-settings` neither reads nor writes any settings file.

The other forms of correspondence, the optional key `annotator` and the way the script rewrites this file are described in [docs/TECHNICAL.md](docs/TECHNICAL.md#6-settings), section 6.

### What you get

Archive: `analysis-<label>-<YYYYMMDD-HHMMSS>.zip`, the label being the name of the PGN without extension, or the Lichess identifier.\
A folder or an archive of the same name adds a suffix -2, -3...

Next to the archive, and not inside it:

```text
analysis-<label>-<YYYYMMDD-HHMMSS>.prompt.txt
```

It is the analysis prompt of this game, to be pasted into the conversation.\
The log gives its path; standard output only carries the path of the archive.

With `--prompt-only`, there is no archive: standard output carries the path of the prompt.

On failure, the working folder is kept as it is for diagnosis.

The archive holds the summary that the analyst reads first, `summary.md`, the game, your answers, and the raw data of the engine and of the explorer.\
The content of each of its files is detailed in [docs/TECHNICAL.md](docs/TECHNICAL.md#10-files-produced), section 10.

### Sending it to the analyst

The prompt is pasted as a message, in a new conversation, with the archive as an attachment.\
It is valid for one game: pasting it in each conversation is what guarantees that it matches the archive.

The prompt follows what the collection really did. Without the explorer, it asks for neither frequency nor most played move.\
With `--stockfish-moves`, it says how far the engine evaluated. With `--multipv 1`, it does not announce three moves per position.

Not every LLM opens a zip file, and not every LLM runs code.

The prompt provides for both cases:

- **The LLM does not accept the archive**: unzip it and send it **all** its files, attached or pasted.

  `--keep-folder` leaves the unzipped folder next to the archive.

  The prompt asks the analyst to use all the files, not only the summary: the `.json` files carry the whole variations of the engine and all the moves known to the explorer, which `summary.md` summarizes.

  If it receives only some of them, it must say which ones are missing and ask you to send them.

- **The LLM runs code**: it builds the PGN with python-chess and proves its legality.
- **The LLM does not run code**: it writes the PGN itself, says so, and lets you open the file to confirm.

The prompt is drawn from the template `prompt-template.txt`, kept next to the script, which you can edit freely, without touching the script.\
At each collection, the script draws the prompt of the game from it: it fills in the values and keeps only the passages that apply.\
To write your own template, the list of the markers, the values and the conditions is in [docs/TECHNICAL.md](docs/TECHNICAL.md#12-prompt-template), section 12.

## 3. Common options

A few options are enough for most uses:

| Option | Effect |
|---|---|
| `--no-explorer` | no opening statistics: neither token nor catalog is needed |
| `--no-questions` | no question: the LLM will ask them itself |
| `--prompt-only` | a short prompt to be pasted alone, without an archive, for a free account or an LLM that does not open zip files (section 4) |
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

## 4. Choosing an LLM

**Go for Claude**: this is the advice of this repository, and it comes from the trials described in [docs/TRIALS.md](docs/TRIALS.md). The other LLMs were only tried on their free plans.

With the zip, Claude is the only one that returned a PGN usable as it is.\
With the short prompt, with a subscription as with a free account, it returned the cleanest PGNs, and its explanations are the ones that best stood the check on the board.

IAnalyze was developed with it by the author, who uses it to analyze their games.\
Two routes lead to an analysis, and it is the first choice on both:

| Route | What you send | What the LLM needs | What you get back |
|---|---|---|---|
| The zip and the prompt | the archive as an attachment, the prompt pasted | to open a zip file, run code, return a file | a PGN file built with python-chess, based on all the data |
| `--prompt-only` | a single pasted text, without an attachment | a plain conversation | the annotated PGN in a code block |

**With a free account, take `--prompt-only` and Claude. Choose the model `Sonnet 5.5` with the effort `Max`.**\
This is the combination that gave the best result without paying anything.\
The zip also goes through on a free plan, if you can wait for the quota to come back: see [the series of 27 November 2026](docs/TRIALS.md#27-november-2026-the-two-routes-with-the-prompts-as-released).

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

To check the returned PGN with `verify-analysis.py --prompt-only` (section 5), add `--keep-folder` to the collection: the checker needs the evaluations that were used for the prompt.

### Trust the figures, check the stories

This is what all the trials have in common.

**The figures hold.** No LLM invented an evaluation, with the zip as with the short prompt.\
What comes from the table of the engine is copied faithfully: the losses, the best moves, their continuations.

**The stories are fragile.**\
What the LLM deduces from the position on its own can be wrong: a sacrifice that is not one, a check that is not one, a hanging piece that nobody points out, a mate in one that is a mate in two, a piece down taken for level material.

When a comment surprises you, set up the pieces and look.\
The script `verify-analysis.py` checks the form of the PGN and the figures quoted, it does not judge what is told.

## 5. Checking the returned PGN

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

The short prompt asks for less than the full prompt: with this option, the checks that it does not ask for are skipped.

If you agreed on a scope with the LLM, the first 20 moves for example, the script reads it in your answer to the startup question and expects no comment beyond it.\
When the scope was set in the conversation, give it:

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip llm-annotated.pgn --scope 20
```

The script accepts the zip or its unzipped folder, and restarts by itself in the virtual environment of IAnalyze, at its default location.\
A folder that holds several collections is refused: give the one of the collection that the LLM received.

It has no `--venv` option. If your environment is elsewhere, run it with the Python of that environment: `~/venv/chess/bin/python3 verify-analysis.py ...`

What it checks, and the rules of each check, are in [docs/TECHNICAL.md](docs/TECHNICAL.md#13-the-checker-in-detail), section 13.

### Reading the report

| Marker | Meaning |
|---|---|
| `OK` | compliant |
| `FAIL` | contrary to a mandatory instruction of the prompt |
| `WARNING` | to be looked at closely, without being necessarily wrong |
| `INFO` | measure given to compare the LLMs with one another |

Exit code: 0 without `FAIL`, 1 with at least one `FAIL`, 2 if a file cannot be read or if the archive is not an IAnalyze one.\
With the code 2, no check took place.

### What it does not judge

It does not judge the quality of the commentary. A wrong but well-formed explanation goes through: an LLM can put a queen on the wrong square in a sentence without any check seeing it.\
This reading stays yours.

The limits of its checks are in [docs/TECHNICAL.md](docs/TECHNICAL.md#13-the-checker-in-detail), section 13.

## 6. Going further

- [EXAMPLES.md](EXAMPLES.md): the quick reference, every command, every option, and what the terminal shows
- [docs/TECHNICAL.md](docs/TECHNICAL.md): how the script works, its use from another program, the detail of the files produced, and the guide to take over the project
- [docs/TESTS.md](docs/TESTS.md): the test suite, test by test
- [docs/TRIALS.md](docs/TRIALS.md): the trials of the LLMs, on which the advice of section 4 rests
- [CHANGELOG.md](CHANGELOG.md): the history of the versions

Each document also exists in French, under the same name ending in `.fr.md`, the CHANGELOG aside.\
The sources that the script queries and relies on are listed in [docs/TECHNICAL.md](docs/TECHNICAL.md#14-sources-and-links), section 14.

---

## Licenses

- Catalog of the openings of Lichess (chess-openings): CC0. It is downloaded at installation, not distributed with this repository.
- python-chess, installed in the virtual environment: GPL-3.0-or-later.
- Stockfish, installed by your system: GPL-3.0.
- All the content of this repository is under the [CC0](LICENSE) license: do whatever you want with it :)

[![CC0](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/cc-zero.svg)](https://creativecommons.org/publicdomain/zero/1.0/)

<p align="center">With ❤️ by <a href="https://github.com/deuza">DeuZa</a></p>
