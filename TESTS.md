# IAnalyze, the tests

Version française : [TESTS.fr.md](TESTS.fr.md)

All the tests are run by a single script, `test-app.sh`, under Debian as under macOS.

This document says how to run it, then what each test checks. The detail, command by command, is in the script, which is authoritative.

The [README](README.md) explains the installation and everyday use, [EXAMPLES.md](EXAMPLES.md) the commands and their outputs, [TECHNICAL.md](TECHNICAL.md) how the script works.

## Contents

- [1. Running the tests](#1-running-the-tests)
- [2. What the tests do not touch](#2-what-the-tests-do-not-touch)
- [3. What you need to run them](#3-what-you-need-to-run-them)
- [4. Optional variables](#4-optional-variables)
- [5. Offline tests](#5-offline-tests)
- [6. Tests with `--network`](#6-tests-with---network)
- [7. The test game](#7-the-test-game)
- [8. The only test to run by hand](#8-the-only-test-to-run-by-hand)

---

## 1. Running the tests

From the repository, after the installation described in the README:

```bash
./test-app.sh
```

```bash
./test-app.sh --network
```

```bash
./test-app.sh --network <identifier or address of a Lichess game>
```

| Command | What it runs | Duration |
|---|---|---|
| `./test-app.sh` | the offline tests, without a token | about 3 minutes on a recent Mac, 6 on a Raspberry Pi |
| `./test-app.sh --network` | the same, then those that need the network and your Lichess token, except T24 | about 3 more minutes |
| `./test-app.sh --network GAME` | likewise, with T24: the download of the game you name | a few more seconds |

**The game of T24 is yours to choose.** The repository names no real game: T24 downloads the one you give after `--network`, by its identifier or by its address. Any Lichess game will do, yours or another one. Without it, T24 is counted as skipped, and the script reminds you of the command to run when it starts. The identifier given is not written in the report.

The script ends with a summary:

```text
Passed: 598, failed: 0, skipped: 0
Report: /path/of/the/repository/test-report-Linux-20261125-154836.txt
```

The report repeats the environment (system, Python, python-chess, Stockfish), the result of each check and the extracts useful for a diagnosis. You can send it as it is.

The number of checks depends on the version and on the mode chosen. Under macOS, a check of T44 is always skipped: it creates a file whose name is not UTF-8, which its file system refuses.

## 2. What the tests do not touch

- **Your settings and your catalog**: the tests name their own, in a temporary directory deleted at the end.
- **The repository**: nothing is written in it, except the report.
- **Your token**: it is neither displayed, nor copied, nor passed in a command line. The script checks, on the contrary, that it appears neither in the archives it checks nor in the report.

With `--network`, count about 70 requests to the Lichess explorer, spaced 2 seconds apart, 10 files of the catalog and, if you give a game, 2 exports of that game. PyPI is also asked once, for python-chess, to rebuild a virtual environment (T84).

## 3. What you need to run them

- the virtual environment, installed by `--install-venv`
- Stockfish, mandatory: every collection uses it. Without it, the script stops at the start
- with `--network` only, your token in `~/.lichess_token`

The tests that do not deal with the engine set it to the shortest, `--depth 1`.

## 4. Optional variables

| Variable | Role | Default |
|---|---|---|
| `VENV` | virtual environment of python-chess | `local/venv` of the repository |
| `STOCKFISH` | engine used by the tests | the one of the PATH, otherwise `/opt/homebrew/bin`, `/usr/local/bin` or `/usr/games` |
| `TOKEN` | token file | `~/.lichess_token` |
| `KEEP` | `1` keeps the temporary directory | deleted |

```bash
KEEP=1 ./test-app.sh
```

## 5. Offline tests

The numbers follow the order in which the tests were created, not the order in which they run. A missing number is the one of a removed test. M1 and M2 are two full collections, engine only.

| Test | Subject | What is checked |
|---|---|---|
| T01 | Compilation | `ianalyze.py` passes `py_compile` |
| T02 | Help | `--help` returns 0 and is shown whole, `--min-moves` quoted four times; it places the defaults of `--venv` and `--catalog` in the `local/` folder of the application, and the one of `--settings` at its root |
| T03 | Refused options | an unknown option or a refused value stops the script with the exit code 2 |
| T04 | PGN not found | the missing file is named, and a relative name is taken for a file, not for an identifier |
| T05 | Minimal collection | a single line on standard output; the archive exists and carries `summary.md` and `collection.json`, without a temporary file |
| T06 | Folder kept | `--keep-folder` leaves the working folder next to the archive |
| T08 | Output directory | `--output-dir` receives the archive, and the directory is created if need be |
| T25 | Engine limited | `--stockfish-moves` limits the analysis to the first moves, the summary and both prompts say so; Threads and Hash are recorded in `collection.json` |
| T26 | Engine not found | a missing binary stops the script with a message and the installation command |
| T27 | Token missing | the missing token file is reported before any request, without a working folder |
| T31 | Platform, `brew` | the `brew install` command is suggested under macOS, never under Linux |
| T32 | Platform, `apt` | the `apt install` command is suggested under Linux, never under macOS |
| T34 | Latin-1 | a PGN in latin-1 is read, an unrecognized encoding is refused without anything written |
| T35 | cp1252 | a PGN in cp1252 is read, curly apostrophe, dash and euro included |
| T36 | UTF-8 mark | the byte order mark at the head of the PGN is removed |
| T37 | UTF-16 | a PGN in UTF-16 is read, with or without a byte order mark |
| T38 | Damaged UTF-8 | the invalid bytes are replaced, the rest of the PGN is kept |
| T39 | NUL bytes | they are removed, none stays in the archive |
| T40 | CRLF line ends | a PGN from Windows is read like the others |
| T41 | C locale | the script runs under an ASCII locale, where the accents of its output become `?` |
| T42 | Control characters | those of a tag are removed, a tab becomes a space |
| T43 | Dummy token | byte order mark removed, non-ASCII token refused, token never displayed |
| T44 | File names | a name with a colon or a question mark, or not in UTF-8, gives a sanitized folder |
| T45 | Input in latin-1 | an answer typed in latin-1 in a terminal is decoded without an error |
| T46 | Sound PGN | a PGN in UTF-8 produces neither warning nor remark |
| T47 | Version | the version has the form X.Y.Z and appears in the user agent header |
| T48 | Dot in the name | a PGN whose name carries a dot gives a well-named archive |
| T49 | Simulated explorer | unexpected answers are reported without an unexpected error |
| T50 | Non-finite values | `nan` and `inf` are refused for the numeric options, without a folder created |
| T51 | Mates | missed mate and conceded mate marked `mate` and `blunder`, mate counted after the move, legend of the summary |
| T52 | Null move | the `--` move keeps its line in the table, without an invented evaluation, and the short prompt explains it |
| T53 | Interruption | an interruption during the archiving, or a write that fails, keeps the working folder and leaves no truncated archive |
| T54 | False addresses | a URL that is not a game is refused without anything sent, the identifiers are extracted from the real ones |
| T55 | Engine options | a value outside the bounds is refused with its bounds, `--stockfish` accepts a tilde or a name looked up in the PATH |
| T56 | Null move, explorer | the querying stops at the null move, on a simulated explorer |
| T57 | First run | after the confirmation of the new name, the settings are asked once, then saved; an empty tag is filled in with the username, and the usual time control is suggested |
| T58 | Second run | the settings are read again, and `--usernames` wins over them |
| T59 | Outside a terminal | nothing is asked or written. On a terminal without a username, the name of the player is asked |
| T60 | Badly formed settings | the unreadable file is reported with its remedy, the keys added by hand are kept |
| T61 | Username | no username is hard-coded in the script or in its help |
| T62 | Time control | the answers are checked, the wrong ones refused; a TimeControl tag spares the question |
| T63 | Correspondence | the three systems of correspondence time control are recognized, with the English plural of the durations |
| T64 | Prompt written | the prompt is written next to the archive, with its values filled in |
| T65 | Adapted prompt | the prompt keeps only the passages that apply: explorer, database, answers, section 2; it carries the instructions drawn from the trials, among them where a variation starts and where `$7` and `$8` go; its final summary asks for the errors of the player, according to their count |
| T66 | Faulty template | unknown marker, condition never closed or missing template stop the script before the collection |
| T67 | Script without template | the script copied alone makes its collection without a prompt, and says so |
| T68 | Rating | the rating in Elo points is checked and repeated in the prompt |
| T69 | Purge of the settings | file deleted, missing file accepted, directory and foreign file refused, damaged or empty settings file deleted all the same |
| T70 | Test game | `test.pgn` is read whole: comments, variations, en passant capture, promotion, castling, null move |
| T71 | Removed options | `--sans-stockfish`, `--avec-stockfish` and `--consignes` are unknown |
| T72 | Contrary result | a game marked won in a lost position is reported in the summary and in the prompt |
| T73 | Checker | a compliant PGN passes, a faulty PGN sees each defect reported, missing PGN, unreadable archive |
| T74 | Prompt only | short prompt written without an archive, table of the engine, where a variation starts, review according to the number of weak moves, unknown side, prompt never overwritten |
| T75 | Misread PGNs | the PGNs that python-chess would misread, or with several games, are refused with their cause, without anything written. A result repeated at the end of the file is ignored, unless a real game follows it |
| T76 | Token and servers | on simulated servers, a redirect is not followed and the token is redacted from the quoted answers |
| T77 | Unexpected inputs | standard input closed, name too long, badly formed URL, game that starts from a FEN, tilde of `--output-dir`: a message, no longer an unexpected error |
| T78 | Engine that stops | an engine dead outside a search gives a message and the exit code 1 |
| T79 | Refused answers | an answer too long or carrying signs of the PGN is refused and asked again |
| T80 | Long name | a long PGN name, in multibyte characters, gives a bounded and valid label |
| T81 | Combined cases | the purge is used alone, an empty template is refused, a badly written token is refused without being displayed |
| T82 | Checker, continued | quoted mates, agreed scope, skipped checks of the short mode, parent folder with one or several collections |
| T83 | Example games | the files of `example-games` stay what `EXAMPLES.md` says of them: eight games accepted, among them the exports of four sites and of a program, four refused with their cause, two annotated PGNs checked, no address or identifier of a real game |
| T84 | Incomplete virtual environment | an environment without pip is recognized, a directory without `pyvenv.cfg` never is; with `--network`, `--install-venv` rebuilds the former and installs python-chess in it |
| T85 | `--venv` that is not a virtual environment | a non-empty directory without `pyvenv.cfg`, with or without an interpreter, is refused by `--install-venv` before any pip, and nothing is added to it; a missing or empty directory is not |
| T86 | `--no-settings` | the settings file is neither read nor written, as the log and `collection.json` say: side deduced from `--usernames` or unknown, rating taken from the Elo tag of that side, file untouched; on a terminal, no settings question, the side is asked, no file created; refused with `--settings` and with `--purge-settings` |
| T87 | Keys of `collection.json` | one English key for each option, none left over or repeated; the keys of the depth and of the output directory checked by name |
| T88 | Ranks of the variations | English ordinals, from 1st to 112th |
| T89 | Settings written over a settings file only | a FIFO, a directory or the file of another program is left as it is, and the reason is said; a file of the former format is written with its `[joueur]` section kept; no partial file left; on a terminal, a warning, and the answers serve the current run |
| T90 | Settings name | `--settings` takes a name: a path or another name is refused, nothing created; `/dev/null` is refused, `--no-settings` suggested; the help speaks of a name; a new name asks for a confirmation, asked again after an unexpected answer; refused, nothing is done: no file, no collection |
| T91 | Quality NAGs | `$1` on a mistake or a blunder, and `$6` on a move that the engine does not classify, are counted and named as other opinions, beside the NAGs that match the category |
| M1 | Collection, names | accented PGN name, output path with a space and an accent |
| M2 | Full collection | the Italian analyzed whole, engine only, without an engine process left behind |

## 6. Tests with `--network`

These tests use your token and the real explorer. N1 and N2 are two full collections.

| Test | Subject | What is checked |
|---|---|---|
| T09 | Catalog installed | the five files are downloaded, the installation message is written |
| T10 | Catalog, format | the index starts with its header, format 2, and no temporary file is left |
| T11 | Reinstallation | a second installation gives an identical catalog, its dated line aside |
| T12 | Catalog missing | it is reported, with the installation command |
| T13 | Catalog truncated | it is reported rather than half read |
| T14 | Italian, masters | the table of the explorer and the exit from theory on the masters database |
| T15 | Polish, masters | a rare opening on the masters database |
| T16 | Polish, Lichess | the same on the database of all the players: starting window, first exit, last named position |
| T17 | First exit | the querying stops at the first exit from theory when asked |
| T18 | Filters | the speed and rating filters are passed on and written in the summary |
| T19 | Game threshold | an unreachable threshold gives an insufficient sample from the first ply, noted in section 4 |
| T20 | Frequency threshold | a threshold at zero declares no exit |
| T21 | Exhaustive | `--exhaustive` is announced, and the first exit from theory stays the same |
| T22 | Cap | `--max-plies` limits the querying |
| T23 | Pause | the delay between two requests is respected |
| T24 | Downloaded game | the game you name is downloaded by its address and by its identifier |
| T28 | Rights of the token | a token file readable by others is reported |
| T29 | Token and archive | the token appears neither in the archive nor in the log |
| T33 | Castling | both castlings appear in the table, none is given outside the database or at 0.0 % |
| N1 | Null move | the querying stops at the null move on the real explorer, without a refused request |
| N2 | Full collection | explorer and engine together |

The figures of the explorer change every month: these tests check forms and orders of magnitude, not exact totals.

## 7. The test game

`test.pgn` gathers in a single legal game what has already tripped up a PGN reader:

- accented tags
- comment before the first move, end-of-line comment introduced by a semicolon
- NAGs, `??` and `?` signs, clock comments `[%clk]`
- nested variations
- missed mate, en passant capture, promotion with capture and check, both castlings, a null move

The game has no chess interest. It also serves for a full trial, by hand:

```bash
./ianalyze.py test.pgn --no-questions
```

## 8. The only test to run by hand

Reinstalling your virtual environment touches your installation: `test-app.sh` does not do it, T84 only rebuilds an environment of its own.

```bash
./ianalyze.py --install-venv
```

Expected, on an environment already present: "Virtual environment already present", then "Installing python-chess in the virtual environment." and "Virtual environment ready".
