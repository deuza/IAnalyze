# Changelog

All notable changes to IAnalyze are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project applies [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `--no-settings`: for a single run, the settings file is neither read
  nor written, and its questions are not asked. The side is asked, or
  deduced from `--usernames`; the rating comes from the Elo tag of the
  player's side, and the time control from the TimeControl tag or from
  the question about the game, which then suggests "unspecified". The
  option is refused with `--settings`, whatever the name given, and
  with `--purge-settings`.
- `README.fr.md`, the French version of the README, kept up to date
  with it.
- `EXAMPLES.fr.md`, the French version of `EXAMPLES.md`, kept up to
  date with it.
- `TESTS.fr.md`, the French version of `TESTS.md`, kept up to date
  with it.
- `TECHNICAL.fr.md`, the French version of `TECHNICAL.md`, kept up to
  date with it.
- README, section Licenses: the icon of the CC0 license, linked to the
  page of the license, and a link to `LICENSE` in the sentence on the
  license of the repository.
- `example-games/tag-with-moves.pgn`,
  `example-games/bracket-among-moves.pgn` and
  `example-games/null-move-in-check.pgn`, for the new error messages of
  `EXAMPLES.md`, and `example-games/llm-faulty-words.pgn`, for the new
  checks of `verify-analysis.py`.
- `verify-analysis.py` checks the words of the PGN returned outside the
  comments: free text, a line that starts with a bracket among the
  moves, a move written with a `P`, a hyphen between two squares, and,
  for the full prompt, castling written with zeros are failures named
  with their line. python-chess skipped them, or read them, without a
  word. The tail of a comment cut too early by a closing brace stays
  counted in that single flaw. With `--prompt-only`, a word that the
  original game itself writes outside standard notation, `e2-e4` or
  `bxa8Q`, is accepted: the short prompt asks to copy the moves
  without changing a single one.
- `verify-analysis.py` reports a second game in the file returned, as
  one failure: only the first one is read and checked, its end marker
  included.
- `verify-analysis.py` sets aside the notes that the original game
  already carried, which both prompts now ask to keep, before it
  judges the comments, whatever their line breaks, one after a hyphen
  included, and counts them in its report: "notes of the original
  game: 2 kept out of 2". A figure quoted in a note is not an
  evaluation made up by the LLM, and a mistake that only carries its
  original note is not held as commented on.
- The value `{{FENCE}}` of the prompt templates: the fence of the code
  block that holds the game in the short prompt, a run of backquotes
  longer than any run of the game, three at least. With a fixed fence
  of three, a comment of the PGN that held such a line closed the
  block.
- `test-app.sh`, T93 to T98: W/D/L and the variations of Black; the
  catalog installed and checked without the network, from local
  sources; the thresholds of the explorer, the retry after a 429, the
  pauses, `--timeout` and a token refused, on a simulated explorer and
  local servers; the errors of the PGN, of the arguments, of the engine
  and of the archive, `--pv-length` included; Ctrl-C during the engine
  phase; an unexpected error with and without `--debug`, on a copy with
  an injected fault. New cases in T37, T45, T49, T51, T54, T65, T70,
  T74, T82, T83, T85 and T90, and the conversation and the PGN of the
  short prompt of `EXAMPLES.md` go through T83.
- The link references of this file, for `[Unreleased]` and the three
  tagged versions.

### Changed

- The comments and docstrings of `ianalyze.py`, `verify-analysis.py`
  and `test-app.sh`, and the comments of `.gitignore`, are in English.
  The code is unchanged: the Python syntax trees, docstrings set aside,
  and the shell code, comments set aside, are identical to those of
  version 4.0.2.
- The messages that `ianalyze.py` writes on standard error are in
  English: progress log, warnings, errors, and the command line help
  with its option descriptions, group titles, placeholders and
  examples. A warning now starts with "Warning" instead of
  "Attention".
- The messages of `test-app.sh` are in English: section titles, labels
  of the checks, report and errors. A failed check is now marked
  `FAIL` instead of `ECHEC`, a skipped one `SKIP` instead of `SAUTE`,
  and the summary reads "Passed: N, failed: N, skipped: N".
- Everything the script creates for itself now lives in the
  application folder: the virtual environment (`local/venv`) and the
  opening catalog in `local/`, and the settings in `settings.ini`, at
  the root of the folder. Both are ignored by git. Deleting the
  application folder removes everything, the Lichess token aside,
  which stays in `~/.lichess_token`; emptying `local/` brings the
  application back to a fresh clone and keeps the settings.
  `verify-analysis.py` and `test-app.sh` look for the virtual
  environment at the same place. The former locations,
  `~/.local/share/IAnalyze` and `~/.config/IAnalyze`, are no longer
  read: run `--install-venv` and `--install-catalog` again, then
  delete them by hand. The settings questions are asked again once:
  the settings file has a new format, see below.
- The command line options are in English, and their former names are
  no longer accepted. Those of `ianalyze.py`:

| Former name             | New name            |
| ----------------------- | ------------------- |
| `--installer-venv`      | `--install-venv`    |
| `--sans-questions`      | `--no-questions`    |
| `--pseudos`             | `--usernames`       |
| `--reglages`            | `--settings`        |
| `--purge-reglages`      | `--purge-settings`  |
| `--installer-catalogue` | `--install-catalog` |
| `--catalogue`           | `--catalog`         |
| `--sortie`              | `--output-dir`      |
| `--garder-dossier`      | `--keep-folder`     |
| `--sans-prompt`         | `--no-prompt`       |
| `--prompt-seul`         | `--prompt-only`     |
| `--base`                | `--database`        |
| `--cadences`            | `--speeds`          |
| `--classements`         | `--ratings`         |
| `--jeton-fichier`       | `--token-file`      |
| `--seuil-parties`       | `--min-games`       |
| `--seuil-frequence`     | `--min-frequency`   |
| `--jusqu-a-epuisement`  | `--exhaustive`      |
| `--coups-min`           | `--min-moves`       |
| `--max-demicoups`       | `--max-plies`       |
| `--sans-explorateur`    | `--no-explorer`     |
| `--coups-stockfish`     | `--stockfish-moves` |
| `--profondeur`          | `--depth`           |
| `--fils`                | `--threads`         |
| `--hachage`             | `--hash`            |
| `--longueur-pv`         | `--pv-length`       |
| `--delai`               | `--timeout`         |

- The values of `--database` are `lichess` and `masters`, formerly
  `maitres`. `--venv`, `--prompt`, `--pause`, `--multipv`,
  `--stockfish` and `--debug` keep their names.
- `verify-analysis.py` takes `--summary`, `--name`, `--prompt-only`
  and `--scope` instead of `--synthese`, `--nom`, `--prompt-seul` and
  `--perimetre`.
- `test-app.sh` takes `--network` instead of `--reseau`, and reads the
  variables `TOKEN` and `KEEP` instead of `JETON` and `GARDER`.
- The environment variable that marks the relaunch of `ianalyze.py` in
  its virtual environment is `IANALYZE_RELAUNCHED` instead of
  `IANALYZE_DEJA_RELANCE`.
- The questions asked in the terminal, and the answers they accept, are
  in English; the French answers are no longer understood. Beware of
  the side: `b` used to mean White (Blancs) and now means Black, White
  being `w`, in "Did you play White or Black? [w/b]". The time control
  is `[r]eal time`, `[c]orrespondence` or `[u]nknown`, a correspondence
  system a fixed `[d]elay`, a `[p]eriod` or a `[c]lock`, an increment
  `36h` or `3d`, and an unknown rating `unknown`. "(Enter: ...)" shows
  what the Enter key keeps.
- The settings file is in English: section `[player]`, keys
  `usernames`, `time_control` and `rating`, optional key `annotator`,
  and English comments. A time control is written `15+10`, `14 days`,
  `10 moves in 50 days` or `5 days + 36 hours, maximum 20 days, bank
  50 days`, and an unknown one `unknown`. The settings of version 4,
  `~/.config/IAnalyze/reglages.ini`, are not read: their questions are
  asked again. A `settings.ini` in the former format, copied by hand
  from `reglages.ini` or written by a development version, keeps its
  `[joueur]` section, as a section of your own, after the new `[player]`
  section. `--purge-settings` refuses such a file, which lacks
  `[player]`: delete it by hand, or run a collection first.
- The sentence that describes a time control is in English, in
  `context.md`, in the prompt and as the value suggested in the
  terminal: "rapid, 15 minutes + 10 seconds per move", "correspondence,
  clock of 5 days + 36 hours per move, maximum of 20 days",
  "unspecified". Counts follow the English plural: `1 day`, `0 days`,
  `2 days`.
- The opening catalog is `local/catalog.tsv`, in format 2, with English
  column names (`epd`, `eco`, `name`) and description keys (`lines`,
  `named`, `known`), which `collection.json` repeats. The former
  `catalogue.tsv` is ignored: run `--install-catalog` once.
- The names in the archive are in English. The archive, its working
  folder and the prompt are `analysis-<label>-<YYYYMMDD-HHMMSS>.zip`,
  `analysis-<label>-<YYYYMMDD-HHMMSS>/` and
  `analysis-<label>-<YYYYMMDD-HHMMSS>.prompt.txt`,
  and the archive holds `game.pgn`, `game-original.pgn`, `summary.md`,
  `context.md`, `collection.json`, `explorer/NNN-<uci>.json` and
  `stockfish/evaluations.json`.
- The JSON keys are in English. In `stockfish/evaluations.json`, each
  ply has `ply`, `move_number`, `side_to_move`, `played`, `best`,
  `cp_loss`, `category` and `fen`, and each move `san`, `uci`, `score`,
  `value_for_side`, `depth`, `pv_uci`, `pv_san`, `wdl` (`win`, `draw`,
  `loss`) and, for a null move, `not_evaluated`. `collection.json` gives
  each option under its English name (`output_dir`, `depth`,
  `usernames`...), then `token_present`, `catalog_used`, `side` (with
  `side`, `origin` and `modified_tags`), `context_collected`,
  `pgn_encoding`, `pgn_remarks` and `prompt_written`. A failed explorer
  query records `_error`, and a token found in a message becomes
  `<TOKEN-REDACTED>`.
- `verify-analysis.py` reads the new names and keys, and therefore no
  longer reads an archive made by an earlier version.
- The four startup questions about the game are in English, with their
  labels and defaults: "a. Scope" (the whole game), "b. What the player
  wants to understand" (left open), "c. Particular context" (nothing)
  and "d. Other comments to include in the final PGN" (nothing).
  `context.md` is in English: "Player's side", "Time control",
  "TimeControl tag ..., that is ...", and "(default)" for an answer
  confirmed with Enter.
- `summary.md` is in English: titles, tables, notes and sentences. Its
  sections are "Analysis instructions", "1. Headers and moves of the
  game", "2. Explorer of the ... database, exit from theory", "3.
  Stockfish evaluations", "3a. Principal variations of the engine"
  (formerly "3 bis"), "3b. Mistakes and blunders by side" (formerly "3
  ter"), "4. Positions with an unusable sample" and "5. Raw data of the
  archive". The engine table has the columns Move, Side, Played, Eval,
  W/D/L (formerly G/N/P), CP loss, Category, 1st, 2nd and 3rd, and the
  variations are ranked with English ordinals, "21st" included.
- The values written in the archive are in English: the sides `White`
  and `Black`, the move categories `inaccuracy`, `mistake` and
  `blunder`, the origin of the side (`deduced from the headers`,
  `declared`, `not declared`), a centipawn loss due to a mate `mate`,
  the databases `masters` and `Lichess (all players)`, the remarks on
  the encoding of the PGN, and the errors and stop reasons of the
  explorer, which the log repeats. `verify-analysis.py` reads them, and
  the agreed scope from the line `- a. Scope: ...`.
- The prompt templates are in English, and ask for the analysis in
  English, addressing the player as "you". Their language is in English
  as well, with no alias for the former names: the directives are
  `if`, `if not`, `else`, `end` and `note` (formerly `si`, `si non`,
  `sinon`, `fin` and `note`), and the conditions and values are renamed
  as below. A personal template must be adapted: an unknown name stops
  the script before the collection, giving the line.

| Former name            | New name               |
| ---------------------- | ---------------------- |
| `EXPLORATEUR`          | `EXPLORER`             |
| `BASE_LICHESS`         | `LICHESS_DATABASE`     |
| `BASE_MAITRES`         | `MASTERS_DATABASE`     |
| `REPONSES`             | `ANSWERS`              |
| `CAMP_CONNU`           | `SIDE_KNOWN`           |
| `PSEUDO_CONNU`         | `USERNAME_KNOWN`       |
| `NIVEAU_DECLARE`       | `RATING_DECLARED`      |
| `RESULTAT_CONTREDIT`   | `RESULT_CONTRADICTED`  |
| `CONSIGNES_DONNEES`    | `INSTRUCTIONS_GIVEN`   |
| `OUVERTURE_CONNUE`     | `OPENING_KNOWN`        |
| `COUVERTURE_PARTIELLE` | `PARTIAL_COVERAGE`     |
| `COUP_NUL`             | `NULL_MOVE`            |
| `PEU_DE_COUPS_FAIBLES` | `FEW_WEAK_MOVES`       |
| `AUCUN_COUP_FAIBLE`    | `NO_WEAK_MOVE`         |
| `{{DEPOT}}`            | `{{REPOSITORY}}`       |
| `{{PSEUDOS}}`          | `{{USERNAMES}}`        |
| `{{CAMP}}`             | `{{SIDE}}`             |
| `{{NIVEAU}}`           | `{{RATING}}`           |
| `{{CADENCE}}`          | `{{TIME_CONTROL}}`     |
| `{{ANNOTATEUR}}`       | `{{ANNOTATOR}}`        |
| `{{BASE}}`             | `{{DATABASE}}`         |
| `{{SEUIL_IMPRECISION}}` | `{{INACCURACY_THRESHOLD}}` |
| `{{SEUIL_ERREUR}}`     | `{{MISTAKE_THRESHOLD}}` |
| `{{SEUIL_GAFFE}}`      | `{{BLUNDER_THRESHOLD}}` |
| `{{PROFONDEUR}}`       | `{{DEPTH}}`            |
| `{{PARTIE_PGN}}`       | `{{GAME_PGN}}`         |
| `{{TABLEAU_MOTEUR}}`   | `{{ENGINE_TABLE}}`     |
| `{{ALERTE_RESULTAT}}`  | `{{RESULT_ALERT}}`     |
| `{{CONSIGNES_JOUEUR}}` | `{{PLAYER_INSTRUCTIONS}}` |
| `{{OUVERTURE}}`        | `{{OPENING}}`          |
| `{{DEMI_COUPS}}`       | `{{PLIES}}`            |
| `{{DEMI_COUPS_EVALUES}}` | `{{PLIES_EVALUATED}}` |
| `{{COUPS_FAIBLES_JOUEUR}}` | `{{PLAYER_WEAK_MOVES}}` |

- `STOCKFISH`, `{{VERSION}}`, `{{ARCHIVE}}` and `{{MULTIPV}}` keep their
  names. The values that the script computes for the prompt are in
  English: the rating ("about 1300 Elo, declared by the player", "1500
  Elo, from the BlackElo tag of the game", "unspecified: judge from the
  game, and stay accessible"), the default Annotator ("your model
  name, followed by its publisher in parentheses"), an unknown side or
  number of weak moves ("unknown"), the table of the short prompt
  ("blunder (350): better ...") and the sentence on the opening.
- `--settings` takes a name, never a path: a file name ending in
  `.ini`, kept at the root of the application folder like
  `settings.ini`, such as `--settings player2.ini` for a second player.
  A path, even inside the folder, is refused, `/dev/null` included:
  the settings never leave the folder, and deleting it leaves nothing
  behind. `--no-settings` runs without settings. In a terminal, a name
  whose file does not exist yet is created only after confirmation, so
  that a typo does not start a new file; answering `n` stops the
  script before anything is written or collected. `--purge-settings`
  follows the same rule. A settings file kept elsewhere must be moved
  into the folder, and a shared installation, such as one in `/opt`,
  no longer keeps the settings of each user: each one uses their own
  clone.
- The report of `verify-analysis.py` is in English: the markers
  `FAIL` and `WARNING`, `OK` and `INFO` being unchanged, the titles of
  its eight sections, its checks and their details, and the totals
  under `=== Totals ===`, as `failures` and `warnings`. Its help and
  its errors follow, with `--summary FILE` and `--name NAME`. A script
  that read the French report must follow: `ECHEC` is now `FAIL`.
- The README is in English, and describes the commands, options and
  files of this version. Its earlier French text, brought up to date,
  is now `README.fr.md`.
- `TECHNICAL.md` is in English, and up to date with this version: the
  command line and its rules, the settings and their profiles, the
  language of the templates, the files produced and the rules of the
  checker.
- The files of the repository have English names: `verify-analysis.py`,
  formerly `verifier-analyse.py`; `prompt-template.txt` and
  `prompt-only-template.txt`, formerly `prompt-modele.txt` and
  `prompt-seul-modele.txt`; `example-games/`, formerly
  `parties-exemples/`; `EXAMPLES.md` and `TECHNICAL.md`, formerly
  `EXEMPLES.md` and `TECHNIQUE.md`. The files of `example-games/`
  have English names and contents too, such as `my-game.pgn` and
  `llm-annotated.pgn`: only `french-notation.pgn` keeps its French
  notation, which the script refuses, and which is its point. A
  template kept next to the script under its old name is no longer
  read: the script reads `prompt-template.txt` and
  `prompt-only-template.txt`. The report of `test-app.sh` is named
  `test-report-<system>-<date>.txt`.
- The temporary files that the script writes before renaming them are
  named `.<name>.partial` and `.<folder>.partial.zip`, formerly
  `.partiel`.
- `EXAMPLES.md` is in English, and gives the commands, options and
  real outputs of this version, taken on 25 and 27 November 2026. The
  options and messages of the settings have their examples:
  confirmation of a new name given to `--settings`, refusal of a
  path, warning for a file that is not a settings file,
  `--no-settings`, refusal of a settings file of the former format by
  `--purge-settings`. Its earlier French text, brought up to date,
  is now `EXAMPLES.fr.md`.
- `TESTS.md` is in English, and describes the tests of this version,
  with the English names of the options and variables (`--network`,
  `TOKEN`, `KEEP`). The tests added during the translation, T86 to
  T92, have their rows, and the rows of T02, T05, T10, T11, T25,
  T27, T57, T60, T62, T63 and T69 say all that these tests now
  check. Its earlier French text, brought up to date, is now
  `TESTS.fr.md`.
- Each of the four documents, README, `EXAMPLES.md`, `TECHNICAL.md`
  and `TESTS.md`, has its French version, under the same name ending
  in `.fr.md`, as the README says. The French versions link to one
  another. In `TECHNICAL.md`, the exit code 2 also covers the options
  that exclude each other, as `EXAMPLES.md` already said.
- The history of this file, from version 4.0.2 back, is in English,
  like the rest of it, and so is its introduction. The names of the
  options, files, keys and messages of each version stay as they were
  then, in French. The heading of the additions of this version no
  longer carries a date, which Keep a Changelog only puts on the
  heading of a release.
- The final summary of the full prompt asks for the costliest errors
  of the player, as the review of the short prompt does: when the
  table marks fewer than three weak moves on the side of the player,
  it gives their number and asks to keep to those, without replacing
  them with the errors of the opponent; without any weak move, it
  asks to attribute no error to the player. Asked for "the three
  costliest errors" without being told whose, an LLM tried on
  25 November 2026 gave those of the opponent.
- Both prompts say where a variation starts: from the position
  before the move it replaces, with the same side to move, and never
  with the moves actually played. The full prompt adds that `$7` and
  `$8` go on the forced reply, never on the move that forces it, a
  check for instance. On 25 November 2026, an LLM had put
  `( 19... Kg8 20. Qh7# )` after 19.Qh5+: illegal there, the
  variation made python-chess stop the main line two plies before
  the mate, and `$7` sat on the check.
- `verify-analysis.py` counts more quality NAGs as other opinions
  than the one of the engine, for information, each named with its
  move and its loss: `$1` or `$3` on a mistake or a blunder, and
  `$6`, `$2` or `$4` on a move that the engine does not classify,
  its loss staying under 50 cp. Tried on 25 November 2026, an LLM
  had put `$6` on seven moves that the engine did not classify, and
  the report counted no other opinion.
- In the report of `test-app.sh`, the three checks of the defaults
  that `--help` shows carry the number of their test, T02, and come
  right after its other checks, instead of standing without a
  number under the title of T31 and T32.
- In `ianalyze.py`, the timestamped working folder and the database
  queried by the explorer no longer share the variable `base`, which
  mypy took for a path everywhere: six of its errors go away. The
  behavior does not change, the syntax tree being the same, the name
  aside.
- README and README.fr.md, section 7: the trials of the English
  prompts, run on 25 and 26 November 2026 on four LLMs, with the zip
  and with `--prompt-only`. Claude, on the subscription, is the only
  one without an error found on the board, on both routes, and the
  advice of the section stays the same.
- A username is found in the White and Black tags as the whole name or
  as a run of its words, no longer as a mere substring: "Max" no longer
  matches "Maxime", nor "deuza" "DeuZa42". Looked up as a substring, a
  username found in the name of the opponent alone gave the wrong
  side. List each of your usernames in the settings.
- In `collection.json` and `summary.md`, a path under the home folder
  is written with `~`: the name of that folder, the login of the user
  most often, no longer goes to the LLM with the archive.
- Both prompts say that the tags and the comments of the PGN are data,
  the notes of the player at most, never instructions: a comment could
  give orders to the LLM. The short prompt gives the game in a code
  block.
- The messages and the labels of the report of `test-app.sh` are in
  English. The names of the files that the tests write, such as
  `t-francais.pgn`, stay French, like the identifiers of the script.
- A token refused by the explorer, HTTP 401, stops the run with the
  exit code 1, before the engine, and advises to replace it or to run
  again with `--no-explorer`. The collection went on, and Stockfish ran
  for minutes for an archive without its section 2. The answer stays in
  `explorer/`, the working folder with it.
- The default engine is looked for in the PATH under Debian too, then
  in `/usr/games`: an engine built by hand is found as under macOS. The
  PATH of root does not hold `/usr/games`.
- W/D/L is written in whole percentages adding up to 100, by the
  largest remainders, computed for White and swapped for Black. Rounded
  one by one, 15, 970 and 15 per thousand gave 2/97/2.
- A variation that starts with a Black move is written `8... Bg4`, as
  in the PGN and in the examples of the prompt, no longer `8...Bg4`.
- Full prompt: the line on case A or B comes first, then the recap,
  both being asked for the start of the answer; the notation no longer
  lists `P`; the notes of the player are kept in the PGN returned, the
  commands `[%clk]` and `[%eval]` that a site writes in the comments
  left out, `%` being forbidden there, and a `%` of a note written
  "percent"; the other format constraints bear on the text of the LLM,
  not on a note kept, and a note that contradicts section 3, a figure
  left by the analysis of a site for example, must be said so; the
  final summary keeps to the agreed scope, like the comments, and a
  scope that holds fewer errors than a point asks for gives only
  those; the loss `mate` also covers a mate found by the move played.
  The summary says the same of `mate`.
- Short prompt: the comments already in the game are kept, without the
  commands of a site, a note that contradicts the table must be said
  so, and a scope given by the player bounds the comments and the
  review, with only its errors if it holds fewer than asked for.
- The refusal of `--settings` says that the name must not start with a
  dot, and so does the help. The help of `--usernames` gives the rule
  of the whole name or run of words.
- `test-app.sh`: the runs on a pseudo-terminal, T45 and T79 included, go
  through a driver with a deadline of 300 seconds, which reads the whole
  output and returns the exit code of the script; a run that the driver
  had to kill is a failure wherever it happens, and a script that closes
  its terminal no longer blocks the driver; T97 and the reading of the
  FIFO of T89 have a deadline of their own; T58 checks the end of the
  run before an absence; the collision of names of T74 runs on a frozen
  clock; T23 holds across midnight; the engine processes of M2 are found
  by `ps`, a name beyond the 15 characters kept by Linux included, and
  the link through which T55 starts the engine; the guards of the token
  compare the token as the script reads it, through a pipe, a byte order
  mark or a carriage return no longer hiding it, and a blank line or an
  empty file no longer matching everything; the cases of T81 are named
  by their kind, their content being the dummy token `lip_factice`,
  which a run with `--network` on a token file holding that same string
  found in its report, then not written; the totals are displayed before
  that last guard; the refusals run with a missing `--token-file`, T85
  with a dummy interpreter and T81 with a venv that cannot be created;
  the report is written by a literal replacement of the paths; a
  relative `VENV`, `STOCKFISH` or `TOKEN` is taken from the repository;
  a path with a blank, and a missing `unzip`, `python3` or `ps`, stop
  the suite at the start; no `__pycache__` is written.
- `ianalyze.py` passes mypy without an error, without a change of
  behavior: a separate variable for the bytes of the label, two types
  narrowed, the information of the engine typed as such.
- Documentation: the dates written in one form, "25 November 2026"; the
  names of the archive, of the folder and of the prompt written
  `analysis-<label>-<YYYYMMDD-HHMMSS>` in the documents and in the help;
  the README and `EXAMPLES.md` give the rule of the usernames;
  `TECHNICAL.md` says where the default engine is looked for;
  `EXAMPLES.md` calls `../verify-analysis.py` from `example-games`, says
  that the count of the variations of the engine varies from one
  collection to another, and gives the new messages with their real
  output; `TECHNICAL.md` names the conditions that no template of the
  repository uses; the checker documents its limits. The versions
  without a tag lose their brackets.

### Removed

- The French names of the options, without aliases, and the former
  locations of the virtual environment, the catalog and the settings,
  `~/.local/share/IAnalyze` and `~/.config/IAnalyze`, no longer read
  (see Changed).
- The reading of the archives of version 4 by `verify-analysis.py`,
  whose names and keys are now in English.
- The French language of the prompt templates: a template with the
  directives `si`, `sinon` and `fin`, or the French values, is refused
  at its first marker.

### Fixed

- `--install-venv` rebuilds a virtual environment left without pip
  by an interrupted creation, instead of failing on "No module named
  pip". Only a directory that carries `pyvenv.cfg` can be rebuilt, so
  that a wrong `--venv` never loses its content.
- `--install-venv` refuses a `--venv` that is not a virtual
  environment, an existing directory that is not empty and has no
  `pyvenv.cfg`, such as `/usr` or a home directory. It used to run pip
  on the Python found there, often the one of the system, or to
  scatter a new environment among the files already in place.
- `verify-analysis.py` reads the scope agreed at the first startup
  question, in the instructions of the summary. It looked for a line
  `- Périmètre : ...`, whereas the summary writes `- a. Périmètre :
  ...`: without `--scope`, it expected a comment on the mistakes and
  blunders played beyond the agreed scope. The flaw dates from version
  4.0.0, and its test checked a line that the script never writes.
- The settings are written only over a settings file. The writing goes
  through a neighboring file renamed over the path: in a terminal, as
  root on Linux, `--settings /dev/null` replaced the device with a
  regular file, and a typo in the path rewrote the INI file of another
  program, its comments lost. The path is now written only if it does
  not exist yet, or if it is a regular file that is empty or carries
  the `[player]` section, or the `[joueur]` section of a file of the
  former format. Anything else is left untouched: the answers
  serve the current run, and a warning says why they are not kept,
  suggesting `--no-settings` for a device, a FIFO or a directory. The
  flaw dates from version 4.0.0, where the option was `--reglages`.
- `example-games/llm-annotated.pgn` and `llm-conversation.txt` quote
  the evaluations of the engine rounded to one decimal, which the
  checker accepts. Their values with two decimals came from a single
  run of Stockfish, whose evaluations vary from one run to another:
  replayed, the check shown in `EXAMPLES.md` ended on a `FAIL`, an
  evaluation not found. The flaw dates from version 4.0.0.
- The report of `verify-analysis.py` agrees its words with its
  counts: "the only variation is written inside a comment" instead
  of "the 1 variations are written inside the comments", "1
  variation starts from a line of the engine" and "1 is the LLM's
  own" instead of "1 variation(s) start" and "1 are", "1 of which
  starts", "the first move" for a scope of one move, and "ply" for a
  single ply. The forms in "(s)", such as "3 move(s) commented",
  stay as they are.
- The header of the opening catalog, and `collection.json` after it,
  give the source of the five files as `.../{part}.tsv`, instead of
  `{partie}`, a French word left in the archive. A catalog installed
  before keeps its former header until `--install-catalog` is run
  again.
- Both prompts are wrapped at 71 columns, as rendered, whatever the
  conditions of the template. A sentence cut by a condition left short
  lines, such as "variation, scope and goal), then" in the recap of the
  full prompt, or "questions in a single message, numbered," before
  the startup questions: each branch now carries whole lines. The
  fixed text follows the same rule: two lines of 72 columns and one of
  76 are shortened, others take the first word of the next line, and a
  continued line no longer opens on a figure, such as "3 writes", which
  could read as an item of a list. Only the line breaks change: the
  words are the same in every combination of the conditions.
- The docstring of `etiquette_sure()`, in `ianalyze.py`, gives `game`
  as the label of an empty name, the one that the code returns since
  the names of the archive are in English. It still gave `partie`.
- `test-app.sh` runs under posh without an argument: with `set -u`,
  posh took an empty `"$@"` for an unset parameter and stopped at
  once. The header of the script names posh among the shells checked.
- Two checks of `test-app.sh` could not fail. T77 read its last log
  twice, instead of those of all its inputs. T91 compared its report
  with expected lines that an error of their generator left empty; the
  generator must now succeed and write them.
- A line of the PGN that starts with a bracket is accepted only as a
  well-formed tag, alone on its line, before the moves of its game.
  python-chess skipped any other such line without a word, with the
  moves that it carried, and played the moves held by brackets among
  the moves: the game analyzed was not the one given.
- A null move played in check, after a mate for example, is refused at
  the reading: Stockfish died on the illegal position that followed,
  without the message saying why.
- A PGN in UTF-32 without a byte order mark is recognized: it passed
  for cp1252 once its null bytes removed, losing every character
  beyond latin-1.
- An illegal move of the PGN is named once: python-chess wrote it on
  its own, before the refusal of the script.
- A settings file in UTF-16, which the reading accepted, is rewritten
  and purged like the others: its section was looked for in the raw
  bytes.
- `--timeout` is checked with `--install-catalog` too: a negative value
  ended in an unexpected error, a null one in an unreachable catalog.
- With `--stockfish-moves`, both prompts bound the count of the weak
  moves of the player, or their absence, to the plies evaluated, and
  leave an error beyond them to the estimate of the LLM: a player
  without a weak move in the window was said to have made no error in
  the whole game.
- `verify-analysis.py`: a `#7` without a sign that is not found in the
  data of the engine is only a warning, a rank such as "mistake #7"
  having counted as a mate not found. A FEN quoted with its en passant
  square after a double step, as the standard writes it, is recognized
  as a position of the game. The report shows the control characters
  of the PGN as `?`, and an output that cannot represent a character no
  longer stops it on UnicodeEncodeError.
- The French documents give the commands, the outputs, the file names
  and the placeholders in English, as the English ones do: some had
  been translated. TECHNICAL, EXAMPLES and this file no longer say that
  version 4 wrote a `settings.ini` with a `[joueur]` section: it wrote
  `~/.config/IAnalyze/reglages.ini`.
- TESTS.md and TESTS.fr.md describe T03, T14 and T81 as they are, and
  T12, T26 and T55 now check what their rows said. A check of T83 used
  the alternation of GNU grep, which another grep may take literally.
- `--install-venv` on a regular file is refused with its own message:
  `python -m venv` failed on it, and the message asked whether
  `python3-venv` was installed.
- A PGN in UTF-16 or UTF-32 cut or damaged is refused with its cause:
  the check of the notation blamed a U+FFFD for not being a move, or a
  brace for never being closed, the cause staying in the remark on the
  encoding.
- A negative loss beyond 10000, a mate found by the move played that
  the search of the best moves did not see, reads `mate` instead of
  some -99000 centipawns.
- `https://lichess.org/timeline`, and the sections `bookmark`,
  `password` and `markdown`, of eight letters like an identifier, were
  requested from Lichess as games.
- An answer of the explorer whose `moves` key is missing or is not a
  list is an unusable answer: it passed for an exit from theory at
  0.0 %.
- `verify-analysis.py`: a blank line inside a comment is no longer
  said to stop python-chess, which reads on up to the closing brace;
  a third decimal at zero, `+1.910`, is accepted; removing the blank
  lines of the body no longer merges a second game into the first.

## [4.0.2] - 2026-11-21

### Added

- `parties-exemples/partie-lichess-org.pgn`: a real anonymized game,
  as Lichess exports it without the analysis of the site. It is the one
  of the trials of 21 November 2026, which the README describes in
  section 7.

### Changed

- README: Lichess is presented as the reference source of the script,
  with its two examples, the plain export and the commented export.

## [4.0.1] - 2026-11-21

### Added

- `parties-exemples/`: four real anonymized games, as Chess.com,
  chess-mail.com, ajedrezmail.org and Lucas Chess export them. With the
  one from Lichess, they show the exports tried, which the README
  lists.

### Fixed

- A PGN whose result is written twice at the end of the file, like
  those of chess-mail.com, was refused for "2 parties": python-chess
  reads in the second result a game without a tag or a move. It is now
  ignored, and the log says so. A file that really gathers several
  games stays refused.

## [4.0.0] - 2026-11-21

First version published since 3.5.8. It gathers the work of versions
3.5.9 to 3.8.0, which stayed on the development branch and were never
published.

### Added

- Analysis prompt written next to the archive, under the name
  `<archive>.prompt.txt`, to be pasted into the conversation with the
  archive as an attachment. It is drawn from a template,
  `prompt-modele.txt`, kept next to the script and editable without
  touching the code: the script fills in the values (username, side,
  rating, time control, name of the archive) and keeps only the
  passages that apply (database queried, explorer or not, answers
  collected or not). The prompt thus always describes the summary that
  this version has just written.
- Markers of the template: `{{NOM}}` for a value, and the directives
  `#! si`, `#! si non`, `#! sinon`, `#! fin` and `#! note`. The
  template is checked before the collection: an unknown or badly
  written marker, a condition never closed or a template without a
  single line of text stop the script, with the number of the line.
  `TECHNIQUE.md`, section 12, gives the list of the values and of the
  conditions.
- Options `--prompt FICHIER`, for another template, and
  `--sans-prompt`.
- Option `--prompt-seul`: a short prompt, to be pasted alone into the
  conversation, without an attachment. It holds a few instructions, the
  game and the evaluations of Stockfish, one line per ply, the best
  move and its continuation behind each weak move. It is the road to
  take with a free account, or with an LLM that does not open zip
  files or does not run code, after the model of the analysis prompt
  of Lucas Chess, with the figures of the engine in addition. It is
  drawn from a separate template, `prompt-seul-modele.txt`. No archive
  is then written: the prompt is the only file produced, except with
  `--garder-dossier`, which leaves the working folder to
  `verifier-analyse.py`. Its report asks for the three costliest errors
  of the player: when the table of the engine marks fewer than three
  weak moves on their side, the prompt gives their number and asks to
  keep to those, since an LLM asked for three makes one up. Value
  `COUPS_FAIBLES_JOUEUR` and conditions `PEU_DE_COUPS_FAIBLES` and
  `AUCUN_COUP_FAIBLE` for the personal templates. Without any weak
  move, the prompt asks to attribute no error to the player. When their
  side is not known, it asks to comment on both sides in the same way
  and to give the report for each one.
- `verifier-analyse.py`, which checks the annotated PGN returned by an
  LLM by comparing it with the archive that it received: reading, main
  line, format, mistakes and blunders commented on, evaluations quoted,
  variations, positions quoted in the conversation. It names the traps
  found in real PGNs of LLMs, among them the blank line in the body of
  the game and the variation written inside a comment, which it
  replays itself. It does not judge the quality of the commentary. Its
  option `--prompt-seul` checks a PGN returned after the short prompt,
  which asks for no overview, no lines of 79 characters, no NAG, no em
  dash and no FEN. Its option `--perimetre N` limits the check of the
  mistakes and blunders commented on to the scope agreed with the LLM.
  Without it, the scope is read in the answer of the player to the
  startup question. A quoted mate, `#+2` or `#2`, is checked like the
  other evaluations. In a folder that contains several collections,
  only a complete collection is kept, and named: if there are several,
  the script stops rather than choose one.
- Settings file, `~/.config/IAnalyze/reglages.ini`, in INI format: it
  keeps your usernames, your usual time control and your rating in Elo
  points, plus an optional setting `annotateur`. The missing keys are
  asked only once, at the first run in a terminal. Outside a terminal,
  nothing is asked or written.
- Options `--reglages FICHIER`, to designate another file, and
  `--purge-reglages`, which deletes it then exits. Only a file that
  carries the `[joueur]` section, or an empty file, is deleted: a typo
  after `--reglages` does not destroy another file.
- Time control entered through checked questions, and no longer as
  free text: real time, correspondence or unknown, then the minutes per
  player and the increment in seconds. Correspondence knows three
  systems: a fixed delay in days per move (Lichess, chess.com), a
  number of moves per period, such as "10 coups en 50 jours" (standard
  time control of the ICCF), or a clock with an optional increment,
  maximum and bank (chess-mail.com, Triple Block of the ICCF). The last
  two follow the ICCF Rules in force since 1 January 2026. The script
  writes itself the sentence passed on to the analyst, with the
  category of Lichess, computed as Lichess does on the initial time
  plus forty times the increment.
- A `TimeControl` tag of the form `600+5` or `300` is quoted, then
  translated: "soit rapide, 10 minutes + 5 secondes par coup".
- Without a known username, the script asks for your player name when
  your tag is empty, as it does for the opponent. Outside a terminal,
  the side of the player is deduced from their usernames, without a
  question.
- Summary: under the table of Stockfish, a line "Résultat et
  évaluation finale se contredisent" when the side declared the winner
  is worse by at least 300 cp after the last move. The game was then
  not decided on the board, and the prompt asks the analyst to say so.
- `collecte.json`: key `prompt_ecrit`, and the usernames really used.
- `parties-exemples/`, the files quoted in `EXEMPLES.md`: the games of
  the examples, the PGNs that the script refuses, three annotated PGNs
  for the checker, and a real anonymized game, exported from Lichess
  with its comments, for a first try.
- `test.pgn`, a test game that gathers the tricky cases of a PGN:
  accented tags, comments of all kinds, NAGs, nested variations, missed
  mate, en passant capture, promotion, both castlings and a null move.
- `test-app.sh`, which runs the test suite in one go and writes a
  report, under Linux as under macOS: `sh test-app.sh` offline,
  `sh test-app.sh --reseau PARTIE` with a token and a Lichess game of
  your choice. The repository quotes no real game: without a game, the
  download test is skipped.
- `.gitignore`: reports of `test-app.sh`, archives, working folders and
  prompts produced in the repository.

### Changed

- The script is called `ianalyze.py`, after the name of the project,
  instead of `collecte-partie.py`. The command becomes
  `./ianalyze.py ma-partie.pgn`.
- Stockfish is mandatory: its evaluation is part of every collection.
  A summary without the figures of the engine left the analyst to
  estimate alone, which is not the aim of the project.
- Default locations, the same under Debian and under macOS, all in the
  home directory: virtual environment in
  `~/.local/share/IAnalyze/venv`, catalog in `~/.local/share/IAnalyze`,
  settings in `~/.config/IAnalyze`. Under Debian, only the packages
  still require root rights. The former locations were
  `/opt/venv/lichess`, `/usr/local/share/collecte-partie` and
  `~/.local/share/collecte-partie`.
- HTTP agent header: `IAnalyze/4.0.0`, followed by the address of the
  repository.
- `--pseudos` no longer has a default value in the code: without the
  option, the usernames come from the settings file. Given, it always
  wins.
- A PGN that contains several games is refused, with their number. Up
  to now the first one was analyzed after a mere warning.
- A PGN that does not start from the initial position, and therefore
  carries a FEN tag, is refused. IAnalyze analyzes a whole game, from
  the first move to the last.
- A PGN whose encoding is neither UTF-8, nor UTF-16, nor cp1252 is
  refused, with the advice to convert it. It used to be read in
  latin-1, and its accented letters removed as control characters.
- `--profondeur` is bounded to 60. An excessive value, given by a typo,
  kept the engine busy without ever giving control back.
- Startup questions: an answer is 255 characters at most, and a player
  name can no longer contain a double quote, a backslash, a square
  bracket or a brace. Such a name gave a non-compliant `partie.pgn`.
  The question is asked again.
- Name of the archive: the spaces of the name of the PGN become
  hyphens in it, `partie contre machin.pgn` gives
  `analyse-partie-contre-machin-...`.
- The template of the prompt, `prompt-modele.txt`, replaces
  `INSTRUCTIONS.txt`, which was a text to be pasted as it was. The
  prompt asks the analyst to use all the files of the archive, and
  describes them one by one. It no longer assumes that the analyst runs
  code: an analyst that does not writes the PGN itself, says so, and
  invents neither a result of execution nor a figured evaluation.
- Prompt: instructions added after trials on four LLMs, each one
  answering a flaw found in a PGN really returned. No blank line in the
  body of the game, variations written outside the braces, never
  announce a file that was not created, never return a PGN without
  comments on the ground that a file is missing. The wrapping of the
  comments goes from 76 to 75 columns, so that the exported lines fit
  in 79 characters.
- Documentation in Markdown, in four files. `README.md` replaces
  `README.nfo` and keeps to the installation and everyday use.
  `EXEMPLES.md` is the quick reference, built like a manual page: every
  command, every option, and what the terminal shows. `TECHNIQUE.md`
  explains how the script works, its use from another program, the
  detail of the files produced, the encodings and the prompt template.
  `TESTS.md` replaces `TESTS.nfo`: how to run the tests, then a table
  that gives, test by test, what is checked. The README recommends
  Claude, with the zip and the prompt as with `--prompt-seul`, free
  account included, and reports on two series of trials on four LLMs:
  on 20 November 2026 with the zip, on the 21st with the short prompt.
  It draws a reading rule from them: the figures hold, the stories are
  to be checked on the board.

### Removed

- Options `--avec-stockfish` and `--sans-stockfish`: the engine is
  always called. The key `avec_stockfish` of `collecte.json` goes away
  too.
- Option `--consignes`, which inserted a file of your own at the head
  of the summary. It dated from before the prompt, when the summary was
  the only file given to the LLM. The prompt now carries the analysis
  instructions, and your answers to the startup questions the context
  of the game.
- The personal username and time control of the author, until then
  default values of the script. The examples of the help and of the
  documentation use neutral usernames.
- `INSTRUCTIONS.txt`, `README.nfo` and `TESTS.nfo`, replaced by the
  files quoted above.

### Fixed

- Mates: the number of moves was the one before the move. In a table
  that gives the evaluation after each move, the side that mates showed
  one move too many: `#+2` after a check that left only one move, `#+1`
  on the mating move itself. The count is now read after the move,
  `#+0` or `#-0` designating the move that gives mate. The centipawns,
  the losses and the categories of the moves do not change.
- A game written in French notation, in figurines or in lowercase was
  analyzed wrongly without any message: python-chess drops the letter
  that it does not know, and "Cf3" became "f3", a pawn move. The body
  of the game is now checked before the reading, and the first word
  that is not an element of PGN stops the script.
- A comment whose brace is never closed truncated the game silently.
  It is refused, like a parenthesis of variation never closed or closed
  once too often.
- Explorer: a null move, `--` in the PGN, came out in the table at
  0.0 % and was designated as the first exit from theory, or caused an
  HTTP 400 from Lichess. The querying now stops at the null move,
  without a request for this ply, and section 4 of the summary lists
  it.
- Explorer: an HTTP error whose body arrives cut off, or an answer
  nested to excess, aborted the whole collection. Only the querying now
  stops, and Stockfish does its work. A negative or excessive count of
  games is taken as missing.
- Several inputs ended in "Erreur inattendue" instead of the expected
  message: free text after the game, standard input closed by the
  caller, a file name too long, a URL with misplaced brackets, an
  engine that stops outside a search.
- Source: an address with an uppercase scheme, `HTTPS://`, was taken
  for a file. A Lichess section of eight letters, `Analysis` or
  `features`, and a local directory of eight letters were taken for
  game identifiers, and a request went out.
- Paths: `--sortie='~/analyses'` created a directory named `~`, and
  `--stockfish` did not expand the tilde. An engine designated by its
  bare name was checked in the current directory, then started from
  the PATH.
- A PGN with a long name, written in multibyte characters, made the
  writing of the archive fail after the whole analysis.
- Summary: between two mates of the same direction, the column "Écart
  cp" showed 1, read as a centipawn. It shows 0, and the legend says
  what a negative loss is worth. The title of a game without a Site tag
  is "partie locale" and not "?".
- A token file written `LICHESS_TOKEN=...` or between quotes passed
  the reading, and Lichess answered 401: it is refused with a clear
  message.
- On a game that contains a null move, the log repeated a notice of
  python-chess at each following position. Without consequence on the
  evaluations, it is set aside.

### Security

- The Lichess token no longer follows an HTTP redirect. If the explorer
  answered 301, 302, 303, 307 or 308, the Authorization header went
  with the request to the new address, whatever its host. The redirect
  is now refused and the querying stops.
- The token is removed from the answer of the explorer before it is
  kept in the archive, in case a server sent back the header that it
  received.

## 3.5.8 - 2026-11-18

### Changed

- HTTP agent header: `collecte-partie/3.5.8`.
- The angle quotation marks of the script are replaced by straight
  quotes: two comments, and the help of `--consignes`, which now shows
  `sous le titre "Consignes d'analyse"`.

## 3.5.7 - 2026-11-18

### Added

- TESTS.nfo: test T55, the engine options out of bounds.

### Changed

- HTTP agent header: `collecte-partie/3.5.7`.
- `collecte-partie.py` is recorded as executable (mode 755) in the
  repository.
- The engine is started a first time, briefly, during the preliminary
  checks, then a second time for the analysis.
- README.nfo, section 5: the check of the engine options.

### Removed

- Constant `RE_ID_PARTIE`, unused since `RE_ID_SOURCE` replaced it.

### Fixed

- A value of `--fils`, `--hachage` or `--multipv` out of the bounds of
  the engine, or an engine that does not know one of these options, was
  only refused at the configuration of the engine, after the whole
  explorer phase, by the message "Le moteur a échoué en cours
  d'analyse". These options are now checked with the engine during the
  preliminary checks, before any request and before the creation of the
  working folder.

## 3.5.6 - 2026-11-18

### Added

- TESTS.nfo: test T54, the URLs that are not games.
- Stop message specific to the refused URLs, which recalls the
  expected form.

### Changed

- HTTP agent header: `collecte-partie/3.5.6`.
- README.nfo, section 3: the forms of URL accepted.

### Fixed

- A URL that is not the one of a game was requested from Lichess all
  the same: `https://lichess.org/analysis/...` gave the identifier
  "analysis", the URL of a study the one of the study, and
  `https://example.com/abcdefgh` was accepted whatever the host. A
  useless request and an "Export PGN : HTTP 404" followed. A URL must
  now target `lichess.org` and carry the identifier at the head of the
  path, or after `/embed/game/`, `/embed/` or `/game/export/`. The
  sections `analysis`, `training`, `practice` and `streamer` no longer
  pass for identifiers.

## 3.5.5 - 2026-11-18

### Added

- TESTS.nfo: test T53, interruption during the archiving and a write
  that fails along the way, on a simulated archiving.

### Changed

- HTTP agent header: `collecte-partie/3.5.5`.
- README.nfo, section 7: what stays on the disk after a failure.

### Fixed

- An interruption (Ctrl-C) or a failure during the creation of the zip
  left a truncated archive under its final name, which nothing told
  apart from a valid archive. The zip is now written under a temporary
  name, `.<folder>.partiel.zip`, checked, then renamed; in case of a
  stop it is removed, and the working folder is kept.
- An interrupted write left a truncated file, `synthese.md` or
  `collecte.json` for instance, in the working folder kept. Each file
  of the archive is now written into a neighboring file
  `.<name>.partiel`, renamed once complete.

## 3.5.4 - 2026-11-18

### Added

- TESTS.nfo: test T52, the null move in the Stockfish table.
- Summary, section 3: a sentence explains the line of a null move,
  when the game contains one.
- `stockfish/evaluations.json`: key `non_evalue` on the move played
  when it is a null move.

### Changed

- HTTP agent header: `collecte-partie/3.5.4`.
- README.nfo, section 7: the line of a null move.

### Fixed

- Stockfish: a null move, `--` in the PGN, received an evaluation, a
  loss and sometimes a category ("+0.00", 55 cp, "imprécision") that
  the engine had never given, the UCI protocol not knowing how to
  restrict a search to this move. Its line is kept with the best moves
  of the position, but its columns Éval, G/N/P, Écart and Nature now
  carry `-`. The rest of the game is analyzed as before.

## 3.5.3 - 2026-11-18

### Added

- TESTS.nfo: test T51, the loss of a missed mate.
- Summary, section 3: a sentence explains the mention `mat` of the
  column Écart cp.

### Changed

- HTTP agent header: `collecte-partie/3.5.3`.
- README.nfo, section 7: the mention `mat` of the column Écart.

### Fixed

- Stockfish table: when the move played missed a mate, or conceded
  one, the column Écart cp showed a number close to 100000, 99729 for
  instance. This number comes from the bounded value by which the
  script replaces a mate to rank the moves, not from the engine. The
  cell now carries `mat`, as the ranking already wrote "écart lié à
  un mat". `stockfish/evaluations.json` keeps the raw value in
  `ecart_cp`.

## 3.5.2 - 2026-11-18

### Added

- TESTS.nfo: tests T49, unexpected answers of the explorer, on a
  simulated explorer, and T50, non-finite values.
- README.nfo, section 5: `--pause` and `--seuil-frequence` refuse
  `nan` and `inf`.

### Changed

- HTTP agent header: `collecte-partie/3.5.2`.

### Fixed

- Explorer: a JSON answer whose key `moves` is not a list, or one of
  whose counters is worth infinity (`1e999`), stopped the script on a
  `TypeError` or an `OverflowError`. These values are now ignored, like
  the other departures from the schema.
- `--pause nan` and `--pause inf` were accepted, then stopped the
  collection on an unexpected error at the first pause, working folder
  already created; `--seuil-frequence nan` was accepted and silently
  neutralized the frequency criterion. These values are refused at the
  reading of the options, code 2.

## 3.5.1 - 2026-11-18

### Added

- TESTS.nfo: test T48, a dot in the name of the PGN.

### Changed

- HTTP agent header: `collecte-partie/3.5.1`.

### Fixed

- A PGN whose name contains a dot, like the exports of Lichess
  (`lichess_pgn_2026.11.18_A_vs_B.pgn`), made the archiving fail with
  "Archive illisible, dossier conservé" and the code 1: the script
  looked for `analyse-lichess_pgn_2026.11.zip` whereas the archive,
  valid, was written under the full name of the folder. The path of the
  archive was not shown and the working folder stayed in place. The
  check of the archives of the same name suffered from the same flaw.

## 3.5.0 - 2026-11-18

### Added

- Console output: standard output and standard error are reconfigured
  with `errors="replace"`. A character that the terminal cannot show
  becomes `?` instead of causing a `UnicodeEncodeError`, for instance
  with `PYTHONIOENCODING=ascii`, or under `LC_ALL=C` with
  `PYTHONUTF8=0`.
- The control characters are removed from the lines of the log and
  from the stop messages before display.
- Reading of the PGN and of the instructions whatever their encoding:
  byte order mark (BOM) UTF-8, UTF-16 or UTF-32, UTF-16 without a mark,
  UTF-8, then fallback to cp1252 and to latin-1. An "Attention" line of
  the log names the encoding used. A UTF-8 file damaged by a few
  invalid bytes is still read in UTF-8, these bytes becoming U+FFFD.
- The control characters of the PGN, NUL included, are removed and
  counted in the log; the CRLF and CR line ends are brought back to LF.
- collecte.json: keys `pgn_encodage` and `pgn_remarques`. If the PGN
  had to be converted, section 5 of the summary reports it.
- Token file: same encoding detection as for the PGN, byte order mark
  and UTF-16 included. A token outside printable ASCII is refused
  before any request, by a message that does not reproduce it.
- Catalog and answers of the explorer: read in `utf-8-sig`, with an
  explicit error handling, without dependence on the locale.
- Writing: all the files of the archive go through a single function,
  in UTF-8, LF line ends, without dependence on the locale.
- Name of the working folder and paths of the zip: the control
  characters, `/ \\ : * ? " < > |` and the undecodable bytes of the
  name of the PGN become `_`, the label is bounded to 80 characters.
  Spaces and accented letters are kept.
- The path of the archive is written in bytes on standard output, as
  the file system knows it.
- Values drawn from the PGN (names of the players, Event, Site and any
  other tag): tabs and control characters are removed before the
  headers are written into `synthese.md` and before any display.
- Startup questions: an answer typed in another encoding than the one
  of the terminal is decoded again (cp1252, then latin-1) and cleaned
  of its control characters.
- Constant `VERSION`, from which the HTTP agent header is drawn.
- TESTS.nfo: section L, tests T34 to T47, whose fixtures are produced
  by the tests themselves.
- README.nfo: section 8, encodings and characters.

### Changed

- HTTP agent header: `collecte-partie/3.5.0`.
- `partie.pgn` is always written in UTF-8, LF line ends, without a
  byte order mark or a control character: it is no longer, byte for
  byte, the file given when that one departed from this.
- README.nfo: the sections Token and Sources become 9 and 10.

### Fixed

- A PGN in latin-1 or in cp1252 was read as UTF-8: each accented
  letter became U+FFFD in `synthese.md` and in `partie.pgn`, without
  any warning.
- A PGN in UTF-16 was refused with the misleading message "PGN sans
  aucun coup dans la ligne principale".

- A token file saved with a byte order mark made the first request
  fail with the diagnosis "réponse non JSON : 'latin-1' codec can't
  encode character '\ufeff'", and the archive was produced without the
  explorer.

- A PGN with an undecodable name, in latin-1 on a UTF-8 system for
  instance, stopped the collection on a `UnicodeEncodeError` at the
  writing of `collecte.json`, working folder left in place.

- NUL, ESC and other control characters of the tags of the PGN were
  copied as they were into `synthese.md`, and a booby-trapped `Variant`
  tag sent its escape sequences to the terminal.
- An answer to the startup questions typed in latin-1 stopped the
  script on a `UnicodeEncodeError`, working folder left in place.

## 3.4.1 - 2026-11-17

### Added

- TESTS.nfo: test T33, castling in the explorer.

### Changed

- HTTP agent header: `collecte-partie/3.4.1`.
- TESTS.nfo: T12, T13 and T26 state that the token file must exist.

### Fixed

- Explorer: a castling played was not found in the answer of the
  database, which writes it "king takes rook" (`e1h1`, `e1a1`, `e8h8`,
  `e8a8`) whereas the script compared with `e1g1`, `e1c1`, `e8g8` and
  `e8c8`. The castling came out at 0 games, at the rank "hors base",
  and triggered a false exit from theory, hence a premature stop of the
  querying. Both notations are now accepted.

## 3.4.0 - 2026-11-17

### Added

- Support of macOS: the default locations now depend on the platform.
  - `--venv`: `~/.local/share/collecte-partie/venv`.
  - `--catalogue`: `~/.local/share/collecte-partie`.
  - `--stockfish`: the binary found in the PATH, with a fallback to
    `/opt/homebrew/bin/stockfish`.
- Under macOS, the error messages and the help suggest `brew install`
  instead of `apt install`.
- README.nfo: macOS packages and table of the locations by platform.
- TESTS.nfo: variables `CAT` and `VENV` by platform, tests T31 and
  T32.
- CHANGELOG.md.

### Changed

- HTTP agent header: `collecte-partie/3.4`.
- TESTS.nfo: commands made portable (`head -n -10`, `shred`) and
  expected results of T03, T04, T14, T15 and T26 realigned on the
  defaults and the messages of version 3.3.0.

Under Debian, the defaults, the messages and the output of `--help`
are unchanged.

## 3.3.0 - 2026-10-09

History rebuilt from the conversations of 8 and 9 October 2026. The
numbering of the intermediate steps was not kept: their changes are
gathered here, under the version that the agent header of the script
carries.

### Added

- `--base {lichess,maitres}`: querying of the database of all the
  Lichess players, the one of <https://lichess.org/opening>, besides
  the masters database.
- `--cadences` and `--classements`: filters of the Lichess database,
  with the defaults of <https://lichess.org/opening> and the games
  since January 2017.
- Local catalog of the named openings of Lichess (public domain, CC0):
  `--installer-catalogue`, `--catalogue`, and column Ouverture in the
  summary.
- `--coups-min` (default 6): no stop on frequency in the starting
  window, the first exit from theory staying noted.
- Startup questions on an interactive terminal: side, opponent, time
  control and the four questions of the analysis project. The answers
  go into `contexte.md` and at the head of the summary.
- `--pseudos` to deduce the side from the White and Black tags, and
  `--sans-questions`.
- `partie-origine.pgn`: the PGN given, kept when the script fills in
  headers.
- Section 3: columns Nature (imprécision, erreur, gaffe at 50, 100 and
  300 cp) and G/N/P, and section 3 ter, mistakes and blunders by side
  with the best move, its line and the FEN.
- Section 1: phase markers (castlings, disappearance of the queens,
  entry into the endgame).
- Log: announcement of the Stockfish phase and estimated time left.
- `--sans-stockfish`.
- README.nfo and TESTS.nfo.

### Changed

- The Lichess database becomes the default database, in place of the
  masters database.
- The Stockfish evaluation is computed by default. `--avec-stockfish`
  stays accepted, without effect.
- `--longueur-pv` goes from 6 to 5.
- A rare move that stays in a line of the catalog is no longer an exit
  from theory.
- A Lichess identifier is exactly 8 or 12 characters: a missing file is
  reported as not found instead of being sent to Lichess.

### Fixed

- Explorer: the request asked only for the first ten moves
  (`moves=10`), a rarer move came out at 0 games and at the rank "hors
  base". It now asks for `moves=256`.

## Versions before 8 October 2026

Not documented. The script already collected the PGN, local or
downloaded from Lichess, the statistics of the masters database of the
explorer and, on request with `--avec-stockfish`, the evaluations of
the engine, all in a zip archive with `synthese.md`.

[Unreleased]: https://github.com/deuza/IAnalyze/compare/v4.0.2...dev
[4.0.2]: https://github.com/deuza/IAnalyze/compare/v4.0.1...v4.0.2
[4.0.1]: https://github.com/deuza/IAnalyze/compare/v4.0.0...v4.0.1
[4.0.0]: https://github.com/deuza/IAnalyze/releases/tag/v4.0.0
