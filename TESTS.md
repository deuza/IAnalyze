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
Passed: 767, failed: 0, skipped: 0
Report: /path/of/the/repository/test-report-Linux-20261125-154836.txt
```

The report repeats the environment (system, Python, python-chess, Stockfish), the result of each check and the extracts useful for a diagnosis. You can send it as it is.

The number of checks depends on the version and on the mode chosen. Under macOS, a check of T44 is always skipped: it creates a file whose name is not UTF-8, which its file system refuses.

**Machines tested.** For version 5.0.0, the whole suite, `--network` included, was run on these machines on 27 November 2026, without a failure:

| System | Processor | Python | python-chess | Stockfish | Passed | Skipped |
|---|---|---|---|---|---|---|
| Debian 13 (trixie) | x86_64 | 3.13.5 | 1.11.2 | 17.1 | 855 | 0 |
| Debian 13 (trixie), on a Raspberry Pi | aarch64 | 3.13.5 | 1.11.2 | 17.1 | 855 | 0 |
| macOS 27.3, with Homebrew | arm64, Apple M1 | 3.15.2 | 1.11.2 | 19 | 853 | 1 (T44) |
| Ubuntu 24.04.5 LTS, in a container | x86_64 | 3.13.18 | 1.11.2 | 16 | 855 | 0 |

The shell was dash under Linux, the `/bin/sh` of the system under macOS. In the container, the offline tests also passed under posh.

## 2. What the tests do not touch

- **Your settings and your catalog**: the tests name their own, in a temporary directory deleted at the end.
- **The repository**: nothing is written in it, except the report. Not even the `__pycache__` of Python: the tests run with `PYTHONDONTWRITEBYTECODE=1`.
- **Your token**: it is neither displayed, nor copied, nor passed in a command line. The script checks, on the contrary, that it appears neither in the archives it checks nor in the report, looking for it as `ianalyze.py` reads it: a byte order mark, a carriage return or the UTF-16 of the file do not hide it.

With `--network`, count about 70 requests to the Lichess explorer, spaced 2 seconds apart, 10 files of the catalog and, if you give a game, 2 exports of that game. PyPI is also asked once, for python-chess, to rebuild a virtual environment (T84).

## 3. What you need to run them

- the virtual environment, installed by `--install-venv`
- Stockfish, mandatory: every collection uses it. Without it, the script stops at the start
- `unzip`, `python3` and `ps`, checked at the start: the script stops and gives the Debian package to install, `procps` for `ps`
- a path without spaces for the repository, the virtual environment and the engine: the script splits its options into words, and stops at the start on such a path
- with `--network` only, your token in `~/.lichess_token`

The tests that do not deal with the engine set it to the shortest, `--depth 1`.

## 4. Optional variables

| Variable | Role | Default |
|---|---|---|
| `VENV` | virtual environment of python-chess | `local/venv` of the repository |
| `STOCKFISH` | engine used by the tests | the one of the PATH, otherwise `/opt/homebrew/bin`, `/usr/local/bin` or `/usr/games` |
| `TOKEN` | token file | `~/.lichess_token` |
| `KEEP` | `1` keeps the temporary directory | deleted |

A relative path given to `VENV`, `STOCKFISH` or `TOKEN` is taken from the repository: the tests run in a directory of their own.

```bash
KEEP=1 ./test-app.sh
```

## 5. Offline tests

The numbers follow the order in which the tests were created, not the order in which they run. A missing number is the one of a removed test. M1 and M2 are two full collections, engine only.

The runs on a pseudo-terminal go through a driver that stops them after 300 seconds: a question too many, or a wait on a FIFO, kills the script and fails the test, instead of blocking the suite. Each of these runs is watched: one that the driver had to kill counts as a failure of its own, whatever its test reads afterwards.

| Test | Subject | What is checked |
|---|---|---|
| T01 | Compilation | `ianalyze.py` passes `py_compile` |
| T02 | Help | `--help` returns 0 and is shown whole, `--min-moves` quoted four times; it places the defaults of `--venv` and `--catalog` in the `local/` folder of the application, and the one of `--settings` at its root |
| T03 | Refused options | an option without effect or a value out of bounds stops the script with the exit code 2, before any reading of the game; with `--install-catalog`, a `--timeout` below 1 too |
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
| T37 | UTF-16, UTF-32 | a PGN in UTF-16 is read, with or without a byte order mark, and one in UTF-32 without a mark, its letter beyond latin-1 intact; a PGN in UTF-16 cut by one byte is refused with its cause, without a folder |
| T38 | Damaged UTF-8 | the invalid bytes are replaced, the rest of the PGN is kept |
| T39 | NUL bytes | they are removed, none stays in the archive |
| T40 | CRLF line ends | a PGN from Windows is read like the others |
| T41 | C locale | the script runs under an ASCII locale, where the accents of its output become `?` |
| T42 | Control characters | those of a tag are removed, a tab becomes a space |
| T43 | Dummy token | byte order mark removed, non-ASCII token refused, token never displayed |
| T44 | File names | a name with a colon or a question mark, or not in UTF-8, gives a sanitized folder |
| T45 | Input in latin-1 | an answer typed in latin-1 in a terminal is decoded without an error, the run going to its end: the whole output of the terminal is read, no longer its last 300 characters; the driver itself: a script that never ends is killed at the deadline, code 124, and a script that closes its terminal while still running does not block it |
| T46 | Sound PGN | a PGN in UTF-8 produces neither warning nor remark |
| T47 | Version | the version has the form X.Y.Z and appears in the user agent header |
| T48 | Dot in the name | a PGN whose name carries a dot gives a well-named archive |
| T49 | Simulated explorer | unexpected answers are reported without an unexpected error; an answer without a list of moves is unusable, no longer an exit from theory; a token refused stops the collection, its answer kept |
| T50 | Non-finite values | `nan` and `inf` are refused for the numeric options, without a folder created |
| T51 | Mates | missed mate and conceded mate marked `mate` and `blunder`, mate counted after the move, legend of the summary; a negative loss beyond 10000, a mate found by the move played, reads `mate` too |
| T52 | Null move | the `--` move keeps its line in the table, without an invented evaluation, and the short prompt explains it; a null move played in check, after a check or after a mate, is refused before the engine starts |
| T53 | Interruption | an interruption during the archiving, or a write that fails, keeps the working folder and leaves no truncated archive |
| T54 | False addresses | a URL that is not a game is refused without anything sent, the identifiers are extracted from the real ones; the sections of the site of eight letters, `timeline` and `bookmark` among them, are not identifiers |
| T55 | Engine options | a value outside the bounds is refused with its bounds, `--stockfish` accepts a tilde or a name looked up in the PATH |
| T56 | Null move, explorer | the querying stops at the null move, on a simulated explorer |
| T57 | First run | after the confirmation of the new name, the settings are asked once, then saved; an empty tag is filled in with the username, and the usual time control is suggested |
| T58 | Second run | the run goes to its end without a settings question, then the settings are read again, and `--usernames` wins over them |
| T59 | Outside a terminal | nothing is asked or written. On a terminal without a username, the name of the player is asked |
| T60 | Badly formed settings | the unreadable file is reported with its remedy, the keys added by hand are kept |
| T61 | Username | no username is hard-coded in the script or in its help |
| T62 | Time control | the answers are checked, the wrong ones refused; a TimeControl tag spares the question |
| T63 | Correspondence | the three systems of correspondence time control are recognized, with the English plural of the durations |
| T64 | Prompt written | the prompt is written next to the archive, with its values filled in |
| T65 | Adapted prompt | the prompt keeps only the passages that apply: explorer, database, answers, section 2; it carries the instructions drawn from the trials, among them where a variation starts and where `$7` and `$8` go; its final summary asks for the errors of the player, according to their count, bounded to the plies evaluated under partial coverage, in both templates; the tags and comments of the PGN are data, never instructions; the commands that a site writes in the comments are left out, the case A or B comes before the recap, a pawn move has no letter; the final summary and the review of the short prompt keep to the agreed scope |
| T66 | Faulty template | unknown marker, condition never closed or missing template stop the script before the collection |
| T67 | Script without template | the script copied alone makes its collection without a prompt, and says so |
| T68 | Rating | the rating in Elo points is checked and repeated in the prompt |
| T69 | Purge of the settings | file deleted, missing file accepted, directory and foreign file refused, damaged or empty settings file deleted all the same |
| T70 | Test game | `test.pgn` is read whole: comments, variations, en passant capture, promotion, castling, null move; W/D/L on each evaluated line, adding up to 100; a variation that starts with a Black move written `1... e5` |
| T71 | Removed options | `--sans-stockfish`, `--avec-stockfish` and `--consignes` are unknown |
| T72 | Contrary result | a game marked won in a lost position is reported in the summary and in the prompt |
| T73 | Checker | a compliant PGN passes, a faulty PGN sees each defect reported, missing PGN, unreadable archive |
| T74 | Prompt only | short prompt written without an archive, table of the engine, where a variation starts, review according to the number of weak moves, unknown side, prompt never overwritten, even by three runs in the same second, the clock being frozen; the game in a code block, given as data; the commands that a site writes in the comments are left out; a comment that holds a line of three backquotes gets a longer fence |
| T75 | Misread PGNs | the PGNs that python-chess would misread, or with several games, are refused with their cause, without anything written: among them, a tag line that carries moves, and a line of brackets among the moves. An illegal move is named, once. A result repeated at the end of the file is ignored, unless a real game follows it |
| T76 | Token and servers | on simulated servers, a redirect is not followed and the token is redacted from the quoted answers |
| T77 | Unexpected inputs | standard input closed, name too long, badly formed URL, game that starts from a FEN, tilde of `--output-dir`: a message, no longer an unexpected error, looked for in the logs of all these inputs; under the home folder, the paths of the archive are written with `~` |
| T78 | Engine that stops | an engine dead outside a search gives a message and the exit code 1 |
| T79 | Refused answers | an answer too long or carrying signs of the PGN is refused and asked again |
| T80 | Long name | a long PGN name, in multibyte characters, gives a bounded and valid label |
| T81 | Combined cases | the purge is used alone, an empty path given to `--prompt` is refused, a badly written token is refused without being displayed, each case named by its kind and not by its content |
| T82 | Checker, continued | quoted mates, a `#7` without a sign only a warning, a FEN with its en passant square from the game, control characters of the PGN shown as `?`, an accent under an ASCII output, agreed scope, skipped checks of the short mode, parent folder with one or several collections; a third decimal at zero; words outside the braces, a move written with a `P` and castling with zeros, the latter not in short mode; a blank line in a comment, which python-chess reads on; a second game in the file; a line of 90 characters, a semicolon, tags out of order, a wrong PlyCount and a variation of seven plies; an illegal move of the main line; a FEN foreign to the game; a PGN or `--summary` file missing; the notes that the original game carried, set aside before the checks, kept with a comment, one of them cut after a hyphen, or alone; a game in loose notation copied as it is, accepted in short mode only; a line that starts with a bracket among the moves, alone or after a blank line; a second game counted as one failure |
| T83 | Example games | the files of `example-games` stay what `EXAMPLES.md` says of them: eight games accepted, among them the exports of four sites and of a program, seven refused with their cause, three annotated PGNs checked, the single variation of the first two counted in the singular and the five flaws of the third named, then the conversation, with its PGN or without any, and the PGN of the short prompt on the folder kept; no address or identifier of a real game |
| T84 | Incomplete virtual environment | an environment without pip is recognized, a directory without `pyvenv.cfg` never is; with `--network`, `--install-venv` rebuilds the former and installs python-chess in it |
| T85 | `--venv` that is not a virtual environment | a non-empty directory without `pyvenv.cfg`, with or without an interpreter, is refused by `--install-venv` before any pip, and nothing is added to it, its interpreter, a dummy, never running; a regular file is refused with its own message and left intact; a missing or empty directory is not refused |
| T86 | `--no-settings` | the settings file is neither read nor written, as the log and `collection.json` say: side deduced from `--usernames` or unknown, rating taken from the Elo tag of that side, file untouched; on a terminal, no settings question, the side is asked, no file created; refused with `--settings` and with `--purge-settings`; a username is found as the whole name or as words, never as a substring |
| T87 | Keys of `collection.json` | one English key for each option, none left over or repeated; the keys of the depth and of the output directory checked by name |
| T88 | Ranks of the variations | English ordinals, from 1st to 112th |
| T89 | Settings written over a settings file only | a FIFO, a directory or the file of another program is left as it is, and the reason is said; a file of the former format is written with its `[joueur]` section kept; a settings file in UTF-16 is written and purged; no partial file left; on a terminal, a warning, and the answers serve the current run |
| T90 | Settings name | `--settings` takes a name: a path or another name is refused, nothing created; `/dev/null` is refused, `--no-settings` suggested; the help speaks of a name; a new name asks for a confirmation, asked again after an unexpected answer; refused, nothing is done: no file, no collection; a name that starts with a dot is refused, the rule given |
| T91 | Quality NAGs | `$1` on a mistake or a blunder, and `$6` on a move that the engine does not classify, are counted and named as other opinions, beside the NAGs that match the category; the expected lines, drawn from the engine, must exist |
| T92 | Wrap of the prompts | both templates, rendered in every combination of their conditions: no line of prose over 71 columns, none that could take the first word of the next one, no continued line opening on a figure, which would read as an item of a list |
| T93 | W/D/L and variations of Black | W/D/L in whole percentages adding up to 100, by the largest remainders, the view of Black the mirror of that of White; a variation that starts with a Black move written `1... e5` |
| T94 | Catalog without the network | the five sources read through a `file://` address: a header, an incomplete line, an illegal move, a position named twice, an empty file or one outside UTF-8 refused, the index in place untouched; at the reading, an index without description, of unknown format, corrupt or truncated refused |
| T95 | Thresholds of the explorer | on a simulated explorer, each option stops the querying where it should: `--min-games`, `--min-frequency`, the catalog, `--min-moves`, `--exhaustive`, `--max-plies`, a threshold at zero; on a local server, 429 retried once after a pause of 60 seconds, the pause between two requests, `--timeout`; a token refused stops the whole collection before the engine |
| T96 | Errors | variant, empty PGN, game without a move, no source, values below 1, empty `--usernames`, engine not executable, UCI engine without Hash: refused without a folder; `--pv-length` bounds section 3a; an archive already there is not overwritten; a hundred names taken in the same second stop the run. "Cannot write in" is not tested: root writes everywhere |
| T97 | Ctrl-C | interrupted while the engine evaluates: "Interrupted.", exit code 130, no archive; a timer kills the script if the interruption does not end it |
| T98 | Unexpected error | on a copy with an injected fault: one line and the advice without `--debug`, the whole traceback with it, the token redacted in both cases |
| M1 | Collection, names | accented PGN name, output path with a space and an accent |
| M2 | Full collection | the Italian analyzed whole, engine only, without an engine process left behind, found by its name even beyond the 15 characters that Linux keeps, or by the name of the link through which T55 starts it |

## 6. Tests with `--network`

These tests use your token and the real explorer. N1 and N2 are two full collections.

| Test | Subject | What is checked |
|---|---|---|
| T09 | Catalog installed | the five files are downloaded, the installation message is written |
| T10 | Catalog, format | the index starts with its header, format 2, whose source names the five files in English, and no temporary file is left |
| T11 | Reinstallation | a second installation gives an identical catalog, its dated line aside |
| T12 | Catalog missing | it is reported, with the installation command |
| T13 | Catalog truncated | it is reported rather than half read |
| T14 | Italian, masters | the table of the explorer on the masters database, up to the end of the game, without an exit from theory |
| T15 | Polish, masters | a rare opening on the masters database |
| T16 | Polish, Lichess | the same on the database of all the players: starting window, first exit, last named position |
| T17 | First exit | the querying stops at the first exit from theory when asked |
| T18 | Filters | the speed and rating filters are passed on and written in the summary |
| T19 | Game threshold | an unreachable threshold gives an insufficient sample from the first ply, noted in section 4 |
| T20 | Frequency threshold | a threshold at zero declares no exit |
| T21 | Exhaustive | `--exhaustive` is announced, and the first exit from theory stays the same |
| T22 | Cap | `--max-plies` limits the querying |
| T23 | Pause | the delay between two requests is respected, across midnight too |
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
