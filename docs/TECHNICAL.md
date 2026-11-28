# IAnalyze: technical documentation

Version française : [TECHNICAL.fr.md](TECHNICAL.fr.md)

The [README](../README.md) is enough to install IAnalyze and analyze a game. [EXAMPLES.md](../EXAMPLES.md) gives every command, every option and what they display.

This document goes further. It is meant for whoever wants to understand what the script does, call it from another program, read the files it produces, write their own prompt template, or take over the project: section 15 is the guide for that. The tests have their own document, [TESTS.md](TESTS.md), and so do the trials of the LLMs, [TRIALS.md](TRIALS.md).

## Contents

- [1. What the script does, step by step](#1-what-the-script-does-step-by-step)
- [2. Files of the repository](#2-files-of-the-repository)
- [3. Command line](#3-command-line)
- [4. The game, its source and its checks](#4-the-game-its-source-and-its-checks)
- [5. Startup questions and terminal](#5-startup-questions-and-terminal)
- [6. Settings](#6-settings)
- [7. Token](#7-token)
- [8. Explorer](#8-explorer)
- [9. Engine](#9-engine)
- [10. Files produced](#10-files-produced)
- [11. Encodings and characters](#11-encodings-and-characters)
- [12. Prompt template](#12-prompt-template)
- [13. The checker in detail](#13-the-checker-in-detail)
- [14. Sources and links](#14-sources-and-links)
- [15. Taking over the project](#15-taking-over-the-project)

## 1. What the script does, step by step

A collection always follows the same order. The checks come first: as long as they have not all passed, nothing is written in the output directory and no request goes to the explorer.

1. **Options.** They are read and checked (section 3). A refused option stops the script with the code 2.
2. **Virtual environment.** The system's Python does not have python-chess: the script restarts itself with the Python of its virtual environment. The log announces it with "Virtual environment: restarting with ...". This is the normal behavior, at each run.
3. **Settings and prompt template.** The settings file is read (section 6), the prompt template is read and checked (section 12).
4. **Game.** The PGN is read from the file, or downloaded from Lichess. It is decoded (section 11), then checked (section 4).
5. **Token and catalog.** Except with `--no-explorer`, the token is read (section 7) and the catalog of openings loaded (section 8).
6. **Engine.** The Stockfish binary is checked, then started a first time, only to ask it for the bounds of its options (section 9).
7. **Questions.** In a terminal, the script asks its questions (section 5).
8. **Working folder.** It is created in the output directory. The script writes `game.pgn` into it and, if you answered the questions, `context.md`.
9. **Explorer.** One request per ply, up to a stop criterion (section 8).
10. **Stockfish.** One evaluation per ply (section 9). This is the longest phase.
11. **Summary.** `collection.json` and `summary.md` are written (section 10).
12. **Archive.** The folder is compressed, the archive checked, the folder deleted. With `--prompt-only`, there is no archive.
13. **Prompt.** It is written next to the archive.
14. **Standard output.** The path of the archive, or the one of the prompt with `--prompt-only`, is written there alone.

Three commands collect nothing and stop once their work is done: `--install-venv`, `--install-catalog` and `--purge-settings`.

`--install-venv` checks the exit code of `python -m venv`. A creation interrupted before this return, by Ctrl-C or a power cut, leaves an environment without pip, which the next run finds half done. The script recognizes it: `pyvenv.cfg` and the interpreter are there, but `python -m pip --version` fails. It then rebuilds it with `python -m venv --clear`, then installs python-chess. Without `pyvenv.cfg`, a directory is never taken for an environment to rebuild, and `--clear` cannot erase anything in it.

A `--venv` that is not a virtual environment is refused before anything else: a path that exists without being a directory, a regular file for example, on which `python -m venv` failed with a message that suggested a missing package; an existing directory, not empty and without `pyvenv.cfg`, such as `/usr` or a home directory. pip would have run on the Python found there, often the one of the system, and `python -m venv` would have mixed its files with the ones already there. A missing or empty directory receives the environment. A creation interrupted in the very first moments, before `pyvenv.cfg` is written, leaves a directory that this refusal also sets aside: it is then enough to delete it.

After step 8, a failure leaves the working folder in place, as it is, for diagnosis.

## 2. Files of the repository

| File | Role |
|---|---|
| `ianalyze.py` | the collection, in a single file. It only needs python-chess and Stockfish |
| `verify-analysis.py` | the check of the PGN returned by an LLM (section 13) |
| `prompt-template.txt`, `prompt-only-template.txt` | the two prompt templates (section 12) |
| `tests/test-app.sh` | the test suite, for Linux and macOS, described in [TESTS.md](TESTS.md) |
| `tests/test.pgn` | a test game that gathers the tricky cases of a PGN, described in [TESTS.md](TESTS.md) |
| `tests/refused/`, `tests/llm/` | the PGNs that the script refuses and the annotated PGNs written for [EXAMPLES.md](../EXAMPLES.md), which the tests also read |
| `example-games/` | the games quoted in [EXAMPLES.md](../EXAMPLES.md), ready to be analyzed |
| `README.md`, `EXAMPLES.md`, and in `docs/`: `TECHNICAL.md`, `TESTS.md`, `TRIALS.md` | the documentation, each document with its French version, under the same name ending in `.fr.md` |
| `CHANGELOG.md` | the history of the versions, in English only |
| `LICENSE` | the license, CC0 |

HTTP goes through urllib and the archive through zipfile, both from the standard library of Python.

### Where the script keeps what it creates

The same on both platforms, except for the engine.

Everything the script creates for itself stays in the folder of the application: deleting this folder leaves nothing behind, except your token.\
The `local/` folder only keeps what the script can rebuild by itself, the virtual environment and the catalog: emptying it brings the application back to a fresh state without touching your settings. `local/` and the settings files are ignored by git.

| | Location |
|---|---|
| `--venv` | `local/venv`, in the folder of the application |
| `--catalog` | `local/`, in the folder of the application |
| settings | `settings.ini`, at the root of the folder of the application, like any other settings file named by `--settings` |
| token | `~/.lichess_token` |
| `--stockfish`, Debian | the binary found in the PATH, otherwise `/usr/games/stockfish` |
| `--stockfish`, macOS | the binary found in the PATH, otherwise `/opt/homebrew/bin/stockfish` |

Up to version 4.0.2, the virtual environment and the catalog were kept in `~/.local/share/IAnalyze`, the settings in `~/.config/IAnalyze`.\
The script no longer reads them there: run `--install-venv` and `--install-catalog` again, then delete these two directories. Your settings are asked again on the first run in a terminal.

## 3. Command line

### Consistency rules

An option without effect, or a value out of bounds, is refused rather than silently ignored:

- `--speeds` and `--ratings` require `--database lichess`.
- `--pause` does not go below 2, `--min-frequency` stays between 0 and 100, `--min-moves`, `--stockfish-moves` and `--pv-length` are 0 or more, `--depth` goes from 1 to 60, the other numeric values are at least 1. `--timeout` is checked with `--install-catalog` too, which downloads as well.
- `--pause` and `--min-frequency` refuse nan and inf.
- `--threads`, `--hash` and `--multipv` are checked against the engine, which announces its bounds: a value that it does not accept is refused before any request to the explorer and before the working folder is created.
- `--settings` takes a file name ending in `.ini`, without a folder and not starting with a dot (section 6): a path is refused, `/dev/null` included.
- `--settings` and `--no-settings` exclude each other, and so do `--purge-settings` and `--no-settings`.
- `--purge-settings` is used alone, without a game or another action.
- `--no-prompt` excludes `--prompt` and `--prompt-only`.
- `--usernames` and `--prompt` refuse an empty value.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | error reported by a message, among them a value that the engine does not accept, or unexpected error |
| 2 | unknown option, options that exclude each other, or value refused before any reading of the game |
| 130 | interruption (Ctrl-C) |

Those of `verify-analysis.py` are given in section 13.

### Standard output and log

The path of the archive is written alone on standard output, the timestamped log goes to standard error:

```bash
ARCHIVE=$(./ianalyze.py my-game.pgn 2>/dev/null)
```

With `--prompt-only`, it is the path of the prompt that is written on standard output.

The log, the questions and the error messages all go to standard error. Each line of the log carries the time:

```text
[14:20:16] Virtual environment: restarting with /home/user/IAnalyze/local/venv/bin/python3
[14:20:16] Reading the local PGN: my-game.pgn
[14:20:17] Working folder: analysis-my-game-20261125-142017
[14:20:33] Stockfish: evaluation of 9 plies, depth 18, multipv 3, threads 4. This is the longest phase.
```

An error message, for its part, is not timestamped: it is the last line, and the exit code is 1 or 2.

### Calling the script from another program

```bash
ARCHIVE=$(./ianalyze.py my-game.pgn --no-questions 2> collection.log)
```

The exit code says whether the collection succeeded, `collection.log` keeps the log and `$ARCHIVE` receives the path of the archive.

Redirecting standard error is enough to silence the questions (section 5): `--no-questions` only says it plainly.

On macOS, this command puts the short prompt into the clipboard, ready to be pasted into the conversation. Standard error not being redirected, the questions are still asked:

```bash
pbcopy < "$(./ianalyze.py my-game.pgn --prompt-only)"
```

## 4. The game, its source and its checks

SOURCE designates the game in three ways: a PGN file, the address of a Lichess game, or its identifier.

**A URL** must target lichess.org and carry the identifier at the head of the path.

The identifier is the string of 8 characters that follows `lichess.org/` in the address of the game. The forms `/<id>/black`, `/embed/game/<id>`, `/embed/<id>` and `/game/export/<id>` are accepted.

Another host, or another page of the site (study, analysis, puzzles), is refused without sending anything to Lichess. Some sections of the site have a name of eight letters, the form of an identifier: `analysis`, `training`, `timeline` or `bookmark` for example. They are refused too, from a list that the routes of the site completed in November 2026.

**An identifier** is exactly 8 or 12 alphanumeric characters.

A source that looks like a path (dot, slash or tilde) and does not exist is reported as a file not found. A directory is refused, even if its name has the form of an identifier.

**A PGN** must contain a single game, in standard chess. A file that gathers several of them is refused: isolate the one to analyze in a separate file.

**A repeated result** at the end of the file is not a second game. Some sites write the result, a blank line, then the result again: python-chess reads one more game there, without a single tag or move. The script ignores it and writes it in the log. The file kept in the archive stays the one you gave.

A corrupt PGN is refused rather than analyzed truncated. A game that does not start from the initial position, that is, one that carries a FEN tag, is refused too: IAnalyze analyzes a whole game, from the first move to the last. To study a position, load it into an analysis board.

The moves must be written in English notation: K, Q, R, B, N. A game written in French notation (R, D, T, F, C) or in figurines is refused, with the first word that was not understood. Without this refusal, "Cf3" would be read "f3", a pawn move, and the analysis would be about another game than yours.

Refused in the same way:

- a comment whose brace is never closed
- a variation whose parenthesis is never closed, or an extra closing parenthesis
- free text outside the braces, after the game for example
- a line that starts with a bracket without being a well-formed tag, alone on its line, before the moves of its game: python-chess would skip it, together with what it carries, or would play the moves that its brackets hold
- a null move played in check, after a mate for example: the positions that follow are illegal, and Stockfish died on them without saying why

A Lichess game is downloaded from `https://lichess.org/game/export/<identifier>`, which requires no token.

The check of the notation comes before the reading by python-chess, which, for its part, would refuse nothing: it silently skips the characters it does not know. Allowed outside the comments: the tags, alone on their line and before the moves of their game, the move numbers, the moves in English notation, the null move `--`, the NAGs, the annotation signs, the parentheses of variations and the result.

An illegal move stops the script too. python-chess, at that point, would stop reading without raising an error, and the game would be analyzed truncated. The refusal names the move, once: python-chess no longer writes it on its own beforehand.

## 5. Startup questions and terminal

### Order of the questions

1. On the first run, the missing settings: username, usual time control, rating (section 6). With `--settings`, a name whose file does not exist yet is confirmed first.
2. Your side, if it cannot be deduced from your usernames: "Did you play White or Black? [w/b]". The empty White and Black tags are then filled in: yours with your first username, or with your name, asked for lack of a username, the one of the opponent with their name, asked too.
3. The time control of the game, if the TimeControl tag is missing, empty, or is "?" or "-".
4. The four context questions: scope, what you want to understand, particular context, other comments to include in the final PGN.

Enter keeps the suggested value. Ctrl-D ends the questions: the remaining ones take their default value.

The settings questions are the exception: interrupted by Ctrl-D, they save nothing and will come back at the next run.

### Limits of an answer

An answer is 255 characters at most.\
A player name or a username can contain neither a quote, nor a backslash, nor a square bracket, nor a brace: it goes into a tag of the PGN, which these signs would make unreadable.

A refused answer is asked again.

### What becomes of the answers

The answers go into `context.md`, repeated at the top of the summary under the title "Analysis instructions".

An answer left at its suggested value carries the mention "(default)" there: the analyst thus tells your choice from a default value.

```text
The player's answers to the startup questions, asked by the script before the collection. "(default)" marks an answer confirmed with Enter.

- Player's side: White, deduced from the headers
- Time control: TimeControl tag `600+5`, that is rapid, 10 minutes + 5 seconds per move
- a. Scope: the whole game (default)
- b. What the player wants to understand: the early queen sortie
- c. Particular context: nothing (default)
- d. Other comments to include in the final PGN: nothing (default)
```

When a White or Black tag has been filled in, `game.pgn` carries the game with its new tags, and the PGN given is kept as `game-original.pgn`.

### When the questions are not asked

The questions are displayed in the terminal and wait for an answer at the keyboard.

The script therefore only asks them if it is run by hand, in a terminal. It asks nothing in these four cases:

- you pass `--no-questions`
- another program runs it without a terminal: cron, a service
- its input does not come from the keyboard: `./ianalyze.py my-game.pgn < /dev/null`
- its log does not go to the screen: `./ianalyze.py my-game.pgn 2> log.txt`

The last case is surprising: the questions are written at the same place as the log, standard error. If you redirect it, you would not see them.

The example of section 3, with `2>/dev/null`, therefore asks no question. Without this redirection, `ARCHIVE=$(./ianalyze.py my-game.pgn)` asks them normally.

In what follows, "without a terminal" denotes these four cases.

### Without questions, what changes

- The log says so: "Startup questions skipped", followed by the reason, the option or the non-interactive terminal.
- The missing settings are neither asked nor written.
- `context.md` is not written, and the summary has no "Analysis instructions" section.
- The side is deduced from your usernames, without a question. For that, only one of the two tags, White or Black, must carry one of them. Otherwise the side stays "unknown".
- The prompt tells the LLM that your answers were not collected: it is the LLM that asks the four context questions, in a single message, before analyzing.

## 6. Settings

The settings file, `settings.ini` or the one named by `--settings`, is kept at the root of the folder of the application, in INI format. Its `[player]` section carries three keys that the script asks for, `usernames`, `time_control` and `rating`, and an optional key, `annotator`.

### Keys and accepted forms

**The usernames** are your player names, separated by commas. They are looked up, ignoring case, in the White and Black tags to deduce your side, as the whole name or as a run of its words: "Müller" is found in "Müller, Noël", but "Max" is not in "Maxime", nor "deuza" in "DeuZa42". List each of your usernames. The first one is used to fill in an empty tag.

**The rating** is a number of approximate Elo points, from 100 to 3500, or "unknown".

**The annotator** is an optional key, which the script does not ask for. It sets the Annotator tag of the annotated PGN:

```text
annotator = Claude (Anthropic)
```

Without it, the prompt asks the analyst to put its own model name there.

**The time control** is written in one of these ways:

| You write | System | Where it is found |
|---|---|---|
| `15+10` | real time: minutes per player, then increment in seconds | Lichess |
| `14 days` | correspondence with a fixed delay: days per move, nothing is carried over from one move to the next | Lichess, chess.com |
| `10 moves in 50 days` | correspondence by period: the time saved is carried over | ICCF, standard time control |
| `5 days + 36 hours, maximum 20 days` | correspondence with a clock: days at the start, then increment per move in hours or in days, optional maximum | chess-mail.com |
| `50 days + 3 days, maximum 50 days, bank 75 days` | the same, with a bank beside the clock | ICCF, Triple Block |
| `unknown` | | |

The two systems of the ICCF follow its rules in force since 1 January 2026, section 2.4.

The fixed delay per move, for its part, does not exist at the ICCF.

The script tolerates a few variants of spelling: "d" or "day" for "days", "h" or "hour" for "hours", "move" for "moves". An empty time control, "?" or "unspecified" counts as "unknown".

For real time, the category is computed as Lichess does, on an estimated duration: the initial time plus forty times the increment.

| Estimated duration | Category |
|---|---|
| less than 30 seconds | ultrabullet |
| from 30 seconds to less than 3 minutes | bullet |
| from 3 to less than 8 minutes | blitz |
| from 8 to less than 25 minutes | rapid |
| 25 minutes and more | classical |

`15+10` gives 900 + 400 = 1300 seconds: rapid.

### Reading

- A missing file counts as empty settings.
- A missing key is asked for, only once, in a terminal.
- A key that is present, even empty, is never asked for again.
- An unreadable time control or rating is asked for again, and the log says so.
- A badly formed file stops the script, with the remedy: fix it or delete it.
- The "%" sign is a character like any other, it triggers no substitution.
- The file goes through the same decoding as the PGN (section 11): its encoding does not matter.
- `--usernames` replaces the usernames of the file for a run. On the very first run, it is suggested as the answer to the username question.
- A `settings.ini` in the former format, copied by hand from the `reglages.ini` of version 4 or written by a development version of 5.0.0, carries a `[joueur]` section, which is no longer read: its questions are asked again, and the section stays in the file after `[player]`, as a section of your own.

### Writing

The script writes the file only when it has just obtained an answer. It then rewrites it entirely:

1. a header of comments
2. the keys that it knows, each one under a comment that recalls its accepted forms
3. the other keys that you added to `[player]`
4. your other sections

Your own comment lines therefore do not survive a rewrite.

The file is written only over a settings file: a path that does not exist yet, or a regular file that is empty or carries the `[player]` section, or the `[joueur]` section of the former format. The section is looked up in the text decoded as the reading does: a settings file in UTF-16 is recognized, for the writing as for `--purge-settings`. Anything else, a device, a FIFO, a directory or the file of another program, is left untouched.

If the writing fails, or if the file must not be replaced, the collection goes on: the log reports it, and the question will be asked again at the next run.

Without a terminal, nothing is asked or written.

### Several profiles

`--settings NAME` designates another file: a file name ending in `.ini` and not starting with a dot, which would hide it, kept at the root of the folder of the application, next to `settings.ini`. A path is refused, even inside the folder: the settings never leave the folder, and deleting it leaves nothing behind. If the file does not exist, it is created by the same questions: this is the way to keep one profile per player.

In a terminal, a name whose file does not exist yet is first confirmed: "Settings: player2.ini does not exist yet in ... Create it? [y/n]". `n`, or Ctrl-D, stops the script before anything is written or collected: a typo does not start a new file. The default file, `settings.ini`, is created without this question.

`--no-settings` leaves the settings aside for a single run: no file is read or written, and the settings questions are not asked. The side is asked, or deduced from `--usernames`, and the rating comes from the Elo tag of your side.

`--purge-settings` deletes the settings file, the one of `--settings` if given, then exits. Only a file that carries the `[player]` section, or an empty file, is deleted: a typo must not destroy another file. A missing file is not an error, a directory is refused.

## 7. Token

The token is only sent in the Authorization header, never in the URL. It appears neither in the log, nor in the archive, where `collection.json` only notes its presence.

It is only sent to the address of the explorer: if the explorer answered with a redirect, it would not be followed, and the querying would stop there.

A token file that others can read triggers a warning. The file carries only the token: an assignment, `LICHESS_TOKEN=...`, or quotes are refused.

The file may carry a byte order mark or be in UTF-16, as some Windows editors produce: the log reports it and the token is read normally.

The file is only opened if the explorer is used: with `--no-explorer`, it is not read. The download of a Lichess game, for its part, is done without a token.

Checks at reading:

- a missing or empty file stops the script
- a space, an equal sign or a quote in the token stops the script: the file must carry only the token
- a character outside printable ASCII stops the script, without the message reproducing the token

The answer of the explorer is redacted of the token before being kept in the archive, in case a server sent back the header that it received. The same goes for the traceback of an unexpected error, with `--debug`.

## 8. Explorer

### Requests

The script sends one request per ply, to `https://explorer.lichess.org/lichess` or to `https://explorer.lichess.org/masters` according to `--database`. The position is designated there by the sequence of the moves played since the start of the game, and not by a FEN.

| Parameter | Value | Role |
|---|---|---|
| `play` | the moves already played, in UCI notation, separated by commas | the position queried |
| `moves` | `256` | all the moves known in the position, and not only the first ones |
| `topGames` | `0` | no reference game, only the statistics are used |

The `lichess` database also receives the filters:

| Parameter | Value |
|---|---|
| `variant` | `standard` |
| `speeds` | the list of `--speeds` |
| `ratings` | the list of `--ratings` |
| `since` | `2017-01` |
| `recentGames` | `0` |

Each request carries the agent header `IAnalyze/<version> (+https://github.com/deuza/IAnalyze)` and the token, in the Authorization header.

Each answer is kept as it is in `explorer/NNN-<uci>.json`: NNN is the number of the ply, `<uci>` the move played. It is the answer about the position before this move.

### Pause, HTTP 429 and errors

The script waits `--pause` seconds between two requests, 2 at least, and nothing before the first one.

On an HTTP 429, the script waits 60 seconds and tries again only once. At the second refusal, it stops querying: better to stop than to get banned.

Any other unusable answer stops the querying at this ply: an HTTP error, a timeout (`--timeout`), an answer that is not JSON, a redirect, an answer without a list of moves. The collection, for its part, goes on: the table of the explorer stops there, and Stockfish evaluates the whole game. An answer without a list of moves passed for an exit from theory, its move played at 0.0 %.

Without a token, the `lichess` database answers 401. The script requires a token for both databases, and stops before any request if the file is missing.

A token refused, HTTP 401 at any ply, stops the whole run, with the exit code 1, before the engine: no other answer can come, and Stockfish ran for minutes for a collection without its section 2. The message advises to replace the token or to run again with `--no-explorer`. The answer stays in `explorer/`, and the working folder is kept.

### Stop criteria

For each ply, the position BEFORE the move is queried, which gives the rank and the frequency of the move really played.

The querying stops, in this order of testing:

1. on an HTTP error, an unusable answer or a position missing from the database.
2. on a sample smaller than `--min-games`.
3. on an exit from theory, outside the `--min-moves` window.
4. at the `--max-plies` cap, or at the end of the game.

A null move, "--" in the PGN, also stops the querying, before any request for this ply and whatever the mode: it is not a chess move, the database cannot follow the game beyond it.

It is not counted as an exit from theory, and section 4 of the summary reports it.

### Exit from theory

A move is rare when it is played in less than `--min-frequency` percent of the games of the position.

A rare move is an exit from theory if it leads to a position missing from the catalog of openings. If it stays in a line that the catalog knows, it is not one.

The first exit is always noted. It only stops the querying after the first `--min-moves` moves, so that the table covers the start of the game even after an early exit.

### Catalog of openings

The catalog comes from the five files `a.tsv` to `e.tsv` of the repository [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings).

`--install-catalog` downloads them and replays each line with python-chess. An unreadable or illegal move, or a position named twice, stops the installation without touching the catalog in place.

The index is then written into `catalog.tsv`, in the directory of `--catalog`. It is written under a temporary name, then renamed: a collection started during an update reads the old index or the new one, never a mix.

```text
#format=2  date=2026-11-25T14:20:09+00:00  lines=3865  named=3865  known=7982  source=...
epd  eco  name
```

The first line describes the index, the second one names the columns, and each following line carries a position: its EPD, its ECO code and its name, separated by tabs. The positions are sorted, so that two installations of the same catalog give two identical files.

A position is identified by its EPD, the en passant square appearing in it only if the capture can be played: this is also the rule of the server of the explorer.

The catalog says "known", never "good": "Barnes Opening: Fool's Mate" is in it.

It also counts the intermediate positions of the named lines, which the explorer does not name itself.

These intermediate positions have an empty name in the index. On 25 November 2026, the catalog counted 3865 named lines, that is 7982 known positions counting them.

At loading, the format and the number of positions announced are checked: a missing, damaged or truncated index stops the script, which gives the command to run again.

A catalog index written before version 5.0.0, `catalogue.tsv`, is not read: run `--install-catalog` again.

## 9. Engine

### Dialogue with Stockfish

By default, the engine is the `stockfish` binary found in the PATH, on Debian as on macOS. Failing that, it is the one of the package: `/usr/games/stockfish` on Debian, which the PATH of root does not hold, and `/opt/homebrew/bin/stockfish` on macOS. `--stockfish` names another one.

The script drives Stockfish over the UCI protocol, through python-chess. It starts it twice:

1. before the collection, to read the bounds that the engine announces for its options, then stop it. A value out of bounds is thus refused at once, and not after several minutes of explorer
2. for the analysis: it sets `Threads` and `Hash`, asks for the winning chances with `UCI_ShowWDL` if the engine knows this option, then has each position analyzed up to the requested depth

### Threads, Hash and MultiPV

| Option of the script | UCI option | Default of the script | Default of Stockfish |
|---|---|---|---|
| `--threads` | `Threads` | the number of processors | 1 |
| `--hash` | `Hash` | 256 | 16 |
| `--multipv` | `MultiPV` | 3 | 1 |

**Threads.** This is the number of threads of execution that the engine uses to explore a position. The more it has, the faster it reaches the requested depth. The documentation of Stockfish advises giving it as many as the machine has cores: this is the default of the script.

A consequence to know: with several threads, two analyses of the same position do not give exactly the same figures. Measured with Stockfish 16 at depth 16: three identical analyses with one thread, three analyses differing by a few centipawns with four threads, the order of the best moves possibly changing when they are worth the same. Two collections of the same game therefore differ a little. For reproducible figures, run the script with `--threads 1`.

**Hash, the hash table.** While exploring, an engine keeps falling back on the same positions through different move orders. The hash table, or transposition table, keeps the result of the searches already done so as not to redo them. `--hash` sets its size, in megabytes. Too small, it fills up and the engine recomputes. Too large for the free memory, the system refuses to allocate it and the engine stops: the script then says so, and names `--hash`.

**MultiPV, the best moves.** By default, an engine only looks for the best continuation, its "principal variation". With MultiPV, it returns several of them, ranked. The script asks for 3, so that the summary shows what the engine preferred to the move played. The search is slowed down by it: the documentation of Stockfish advises leaving 1 for the best performance.

If the move played is not among these best moves, the script starts a second search, restricted to this single move, to give it an evaluation and measure the loss.

**The depth.** `--depth` stops the search when the engine has reached this depth. The computing time grows very fast with it. The script bounds it to 60.

The bounds are the ones that the engine announces. Stockfish 17.1 and Stockfish 19 accept from 1 to 1024 for Threads, from 1 to 33554432 for Hash and from 1 to 256 for MultiPV.

Sources: [UCI options of Stockfish](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html) for Threads, Hash, MultiPV and UCI_ShowWDL, and [Transposition Table](https://www.chessprogramming.org/Transposition_Table), on the Chess Programming wiki, for the hash table.

### What the script draws from the evaluations

- **The evaluation** is given from White's point of view, in pawns: `+0.35`. A mate is written `#+2`, White mates in two moves, or `#-1`, Black mates in one move.
- **A mate is counted after the move**, like any evaluation of the table. The engine, for its part, counts before the move, this one included: the script therefore removes one move from the side that mates when it has just played. `#+0` or `#-0`: the move of the line gives mate.
- **The loss** is what the move played loses compared with the first choice of the engine, in centipawns, from the point of view of the side to move.
- **The category** follows the loss: inaccuracy from 50, mistake from 100, blunder from 300.
- **A negative loss** is not a fault. The move played, evaluated apart when it is not among the first choices, then comes out slightly above the first one: the two are worth the same. Beyond 10000, the search of the move played found a mate that the search of the best moves did not see: the loss reads "mate", instead of some -99000 centipawns.
- **The mates** are not counted in centipawns. Between two mates of the same direction, mating in two moves instead of one for example, the loss is 0. A move that misses a mate or concedes one carries the loss "mate" and the category "blunder".
- **W/D/L** gives the chances of win, draw and loss of White. They are those of the model of Stockfish, built on games of the engine against itself: a trend, and not a probability between human players. The engine gives them per thousand; the script writes them in whole percentages whose sum is 100, by the largest remainders: each share is rounded down, then the points missing go to the largest remainders. Rounded one by one, 15, 970 and 15 per thousand gave 2/97/2. The shares are computed for White, then swapped for Black, whose view stays the mirror of the one of White.
- **The variations** are written in numbered notation, the one of the PGN: a variation that starts with a Black move reads `8... Bg4`, with a space after the dots. python-chess wrote `8...Bg4`.
- **A null move**, `--`, is not evaluated: it is not a chess move, the engine cannot judge it. Its line keeps the best moves of the position.

### `stockfish/evaluations.json`

The file is a list, one object per evaluated ply:

| Key | Content |
|---|---|
| `ply`, `move_number`, `side_to_move` | the rank of the ply, the number of the move, "White" or "Black" |
| `fen` | the position before the move |
| `played` | the move played and its evaluation |
| `best` | the best moves of the engine, in order, as many as `--multipv` |
| `cp_loss` | the loss in centipawns. From 10000 on, it no longer measures anything: one of the two moves is a mate |
| `category` | "inaccuracy", "mistake", "blunder", or null |

For a null move, `played` carries `not_evaluated`, and `cp_loss` as well as `category` are null.

`played` and each element of `best` carry the same keys:

| Key | Content |
|---|---|
| `san`, `uci` | the move, in algebraic notation and in UCI notation |
| `score` | the evaluation from White's point of view, as in the summary |
| `value_for_side` | the same in centipawns, from the point of view of the side to move. A mate in n moves is worth 100000 - n there |
| `depth` | the depth reached |
| `pv_san`, `pv_uci` | the whole principal variation, which the summary cuts at `--pv-length` plies |
| `wdl` | `win`, `draw` and `loss` of White, per thousand |

## 10. Files produced

### Content of the archive, at a glance

| File | Content |
|---|---|
| `summary.md` | the summary, which the analyst reads first |
| `game.pgn` | the PGN, headers filled in if need be |
| `game-original.pgn` | the PGN given, if headers were missing |
| `context.md` | the answers to the startup questions |
| `explorer/NNN-<uci>.json` | one raw answer per ply queried |
| `stockfish/evaluations.json` | the complete evaluations of the engine, whole variations |
| `collection.json` | exact parameters of the collection, without the token. `pgn_encoding` and `pgn_remarks` say how the PGN was decoded, `prompt_written` names the prompt |

The prompt, `analysis-<label>-<YYYYMMDD-HHMMSS>.prompt.txt`, is written next to the archive, not inside it.

### Working folder and archive

The working folder is named `analysis-<label>-<YYYYMMDD-HHMMSS>`. The label is the name of the PGN without its extension, sanitized (section 11), or the Lichess identifier: a sanitized label is announced in the log by "Folder name sanitized: ...". A folder or an archive of the same name adds a suffix, -2, -3 and so on.

An archive present under its final name is always complete and checked: it is written under the temporary name `.<folder>.partial.zip`, then renamed.

The same goes for each file of the working folder, written as `.<name>.partial`. After an interruption (Ctrl-C) or a failure, these temporary files are removed and the working folder stays, without an archive.

### `game.pgn` and `game-original.pgn`

`game.pgn` is the PGN given, converted to UTF-8 if it was not.

If your answers filled in a White or Black tag, `game.pgn` carries the game rewritten by python-chess with its new tags, and `game-original.pgn` keeps the text given.

### `collection.json`

The file keeps the exact parameters of the collection: all the options of the command line, under their name, the hyphens becoming underscores, plus these keys:

| Key | Content |
|---|---|
| `token_present` | true if a token was read. The token itself never appears there |
| `catalog_used` | the description of the catalog: date, number of lines and of positions |
| `side` | your side, its origin, deduced or declared, and the tags filled in |
| `context_collected` | true if you answered the questions |
| `pgn_encoding`, `pgn_remarks` | how the PGN was decoded |
| `prompt_written` | the name of the prompt, or null with `--no-prompt` |

`usernames` carries there the usernames really used, those of `--usernames` or those of the settings.

A path under your home folder is written with `~`, there as for the source and the engine in `summary.md`: the name of that folder, your login most often, does not go to the LLM with the archive.

### `summary.md`

Sections of `summary.md`:

| Section | Content |
|---|---|
| Analysis instructions | `context.md`, your answers to the startup questions. Missing when they are not asked |
| 1. Headers and moves of the game | headers, main line, phase markers (castling, queens, entry into the endgame) |
| 2. Explorer of the ... database, exit from theory | filters, thresholds, table, first exit |
| 3. Stockfish evaluations | category and W/D/L of each move |
| 3a. Principal variations of the engine | the principal variations of the engine |
| 3b. Mistakes and blunders by side | mistakes and blunders by side, with the FEN |
| 4. Positions with an unusable sample | where the database says nothing more, or the ply of a null move |
| 5. Raw data of the archive | the content of the zip, and the encoding of the PGN if it was converted. The `explorer/` folder only appears there if it exists |

**Table of the explorer**, one line per ply, under the columns `#`, `Move`, `Side`, `Pos. games`, `Played`, `Rank`, `Freq.`, `White score`, `Top move`, `Top freq.`, `Top White score` and `Opening`:

- ply, number of the move, side to move
- games of the position
- move played, its rank, its frequency, the score of White on this move
- most played move, its frequency and its score
- Opening: ECO name of the position reached, "(intermediate)" for a passing position of a named line, "-" outside the catalog

**Table of Stockfish**, one line per ply, under the columns `#`, `Move`, `Side`, `Played`, `Eval`, `W/D/L`, `CP loss`, `Category`, `1st`, `2nd` and `3rd`:

- ply, number of the move, side to move, move played
- evaluation, from White's point of view
- W/D/L: chances of win, draw and loss of White according to the model of Stockfish, to be read as a trend rather than as a probability between human players
- loss compared with the first choice of the engine, from the point of view of the side to move
- category: inaccuracy from 50 cp of loss, mistake from 100, blunder from 300
- the three best moves

Three special cases:

- the loss reads "mate" when the move played misses a mate, concedes one, or finds one that the search of the best moves did not see: it is not counted in centipawns
- under the table, a line "Result and final evaluation contradict each other" appears when the side declared the winner is clearly worse after the last move, by at least 300 cp: the game was not decided on the board, and the analyst must say so instead of telling the story of a deserved win
- a null move, "--" in the PGN, is not evaluated: its line keeps the three best moves of the position, its other columns carry "-"

## 11. Encodings and characters

No badly encoded input must stop the script on a Python traceback: at worst, a "Warning" line of the log and a clean degradation.

PGN, prompt template and token file, tried in this order:

1. byte order mark (BOM) UTF-8, UTF-16 or UTF-32
2. UTF-32 without a mark, recognized by its three null bytes out of four
3. UTF-16 without a mark, recognized by its null byte out of two
4. UTF-8
5. damaged UTF-8: at least one correctly encoded accented character and at most four invalid bytes for each of them, these bytes becoming U+FFFD
6. cp1252, then latin-1, which accepts any byte

Outside flawless UTF-8, the log names the encoding used:

```text
Warning, PGN: the content is not UTF-8, encoding used: cp1252.
```

The CRLF and CR line ends are brought back to LF. The control characters, NUL included, are removed and counted in the log, the tab and the line feed are kept.

The `game.pgn` file is therefore always clean UTF-8: if the file given had to be converted, section 5 of the summary says so, and `collection.json` keeps the detail.

A latin-1 text also decodes without error in cp1252, the two only differing on the bytes 0x80 to 0x9F: it is cp1252 that is announced.

A PGN that is neither in UTF-8, nor in UTF-16, nor in cp1252 is refused, with the advice to convert it. The script recognizes it by one of the five bytes that cp1252 does not define.

A PGN in UTF-16 or in UTF-32 whose bytes do not all form characters is refused too: in these encodings, a character takes two or four bytes, and a single byte lost, by a cut transfer for example, shifts the whole text that follows. The refusal names the encoding. It used to blame a U+FFFD for not being a move, or a brace for never being closed, the cause staying in the "Warning" line of the encoding. In UTF-8, an invalid byte only damages one character: the damaged UTF-8 of step 5 stays accepted.

Limit: a file in cp850 or in MacRoman that contains none of these five bytes passes for cp1252. Its accented letters come out wrong in the names and the comments, and nothing allows to see it. The moves, written in ASCII, stay right.

Tags of the PGN (White, Black, Event, Site and the others): tabs and control characters are removed from them before the headers of the summary are written and before any display.

Other readings:

- the token file follows the same detection as the PGN, and a token outside printable ASCII is refused before any request
- the catalog and the answers of the explorer are read in UTF-8, byte order mark tolerated
- the output of the engine is decoded in UTF-8 by python-chess, which sets aside an unreadable line without stopping

Nothing depends on the locale.

Writing: all the files of the archive are in UTF-8, LF line ends.

In the label of the archive, the control characters, the characters `/ \ : * ? " < > |` and the undecodable bytes of the name of the PGN become "\_", and the spaces become hyphens: `game against machine.pgn` gives `analysis-game-against-machine-...`. The label is bounded to 80 bytes.

The accented letters are kept.

Console: a character that the terminal cannot display becomes "?" instead of stopping the script, under LANG=C as with PYTHONIOENCODING=ascii.

The path of the archive is written in bytes on standard output: ARCHIVE=$(...) stays exact in every case.

Startup questions: an answer typed in another encoding than the one of the terminal is decoded again, cp1252 then latin-1.

## 12. Prompt template

The prompt of each game is drawn from a template: `prompt-template.txt`, or `prompt-only-template.txt` with `--prompt-only`. You can edit them, or designate your own with `--prompt`.

The prompt always describes the summary that this version of the script has just written: the two cannot diverge.

Two kinds of markers are interpreted:

| Marker | Effect |
|---|---|
| `{{NAME}}` | a value, replaced |
| `#! if CONDITION` | keeps what follows if the condition is true |
| `#! if not CONDITION` | keeps what follows if it is false |
| `#! else` | switches |
| `#! end` | closes the last "if" opened |
| `#! note ...` | comment of the template, never copied |

A directive takes a whole line, and the "if" may be nested. The blank lines left by a removed passage are tightened.

In the templates of the repository, the lines of text are wrapped at 71 columns, as the prompt shows them. A sentence that a condition cuts goes on with whole lines in each branch, even if their beginning repeats: the prompt keeps an even wrap whatever the conditions, which test T92 checks.

Values:

| Value | Content |
|---|---|
| `VERSION` | version of the script |
| `REPOSITORY` | address of the repository of IAnalyze |
| `ARCHIVE` | name of the file of the archive |
| `USERNAMES` | your usernames, separated by commas |
| `SIDE` | White, Black or unknown |
| `RATING` | your rating, phrased: "about 1300 Elo, declared by the player", otherwise the Elo of your tag, otherwise "unspecified: judge from the game, and stay accessible" |
| `TIME_CONTROL` | your usual time control, phrased |
| `ANNOTATOR` | value of the Annotator tag |
| `DATABASE` | database queried: "Lichess (all players)" or "masters" |
| `INACCURACY_THRESHOLD`, `MISTAKE_THRESHOLD`, `BLUNDER_THRESHOLD` | thresholds of the category of the move, in centipawns: 50, 100 and 300 |
| `DEPTH`, `MULTIPV` | values of `--depth` and of `--multipv` |
| `GAME_PGN` | the PGN of the game, as the archive contains it |
| `ENGINE_TABLE` | the evaluations of Stockfish, one line per ply. Behind a weak move: its category, its loss, the best move, its continuation over `--pv-length` plies and its evaluation |
| `RESULT_ALERT` | the sentence that reports a result contrary to the final evaluation, empty otherwise |
| `PLAYER_INSTRUCTIONS` | those of your answers to the startup questions that you did not leave at their default |
| `OPENING` | the opening and the exit from theory in one sentence, according to the explorer |
| `PLIES` | number of plies of the game |
| `PLIES_EVALUATED` | number of plies that the engine evaluated, smaller with `--stockfish-moves` |
| `PLAYER_WEAK_MOVES` | number of your moves that `ENGINE_TABLE` marks inaccuracy, mistake or blunder, "unknown" if your side is not known |
| `FENCE` | fence of the code block that holds `GAME_PGN`: a run of backquotes longer than any run of the game, three at least |

Conditions:

| Condition | True when |
|---|---|
| `STOCKFISH` | always, since version 4.0.0. Kept for the personal templates that use it |
| `EXPLORER` | section 2 was collected |
| `LICHESS_DATABASE` | database of all the players |
| `MASTERS_DATABASE` | masters database |
| `ANSWERS` | the script collected your answers to the startup questions |
| `SIDE_KNOWN` | your side is known |
| `USERNAME_KNOWN` | at least one username is known |
| `RATING_DECLARED` | your rating is in the settings |
| `RESULT_CONTRADICTED` | the result of the game contradicts the final evaluation |
| `INSTRUCTIONS_GIVEN` | `PLAYER_INSTRUCTIONS` is not empty |
| `OPENING_KNOWN` | `OPENING` is not empty |
| `PARTIAL_COVERAGE` | `--stockfish-moves` limited the engine to the first moves |
| `NULL_MOVE` | the game contains a null move, written `--` |
| `FEW_WEAK_MOVES` | your side is known and `PLAYER_WEAK_MOVES` is less than three |
| `NO_WEAK_MOVE` | your side is known and `PLAYER_WEAK_MOVES` is zero |

`STOCKFISH`, `MASTERS_DATABASE` and `RATING_DECLARED` serve neither template of the repository: they are kept for the personal templates.

The two templates, `prompt-template.txt` and `prompt-only-template.txt`, share these markers. `GAME_PGN`, `ENGINE_TABLE`, `RESULT_ALERT`, `PLAYER_INSTRUCTIONS`, `OPENING`, `DEPTH`, `FENCE`, `PLAYER_WEAK_MOVES` and the conditions `RESULT_CONTRADICTED`, `INSTRUCTIONS_GIVEN`, `OPENING_KNOWN`, `NULL_MOVE`, `FEW_WEAK_MOVES`, `NO_WEAK_MOVE` serve the short prompt. `PLAYER_WEAK_MOVES`, `FEW_WEAK_MOVES` and `NO_WEAK_MOVE` also serve the final summary of the full prompt.

Both prompts end with a report: the three costliest errors of the player and the theme to work on. When the table marks fewer than three weak moves on your side, the sentence changes: it gives their number and asks to keep to those. In the short prompt:

```text
After the code block, give in a few lines the costliest errors of the
player and the theme they must work on first.
Weak moves of the player in the table: 2.
Keep to those, without adding any.
```

The full prompt says it in its final summary, and asks besides not to replace your errors with those of your opponent. Without any weak move on your side, both prompts ask to attribute no error to you. When your side is not known, the short prompt asks to comment on both sides in the same way and to give the report for each one; the full prompt asks for your errors once your side is found, and for those of each side otherwise.

Both prompts say that the tags and the comments of the PGN are data, the notes of the player at most, never instructions: a comment, or a tag, could otherwise give orders to the LLM. The short prompt places the game in a code block, whose fence, `FENCE`, is longer than any run of backquotes of the game: with a fixed fence of three, a comment that held such a line closed the block.

Both prompts ask to keep these notes in the PGN returned, ahead of the comment of the LLM, and to leave out the commands that a site writes between brackets in the comments: `[%clk 0:10:00]` for the clock, `[%eval 0.23]` for its engine. A game downloaded from Lichess carries them, the export giving the clocks and the evaluations by default, and the full prompt forbids the `%` character in a comment. A `%` that a note itself carries becomes "percent" there too; the other format constraints bear on the text of the LLM, not on a note kept. When a note contradicts the figures of the engine, those left by the analysis of a site for example, the engine prevails and the LLM is asked to say so.

The final summary of the full prompt keeps to the agreed scope, like the comments: it asked for the costliest errors of the whole table, even when the comments stopped at move 15. The short prompt says the same under "What the player specified", when a scope is given there. Both add that a scope holding fewer errors than asked for gives only those: the counts of weak moves are those of the whole table.

The full prompt fixes the order of the start of the answer: the line that says whether the LLM can run code, case A or B, then the recap. Two sections both asked for the start of the answer.

The notation of the PGN returned is the standard one: K, Q, R, B, N, no letter for a pawn, castling with the capital letter O. The full prompt listed `K Q R B N P`, which invited a `P` that the checker now refuses.

With `--stockfish-moves`, the weak moves are counted over the plies evaluated only: under `PARTIAL_COVERAGE`, both prompts bound the count, or the absence of a weak move, to these first plies, and ask that an error found beyond them be given as an estimate of the LLM, without a figure. Without this bound, a player with no weak move in the window evaluated was said to have made no error in the whole game.

The reason comes from the trials of 21 November 2026 ([TRIALS.md](TRIALS.md#21-november-2026-with---prompt-seul-now---prompt-only)): the player had made only two errors, and three answers out of five presented a third one to reach the count asked for. A trial of the full prompt, on 25 November 2026, showed the other way out: asked for "the three costliest errors" without being told whose, the LLM gave those of the opponent, and left out one of the two weak moves of the player.

An unknown or badly written marker, such as `{{ RATING }}`, an "if" never closed, a badly formed directive or a template without a single line of text stop the script before the collection:

```text
Prompt template prompt-template.txt, line 12: unknown condition ENGINE, accepted conditions: STOCKFISH, EXPLORER, ...
```

The check of the template takes place before the collection, so as not to do it for nothing.

A file designated by `--prompt` must exist. The default template, for its part, may be missing when the script was copied alone: the collection is then done without a prompt, and the log reports it. With `--prompt-only`, whose prompt is the goal, the script stops.

With `--prompt-only`, the template must place `{{GAME_PGN}}` in a line of text, and not in a note: without the game, the prompt would have nothing to have analyzed. If the marker is placed under a condition that does not apply to the game, the prompt is written, but the log warns that it cannot be pasted alone.

A template written before version 5.0.0, with the directives `si`, `sinon` and `fin` and the French values, is refused in the same way, at its first marker of the old language, `{{DEPOT}}` for example: its directives, conditions and values must be renamed.

## 13. The checker in detail

The README says how to run the script. This section gives what it checks and its exact rules.

### What is checked, at a glance

| Check | Flaws found |
|---|---|
| Reading | file outside UTF-8, illegal move in the game or in a variation, blank line in the body of the game, second game in the file |
| Main line | different from the original game |
| Format | line of more than 79 characters, opening or closing brace in a comment, word outside the braces, move written with a `P`, castling written with zeros, `%`, em dash, suffix notation, tags missing or out of order, end marker |
| Commented moves | mistake or blunder of Stockfish left without a comment within the agreed scope, position NAG contrary to the evaluation of the engine; for information, the quality NAGs of another opinion than the engine. The notes that the original game already carried, which both prompts ask to keep, are set aside first: only the text of the LLM is judged |
| Evaluations | figure or mate quoted that exists nowhere in the data of the engine; a `#7` without a sign, which may be a rank, is only a warning |
| Variations | variation written inside a comment, hence not playable, illegal or too long variation |
| Conversation | FEN invalid or foreign to the game, em dash |

### Three flaws seen in real PGNs

- **The blank line in the body of the game.** python-chess sees the end of the game there and does not read what follows. The script finds it wherever it is, even if it only hides a variation or the end marker, then goes on with its checks on the file once the line is removed. Inside a comment, python-chess reads on up to the closing brace: the report says so, and still counts the line as a fault, the prompt forbidding it and another reader stopping there.
- **The words outside the braces.** python-chess skips them without a word: free text written between two moves is lost, and a move written `Pg2xf3`, or a castling written `0-0`, is read all the same, which hides the flaw. The script names each of these words, line by line.
- **The variation written between braces.** It is only text, SCID does not replay it. The script replays it itself to say whether it is legal and whether it comes from a line of the engine.

### What it reads

Three files of the archive: `game.pgn`, `summary.md` and `stockfish/evaluations.json`. It takes them in the zip, or in a folder: the working folder itself, or the one that contains it.

The three files always come from the same collection. In a parent folder, only a complete collection is kept, and the report names it: an interrupted collection kept beside it is ignored. If the folder contains several complete ones, the script stops and names them, rather than choosing one.

If one of them is missing, or if the archive cannot be read, no check takes place and the exit code is 2. An archive written before version 5.0.0, with its French names, is in this case.

Like `ianalyze.py`, it restarts in the virtual environment when python-chess is missing, but only at its default location: it has no `--venv` option.

Of the PGN returned, python-chess reads only the first game: a second one in the file is reported as a failure, nothing of it being checked. A result repeated alone at the end is not a game, as for `ianalyze.py`. The blank lines of the body are removed for the following checks, but only in the body of the first game: the blank line that opens the tags of another game stays, which used to merge the two games into one.

### Markers of the report

| Marker | Counts as | Example |
|---|---|---|
| `FAIL` | a failure, the exit code is 1 | a mistake of Stockfish left without a comment |
| `WARNING` | a point to look at, without a failure | a variation of more than 5 plies |
| `INFO` | a measure | the number of commented moves |
| `OK` | a check passed | |

The report ends with its totals, under `=== Totals ===`: the number of failures and of warnings.

Exit code: 0 without `FAIL`, 1 with at least one `FAIL`, 2 if no check could take place.

### Rules with figures

- **Lines**: 79 characters at most.
- **Overview**: a comment before the first move. Its absence is a failure.
- **Signs forbidden in a comment**: brace, percent sign, em dash. A semicolon counts as `WARNING`.
- **Outside the comments**: only moves in standard notation, move numbers, NAGs, the parentheses of the variations and the result. Any other word is a failure, named with its line: free text, which python-chess skips without a word, a move written `Pg2xf3`, which it reads as `g2xf3`, a move written with a hyphen between its squares. The rule is stricter than that of `ianalyze.py`, which reads the PGNs of every site. Castling written with zeros, `0-0`, which python-chess reads as `O-O`, is a failure of its own, outside `--prompt-only`. The words of a comment cut too early by a closing brace stay counted in that single flaw.
- **Blank line**: in the body of the game, it is a failure. Inside a comment, python-chess reads on up to the closing brace: the report says so, the prompt forbidding the line all the same.
- **Tags**: the seven mandatory ones at the top and in order, their values taken from the original game. The others in alphabetical order, Annotator filled in and PlyCount exact, otherwise `WARNING`.
- **Notes of the original game**: both prompts ask to keep them ahead of the comment of the LLM. The script takes them out of each comment first, before move 1 and after each move of the main line, whatever the line breaks, one after a hyphen included, the commands of a site left out and a `%` written "percent" or not. What remains is the text of the LLM, the only one judged: a figure quoted in a note is not an evaluation made up, and a move that only carries its original note is not commented on. The report counts the notes kept.
- **Commented moves**: each mistake and each blunder of Stockfish must be. One of them commented on without a NAG counts as `WARNING`, outside `--prompt-only`. The total number of commented moves is given for information, the prompt aiming at 15 to 25.
- **Scope**: the prompt limits the comments to the agreed scope. A mistake played beyond it is not expected. The scope is the first number of your answer to the startup question, read in the instructions of `summary.md`: "the first 20 moves" counts as 20 moves, but "moves 15 to 30" counts as the first 15 moves: give `--scope` when it does not fit. An answer without a number, or left at its default, counts as the whole game. `--scope N` gives it by hand, when it was agreed in the conversation.
- **Position NAGs**: `$14`, `$16`, `$18` and `$20` give White better, `$15`, `$17`, `$19` and `$21` Black. Such a NAG is contrary to the engine when the engine gives the other side better by at least half a pawn, or a mate. `$10`, an equal position, is not compared: put on a won position, it goes through.
- **Quality NAGs**: `$6` for an inaccuracy, `$2` for a mistake, `$4` for a blunder. Another opinion than the one of the engine is given for information, with the move and its loss: another of these three NAGs, `$1` or `$3` on a mistake or a blunder, or `$6`, `$2` or `$4` on a move that the engine does not classify, its loss staying under 50 cp.
- **Variations**: 5 plies at most, otherwise `WARNING`. A variation is said to be backed by the engine when its first two moves are those of a line that the engine gives for this ply.
- **Positions quoted in the conversation**: a FEN must be valid and come from a position of the game, recognized by its first four fields once written as python-chess writes it: the en passant square, which the standard writes after any double step of a pawn, only counts if the capture can be played. Two FENs are asked for, otherwise `WARNING`.

### Evaluations quoted

An evaluation is recognized by its sign: `+0.35`, `-1,20`, `+ 0.35`, the typographic minus sign, or `#-3` for a mate. A number without a sign is not one, except for a mate: `#2` is read as `#+2`, the form of the folder.

It must exist in `evaluations.json`, for the move played or for one of the best moves, as it is or rounded to one decimal: `+0.35` may be quoted `+0.4` or `+0.3`. A third decimal at zero adds nothing: `+0.350` is read `+0.35`; any other third decimal is a precision that the engine did not give. A `#7` without a sign that is not found there is only a `WARNING`: it may be a rank, "mistake #7", as well as a mate.

A difference that the LLM computed between two evaluations, `+1.77`, exists nowhere in the data: it is reported as invented, like a made-up figure.

The report quotes the PGN and the text returned by the LLM: their control characters are shown as `?`, never played by the terminal. A character that the output cannot represent becomes `?` too, and the report goes to its end.

### With `--prompt-only`

The short prompt asks for less than the full prompt. The checks that it does not ask for are skipped: length of the lines, overview, NAGs, percent sign, semicolon, em dash, suffix notation, castling written with zeros, alphabetical order of the other tags, Annotator and PlyCount tags, length of the variations. The short prompt asks to copy the moves as they are: a game exported with `0-0` stays faithful with it. The words outside the braces, for their part, are checked: the short prompt asks for the comments between braces. With `--summary`, the em dash of the conversation and the number of FENs are not checked either: a quoted FEN must only be valid and come from the game.

The tags are checked differently. The full prompt wants the seven mandatory tags of the PGN standard, in their order. The short prompt only asks to copy those of the game: among the seven, only those that the original game carries are expected, in the order in which it writes them.

The words outside the braces are checked differently too. The short prompt asks to copy the moves without changing a single one: a word that the original game itself writes outside standard notation, `e2-e4` or `bxa8Q`, which `ianalyze.py` reads, is accepted as it is.

### What it does not judge

It does not judge the quality of the commentary. A wrong but well-formed explanation goes through: an LLM can put a queen on the wrong square in a sentence without any check seeing it.\
This reading stays yours, and [TRIALS.md](TRIALS.md) shows how often it is needed.

Two limits come on top of those given with each rule above, the rounded evaluations, the computed differences, the position NAGs compared and the scope read:

- A number written without a sign, "7.77", is not taken for an evaluation: the script would confuse it with a duration or a rating. An invented figure written this way thus goes through
- The script finds a figure that exists nowhere, not a real figure given to the wrong move

## 14. Sources and links

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
- Correspondence, ICCF: [ICCF Rules, in force since 1 January 2026](https://webfiles.iccf.com/rules/2026/2026%20ICCF%20Rules%2C%20260311.pdf), section 2.4 (PDF)
- Correspondence, clock: [rules of chess-mail.com](https://www.chess-mail.com/index.php?page=reg)

Conventions of the repository:

- [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) for `CHANGELOG.md`
- [Semantic Versioning](https://semver.org/) for the version numbers

## 15. Taking over the project

This section is for whoever takes the code over: how it is laid out, how to change it without breaking it, and how a version is published.

### Layout of `ianalyze.py`

The script is a single file, run as a whole by `main()`, in this order:

1. The options, read by `analyser_arguments()`, which builds the command line with argparse, in groups, then checks their consistency.
2. The actions that stop there: `--install-venv`, by `installer_venv()`, and `--purge-settings`.
3. The restart in the virtual environment, when python-chess cannot be imported: `relancer_dans_venv()` runs the script again with the Python of the environment, and a marker in the environment prevents a loop. `--install-catalog`, by `installer_catalogue()`, comes after it: it needs python-chess.
4. The settings: `lire_reglages()`, or `reglages_vides()` with `--no-settings`.
5. The prompt template, checked before anything is collected: `chemin_modele()`, then `verifier_modele()`.
6. The game: `lire_fichier_texte()` and `decoder_octets()` for a local file, `extraire_id()` and `telecharger_pgn()` for Lichess, then `charger_partie()`, which first runs the lexical check of `controler_lexique()`.
7. The token and the catalog, without `--no-explorer`: `lire_jeton()`, `lire_catalogue()`.
8. The engine, checked before the questions: `verifier_moteur()`, `verifier_options_moteur()`.
9. The startup questions: `completer_reglages()`, `completer_entetes()`, `recueillir_contexte()`. Every answer goes through `demander()`.
10. The working folder, then the explorer, `collecter_explorateur()` with the class `Explorateur`, and the engine, `collecter_stockfish()`.
11. The files: `collection.json`, `summary.md` by `ecrire_synthese()`, the archive by `archiver()`, then the prompt, drawn by `rendre_modele()`.

The path that `annoncer_archive()` writes alone on standard output is that of the archive, or of the prompt with `--prompt-only`.\
Every text file is written by `ecrire_texte()`, under a temporary name, `.<name>.partial`, then renamed: no file is ever left half written (section 10).

### The tables to know

| Name | Role |
|---|---|
| `VERSION` | the version of the script, the only place to change: the User-Agent `UA` derives from it |
| `CLEFS_COLLECTE` | for each option, its key in `collection.json`: the dest of argparse stay French in the code, the archive is in English |
| `PROMPT_CONDITIONS`, `PROMPT_VALEURS` | the conditions and the values that a template may use (section 12), computed in `main()` |
| `REGLAGES_CLEFS` | the keys of `settings.ini`, with their comments |
| `SEUIL_IMPRECISION`, `SEUIL_ERREUR`, `SEUIL_GAFFE` | the losses, in centipawns, from which a move is an inaccuracy, a mistake or a blunder: 50, 100 and 300 |
| `EXEMPLES` | the examples at the end of `--help` |

### Adding an option

1. Declare it in its group of `analyser_arguments()`, with its check after the reading of the command line if it needs one.
2. Give it its key in `CLEFS_COLLECTE`: the name of the option without its two leading dashes, its hyphens becoming underscores, `no_questions` for `--no-questions`. T87 fails as long as an option has no key, or a key no option.
3. If it has a default in the settings, as `--usernames`: `REGLAGES_CLEFS` and `completer_reglages()`.
4. If the prompt uses it: a condition or a value, added to `PROMPT_CONDITIONS` or to `PROMPT_VALEURS` and computed in `main()`.
5. A test in `tests/test-app.sh`, and the documentation in both languages: [EXAMPLES.md](../EXAMPLES.md) with its real output, the README if the everyday use changes, this document, and the line of the test in [TESTS.md](TESTS.md). The CHANGELOG under Unreleased.

### The checker

`verify-analysis.py` reads the archive with `lire_archive()`, then makes its checks in the order of its report:

| Section of the report | Function |
|---|---|
| 1. Reading the PGN | `controler_lecture()` |
| 2. Main line | `controler_partie()`, then `retirer_notes()`, which sets aside the notes of the original game |
| 3. Format | `controler_format()` |
| 4. Commented moves | `controler_couverture()` |
| 5. Evaluations quoted in the PGN | `controler_chiffres()` |
| 6. Variations | `controler_variantes()` |
| 7. Conversation: positions quoted, language | `controler_synthese()`, with `--summary` |
| 8. Evaluations quoted in the conversation | `controler_chiffres()` again |

Sections 4 and 6 only run on a main line identical to the original game. `afficher()` writes the report and its totals.\
The short mode, `--prompt-only`, skips what the short prompt does not ask for (section 13).

### The test suite

`tests/test-app.sh` is a POSIX shell script: it runs under dash, bash and posh. Its helpers:

| Helper | Role |
|---|---|
| `titre` | opens a test: "Tnn: what it checks" |
| `lancer` | runs the script with the settings file of the tests: standard output in `sortie`, the log in `journal`, the exit code in `RC`, the archive in `ARCH` |
| `piloter` | runs it on a pseudo-terminal, the answers given in a single argument, separated by vertical bars |
| `verifier`, `egal` | a check: a command that must succeed, or an expected value |
| `sauter` | a check that cannot run here |
| `joindre` | attaches an extract of a file to the report |

Checks are counted, not tests. A test is a `titre`, a run, then its checks, each one labelled with the number of its test; [TESTS.md](TESTS.md) gives it its line.

Two traps were met for real:

- One suite at a time on a machine: M2 counts the engine processes of the whole machine, and sees those of another suite.
- The pseudo-terminal driver answers after a second of silence: on a slow machine, a Raspberry Pi, the answer can come before the question. A question ends without a line break: a check counts its occurrences, never its lines.

### Conventions

- The names of functions, variables and constants are in French; the comments, the docstrings, the messages and the documentation in English.
- No em dash, no guillemets, no emoji in the scripts.
- The README, `EXAMPLES.md` and each document of `docs/` have a French version, `.fr.md`, on the same plan, kept up to date in the same change. The CHANGELOG is in English only.
- Every change of behavior comes with a test and with its documentation, in both languages.
- No code is removed to "optimize": a removal that is needed is said in the commit.

### Checks before a commit

On the scripts: `python3 -m py_compile`, `flake8`, `ruff check`, `mypy`, `bandit`, `codespell` and `vulture`. `mypy` must see python-chess, which lives in the virtual environment: `mypy --python-executable local/venv/bin/python3 ianalyze.py verify-analysis.py`. Without this option, it reports the imports of python-chess as missing. On the suite: `shellcheck`, `checkbashisms`, and `sh -n`, `dash -n`, `bash -n`, `posh -n`. Then, when the code, the prompt templates or the tests change, the suite itself, offline under `sh` and under `posh`, and with `--network`: the date and the time of the last runs that passed go into [TESTS.md](TESTS.md#1-running-the-tests), section 1. A change of the documentation alone does not need it.

Some remarks are known and accepted:

- `ruff`, version 0.16 without a configuration file: UP031, the formatting with `%` being the style of the house, three DTZ005, `datetime.now()` without time zone, for a local time wanted, and one S110, the `try`/`except`/`pass` that `bandit` reports too
- `bandit`: eleven remarks, on the launch of processes, by `subprocess` and `os.execv`, on `urllib` and on this `try`/`except`/`pass`
- `flake8`: one line of 81 characters, the signature of `ecrire_synthese()`
- `vulture`: `redirect_request`, a method of urllib redefined
- `codespell`: the French identifiers
- `mdl`: MD013, the documents writing one sentence per line

### Branches and versions

- Work goes on the branch `dev`; `main` only receives the published versions.
- `dev` also carries `CLAUDE.md`, the working notes of the assistant used to develop the project, which `main` does not publish: each merge removes it with `git rm -f CLAUDE.md`. That is why `main` is not an ancestor of `dev`, and why each merge stops on a modify/delete conflict on this file, settled by the same command.
- The versions follow [Semantic Versioning](https://semver.org/), the CHANGELOG [Keep a Changelog](https://keepachangelog.com/en/1.1.0/): between two merges, everything goes under Unreleased.

A version is published in this order:

1. On `dev`, a commit "Version X.Y.Z": `VERSION`, the title of the version in the CHANGELOG and its link references.
2. The suite with `--network` run again on each test machine, and the table of the machines of [TESTS.md](TESTS.md#1-running-the-tests), section 1, updated in both languages.
3. On `main`, the merge of `dev`, titled "IAnalyze X.Y.Z".
4. An annotated and signed tag, `vX.Y.Z`, made with `git tag -s`.
5. A GitHub release of the same name.
