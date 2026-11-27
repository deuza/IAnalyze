# IAnalyze: commands, options and outputs

Version française : [EXAMPLES.fr.md](EXAMPLES.fr.md)

This page is the quick reference of IAnalyze, built like a manual page: every command, every option, and what the terminal shows.

The [README](README.md) explains the installation and everyday use. [TECHNICAL.md](TECHNICAL.md) explains how it works.

## Contents

- [NAME](#name)
- [SYNOPSIS](#synopsis)
- [DESCRIPTION](#description)
- <details><summary><a href="#examples">EXAMPLES</a></summary>

  - [first collection](#first-collection)
  - [collection without typing anything](#collection-without-typing-anything)
  - [game from Lichess](#game-from-lichess)
  - [with the explorer](#with-the-explorer)
  - [for an LLM that does not open zip files](#for-an-llm-that-does-not-open-zip-files)
  - [checking the answer of the LLM](#checking-the-answer-of-the-llm)

  </details>
- <details><summary><a href="#options">OPTIONS</a></summary>

  - [general](#general)
  - [virtual environment](#virtual-environment)
  - [startup questions](#startup-questions)
  - [opening catalog](#opening-catalog)
  - [output](#output)
  - [explorer](#explorer)
  - [engine](#engine)
  - [checker](#checker)

  </details>
- [ERROR MESSAGES](#error-messages)
- [EXIT CODES](#exit-codes)
- [FILES](#files)
- [SEE ALSO](#see-also)

## NAME

**ianalyze.py**: prepares the analysis of a chess game by an LLM.

**verify-analysis.py**: checks the annotated PGN that the LLM returned.

## SYNOPSIS

```text
./ianalyze.py SOURCE [options]
./ianalyze.py --install-venv [--venv PATH]
./ianalyze.py --install-catalog [--catalog DIR]
./ianalyze.py --purge-settings [--settings NAME]
./ianalyze.py --help

./verify-analysis.py ARCHIVE PGN [--summary FILE] [--name NAME] [--prompt-only] [--scope N]
```

SOURCE is a PGN file, the address of a Lichess game or its identifier.

## DESCRIPTION

`ianalyze.py` gathers the PGN of a game, the statistics of the Lichess explorer and the evaluations of Stockfish.\
It writes a zip archive and the prompt that goes with it, to be given to an LLM. It analyzes nothing itself.

`verify-analysis.py` then compares the annotated PGN returned by the LLM with this archive.

### Reading this page

- Each example gives the command, then what the terminal shows.
- The lines that start with a time form the log: they go to standard error.
- The last line, the path of the file produced, is the only one that goes to standard output.
- A line `...` stands for lines left out for brevity.
- `~` stands for your home directory.

### Where the outputs come from

They are real outputs of version 5.0.0, taken on 25 and 27 November 2026 under Linux, with Python 3.13 and Stockfish 16.\
Those of the explorer come from collections of the same day: its statistics change every month, yours will differ.

The evaluations of the engine vary a little too, from one machine to another and from one run to another.\
So that they can be replayed without a Lichess token and without typing anything, most examples add `--no-explorer` and `--no-questions`.

### The games of the examples

All the files quoted on this page are in the `example-games` directory of the repository.

To replay an example as it is, go to this directory and call the scripts one level up: `../ianalyze.py` instead of `./ianalyze.py`, and `../verify-analysis.py` instead of `./verify-analysis.py`.

```bash
cd example-games
```

```bash
../ianalyze.py my-game.pgn --no-explorer --no-questions
```

| File | What it is |
|---|---|
| `my-game.pgn` | an Italian game of nine plies, the one of almost every example |
| `polish-opening.pgn` | an opening that leaves theory early, for the options of the explorer |
| `game-lichess-org.pgn` | a real game of 20 moves, anonymized, as Lichess exports it: the one of the trials of 21 November 2026 (README, section 7) |
| `commented-game.pgn` | another real game from Lichess, 25 moves, anonymized, exported with the analysis of the site: comments, variations and clocks |
| `player-notes.pgn` | the same game, without the analysis of the site, its clocks kept, with three notes of the player: the one of the trials of 27 November 2026 (README, section 7) |
| `game-chess-com.pgn`, `game-chess-mail.pgn`, `game-ajedrezmail.pgn`, `game-lucas-chess.pgn` | four real games, anonymized, as these sites and this program export them |
| `french-notation.pgn`, `two-games.pgn`, `position.pgn`, `unclosed-brace.pgn`, `tag-with-moves.pgn`, `bracket-among-moves.pgn`, `null-move-in-check.pgn` | seven files that the script refuses, for the error messages |
| `llm-annotated.pgn`, `llm-faulty.pgn`, `llm-faulty-words.pgn`, `llm-short.pgn` | four annotated PGNs written for the examples, in place of those an LLM would return |
| `llm-conversation.txt` | the text of a conversation, for the `--summary` option of the checker |

Your own games can be kept wherever you like: the script takes the path of the PGN you give it, and writes the archive in the current directory, or in the one of `--output-dir`.

`my-game.pgn` is an Italian game of nine plies:

```text
[Event "Friendly game"]
[Site "?"]
[Date "2026.11.19"]
[Round "-"]
[White "MyUsername"]
[Black "Opponent"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 *
```

`polish-opening.pgn` leaves theory early, which puts the thresholds of the explorer to the test:

```text
1. b4 g6 2. Bb2 Nf6 3. e3 Bg7 4. Nf3 O-O *
```

## EXAMPLES

These examples assume that IAnalyze is installed (README, section 2). The two installation commands are described further down, at [`--install-venv`](#--install-venv) and at [`--install-catalog`](#--install-catalog).

### First collection

At the very first run in a terminal, the script asks for your settings, then asks the questions about the game.

Enter keeps the value suggested in parentheses.

```bash
./ianalyze.py my-game.pgn --no-explorer
```

```text
[15:29:26] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:29:26] Reading the local PGN: my-game.pgn
[15:29:27] Settings: 3 answer(s) to give only once, kept in ~/IAnalyze/settings.ini.
Your username, or several separated by commas? (Enter: none) MyUsername
Your usual time control: [r]eal time, [c]orrespondence or [u]nknown? (Enter: unspecified) r
  Minutes per player? 15
  Increment in seconds? 10
Your rating, in approximate Elo points? (Enter: unknown) 1300
[15:29:34] Settings saved: ~/IAnalyze/settings.ini
[15:29:34] Startup questions, Enter keeps the suggested value.
Time control of the game: [r]eal time, [c]orrespondence or [u]nknown? (Enter: rapid, 15 minutes + 10 seconds per move)
Scope: the first N moves, or the whole game? (Enter: the whole game)
What do you want to understand in this game? (Enter: left open) the end of the opening
Particular context: time trouble, fatigue, unknown opening, particular opponent? (Enter: nothing)
Other comments to include in the final PGN? (Enter: nothing)
[15:29:42] Working folder: analysis-my-game-20261125-152942
[15:29:42] Stockfish: evaluation of 9 plies, depth 18, multipv 3, threads 4. This is the longest phase.
[15:29:42] Stockfish: ply 1/9 (e4)
[15:29:43] Stockfish: ply 2/9 (e5)
[15:29:44] Stockfish: ply 3/9 (Nf3)
[15:29:45] Stockfish: ply 4/9 (Nc6), less than a minute left
[15:29:46] Stockfish: ply 5/9 (Bc4), less than a minute left
[15:29:47] Stockfish: ply 6/9 (Bc5), less than a minute left
[15:29:47] Stockfish: ply 7/9 (c3), less than a minute left
[15:29:48] Stockfish: ply 8/9 (Nf6), less than a minute left
[15:29:49] Stockfish: ply 9/9 (d3), less than a minute left
[15:29:49] Stockfish: done in 0 min 07 s.
[15:29:49] Summary written: analysis-my-game-20261125-152942/summary.md
[15:29:49] Creating the archive: analysis-my-game-20261125-152942.zip
[15:29:49] Working folder deleted.
[15:29:49] Analysis prompt written: analysis-my-game-20261125-152942.prompt.txt, to be pasted into the conversation, with the archive as an attachment.
analysis-my-game-20261125-152942.zip
```

The settings will not be asked again.\
The last line is the path of the archive, the one before it names the prompt: paste its content into a new conversation with the LLM, and attach the archive.

### Collection without typing anything

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions
```

```text
[15:29:55] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:29:55] Reading the local PGN: my-game.pgn
[15:29:55] Startup questions skipped: option --no-questions.
[15:29:55] Working folder: analysis-my-game-20261125-152955
[15:29:55] Stockfish: evaluation of 9 plies, depth 18, multipv 3, threads 4. This is the longest phase.
[15:29:55] Stockfish: ply 1/9 (e4)
[15:29:56] Stockfish: ply 2/9 (e5)
[15:29:57] Stockfish: ply 3/9 (Nf3)
[15:29:58] Stockfish: ply 4/9 (Nc6), less than a minute left
[15:29:59] Stockfish: ply 5/9 (Bc4), less than a minute left
[15:30:00] Stockfish: ply 6/9 (Bc5), less than a minute left
[15:30:01] Stockfish: ply 7/9 (c3), less than a minute left
[15:30:01] Stockfish: ply 8/9 (Nf6), less than a minute left
[15:30:02] Stockfish: ply 9/9 (d3), less than a minute left
[15:30:03] Stockfish: done in 0 min 07 s.
[15:30:03] Summary written: analysis-my-game-20261125-152955/summary.md
[15:30:03] Creating the archive: analysis-my-game-20261125-152955.zip
[15:30:03] Working folder deleted.
[15:30:03] Analysis prompt written: analysis-my-game-20261125-152955.prompt.txt, to be pasted into the conversation, with the archive as an attachment.
analysis-my-game-20261125-152955.zip
```

### Game from Lichess

By its address, or by its identifier, the 8 characters that follow `lichess.org/`:

```bash
./ianalyze.py https://lichess.org/<identifier>
```

```bash
./ianalyze.py <identifier>
```

The PGN is downloaded, then the collection goes on as for a file.\
The archive carries the identifier of the game: `analysis-<identifier>-<YYYYMMDD-HHMMSS>.zip`.

### With the explorer

Without `--no-explorer`, the script also queries the Lichess explorer.\
It needs the token and the catalog of the openings (README, section 2).

```bash
./ianalyze.py my-game.pgn --no-questions --database masters
```

Section 2 of `summary.md` then receives the table of the explorer, one line per ply queried.

For this game and the masters database, on 25 November 2026:

| # | Move | Side | Pos. games | Played | Rank | Freq. | White score | Top move | Top freq. | Top White score | Opening |
|---:|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|
| 1 | 1 | White | 2997412 | e4 | 1 | 45.6 % | 53.8 % | e4 | 45.6 % | 53.8 % | B00 King's Pawn Game |
| 2 | 1 | Black | 1368125 | e5 | 2 | 24.3 % | 54.4 % | c5 | 45.9 % | 52.8 % | C20 King's Pawn Game |
| 3 | 2 | White | 332635 | Nf3 | 1 | 92.3 % | 54.6 % | Nf3 | 92.3 % | 54.6 % | C40 King's Knight Opening |
| 4 | 2 | Black | 307183 | Nc6 | 1 | 85.8 % | 54.1 % | Nc6 | 85.8 % | 54.1 % | C44 King's Knight Opening: Normal Variation |
| 5 | 3 | White | 264440 | Bc4 | 2 | 19.2 % | 53.0 % | Bb5 | 65.3 % | 54.9 % | C50 Italian Game |
| 6 | 3 | Black | 51257 | Bc5 | 1 | 52.5 % | 52.5 % | Bc5 | 52.5 % | 52.5 % | C50 Italian Game: Giuoco Piano |
| 7 | 4 | White | 26979 | c3 | 1 | 55.6 % | 52.8 % | c3 | 55.6 % | 52.8 % | C53 Italian Game: Classical Variation |
| 8 | 4 | Black | 14997 | Nf6 | 1 | 96.2 % | 52.5 % | Nf6 | 96.2 % | 52.5 % | C54 Italian Game: Classical Variation |
| 9 | 5 | White | 14427 | d3 | 1 | 74.2 % | 53.3 % | d3 | 74.2 % | 53.3 % | C54 Italian Game: Classical Variation, Giuoco Pianissimo |

```text
Stop of the querying: end of the game.
```

### For an LLM that does not open zip files

`--prompt-only` writes a short prompt, to be pasted alone into the conversation. No archive is written.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --prompt-only
```

```text
[22:18:17] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[22:18:17] Reading the local PGN: my-game.pgn
[22:18:17] Startup questions skipped: option --no-questions.
[22:18:17] Working folder: analysis-my-game-20261125-221817
[22:18:17] Stockfish: evaluation of 9 plies, depth 18, multipv 3, threads 4. This is the longest phase.
...
[22:18:24] Summary written: analysis-my-game-20261125-221817/summary.md
[22:18:24] Analysis prompt written: analysis-my-game-20261125-221817.prompt.txt, to be pasted alone into the conversation: it carries the game and the evaluations, no attachment is needed.
[22:18:24] Working folder deleted, no archive is written with --prompt-only.
analysis-my-game-20261125-221817.prompt.txt
```

The prompt carries the instructions, the game, then the evaluations of the engine:

```text
You are an International Master of chess.

Analyze the game below move by move, for a player who wants to improve.
The style is instructive and detailed, in English, and you address the
player as "you", in a friendly tone.
The player had White.
Their rating: about 1300 Elo, declared by the player.
...
Evaluations of Stockfish, depth 18, from White's point of view, after
each move played.
After a weak move come its category, what it loses in centipawns
against the best move, then this best move, its continuation and its
evaluation. "mate" instead of the number: the move misses a mate or
concedes one.
A mate is written "#+2", White mates in two moves, or "#-1", Black
mates in one move. The count reads after the move of the line: "#+0" or
"#-0", this move gives mate.

1. e4           +0.28
1... e5         +0.28
2. Nf3          +0.26
2... Nc6        +0.24
3. Bc4          +0.22
3... Bc5        +0.19
4. c3           +0.15
4... Nf6        +0.21
5. d3           +0.17
```

### Checking the answer of the LLM

`llm-annotated.pgn` stands here for the annotated PGN that an LLM would have returned: it was written for the example.\
The checker compares it with the archive:

```bash
./verify-analysis.py analysis-my-game-20261125-152942.zip llm-annotated.pgn
```

```text
Check of an analysis returned by an LLM
  archive    : analysis-my-game-20261125-152942.zip
  PGN        : llm-annotated.pgn

=== 1. Reading the PGN ===
  OK        file in UTF-8
  OK        a single game in the file
  OK        no illegal move, variations included (0 reading error(s))

=== 2. Main line ===
  OK        main line identical to the original game (9 plies)

=== 3. Format ===
  OK        no line of more than 79 characters
  OK        no brace in a comment
  OK        outside the braces, only moves in standard notation, move numbers, NAGs and the result
  OK        castling written with the letter O, never the digit zero
  OK        no % character in a comment
  OK        no em dash
  OK        no semicolon in a comment
  OK        no suffix notation, NAGs only
  OK        the seven mandatory tags, in order
  OK        the other tags in alphabetical order
  OK        values of the seven tags taken from the original game
  OK        Annotator tag filled in: "Example"
  OK        PlyCount tag: "9", expected "9"
  OK        end marker "*" identical to the Result tag "*"

=== 4. Commented moves ===
  OK        overview of the game before move 1 (3 line(s), 6 to 10 requested)
  INFO      3 move(s) commented out of 9, 15 to 25 aimed for over a whole game
  INFO      0 move(s) carrying a NAG
  OK        the 0 mistake(s) and blunder(s) of Stockfish are all commented on (0 missed)
  OK        no position NAG contrary to the evaluation of the engine
  INFO      quality NAGs: 0 matching the category given by the engine, 0 of another opinion

=== 5. Evaluations quoted in the PGN ===
  INFO      2 evaluation(s) quoted
  OK        all are found in the data of the engine (0 not found)

=== 6. Variations ===
  INFO      1 playable variation(s) on the main line
  OK        no variation of more than 5 plies
  INFO      1 variation starts from a line of the engine, 0 are the LLM's own

=== Totals ===
  failures : 0
  warnings : 0
```

The last line of section 6 varies with the collection: on several threads, Stockfish does not always give the same lines, and on another archive of the same game the variation may be counted as the LLM's own. With `--threads 1`, two collections give the same lines (TECHNICAL, section 9).

A faulty PGN, for its part, sees each of its defects named.\
This one carries a blank line between two moves, a percent sign, a made-up figure and a variation written in a comment:

```bash
./verify-analysis.py analysis-my-game-20261125-152942.zip llm-faulty.pgn --name "Model tried"
```

```text
Check of an analysis returned by an LLM
  model      : Model tried
  archive    : analysis-my-game-20261125-152942.zip
  PGN        : llm-faulty.pgn

=== 1. Reading the PGN ===
...
  FAIL      blank line in the body of the game: python-chess stops reading there and only sees 2 of the 9 plies
            - line 13
...
=== 2. Main line ===
...
=== 3. Format ===
...
  FAIL      no % character in a comment
            - 1. e4
...
=== 4. Commented moves ===
...
=== 5. Evaluations quoted in the PGN ===
...
  FAIL      all are found in the data of the engine (1 not found)
            - 1. e4: +1.50
...
=== 6. Variations ===
...
  FAIL      no playable variation: the only variation is written inside a comment, where it is only text
...
=== Totals ===
  failures : 4
  warnings : 0
```

Another faulty PGN shows the flaws that python-chess reads without a word.\
This one carries a blank line inside a comment, a text written outside the braces, a castling written with zeros, a rank written `#7` and a second game:

```bash
./verify-analysis.py analysis-my-game-20261125-152942.zip llm-faulty-words.pgn --name "Model tried"
```

```text
Check of an analysis returned by an LLM
  model      : Model tried
  archive    : analysis-my-game-20261125-152942.zip
  PGN        : llm-faulty-words.pgn

=== 1. Reading the PGN ===
...
  FAIL      blank line in the body of the game: inside a comment, python-chess reads on, but another PGN reader may take it for the end of the game
            - line 13
  INFO      the following checks are made on the file once these lines are removed
  FAIL      a single game in the file
            - 1 more game after the first one, which alone is checked
...
=== 2. Main line ===
...
=== 3. Format ===
...
  FAIL      outside the braces, only moves in standard notation, move numbers, NAGs and the result
            - line 15: and castling comes next
  FAIL      castling written with the letter O, never the digit zero
            - line 17: 0-0
...
=== 4. Commented moves ===
...
=== 5. Evaluations quoted in the PGN ===
...
  WARNING   1 "#N" written without a sign and not found in the data of the engine: a rank, "mistake #7", rather than a mate?
            - 1. e4: #7
...
=== 6. Variations ===
...
=== Totals ===
  failures : 4
  warnings : 1
```

## OPTIONS

### General

#### `-h, --help`

Shows the full help and the examples.

```bash
./ianalyze.py --help
```

```text
usage: ianalyze.py [-h] [--install-venv] [--venv PATH] [--no-questions]
                   [--usernames LIST] [--settings NAME | --no-settings]
                   [--purge-settings] [--install-catalog] [--catalog DIR]
                   [--output-dir DIR] [--keep-folder] [--prompt FILE]
                   [--no-prompt] [--prompt-only]
                   [--database {lichess,masters}] [--speeds LIST]
                   [--ratings LIST] [--token-file FILE] [--min-games N]
                   [--min-frequency P] [--exhaustive] [--min-moves N]
                   [--max-plies N] [--pause S] [--no-explorer]
                   [--stockfish-moves N] [--depth D] [--multipv K]
                   [--threads N] [--hash MB] [--stockfish PATH]
                   [--pv-length N] [--timeout S] [--debug]
                   [source]

Gathers the material for the analysis of a chess game: PGN, statistics
of the Lichess explorer (database of all players, or masters database
with --database masters) to find the exit from theory, and Stockfish
evaluations of the game. Produces no analysis.

positional arguments:
  source                local PGN file, Lichess URL, or game identifier of
                        eight or twelve characters

options:
  -h, --help            show this help message and exit
  --timeout S           maximum network delay, in seconds (default: 30)
  --debug               lets the full traceback of unexpected errors come up
...
```

#### `--timeout S`

*Default: `30`*

Maximum network delay per request, in seconds: PGN export, explorer, download of the catalog.\
It is at least 1, with `--install-catalog` too, which downloads as well.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --timeout 60
```

Nothing changes on screen without a network request: the timeout only applies to them.\
The log is the same as in the section [Collection without typing anything](#collection-without-typing-anything).

#### `--debug`

Lets the full traceback of an unexpected error come up, with the token redacted.\
Without this option, only a one-line message is shown.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --debug
```

Without an unexpected error, nothing changes. The log is the same as in the section [Collection without typing anything](#collection-without-typing-anything).

### Virtual environment

#### `--install-venv`

Creates the virtual environment if it is missing, installs or updates python-chess in it, then exits.\
It can be run again safely.

The first time:

```bash
./ianalyze.py --install-venv
```

```text
[15:28:01] Creating the virtual environment: ~/IAnalyze/local/venv
[15:28:03] Installing python-chess in the virtual environment.
[15:28:07] Virtual environment ready: ~/IAnalyze/local/venv/bin/python3
```

The following times:

```bash
./ianalyze.py --install-venv
```

```text
[15:28:41] Virtual environment already present: ~/IAnalyze/local/venv
[15:28:41] Installing python-chess in the virtual environment.
[15:28:42] Virtual environment ready: ~/IAnalyze/local/venv/bin/python3
```

After an interrupted creation, by Ctrl-C for instance, the environment is left without pip: the script rebuilds it before installing python-chess.

```bash
./ianalyze.py --install-venv
```

```text
[15:28:17] Virtual environment incomplete, pip does not answer: rebuilding it: ~/IAnalyze/local/venv
[15:28:19] Installing python-chess in the virtual environment.
[15:28:20] Virtual environment ready: ~/IAnalyze/local/venv/bin/python3
```

A directory without `pyvenv.cfg`, such as a `--venv /usr` given by mistake, is never taken for an environment to rebuild: nothing is erased in it.

#### `--venv PATH`

*Default: `local/venv`, in the application folder*

Location of the virtual environment, at installation as in use.

```bash
./ianalyze.py --install-venv --venv ~/venv/chess
```

```text
[15:34:04] Creating the virtual environment: ~/venv/chess
[15:34:06] Installing python-chess in the virtual environment.
[15:34:07] Virtual environment ready: ~/venv/chess/bin/python3
```

A directory that is not a virtual environment, not empty and without `pyvenv.cfg`, is refused before any installation: pip does not run on the Python it contains, and nothing is added to it.

```bash
./ianalyze.py --install-venv --venv /usr
```

```text
--venv: /usr is not a virtual environment, the directory is not empty and has no pyvenv.cfg: nothing is changed. Give a new or empty directory, or an existing virtual environment.
```

A path that exists without being a directory, a file given by mistake, is refused too, with its own message:

```bash
./ianalyze.py --install-venv --venv ~/chess-venv
```

```text
--venv: ~/chess-venv exists and is not a directory: nothing is changed. Give a new or empty directory, or an existing virtual environment.
```

The same option then serves at each collection, and the log names the environment used:

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --venv ~/venv/chess
```

```text
[15:34:07] Virtual environment: restarting with ~/venv/chess/bin/python3
[15:34:07] Reading the local PGN: my-game.pgn
...
```

### Startup questions

#### `--no-questions`

Asks no question, neither side nor context.\
Nothing is assumed in your place: the prompt then tells the LLM that your answers were not collected, and the LLM asks you the questions before analyzing.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions
```

```text
...
[15:29:55] Reading the local PGN: my-game.pgn
[15:29:55] Startup questions skipped: option --no-questions.
...
```

#### `--usernames LIST`

*Default: those of your settings*

Your player names, separated by commas, looked up ignoring case in White and Black to deduce your side: each one as the whole name or as a run of its words, never as a part of a word. `Max` is found in `Max Power`, not in `Maxime` nor in `Max_Power`.\
The first one serves to fill an empty tag. The option replaces the usernames of the settings file for one run.

`my-game.pgn` opposes MyUsername, with White, to Opponent.\
With the username of the latter, the side kept for the prompt changes:

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --usernames Opponent
```

```bash
grep "side in this game" analysis-my-game-20261125-153415.prompt.txt
```

```text
- side in this game: Black
```

#### `--settings NAME`

*Default: `settings.ini`*

Name of the settings file to use instead of yours: usernames, usual time control and rating (README, section 2).\
It is a file name ending in `.ini`, without a folder and not starting with a dot: every settings file is kept at the root of the application folder, next to `settings.ini`.

If the file does not exist yet, the script asks for a confirmation, then asks its three questions in the terminal, and creates it.\
This is the way to keep several profiles on one account, one per player for instance.

```bash
./ianalyze.py my-game.pgn --no-explorer --settings player2.ini
```

```text
[15:31:58] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:31:58] Reading the local PGN: my-game.pgn
Settings: player2.ini does not exist yet in ~/IAnalyze. Create it? [y/n] y
[15:32:00] Settings: 3 answer(s) to give only once, kept in ~/IAnalyze/player2.ini.
Your username, or several separated by commas? (Enter: none) Player2
Your usual time control: [r]eal time, [c]orrespondence or [u]nknown? (Enter: unspecified) u
Your rating, in approximate Elo points? (Enter: unknown) 1800
[15:32:05] Settings saved: ~/IAnalyze/player2.ini
[15:32:05] Startup questions, Enter keeps the suggested value.
Did you play White or Black? [w/b] b
Time control of the game: [r]eal time, [c]orrespondence or [u]nknown? (Enter: unspecified)
Scope: the first N moves, or the whole game? (Enter: the whole game)
What do you want to understand in this game? (Enter: left open)
Particular context: time trouble, fatigue, unknown opening, particular opponent? (Enter: nothing)
Other comments to include in the final PGN? (Enter: nothing)
[15:32:14] Working folder: analysis-my-game-20261125-153214
...
[15:32:20] Summary written: analysis-my-game-20261125-153214/summary.md
[15:32:20] Creating the archive: analysis-my-game-20261125-153214.zip
[15:32:20] Working folder deleted.
[15:32:20] Analysis prompt written: analysis-my-game-20261125-153214.prompt.txt, to be pasted into the conversation, with the archive as an attachment.
analysis-my-game-20261125-153214.zip
```

Here the username of the second player does not appear in the game: the script therefore asks for their side.\
The following runs with this file do not ask for the settings again.

- A key missing from the file is asked once, then saved.
- A key that is present, even empty, is never asked again.
- An unreadable time control or rating is asked again.
- The keys and the sections that you add are kept.

A malformed file stops the script with a message.

A misspelled name starts no new file: answering `n` stops the script before anything is written or collected, with the exit code 1.

```bash
./ianalyze.py my-game.pgn --no-explorer --settings player3.ini
```

```text
[15:32:25] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:32:25] Reading the local PGN: my-game.pgn
Settings: player3.ini does not exist yet in ~/IAnalyze. Create it? [y/n] n
Nothing done: check the name given to --settings, or use --no-settings to run without settings.
```

An existing file that is not a settings file, without the `[player]` section or the `[joueur]` section of the former format, is never rewritten: the answers only serve the current run, a warning says why, and the file stays as it was.\
Here `notes.ini`, at the root of the application folder, is an INI file that has nothing to do with IAnalyze:

```bash
./ianalyze.py my-game.pgn --no-explorer --settings notes.ini
```

```text
[15:41:00] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:41:00] Reading the local PGN: my-game.pgn
[15:41:00] Settings: 3 answer(s) to give only once, kept in ~/IAnalyze/notes.ini.
Your username, or several separated by commas? (Enter: none) MyUsername
Your usual time control: [r]eal time, [c]orrespondence or [u]nknown? (Enter: unspecified) r
  Minutes per player? 15
  Increment in seconds? 10
Your rating, in approximate Elo points? (Enter: unknown) 1300
[15:41:07] Warning: settings not saved in ~/IAnalyze/notes.ini: it is not a settings file, it does not carry the [player] section.
[15:41:07] Startup questions, Enter keeps the suggested value.
...
analysis-my-game-20261125-154115.zip
```

A path is refused, even inside the application folder, with the exit code 2:

```bash
./ianalyze.py my-game.pgn --settings ~/IAnalyze/settings.ini
```

```text
usage: ianalyze.py [-h] [--install-venv] [--venv PATH] [--no-questions]
...
ianalyze.py: error: --settings: ~/IAnalyze/settings.ini is not a settings name. Give a file name ending in .ini, without a folder and not starting with a dot: every settings file is kept in ~/IAnalyze. To run without settings, use --no-settings.
```

#### `--no-settings`

For this run only, the settings file is neither read nor written, and its questions are not asked.\
The side is asked, or deduced from `--usernames`. The rating comes from the Elo tag of your side, and the time control from the TimeControl tag or from the question about the game, which then suggests "unspecified".

```bash
./ianalyze.py my-game.pgn --no-explorer --no-settings
```

```text
[15:32:27] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:32:27] Settings neither read nor written: option --no-settings.
[15:32:27] Reading the local PGN: my-game.pgn
[15:32:28] Startup questions, Enter keeps the suggested value.
Did you play White or Black? [w/b] w
Time control of the game: [r]eal time, [c]orrespondence or [u]nknown? (Enter: unspecified)
Scope: the first N moves, or the whole game? (Enter: the whole game)
What do you want to understand in this game? (Enter: left open)
Particular context: time trouble, fatigue, unknown opening, particular opponent? (Enter: nothing)
Other comments to include in the final PGN? (Enter: nothing)
[15:32:37] Working folder: analysis-my-game-20261125-153237
...
[15:32:44] Summary written: analysis-my-game-20261125-153237/summary.md
[15:32:44] Creating the archive: analysis-my-game-20261125-153237.zip
[15:32:44] Working folder deleted.
[15:32:44] Analysis prompt written: analysis-my-game-20261125-153237.prompt.txt, to be pasted into the conversation, with the archive as an attachment.
analysis-my-game-20261125-153237.zip
```

The option excludes `--settings`, whatever the name given, and `--purge-settings`. The exit code is then 2:

```bash
./ianalyze.py my-game.pgn --no-settings --settings player2.ini
```

```text
usage: ianalyze.py [-h] [--install-venv] [--venv PATH] [--no-questions]
...
ianalyze.py: error: argument --settings: not allowed with argument --no-settings
```

#### `--purge-settings`

Deletes the settings file, then exits. No game is expected.\
Your answers will be asked again at the next collection run in a terminal.

With `--settings`, it is the named file that is deleted:

```bash
./ianalyze.py --purge-settings --settings player2.ini
```

```text
[15:41:22] Settings deleted: ~/IAnalyze/player2.ini. They will be asked again at the next collection run in a terminal.
```

A missing file is not an error, a directory is refused.\
A file that is not a settings file is refused too: only a file carrying the `[player]` section, or an empty file, is deleted.

```bash
./ianalyze.py --purge-settings
```

```text
[15:41:23] Settings deleted: ~/IAnalyze/settings.ini. They will be asked again at the next collection run in a terminal.
```

Run again straight away:

```bash
./ianalyze.py --purge-settings
```

```text
[15:41:23] No settings file to delete: ~/IAnalyze/settings.ini
```

### Opening catalog

#### `--install-catalog`

Downloads the catalog of the openings of Lichess, checks it, then exits.\
Running the option again updates it. A failure leaves the former catalog in place.

```bash
./ianalyze.py --install-catalog
```

```text
[15:28:42] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:28:42] Downloading the catalog: https://raw.githubusercontent.com/lichess-org/chess-openings/master/a.tsv
[15:28:42] Downloading the catalog: https://raw.githubusercontent.com/lichess-org/chess-openings/master/b.tsv
[15:28:43] Downloading the catalog: https://raw.githubusercontent.com/lichess-org/chess-openings/master/c.tsv
[15:28:43] Downloading the catalog: https://raw.githubusercontent.com/lichess-org/chess-openings/master/d.tsv
[15:28:44] Downloading the catalog: https://raw.githubusercontent.com/lichess-org/chess-openings/master/e.tsv
[15:28:44] Catalog installed: 3865 lines, 3865 named positions, 7982 known positions, in ~/IAnalyze/local/catalog.tsv
```

#### `--catalog DIR`

*Default: `local/`, in the application folder*

Directory of the local catalog, at installation as in use.

```bash
./ianalyze.py --install-catalog --catalog ~/chess/catalog
```

```text
[15:34:22] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:34:22] Downloading the catalog: https://raw.githubusercontent.com/lichess-org/chess-openings/master/a.tsv
...
[15:34:24] Catalog installed: 3865 lines, 3865 named positions, 7982 known positions, in ~/chess/catalog/catalog.tsv
```

The same option then serves at each collection:

```bash
./ianalyze.py my-game.pgn --catalog ~/chess/catalog
```

### Output

Without any of these options, the script writes two files in the current directory: the archive and the full prompt.

| You add | The script writes | What you do with it |
|---|---|---|
| nothing | the archive `.zip` and the full prompt `.prompt.txt` | you paste the prompt into the conversation and attach the archive |
| `--prompt-only` | the short prompt, without an archive | you paste the prompt, without attaching anything |
| `--no-prompt` | the archive, without a prompt | you write your request to the LLM yourself |
| `--prompt FILE` | the archive and a prompt drawn from your own template | you paste the prompt and attach the archive |

#### `--output-dir DIR`

*Default: `.`, the current directory*

Directory where the script writes its files. It is created if need be.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --output-dir ~/analyses
```

```text
[15:34:24] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:34:24] Reading the local PGN: my-game.pgn
...
[15:34:24] Working folder: ~/analyses/analysis-my-game-20261125-153424
...
[15:34:32] Summary written: ~/analyses/analysis-my-game-20261125-153424/summary.md
[15:34:32] Creating the archive: ~/analyses/analysis-my-game-20261125-153424.zip
[15:34:32] Working folder deleted.
[15:34:32] Analysis prompt written: ~/analyses/analysis-my-game-20261125-153424.prompt.txt, to be pasted into the conversation, with the archive as an attachment.
~/analyses/analysis-my-game-20261125-153424.zip
```

```bash
ls ~/analyses
```

```text
analysis-my-game-20261125-153424.prompt.txt
analysis-my-game-20261125-153424.zip
```

#### `--keep-folder`

During the collection, the script puts its files in a working folder, `analysis-<label>-<YYYYMMDD-HHMMSS>`.\
It then compresses it into a zip, then deletes it.

With this option, the folder stays next to the archive.\
It is useful when the LLM does not open zip files: you then send it the files of the folder.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --keep-folder
```

```text
[15:34:32] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:34:32] Reading the local PGN: my-game.pgn
...
[15:34:32] Working folder: analysis-my-game-20261125-153432
...
[15:34:40] Summary written: analysis-my-game-20261125-153432/summary.md
[15:34:40] Creating the archive: analysis-my-game-20261125-153432.zip
[15:34:40] Folder kept on request: analysis-my-game-20261125-153432
[15:34:40] Analysis prompt written: analysis-my-game-20261125-153432.prompt.txt, to be pasted into the conversation, with the archive as an attachment.
analysis-my-game-20261125-153432.zip
```

The folder carries the files of the archive:

```bash
ls -R analysis-my-game-20261125-153432/ | grep -v "^$"
```

```text
analysis-my-game-20261125-153432/:
collection.json
game.pgn
stockfish
summary.md
analysis-my-game-20261125-153432/stockfish:
evaluations.json
```

#### `--prompt-only`

Writes a short prompt, to be pasted alone into the conversation, without an attachment: a few instructions, the game, then the evaluations of Stockfish.

It is the road to take with a free account, or with an LLM that does not open zip files or does not run code (README, section 7).\
The annotated PGN is requested in a code block.

No archive is written: the prompt is the only file produced, and its path is what is written on standard output.\
For the archive and its data, run a collection without this option.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --prompt-only
```

```text
[22:18:17] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[22:18:17] Reading the local PGN: my-game.pgn
...
[22:18:17] Working folder: analysis-my-game-20261125-221817
...
[22:18:24] Summary written: analysis-my-game-20261125-221817/summary.md
[22:18:24] Analysis prompt written: analysis-my-game-20261125-221817.prompt.txt, to be pasted alone into the conversation: it carries the game and the evaluations, no attachment is needed.
[22:18:24] Working folder deleted, no archive is written with --prompt-only.
analysis-my-game-20261125-221817.prompt.txt
```

Add `--keep-folder` if you intend to have the answer of the LLM checked by `verify-analysis.py`: the working folder then stays next to the prompt.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --prompt-only --keep-folder
```

```text
[15:34:40] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:34:40] Reading the local PGN: my-game.pgn
...
[15:34:40] Working folder: analysis-my-game-20261125-153440
...
[15:34:49] Summary written: analysis-my-game-20261125-153440/summary.md
[15:34:49] Analysis prompt written: analysis-my-game-20261125-153440.prompt.txt, to be pasted alone into the conversation: it carries the game and the evaluations, no attachment is needed.
[15:34:49] Folder kept on request: analysis-my-game-20261125-153440
analysis-my-game-20261125-153440.prompt.txt
```

Excludes `--no-prompt`.

#### `--no-prompt`

Writes only the archive, without a prompt. Excludes `--prompt` and `--prompt-only`.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --no-prompt
```

```text
[15:34:49] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:34:49] Reading the local PGN: my-game.pgn
...
[15:34:49] Working folder: analysis-my-game-20261125-153449
...
[15:34:56] Summary written: analysis-my-game-20261125-153449/summary.md
[15:34:56] Creating the archive: analysis-my-game-20261125-153449.zip
[15:34:56] Working folder deleted.
analysis-my-game-20261125-153449.zip
```

#### `--prompt FILE`

*Default: `prompt-template.txt`, next to the script*

To be used only if you wrote your own prompt template.

The prompt of a game is not a fixed text. The script builds it from a template:\
a text file whose blanks it fills, your username, your side or the name of the archive, and of which it keeps only the passages useful to this game.

This option makes it take your template instead of the one of the repository.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --prompt ~/my-template.txt
```

```text
[15:34:56] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:34:57] Reading the local PGN: my-game.pgn
...
[15:34:57] Working folder: analysis-my-game-20261125-153457
...
[15:35:04] Summary written: analysis-my-game-20261125-153457/summary.md
[15:35:04] Creating the archive: analysis-my-game-20261125-153457.zip
[15:35:04] Working folder deleted.
[15:35:04] Analysis prompt written: analysis-my-game-20261125-153457.prompt.txt, to be pasted into the conversation, with the archive as an attachment.
analysis-my-game-20261125-153457.zip
```

The file must exist.\
To write a template, start from a copy of `prompt-template.txt`: what it may contain is described in [TECHNICAL.md](TECHNICAL.md), section 12.

With `--prompt-only`, the default template is `prompt-only-template.txt`, and it is the one to start from.

### Explorer

These options require the token and the catalog.\
The extracts come from section 2 of `summary.md`, taken on 25 November 2026.

#### `--database {lichess,masters}`

*Default: `lichess`*

Database queried:

- `lichess`: the rated games of all the players of the site, the database of <https://lichess.org/opening>
- `masters`: the games of masters

```bash
./ianalyze.py polish-opening.pgn --no-questions --database lichess
```

| # | Move | Side | Pos. games | Played | Rank | Freq. | White score | Top move | Top freq. | Top White score | Opening |
|---:|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|
| 1 | 1 | White | 7676304687 | b4 | 11 | 0.4 % | 53.4 % | e4 | 58.5 % | 51.3 % | A00 Polish Opening |
| 2 | 1 | Black | 33336712 | g6 | 5 | 4.9 % | 55.0 % | e5 | 34.5 % | 54.7 % | - |
| 3 | 2 | White | 1638628 | Bb2 | 1 | 92.5 % | 55.9 % | Bb2 | 92.5 % | 55.9 % | - |
| 4 | 2 | Black | 1514424 | Nf6 | 1 | 67.6 % | 49.5 % | Nf6 | 67.6 % | 49.5 % | A00 Polish Opening: King's Indian Variation |
| 5 | 3 | White | 2055319 | e3 | 1 | 24.5 % | 49.2 % | e3 | 24.5 % | 49.2 % | - |
| 6 | 3 | Black | 510542 | Bg7 | 1 | 96.6 % | 49.1 % | Bg7 | 96.6 % | 49.1 % | - |
| 7 | 4 | White | 493481 | Nf3 | 1 | 39.5 % | 49.9 % | Nf3 | 39.5 % | 49.9 % | - |
| 8 | 4 | Black | 334723 | O-O | 1 | 69.6 % | 49.7 % | O-O | 69.6 % | 49.7 % | - |

```text
Stop of the querying: end of the game.
...
First move below the threshold of 10.0 % outside the catalog: **Black plays g6** at move **1** (ply 2).
...
- frequency of the move played: 4.9 % (1640131 games out of 33336712)
```

The same game in the masters database, where it is much rarer:

```bash
./ianalyze.py polish-opening.pgn --no-questions --database masters
```

| # | Move | Side | Pos. games | Played | Rank | Freq. | White score | Top move | Top freq. | Top White score | Opening |
|---:|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|
| 1 | 1 | White | 2997412 | b4 | 9 | 0.1 % | 46.7 % | e4 | 45.6 % | 53.8 % | A00 Polish Opening |
| 2 | 1 | Black | 2269 | g6 | 10 | 0.5 % | 45.8 % | e5 | 53.2 % | 45.1 % | - |

```text
Stop of the querying: insufficient sample at ply 3: 12 games for a threshold of 50.
```

#### `--speeds LIST`

*Default: `bullet,blitz,rapid,classical,correspondence`*

`lichess` database only.

Speeds kept, separated by commas, among:

- `ultraBullet`
- `bullet`
- `blitz`
- `rapid`
- `classical`
- `correspondence`

Case is tolerated, duplicates are removed.

#### `--ratings LIST`

*Default: `1000,1200,1400,1600,1800,2000,2200,2500`*

`lichess` database only.\
Rating bands kept among 0, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2500.

Each band runs from its value to the next one: 0 covers 0 to 999 (shown as "400" on the site), 2500 everything above.\
A game is placed according to the average of the ratings of its two players.

The default filters, plus the start date set to January 2017, are those of <https://lichess.org/opening>: you find the same percentages there.\
Both filters together, on the slow games of the players rated under 1200:

```bash
./ianalyze.py polish-opening.pgn --no-questions --min-moves 0 --speeds rapid,classical --ratings 0,1000
```

| # | Move | Side | Pos. games | Played | Rank | Freq. | White score | Top move | Top freq. | Top White score | Opening |
|---:|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|
| 1 | 1 | White | 222375359 | b4 | 14 | 0.2 % | 46.9 % | e4 | 68.6 % | 52.6 % | A00 Polish Opening |
| 2 | 1 | Black | 504056 | g6 | 7 | 2.9 % | 47.2 % | e5 | 49.7 % | 46.1 % | - |

#### `--token-file FILE`

*Default: `~/.lichess_token`*

File containing the personal token, and nothing else.\
If the file is missing, the script stops before any request:

```bash
./ianalyze.py my-game.pgn --no-questions --token-file ~/.test-token
```

```text
[15:38:19] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:38:19] Reading the local PGN: my-game.pgn
Token missing: ~/.test-token not found.
```

#### `--min-games N`

*Default: `50`*

Stop when the position counts fewer than N games in the database.\
With the default threshold, 50, the Polish stops at the third ply in the masters database:

```bash
./ianalyze.py polish-opening.pgn --no-questions --database masters
```

```text
Stop of the querying: insufficient sample at ply 3: 12 games for a threshold of 50.
```

For a more demanding threshold:

```bash
./ianalyze.py my-game.pgn --no-questions --min-games 200
```

#### `--min-frequency P`

*Default: `10.0`*

A move played in fewer than P % of the games of the position is rare.\
A rare move that leads out of the opening catalog is an exit from theory. If it stays in a named line, it is not one.

0 disables the criterion.

```bash
./ianalyze.py polish-opening.pgn --no-questions --min-moves 0
```

```text
Stop of the querying: exit from theory at ply 2: g6 played at 4.9 %, threshold 10.0 %, outside the catalog.
```

With 0, no move is an exit from theory any more:

```bash
./ianalyze.py polish-opening.pgn --no-questions --min-moves 0 --min-frequency 0
```

```text
Stop of the querying: end of the game.
```

#### `--min-moves N`

*Default: `6`*

No stop on frequency before the end of move N, that is 2N plies.\
The table thus covers the start of the game even after an early exit.

The game threshold stays active, and the first exit is noted even inside the window. 0 stops at the first exit.

With the default value, the table of the Polish goes to the end of the game, although 1... g6 is an exit from theory: see `--database`, above.\
With 0, it stops on this move:

```bash
./ianalyze.py polish-opening.pgn --no-questions --min-moves 0
```

```text
Stop of the querying: exit from theory at ply 2: g6 played at 4.9 %, threshold 10.0 %, outside the catalog.
```

#### `--exhaustive`

Ignores both thresholds for the stop: the querying goes down as long as the database knows the position.\
The first exit stays noted.

```bash
./ianalyze.py polish-opening.pgn --no-questions --exhaustive
```

```text
Stop of the querying: end of the game.
```

#### `--max-plies N`

*Default: `60`*

Cap on the plies queried, a safeguard always active.

```bash
./ianalyze.py my-game.pgn --no-questions --exhaustive --max-plies 4
```

```text
Stop of the querying: cap of 4 plies reached (option --max-plies).
```

#### `--pause S`

*Default: `2.0`*

Pause between two requests to the explorer, 2 seconds at least.\
With a pause of 3 seconds, visible at the time of each line:

```bash
./ianalyze.py my-game.pgn --no-questions --pause 3 --max-plies 3
```

```text
[15:39:43] Explorer: ply 1 (e4)
[15:39:43] Explorer: ply 2 (e5)
[15:39:46] Explorer: ply 3 (Nf3)
```

#### `--no-explorer`

Skips the explorer collection: no network to the explorer, no token, no catalog required.\
The log then goes from reading the game to the engine, without an "Explorer" line:

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions
```

```text
[15:29:55] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:29:55] Reading the local PGN: my-game.pgn
[15:29:55] Startup questions skipped: option --no-questions.
[15:29:55] Working folder: analysis-my-game-20261125-152955
[15:29:55] Stockfish: evaluation of 9 plies, depth 18, multipv 3, threads 4. This is the longest phase.
[15:29:55] Stockfish: ply 1/9 (e4)
...
```

### Engine

The Stockfish evaluation is part of every collection: the binary is checked before anything is written.

#### `--stockfish-moves N`

*Default: `0`*

Limits the engine to the first N full moves, that is 2N plies. 0 analyzes the whole game.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --stockfish-moves 3
```

```text
...
[15:35:05] Stockfish: evaluation of 6 plies, depth 18, multipv 3, threads 4. This is the longest phase.
...
```

#### `--depth D`

*Default: `18`*

Search depth per position, from 1 to 60.\
The computing time grows very fast with it: beyond 60, a single position would keep the engine busy for hours!

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --depth 12
```

```text
...
[15:35:10] Stockfish: evaluation of 9 plies, depth 12, multipv 3, threads 4. This is the longest phase.
...
```

#### `--multipv K`

*Default: `3`*

Number of best moves that the engine gives for each position.\
With 3, the summary shows, next to each move of the game, the three moves that Stockfish preferred.

If the move played is not one of them, the script has it evaluated separately, to measure what it loses.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --multipv 5
```

```text
...
[15:35:12] Stockfish: evaluation of 9 plies, depth 18, multipv 5, threads 4. This is the longest phase.
...
```

#### `--threads N`

*Default: the number of processors of the machine*

Number of processors that Stockfish uses at the same time. Lower it to keep the machine available during the computation.

#### `--hash MB`

*Default: `256`*

Memory that Stockfish reserves for its computations, in megabytes. The default value suits everyday use.

Both together.\
The log names the number of threads, not the size of the table:

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --threads 2 --hash 128
```

```text
...
[15:35:26] Stockfish: evaluation of 9 plies, depth 18, multipv 3, threads 2. This is the longest phase.
...
```

These three settings, MultiPV, Threads and Hash for Stockfish, are explained in [TECHNICAL.md](TECHNICAL.md), section 9.

#### `--stockfish PATH`

*Default: the binary found in the PATH, otherwise `/usr/games/stockfish` under Debian and `/opt/homebrew/bin/stockfish` under macOS*

Binary of the engine.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --stockfish /usr/games/stockfish
```

The log is the same as in the section [Collection without typing anything](#collection-without-typing-anything).

A path that leads nowhere stops the script before the collection:

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --stockfish /nowhere
```

```text
[15:35:45] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:35:45] Reading the local PGN: my-game.pgn
Stockfish not found: /nowhere. Install it (apt install stockfish, in /usr/games), or give its path with --stockfish. The engine evaluation is part of every collection.
```

#### `--pv-length N`

*Default: `5`*

Plies of principal variation reproduced in the summary, 0 for the whole variation.

The full variations stay in `stockfish/evaluations.json`.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --pv-length 2 --keep-folder
```

In `summary.md`, the variations are then cut at two plies:

```text
### 3a. Principal variations of the engine

Variations cut at 2 plies; the full variations are in `stockfish/evaluations.json`.

- Ply 1, White plays e4 (position before the move)
    - 1st, played (+0.35): 1. e4 e5
    - 2nd (+0.30): 1. d4 Nf6
    - 3rd (+0.27): 1. Nf3 e6
...
```

### Checker

The options that follow are those of `verify-analysis.py`.

#### `ARCHIVE PGN`

The archive written by `ianalyze.py`, zip or unzipped folder, then the annotated PGN returned by the LLM.\
A dash in place of the PGN signals that the LLM returned none.

The folder may also be the one that contains the collection, if it contains only one complete collection: the report names it.\
See [Checking the answer of the LLM](#checking-the-answer-of-the-llm) for a full report.

#### `--name NAME`

Name of the model tried, repeated at the head of the report.

```bash
./verify-analysis.py analysis-my-game-20261125-152942.zip llm-faulty.pgn --name "Model tried"
```

```text
Check of an analysis returned by an LLM
  model      : Model tried
  archive    : analysis-my-game-20261125-152942.zip
  PGN        : llm-faulty.pgn

...
```

#### `--summary FILE`

The conversation with the LLM, copied into a text file.\
The positions and the evaluations that it quotes are then checked too, in two more sections.

```bash
./verify-analysis.py analysis-my-game-20261125-152942.zip llm-annotated.pgn --summary llm-conversation.txt
```

```text
Check of an analysis returned by an LLM
  archive    : analysis-my-game-20261125-152942.zip
  PGN        : llm-annotated.pgn
...
=== 7. Conversation: positions quoted, language ===
  OK        no em dash in the conversation (0 found)
  OK        2 FEN quoted, two requested
  OK        all the FEN are valid positions
  OK        all come from a position of the game

=== 8. Evaluations quoted in the conversation ===
  INFO      2 evaluation(s) quoted
  OK        all are found in the data of the engine (0 not found)

=== Totals ===
  failures : 0
  warnings : 0
```

Without a returned PGN, only the conversation is checked:

```bash
./verify-analysis.py analysis-my-game-20261125-152942.zip - --summary llm-conversation.txt
```

```text
Check of an analysis returned by an LLM
  archive    : analysis-my-game-20261125-152942.zip
  PGN        : -

=== 1. Reading the PGN ===
  FAIL      no PGN returned: checks 2 to 6 do not apply

=== 7. Conversation: positions quoted, language ===
  OK        no em dash in the conversation (0 found)
  OK        2 FEN quoted, two requested
  OK        all the FEN are valid positions
  OK        all come from a position of the game

=== 8. Evaluations quoted in the conversation ===
  INFO      2 evaluation(s) quoted
  OK        all are found in the data of the engine (0 not found)

=== Totals ===
  failures : 1
  warnings : 0
```

#### `--prompt-only`, for the checker

The PGN answers the short prompt of `ianalyze.py --prompt-only`.\
This prompt asks for less than the full prompt: the checks that it does not ground are skipped.

The archive is here the folder kept by `--prompt-only --keep-folder`.

```bash
./verify-analysis.py analysis-my-game-20261125-153440 llm-short.pgn --prompt-only
```

```text
Check of an analysis returned by an LLM
  archive    : analysis-my-game-20261125-153440
  PGN        : llm-short.pgn
  prompt     : short (--prompt-only), checks limited to what it asks for

=== 1. Reading the PGN ===
  OK        file in UTF-8
  OK        a single game in the file
  OK        no illegal move, variations included (0 reading error(s))

=== 2. Main line ===
  OK        main line identical to the original game (9 plies)

=== 3. Format ===
  OK        no brace in a comment
  OK        outside the braces, only moves in standard notation, move numbers, NAGs and the result
  OK        the mandatory tags of the original game, in the same order
  OK        values of the seven tags taken from the original game
  OK        end marker "*" identical to the Result tag "*"

=== 4. Commented moves ===
  INFO      3 move(s) commented out of 9
  INFO      0 move(s) carrying a NAG
  OK        the 0 mistake(s) and blunder(s) of Stockfish are all commented on (0 missed)

=== 5. Evaluations quoted in the PGN ===
  INFO      0 evaluation(s) quoted
  OK        all are found in the data of the engine (0 not found)

=== 6. Variations ===
  INFO      0 playable variation(s) on the main line

=== Totals ===
  failures : 0
  warnings : 0
```

#### `--scope N`

The scope agreed with the LLM, in moves.\
The mistakes and blunders played after move N are not expected in the PGN: the prompt limits the comments to the scope.

Without this option, the scope is the one of your answer to the startup question, read in the archive.\
It is useful when the scope was set in the conversation.

```bash
./verify-analysis.py analysis-my-game-20261125-152942.zip llm-annotated.pgn --scope 3
```

```text
...
=== 4. Commented moves ===
  OK        overview of the game before move 1 (3 line(s), 6 to 10 requested)
  INFO      3 move(s) commented out of 9, 15 to 25 aimed for over a whole game
  INFO      0 move(s) carrying a NAG
  INFO      agreed scope: the first 3 moves, the mistakes and blunders played beyond are not expected
  OK        the 0 mistake(s) and blunder(s) of Stockfish are all commented on (0 missed)
  OK        no position NAG contrary to the evaluation of the engine
  INFO      quality NAGs: 0 matching the category given by the engine, 0 of another opinion
...
```

## ERROR MESSAGES

An error message is not timestamped: it is the last line, and the exit code is 1 or 2.

### File not found

```bash
./ianalyze.py missing-game.pgn
```

```text
[15:35:52] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
PGN file not found: missing-game.pgn
```

### Game written in French notation

The moves must be written in English notation: K, Q, R, B, N.

```bash
./ianalyze.py french-notation.pgn --no-explorer --no-questions
```

```text
[15:35:52] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:35:52] Reading the local PGN: french-notation.pgn
Corrupt PGN: "Cf3", line 1, is neither a move in English notation (K, Q, R, B, N) nor another PGN element. A game written in French notation or with figurines must be converted, free text placed between braces.
```

### Result repeated at the end of the file

This is not an error: the export of chess-mail.com writes the result twice, and the second one is ignored. The log says so, and the collection goes on.

```bash
./ianalyze.py game-chess-mail.pgn --no-explorer --no-questions
```

```text
[15:35:53] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:35:53] Reading the local PGN: game-chess-mail.pgn
[15:35:53] Result repeated at the end of the file, after the game: ignored.
[15:35:53] Startup questions skipped: option --no-questions.
...
analysis-game-chess-mail-20261125-153553.zip
```

### Several games in the file

```bash
./ianalyze.py two-games.pgn --no-explorer --no-questions
```

```text
[15:36:57] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:36:57] Reading the local PGN: two-games.pgn
The PGN contains 2 games: put the one to analyze in a separate file.
```

### Game that starts from a position

```bash
./ianalyze.py position.pgn --no-explorer --no-questions
```

```text
[15:36:57] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:36:57] Reading the local PGN: position.pgn
The game does not start from the initial position, it starts from a FEN tag. IAnalyze analyzes a whole game, from the first move to the last: to study a position, load it into an analysis board.
```

### Comment never closed

```bash
./ianalyze.py unclosed-brace.pgn --no-explorer --no-questions
```

```text
[15:36:57] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:36:57] Reading the local PGN: unclosed-brace.pgn
Corrupt PGN: the comment opened by a brace on line 1 is never closed.
```

### Moves on a tag line

A tag takes a whole line, before the moves of its game. python-chess would skip this line, its moves with it, and the analysis would be about another game than yours. A line of brackets among the moves is refused as well: python-chess would play the moves that it holds.

```bash
./ianalyze.py tag-with-moves.pgn --no-explorer --no-questions
```

```text
[18:49:51] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[18:49:51] Reading the local PGN: tag-with-moves.pgn
Corrupt PGN: line 4 is not a well-formed tag, [Name "value"] alone on its line: python-chess would skip it, together with what it carries.
```

The same goes for a line that starts with a bracket among the moves:

```bash
./ianalyze.py bracket-among-moves.pgn --no-explorer --no-questions
```

```text
[10:47:00] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[10:47:00] Reading the local PGN: bracket-among-moves.pgn
Corrupt PGN: line 9 starts with a bracket among the moves. A tag goes before the moves of its game, and python-chess would read as moves what the brackets hold.
```

### Null move played in check

A null move, `--`, passes the turn. Played in check, it leaves the king attacked: the positions that follow are illegal, and the engine cannot evaluate them.

```bash
./ianalyze.py null-move-in-check.pgn --no-explorer --no-questions
```

```text
[18:49:52] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[18:49:52] Reading the local PGN: null-move-in-check.pgn
Corrupt PGN: null move "--" played in check, at move 2, by Black. Passing leaves the king attacked: the positions that follow are illegal, and the engine cannot evaluate them.
```

### PGN in UTF-16, cut short

A file in UTF-16 that lost a byte, by a cut transfer for example, is refused with its cause: in this encoding, one byte lost shifts the whole text that follows.\
Here the last byte is removed on purpose:

```bash
iconv -f UTF-8 -t UTF-16 my-game.pgn > my-game-utf16.pgn
```

```bash
dd if=my-game-utf16.pgn of=my-game-cut.pgn bs=1 count=$(($(wc -c < my-game-utf16.pgn) - 1))
```

```bash
./ianalyze.py my-game-cut.pgn --no-explorer --no-questions
```

```text
[08:21:33] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[08:21:33] Reading the local PGN: my-game-cut.pgn
[08:21:33] Warning, PGN: byte order mark (BOM) detected, encoding used: utf-16-le.
[08:21:33] Warning, PGN: invalid utf-16-le sequences replaced by U+FFFD.
Corrupt PGN: the file is in utf-16-le, but some of its bytes form no character: it is truncated or damaged, and in this encoding a single byte lost shifts the whole text that follows. Export it again from its source, then run again.
```

### Unknown option

Here a former French name, no longer accepted since version 5.0.0. The exit code is 2.

```bash
./ianalyze.py my-game.pgn --sans-questions
```

```text
usage: ianalyze.py [-h] [--install-venv] [--venv PATH] [--no-questions]
...
ianalyze.py: error: unrecognized arguments: --sans-questions
```

### Refused value

The exit code is 2.

```bash
./ianalyze.py my-game.pgn --pause 1
```

```text
usage: ianalyze.py [-h] [--install-venv] [--venv PATH] [--no-questions]
...
ianalyze.py: error: --pause must not go below 2 seconds
```

### Value outside the bounds of the engine

The bounds are those that the engine announces: they change from one version of Stockfish to another.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --multipv 9999
```

```text
[15:36:57] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:36:58] Reading the local PGN: my-game.pgn
--multipv: 9999 is out of the bounds of the engine /usr/games/stockfish, which accepts 1 to 500 for MultiPV.
```

### Engine not found

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --stockfish /nowhere
```

```text
[15:35:45] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:35:45] Reading the local PGN: my-game.pgn
Stockfish not found: /nowhere. Install it (apt install stockfish, in /usr/games), or give its path with --stockfish. The engine evaluation is part of every collection.
```

### Token missing

Without `--no-explorer`, the script needs the Lichess token (README, section 2).

```bash
./ianalyze.py my-game.pgn --no-questions
```

```text
[15:40:29] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:40:29] Reading the local PGN: my-game.pgn
Token missing: ~/.lichess_token not found.
```

### Token refused

The token is in place, but Lichess refuses it: wrong, expired or revoked.\
The run stops at the first request, before the engine:

```bash
./ianalyze.py my-game.pgn --no-questions
```

```text
[08:22:10] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[08:22:10] Reading the local PGN: my-game.pgn
[08:22:10] Opening catalog: 7982 known positions, from 2026-11-25T15:28:44+00:00
[08:22:10] Startup questions skipped: option --no-questions.
[08:22:10] Working folder: analysis-my-game-20261127-082210
[08:22:10] Explorer: database Lichess (all players), https://explorer.lichess.org/lichess
[08:22:10] Explorer: ply 1 (e4)
Explorer: the token is refused (HTTP 401), it is wrong, expired or revoked. Replace it in its file (see --token-file), or run again with --no-explorer. Working folder kept: analysis-my-game-20261127-082210
```

The working folder keeps the answer of Lichess, in `explorer/001-e2e4.json`: delete it once read.

### Catalog missing

The token is in place, but the catalog of the openings has not been installed.

```bash
./ianalyze.py my-game.pgn --no-questions
```

```text
[15:40:29] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:40:29] Reading the local PGN: my-game.pgn
Opening catalog missing: ~/IAnalyze/local/catalog.tsv not found.

Install it with one command:
    ~/IAnalyze/ianalyze.py --install-catalog
```

### Faulty prompt template

The template named by `--prompt` carries here a misspelled value.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --prompt ~/faulty-template.txt
```

```text
[15:36:58] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
Prompt template ~/faulty-template.txt, line 21: unknown value {{VERSON}}, accepted values: VERSION, REPOSITORY, ARCHIVE, USERNAMES, SIDE, RATING, TIME_CONTROL, ANNOTATOR, DATABASE, INACCURACY_THRESHOLD, MISTAKE_THRESHOLD, BLUNDER_THRESHOLD, DEPTH, MULTIPV, GAME_PGN, ENGINE_TABLE, RESULT_ALERT, PLAYER_INSTRUCTIONS, OPENING, PLIES, PLIES_EVALUATED, PLAYER_WEAK_MOVES, FENCE
```

### Settings file in the former format

A `settings.ini` in the former format carries the `[joueur]` section, not `[player]`: the `reglages.ini` of version 4 copied by hand, or a file written by a development version of 5.0.0. `--purge-settings` refuses it, as it refuses any file that is not a settings file, with the exit code 1. Delete it by hand, or run a collection first: it asks the settings questions again and adds the `[player]` section.

```bash
./ianalyze.py --purge-settings
```

```text
--purge-settings: ~/IAnalyze/settings.ini is not a settings file, it does not carry the [player] section. Nothing is deleted.
```

### Folder with several collections, for the checker

The current directory contains here several complete collection folders. The exit code is 2.

```bash
./verify-analysis.py . llm-annotated.pgn
```

```text
Cannot read: . holds 3 complete collections: analysis-my-game-20261125-153432, analysis-my-game-20261125-153440, analysis-my-game-20261125-153545. Give the folder of the one that the LLM received.
```

### Archive not found, for the checker

The exit code is 2.

```bash
./verify-analysis.py missing-archive.zip llm-annotated.pgn
```

```text
Cannot read: [Errno 2] No such file or directory: 'missing-archive.zip'
```

## EXIT CODES

`ianalyze.py`:

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | error reported by a message, including a value that the engine does not accept, or unexpected error |
| 2 | unknown option, options that exclude each other, or value refused before any reading of the game |
| 130 | interruption (Ctrl-C) |

`verify-analysis.py`:

| Code | Meaning |
|---|---|
| 0 | no `FAIL` in the report |
| 1 | at least one `FAIL` |
| 2 | a file cannot be read, or the archive is not one of IAnalyze: no check took place |

## FILES

What the script reads:

| File | Role |
|---|---|
| `local/venv` | the virtual environment, where python-chess lives |
| `local/catalog.tsv` | the catalog of the openings |
| `settings.ini` | your settings: usernames, usual time control, rating |
| `~/.lichess_token` | your Lichess token, in mode 600 |
| `prompt-template.txt`, `prompt-only-template.txt` | the prompt templates, next to the script |
| `/usr/games/stockfish` | the engine under Debian, when the PATH does not hold it, the one of root for example. Otherwise, the one of the PATH |
| `/opt/homebrew/bin/stockfish` | the engine under macOS, when the PATH does not hold it |

What it writes, in the current directory or in the one of `--output-dir`:

| File | Role |
|---|---|
| `analysis-<label>-<YYYYMMDD-HHMMSS>.zip` | the archive, to be attached to the conversation |
| `analysis-<label>-<YYYYMMDD-HHMMSS>.prompt.txt` | the prompt, to be pasted into the conversation |
| `analysis-<label>-<YYYYMMDD-HHMMSS>/` | the working folder, kept only with `--keep-folder` or after a failure |

The content of the archive is described in the README, section 5.

The settings file, as the script writes it after the first collection:

```ini
# Settings of ianalyze.py.
# You may edit this file by hand. A deleted key will be asked
# again at the next run in a terminal.

[player]
# Your player names, separated by commas. They are looked up,
# ignoring case, in the White and Black tags to deduce your
# side. The --usernames option replaces them for one run.
usernames = MyUsername
# Your usual time control, suggested when the TimeControl tag of
# a game does not give it. Accepted forms:
#   15+10                real time, minutes then increment in
#                        seconds
#   14 days              correspondence, fixed delay per move
#   10 moves in 50 days  correspondence, moves per period
#   5 days + 36 hours    correspondence, starting clock then
#                        increment per move, in hours or in
#                        days; add if need be ", maximum 20
#                        days" and ", bank 50 days"
#   unknown
time_control = 15+10
# Your rating, in approximate Elo points, or unknown. It is
# passed on to the analyst, who adapts the explanations to it.
# Without it, the Elo of your tag in the game is used.
rating = 1300
```

## SEE ALSO

- [README.md](README.md): the installation, everyday use, the choice of the LLM
- [TECHNICAL.md](TECHNICAL.md): how the script works, the format of the files
- [TESTS.md](TESTS.md): the test suite, test by test
- [CHANGELOG.md](CHANGELOG.md): the history of the versions
- `./ianalyze.py --help`: the summary of the options, in the terminal
