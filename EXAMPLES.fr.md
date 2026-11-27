# IAnalyze : commandes, options et sorties

English version: [EXAMPLES.md](EXAMPLES.md)

Cette page est l'aide-mémoire d'IAnalyze, bâtie comme une page de manuel : chaque commande, chaque option, et ce que le terminal affiche.

Le [README](README.fr.md) explique l'installation et l'usage courant. [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md) explique le fonctionnement.

Le script, ses messages et ses fichiers sont en anglais : les commandes et les sorties de cette page sont donc les mêmes que dans sa version anglaise.

## Sommaire

- [NOM](#nom)
- [SYNOPSIS](#synopsis)
- [DESCRIPTION](#description)
- <details><summary><a href="#exemples">EXEMPLES</a></summary>

  - [première collecte](#première-collecte)
  - [collecte sans rien saisir](#collecte-sans-rien-saisir)
  - [partie de Lichess](#partie-de-lichess)
  - [avec l'explorateur](#avec-lexplorateur)
  - [pour un LLM qui n'ouvre pas les zip](#pour-un-llm-qui-nouvre-pas-les-zip)
  - [vérifier la réponse du LLM](#vérifier-la-réponse-du-llm)

  </details>
- <details><summary><a href="#options">OPTIONS</a></summary>

  - [général](#général)
  - [environnement virtuel](#environnement-virtuel)
  - [questions de démarrage](#questions-de-démarrage)
  - [catalogue des ouvertures](#catalogue-des-ouvertures)
  - [sortie](#sortie)
  - [explorateur](#explorateur)
  - [moteur](#moteur)
  - [vérificateur](#vérificateur)

  </details>
- [MESSAGES D'ERREUR](#messages-derreur)
- [CODES DE RETOUR](#codes-de-retour)
- [FICHIERS](#fichiers)
- [VOIR AUSSI](#voir-aussi)

## NOM

**ianalyze.py** : prépare l'analyse d'une partie d'échecs par un LLM.

**verify-analysis.py** : contrôle le PGN annoté que le LLM a rendu.

## SYNOPSIS

```text
./ianalyze.py SOURCE [options]
./ianalyze.py --install-venv [--venv PATH]
./ianalyze.py --install-catalog [--catalog DIR]
./ianalyze.py --purge-settings [--settings NAME]
./ianalyze.py --help

./verify-analysis.py ARCHIVE PGN [--summary FILE] [--name NAME] [--prompt-only] [--scope N]
```

SOURCE est un fichier PGN, l'adresse d'une partie de Lichess ou son identifiant.

## DESCRIPTION

`ianalyze.py` rassemble le PGN d'une partie, les statistiques de l'explorateur Lichess et les évaluations de Stockfish.\
Il écrit une archive zip et le prompt qui va avec, à donner à un LLM. Il n'analyse rien lui-même.

`verify-analysis.py` compare ensuite le PGN annoté rendu par le LLM à cette archive.

### Lire cette page

- Chaque exemple donne la commande, puis ce que le terminal affiche.
- Les lignes qui commencent par une heure forment le journal : elles vont sur la sortie d'erreur.
- La dernière ligne, le chemin du fichier produit, est la seule à aller sur la sortie standard.
- Une ligne `...` remplace des lignes retirées pour abréger.
- `~` désigne votre répertoire personnel.

### D'où viennent les sorties

Ce sont de vraies sorties de la version 5.0.0, relevées les 25 et 27 novembre 2026 sous Linux, avec Python 3.13 et Stockfish 16.\
Celles de l'explorateur viennent de collectes du même jour : ses statistiques changent chaque mois, les vôtres différeront.

Les évaluations du moteur varient elles aussi un peu, d'une machine à l'autre et d'un lancement à l'autre.\
Pour être rejoués sans jeton Lichess et sans rien saisir, la plupart des exemples ajoutent `--no-explorer` et `--no-questions`.

### Les parties des exemples

Les fichiers cités dans cette page sont dans trois répertoires du dépôt : `example-games` tient les parties, `tests/refused` les PGN que le script refuse, et `tests/llm` les réponses de LLM écrites pour les exemples.

Pour rejouer un exemple tel quel, placez-vous dans le répertoire de son fichier et appelez les scripts depuis là : `../ianalyze.py` à la place de `./ianalyze.py` depuis `example-games`, `../../ianalyze.py` depuis `tests/refused`. Le vérificateur lit une archive faite dans `example-games` et un PGN de `tests/llm` : lancez `../verify-analysis.py` depuis `example-games`, avec `../tests/llm/` devant le nom du PGN et celui de la conversation de `--summary`.

```bash
cd example-games
```

```bash
../ianalyze.py my-game.pgn --no-explorer --no-questions
```

| Fichier | Ce que c'est |
|---|---|
| `my-game.pgn` | une partie italienne de neuf demi-coups, celle de presque tous les exemples |
| `polish-opening.pgn` | une ouverture qui sort tôt de la théorie, pour les options de l'explorateur |
| `game-lichess-org.pgn` | une vraie partie de 20 coups, anonymisée, telle que Lichess l'exporte : c'est celle des essais du 21 novembre 2026 ([docs/TRIALS.fr.md](docs/TRIALS.fr.md#le-21-novembre-2026-avec---prompt-seul-aujourdhui---prompt-only)) |
| `commented-game.pgn` | une autre vraie partie de Lichess, 25 coups, anonymisée, exportée avec l'analyse du site : commentaires, variantes et horloges |
| `player-notes.pgn` | la même partie, sans l'analyse du site, ses horloges gardées, avec trois notes du joueur : celle des essais du 27 novembre 2026 ([docs/TRIALS.fr.md](docs/TRIALS.fr.md#le-27-novembre-2026-les-deux-routes-avec-les-prompts-publiés)) |
| `game-chess-com.pgn`, `game-chess-mail.pgn`, `game-ajedrezmail.pgn`, `game-lucas-chess.pgn` | quatre vraies parties, anonymisées, telles que ces sites et ce logiciel les exportent |
| `tests/refused/` : `french-notation.pgn`, `two-games.pgn`, `position.pgn`, `unclosed-brace.pgn`, `tag-with-moves.pgn`, `bracket-among-moves.pgn`, `null-move-in-check.pgn` | sept fichiers que le script refuse, pour les messages d'erreur |
| `tests/llm/` : `llm-annotated.pgn`, `llm-faulty.pgn`, `llm-faulty-words.pgn`, `llm-short.pgn` | quatre PGN annotés écrits pour l'exemple, à la place de ceux qu'un LLM rendrait |
| `tests/llm/llm-conversation.txt` | le texte d'une conversation, pour l'option `--summary` du vérificateur |

Ces fichiers sont en anglais, sauf `french-notation.pgn`, dont la notation française est justement le sujet.

Vos propres parties se rangent où vous voulez : le script prend le chemin du PGN que vous lui donnez, et écrit l'archive dans le répertoire courant, ou dans celui de `--output-dir`.

`my-game.pgn` est une partie italienne de neuf demi-coups :

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

`polish-opening.pgn` sort tôt de la théorie, ce qui met les seuils de l'explorateur à l'épreuve :

```text
1. b4 g6 2. Bb2 Nf6 3. e3 Bg7 4. Nf3 O-O *
```

## EXEMPLES

Ces exemples supposent IAnalyze installé (README, section 1). Les deux commandes d'installation sont décrites plus bas, à [`--install-venv`](#--install-venv) et à [`--install-catalog`](#--install-catalog).

### Première collecte

Au tout premier lancement dans un terminal, le script demande vos réglages, puis pose les questions propres à la partie, en anglais.

Entrée retient la valeur proposée entre parenthèses.

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

Les réglages ne seront plus demandés.\
La dernière ligne est le chemin de l'archive, celle d'avant nomme le prompt : collez son contenu dans une conversation neuve avec le LLM, et joignez l'archive.

### Collecte sans rien saisir

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

### Partie de Lichess

Par son adresse, ou par son identifiant, la suite de 8 caractères qui suit `lichess.org/` :

```bash
./ianalyze.py https://lichess.org/<identifier>
```

```bash
./ianalyze.py <identifier>
```

Le PGN est téléchargé, puis la collecte se déroule comme pour un fichier.\
L'archive porte l'identifiant de la partie : `analysis-<identifier>-<YYYYMMDD-HHMMSS>.zip`.

### Avec l'explorateur

Sans `--no-explorer`, le script interroge aussi l'explorateur de Lichess.\
Il lui faut le jeton et le catalogue des ouvertures (README, section 1).

```bash
./ianalyze.py my-game.pgn --no-questions --database masters
```

La section 2 de `summary.md` reçoit alors la table de l'explorateur, une ligne par demi-coup interrogé.

Pour cette partie et la base des maîtres, le 25 novembre 2026 :

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

### Pour un LLM qui n'ouvre pas les zip

`--prompt-only` écrit un prompt court, à coller seul dans la conversation. Aucune archive n'est écrite.

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

Le prompt porte les consignes, la partie, puis les évaluations du moteur :

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

### Vérifier la réponse du LLM

`llm-annotated.pgn` tient ici la place du PGN annoté qu'un LLM aurait rendu : il a été écrit pour l'exemple.\
Le vérificateur le compare à l'archive :

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

La dernière ligne de la section 6 varie avec la collecte : sur plusieurs fils, Stockfish ne donne pas toujours les mêmes lignes, et sur une autre archive de la même partie la variante peut être comptée comme celle du LLM. Avec `--threads 1`, deux collectes donnent les mêmes lignes (TECHNICAL, section 9).

Un PGN fautif, lui, voit chacun de ses défauts nommé.\
Celui-ci porte une ligne vide entre deux coups, un signe pour cent, un chiffre inventé et une variante écrite dans un commentaire :

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

Un autre PGN fautif montre les défauts que python-chess lit sans rien dire.\
Celui-ci porte une ligne vide dans un commentaire, un texte écrit hors des accolades, un roque écrit avec des zéros, un rang écrit `#7` et une seconde partie :

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

### Général

#### `-h, --help`

Affiche l'aide complète et les exemples, en anglais.

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

*Défaut : `30`*

Délai réseau maximal par requête, en secondes : export PGN, explorateur, téléchargement du catalogue.\
Il vaut au moins 1, avec `--install-catalog` aussi, qui télécharge également.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --timeout 60
```

Rien ne change à l'écran sans requête réseau : le délai ne joue que sur elles.\
Le journal est le même qu'à la section [Collecte sans rien saisir](#collecte-sans-rien-saisir).

#### `--debug`

Laisse remonter la trace complète d'une erreur inattendue, expurgée du jeton.\
Sans cette option, seul un message d'une ligne s'affiche.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --debug
```

Sans erreur inattendue, rien ne change. Le journal est le même qu'à la section [Collecte sans rien saisir](#collecte-sans-rien-saisir).

### Environnement virtuel

#### `--install-venv`

Crée l'environnement virtuel s'il manque, y installe ou met à jour python-chess, puis quitte.\
Il peut être relancé sans risque.

La première fois :

```bash
./ianalyze.py --install-venv
```

```text
[15:28:01] Creating the virtual environment: ~/IAnalyze/local/venv
[15:28:03] Installing python-chess in the virtual environment.
[15:28:07] Virtual environment ready: ~/IAnalyze/local/venv/bin/python3
```

Les fois suivantes :

```bash
./ianalyze.py --install-venv
```

```text
[15:28:41] Virtual environment already present: ~/IAnalyze/local/venv
[15:28:41] Installing python-chess in the virtual environment.
[15:28:42] Virtual environment ready: ~/IAnalyze/local/venv/bin/python3
```

Après une création interrompue, par Ctrl-C par exemple, l'environnement reste sans pip : le script le reconstruit avant d'installer python-chess.

```bash
./ianalyze.py --install-venv
```

```text
[15:28:17] Virtual environment incomplete, pip does not answer: rebuilding it: ~/IAnalyze/local/venv
[15:28:19] Installing python-chess in the virtual environment.
[15:28:20] Virtual environment ready: ~/IAnalyze/local/venv/bin/python3
```

Un répertoire sans `pyvenv.cfg`, un `--venv /usr` par erreur par exemple, n'est jamais pris pour un environnement à reconstruire : rien n'y est effacé.

#### `--venv PATH`

*Défaut : `local/venv`, dans le dossier de l'application*

Emplacement de l'environnement virtuel, à l'installation comme à l'usage.

```bash
./ianalyze.py --install-venv --venv ~/venv/chess
```

```text
[15:34:04] Creating the virtual environment: ~/venv/chess
[15:34:06] Installing python-chess in the virtual environment.
[15:34:07] Virtual environment ready: ~/venv/chess/bin/python3
```

Un répertoire qui n'est pas un environnement virtuel, non vide et sans `pyvenv.cfg`, est refusé avant toute installation : pip ne tourne pas sur le Python qu'il contient, et rien n'y est ajouté.

```bash
./ianalyze.py --install-venv --venv /usr
```

```text
--venv: /usr is not a virtual environment, the directory is not empty and has no pyvenv.cfg: nothing is changed. Give a new or empty directory, or an existing virtual environment.
```

Un chemin qui existe sans être un répertoire, un fichier donné par erreur, est refusé lui aussi, avec son propre message :

```bash
./ianalyze.py --install-venv --venv ~/chess-venv
```

```text
--venv: ~/chess-venv exists and is not a directory: nothing is changed. Give a new or empty directory, or an existing virtual environment.
```

La même option sert ensuite à chaque collecte, et le journal nomme l'environnement employé :

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --venv ~/venv/chess
```

```text
[15:34:07] Virtual environment: restarting with ~/venv/chess/bin/python3
[15:34:07] Reading the local PGN: my-game.pgn
...
```

### Questions de démarrage

#### `--no-questions`

Ne pose aucune question, ni camp ni contexte.\
Rien n'est retenu à votre place : le prompt dit alors au LLM que vos réponses n'ont pas été recueillies, et c'est lui qui vous pose les questions avant d'analyser.

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

*Défaut : ceux de vos réglages*

Vos noms de joueur, séparés par des virgules, cherchés sans tenir compte de la casse dans White et Black pour déduire votre camp : chacun comme le nom entier ou comme une suite de ses mots, jamais comme un morceau de mot. `Max` est trouvé dans `Max Power`, pas dans `Maxime` ni dans `Max_Power`.\
Le premier sert à compléter une balise vide. L'option remplace, le temps d'un lancement, les pseudos du fichier de réglages.

`my-game.pgn` oppose MyUsername, avec les Blancs, à Opponent.\
Avec le pseudo de celui-ci, le camp retenu pour le prompt change :

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

*Défaut : `settings.ini`*

Nom du fichier de réglages à employer à la place du vôtre : pseudos, cadence habituelle et niveau (README, section 2).\
C'est un nom de fichier qui finit par `.ini`, sans dossier et sans point au début : tout fichier de réglages est rangé à la racine du dossier de l'application, à côté de `settings.ini`.

Si le fichier n'existe pas encore, le script demande confirmation, pose ses trois questions dans le terminal, puis le crée.\
C'est la façon de tenir plusieurs profils sur un même compte, un par joueur par exemple.

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

Ici le pseudo du second joueur ne figure pas dans la partie : le script demande donc son camp.\
Les lancements suivants avec ce fichier ne redemandent pas les réglages.

- Une clef absente du fichier est demandée une seule fois, puis enregistrée.
- Une clef présente, même vide, n'est jamais redemandée.
- Une cadence ou un niveau illisible est redemandé.
- Les clefs et les sections que vous ajoutez sont conservées.

Un fichier mal formé arrête le script avec un message.

Un nom mal tapé ne crée aucun fichier : répondre `n` arrête le script avant toute écriture et toute collecte, avec le code de retour 1.

```bash
./ianalyze.py my-game.pgn --no-explorer --settings player3.ini
```

```text
[15:32:25] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:32:25] Reading the local PGN: my-game.pgn
Settings: player3.ini does not exist yet in ~/IAnalyze. Create it? [y/n] n
Nothing done: check the name given to --settings, or use --no-settings to run without settings.
```

Un fichier existant qui n'est pas un fichier de réglages, sans la section `[player]` ni la section `[joueur]` de l'ancien format, n'est jamais réécrit : les réponses ne servent qu'au lancement en cours, un avertissement dit pourquoi, et le fichier reste tel qu'il était.\
Ici `notes.ini`, à la racine du dossier de l'application, est un fichier INI sans rapport avec IAnalyze :

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

Un chemin est refusé, même à l'intérieur du dossier de l'application, avec le code de retour 2 :

```bash
./ianalyze.py my-game.pgn --settings ~/IAnalyze/settings.ini
```

```text
usage: ianalyze.py [-h] [--install-venv] [--venv PATH] [--no-questions]
...
ianalyze.py: error: --settings: ~/IAnalyze/settings.ini is not a settings name. Give a file name ending in .ini, without a folder and not starting with a dot: every settings file is kept in ~/IAnalyze. To run without settings, use --no-settings.
```

#### `--no-settings`

Le temps d'un lancement, le fichier de réglages n'est ni lu ni écrit, et ses questions ne sont pas posées.\
Le camp est demandé, ou déduit de `--usernames`. Le niveau vient de la balise Elo de votre camp, et la cadence de la balise TimeControl ou de la question sur la partie, qui propose alors "unspecified".

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

L'option exclut `--settings`, quel que soit le nom donné, et `--purge-settings`. Le code de retour vaut alors 2 :

```bash
./ianalyze.py my-game.pgn --no-settings --settings player2.ini
```

```text
usage: ianalyze.py [-h] [--install-venv] [--venv PATH] [--no-questions]
...
ianalyze.py: error: argument --settings: not allowed with argument --no-settings
```

#### `--purge-settings`

Supprime le fichier de réglages, puis quitte. Aucune partie n'est attendue.\
Vos réponses seront redemandées à la prochaine collecte lancée dans un terminal.

Avec `--settings`, c'est le fichier nommé qui est supprimé :

```bash
./ianalyze.py --purge-settings --settings player2.ini
```

```text
[15:41:22] Settings deleted: ~/IAnalyze/player2.ini. They will be asked again at the next collection run in a terminal.
```

Un fichier absent n'est pas une erreur, un répertoire est refusé.\
Un fichier qui n'est pas un fichier de réglages est refusé lui aussi : seul un fichier portant la section `[player]`, ou un fichier vide, est supprimé.

```bash
./ianalyze.py --purge-settings
```

```text
[15:41:23] Settings deleted: ~/IAnalyze/settings.ini. They will be asked again at the next collection run in a terminal.
```

Relancée aussitôt :

```bash
./ianalyze.py --purge-settings
```

```text
[15:41:23] No settings file to delete: ~/IAnalyze/settings.ini
```

### Catalogue des ouvertures

#### `--install-catalog`

Télécharge le catalogue des ouvertures de Lichess, le contrôle, puis quitte.\
Relancer l'option le met à jour. Un échec laisse l'ancien catalogue en place.

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

*Défaut : `local/`, dans le dossier de l'application*

Répertoire du catalogue local, à l'installation comme à l'usage.

```bash
./ianalyze.py --install-catalog --catalog ~/chess/catalog
```

```text
[15:34:22] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:34:22] Downloading the catalog: https://raw.githubusercontent.com/lichess-org/chess-openings/master/a.tsv
...
[15:34:24] Catalog installed: 3865 lines, 3865 named positions, 7982 known positions, in ~/chess/catalog/catalog.tsv
```

La même option sert ensuite à chaque collecte :

```bash
./ianalyze.py my-game.pgn --catalog ~/chess/catalog
```

### Sortie

Sans aucune de ces options, le script écrit deux fichiers dans le répertoire courant : l'archive et le prompt complet.

| Vous ajoutez | Le script écrit | Vous en faites |
|---|---|---|
| rien | l'archive `.zip` et le prompt complet `.prompt.txt` | vous collez le prompt dans la conversation et vous joignez l'archive |
| `--prompt-only` | le prompt court, sans archive | vous collez le prompt, sans rien joindre |
| `--no-prompt` | l'archive, sans prompt | vous rédigez vous-même votre demande au LLM |
| `--prompt FILE` | l'archive et un prompt tiré de votre propre modèle | vous collez le prompt et vous joignez l'archive |

#### `--output-dir DIR`

*Défaut : `.`, le répertoire courant*

Répertoire où le script écrit ses fichiers. Il est créé au besoin.

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

Pendant la collecte, le script range ses fichiers dans un dossier de travail, `analysis-<label>-<YYYYMMDD-HHMMSS>`.\
Il le compresse ensuite en zip, puis le supprime.

Avec cette option, le dossier reste à côté de l'archive.\
Il sert quand le LLM n'ouvre pas les zip : vous lui envoyez alors les fichiers du dossier.

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

Le dossier porte les fichiers de l'archive :

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

Écrit un prompt court, à coller seul dans la conversation, sans pièce jointe : quelques consignes, la partie, puis les évaluations de Stockfish.

C'est la route à prendre avec un compte gratuit, ou avec un LLM qui n'ouvre pas les zip ou n'exécute pas de code (README, section 4).\
Le PGN annoté lui est demandé dans un bloc de code.

Aucune archive n'est écrite : le prompt est le seul fichier produit, et c'est son chemin qui est écrit sur la sortie standard.\
Pour l'archive et ses données, lancez une collecte sans cette option.

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

Ajoutez `--keep-folder` si vous comptez faire contrôler la réponse du LLM par `verify-analysis.py` : le dossier de travail reste alors à côté du prompt.

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

S'exclut avec `--no-prompt`.

#### `--no-prompt`

N'écrit que l'archive, sans prompt. S'exclut avec `--prompt` et avec `--prompt-only`.

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

*Défaut : `prompt-template.txt`, rangé à côté du script*

À n'employer que si vous avez écrit votre propre modèle de prompt.

Le prompt d'une partie n'est pas un texte fixe. Le script le fabrique à partir d'un modèle :\
un fichier texte dont il remplit les blancs, votre pseudo, votre camp ou le nom de l'archive, et dont il ne garde que les passages utiles à cette partie.

Cette option lui fait prendre votre modèle à la place de celui du dépôt.

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

Le fichier doit exister.\
Pour écrire un modèle, partez d'une copie de `prompt-template.txt` : ce qu'il peut contenir est décrit dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md), section 12.

Avec `--prompt-only`, le modèle par défaut est `prompt-only-template.txt`, et c'est de lui qu'il faut partir.

### Explorateur

Ces options demandent le jeton et le catalogue.\
Les extraits viennent de la section 2 de `summary.md`, relevés le 25 novembre 2026.

#### `--database {lichess,masters}`

*Défaut : `lichess`*

Base interrogée :

- `lichess` : les parties classées de tous les joueurs du site, la base de <https://lichess.org/opening>
- `masters` : les parties de maîtres

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

La même partie dans la base des maîtres, où elle est bien plus rare :

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

*Défaut : `bullet,blitz,rapid,classical,correspondence`*

Base `lichess` seulement.

Cadences retenues, séparées par des virgules, parmi :

- `ultraBullet`
- `bullet`
- `blitz`
- `rapid`
- `classical`
- `correspondence`

La casse est tolérée, les doublons sont retirés.

#### `--ratings LIST`

*Défaut : `1000,1200,1400,1600,1800,2000,2200,2500`*

Base `lichess` seulement.\
Tranches de classement retenues parmi 0, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2500.

Chaque tranche court de sa valeur à la suivante : 0 couvre 0 à 999 (affichée "400" sur le site), 2500 tout ce qui dépasse.\
Une partie est rangée selon la moyenne des classements de ses deux joueurs.

Les filtres par défaut, plus la date de début fixée à janvier 2017, reprennent ceux de <https://lichess.org/opening> : vous y retrouvez les mêmes pourcentages.\
Les deux filtres ensemble, sur les parties lentes des joueurs classés sous 1200 :

```bash
./ianalyze.py polish-opening.pgn --no-questions --min-moves 0 --speeds rapid,classical --ratings 0,1000
```

| # | Move | Side | Pos. games | Played | Rank | Freq. | White score | Top move | Top freq. | Top White score | Opening |
|---:|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|
| 1 | 1 | White | 222375359 | b4 | 14 | 0.2 % | 46.9 % | e4 | 68.6 % | 52.6 % | A00 Polish Opening |
| 2 | 1 | Black | 504056 | g6 | 7 | 2.9 % | 47.2 % | e5 | 49.7 % | 46.1 % | - |

#### `--token-file FILE`

*Défaut : `~/.lichess_token`*

Fichier contenant le jeton personnel, et rien d'autre.\
Si le fichier manque, le script s'arrête avant toute requête :

```bash
./ianalyze.py my-game.pgn --no-questions --token-file ~/.test-token
```

```text
[15:38:19] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:38:19] Reading the local PGN: my-game.pgn
Token missing: ~/.test-token not found.
```

#### `--min-games N`

*Défaut : `50`*

Arrêt quand la position compte moins de N parties dans la base.\
Avec le seuil par défaut, 50, la Polonaise s'arrête au troisième demi-coup dans la base des maîtres :

```bash
./ianalyze.py polish-opening.pgn --no-questions --database masters
```

```text
Stop of the querying: insufficient sample at ply 3: 12 games for a threshold of 50.
```

Pour un seuil plus exigeant :

```bash
./ianalyze.py my-game.pgn --no-questions --min-games 200
```

#### `--min-frequency P`

*Défaut : `10.0`*

Un coup joué dans moins de P % des parties de la position est rare.\
Un coup rare qui mène hors du catalogue des ouvertures est une sortie de théorie. S'il reste dans une ligne nommée, ce n'en est pas une.

0 désactive le critère.

```bash
./ianalyze.py polish-opening.pgn --no-questions --min-moves 0
```

```text
Stop of the querying: exit from theory at ply 2: g6 played at 4.9 %, threshold 10.0 %, outside the catalog.
```

Avec 0, plus aucun coup n'est une sortie de théorie :

```bash
./ianalyze.py polish-opening.pgn --no-questions --min-moves 0 --min-frequency 0
```

```text
Stop of the querying: end of the game.
```

#### `--min-moves N`

*Défaut : `6`*

Aucun arrêt sur la fréquence avant la fin du coup N, soit 2N demi-coups.\
La table couvre ainsi le début de partie même après une sortie précoce.

Le seuil de parties reste actif, et la première sortie est notée même dans la fenêtre. 0 arrête dès la première sortie.

Avec la valeur par défaut, la table de la Polonaise va jusqu'au bout de la partie, bien que 1... g6 soit une sortie de théorie : voir `--database`, plus haut.\
Avec 0, elle s'arrête sur ce coup :

```bash
./ianalyze.py polish-opening.pgn --no-questions --min-moves 0
```

```text
Stop of the querying: exit from theory at ply 2: g6 played at 4.9 %, threshold 10.0 %, outside the catalog.
```

#### `--exhaustive`

Ignore les deux seuils pour l'arrêt : l'interrogation descend tant que la base connaît la position.\
La première sortie reste notée.

```bash
./ianalyze.py polish-opening.pgn --no-questions --exhaustive
```

```text
Stop of the querying: end of the game.
```

#### `--max-plies N`

*Défaut : `60`*

Plafond de demi-coups interrogés, garde-fou toujours actif.

```bash
./ianalyze.py my-game.pgn --no-questions --exhaustive --max-plies 4
```

```text
Stop of the querying: cap of 4 plies reached (option --max-plies).
```

#### `--pause S`

*Défaut : `2.0`*

Pause entre deux requêtes à l'explorateur, 2 secondes au minimum.\
Avec une pause de 3 secondes, visible à l'heure de chaque ligne :

```bash
./ianalyze.py my-game.pgn --no-questions --pause 3 --max-plies 3
```

```text
[15:39:43] Explorer: ply 1 (e4)
[15:39:43] Explorer: ply 2 (e5)
[15:39:46] Explorer: ply 3 (Nf3)
```

#### `--no-explorer`

Saute la collecte explorateur : ni réseau vers l'explorateur, ni jeton, ni catalogue requis.\
Le journal passe alors de la lecture de la partie au moteur, sans ligne "Explorer" :

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

### Moteur

L'évaluation Stockfish fait partie de toute collecte : le binaire est vérifié avant toute écriture.

#### `--stockfish-moves N`

*Défaut : `0`*

Limite le moteur aux N premiers coups entiers, soit 2N demi-coups. 0 analyse toute la partie.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --stockfish-moves 3
```

```text
...
[15:35:05] Stockfish: evaluation of 6 plies, depth 18, multipv 3, threads 4. This is the longest phase.
...
```

#### `--depth D`

*Défaut : `18`*

Profondeur de recherche par position, de 1 à 60.\
Le temps de calcul croît très vite avec elle : au-delà de 60, une seule position occuperait le moteur des heures !

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --depth 12
```

```text
...
[15:35:10] Stockfish: evaluation of 9 plies, depth 12, multipv 3, threads 4. This is the longest phase.
...
```

#### `--multipv K`

*Défaut : `3`*

Nombre de meilleurs coups que le moteur donne pour chaque position.\
Avec 3, la synthèse montre, en face de chaque coup de la partie, les trois coups que Stockfish préférait.

Si le coup joué n'en fait pas partie, le script le fait évaluer à part, pour mesurer ce qu'il perd.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --multipv 5
```

```text
...
[15:35:12] Stockfish: evaluation of 9 plies, depth 18, multipv 5, threads 4. This is the longest phase.
...
```

#### `--threads N`

*Défaut : le nombre de processeurs de la machine*

Nombre de processeurs que Stockfish emploie en même temps. Baissez-le pour garder la machine disponible pendant le calcul.

#### `--hash MB`

*Défaut : `256`*

Mémoire que Stockfish réserve à ses calculs, en mégaoctets. La valeur par défaut convient à l'usage courant.

Les deux ensemble.\
Le journal nomme le nombre de fils, "threads", pas la taille de la table :

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --threads 2 --hash 128
```

```text
...
[15:35:26] Stockfish: evaluation of 9 plies, depth 18, multipv 3, threads 2. This is the longest phase.
...
```

Ces trois réglages, MultiPV, Threads et Hash pour Stockfish, sont expliqués dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md), section 9.

#### `--stockfish PATH`

*Défaut : le binaire trouvé dans le PATH, sinon `/usr/games/stockfish` sous Debian et `/opt/homebrew/bin/stockfish` sous macOS*

Binaire du moteur.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --stockfish /usr/games/stockfish
```

Le journal est le même qu'à la section [Collecte sans rien saisir](#collecte-sans-rien-saisir).

Un chemin qui ne mène à rien arrête le script avant la collecte :

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --stockfish /nowhere
```

```text
[15:35:45] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:35:45] Reading the local PGN: my-game.pgn
Stockfish not found: /nowhere. Install it (apt install stockfish, in /usr/games), or give its path with --stockfish. The engine evaluation is part of every collection.
```

#### `--pv-length N`

*Défaut : `5`*

Demi-coups de variante principale reproduits dans la synthèse, 0 pour la variante entière.

Les variantes complètes restent dans `stockfish/evaluations.json`.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --pv-length 2 --keep-folder
```

Dans `summary.md`, les variantes sont alors coupées à deux demi-coups :

```text
### 3a. Principal variations of the engine

Variations cut at 2 plies; the full variations are in `stockfish/evaluations.json`.

- Ply 1, White plays e4 (position before the move)
    - 1st, played (+0.35): 1. e4 e5
    - 2nd (+0.30): 1. d4 Nf6
    - 3rd (+0.27): 1. Nf3 e6
...
```

### Vérificateur

Les options qui suivent sont celles de `verify-analysis.py`.

#### `ARCHIVE PGN`

L'archive écrite par `ianalyze.py`, zip ou dossier décompressé, puis le PGN annoté rendu par le LLM.\
Un tiret à la place du PGN signale que le LLM n'en a rendu aucun.

Le dossier peut aussi être celui qui contient la collecte, s'il n'en contient qu'une complète : le bilan la nomme.\
Voir [Vérifier la réponse du LLM](#vérifier-la-réponse-du-llm) pour un bilan complet.

#### `--name NAME`

Nom du modèle essayé, repris en tête du bilan.

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

La conversation avec le LLM, copiée dans un fichier texte.\
Les positions et les évaluations qu'elle cite sont alors contrôlées aussi, dans deux sections de plus.

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

Sans PGN rendu, seule la conversation est contrôlée :

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

#### `--prompt-only`, pour le vérificateur

Le PGN répond au prompt court de `ianalyze.py --prompt-only`.\
Ce prompt demande moins que le prompt complet : les contrôles qu'il ne fonde pas sont sautés.

L'archive est ici le dossier gardé par `--prompt-only --keep-folder`.

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

Le périmètre convenu avec le LLM, en coups.\
Les erreurs et gaffes jouées après le coup N ne sont pas attendues dans le PGN : le prompt limite les commentaires au périmètre.

Sans cette option, le périmètre est celui de votre réponse à la question de démarrage, lu dans l'archive.\
Elle sert quand il a été fixé dans la conversation.

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

## MESSAGES D'ERREUR

Un message d'erreur n'est pas horodaté : c'est la dernière ligne, et le code de retour vaut 1 ou 2.

### Fichier introuvable

```bash
./ianalyze.py missing-game.pgn
```

```text
[15:35:52] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
PGN file not found: missing-game.pgn
```

### Partie notée en français

Les coups doivent être notés en anglais : K, Q, R, B, N.

```bash
./ianalyze.py french-notation.pgn --no-explorer --no-questions
```

```text
[15:35:52] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:35:52] Reading the local PGN: french-notation.pgn
Corrupt PGN: "Cf3", line 1, is neither a move in English notation (K, Q, R, B, N) nor another PGN element. A game written in French notation or with figurines must be converted, free text placed between braces.
```

### Résultat répété en fin de fichier

Ce n'est pas une erreur : l'export de chess-mail.com écrit le résultat deux fois, et le second est ignoré. Le journal le signale, la collecte se poursuit.

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

### Plusieurs parties dans le fichier

```bash
./ianalyze.py two-games.pgn --no-explorer --no-questions
```

```text
[15:36:57] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:36:57] Reading the local PGN: two-games.pgn
The PGN contains 2 games: put the one to analyze in a separate file.
```

### Partie qui part d'une position

```bash
./ianalyze.py position.pgn --no-explorer --no-questions
```

```text
[15:36:57] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:36:57] Reading the local PGN: position.pgn
The game does not start from the initial position, it starts from a FEN tag. IAnalyze analyzes a whole game, from the first move to the last: to study a position, load it into an analysis board.
```

### Commentaire jamais fermé

```bash
./ianalyze.py unclosed-brace.pgn --no-explorer --no-questions
```

```text
[15:36:57] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:36:57] Reading the local PGN: unclosed-brace.pgn
Corrupt PGN: the comment opened by a brace on line 1 is never closed.
```

### Des coups sur une ligne de balise

Une balise occupe une ligne entière, avant les coups de sa partie. python-chess sauterait cette ligne, ses coups avec elle, et l'analyse porterait sur une autre partie que la vôtre. Une ligne de crochets parmi les coups est refusée de même : python-chess jouerait les coups qu'elle contient.

```bash
./ianalyze.py tag-with-moves.pgn --no-explorer --no-questions
```

```text
[18:49:51] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[18:49:51] Reading the local PGN: tag-with-moves.pgn
Corrupt PGN: line 4 is not a well-formed tag, [Name "value"] alone on its line: python-chess would skip it, together with what it carries.
```

Il en va de même d'une ligne qui commence par un crochet parmi les coups :

```bash
./ianalyze.py bracket-among-moves.pgn --no-explorer --no-questions
```

```text
[10:47:00] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[10:47:00] Reading the local PGN: bracket-among-moves.pgn
Corrupt PGN: line 9 starts with a bracket among the moves. A tag goes before the moves of its game, and python-chess would read as moves what the brackets hold.
```

### Coup nul joué en échec

Un coup nul, `--`, passe le trait. Joué en échec, il laisse le roi attaqué : les positions qui suivent sont illégales, et le moteur ne peut pas les évaluer.

```bash
./ianalyze.py null-move-in-check.pgn --no-explorer --no-questions
```

```text
[18:49:52] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[18:49:52] Reading the local PGN: null-move-in-check.pgn
Corrupt PGN: null move "--" played in check, at move 2, by Black. Passing leaves the king attacked: the positions that follow are illegal, and the engine cannot evaluate them.
```

### PGN en UTF-16, coupé

Un fichier en UTF-16 qui a perdu un octet, par un transfert coupé par exemple, est refusé avec sa cause : dans cet encodage, un octet perdu décale tout le texte qui suit.\
Le dernier octet est ici retiré exprès :

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

### Option inconnue

Ici un ancien nom français, refusé depuis la version 5.0.0. Le code de retour vaut 2.

```bash
./ianalyze.py my-game.pgn --sans-questions
```

```text
usage: ianalyze.py [-h] [--install-venv] [--venv PATH] [--no-questions]
...
ianalyze.py: error: unrecognized arguments: --sans-questions
```

### Valeur refusée

Le code de retour vaut 2.

```bash
./ianalyze.py my-game.pgn --pause 1
```

```text
usage: ianalyze.py [-h] [--install-venv] [--venv PATH] [--no-questions]
...
ianalyze.py: error: --pause must not go below 2 seconds
```

### Valeur hors des bornes du moteur

Les bornes sont celles que le moteur annonce : elles changent d'une version de Stockfish à l'autre.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --multipv 9999
```

```text
[15:36:57] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:36:58] Reading the local PGN: my-game.pgn
--multipv: 9999 is out of the bounds of the engine /usr/games/stockfish, which accepts 1 to 500 for MultiPV.
```

### Moteur introuvable

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --stockfish /nowhere
```

```text
[15:35:45] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:35:45] Reading the local PGN: my-game.pgn
Stockfish not found: /nowhere. Install it (apt install stockfish, in /usr/games), or give its path with --stockfish. The engine evaluation is part of every collection.
```

### Jeton absent

Sans `--no-explorer`, le script a besoin du jeton Lichess (README, section 1).

```bash
./ianalyze.py my-game.pgn --no-questions
```

```text
[15:40:29] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
[15:40:29] Reading the local PGN: my-game.pgn
Token missing: ~/.lichess_token not found.
```

### Jeton refusé

Le jeton est en place, mais Lichess le refuse : faux, expiré ou révoqué.\
L'exécution s'arrête à la première requête, avant le moteur :

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

Le dossier de travail garde la réponse de Lichess, dans `explorer/001-e2e4.json` : supprimez-le une fois lu.

### Catalogue absent

Le jeton est en place, mais le catalogue des ouvertures n'a pas été installé.

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

### Modèle de prompt fautif

Le modèle désigné par `--prompt` porte ici une valeur mal écrite.

```bash
./ianalyze.py my-game.pgn --no-explorer --no-questions --prompt ~/faulty-template.txt
```

```text
[15:36:58] Virtual environment: restarting with ~/IAnalyze/local/venv/bin/python3
Prompt template ~/faulty-template.txt, line 21: unknown value {{VERSON}}, accepted values: VERSION, REPOSITORY, ARCHIVE, USERNAMES, SIDE, RATING, TIME_CONTROL, ANNOTATOR, DATABASE, INACCURACY_THRESHOLD, MISTAKE_THRESHOLD, BLUNDER_THRESHOLD, DEPTH, MULTIPV, GAME_PGN, ENGINE_TABLE, RESULT_ALERT, PLAYER_INSTRUCTIONS, OPENING, PLIES, PLIES_EVALUATED, PLAYER_WEAK_MOVES, FENCE
```

### Fichier de réglages à l'ancien format

Un `settings.ini` à l'ancien format porte la section `[joueur]`, et non `[player]` : le `reglages.ini` de la version 4 recopié à la main, ou un fichier écrit par une version de développement de la 5.0.0. `--purge-settings` le refuse, comme tout fichier qui n'est pas un fichier de réglages, avec le code de retour 1. Supprimez-le à la main, ou lancez d'abord une collecte : elle repose les questions des réglages et ajoute la section `[player]`.

```bash
./ianalyze.py --purge-settings
```

```text
--purge-settings: ~/IAnalyze/settings.ini is not a settings file, it does not carry the [player] section. Nothing is deleted.
```

### Dossier à plusieurs collectes, pour le vérificateur

Le répertoire courant contient ici plusieurs dossiers de collecte complets. Le code de retour vaut 2.

```bash
./verify-analysis.py . llm-annotated.pgn
```

```text
Cannot read: . holds 3 complete collections: analysis-my-game-20261125-153432, analysis-my-game-20261125-153440, analysis-my-game-20261125-153545. Give the folder of the one that the LLM received.
```

### Archive introuvable, pour le vérificateur

Le code de retour vaut 2.

```bash
./verify-analysis.py missing-archive.zip llm-annotated.pgn
```

```text
Cannot read: [Errno 2] No such file or directory: 'missing-archive.zip'
```

## CODES DE RETOUR

`ianalyze.py` :

| Code | Signification |
|---|---|
| 0 | succès |
| 1 | erreur signalée par un message, dont une valeur que le moteur n'admet pas, ou erreur inattendue |
| 2 | option inconnue, options qui s'excluent, ou valeur refusée avant toute lecture de la partie |
| 130 | interruption (Ctrl-C) |

`verify-analysis.py` :

| Code | Signification |
|---|---|
| 0 | aucun `FAIL` dans le bilan |
| 1 | au moins un `FAIL` |
| 2 | un fichier ne peut pas être lu, ou l'archive n'est pas celle d'IAnalyze : aucun contrôle n'a eu lieu |

## FICHIERS

Ce que le script lit :

| Fichier | Rôle |
|---|---|
| `local/venv` | l'environnement virtuel, où vit python-chess |
| `local/catalog.tsv` | le catalogue des ouvertures |
| `settings.ini` | vos réglages : pseudos, cadence habituelle, niveau |
| `~/.lichess_token` | votre jeton Lichess, en mode 600 |
| `prompt-template.txt`, `prompt-only-template.txt` | les modèles de prompt, à côté du script |
| `/usr/games/stockfish` | le moteur sous Debian, quand le PATH ne le contient pas, celui de root par exemple. Sinon, celui du PATH |
| `/opt/homebrew/bin/stockfish` | le moteur sous macOS, quand le PATH ne le contient pas |

Ce qu'il écrit, dans le répertoire courant ou dans celui de `--output-dir` :

| Fichier | Rôle |
|---|---|
| `analysis-<label>-<YYYYMMDD-HHMMSS>.zip` | l'archive, à joindre à la conversation |
| `analysis-<label>-<YYYYMMDD-HHMMSS>.prompt.txt` | le prompt, à coller dans la conversation |
| `analysis-<label>-<YYYYMMDD-HHMMSS>/` | le dossier de travail, gardé seulement avec `--keep-folder` ou après un échec |

Le contenu de l'archive est décrit dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md), section 10.

Le fichier de réglages, tel que le script l'écrit après la première collecte, en anglais lui aussi :

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

## VOIR AUSSI

- [README.fr.md](README.fr.md) : l'installation, l'usage courant, le choix du LLM
- [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md) : le fonctionnement du script, le format des fichiers, le guide pour reprendre le projet
- [docs/TESTS.fr.md](docs/TESTS.fr.md) : la suite de tests, test par test
- [docs/TRIALS.fr.md](docs/TRIALS.fr.md) : les essais des LLM
- [CHANGELOG.md](CHANGELOG.md) : l'historique des versions (en anglais)
- `./ianalyze.py --help` : le résumé des options, dans le terminal, en anglais
