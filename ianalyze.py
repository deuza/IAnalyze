#!/usr/bin/env python3
"""
Gathers the material for the analysis of a chess game.

This program produces no analysis. It collects and formats:

  1. the PGN of the game, read from a local file or downloaded
     from Lichess;
  2. the statistics of the Lichess explorer, position by position,
     to find where the game leaves theory: the database of all
     Lichess players by default, or the masters database with
     --database masters. A rare move that stays within a line of the
     catalog of named openings, kept locally, does not count as
     leaving theory;
  3. the Stockfish evaluation of the game in multipv, computed locally
     to spare the analyst this work. The engine is mandatory.

Before the collection, on an interactive terminal, the script asks for
your side if the headers do not give it, then for your answers to the
startup questions, stored in context.md and repeated at the top of
the summary.

Your username, your usual time control and your rating are not in the
code: you are asked for them only once, on the first run in a
terminal, and they are then kept in a settings file that you can edit
by hand.

Next to the archive, the script writes the analysis prompt for the
game, drawn from the template prompt-template.txt: you paste it into the
conversation, with the archive as an attachment. With --prompt-only,
it is a short prompt, drawn from prompt-only-template.txt, that carries
the game and the Stockfish evaluations: it is pasted on its own,
without an attachment, and no archive is written then.

The result is a zip archive containing the raw data and a single
summary file, meant to be attached to an annotation conversation. The
working folder is deleted once the archive has been checked, unless
you ask otherwise.

Run it with --help for the list of options and usage examples.
"""

from __future__ import annotations

import argparse
import codecs
import concurrent.futures
import configparser
import contextlib
import csv
import datetime
import http.client
import io
import json
import logging
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile

# ===========================================================================
# Bootstrapping the virtual environment
#
# The python-chess module is not packaged by Debian. You must therefore
# install it in a dedicated virtual environment rather than in the
# system's Python environment. This block handles three cases:
#
#   - the module is available: we carry on normally;
#   - it is not, but the virtual environment exists: we restart
#     automatically with the interpreter of that environment;
#   - it is not and the environment does not exist: we tell you what to
#     do, or we create it if you passed --install-venv.
# ===========================================================================


def est_fichier(candidat: pathlib.Path) -> bool:
    """
    True if the path names a file, false in every other case.

    Path.is_file() returns false for a missing file, but lets other system
    errors through: name too long, forbidden directory. Text pasted by
    mistake instead of a file name thus ended in an unexpected error.
    Here, what the system refuses to look at is not a readable file, and
    the usual message follows.
    """
    try:
        return candidat.is_file()
    except OSError:
        return False


def est_repertoire(candidat: pathlib.Path) -> bool:
    """True if the path names a directory, false in the other cases."""
    try:
        return candidat.is_dir()
    except OSError:
        return False


#: True on macOS. The installation commands suggested in the messages
#: and the location of the engine depend on it.
EST_MACOS = sys.platform == "darwin"

#: Folder of the application, found through the real path of the script:
#: a symbolic link placed elsewhere still leads to the folder of the
#: repository. Everything the script creates for itself lives in it, at
#: the same place on Debian and on macOS: deleting the folder removes
#: everything, and you need no root rights to install anything.
DOSSIER_APPLICATION = os.path.dirname(os.path.realpath(__file__))

#: Data directory of the script, the local/ folder of the application:
#: the virtual environment and the catalog go there, everything that the
#: script can rebuild by itself. Emptying it brings the application back
#: to a fresh clone without touching the settings, which stay outside
#: (REGLAGES_DEFAUT). Up to version 4.0.2, the data lived in
#: ~/.local/share/IAnalyze and the settings in ~/.config/IAnalyze; up to
#: version 3.8.0, Debian kept the data in /opt/venv/lichess and in
#: /usr/local/share.
DONNEES = os.path.join(DOSSIER_APPLICATION, "local")

#: Installation commands for the prerequisites, repeated in the messages
#: and in the help. On macOS, the Homebrew Python already provides the
#: venv module: there is no separate package to install.
if EST_MACOS:
    CMD_PAQUET_VENV = "brew install python"
    CMD_PAQUET_STOCKFISH = "brew install stockfish"
else:
    CMD_PAQUET_VENV = "apt install python3-venv"
    CMD_PAQUET_STOCKFISH = "apt install stockfish"

#: Default location of the dedicated virtual environment.
VENV_DEFAUT = DONNEES + "/venv"

#: Environment variable that guards against an endless restart loop if
#: the virtual environment exists but remains incomplete.
MARQUEUR_RELANCE = "IANALYZE_RELAUNCHED"

#: Token in use, kept only so that the last-resort error handler can
#: redact it from an unexpected message.
JETON_COURANT: str | None = None

#: With --debug, unexpected errors come up with their full traceback.
DEBUG = False

try:
    import chess
    import chess.engine
    import chess.pgn
    CHESS_DISPONIBLE = True
except ImportError:
    CHESS_DISPONIBLE = False

#: On a game that contains a null move, python-chess writes at each
#: following position "Not transmitting history with null moves to UCI
#: engine": it warns that it gives the engine the position alone, without
#: the move history. The evaluations do not depend on it, and the null
#: move is already reported in the log and in the summary: this repeated
#: message is filtered out. The other notices of the library are still
#: displayed.
logging.getLogger("chess.engine").addFilter(
    lambda avis: "null moves" not in avis.getMessage())

#: python-chess also writes each illegal move of a PGN on standard error,
#: in English, before the script refuses the game with the same move:
#: the message came twice. Its log of the PGN reading is silenced, the
#: refusal giving the move.
logging.getLogger("chess.pgn").setLevel(logging.CRITICAL)


def python_du_venv(venv: str) -> pathlib.Path:
    """Returns the path of the interpreter of a virtual environment."""
    return pathlib.Path(os.path.expanduser(venv)) / "bin" / "python3"


def venv_operationnel(venv: str) -> bool:
    """
    Tells whether the virtual environment exists and provides python-chess.

    The check is done by actually running the interpreter of the
    environment, rather than by assuming that an existing directory is a
    working environment.
    """
    interpreteur = python_du_venv(venv)
    if not est_fichier(interpreteur):
        return False
    try:
        subprocess.run([str(interpreteur), "-c", "import chess"],
                       check=True, capture_output=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False
    return True


def venv_incomplet(venv: str) -> bool:
    """
    Tells whether a virtual environment was left incomplete: its
    pyvenv.cfg and its interpreter exist, but pip does not answer.

    A creation interrupted before its end (Ctrl-C, killed process, cut
    power) leaves such an environment: python -m venv writes pyvenv.cfg
    and the interpreter first, pip last. --install-venv took it for
    complete, then failed on "No module named pip". An interpreter that
    exists but can no longer be run gives the same verdict. A timeout
    does not: in doubt, nothing is rebuilt.

    A directory without pyvenv.cfg is not a virtual environment: it is
    never taken for an incomplete one, so that the rebuild, which empties
    the directory, can only ever reach a virtual environment. A wrong
    --venv, /usr for example, must not lose its content.
    """
    racine = pathlib.Path(os.path.expanduser(venv))
    interpreteur = python_du_venv(venv)
    if not (est_fichier(racine / "pyvenv.cfg")
            and est_fichier(interpreteur)):
        return False
    try:
        rendu = subprocess.run([str(interpreteur), "-m", "pip", "--version"],
                               capture_output=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        return False
    except OSError:
        return True
    return rendu.returncode != 0


def pas_un_venv(venv: str) -> bool:
    """
    Tells whether --venv names an existing directory that is not a
    virtual environment: not empty, and without pyvenv.cfg. /usr is one,
    with its bin/python3, so is a home directory.

    --install-venv refuses it: pip would run on the Python found
    there, often the one of the system, and python -m venv would scatter
    its files among those already in place. A missing or empty directory
    is not refused, a virtual environment is created in it. A directory
    that the system refuses to list is not refused either: python -m
    venv then fails with its own message.
    """
    racine = pathlib.Path(os.path.expanduser(venv))
    if not est_repertoire(racine) or est_fichier(racine / "pyvenv.cfg"):
        return False
    try:
        return any(racine.iterdir())
    except OSError:
        return False


def installer_venv(venv: str) -> None:
    """
    Creates the virtual environment if missing, then installs python-chess.

    The operation is idempotent: you can safely run it again on an
    environment already in place, it will then simply update the module.
    An environment left incomplete by an interrupted creation is rebuilt
    from scratch first (see venv_incomplet). A directory that is not a
    virtual environment is refused before anything runs (see
    pas_un_venv), and so is a path that exists without being a
    directory.
    """
    racine = pathlib.Path(os.path.expanduser(venv))
    interpreteur = python_du_venv(venv)

    # A path that exists without being a directory, a regular file for
    # example, cannot receive an environment: python -m venv failed on it,
    # and the message asked whether python3-venv was installed. A broken
    # symbolic link is refused the same way, python -m venv failing on it
    # too.
    if os.path.lexists(racine) and not est_repertoire(racine):
        raise SystemExit("--venv: %s exists and is not a directory: nothing "
                         "is changed. Give a new or empty directory, or an "
                         "existing virtual environment." % racine)

    if pas_un_venv(venv):
        raise SystemExit("--venv: %s is not a virtual environment, the "
                         "directory is not empty and has no pyvenv.cfg: "
                         "nothing is changed. Give a new or empty "
                         "directory, or an existing virtual environment."
                         % racine)

    # The exit code of python -m venv is checked below; what it cannot
    # catch is a creation interrupted before it returns, which the next
    # run finds half done.
    if not est_fichier(interpreteur):
        journal("Creating the virtual environment: %s" % racine)
        creation = [sys.executable, "-m", "venv", str(racine)]
    elif venv_incomplet(venv):
        # --clear empties the directory before building it again: only a
        # directory carrying pyvenv.cfg gets here.
        journal("Virtual environment incomplete, pip does not answer: "
                "rebuilding it: %s" % racine)
        creation = [sys.executable, "-m", "venv", "--clear", str(racine)]
    else:
        journal("Virtual environment already present: %s" % racine)
        creation = []

    if creation:
        try:
            racine.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(creation, check=True)
        except OSError as err:
            raise SystemExit("Cannot create %s: %s" % (racine, err)) \
                from err
        except subprocess.CalledProcessError as err:
            # The text displayed on Debian is the original one; on macOS
            # there is no python3-venv package to suggest.
            raise SystemExit(
                "Failed to create the virtual environment. %s (%s)"
                % ("Does the installed Python provide the venv module?"
                   if EST_MACOS else
                   "Is the python3-venv package installed?",
                   CMD_PAQUET_VENV)
            ) from err

    journal("Installing python-chess in the virtual environment.")
    try:
        subprocess.run([str(interpreteur), "-m", "pip", "install",
                        "--quiet", "--upgrade", "pip"], check=True)
        subprocess.run([str(interpreteur), "-m", "pip", "install",
                        "--quiet", "--upgrade", "chess"], check=True)
    except (subprocess.CalledProcessError, OSError) as err:
        raise SystemExit("Failed to install python-chess in %s: %s"
                         % (racine, err)) from err

    if not venv_operationnel(venv):
        raise SystemExit("The environment %s still does not provide the chess "
                         "module after installation." % venv)
    journal("Virtual environment ready: %s" % interpreteur)


def relancer_dans_venv(venv: str, argv: list[str]) -> None:
    """
    Restarts with the interpreter of the virtual environment.

    This function never returns on success: the current process is
    replaced. If the environment is missing or incomplete, it stops the
    program with the instructions to follow.
    """
    interpreteur = python_du_venv(venv)
    script = os.path.abspath(__file__)

    if os.environ.get(MARQUEUR_RELANCE) == "1":
        raise SystemExit(
            "The environment %s does not provide the chess module.\n"
            "Repair it with: %s --install-venv --venv %s"
            % (venv, script, venv))

    if est_fichier(interpreteur):
        journal("Virtual environment: restarting with %s" % interpreteur)
        os.environ[MARQUEUR_RELANCE] = "1"
        try:
            os.execv(str(interpreteur), [str(interpreteur), script] + argv)
        except OSError as err:
            raise SystemExit("Cannot restart with %s: %s"
                             % (interpreteur, err)) from err

    supplement = "" if venv == VENV_DEFAUT else " --venv %s" % venv
    raise SystemExit(
        "The python-chess module cannot be found and the virtual environment "
        "%s does not exist.\n\n"
        "Create it with one command:\n"
        "    %s\n"
        "    %s --install-venv%s\n"
        % (venv, CMD_PAQUET_VENV, script, supplement))


# ===========================================================================
# Constants
# ===========================================================================

#: Explorer host. The old name explorer.lichess.ovh no longer answers.
EXPLORER_URL = "https://explorer.lichess.org/masters"

#: Database of all Lichess players, rated games only. Same host and same
#: token requirement as the masters database. This is the database shown
#: on the page https://lichess.org/opening.
EXPLORER_LICHESS_URL = "https://explorer.lichess.org/lichess"

#: Databases that --database can query: endpoint, and label repeated in the
#: summary and the prompt, where it reads "the masters database".
BASES_EXPLORATEUR = {
    "masters": {"url": EXPLORER_URL, "libelle": "masters"},
    "lichess": {"url": EXPLORER_LICHESS_URL,
                "libelle": "Lichess (all players)"},
}

#: Speeds accepted by the /lichess endpoint, Speed schema of the API.
CADENCES_LICHESS = ("ultraBullet", "bullet", "blitz", "rapid", "classical",
                    "correspondence")

#: Rating bands accepted by the /lichess endpoint. Each one runs from its
#: value up to the next: 0 covers 0 to 999 (band shown as "400" on the
#: site), 2500 covers everything above. The server files each game under
#: the average rating of its two players.
CLASSEMENTS_LICHESS = ("0", "1000", "1200", "1400", "1600", "1800", "2000",
                       "2200", "2500")

#: Default filters of the Lichess database, taken from the default
#: configuration of https://lichess.org/opening (OpeningConfig.default
#: and OpeningQuery.firstMonth in the lila source): all speeds except
#: UltraBullet, all bands except the lowest, and only the games played
#: since January 2017. You thus get the same percentages as on that page.
CADENCES_DEFAUT = "bullet,blitz,rapid,classical,correspondence"
CLASSEMENTS_DEFAUT = "1000,1200,1400,1600,1800,2000,2200,2500"
DEPUIS_LICHESS = "2017-01"

#: Catalog of the named openings of Lichess, in the public domain (CC0).
#: These are the five files that the explorer server also loads to name
#: the positions.
CATALOGUE_SOURCE = ("https://raw.githubusercontent.com/lichess-org/"
                    "chess-openings/master/{part}.tsv")
CATALOGUE_PARTIES = ("a", "b", "c", "d", "e")

#: Default directory of the local catalog, and name of its index.
CATALOGUE_DEFAUT = DONNEES
CATALOGUE_INDEX = "catalog.tsv"

#: Version of the index format, checked on loading.
CATALOGUE_FORMAT = "2"

#: Move number in a catalog line, "1." or "12." for example.
RE_NUMERO_COUP = re.compile(r"\d+\.+")

#: User settings file, settings.ini at the root of the application
#: folder, at the same place on Debian and on macOS. It holds what
#: depends on the person and not on the game: their usernames, their
#: usual time control and their rating. Nothing personal therefore
#: appears in this script, which anyone can reuse as it is. It stays out
#: of local/, which only holds what the script can rebuild: emptying
#: local/ keeps the answers, and the file stays in sight, to be edited
#: by hand.
#:
#: --settings takes a name, never a path: every settings file, this one
#: or joueur1.ini for a second player, lives at the root of the
#: application folder, and deleting the folder leaves nothing behind
#: (see verifier_nom_reglages and chemin_reglages).
REGLAGES_DEFAUT = "settings.ini"

#: Name accepted by --settings: a file name ending in .ini, without a
#: folder, without a leading dot and without a control character.
RE_NOM_REGLAGES = re.compile(r"[^\x00-\x1f\x7f./\\][^\x00-\x1f\x7f/\\]*\.ini")

#: Section of the settings file that describes the player.
REGLAGES_SECTION = "player"

#: Section that described the player before version 5.0.0, at the time
#: of the French names. A file that still carries it is a settings file
#: of IAnalyze: it may be written again, the old section being copied
#: after [player] like any section unknown to the script.
REGLAGES_SECTION_ANCIENNE = "joueur"

#: Known keys of this section, with the comment lines written above each
#: one in the file. The usernames are looked up, ignoring case, in the
#: White and Black tags to deduce the player's side; the first one is
#: used to fill in an empty tag.
REGLAGES_CLEFS = (
    ("usernames",
     ("Your player names, separated by commas. They are looked up,",
      "ignoring case, in the White and Black tags to deduce your",
      "side. The --usernames option replaces them for one run.")),
    ("time_control",
     ("Your usual time control, suggested when the TimeControl tag of",
      "a game does not give it. Accepted forms:",
      "  15+10                real time, minutes then increment in",
      "                       seconds",
      "  14 days              correspondence, fixed delay per move",
      "  10 moves in 50 days  correspondence, moves per period",
      "  5 days + 36 hours    correspondence, starting clock then",
      "                       increment per move, in hours or in",
      "                       days; add if need be \", maximum 20",
      "                       days\" and \", bank 50 days\"",
      "  unknown")),
    ("rating",
     ("Your rating, in approximate Elo points, or unknown. It is",
      "passed on to the analyst, who adapts the explanations to it.",
      "Without it, the Elo of your tag in the game is used.")),
)

#: Bounds of a rating expressed in Elo points.
NIVEAU_MIN, NIVEAU_MAX = 100, 3500

#: Template of the analysis prompt, looked up next to the script, and
#: suffix of the prompt written next to the archive.
PROMPT_MODELE = "prompt-template.txt"
PROMPT_SUFFIXE = ".prompt.txt"

#: Template of the short prompt of --prompt-only: a few instructions, the
#: game and the engine evaluations, to be pasted alone, without an
#: attachment.
PROMPT_SEUL_MODELE = "prompt-only-template.txt"

#: Value through which a template places the game. With --prompt-only, a
#: template that did not place it would give nothing to analyze.
PROMPT_DONNEES = "{{GAME_PGN}}"

#: Markers of the template. A line starting with PROMPT_DIRECTIVE is a
#: directive, never copied; a value is written between double braces.
PROMPT_DIRECTIVE = "#!"
RE_VALEUR_MODELE = re.compile(r"\{\{([A-Za-z_]+)\}\}")

#: Conditions known to an "if" directive, and replaceable values. A name
#: missing from these lists stops the script before the collection.
PROMPT_CONDITIONS = ("STOCKFISH", "EXPLORER", "LICHESS_DATABASE",
                     "MASTERS_DATABASE", "ANSWERS",
                     "SIDE_KNOWN", "USERNAME_KNOWN", "RATING_DECLARED",
                     "RESULT_CONTRADICTED", "INSTRUCTIONS_GIVEN",
                     "OPENING_KNOWN", "PARTIAL_COVERAGE", "NULL_MOVE",
                     "FEW_WEAK_MOVES", "NO_WEAK_MOVE")
PROMPT_VALEURS = ("VERSION", "REPOSITORY", "ARCHIVE", "USERNAMES", "SIDE",
                  "RATING", "TIME_CONTROL", "ANNOTATOR", "DATABASE",
                  "INACCURACY_THRESHOLD", "MISTAKE_THRESHOLD",
                  "BLUNDER_THRESHOLD", "DEPTH", "MULTIPV",
                  "GAME_PGN", "ENGINE_TABLE", "RESULT_ALERT",
                  "PLAYER_INSTRUCTIONS", "OPENING", "PLIES",
                  "PLIES_EVALUATED", "PLAYER_WEAK_MOVES", "FENCE")

#: Number of errors that the short prompt asks for in its review. When
#: the engine table marks fewer of them for the player, the prompt gives
#: their real number: an LLM asked for three makes one up.
ERREURS_DU_BILAN = 3

#: Value of the Annotator tag when the settings do not give one: the
#: script does not know which model will write the analysis.
ANNOTATEUR_DEFAUT = ("your model name, followed by its publisher in "
                     "parentheses")

#: Label of an unknown time control, when neither the TimeControl tag
#: nor the settings give it.
CADENCE_DEFAUT = "unspecified"

#: Lichess time control categories, from the slowest to the fastest, each
#: with the estimated duration, in seconds, from which it applies. The
#: estimated duration of a game is the initial time plus COUPS_ESTIMES
#: times the increment. Bounds and formula taken from the Lichess source
#: (scalachess: Speed.scala and Clock.scala). Beyond six hours, Lichess
#: speaks of correspondence; a time control entered as real time stays
#: "classical" here.
CATEGORIES_CADENCE = ((1500, "classical"), (480, "rapid"), (180, "blitz"),
                      (30, "bullet"), (0, "ultrabullet"))
COUPS_ESTIMES = 40

#: Time control forms accepted in the settings file: "15+10", minutes per
#: player then increment in seconds, the Lichess way, and "14 days" for
#: correspondence. The other values of CADENCES_INCONNUES denote an
#: unknown time control.
RE_CADENCE_REELLE = re.compile(r"([0-9]{1,5})\s*\+\s*([0-9]{1,5})")
RE_CADENCE_JOURS = re.compile(r"([0-9]{1,4})\s*(?:d|day|days)")

#: Correspondence by period: "10 moves in 50 days". This is the
#: so-called standard ICCF time control, the time saved over a period
#: being carried over to the next one.
RE_CADENCE_PERIODE = re.compile(
    r"([0-9]{1,3})\s*moves?\s*in\s*([0-9]{1,4})\s*(?:d|day|days)")

#: Correspondence with a clock: "5 days + 36 hours", followed if need be
#: by ", maximum 20 days" and by ", bank 50 days". A clock is given at
#: the start, an increment is added to it at each move, a maximum may cap
#: it, and a bank may exist beside it, which the player draws from at
#: will. chess-mail.com is its simple form (5 days, 36 hours per move,
#: maximum of 20 days), the ICCF Triple Block its full form (50 days, an
#: increment in days, maximum of 50 days, bank of 50 or 75 days). The
#: increment carries its unit, hours or days: a day and a half cannot be
#: written in whole days.
RE_CADENCE_CAPITAL = re.compile(
    r"([0-9]{1,4})\s*(?:d|day|days)\s*\+\s*([0-9]{1,4})\s*"
    r"(h|hour|hours|d|day|days)"
    r"(?:\s*,?\s*maximum\s*([0-9]{1,4})\s*(?:d|day|days))?"
    r"(?:\s*,?\s*bank\s*([0-9]{1,4})\s*(?:d|day|days))?")

#: Increment entered with its unit: "36h" or "3d".
RE_INCREMENT = re.compile(r"([0-9]{1,4})\s*(h|hour|hours|d|day|days)")
CADENCES_INCONNUES = ("", "?", "unknown", "unspecified")

#: TimeControl tag of the PGN standard, in its two most common forms:
#: "600+5", seconds then increment, and "300", time only.
RE_TIMECONTROL = re.compile(r"([0-9]{1,6})(?:\+([0-9]{1,5}))?")

#: Unknown time control, fallback value.
CADENCE_INCONNUE = {"type": "inconnue"}

#: Startup questions, with the default that an empty answer keeps: label
#: in context.md, question, default.
QUESTIONS_CONTEXTE = (
    ("a. Scope",
     "Scope: the first N moves, or the whole game?",
     "the whole game"),
    ("b. What the player wants to understand",
     "What do you want to understand in this game?",
     "left open"),
    ("c. Particular context",
     ("Particular context: time trouble, fatigue, unknown opening, "
      "particular opponent?"),
     "nothing"),
    ("d. Other comments to include in the final PGN",
     "Other comments to include in the final PGN?",
     "nothing"),
)

#: Category of a move according to its loss against the engine's first
#: choice, in centipawns from the point of view of the side to move. 100
#: is the threshold of the mandatory comment in the project instructions.
SEUIL_IMPRECISION = 50
SEUIL_ERREUR = 100
SEUIL_GAFFE = 300

#: Loss, in centipawns, from which it no longer measures anything: one of
#: the two scores is a mate, which valeur_pour_trait brings down to a
#: bounded value close to 100000 so that the moves can be ranked. This
#: number is a computing convention, not an engine evaluation: it is not
#: displayed.
SEUIL_ECART_MAT = 10000

#: Value from which a bounded evaluation is that of a mate:
#: valeur_pour_trait turns a mate in n moves into 100000 - n.
SEUIL_MAT = 90000

#: Maximum number of mistakes and blunders listed, per side, in the
#: ranking.
PALMARES_MAX = 5

#: Marker of the entry into the endgame: material other than pawns and
#: kings of both sides together, at most SEUIL_FINALE with the values of
#: VALEUR_PIECES. The letters are those of the FEN, in lowercase.
SEUIL_FINALE = 26
VALEUR_PIECES = {"n": 3, "b": 3, "r": 5, "q": 9}

#: Public PGN export, requires no authentication.
EXPORT_URL = "https://lichess.org/game/export/{id}"

#: Default engine: the binary found in the PATH, on Debian as on macOS,
#: so that an engine built by hand, in /usr/local/bin for example, is
#: found the same way on both. Failing that, the location of the
#: package: /usr/games on Debian, which the PATH of root does not hold
#: (/etc/profile of the base-files package gives /usr/games to the
#: other accounts only), and that of Homebrew for Apple Silicon on macOS.
STOCKFISH_DEFAUT = (shutil.which("stockfish")
                    or ("/opt/homebrew/bin/stockfish" if EST_MACOS
                        else "/usr/games/stockfish"))

#: Hint for installing the engine, repeated in the error message.
AIDE_STOCKFISH = (CMD_PAQUET_STOCKFISH if EST_MACOS
                  else CMD_PAQUET_STOCKFISH + ", in /usr/games")

#: File holding the personal token, in mode 600, and nothing else.
JETON_DEFAUT = "~/.lichess_token"

#: Identifier as it is typed: 8 characters for the game, 12 for the view
#: of one player. Requiring the exact length avoids taking a missing file
#: name, "inexistant.pgn" for example, for the identifier "inexista", and
#: sending it to Lichess.
RE_ID_SOURCE = re.compile(r"[A-Za-z0-9]{8}(?:[A-Za-z0-9]{4})?")

#: Version of the script, following semantic versioning. It is repeated
#: in the user agent header: this is the only place to change.
VERSION = "4.0.2"

#: Address of the project repository, quoted at the top of the analysis
#: prompt so that the analyst, or anyone the prompt is passed on to,
#: knows where the prompt and the archive come from.
DEPOT = "https://github.com/deuza/IAnalyze"

#: User agent header, out of courtesy towards the API.
UA = "IAnalyze/%s (+%s)" % (VERSION, DEPOT)


# ===========================================================================
# General utilities
# ===========================================================================

#: Control characters removed from a text before display: C0 set except
#: tab and line feed, DEL, then C1 set. An escape sequence coming from a
#: PGN or from a file name must never reach your terminal.
RE_CONTROLES = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


#: Separators that a value fitting on one line must not contain: tabs,
#: line ends, Unicode line and paragraph separators. They become a
#: space.
RE_BLANCS_VALEUR = re.compile(r"[\t\n\x0b\x0c\r\x85\u2028\u2029]")

#: Lone surrogates, traces of bytes that the expected encoding could not
#: decode (file name, keyboard input).
RE_SUBSTITUTS = re.compile(r"[\ud800-\udfff]")


def nettoyer_valeur(texte: str) -> str:
    """
    Cleans a short value before writing or displaying it: player name,
    Event or Site tag, answer to a question.

    Separators become a space, lone surrogates U+FFFD, and the other
    control characters as well as the byte order mark are removed. A sound
    value comes out unchanged.
    """
    texte = RE_BLANCS_VALEUR.sub(" ", texte)
    texte = RE_SUBSTITUTS.sub("\ufffd", texte)
    return RE_CONTROLES.sub("", texte).replace("\ufeff", "")


def configurer_console() -> None:
    """
    Makes standard output and standard error tolerant of the encoding.

    A character that the terminal encoding cannot represent is replaced
    by "?" instead of raising UnicodeEncodeError: this is the case of the
    accents of the messages with PYTHONIOENCODING=ascii, or under a C
    locale when the UTF-8 mode of Python is disabled (PYTHONUTF8=0). The
    encoding itself is not changed, only the error handling is.

    Standard input switches to "surrogateescape": a byte that the terminal
    encoding cannot decode, an "é" typed in latin-1 on a UTF-8 console for
    example, is set aside instead of raising UnicodeDecodeError, and
    demander() decodes it again afterwards.
    """
    reconfigurer = getattr(sys.stdin, "reconfigure", None)
    if reconfigurer is not None:
        with contextlib.suppress(ValueError, OSError):
            reconfigurer(errors="surrogateescape")
    for flux in (sys.stdout, sys.stderr):
        # A closed stream (None) or one replaced by an object without
        # reconfigure() is left as it is: a degraded display is better than a
        # failure before even starting.
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is None:
            continue
        with contextlib.suppress(ValueError, OSError):
            reconfigurer(errors="replace")


def journal(message: str) -> None:
    """
    Writes a timestamped progress line on standard error.

    The control characters of the message are removed on the way.
    """
    message = RE_CONTROLES.sub("", message)
    heure = datetime.datetime.now().strftime("%H:%M:%S")
    sys.stderr.write("[%s] %s\n" % (heure, message))
    sys.stderr.flush()


def expurger(texte: str, jeton: str | None) -> str:
    """
    Removes every occurrence of the token from a string before display.

    No message and no exception is supposed to contain the token, but you
    want to take no risk with a traceback that may end up in a bug report.
    """
    if jeton:
        texte = texte.replace(jeton, "<TOKEN-REDACTED>")
    return texte


#: Largest search depth accepted. Beyond it, a single position would keep
#: the engine busy for hours, without adding anything to the analysis of
#: a game: a typo, "180" for "18", must not lock up the machine.
PROFONDEUR_MAX = 60

#: Largest game count held as plausible in an answer of the explorer.
#: The Lichess database counts a few billion games.
COMPTE_MAX = 10 ** 15


def entier(valeur) -> int:
    """
    Cautiously converts a value from an external JSON into an integer.

    A missing, null or unexpectedly typed value counts as zero: a missing
    figure is better than a stop over a detail of the schema. The same
    goes for an infinite number: json.loads reads "1e999" as infinity,
    which int() rejects with an OverflowError.
    """
    try:
        nombre = int(valeur)
    except (TypeError, ValueError, OverflowError):
        return 0
    # A game count is positive, and no database holds more than a few
    # billion games. Outside these bounds the value is held as missing:
    # negative, it would give a frequency of -5 %; huge, it would make the
    # division that follows fail.
    return nombre if 0 <= nombre <= COMPTE_MAX else 0


#: Byte order marks recognized at the start of a file. Those of UTF-32
#: come first: the little-endian UTF-32 mark starts with the
#: little-endian UTF-16 one.
BOMS_LARGES = (
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
)

#: Bytes examined to recognize UTF-16 or UTF-32 without a byte order
#: mark.
ECHANTILLON_UTF16 = 4096

#: Invalid bytes tolerated, per correctly encoded non-ASCII character,
#: for a text to still be held as damaged UTF-8.
UTF8_TOLERANCE = 4

#: Remark of decoder_octets when a UTF-16 or UTF-32 text holds bytes
#: that form no character, %s being the codec. The reading of the PGN
#: looks for it: in these encodings, a single byte lost shifts the whole
#: text that follows.
REMARQUE_SEQUENCES = "invalid %s sequences replaced by U+FFFD"


def utf16_sans_bom(brut: bytes) -> str | None:
    """
    Recognizes a UTF-16 text that has no byte order mark.

    A mostly ASCII text encoded in UTF-16 carries a null byte in every
    other position: at odd positions in little-endian, at even positions
    in big-endian. Returns the name of the codec, or None if the pattern
    does not appear.
    """
    echantillon = brut[:ECHANTILLON_UTF16]
    pairs, impairs = echantillon[0::2], echantillon[1::2]
    if len(impairs) < 2:
        return None
    nuls_pairs, nuls_impairs = pairs.count(0), impairs.count(0)
    if nuls_impairs > 0.4 * len(impairs) and nuls_pairs < 0.05 * len(pairs):
        return "utf-16-le"
    if nuls_pairs > 0.4 * len(pairs) and nuls_impairs < 0.05 * len(impairs):
        return "utf-16-be"
    return None


def utf32_sans_bom(brut: bytes) -> str | None:
    """
    Recognizes a UTF-32 text that has no byte order mark.

    Each character takes four bytes, and the two high ones are null for
    any character up to U+FFFF: at positions 2 and 3 of each group in
    little-endian, at positions 0 and 1 in big-endian, while the low byte
    is almost never null. Without this test, such a text passed for
    cp1252 once its null bytes were removed, losing every character
    beyond latin-1. Returns the name of the codec, or None.
    """
    echantillon = brut[:ECHANTILLON_UTF16]
    groupes = len(echantillon) // 4
    if groupes < 2:
        return None
    nuls = [echantillon[k:4 * groupes:4].count(0) / groupes
            for k in range(4)]
    if nuls[2] > 0.9 and nuls[3] > 0.9 and nuls[0] < 0.05:
        return "utf-32-le"
    if nuls[0] > 0.9 and nuls[1] > 0.9 and nuls[3] < 0.05:
        return "utf-32-be"
    return None


def decoder_octets(brut: bytes) -> tuple[str, str, list[str]]:
    """
    Decodes the content of a text file without ever raising an exception.

    Order of the attempts: byte order mark (UTF-8, UTF-16, UTF-32), UTF-16
    without a mark, strict UTF-8, then fallback on cp1252 and finally on
    latin-1, which accepts any byte. A text plainly in UTF-8 but damaged
    by a few invalid bytes stays decoded as UTF-8, those bytes becoming
    U+FFFD: switching it to cp1252 would damage all its accents to save a
    few of them. The criterion: at least one correctly encoded non-ASCII
    character, and at most UTF8_TOLERANCE invalid bytes for each of them.
    A latin-1 text does not meet it, its accented letters being almost all
    invalid in UTF-8.

    CRLF and CR line ends are turned into LF, and the control characters
    are removed, NUL included; vertical tab and form feed become a space.

    Returns the text, the name of the encoding chosen and the list of the
    remarks to report, empty for a UTF-8 file without a flaw.
    """
    remarques: list[str] = []
    texte: str | None = None
    encodage = "utf-8"

    if brut.startswith(codecs.BOM_UTF8):
        # The mark is removed, the rest follows the normal path: it does not
        # guarantee that what follows is valid UTF-8.
        brut = brut[len(codecs.BOM_UTF8):]
        remarques.append("UTF-8 byte order mark (BOM) removed")
    else:
        large = None
        for marque, codec in BOMS_LARGES:
            if brut.startswith(marque):
                brut = brut[len(marque):]
                large = codec
                remarques.append("byte order mark (BOM) detected, encoding "
                                 "used: %s" % codec)
                break
        if large is None:
            large = utf32_sans_bom(brut)
            if large is not None:
                remarques.append("three null bytes out of four and no byte "
                                 "order mark, encoding used: %s"
                                 % large)
        if large is None:
            large = utf16_sans_bom(brut)
            if large is not None:
                remarques.append("one null byte out of two and no byte "
                                 "order mark, encoding used: %s"
                                 % large)
        if large is not None:
            encodage = large
            try:
                texte = brut.decode(large)
            except UnicodeDecodeError:
                texte = brut.decode(large, errors="replace")
                remarques.append(REMARQUE_SEQUENCES % large)

    if texte is None:
        try:
            texte = brut.decode("utf-8")
        except UnicodeDecodeError:
            essai = brut.decode("utf-8", errors="replace")
            invalides = essai.count("\ufffd")
            valides = sum(1 for c in essai if ord(c) > 127) - invalides
            if valides > 0 and invalides <= UTF8_TOLERANCE * valides:
                texte = essai
                remarques.append("damaged UTF-8, %d invalid byte(s) "
                                 "replaced by U+FFFD, encoding used: "
                                 "utf-8" % invalides)
            else:
                try:
                    texte = brut.decode("cp1252")
                    encodage = "cp1252"
                except UnicodeDecodeError:
                    texte = brut.decode("latin-1")
                    encodage = "latin-1"
                remarques.append("the content is not UTF-8, encoding used: "
                                 "%s" % encodage)

    texte = texte.replace("\r\n", "\n").replace("\r", "\n")
    controles = RE_CONTROLES.findall(texte)
    if controles:
        texte = RE_CONTROLES.sub(
            lambda m: " " if m.group() in "\x0b\x0c" else "", texte)
        remarques.append("%d control character(s) removed, %d of them NUL"
                         % (len(controles), controles.count("\x00")))
    return texte, encodage, remarques


def lire_fichier_texte(chemin: pathlib.Path,
                       role: str) -> tuple[str, str, list[str]]:
    """
    Reads a text file whatever its encoding, and reports what departs from
    UTF-8 with a "Warning" line in the log.

    Returns the text, the encoding chosen and the remarks, like
    decoder_octets. Only an error accessing the file stops the script.
    """
    try:
        brut = chemin.read_bytes()
    except OSError as err:
        raise SystemExit("Cannot read (%s): %s" % (role, err)) from err
    texte, encodage, remarques = decoder_octets(brut)
    for remarque in remarques:
        journal("Warning, %s: %s." % (role, remarque))
    return texte, encodage, remarques


def lire_texte(chemin: pathlib.Path, role: str) -> str:
    """
    Reads a text file, with a clear message on failure.

    The encoding is detected by lire_fichier_texte; this short form is
    used when only the text matters, for the instructions for example.
    """
    return lire_fichier_texte(chemin, role)[0]


def ecrire_texte(chemin: pathlib.Path, texte: str) -> None:
    """
    Writes a text file in UTF-8, whatever the locale.

    A character that cannot be encoded in UTF-8, a lone surrogate coming
    from a badly encoded file name or input for example, is replaced by
    "?" instead of raising UnicodeEncodeError in the middle of the
    collection. Line ends stay LF on every platform. Access errors
    (OSError) go up to the caller.

    The writing goes through a neighboring file, ".<name>.partial", renamed
    once complete: an interruption (Ctrl-C) or an error along the way
    never leaves a truncated file under its final name. The file that
    already existed, if there was one, then stays intact, and the partial
    file is removed.
    """
    partiel = chemin.with_name(".%s.partial" % chemin.name)
    try:
        with partiel.open("w", encoding="utf-8", errors="replace",
                          newline="\n") as f:
            f.write(texte)
        partiel.replace(chemin)
    except BaseException:
        # BaseException and not Exception: KeyboardInterrupt must also trigger
        # the cleanup, before going up unchanged.
        with contextlib.suppress(OSError):
            partiel.unlink()
        raise


#: Characters dropped from a folder name, hence from the names stored in
#: the zip: control characters, path separators, characters forbidden by
#: Windows, lone surrogates and U+FFFD. Spaces and accented letters are
#: kept.
RE_NOM_RISQUE = re.compile(
    r'[\x00-\x1f\x7f-\x9f/\\:*?"<>|\ud800-\udfff\ufffd]')

#: Maximum length, in bytes, of the label repeated in the folder name.
ETIQUETTE_MAX = 80


def masquer_maison(valeur: str) -> str:
    """
    Writes a path under the home folder with "~", as the shell does: the
    name of that folder, the login of the user most often, does not go to
    the LLM with the archive. Any other value is returned as it is. A home
    folder reduced to "/" is not masked, every path would start with it.
    """
    maison = os.path.expanduser("~").rstrip(os.sep)
    if maison and (valeur == maison or valeur.startswith(maison + os.sep)):
        return "~" + valeur[len(maison):]
    return valeur


def etiquette_sure(nom: str) -> str:
    """
    Derives from a file name a safe label for the working folder and for
    the paths of the archive.

    Each risky character becomes "_", each run of spaces a hyphen: an
    archive name without spaces needs no quotes in a command line. Dots
    and hyphens at the edges are removed, and an empty label becomes
    "game".

    The length is bounded in bytes, not in characters: the file system
    counts in bytes, and eighty ideograms make two hundred and forty of
    them. Bounded in characters, the label let through names that the
    archive, once the timestamp was added, could no longer carry.
    """
    sure = RE_NOM_RISQUE.sub("_", re.sub(r"\s+", "-", nom.strip()))
    octets = sure.encode("utf-8", errors="surrogateescape")[:ETIQUETTE_MAX]
    # A cut in the middle of a character leaves orphan bytes: they are
    # dropped at decoding.
    sure = octets.decode("utf-8", errors="ignore").strip("-.")
    return sure or "game"


def annoncer_archive(archive: pathlib.Path) -> None:
    """
    Writes the path of the archive, alone, on standard output.

    The path is written in bytes, as the file system knows it:
    ARCHIVE=$(...) thus receives a usable path even if the terminal cannot
    display all its characters. Without access to the bytes of the output,
    the original text writing is kept.
    """
    tampon = getattr(sys.stdout, "buffer", None)
    if tampon is None:
        sys.stdout.write("%s\n" % archive)
        return
    sys.stdout.flush()
    tampon.write(os.fsencode(str(archive)) + b"\n")
    tampon.flush()


def lire_jeton(chemin: str) -> str:
    """
    Reads the personal token from a file that holds only the token.

    The file is not a shell script, it holds no variable assignment: it is
    read directly, not sourced. Its permissions are checked on the way.
    """
    p = pathlib.Path(os.path.expanduser(chemin))
    if not est_fichier(p):
        raise SystemExit("Token missing: %s not found." % p)

    try:
        mode = p.stat().st_mode
        brut = p.read_bytes()
    except (OSError, UnicodeDecodeError) as err:
        raise SystemExit("Cannot read the token in %s: %s" % (p, err)) from err

    # Same decoding as for the PGN: a file saved by a Windows editor, with a
    # byte order mark or in UTF-16, stays readable. The remarks never quote
    # the content of the file.
    contenu, _encodage, remarques = decoder_octets(brut)
    for remarque in remarques:
        journal("Warning, token (%s): %s." % (p, remarque))

    if mode & 0o077:
        journal("Warning: %s is readable by others (mode %o)."
                % (p, mode & 0o777))

    jeton = contenu.strip()
    # An assignment, LICHESS_TOKEN=lip_..., or quotes around the token fit in
    # a single word: without this check, they got through, and Lichess
    # answered 401 without anything pointing to the file.
    if (not jeton or any(c.isspace() for c in jeton)
            or any(c in jeton for c in "=\"'")):
        raise SystemExit("The file %s must contain the token alone, without "
                         "spaces or variable assignment." % p)
    # The token goes into an HTTP header: outside printable ASCII, it would
    # be rejected by http.client with an encoding error that nothing links
    # to the file. The message does not reproduce the token.
    if not jeton.isascii() or not jeton.isprintable():
        raise SystemExit("The token read in %s contains characters outside "
                         "printable ASCII: copy it again from Lichess, with "
                         "nothing else in the file." % p)
    return jeton


#: Hosts from which a game URL is accepted.
HOTES_LICHESS = ("lichess.org", "www.lichess.org")

#: Sections of the site whose name has eight letters: they look like a
#: game identifier without being one. https://lichess.org/analysis was
#: taken for the game "analysis" and requested from Lichess. The last
#: four come from the routes of the site (conf/routes of the lila
#: repository, read in November 2026), which list no other first segment
#: of eight or twelve letters.
RUBRIQUES_LICHESS = ("analysis", "training", "practice", "streamer",
                     "features", "insights", "learning", "username",
                     "patron", "calendar", "storm", "racer", "coach",
                     "broadcast", "tournament", "simul", "swiss", "team",
                     "forum", "player", "games", "editor", "variant",
                     "paste", "contact", "mobile", "about", "account",
                     "timeline", "bookmark", "password", "markdown")

#: Path prefixes accepted before the identifier, besides the direct form
#: /<identifier>: the embedded game and the PGN export.
PREFIXES_PARTIE = (("embed", "game"), ("embed",), ("game", "export"))


def extraire_id(source: str) -> str | None:
    """
    Extracts the game identifier from a URL or from a raw string.

    Accepts https://lichess.org/<identifier>, the same address followed by
    /black, the identifier alone, as well as the twelve-character move
    identifiers, of which only the first eight are kept. The identifier,
    alone or in the URL, must be exactly 8 or 12 alphanumeric characters.

    A URL must point to lichess.org and carry the identifier at the start
    of the path, or after /embed/game/, /embed/ or /game/export/. Any other
    host, any other page of the site (study, analysis, puzzles) and the
    sections of RUBRIQUES_LICHESS give None: nothing is then requested
    from Lichess.
    """
    source = source.strip()
    if source.lower().startswith(("http://", "https://")):
        try:
            url = urllib.parse.urlparse(source)
            hote = (url.hostname or "").lower()
        except ValueError:
            # Misplaced brackets, for example: urlparse sees an invalid IPv6
            # address in them. This is not a Lichess game.
            return None
        if hote not in HOTES_LICHESS:
            return None
        morceaux = [m for m in url.path.split("/") if m]
        for prefixe in PREFIXES_PARTIE:
            if tuple(morceaux[:len(prefixe)]) == prefixe:
                morceaux = morceaux[len(prefixe):]
                break
        # Only the first segment counts: the old loop kept the first
        # eight-character segment wherever it was, the identifier of a study
        # for example.
        if (morceaux and RE_ID_SOURCE.fullmatch(morceaux[0])
                and morceaux[0].lower() not in RUBRIQUES_LICHESS):
            return morceaux[0][:8]
        return None
    if (RE_ID_SOURCE.fullmatch(source)
            and source.lower() not in RUBRIQUES_LICHESS):
        return source[:8]
    return None


# ===========================================================================
# Fetching the PGN
# ===========================================================================

def telecharger_pgn(identifiant: str, delai: int) -> str:
    """Downloads the raw PGN. This endpoint answers 200 without a token."""
    url = EXPORT_URL.format(id=identifiant)
    requete = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/x-chess-pgn",
    })
    journal("Downloading the PGN: %s" % url)
    try:
        with urllib.request.urlopen(requete, timeout=delai) as reponse:
            # Same decoding as for a local file: Lichess answers in UTF-8, but
            # nothing must depend on this assumption.
            texte, _encodage, remarques = decoder_octets(reponse.read())
            for remarque in remarques:
                journal("Warning, downloaded PGN: %s." % remarque)
            return texte
    except urllib.error.HTTPError as err:
        raise SystemExit("PGN export: HTTP %d for the game %s."
                         % (err.code, identifiant)) from err
    except (OSError, http.client.HTTPException) as err:
        # URLError is a subclass of OSError: this block covers a failed DNS
        # resolution as well as a timeout or a dropped connection.
        raise SystemExit("PGN export unreachable: %s"
                         % getattr(err, "reason", err)) from err


#: What the body of a game may contain outside the comments: a result, a
#: move number, a NAG, a move in English notation or an annotation
#: symbol. The order matters: the result, then castling written with
#: zeros, come before the move number, which also starts with a digit.
RE_JETON_PGN = re.compile(
    r"(?:1-0|0-1|1/2-1/2|\*)(?![\w/-])"
    r"|(?:O-O-O|O-O|0-0-0|0-0|--|Z0|0000|@@@@"
    r"|[KQRBN]?[a-h]?[1-8]?[-x]?[a-h][1-8](?:=?[QRBNKqrbnk])?)"
    r"[+#]?[!?]{0,2}(?![\w=])"
    r"|\d+\.*"
    r"|\$\d+"
    r"|[!?]{1,2}")


#: A tag line as python-chess reads it: a single tag, alone on its line,
#: the bracket in the first column. python-chess skips a line of the
#: tags that does not match it, together with whatever it carries, and
#: reads as moves what the brackets of such a line hold among the moves.
RE_BALISE_PGN = re.compile(
    r"\[([A-Za-z0-9][A-Za-z0-9_+#=:-]*)\s+\"([^\r]*)\"\]\s*$")


def controler_lexique(texte_pgn: str) -> None:
    """
    Rejects a PGN whose body contains something other than moves.

    python-chess silently skips the characters it does not recognize. A
    move written in French notation, "Cf3", is then read as "f3", a pawn
    move: the game analyzed is no longer the one that was played, and
    nothing reports it. Likewise, a brace never closed swallows the whole
    rest of the game. This check therefore comes before the reading: it
    plays no move, it only checks that each word of the body has the form
    of a PGN word.

    Accepted outside the comments: the tags, the move numbers, the moves
    in English notation, the NAGs, the annotation symbols, the variation
    parentheses and the result. A tag is accepted where python-chess reads
    it: alone on its line, the bracket in the first column, before the
    moves of its game. Anywhere else, a line that starts with a bracket
    would be skipped or read as moves, without a word: it is refused.
    """
    i, n = 0, len(texte_pgn)
    profondeur = 0
    ligne = 1
    debut_de_ligne = True
    # True where python-chess reads the tags of a game: at the start of
    # the file, then after the blank line that ends a game. A move, a
    # comment or a parenthesis ends this zone.
    zone_balises = True
    # True once the current line holds something other than spaces.
    contenu = False
    while i < n:
        c = texte_pgn[i]
        colonne_un = i == 0 or texte_pgn[i - 1] == "\n"
        if c == "\n":
            # python-chess ends a game at a blank line: the tags of the next
            # game may follow it.
            if not contenu and profondeur == 0:
                zone_balises = True
            ligne += 1
            debut_de_ligne = True
            contenu = False
            i += 1
        elif c.isspace():
            i += 1
        elif c == "{":
            fin = texte_pgn.find("}", i)
            if fin < 0:
                raise SystemExit(
                    "Corrupt PGN: the comment opened by a brace on line %d is "
                    "never closed." % ligne)
            ligne += texte_pgn.count("\n", i, fin)
            i = fin + 1
            debut_de_ligne = False
            zone_balises = False
            contenu = True
        elif c == ";" or (c == "%" and colonne_un):
            # End-of-line comment, or escape line in the first column:
            # everything runs to the line feed.
            fin = texte_pgn.find("\n", i)
            i = n if fin < 0 else fin
            contenu = True
        elif c == "[" and debut_de_ligne:
            fin = texte_pgn.find("\n", i)
            fin = n if fin < 0 else fin
            if not zone_balises:
                raise SystemExit(
                    "Corrupt PGN: line %d starts with a bracket among the "
                    "moves. A tag goes before the moves of its game, and "
                    "python-chess would read as moves what the brackets "
                    "hold." % ligne)
            if not colonne_un or not RE_BALISE_PGN.match(texte_pgn, i, fin):
                raise SystemExit(
                    "Corrupt PGN: line %d is not a well-formed tag, "
                    "[Name \"value\"] alone on its line: python-chess would "
                    "skip it, together with what it carries." % ligne)
            i = fin
            contenu = True
        elif c == "(":
            profondeur += 1
            i += 1
            debut_de_ligne = False
            zone_balises = False
            contenu = True
        elif c == ")":
            if profondeur == 0:
                raise SystemExit(
                    "Corrupt PGN: closing parenthesis without an open "
                    "variation, line %d." % ligne)
            profondeur -= 1
            i += 1
            debut_de_ligne = False
            zone_balises = False
            contenu = True
        else:
            m = RE_JETON_PGN.match(texte_pgn, i)
            if m is None:
                mot = re.match(r"\S+", texte_pgn[i:i + 40])
                raise SystemExit(
                    "Corrupt PGN: \"%s\", line %d, is neither a move in "
                    "English notation (K, Q, R, B, N) nor another PGN "
                    "element. A game written in French notation or with "
                    "figurines must be converted, free text placed between "
                    "braces."
                    % (nettoyer_valeur(mot.group(0) if mot else c)[:20],
                       ligne))
            i = m.end()
            debut_de_ligne = False
            zone_balises = False
            contenu = True
    if profondeur:
        raise SystemExit("Corrupt PGN: %d variation(s) opened by a "
                         "parenthesis and never closed." % profondeur)


def resultat_orphelin(partie: chess.pgn.Game) -> bool:
    """
    True for a "game" that python-chess derives from a lone result: no
    move, no comment, no variation, and no tag filled in except Result.
    This is not a game, only the end marker of the previous one, written a
    second time.
    """
    if partie.variations or partie.comment.strip():
        return False
    return all(valeur in ("?", "????.??.??", "")
               for cle, valeur in partie.headers.items() if cle != "Result")


def charger_partie(texte_pgn: str) -> chess.pgn.Game:
    """
    Parses the PGN and returns the game it contains, which must be alone.

    The python-chess parser is tolerant: on an illegal move it stops
    without raising an exception and records the error in the game. Such a
    PGN is rejected rather than silently analyzing a truncated game.
    """
    controler_lexique(texte_pgn)
    flux = io.StringIO(texte_pgn)
    try:
        partie = chess.pgn.read_game(flux)
    except (IndexError, ValueError) as err:
        # Safety net: the lexical check rules out the known cases, but no input
        # must end in an unexpected error.
        raise SystemExit("Corrupt PGN: python-chess could not read it "
                         "(%s)." % type(err).__name__) from err
    if partie is None:
        raise SystemExit("Unreadable or empty PGN.")
    if partie.errors:
        raise SystemExit("Corrupt PGN, illegal or malformed move: %s"
                         % "; ".join(nettoyer_valeur(str(e))
                                     for e in partie.errors))
    if not list(partie.mainline_moves()):
        raise SystemExit("PGN without a single move in the main line.")
    # IAnalyze analyzes a whole game, from the first move to the last: the
    # explorer, the opening catalog and the instructions of the prompt all
    # assume the initial position. A game resumed from a position, given by
    # a FEN tag, is therefore rejected here, rather than half analyzed with
    # a prompt that does not fit it.
    if partie.board().fen() != chess.STARTING_FEN:
        raise SystemExit(
            "The game does not start from the initial position, it starts "
            "from a FEN tag. IAnalyze analyzes a whole game, from the first "
            "move to the last: to study a position, load it into an analysis "
            "board.")
    # python-chess reads a null move played in check, after a mate for
    # instance, without an error. Passing leaves the king attacked: the
    # positions that follow are illegal, and Stockfish dies on them
    # without saying why. The game is refused here, with the move.
    plateau = partie.board()
    for coup in partie.mainline_moves():
        if not coup and plateau.is_check():
            raise SystemExit(
                "Corrupt PGN: null move \"--\" played in check, at move %d, "
                "by %s. Passing leaves the king attacked: the positions that "
                "follow are illegal, and the engine cannot evaluate them."
                % (plateau.fullmove_number,
                   "White" if plateau.turn == chess.WHITE else "Black"))
        plateau.push(coup)

    # The values of the tags go into the headers of the summary and into
    # the log: tabs and control characters are removed from them right now,
    # once and for all. The list is frozen before the loop, as the tags are
    # modified along the way.
    for cle, valeur in list(partie.headers.items()):
        propre = nettoyer_valeur(valeur)
        if propre != valeur:
            partie.headers[cle] = propre

    variante = partie.headers.get("Variant", "Standard")
    if variante.lower() not in ("standard", "from position"):
        raise SystemExit("Variant not supported: %s. This script only handles "
                         "standard chess." % variante)

    # A single game per file. Analyzing the first one of a series would make
    # no sense: nothing says it is the one you wanted, and game.pgn,
    # copied into the archive, would carry them all.
    #
    # A result repeated at the end of the file is not a game. Some sites
    # write "0-1", a blank line, then "0-1" again: python-chess reads a
    # second game there, without a single tag or move. It is ignored, and
    # the log says so.
    autres = 0
    orphelins = 0
    try:
        while True:
            suivante = chess.pgn.read_game(flux)
            if suivante is None:
                break
            if resultat_orphelin(suivante):
                orphelins += 1
            else:
                autres += 1
    except (IndexError, ValueError):
        autres += 1
    if orphelins and not autres:
        journal("Result repeated at the end of the file, after the game: "
                "ignored.")
    if autres:
        raise SystemExit("The PGN contains %d games: put the one to analyze "
                         "in a separate file." % (autres + 1))
    return partie


# ===========================================================================
# Startup questions
#
# The questions go through standard error and standard input, never
# through standard output, which is reserved for the path of the
# archive: the form ARCHIVE=$(./ianalyze.py ...) keeps working,
# questions included. They are only asked on an interactive terminal.
# ===========================================================================

def questions_possibles(sans_questions: bool) -> bool:
    """
    True if questions can be asked: a terminal on both sides.

    A stream closed by the caller, "<&-" in a script, is None in Python:
    it is not a terminal, and no question is asked.
    """
    return (not sans_questions
            and sys.stdin is not None and sys.stderr is not None
            and sys.stdin.isatty() and sys.stderr.isatty())


#: Maximum length of an answer to a startup question. None of them needs
#: that much: beyond it, it is text pasted by mistake.
REPONSE_MAX = 255

#: Characters that a player name cannot contain: the name goes into a PGN tag,
#: where a quote or a bracket would close it too early, and where a brace
#: would open a comment in the eyes of a strict reader.
SIGNES_INTERDITS_NOM = '"\\[]{}'


def demander(question: str, defaut: str | None = None,
             nom: bool = False) -> str | None:
    """
    Asks a question and returns the cleaned answer.

    An empty answer gives the default, or an empty string without a
    default. The end of the stream (Ctrl-D) returns None: the caller then
    applies its defaults without insisting.

    An answer longer than REPONSE_MAX characters is rejected and the
    question asked again; so is, with `nom`, an answer carrying one of the
    characters of SIGNES_INTERDITS_NOM.
    """
    invite = (question if defaut is None
              else "%s (Enter: %s)" % (question, defaut))
    while True:
        sys.stderr.write(invite + " ")
        sys.stderr.flush()
        ligne = sys.stdin.readline()
        if not ligne:
            sys.stderr.write("\n")
            return None
        if RE_SUBSTITUTS.search(ligne):
            # Input that the terminal encoding could not decode: we
            # recover the typed bytes and apply to them the same fallback
            # as for a file, cp1252 then latin-1.
            ligne = decoder_octets(
                ligne.encode("utf-8", errors="surrogateescape"))[0]
        reponse = nettoyer_valeur(ligne).strip()
        if len(reponse) > REPONSE_MAX:
            sys.stderr.write("  Answer too long: %d characters at "
                             "most.\n" % REPONSE_MAX)
            continue
        if nom and any(c in SIGNES_INTERDITS_NOM for c in reponse):
            sys.stderr.write("  A name cannot contain a quote, a "
                             "backslash, a bracket or a brace.\n")
            continue
        return reponse or (defaut or "")


# ---------------------------------------------------------------------------
# Time control
#
# A time control is a small dictionary, in one of these five forms:
#
#     {"type": "reel", "initial": 900, "increment": 10}    in seconds
#     {"type": "correspondance", "jours": 14}              delay per move
#     {"type": "correspondance", "coups": 10,              moves per
#      "periode": 50}                                      period, in days
#     {"type": "correspondance", "capital": 5,             days at the start,
#      "increment": 36, "plafond": 20, "reserve": 0}       hours per move,
#                                                          maximum and bank
#                                                          in days, 0 if
#                                                          there is none
#     {"type": "inconnue"}
#
# Correspondence indeed has three systems:
#
#   - a fixed delay for each move, nothing being carried over from one
#     move to the next: Lichess, chess.com;
#   - a number of moves to play per period, the time saved being carried
#     over: standard ICCF time control, "10 moves in 50 days";
#   - a clock that grows by an increment at each move, with an optional
#     maximum and bank: chess-mail.com, and the ICCF Triple Block.
#
# The last two follow the ICCF Rules in force since 1 January 2026
# (section 2.4). The first one does not exist at the ICCF.
#
# It is never free text: the sentence that the analyst reads is written
# here, always in the same way, from checked numbers.
# ---------------------------------------------------------------------------

def analyser_cadence(texte: str) -> dict | None:
    """
    Reads a time control written in the settings file.

    Returns None if the text has none of the accepted forms, "0+0"
    included: a game with neither time nor increment does not exist.
    """
    texte = texte.strip().casefold()
    if texte in CADENCES_INCONNUES:
        return dict(CADENCE_INCONNUE)
    trouve = RE_CADENCE_REELLE.fullmatch(texte)
    if trouve:
        minutes, increment = int(trouve.group(1)), int(trouve.group(2))
        if minutes == 0 and increment == 0:
            return None
        return {"type": "reel", "initial": 60 * minutes,
                "increment": increment}
    trouve = RE_CADENCE_JOURS.fullmatch(texte)
    if trouve and int(trouve.group(1)) >= 1:
        return {"type": "correspondance", "jours": int(trouve.group(1))}
    trouve = RE_CADENCE_PERIODE.fullmatch(texte)
    if trouve and int(trouve.group(1)) >= 1 and int(trouve.group(2)) >= 1:
        return {"type": "correspondance", "coups": int(trouve.group(1)),
                "periode": int(trouve.group(2))}
    trouve = RE_CADENCE_CAPITAL.fullmatch(texte)
    if trouve:
        return cadence_a_capital(
            int(trouve.group(1)),
            heures_increment(int(trouve.group(2)), trouve.group(3)),
            int(trouve.group(4) or 0), int(trouve.group(5) or 0))
    return None


def heures_increment(nombre: int, unite: str) -> int:
    """Increment in hours, from a number and its unit, h or d."""
    return nombre * 24 if unite.startswith("d") else nombre


def duree_increment(heures: int) -> str:
    """ "36 hours", or "3 days" when the count falls exactly in days."""
    if heures and heures % 24 == 0:
        return pluriel(heures // 24, "day")
    return pluriel(heures, "hour")


def cadence_a_capital(capital: int, increment: int, plafond: int,
                      reserve: int = 0) -> dict | None:
    """
    Correspondence time control with a clock, or None if it is
    inconsistent: neither clock nor increment, or a maximum below the
    starting clock. `increment` is in hours, the other durations in days.
    A zero maximum or bank means that there is none.
    """
    if capital == 0 and increment == 0:
        return None
    if plafond and plafond < max(capital, 1):
        return None
    return {"type": "correspondance", "capital": capital,
            "increment": increment, "plafond": plafond, "reserve": reserve}


def cadence_de_balise(controle: str) -> dict | None:
    """
    Reads a TimeControl tag of the form "600+5" or "300", in seconds.

    The other forms of the standard (moves per period, hourglass) and the
    free values give None: the tag is then quoted as it is.
    """
    trouve = RE_TIMECONTROL.fullmatch(controle.strip())
    if not trouve:
        return None
    initial, increment = int(trouve.group(1)), int(trouve.group(2) or 0)
    if initial == 0 and increment == 0:
        return None
    return {"type": "reel", "initial": initial, "increment": increment}


def noter_cadence(cadence: dict) -> str:
    """Form of a time control in the settings file."""
    if cadence["type"] == "reel":
        return "%d+%d" % (cadence["initial"] // 60, cadence["increment"])
    if cadence["type"] == "correspondance" and "capital" in cadence:
        note = "%s + %s" % (pluriel(cadence["capital"], "day"),
                            duree_increment(cadence["increment"]))
        if cadence["plafond"]:
            note += ", maximum %s" % pluriel(cadence["plafond"], "day")
        if cadence["reserve"]:
            note += ", bank %s" % pluriel(cadence["reserve"], "day")
        return note
    if cadence["type"] == "correspondance" and "coups" in cadence:
        return "%s in %s" % (pluriel(cadence["coups"], "move"),
                             pluriel(cadence["periode"], "day"))
    if cadence["type"] == "correspondance":
        return pluriel(cadence["jours"], "day")
    return "unknown"


def pluriel(nombre: int, mot: str) -> str:
    """ "1 day", "14 days", "0 days": the number, then the word, plural
    unless the number is 1."""
    return "%d %s%s" % (nombre, mot, "s" if nombre != 1 else "")


def ordinal(nombre: int) -> str:
    """
    English ordinal of a rank: "1st", "2nd", "3rd", "4th", then "11th",
    "12th" and "13th", but "21st", "22nd", "23rd" and "101st". A list
    followed by a single suffix, as French allows ("1er", then "2e" and
    beyond), would write "21th" in English: the rule follows the last
    two digits.
    """
    if 11 <= nombre % 100 <= 13:
        suffixe = "th"
    else:
        suffixe = {1: "st", 2: "nd", 3: "rd"}.get(nombre % 10, "th")
    return "%d%s" % (nombre, suffixe)


def categorie_cadence(initial: int, increment: int) -> str:
    """Lichess category of a real-time time control (CATEGORIES_CADENCE)."""
    estimee = initial + COUPS_ESTIMES * increment
    for seuil, nom in CATEGORIES_CADENCE:
        if estimee >= seuil:
            return nom
    return CATEGORIES_CADENCE[-1][1]


def decrire_cadence(cadence: dict) -> str:
    """
    Sentence describing a time control, as it goes into context.md:
    "rapid, 15 minutes + 10 seconds per move", "blitz, 5 minutes
    without increment", "correspondence, 14 days per move",
    "correspondence, 10 moves in 50 days", "correspondence, clock of
    5 days + 36 hours per move, maximum of 20 days", or "unspecified".
    """
    if cadence["type"] == "correspondance" and "capital" in cadence:
        phrase = ("correspondence, clock of %s + %s per move"
                  % (pluriel(cadence["capital"], "day"),
                     duree_increment(cadence["increment"])))
        if cadence["plafond"]:
            phrase += ", maximum of %s" % pluriel(cadence["plafond"], "day")
        if cadence["reserve"]:
            phrase += ", bank of %s" % pluriel(cadence["reserve"], "day")
        return phrase
    if cadence["type"] == "correspondance" and "coups" in cadence:
        return "correspondence, %s in %s" % (
            pluriel(cadence["coups"], "move"),
            pluriel(cadence["periode"], "day"))
    if cadence["type"] == "correspondance":
        return "correspondence, %s per move" % pluriel(cadence["jours"],
                                                       "day")
    if cadence["type"] != "reel":
        return CADENCE_DEFAUT
    minutes, secondes = divmod(cadence["initial"], 60)
    duree = []
    if minutes or not secondes:
        duree.append(pluriel(minutes, "minute"))
    if secondes:
        duree.append(pluriel(secondes, "second"))
    increment = (" + %s per move" % pluriel(cadence["increment"], "second")
                 if cadence["increment"] else " without increment")
    return "%s, %s%s" % (categorie_cadence(cadence["initial"],
                                           cadence["increment"]),
                         " ".join(duree), increment)


def demander_entier(question: str, minimum: int,
                    vide: int | None = None) -> int | None:
    """
    Asks for an integer of at least `minimum`, and asks the question again
    as long as the answer is not one. The end of the stream returns None.
    If `vide` is given, it is the value kept by the Enter key alone.
    """
    while True:
        reponse = demander(question)
        if reponse is None:
            return None
        if reponse == "" and vide is not None:
            return vide
        if re.fullmatch(r"[0-9]{1,5}", reponse) and int(reponse) >= minimum:
            return int(reponse)
        sys.stderr.write("  Expected answer: a whole number, %d or more.\n"
                         % minimum)


def demander_cadence(libelle: str, defaut: dict) -> tuple[dict, bool] | None:
    """
    Asks for a time control in two or three questions, all checked.

    The type first, real time, correspondence or unknown; then the minutes
    per player and the increment in seconds, or, for correspondence, the
    system and its numbers (see demander_correspondance).
    Enter, at the first question, keeps `defaut`. Returns the time control
    and a boolean saying whether it is the default, or None at the end of
    the stream. No free text is accepted: an answer outside the expected
    forms makes the question come again.
    """
    propose = decrire_cadence(defaut)
    while True:
        reponse = demander("%s: [r]eal time, [c]orrespondence or "
                           "[u]nknown?" % libelle, propose)
        if reponse is None:
            return None
        if reponse == propose:
            return defaut, True
        choix = reponse.casefold()
        if choix in ("r", "real", "real time", "real-time"):
            minutes = demander_entier("  Minutes per player?", 0)
            if minutes is None:
                return None
            increment = demander_entier("  Increment in seconds?", 0)
            if increment is None:
                return None
            if minutes == 0 and increment == 0:
                sys.stderr.write("  A time control with neither time nor "
                                 "increment does not exist.\n")
                continue
            return ({"type": "reel", "initial": 60 * minutes,
                     "increment": increment}, False)
        if choix in ("c", "corr", "correspondence"):
            saisie = demander_correspondance()
            if saisie is None:
                return None
            return saisie, False
        if choix in ("u", "unknown", "?"):
            return dict(CADENCE_INCONNUE), False
        sys.stderr.write("  Expected answer: r, c or u.\n")


def analyser_niveau(texte: str) -> int | None:
    """
    Reads a rating written in the settings file: a number of Elo points
    between NIVEAU_MIN and NIVEAU_MAX. Returns 0 for an unknown rating,
    and None for a value of another form.
    """
    texte = texte.strip().casefold()
    if texte in ("", "?", "unknown"):
        return 0
    if (re.fullmatch(r"[0-9]{1,4}", texte)
            and NIVEAU_MIN <= int(texte) <= NIVEAU_MAX):
        return int(texte)
    return None


def demander_niveau() -> int | None:
    """
    Asks for the player's rating in Elo points, Enter meaning "unknown"
    (0). The question is asked again as long as the answer is not an
    integer within the bounds. Returns None at the end of the stream.
    """
    while True:
        reponse = demander("Your rating, in approximate Elo points? "
                           "(Enter: unknown)")
        if reponse is None:
            return None
        niveau = analyser_niveau(reponse)
        if niveau is not None:
            return niveau
        sys.stderr.write("  Expected answer: a whole number between %d and "
                         "%d, or Enter.\n" % (NIVEAU_MIN, NIVEAU_MAX))


def deduire_camp(partie: chess.pgn.Game, pseudos: list[str]) -> str | None:
    """
    Side of the player from their usernames, without asking any question:
    "White", "Black", or None if no tag, or both, carry a username.
    Used outside a terminal, where completer_entetes is not called.
    """
    moi_blancs = est_pseudo(partie.headers.get("White", "?"), pseudos)
    moi_noirs = est_pseudo(partie.headers.get("Black", "?"), pseudos)
    if moi_blancs == moi_noirs:
        return None
    return "White" if moi_blancs else "Black"


def demander_correspondance() -> dict | None:
    """
    Asks for a correspondence time control, in one of its three systems.

    Fixed delay: a number of days for each move. Moves per period: a
    number of moves and a duration in days. Clock: days at the start, an
    increment per move entered with its unit, then an optional maximum and
    bank. An inconsistent input goes back to the choice of the system.
    Returns None at the end of the stream.
    """
    while True:
        reponse = demander("  Correspondence: fixed [d]elay per move, "
                           "[p]eriod for a number of moves, or [c]lock "
                           "with an increment?")
        if reponse is None:
            return None
        choix = reponse.casefold()
        if choix in ("d", "delay"):
            jours = demander_entier("  Days per move?", 1)
            if jours is None:
                return None
            return {"type": "correspondance", "jours": jours}
        if choix in ("p", "period"):
            coups = demander_entier("  Number of moves per period?", 1)
            if coups is None:
                return None
            periode = demander_entier("  Length of the period, in days?", 1)
            if periode is None:
                return None
            return {"type": "correspondance", "coups": coups,
                    "periode": periode}
        if choix in ("c", "clock"):
            capital = demander_entier("  Starting clock, in days?", 0)
            if capital is None:
                return None
            increment = demander_increment()
            if increment is None:
                return None
            plafond = demander_entier("  Maximum of the clock, in days? "
                                      "(Enter: none)", 1, vide=0)
            if plafond is None:
                return None
            reserve = demander_entier("  Bank beside the clock, in "
                                      "days? (Enter: none)", 1, vide=0)
            if reserve is None:
                return None
            cadence = cadence_a_capital(capital, increment, plafond, reserve)
            if cadence is not None:
                return cadence
            sys.stderr.write("  Inconsistent time control: it takes a "
                             "clock or an increment, and a maximum at "
                             "least equal to the starting clock.\n")
            continue
        sys.stderr.write("  Expected answer: d, p or c.\n")


def demander_increment() -> int | None:
    """
    Asks for the increment per move, with its unit, and returns it in
    hours: "36h" gives 36, "3d" gives 72. The question is asked again as
    long as the answer does not have this form. Returns None at the end of
    the stream.
    """
    while True:
        reponse = demander("  Increment per move, with its unit, 36h or 3d "
                           "for example?")
        if reponse is None:
            return None
        trouve = RE_INCREMENT.fullmatch(reponse.casefold())
        if trouve:
            return heures_increment(int(trouve.group(1)), trouve.group(2))
        sys.stderr.write("  Expected answer: a whole number followed by h "
                         "or d.\n")


def mots_nom(nom: str) -> list[str]:
    """
    Words of a name, ignoring case and the forms of the accents:
    "Müller, Noël" gives "müller" and "noël".
    """
    nom = unicodedata.normalize("NFC", nom).casefold()
    return [mot for mot in re.split(r"[\s,]+", nom) if mot]


def est_pseudo(nom: str, pseudos: list[str]) -> bool:
    """
    True if the tag carries one of the usernames, ignoring case: as the
    whole name, or as a run of its words. "Müller" is found in "Müller,
    Noël", "zoé blanche" in "Zoé Blanche", but "Max" no longer in
    "Maxime": looked up as a mere substring, a username found in the
    name of the opponent alone gave the wrong side.
    """
    mots = mots_nom(nom)
    for pseudo in pseudos:
        cherches = mots_nom(pseudo)
        n = len(cherches)
        if n and any(mots[i:i + n] == cherches
                     for i in range(len(mots) - n + 1)):
            return True
    return False


def completer_entetes(partie: chess.pgn.Game, pseudos: list[str]) -> dict:
    """
    Gets the player's side from the White and Black tags, or asks for it.

    Only empty tags or tags set to "?" are filled in: the first username
    for the player's side, the name given for the opponent. A name already
    present is never replaced. Returns the side ("White", "Black" or
    None), the origin of the information and the list of modified tags.

    `pseudos` may be empty, when neither --usernames nor the settings give
    any: the side is then always asked, and so is the player's name if
    its tag is empty.
    """
    moi_blancs = est_pseudo(partie.headers.get("White", "?"), pseudos)
    moi_noirs = est_pseudo(partie.headers.get("Black", "?"), pseudos)
    if moi_blancs != moi_noirs:
        return {"side": "White" if moi_blancs else "Black",
                "origin": "deduced from the headers", "modified_tags": []}

    # No username found, or both: only the player can decide. An unreadable
    # answer makes the question come again, Ctrl-D gives up on it.
    camp = None
    while camp is None:
        reponse = demander("Did you play White or Black? [w/b]")
        if reponse is None:
            return {"side": None, "origin": "not declared",
                    "modified_tags": []}
        choix = reponse.casefold()
        if choix in ("w", "white"):
            camp = "White"
        elif choix in ("b", "black"):
            camp = "Black"

    modifiees = []
    mienne, autre = (("White", "Black") if camp == "White"
                     else ("Black", "White"))
    if partie.headers.get(mienne, "?").strip() in ("", "?"):
        if pseudos:
            partie.headers[mienne] = pseudos[0]
            modifiees.append(mienne)
        else:
            # No known username: pseudos[0] raised IndexError. We ask
            # for the name, as for the opponent, and "?" leaves the tag
            # as it is.
            nom = demander("Your player name?", "?", nom=True)
            if nom and nom != "?":
                partie.headers[mienne] = nom
                modifiees.append(mienne)
    if partie.headers.get(autre, "?").strip() in ("", "?"):
        nom = demander("Opponent's name?", "?", nom=True)
        if nom and nom != "?":
            partie.headers[autre] = nom
            modifiees.append(autre)
    return {"side": camp, "origin": "declared", "modified_tags": modifiees}


def recueillir_contexte(partie: chess.pgn.Game, camp: dict,
                        cadence_habituelle: dict | None = None) -> str:
    """
    Asks the time control question if the TimeControl tag does not give
    it, then the four startup questions of the project, and writes the
    text of context.md. `cadence_habituelle`, taken from the settings, is
    the time control that the question suggests; without it, it is
    "unspecified". A TimeControl tag of a common form is quoted, then
    translated.

    "(default)" marks an answer confirmed with Enter: the analyst thus
    tells a choice of the player from a default value. After an end of
    stream, the remaining questions take their default without being
    asked.
    """
    fin_de_flux = False

    def poser(question: str, defaut: str) -> tuple[str, bool]:
        nonlocal fin_de_flux
        reponse = None if fin_de_flux else demander(question, defaut)
        if reponse is None:
            fin_de_flux = True
            return defaut, True
        return reponse, reponse == defaut

    lignes = [("The player's answers to the startup questions, asked by "
               "the script before the collection. \"(default)\" marks "
               "an answer confirmed with Enter."), ""]
    if camp.get("side"):
        lignes.append("- Player's side: %s, %s"
                      % (camp["side"], camp["origin"]))
    else:
        lignes.append("- Player's side: unknown, not declared")

    # "-" is the value that TimeControl sometimes takes for a correspondence
    # game: it does not tell the real time control, so we ask for it.
    controle = partie.headers.get("TimeControl", "?").strip()
    if controle not in ("", "?", "-"):
        # "600+5" reads badly: ten minutes, or six hundred? The tag is
        # quoted as it is, then translated when its form allows it.
        lue = cadence_de_balise(controle)
        lignes.append("- Time control: TimeControl tag `%s`%s"
                      % (controle,
                         ", that is %s" % decrire_cadence(lue) if lue
                         else ""))
    else:
        habituelle = cadence_habituelle or dict(CADENCE_INCONNUE)
        saisie = (None if fin_de_flux
                  else demander_cadence("Time control of the game",
                                        habituelle))
        if saisie is None:
            fin_de_flux = True
            saisie = (habituelle, True)
        lignes.append("- Time control: %s%s"
                      % (decrire_cadence(saisie[0]),
                         " (default)" if saisie[1] else ""))
    for libelle, question, valeur in QUESTIONS_CONTEXTE:
        reponse, defaut = poser(question, valeur)
        lignes.append("- %s: %s%s"
                      % (libelle, reponse, " (default)" if defaut else ""))
    return "\n".join(lignes) + "\n"


# ===========================================================================
# User settings
#
# What depends on the person, and not on the game, lives in a small file
# in INI format, readable and editable by hand:
#
#     [player]
#     usernames = MyUsername, OtherUsername
#     time_control = 15+10
#     rating = 1500
#
# It is created on the first run in a terminal, by three questions asked
# only once. Outside a terminal, nothing is asked or written: the script
# makes do with what the file already contains.
# ===========================================================================

def chemin_reglages(chemin: str) -> pathlib.Path:
    """
    Path of a settings file: the name given to --settings, at the root of
    the application folder. The name has been checked by
    verifier_nom_reglages: it cannot lead out of the folder.
    """
    return pathlib.Path(DOSSIER_APPLICATION) / chemin


def verifier_nom_reglages(nom: str) -> str | None:
    """
    Reason to refuse the name given to --settings, or None.

    The settings never leave the application folder: deleting it leaves
    nothing behind, and no path, such as /dev/null or that of the file of
    another program, can be written over by mistake. So --settings takes
    a file name ending in .ini, which chemin_reglages puts at the root of
    the folder; a path, even inside the folder, is refused, and so is a
    name that starts with a dot, which would hide the file.
    """
    if RE_NOM_REGLAGES.fullmatch(nom):
        return None
    return ("--settings: %s is not a settings name. Give a file name ending "
            "in .ini, without a folder and not starting with a dot: every "
            "settings file is kept in %s. To run without settings, use "
            "--no-settings." % (nom, DOSSIER_APPLICATION))


def confirmer_nouveaux_reglages(nom: str) -> None:
    """
    Asks before creating a settings file named by --settings that does
    not exist yet.

    A typo in the name, jouer1.ini for joueur1.ini, would otherwise start
    a new file and ask its questions again. Answering n, or Ctrl-D, stops
    the script before anything is written or collected. The default file
    is created without this question on the first run: its name cannot
    be mistyped. An unreadable answer makes the question come again.
    """
    question = ("Settings: %s does not exist yet in %s. Create it? [y/n]"
                % (nom, DOSSIER_APPLICATION))
    while True:
        reponse = demander(question)
        choix = None if reponse is None else reponse.casefold()
        if choix in (None, "n", "no"):
            raise SystemExit("Nothing done: check the name given to "
                             "--settings, or use --no-settings to run "
                             "without settings.")
        if choix in ("y", "yes"):
            return


def purger_reglages(chemin: str) -> None:
    """
    Deletes the settings file, and that file only: its directory stays in
    place, it may contain something else.

    The settings questions will be asked again on the next run in a
    terminal. A missing file is not an error: the goal, having no settings
    any more, is already reached. A directory, or anything that is not a
    file, is refused rather than deleted.

    With --settings, the name comes from the command line: a typo must not
    destroy another file. Only a file that carries the [player] section,
    or an empty file, is deleted. The section is looked up in the text
    decoded as the reading does, a settings file in UTF-16 included,
    without configparser: a damaged settings file, which configparser
    would reject, thus stays deletable.
    """
    p = chemin_reglages(chemin)
    if not p.exists() and not p.is_symlink():
        journal("No settings file to delete: %s" % p)
        return
    if not (est_fichier(p) or p.is_symlink()):
        raise SystemExit("--purge-settings: %s is not a file, nothing is "
                         "deleted." % p)
    try:
        brut = p.read_bytes()
    except OSError as e:
        raise SystemExit("--purge-settings: cannot read %s: %s. Nothing is "
                         "deleted." % (p, e)) from e
    texte = decoder_octets(brut)[0]
    en_tete = re.compile(r"^[ \t]*\[%s\][ \t]*$"
                         % re.escape(REGLAGES_SECTION), re.MULTILINE)
    if texte.strip() and not en_tete.search(texte):
        raise SystemExit("--purge-settings: %s is not a settings file, it "
                         "does not carry the [%s] section. Nothing is "
                         "deleted." % (p, REGLAGES_SECTION))
    try:
        p.unlink()
    except OSError as e:
        raise SystemExit("--purge-settings: cannot delete %s: "
                         "%s" % (p, e)) from e
    journal("Settings deleted: %s. They will be asked again at the next "
            "collection run in a terminal." % p)


def lire_reglages(chemin: str) -> configparser.ConfigParser:
    """
    Loads the settings file, or empty settings if it does not exist.

    The file goes through the same decoding as the PGN: its encoding does
    not matter. A file that configparser rejects stops the script with a
    clear message, rather than being silently ignored. The [player]
    section always exists in the returned object.
    """
    # interpolation=None: the percent sign of a value stays a plain
    # character, it triggers no substitution.
    reglages = configparser.ConfigParser(interpolation=None)
    p = chemin_reglages(chemin)
    if est_fichier(p):
        texte = lire_fichier_texte(p, "settings")[0]
        try:
            reglages.read_string(texte, source=str(p))
        except configparser.Error as err:
            raise SystemExit(
                "Unreadable settings: %s\n"
                "Fix %s, or delete it: it will be created again at the next "
                "run in a terminal."
                % (nettoyer_valeur(str(err)), p)) from err
    if not reglages.has_section(REGLAGES_SECTION):
        reglages.add_section(REGLAGES_SECTION)
    return reglages


def reglages_vides() -> configparser.ConfigParser:
    """
    Empty settings, with only the [player] section: what --no-settings
    puts in place of the file, which is then neither read nor written.

    The usernames, the usual time control and the rating are missing, as
    on a first run outside a terminal: the side is asked, or deduced from
    --usernames, the rating comes from the Elo tag of the player's side,
    and the time control from the TimeControl tag or from the question
    about the game, which then suggests "unspecified".
    """
    reglages = configparser.ConfigParser(interpolation=None)
    reglages.add_section(REGLAGES_SECTION)
    return reglages


def reglage(reglages: configparser.ConfigParser, clef: str) -> str:
    """Value of a key of the [player] section, empty if it is missing."""
    return reglages.get(REGLAGES_SECTION, clef, fallback="").strip()


def decouper_pseudos(texte: str) -> list[str]:
    """List of usernames taken from a comma-separated string."""
    return [x.strip() for x in texte.split(",") if x.strip()]


def refus_ecriture_reglages(p: pathlib.Path) -> str | None:
    """
    Reason not to write the settings in p, or None if they may be.

    The writing goes through a neighboring file renamed over p: whatever
    p names is replaced. As root, --settings /dev/null would thus turn
    the device into a regular file, and a typo in the path would rewrite
    the INI file of another program, its comments lost. So p is written
    only if it does not exist yet, or if it is a regular file that is
    empty or already a settings file: it carries the [player] section,
    or the [joueur] section of the former format, which a settings.ini
    copied from reglages.ini, or written by a development version of
    5.0.0, still carries. A device, a FIFO, a directory or any other file
    is left untouched.

    The section is looked up in the decoded text, as for
    --purge-settings. A file that is not a regular file is never opened:
    reading a FIFO would block the script.
    """
    try:
        if not p.exists():
            return None
    except OSError as err:
        return "cannot check it: %s" % err
    if not est_fichier(p):
        return ("it is not a regular file. To run without settings, use "
                "--no-settings")
    try:
        brut = p.read_bytes()
    except OSError as err:
        return "cannot read it: %s" % err
    texte = decoder_octets(brut)[0]
    sections = "|".join(re.escape(s) for s in
                        (REGLAGES_SECTION, REGLAGES_SECTION_ANCIENNE))
    en_tete = re.compile(r"^[ \t]*\[(%s)\][ \t]*$" % sections,
                         re.MULTILINE)
    if texte.strip() and not en_tete.search(texte):
        return ("it is not a settings file, it does not carry the [%s] "
                "section" % REGLAGES_SECTION)
    return None


def ecrire_reglages(chemin: str, reglages: configparser.ConfigParser) -> bool:
    """
    Writes the settings file, comments included.

    The known keys come first, each one under its comment; the other keys
    of [player] and the other sections, which you may have added, are
    copied after them. A failure to write does not stop the collection: it
    is reported, and the question will be asked again on the next run. The
    same goes for a path that must not be replaced, which is left as it
    is: see refus_ecriture_reglages. Returns true if the file was written.
    """
    def ligne(clef: str, valeur: str) -> str:
        # A value on several lines continues with indented lines: this is
        # the form that configparser can read back.
        valeur = valeur.replace("\n", "\n\t")
        return "%s = %s" % (clef, valeur) if valeur else "%s =" % clef

    out = ["# Settings of ianalyze.py.",
           "# You may edit this file by hand. A deleted key will be asked",
           "# again at the next run in a terminal.",
           "",
           "[%s]" % REGLAGES_SECTION]
    connues = [clef for clef, _ in REGLAGES_CLEFS]
    for clef, commentaire in REGLAGES_CLEFS:
        if reglages.has_option(REGLAGES_SECTION, clef):
            out.extend("# %s" % c for c in commentaire)
            out.append(ligne(clef, reglages.get(REGLAGES_SECTION, clef)))
    for clef, valeur in reglages.items(REGLAGES_SECTION):
        if clef not in connues:
            out.append(ligne(clef, valeur))
    for section in reglages.sections():
        if section != REGLAGES_SECTION:
            out.extend(["", "[%s]" % section])
            out.extend(ligne(c, v) for c, v in reglages.items(section))

    p = chemin_reglages(chemin)
    refus = refus_ecriture_reglages(p)
    if refus is not None:
        journal("Warning: settings not saved in %s: %s." % (p, refus))
        return False
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        ecrire_texte(p, "\n".join(out) + "\n")
    except OSError as err:
        journal("Warning: settings not saved in %s: %s"
                % (p, err))
        return False
    return True


def completer_reglages(chemin: str, reglages: configparser.ConfigParser,
                       pseudos_cli: list[str] | None) -> None:
    """
    Asks, only once, for the settings that the file does not give.

    Called only on an interactive terminal. Each key missing from
    [player] gets a question; a key that is present, even empty, is never
    asked for again. The usernames passed with --usernames serve as the
    suggested answer. An end of stream (Ctrl-D) gives up without writing
    anything: the questions will come back on the next run.
    """
    manquantes = [clef for clef, _ in REGLAGES_CLEFS
                  if not reglages.has_option(REGLAGES_SECTION, clef)]
    # A time control that is present but unreadable, written by hand or
    # inherited from a version that accepted free text, is asked for
    # again too: it must not go to the analyst as it is.
    brute = reglages.get(REGLAGES_SECTION, "time_control", fallback=None)
    if brute is not None and analyser_cadence(brute) is None:
        journal("Settings: the saved time control, \"%s\", cannot be read, it "
                "is asked again." % nettoyer_valeur(brute))
        manquantes.append("time_control")
    # The same goes for the rating, which must be a number of Elo points.
    brute = reglages.get(REGLAGES_SECTION, "rating", fallback=None)
    if brute is not None and analyser_niveau(brute) is None:
        journal("Settings: the saved rating, \"%s\", cannot be read, it is "
                "asked again." % nettoyer_valeur(brute))
        manquantes.append("rating")
    if not manquantes:
        return

    journal("Settings: %d answer(s) to give only once, kept in "
            "%s." % (len(manquantes), chemin_reglages(chemin)))
    for clef in manquantes:
        if clef == "usernames":
            if pseudos_cli:
                reponse = demander("Your username, or several separated "
                                   "by commas?",
                                   ", ".join(pseudos_cli), nom=True)
            else:
                reponse = demander("Your username, or several separated "
                                   "by commas? (Enter: none)", nom=True)
            if reponse is not None:
                reponse = ", ".join(decouper_pseudos(reponse))
        elif clef == "rating":
            niveau = demander_niveau()
            if niveau is None:
                reponse = None
            else:
                reponse = str(niveau) if niveau else "unknown"
        else:
            saisie = demander_cadence("Your usual time control",
                                      dict(CADENCE_INCONNUE))
            reponse = None if saisie is None else noter_cadence(saisie[0])
        if reponse is None:
            journal("Settings not saved: input interrupted.")
            return
        reglages.set(REGLAGES_SECTION, clef, reponse)

    if ecrire_reglages(chemin, reglages):
        journal("Settings saved: %s" % chemin_reglages(chemin))


# ===========================================================================
# Analysis prompt
#
# The data of the archive are not enough: the analyst must be told what
# to do with them. This text lives in a template, prompt-template.txt,
# which you edit without opening this script. At each collection, the
# script derives the prompt of the game from it: it fills in the values
# (username, rating, archive name) and keeps only the passages that apply
# (database queried, engine present or not). The prompt thus always
# describes the summary that this version of the script has just
# written.
#
# Two kinds of markers in the template:
#
#     {{NAME}}            a value, replaced
#     #! if CONDITION     keeps what follows if the condition is true
#     #! if not CONDITION keeps what follows if it is false
#     #! else             switches
#     #! end              closes the last open "if"
#     #! note ...         comment of the template, never copied
#
# The "if" can be nested.
# ===========================================================================

def chemin_modele(option: str | None, seul: bool = False) -> pathlib.Path:
    """
    Path of the prompt template: the one of --prompt, otherwise, next to
    the script, prompt-template.txt or, with --prompt-only, the short
    template prompt-only-template.txt. The real path of the script is
    followed, so that a symbolic link placed elsewhere finds the template
    of the repository.
    """
    if option:
        return pathlib.Path(os.path.expanduser(option))
    return (pathlib.Path(os.path.realpath(__file__)).parent
            / (PROMPT_SEUL_MODELE if seul else PROMPT_MODELE))


def lire_directive(ligne: str) -> list[str] | None:
    """Words of a directive line, or None for an ordinary line."""
    ligne = ligne.strip()
    if not ligne.startswith(PROMPT_DIRECTIVE):
        return None
    return ligne[len(PROMPT_DIRECTIVE):].split()


def rendre_modele(texte: str, conditions: dict[str, bool],
                  valeurs: dict[str, str], source: str) -> str:
    """
    Derives a prompt from the template: applies the directives, replaces
    the values.

    The whole template is checked, discarded passages included: an
    unknown directive, an "if" never closed, a condition or a value that
    the script does not know stop the script with the line number. The
    extra blank lines left by a removed passage are tightened.
    """
    def erreur(numero: int, message: str) -> SystemExit:
        return SystemExit("Prompt template %s, line %d: %s"
                          % (source, numero, message))

    sortie: list[str] = []
    # Stack of the open "if": the line of the "if", the value of its
    # condition, and whether an "else" has already been met.
    pile: list[tuple[int, bool, bool]] = []
    for numero, ligne in enumerate(texte.split("\n"), start=1):
        mots = lire_directive(ligne)
        if mots is None:
            for nom in RE_VALEUR_MODELE.findall(ligne):
                if nom not in PROMPT_VALEURS:
                    raise erreur(numero, "unknown value {{%s}}, accepted "
                                 "values: %s"
                                 % (nom, ", ".join(PROMPT_VALEURS)))
            # Double braces that remain once the recognized markers
            # are removed: a badly written marker, {{ NIVEAU }} or
            # {{CAMP1}}, which would go as it is into the prompt.
            reste = RE_VALEUR_MODELE.sub("", ligne)
            if "{{" in reste or "}}" in reste:
                raise erreur(numero, "badly formed marker, expected form: "
                             "{{NAME}}, in capitals and without spaces")
            if all(vrai for _, vrai, _ in pile):
                sortie.append(RE_VALEUR_MODELE.sub(
                    lambda m: valeurs[m.group(1)], ligne).rstrip())
            continue
        if not mots or mots[0] == "note":
            continue
        if mots[0] == "if":
            negation = len(mots) == 3 and mots[1] == "not"
            if len(mots) != (3 if negation else 2):
                raise erreur(numero, "expected form: \"if CONDITION\" or \"if "
                             "not CONDITION\"")
            if mots[-1] not in PROMPT_CONDITIONS:
                raise erreur(numero, "unknown condition %s, accepted "
                             "conditions: %s"
                             % (mots[-1], ", ".join(PROMPT_CONDITIONS)))
            pile.append((numero, conditions[mots[-1]] != negation, False))
        elif mots == ["else"]:
            if not pile or pile[-1][2]:
                raise erreur(numero, "\"else\" without an open \"if\", or "
                             "repeated")
            pile[-1] = (pile[-1][0], not pile[-1][1], True)
        elif mots == ["end"]:
            if not pile:
                raise erreur(numero, "\"end\" without an open \"if\"")
            pile.pop()
        else:
            raise erreur(numero, "unknown directive \"%s\", accepted "
                         "directives: if, else, end, note" % " ".join(mots))
    if pile:
        raise erreur(pile[-1][0], "this \"if\" is never closed by \"end\"")

    # Blank lines: at most one in a row, none at the start or at the end.
    resserre: list[str] = []
    for ligne in sortie:
        if ligne or (resserre and resserre[-1]):
            resserre.append(ligne)
    return "\n".join(resserre).strip("\n") + "\n"


def lignes_de_texte(modele: str) -> list[str]:
    """Template lines bound for the prompt: neither blank nor directives."""
    return [ligne for ligne in modele.split("\n")
            if ligne.strip() and not ligne.lstrip().startswith("#!")]


def verifier_modele(texte: str, source: str) -> None:
    """
    Checks the template before the collection, to fail early: an unknown
    marker must not show up after ten minutes of engine. The rendering is
    a dry run, its result is not kept.
    """
    rendre_modele(texte, dict.fromkeys(PROMPT_CONDITIONS, False),
                  dict.fromkeys(PROMPT_VALEURS, ""), source)
    # An empty template, or one made only of directives, would give a prompt
    # without a single line, announced as written.
    if not lignes_de_texte(texte):
        raise SystemExit("Prompt template %s: it contains no line of "
                         "text." % source)


def decrire_niveau(niveau: int, partie: chess.pgn.Game,
                   camp: str | None) -> str:
    """
    Sentence of the player's rating. The rating declared in the settings
    wins; failing that, the Elo of the player's tag in this game, if their
    side is known; otherwise nothing precise.
    """
    if niveau:
        return "about %d Elo, declared by the player" % niveau
    balise = {"White": "WhiteElo", "Black": "BlackElo"}.get(camp or "")
    if balise:
        elo = partie.headers.get(balise, "").strip()
        if re.fullmatch(r"[0-9]{3,4}", elo):
            return "%s Elo, from the %s tag of the game" % (elo, balise)
    return "unspecified: judge from the game, and stay accessible"


# ===========================================================================
# Catalog of the named openings
#
# The catalog serves to tell apart two kinds of rare moves: the one that
# stays within a listed line, such as 1.b4, the Polish, played in less
# than one percent of the games, and the one that leaves every known
# line. Only the second one marks leaving theory. The catalog says
# "known", never "good": "Barnes Opening: Fool's Mate" is in it.
#
# The explorer server only names the final position of each line. The
# local index also keeps all the intermediate positions, without a name:
# a named line is thus known along its whole length.
# ===========================================================================

class Catalogue:
    """
    Index of the positions of the catalog, loaded from the local file.

    The positions are identified by their EPD, en passant capture included
    only if it is playable, which matches the hashing of the server
    (EnPassantMode::Legal). An intermediate position has an empty name.
    """

    def __init__(self, positions: dict[str, tuple[str, str]],
                 meta: dict[str, str]):
        self.positions = positions
        self.meta = meta

    def connue(self, plateau: chess.Board) -> bool:
        """Tells whether the position belongs to a line of the catalog."""
        return plateau.epd() in self.positions

    def nom(self, plateau: chess.Board) -> str | None:
        """Returns "ECO name" if the position is named, otherwise None."""
        eco, nom = self.positions.get(plateau.epd(), ("", ""))
        return "%s %s" % (eco, nom) if nom else None


def chemin_catalogue(repertoire: str) -> pathlib.Path:
    """Path of the index in the catalog directory."""
    return pathlib.Path(os.path.expanduser(repertoire)) / CATALOGUE_INDEX


def commande_catalogue(repertoire: str) -> str:
    """Installation command to suggest in the error messages."""
    supplement = ("" if repertoire == CATALOGUE_DEFAUT
                  else " --catalog %s" % repertoire)
    return "%s --install-catalog%s" % (os.path.abspath(__file__),
                                       supplement)


def installer_catalogue(repertoire: str, delai: int) -> None:
    """
    Downloads the catalog, validates it, then writes the local index.

    Each line is replayed with python-chess: an unreadable or illegal move
    stops the installation, and the index already in place is not
    touched. Like the server, we reject a position named twice.

    The index is written to a temporary file in the same directory, synced
    to disk, then renamed: the replacement is atomic, a collection started
    during an update reads the old index or the new one, never a mix of
    the two. Running the option again updates the catalog.
    """
    positions: dict[str, tuple[str, str]] = {}
    nb_lignes = 0
    for morceau in CATALOGUE_PARTIES:
        url = CATALOGUE_SOURCE.format(part=morceau)
        journal("Downloading the catalog: %s" % url)
        requete = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(requete, timeout=delai) as reponse:
                # utf-8-sig: a byte order mark at the start of the
                # file is ignored instead of corrupting the header.
                texte = reponse.read().decode("utf-8-sig", errors="strict")
        except urllib.error.HTTPError as err:
            raise SystemExit("Catalog: HTTP %d for %s."
                             % (err.code, url)) from err
        except (OSError, http.client.HTTPException) as err:
            # URLError is a subclass of OSError, as for the PGN export.
            raise SystemExit("Catalog unreachable: %s"
                             % getattr(err, "reason", err)) from err
        except UnicodeDecodeError as err:
            raise SystemExit("Catalog: %s is not in UTF-8." % url) \
                from err

        lecteur = csv.DictReader(io.StringIO(texte), delimiter="\t")
        if lecteur.fieldnames != ["eco", "name", "pgn"]:
            raise SystemExit("Catalog: unexpected header in %s: %s"
                             % (url, lecteur.fieldnames))

        lignes_fichier = 0
        # Line 1 is the header, the numbering follows that of the file.
        for numero, ligne in enumerate(lecteur, start=2):
            eco = (ligne.get("eco") or "").strip()
            nom = (ligne.get("name") or "").strip()
            coups = [j for j in (ligne.get("pgn") or "").split()
                     if not RE_NUMERO_COUP.fullmatch(j)]
            if not eco or not nom or not coups:
                raise SystemExit("Catalog: line %d of %s is incomplete."
                                 % (numero, url))

            plateau = chess.Board()
            for san in coups:
                try:
                    plateau.push_san(san)
                except ValueError as err:
                    raise SystemExit("Catalog: move %s unreadable or illegal, "
                                     "line %d of %s: %s"
                                     % (san, numero, url, err)) from err
                # Intermediate position: known, without a name, unless another
                # line has already named it.
                positions.setdefault(plateau.epd(), ("", ""))

            epd = plateau.epd()
            if positions[epd][1]:
                raise SystemExit("Catalog: position named twice, %s and %s "
                                 "(line %d of %s)."
                                 % (positions[epd][1], nom, numero, url))
            positions[epd] = (eco, nom)
            lignes_fichier += 1

        if lignes_fichier == 0:
            raise SystemExit("Catalog: %s contains no line." % url)
        nb_lignes += lignes_fichier

    nommees = sum(1 for _, nom in positions.values() if nom)
    date = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    entete = "\t".join(("#format=%s" % CATALOGUE_FORMAT, "date=%s" % date,
                        "lines=%d" % nb_lignes, "named=%d" % nommees,
                        "known=%d" % len(positions),
                        "source=%s" % CATALOGUE_SOURCE))

    cible = chemin_catalogue(repertoire)
    temporaire: pathlib.Path | None = None
    try:
        cible.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         dir=cible.parent,
                                         prefix=".catalog-",
                                         suffix=".tmp",
                                         delete=False) as tmp:
            temporaire = pathlib.Path(tmp.name)
            tmp.write(entete + "\n")
            tmp.write("epd\teco\tname\n")
            # Sorted order: two installations of the same catalog give
            # two identical files, easy to compare with diff.
            for epd in sorted(positions):
                tmp.write("%s\t%s\t%s\n" % (epd, *positions[epd]))
            tmp.flush()
            os.fsync(tmp.fileno())
        temporaire.chmod(0o644)
        temporaire.replace(cible)
    except OSError as err:
        if temporaire is not None:
            temporaire.unlink(missing_ok=True)
        raise SystemExit("Cannot write the catalog in %s: %s"
                         % (cible.parent, err)) from err

    # Full read-back through the normal path: what has just been written
    # must load exactly as it does during a collection.
    catalogue = lire_catalogue(repertoire)
    journal("Catalog installed: %s lines, %s named positions, %s known "
            "positions, in %s"
            % (catalogue.meta["lines"], catalogue.meta["named"],
               catalogue.meta["known"], cible))


def lire_catalogue(repertoire: str) -> Catalogue:
    """
    Loads the local index of the catalog and checks its integrity.

    The first line describes the index. An unknown format, or a number of
    positions different from the announced one, betrays a truncated or
    modified file: it is better to stop than to mark the exit from theory
    on an incomplete catalog.
    """
    chemin = chemin_catalogue(repertoire)
    if not est_fichier(chemin):
        raise SystemExit(
            "Opening catalog missing: %s not found.\n\n"
            "Install it with one command:\n"
            "    %s\n" % (chemin, commande_catalogue(repertoire)))
    reparer = "Reinstall it with: %s" % commande_catalogue(repertoire)

    positions: dict[str, tuple[str, str]] = {}
    try:
        # Explicit encoding and error handling, never those of the
        # locale: a damaged index must be rejected, not misread.
        with chemin.open(encoding="utf-8-sig", errors="strict") as f:
            premiere = f.readline().rstrip("\n")
            entete = f.readline().rstrip("\n")
            for numero, ligne in enumerate(f, start=3):
                champs = ligne.rstrip("\n").split("\t")
                if len(champs) != 3 or not champs[0]:
                    raise SystemExit("Corrupt catalog, line %d of %s.\n"
                                     "%s"
                                     % (numero, chemin, reparer))
                positions[champs[0]] = (champs[1], champs[2])
    except (OSError, UnicodeDecodeError) as err:
        raise SystemExit("Unreadable catalog (%s): %s\n"
                         "%s"
                         % (chemin, err, reparer)) from err

    if not premiere.startswith("#"):
        raise SystemExit("Catalog without a description, %s.\n"
                         "%s"
                         % (chemin, reparer))
    meta = dict(champ.partition("=")[::2]
                for champ in premiere[1:].split("\t"))
    if meta.get("format") != CATALOGUE_FORMAT or entete != "epd\teco\tname":
        raise SystemExit("Catalog of unknown format, %s.\n"
                         "%s"
                         % (chemin, reparer))
    if meta.get("known") != str(len(positions)):
        raise SystemExit("Truncated catalog: %s positions announced, %d read "
                         "in %s.\n"
                         "%s"
                         % (meta.get("known"), len(positions), chemin,
                            reparer))
    return Catalogue(positions, meta)


# ===========================================================================
# Explorer: network access
# ===========================================================================

class SansRedirection(urllib.request.HTTPRedirectHandler):
    """
    Refuses any HTTP redirect.

    The default opener of urllib follows redirects by copying the request
    headers, Authorization included, to the new address, even on another
    host. The token must only go to the explorer: a 301, 302, 303, 307 or
    308 answer is therefore returned as it is, like an HTTP error, and
    nothing is sent elsewhere.
    """

    def redirect_request(self, *_arguments, **_options):
        return None


class Explorateur:
    """
    Minimal client of the Lichess explorer, masters or Lichess database.

    Both endpoints require a personal token, without which they return an
    nginx 401 in HTML format. The token is only sent in the Authorization
    header, never in the URL, so that it appears neither in the logs of
    the server nor in a process table.

    `url` names the endpoint queried, the masters database by default so
    that the existing calls keep their behavior. `filtres` contains the
    parameters specific to the Lichess database (variant, speeds, rating
    bands, start date); it stays empty for the masters database, which
    does not know them.
    """

    def __init__(self, jeton: str, pause: float, delai: int,
                 url: str = EXPLORER_URL,
                 filtres: dict[str, str] | None = None):
        self.jeton = jeton
        self.pause = pause
        self.delai = delai
        self.url = url
        # Defensive copy: a dictionary modified later by the caller
        # must not change the requests during the collection.
        self.filtres = dict(filtres or {})
        self._premiere = True
        # Opener specific to the explorer, which follows no redirect:
        # see SansRedirection.
        self._ouvreur = urllib.request.build_opener(SansRedirection)

    def interroger(self, coups_uci: list[str]) -> tuple[int, dict]:
        """
        Queries the position reached after the given moves.

        Returns the pair (HTTP code, decoded dictionary). Any unusable answer,
        code other than 200, non-JSON body or transport error, comes back with
        a dictionary carrying the key "_error", the code being 0 when no HTTP
        code could be obtained.
        """
        # Courtesy pause. The endpoint is strict about the rate, but there
        # is no point in waiting before the very first request.
        if not self._premiere:
            time.sleep(self.pause)
        self._premiere = False

        # All the moves of the database, and not the first ten: a move
        # played beyond the tenth rank otherwise passed for absent (0
        # games, rank "outside the database") while it was only rarer.
        # The server truncates at this value without a cap of its own,
        # and 256 amply covers all the legal moves of a position.
        parametres = {"topGames": "0", "moves": "256"}

        # Filters of the Lichess database. For the masters database the
        # dictionary is empty: the request stays exactly as before the option.
        parametres.update(self.filtres)
        if coups_uci:
            parametres["play"] = ",".join(coups_uci)
        url = self.url + "?" + urllib.parse.urlencode(parametres)

        requete = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/json",
            "Authorization": "Bearer %s" % self.jeton,
        })

        # A single retry, and only on 429: beyond that, it is better to
        # stop than to get banned.
        for tentative in (1, 2):
            try:
                with self._ouvreur.open(requete, timeout=self.delai) as r:
                    corps = r.read().decode("utf-8-sig", errors="replace")
                    # The answer is copied as it is into the archive:
                    # if a server one day sent back the header received, the
                    # token would not get in.
                    donnees = json.loads(expurger(corps, self.jeton))
                    if not isinstance(donnees, dict):
                        return 0, {"_error": "unexpected JSON answer, an "
                                             "object was expected"}
                    return r.status, donnees
            except urllib.error.HTTPError as err:
                if 300 <= err.code < 400:
                    return err.code, {"_error": "redirect refused: the "
                                      "token is only sent to the address "
                                      "of the explorer"}
                # The body of the error is only read for the message: if it
                # is cut or too slow, the HTTP error stays what it
                # is, and only the query stops.
                try:
                    corps = err.read().decode("utf-8-sig", errors="replace")
                except (OSError, http.client.HTTPException):
                    corps = ""
                if err.code == 429 and tentative == 1:
                    journal("429 received, pausing for 60 seconds.")
                    time.sleep(60)
                    continue
                return err.code, {"_error": expurger(corps, self.jeton)[:500]}
            except (OSError, http.client.HTTPException) as err:
                return 0, {"_error": expurger(
                    str(getattr(err, "reason", err)), self.jeton)}
            except ValueError as err:
                return 0, {"_error": "answer not in JSON: %s" % err}
            except RecursionError:
                # A JSON nested thousands of levels deep.
                return 0, {"_error": "answer not in JSON: nesting too "
                                     "deep"}
        return 0, {"_error": "failure after a retry"}


# ===========================================================================
# Explorer: using the data
# ===========================================================================

def total_parties(bloc: dict | None) -> int:
    """Number of games of a position or of a move, draws included."""
    if not isinstance(bloc, dict):
        return 0
    return entier(bloc.get("white")) + entier(bloc.get("draws")) \
        + entier(bloc.get("black"))


def score_blancs(bloc: dict | None) -> float | None:
    """
    White's score on a move, as a percentage, a draw counting as half.
    """
    n = total_parties(bloc)
    # A missing block counts no game: the second test only tells it to
    # the type checker.
    if n == 0 or bloc is None:
        return None
    return 100.0 * (entier(bloc.get("white"))
                    + 0.5 * entier(bloc.get("draws"))) / n


def collecter_explorateur(partie: chess.pgn.Game, dossier: pathlib.Path,
                          explorateur: Explorateur, seuil_parties: int,
                          seuil_frequence: float, plafond_demicoups: int,
                          jusqu_a_epuisement: bool,
                          catalogue: Catalogue | None = None,
                          demicoups_min: int = 0) -> dict:
    """
    Walks through the game and queries the explorer position by position.

    For ply number i, it is the position BEFORE this move that is queried:
    it is the only way to get the rank and the frequency of the move
    actually played among the moves known to the database.

    Three stop criteria, in this order of testing:

      - an unusable answer, an answer without a list of moves included,
        or an empty sample, which means that the position is unknown to
        the database;
      - a position sample below `seuil_parties`;
      - leaving theory: a played move whose frequency falls below
        `seuil_frequence` and that leads to a position missing from the
        `catalogue`. A rare move that stays within a listed line does not
        leave theory.

    The third criterion is suspended during the first `demicoups_min`
    plies: the table thus covers the start of the game even after an
    early exit from theory, the first criterion and the game threshold
    staying active. Beyond that, the stop resumes at the first move that
    leaves. The first exit is recorded in every case, window included.

    Without a catalog and without a window, the behavior is the original
    one: any rare move leaves theory and stops the collection.

    With `jusqu_a_epuisement`, only the first criterion and the ply cap
    apply: the querying goes as deep as the database answers.

    A null move, "--" in the PGN, stops the collection before any query
    for this ply, whatever the mode: it is not a chess move, the database
    can neither count it nor follow the game beyond it. It is not held as
    leaving theory.

    A token refused, HTTP 401, stops the whole run with SystemExit: no
    other answer can come, and the engine would run for nothing.
    """
    brut = dossier / "explorer"
    brut.mkdir(parents=True, exist_ok=True)

    plateau = partie.board()
    coups = list(partie.mainline_moves())
    joues_uci: list[str] = []
    lignes: list[dict] = []
    non_exploitables: list[dict] = []
    premiere_sortie: dict | None = None
    arret: str | None = None

    for indice, coup in enumerate(coups):
        if indice >= plafond_demicoups:
            arret = ("cap of %d plies reached (option "
                     "--max-plies)" % plafond_demicoups)
            break

        numero = plateau.fullmove_number
        trait = "White" if plateau.turn == chess.WHITE else "Black"
        san_joue = plateau.san(coup)
        uci_joue = coup.uci()

        # Null move: the turn passes without a piece moving. The database
        # does not know it, so it came out with 0 games, at rank "hors
        # base", and passed for the first exit from theory. Worse, the
        # next ply sent the explorer a move list containing "0000",
        # which it rejects with an HTTP 400 ("illegal uci"): the stop
        # was then blamed on a network error. We stop here, without
        # asking anything, giving the real reason.
        if not coup:
            arret = ("null move at ply %d: it is not a chess move, the "
                     "explorer cannot follow the game beyond it"
                     % (indice + 1))
            journal("Explorer: %s." % arret)
            non_exploitables.append({
                "ply": indice + 1, "move_number": numero,
                "side_to_move": trait,
                "san": san_joue, "motif": "null move, not queried",
            })
            break

        # The explorer writes castling the Chess960 way, "king takes rook":
        # e1h1 for White's short castling, where python-chess writes e1g1.
        # Both forms are accepted to find the played move in the answer,
        # otherwise a castling move passed for absent from the database (0
        # games, rank "outside the database") and triggered a false exit
        # from theory.
        # For any other move, they are identical. The move list sent to
        # the explorer, for its part, does not change.
        uci_admis = (uci_joue, plateau.uci(coup, chess960=True))

        journal("Explorer: ply %d (%s)" % (indice + 1, san_joue))
        code, donnees = explorateur.interroger(joues_uci)

        # Systematic saving of the raw data, even on error: this will save
        # you from running the whole collection again to understand a failure.
        fichier = brut / ("%03d-%s.json" % (indice + 1, uci_joue))
        ecrire_texte(fichier,
                     json.dumps(donnees, ensure_ascii=False, indent=1))

        # A refused token: the explorer will answer nothing more, and
        # Stockfish then ran for minutes for a collection without its
        # opening statistics. Everything stops here, before the engine;
        # the answer stays in explorer/, the working folder with it.
        if code == 401:
            raise SystemExit(
                "Explorer: the token is refused (HTTP 401), it is wrong, "
                "expired or revoked. Replace it in its file (see "
                "--token-file), or run again with --no-explorer. Working "
                "folder kept: %s" % dossier)

        # An answer whose "moves" key is missing or is not a list cannot
        # tell whether the played move is known: it is unusable. It came
        # out with 0 games for the played move, and passed for an exit
        # from theory at 0.0 %.
        if code == 200 and not isinstance(donnees.get("moves"), list):
            code, donnees = 0, {"_error": "the \"moves\" key is missing or "
                                          "is not a list"}

        if code != 200:
            if code == 0:
                motif = "unusable answer: %s" % donnees.get("_error")
            else:
                motif = "HTTP %s" % code
            arret = "%s at ply %d" % (motif, indice + 1)
            journal("Explorer: %s, the collection stops." % arret)
            non_exploitables.append({
                "ply": indice + 1, "move_number": numero,
                "side_to_move": trait,
                "san": san_joue, "motif": motif,
            })
            break

        total = total_parties(donnees)

        # Position unknown to the database: the explorer answers 200 with an
        # empty sample, there is nothing more to get from it.
        if total == 0:
            arret = ("position unknown to the database at ply %d, "
                     "empty sample" % (indice + 1))
            journal("Explorer: %s." % arret)
            non_exploitables.append({
                "ply": indice + 1, "move_number": numero,
                "side_to_move": trait,
                "san": san_joue, "motif": "position missing from the "
                "database",
            })
            break

        if not jusqu_a_epuisement and total < seuil_parties:
            non_exploitables.append({
                "ply": indice + 1, "move_number": numero,
                "side_to_move": trait, "san": san_joue,
                "motif": "%d games, threshold %d" % (total, seuil_parties),
            })
            arret = ("insufficient sample at ply %d: %d games for a "
                     "threshold of %d"
                     % (indice + 1, total, seuil_parties))
            journal("Explorer: %s." % arret)
            break

        # Search for the played move among the moves known to the database.
        # Entries of an unexpected type are ignored rather than fatal.
        # A "moves" key that would not be a list is refused above as an
        # unusable answer; the test below stays as a safety net: an
        # integer cannot be iterated, and the loop then raised TypeError.
        coups_base = donnees.get("moves")
        if not isinstance(coups_base, list):
            coups_base = []
        liste = [e for e in coups_base if isinstance(e, dict)]
        rang = None
        bloc_joue = None
        for position, entree in enumerate(liste, start=1):
            if entree.get("uci") in uci_admis:
                rang, bloc_joue = position, entree
                break

        n_joue = total_parties(bloc_joue)
        frequence = 100.0 * n_joue / total

        majoritaire = liste[0] if liste else None
        n_majo = total_parties(majoritaire)

        ligne = {
            "ply": indice + 1,
            "move_number": numero,
            "side_to_move": trait,
            "parties_position": total,
            "san": san_joue,
            "uci": uci_joue,
            "rang": rang,
            "parties_coup": n_joue,
            "frequence": frequence,
            "score_blancs": score_blancs(bloc_joue),
            "majo_san": str(majoritaire.get("san", "?")) if majoritaire
            else None,
            "majo_parties": n_majo,
            "majo_frequence": 100.0 * n_majo / total,
            "majo_score_blancs": score_blancs(majoritaire),
        }
        lignes.append(ligne)

        plateau.push(coup)
        joues_uci.append(uci_joue)

        # Position reached after the move: does it belong to a line of the
        # catalog, and does it carry a name? Both keys always exist, so
        # that the summary does not have to test for their presence.
        ligne["connue"] = catalogue is not None and catalogue.connue(plateau)
        ligne["ouverture"] = (catalogue.nom(plateau) if catalogue is not None
                              else None)

        # Leaving theory: a rare move that leaves the catalog. The move
        # responsible does appear in the table, it is the querying that
        # stops after it, and never within the starting window.
        if (seuil_frequence > 0 and frequence < seuil_frequence
                and not ligne["connue"]):
            if premiere_sortie is None:
                premiere_sortie = dict(ligne)
            if not jusqu_a_epuisement and indice + 1 > demicoups_min:
                arret = ("exit from theory at ply %d: %s played at "
                         "%.1f %%, threshold %.1f %%%s"
                         % (indice + 1, san_joue, frequence, seuil_frequence,
                            ", outside the catalog" if catalogue is not None
                            else ""))
                journal("Explorer: %s." % arret)
                break

    if arret is None:
        arret = "end of the game"

    return {
        "lignes": lignes,
        "non_exploitables": non_exploitables,
        "premiere_sortie": premiere_sortie,
        "arret": arret,
        "seuil_parties": seuil_parties,
        "seuil_frequence": seuil_frequence,
        "jusqu_a_epuisement": jusqu_a_epuisement,
        "demicoups_min": demicoups_min,
        "catalogue": dict(catalogue.meta) if catalogue is not None else None,
    }


# ===========================================================================
# Stockfish
# ===========================================================================

def formater_score(score: chess.engine.PovScore,
                   trait: bool | None = None) -> str:
    """
    Formats a score from White's point of view, in pawns or as a mate.

    The score comes from a search made before the move, and the
    evaluation is announced after it. In pawns, this changes nothing. For
    a mate, the engine counts the moves of the mating side, the current
    move included: when that side is the one playing, given by `trait`, it has
    one fewer left once the move is played. "#+0" and "#-0" denote the
    mating move itself. The mated side, for its part, removes nothing:
    after its move, the opponent still has all of theirs to play.
    """
    blanc = score.white()
    # mate() gives None for a score in centipawns, as is_mate() tests it;
    # score() is then that number, mate_score only serving the type
    # checker, for which it could be None.
    coups = blanc.mate()
    if coups is not None:
        if trait is not None and (coups > 0) == (trait == chess.WHITE):
            coups += -1 if coups > 0 else 1
            if coups == 0:
                return "#+0" if trait == chess.WHITE else "#-0"
        return "#%+d" % coups
    return "%+.2f" % (blanc.score(mate_score=100000) / 100.0)


def valeur_pour_trait(score: chess.engine.PovScore, trait: bool) -> float:
    """
    Value in centipawns from the point of view of the side to move.

    A mate is brought down to a bounded value, enough to rank the moves
    without blowing up the losses displayed.
    """
    return float(score.pov(trait).score(mate_score=100000))


def ecart_au_meilleur(meilleur: float, joue: float) -> float:
    """
    What the played move loses compared with the engine's first choice,
    both values being taken from the point of view of the side to move.

    Two mates in the same direction cannot be compared in centipawns:
    mating in two moves instead of one, or getting mated one move later,
    does not change the outcome. Their bounded values, 99999 and 99998,
    gave a loss of 1, wrongly read as a centipawn: it is zero.
    """
    if min(abs(meilleur), abs(joue)) >= SEUIL_MAT and (meilleur > 0) == (
            joue > 0):
        return 0.0
    return meilleur - joue


def wdl_blancs(info: chess.engine.InfoDict) -> dict | None:
    """White's chances of winning, drawing and losing, per thousand."""
    wdl = info.get("wdl")
    if wdl is None:
        return None
    blancs = wdl.white()
    return {"win": blancs.wins, "draw": blancs.draws,
            "loss": blancs.losses}


def nature_coup(ecart: float | None) -> str | None:
    """Inaccuracy, mistake or blunder according to the loss in centipawns."""
    if ecart is None:
        return None
    if ecart >= SEUIL_GAFFE:
        return "blunder"
    if ecart >= SEUIL_ERREUR:
        return "mistake"
    if ecart >= SEUIL_IMPRECISION:
        return "inaccuracy"
    return None


def reste_estime(ecoule: float, faits: int, total: int) -> str:
    """
    Remaining time, from the average of the plies already analyzed.

    The endgame positions often go faster than the average: the estimate
    tends to err on the high side. Nothing is displayed before three
    plies, the average not making sense yet.
    """
    if faits < 3:
        return ""
    reste = ecoule / faits * (total - faits)
    if reste < 60:
        return ", less than a minute left"
    minutes = int(reste / 60 + 0.5)
    if minutes < 60:
        return ", about %d min left" % minutes
    return ", about %d h %02d left" % divmod(minutes, 60)


def resoudre_moteur(binaire: str) -> str:
    """
    Path of the engine as it will be checked and then started.

    The tilde is expanded, as for the other path options. A bare name,
    "stockfish", is looked up in the PATH: the start already looked for
    it there, while the check looked at the current directory, and the two
    could contradict each other.
    """
    binaire = os.path.expanduser(binaire)
    if os.sep not in binaire and not est_fichier(pathlib.Path(binaire)):
        return shutil.which(binaire) or binaire
    return binaire


def verifier_moteur(binaire: str) -> None:
    """Checks that the binary exists before anything has been created."""
    if not est_fichier(pathlib.Path(binaire)):
        raise SystemExit("Stockfish not found: %s. Install it (%s), or give "
                         "its path with --stockfish. The engine evaluation is "
                         "part of every collection."
                         % (binaire, AIDE_STOCKFISH))
    if not os.access(binaire, os.X_OK):
        raise SystemExit("Stockfish is not executable: %s" % binaire)


def lancer_moteur(binaire: str) -> chess.engine.SimpleEngine:
    """
    Starts the UCI engine and returns its driver, or stops the script.

    A binary that is not executable, missing, or not a UCI engine shows up
    respectively as an OSError, an OSError and a timeout while waiting for
    "uciok".
    """
    try:
        return chess.engine.SimpleEngine.popen_uci(binaire)
    except (OSError, TimeoutError, chess.engine.EngineError) as err:
        raise SystemExit("Cannot start the engine %s: %s"
                         % (binaire, str(err)
                            or "no UCI answer within the time limit")) from err


def fermer_moteur(moteur: chess.engine.SimpleEngine) -> None:
    """
    Stops the engine without ever raising an exception.

    quit() fails if the engine is already dead; close() is always safe
    and guarantees that no Stockfish process outlives the script.
    """
    try:
        moteur.quit()
    except Exception:  # noqa: BLE001 - last-resort cleanup
        pass
    moteur.close()


def verifier_options_moteur(binaire: str, fils: int, hachage: int,
                            multipv: int) -> None:
    """
    Checks --threads, --hash and --multipv with the engine itself, before
    any collection.

    The engine announces its options and their bounds as soon as it
    starts: a value out of bounds, or an option it does not know, is
    refused here rather than after the whole explorer phase, which may
    last several minutes. Nothing is configured, so no hash table is
    allocated: the engine is only started, queried, then stopped.
    """
    moteur = lancer_moteur(binaire)
    try:
        for drapeau, option, valeur in (("--threads", "Threads", fils),
                                        ("--hash", "Hash", hachage),
                                        ("--multipv", "MultiPV", multipv)):
            annonce = moteur.options.get(option)
            if annonce is None:
                raise SystemExit("The engine %s does not know the UCI option "
                                 "%s, required by %s."
                                 % (binaire, option, drapeau))
            mini, maxi = annonce.min, annonce.max
            if ((mini is not None and valeur < mini)
                    or (maxi is not None and valeur > maxi)):
                raise SystemExit("%s: %d is out of the bounds of the engine "
                                 "%s, which accepts %s to %s for %s."
                                 % (drapeau, valeur, binaire, mini, maxi,
                                    option))
    finally:
        fermer_moteur(moteur)


#: Start of a variation that python-chess writes for a Black move,
#: "8...Bg4", without a space after the dots.
RE_DEBUT_NOIR = re.compile(r"^(\d+)\.\.\.(?=\S)")


def variante_san(plateau: chess.Board, coups: list[chess.Move]) -> str:
    """
    Numbered algebraic notation of a variation, from the position.

    python-chess writes a variation that starts with a Black move
    "8...Bg4", while its export of the PGN and the examples of the prompt
    write "8... Bg4": the space is added, so that the tables written for
    the LLM follow the notation asked of it. The dots only appear at the
    start of a variation. A variation that cannot be replayed raises
    ValueError, as with variation_san.
    """
    return RE_DEBUT_NOIR.sub(r"\1... ", plateau.variation_san(coups))


def decrire_variante(plateau: chess.Board, info: chess.engine.InfoDict,
                     trait: bool) -> dict:
    """
    Formats a line returned by the engine: first move, score, numeric
    value for the side to move, depth reached and full principal
    variation, in UCI and in numbered algebraic notation.
    """
    pv = list(info.get("pv") or [])
    try:
        pv_san = variante_san(plateau, pv)
    except ValueError:
        # Variation that python-chess refuses to replay: we keep the raw UCI
        # rather than lose the information.
        pv_san = " ".join(m.uci() for m in pv)
    return {
        "san": plateau.san(pv[0]),
        "uci": pv[0].uci(),
        "score": formater_score(info["score"], trait),
        "value_for_side": valeur_pour_trait(info["score"], trait),
        "depth": info.get("depth"),
        "pv_uci": [m.uci() for m in pv],
        "pv_san": pv_san,
        "wdl": wdl_blancs(info),
    }


def collecter_stockfish(partie: chess.pgn.Game, dossier: pathlib.Path,
                        binaire: str, demicoups: int, profondeur: int,
                        multipv: int, fils: int, hachage: int) -> dict:
    """
    Evaluates the first plies of the game in multipv.

    For each position, the `multipv` best moves are requested, with their
    full principal variation. If the move actually played is not in this
    list, a second analysis restricted to that single move provides its
    evaluation and its variation, and therefore the real loss against the
    engine's first choice.
    """
    verifier_moteur(binaire)
    limite = chess.engine.Limit(depth=profondeur)
    plateau = partie.board()
    resultats: list[dict] = []
    coups = list(partie.mainline_moves())
    # Zero means "the whole game"; otherwise we bound it to the real number
    # of plies so that the counter displayed is exact.
    if demicoups <= 0 or demicoups > len(coups):
        demicoups = len(coups)

    # Start and start errors: see lancer_moteur.
    moteur = lancer_moteur(binaire)

    try:
        moteur.configure({"Threads": fils, "Hash": hachage})
        # Chances of winning, drawing and losing: an engine that does not know
        # this option simply leaves the column empty.
        wdl = "UCI_ShowWDL" in moteur.options
        if wdl:
            moteur.configure({"UCI_ShowWDL": True})
        journal("Stockfish: evaluation of %d plies, depth %d, multipv %d, "
                "threads %d. This is the longest phase."
                % (demicoups, profondeur, multipv, fils))
        debut = time.monotonic()
        for indice, coup in enumerate(coups[:demicoups]):
            trait = plateau.turn
            numero = plateau.fullmove_number
            san_joue = plateau.san(coup)
            fen = plateau.fen()

            journal("Stockfish: ply %d/%d (%s)%s"
                    % (indice + 1, demicoups, san_joue,
                       reste_estime(time.monotonic() - debut, indice,
                                    demicoups)))

            infos = moteur.analyse(plateau, limite, multipv=multipv)
            meilleurs = []
            for info in infos:
                if not info.get("pv") or "score" not in info:
                    continue
                meilleurs.append(decrire_variante(plateau, info, trait))

            eval_joue = None
            for m in meilleurs:
                if m["uci"] == coup.uci():
                    eval_joue = m
                    break
            if eval_joue is None and not coup:
                # Null move, "--" in the PGN: the turn passes without any
                # piece moving. It is not a chess move and the UCI protocol
                # cannot restrict a search to it: the search limited to
                # "0000" returned a score unrelated to it, hence a made-up
                # evaluation and loss. The line is kept, with the best
                # moves of the position, but the played move is not
                # evaluated.
                eval_joue = {
                    "san": san_joue, "uci": coup.uci(), "score": "-",
                    "value_for_side": None, "depth": None,
                    "pv_uci": [], "pv_san": "", "wdl": None,
                    "not_evaluated": True,
                }
            if eval_joue is None:
                info = moteur.analyse(plateau, limite, root_moves=[coup])
                if isinstance(info, list):
                    info = info[0]
                if "score" not in info:
                    raise SystemExit("The engine returned no evaluation for "
                                     "%s at ply %d."
                                     % (san_joue, indice + 1))
                if not info.get("pv"):
                    # A copy, as dict(info, pv=...) made: it keeps the
                    # type of the engine information.
                    info = info.copy()
                    info["pv"] = [coup]
                eval_joue = decrire_variante(plateau, info, trait)

            ecart = None
            if meilleurs and eval_joue["value_for_side"] is not None:
                ecart = ecart_au_meilleur(meilleurs[0]["value_for_side"],
                                          eval_joue["value_for_side"])

            resultats.append({
                "ply": indice + 1,
                "move_number": numero,
                "side_to_move": "White" if trait == chess.WHITE else "Black",
                "played": eval_joue,
                "best": meilleurs,
                "cp_loss": ecart,
                "category": nature_coup(ecart),
                "fen": fen,
            })
            plateau.push(coup)
        journal("Stockfish: done in %d min %02d s."
                % divmod(int(time.monotonic() - debut), 60))
    except chess.engine.EngineError as err:
        raise SystemExit("The engine failed during the analysis: %s"
                         % (err or type(err).__name__)) from err
    except concurrent.futures.CancelledError as err:
        # The engine died outside a search, during a setting for
        # example: python-chess then cancels the pending command instead
        # of raising an EngineError. The most common cause is a hash
        # table that the system refuses to allocate.
        raise SystemExit("The engine failed during the analysis: it stopped "
                         "without answering. If --hash or --threads are high, "
                         "memory may have run out.") from err
    finally:
        # Safe stop in every case: see fermer_moteur.
        fermer_moteur(moteur)

    brut = dossier / "stockfish"
    brut.mkdir(parents=True, exist_ok=True)
    ecrire_texte(brut / "evaluations.json",
                 json.dumps(resultats, ensure_ascii=False, indent=1))

    return {
        "resultats": resultats,
        "depth": profondeur,
        "multipv": multipv,
        "binaire": binaire,
        "wdl": wdl,
    }


# ===========================================================================
# Summary file
# ===========================================================================

def _cellule(valeur, gabarit="%.1f") -> str:
    """Formats a numeric value, or returns a dash if it is missing."""
    return "-" if valeur is None else gabarit % valeur


def resultat_contredit(partie: chess.pgn.Game,
                       resultats: list[dict]) -> str | None:
    """
    Sentence to write when the result of the game contradicts the
    evaluation of the engine after the last move, or None.

    A game scored 1-0 while Black is clearly better was not decided on
    the board: resignation, time out, or another cause that the PGN does
    not tell. Without this sentence, a hurried analyst tells the story of
    a deserved win: out of four LLMs tried, two did. The threshold is that
    of the blunder, to report only the clear cases, and nothing is said if
    the engine did not evaluate the last move.
    """
    vainqueur = {"1-0": "White", "0-1": "Black"}.get(
        partie.headers.get("Result", ""))
    if vainqueur is None or not resultats:
        return None
    dernier = resultats[-1]
    valeur = dernier["played"].get("value_for_side")
    # The rank of the ply is compared with the number of moves played,
    # counted right here, and not with a numbering taken from the PGN.
    joues = sum(1 for _ in partie.mainline_moves())
    if valeur is None or dernier["ply"] != joues:
        return None
    # value_for_side is read from the side of the one who has just played.
    pour_blancs = valeur if dernier["side_to_move"] == "White" else -valeur
    pour_vainqueur = pour_blancs if vainqueur == "White" else -pour_blancs
    if pour_vainqueur > -SEUIL_GAFFE:
        return None
    perdant = "Black" if vainqueur == "White" else "White"
    phrase = (
        "**Result and final evaluation contradict each other.** The game "
        "is scored `%s`, a win for %s, while Stockfish gives %s after the "
        "last move, %d%s %s, that is a clear advantage for %s. The result "
        "therefore does not come from the position on the board: "
        "resignation, time out, or another cause that the PGN does not "
        "tell."
        % (partie.headers["Result"], vainqueur, dernier["played"]["score"],
           dernier["move_number"],
           "." if dernier["side_to_move"] == "White" else "...",
           dernier["played"]["san"], perdant))
    fin = nettoyer_valeur(partie.headers.get("Termination", ""))
    if fin and fin != "?":
        phrase += " The Termination tag reads `%s`." % fin
    return phrase


def _ecart(ecart: float | None) -> str:
    """
    "CP loss" cell of the Stockfish table.

    A missing loss gives a dash. From SEUIL_ECART_MAT on, the loss comes
    from a mate brought down to a bounded value, whether the played move
    misses a mate or concedes one: the cell carries "mate" instead of a
    number of centipawns that would make no sense, the Eval and 1st
    columns giving both scores.

    The same goes below -SEUIL_ECART_MAT: the played move, evaluated by a
    search of its own, then finds a mate that the search of the best
    moves did not see, and the loss, negative, would have been written
    as some -99000 centipawns.
    """
    if ecart is None:
        return "-"
    if abs(ecart) >= SEUIL_ECART_MAT:
        return "mate"
    return "%.0f" % ecart


def pourcentages_entiers(valeurs: tuple[int, ...]) -> list[int] | None:
    """
    Whole percentages whose sum is exactly 100, by the largest remainder
    method: each share is rounded down, then the points missing go to
    the largest remainders, the first value winning a tie.

    Rounding each share on its own gave 101 or 99: 15, 970 and 15 per
    thousand gave 2/97/2, Python rounding 1.5 to 2, and 5, 990 and 5 gave
    0/99/0, 0.5 going to 0. Returns None if the values add up to nothing.
    """
    total = sum(valeurs)
    if total <= 0:
        return None
    parts = [v * 100 // total for v in valeurs]
    restes = [v * 100 % total for v in valeurs]
    # sorted is stable: between two equal remainders, the first value
    # comes first.
    ordre = sorted(range(len(valeurs)), key=lambda k: -restes[k])
    for k in ordre[:100 - sum(parts)]:
        parts[k] += 1
    return parts


def _gnp(wdl: dict | None, pour_noirs: bool = False) -> str:
    """
    Win, draw and loss as whole percentages adding up to 100, for White or
    for Black.

    The percentages are computed for White, then swapped for Black: the
    view of Black stays the mirror of that of White, ties included.
    """
    if not wdl:
        return "-"
    parts = pourcentages_entiers((entier(wdl["win"]), entier(wdl["draw"]),
                                  entier(wdl["loss"])))
    if parts is None:
        return "-"
    gain, nulle, perte = parts
    if pour_noirs:
        gain, perte = perte, gain
    return "%d/%d/%d" % (gain, nulle, perte)


def materiel_hors_pions(plateau: chess.Board) -> int:
    """Material other than pawns and kings of both sides together."""
    return sum(VALEUR_PIECES.get(c.lower(), 0) for c in plateau.board_fen())


def reperes_phase(partie: chess.pgn.Game) -> list[str]:
    """
    Objective markers of phase change on the main line: castling of each
    side, disappearance of the queens, entry into the endgame according
    to SEUIL_FINALE. They locate the transitions, the analyst judges them.
    """
    plateau = partie.board()
    roques: dict = {chess.WHITE: None, chess.BLACK: None}
    sans_dames = None
    finale = None
    for indice, coup in enumerate(partie.mainline_moves()):
        trait, numero = plateau.turn, plateau.fullmove_number
        if roques[trait] is None and plateau.is_castling(coup):
            roques[trait] = (indice + 1, numero, plateau.san(coup))
        plateau.push(coup)
        if (sans_dames is None
                and not plateau.pieces(chess.QUEEN, chess.WHITE)
                and not plateau.pieces(chess.QUEEN, chess.BLACK)):
            sans_dames = (indice + 1, numero)
        if finale is None and materiel_hors_pions(plateau) <= SEUIL_FINALE:
            finale = (indice + 1, numero, materiel_hors_pions(plateau))

    lignes = []
    for couleur, nom in ((chess.WHITE, "White"), (chess.BLACK, "Black")):
        r = roques[couleur]
        lignes.append("- %s castling: %s at move %d (ply %d)."
                      % (nom, r[2], r[1], r[0]) if r
                      else "- %s did not castle." % nom)
    lignes.append("- No queen left on the board after move %d "
                  "(ply %d)." % (sans_dames[1], sans_dames[0])
                  if sans_dames
                  else "- Queens remain on the board until the end.")
    lignes.append("- Entry into the endgame after move %d (ply %d), "
                  "material other than pawns of %d." % (finale[1], finale[0],
                                                        finale[2])
                  if finale else
                  "- No entry into the endgame according to this marker.")
    lignes.append("")
    lignes.append("Endgame marker: material other than pawns and kings of "
                  "both sides together at %d or less, with N = B = 3, "
                  "R = 5, Q = 9." % SEUIL_FINALE)
    return lignes


def cloture_de_bloc(texte: str) -> str:
    """
    Fence of the code block that holds the game in the short prompt: a
    run of backquotes longer than any run of the text, three at least.

    The game is pasted as it is. With a fixed fence of three backquotes,
    a comment of the PGN that held such a line closed the block: what
    followed it stood outside, among the instructions of the prompt.
    """
    plus_longue = max((len(suite) for suite in re.findall(r"`+", texte)),
                      default=0)
    return "`" * max(3, plus_longue + 1)


def tronquer_variante(plateau: chess.Board, pv_uci: list[str],
                      longueur: int) -> str:
    """
    Replays a UCI variation from the position and returns it in numbered
    algebraic notation, limited to `longueur` plies (0 = all).
    """
    coups = []
    for uci in pv_uci[:longueur] if longueur > 0 else pv_uci:
        try:
            coups.append(chess.Move.from_uci(uci))
        except ValueError:
            break
    try:
        return variante_san(plateau, coups)
    except ValueError:
        return " ".join(pv_uci)


def tableau_compact(partie: chess.pgn.Game, resultats: list[dict],
                    longueur_pv: int) -> str:
    """
    Engine evaluations for the short prompt: one line per ply, the played
    move and its evaluation. After a weak move come its category, its
    loss, then the best move, its continuation and its evaluation.

    The table of the summary has eleven columns and three variations per
    move: this one fits in a few kilobytes, for an LLM to which everything
    is pasted in a single message.
    """
    lignes = []
    plateau = partie.board()
    for r, coup in zip(resultats, partie.mainline_moves(), strict=False):
        tete = "%d%s %s" % (r["move_number"],
                            "." if r["side_to_move"] == "White" else "...",
                            r["played"]["san"])
        ligne = "%-13s %7s" % (tete, r["played"]["score"])
        if r.get("category") and r["best"]:
            meilleur = r["best"][0]
            ligne += "   %s (%s): better %s (%s)" % (
                r["category"], _ecart(r["cp_loss"]),
                tronquer_variante(plateau, meilleur["pv_uci"], longueur_pv),
                meilleur["score"])
        lignes.append(ligne.rstrip())
        plateau.push(coup)
    return "\n".join(lignes)


def coups_faibles_joueur(resultats: list[dict],
                         camp: str | None) -> int | None:
    """
    Number of the player's moves that the table of the short prompt marks
    as weak: inaccuracies, mistakes and blunders. None if their side is
    unknown.

    The rule is that of tableau_compact: a move is only marked if the
    engine found a category for it and suggests a better move. The number
    returned is therefore the one that the LLM can count by itself.
    """
    if camp is None:
        return None
    return sum(1 for r in resultats
               if r["side_to_move"] == camp and r.get("category")
               and r["best"])


def phrase_ouverture(explorateur: dict | None, libelle_base: str) -> str:
    """
    For the short prompt, the opening and the exit from theory in one
    sentence, taken from the explorer. Empty string if it gave nothing.
    """
    if explorateur is None:
        return ""
    sortie = explorateur["premiere_sortie"]
    limite = sortie["ply"] if sortie else len(explorateur["lignes"]) + 1
    nommees = [lg["ouverture"] for lg in explorateur["lignes"]
               if lg["ply"] < limite and lg.get("ouverture")]
    phrases = []
    if nommees:
        phrases.append("Opening: %s." % nommees[-1])
    if sortie:
        phrases.append(
            "Theory is left at move %d by %s, with %s, played in %s %% "
            "of the games of the %s database."
            % (sortie["move_number"], sortie["side_to_move"], sortie["san"],
               _cellule(sortie["frequence"]), libelle_base))
    return " ".join(phrases)


def consignes_joueur(contexte: str | None) -> str:
    """
    For the short prompt, what the player really specified: those of
    their answers to the startup questions that they did not leave at
    their default value. The side, stated elsewhere in the prompt, is not
    repeated, nor is the time control when it comes from the TimeControl
    tag or stays unknown: the player then specified nothing.
    """
    if contexte is None:
        return ""
    return "\n".join(
        ligne for ligne in contexte.split("\n")
        if ligne.startswith("- ") and not ligne.endswith("(default)")
        and not ligne.startswith(("- Player's side",
                                  "- Time control: TimeControl tag",
                                  "- Time control: unspecified")))


def ecrire_synthese(chemin: pathlib.Path, partie: chess.pgn.Game,
                    source: str, consignes: str | None,
                    explorateur: dict | None, motif_sans_explorateur: str | None,
                    stockfish: dict, longueur_pv: int,
                    libelle_base: str = "masters",
                    filtres: dict[str, str] | None = None,
                    annexes: list[str] | None = None,
                    pgn_complete: bool = False) -> None:
    """
    Assembles the summary file in markdown, in the expected order.

    `libelle_base` names the database queried in the titles and the text,
    the masters database by default. `filtres`, given only for the
    Lichess database, is
    reproduced in section 2 so that the analyst knows which population of
    games the frequencies are about. `annexes` adds to section 5 the files
    produced in addition, context.md for example, and `pgn_complete`
    reports a game.pgn whose headers were filled in.
    """
    out: list[str] = []
    a = out.append

    identifiant = partie.headers.get("Site", "").rstrip("/").split("/")[-1]
    if identifiant == "?":
        # python-chess gives "?" to a missing Site tag.
        identifiant = ""
    a("# Analysis folder: %s"
      % (nettoyer_valeur(identifiant) or "local game"))
    a("")
    a("Collected on %s. Source: `%s`."
      % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         masquer_maison(nettoyer_valeur(source))))
    a("This file contains no analysis, only collected data.")
    a("")

    # -- 0. Analysis instructions, if given ---------------------------------
    if consignes is not None:
        a("## Analysis instructions")
        a("")
        a("The instructions below come with the data: they describe the "
          "analysis expected from this folder.")
        a("")
        a(consignes.strip())
        a("")

    # -- 1. Headers and moves of the game -----------------------------------
    a("## 1. Headers and moves of the game")
    a("")
    a("| Field | Value |")
    a("|---|---|")
    for cle, valeur in partie.headers.items():
        a("| %s | %s |" % (cle, nettoyer_valeur(valeur).replace("|", "\\|")))
    a("")
    a("Number of plies in the main line: %d."
      % len(list(partie.mainline_moves())))
    a("")
    # The main line is reproduced without comments or variations, so
    # that this single file is enough for the analysis. The raw PGN, with
    # its possible original comments, stays in game.pgn.
    exporteur = chess.pgn.StringExporter(headers=False, comments=False,
                                         variations=False, columns=78)
    a("```")
    a(partie.accept(exporteur).strip())
    a("```")
    a("")
    # Phase markers, computed from castling and material: they locate
    # the ends of phases that the analyst must comment on.
    a("Phase markers, for guidance:")
    a("")
    for ligne in reperes_phase(partie):
        a(ligne)
    a("")

    # -- 2. Exit from theory ------------------------------------------------
    a("## 2. Explorer of the %s database, exit from theory" % libelle_base)
    a("")
    if explorateur is None:
        a("Explorer collection not done: %s."
          % (motif_sans_explorateur or "disabled"))
        a("")
    else:
        if filtres:
            # Lichess database: the frequencies depend entirely on the
            # filtered population, the analyst must know it.
            a("Database queried: **Lichess**, rated games of all the "
              "players of the site, and not the masters database. "
              "Speeds: `%s`. Rating bands: `%s` (average of the two "
              "players; each band runs from its value to the next one, "
              "`0` covers 0 to 999, `2500` everything above). Games "
              "played since: `%s`."
              % (filtres.get("speeds", "all"),
                 filtres.get("ratings", "all"),
                 filtres.get("since", "the start")))
            a("")
        a("The database of the explorer is indexed **by position** and not "
          "by order of the moves. Transpositions are therefore merged, and "
          "the number of games may very well **increase** from one ply to "
          "the next. Do not read the column of the games as a decreasing "
          "sequence.")
        a("")
        if explorateur["jusqu_a_epuisement"]:
            a("Mode `--exhaustive`: no threshold was applied, the querying "
              "went as deep as the database answered.")
        else:
            a("Thresholds applied: stop below **%d games** for the "
              "position, and stop below **%.1f %%** of frequency for the "
              "move played%s."
              % (explorateur["seuil_parties"], explorateur["seuil_frequence"],
                 ", unless this move stays within a line of the catalog of "
                 "named openings" if explorateur.get("catalogue")
                 else ""))
            if explorateur.get("demicoups_min", 0) > 0:
                a("")
                a("Starting window (`--min-moves`): no stop on frequency "
                  "before the end of move %d (ply %d), the threshold of "
                  "games staying active. The table may therefore go on "
                  "after the first exit from theory."
                  % ((explorateur["demicoups_min"] + 1) // 2,
                     explorateur["demicoups_min"]))
        cat = explorateur.get("catalogue")
        if cat:
            a("")
            a("Catalog of the Lichess openings, downloaded on %s: %s "
              "named positions, %s known positions counting the "
              "intermediate positions of the lines. The Opening column "
              "names the position reached by the move played; "
              "`(intermediate)` marks a position along a named line, `-` "
              "a position outside the catalog."
              % (cat.get("date", "?"), cat.get("named", "?"),
                 cat.get("known", "?")))
        a("")
        a("| # | Move | Side | Pos. games | Played | Rank | Freq. | "
          "White score | Top move | Top freq. | Top White score | "
          "Opening |")
        a("|---:|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|")
        for lg in explorateur["lignes"]:
            if lg.get("ouverture"):
                ouverture = lg["ouverture"].replace("|", "\\|")
            elif lg.get("connue"):
                ouverture = "(intermediate)"
            else:
                ouverture = "-"
            a("| %d | %d | %s | %d | %s | %s | %s %% | %s | %s | %s %% | %s "
              "| %s |"
              % (lg["ply"], lg["move_number"], lg["side_to_move"],
                 lg["parties_position"], lg["san"],
                 "-" if lg["rang"] is None else str(lg["rang"]),
                 _cellule(lg["frequence"]),
                 _cellule(lg["score_blancs"], "%.1f %%"),
                 lg["majo_san"] or "-",
                 _cellule(lg["majo_frequence"]),
                 _cellule(lg["majo_score_blancs"], "%.1f %%"),
                 ouverture))
        a("")
        a("Stop of the querying: %s." % explorateur["arret"])
        a("")

        ps = explorateur["premiere_sortie"]
        a("### First exit from theory")
        a("")
        hors_cat = (" outside the catalog" if explorateur.get("catalogue")
                    else "")
        if ps is None:
            a("No move queried goes below the threshold of %.1f %%%s."
              % (explorateur["seuil_frequence"], hors_cat))
        else:
            a("First move below the threshold of %.1f %%%s: **%s plays "
              "%s** at move **%d** (ply %d)."
              % (explorateur["seuil_frequence"], hors_cat, ps["side_to_move"],
                 ps["san"], ps["move_number"], ps["ply"]))
            a("")
            # Last named opening before the exit: it locates, for the
            # analyst, the theoretical line that the game has just left.
            nommees = [lg["ouverture"] for lg in explorateur["lignes"]
                       if lg["ply"] < ps["ply"]
                       and lg.get("ouverture")]
            if nommees:
                a("- last named position before the exit: %s"
                  % nommees[-1])
            a("- frequency of the move played: %s %% (%d games out of %d)"
              % (_cellule(ps["frequence"]), ps["parties_coup"],
                 ps["parties_position"]))
            a("- rank among the answers: %s"
              % ("outside the database" if ps["rang"] is None
                 else ps["rang"]))
            a("- most played move: %s at %s %%"
              % (ps["majo_san"] or "-", _cellule(ps["majo_frequence"])))
        a("")

    # -- 3. Stockfish -------------------------------------------------------
    a("## 3. Stockfish evaluations")
    a("")
    a("Engine: `%s`, depth %d, multipv %d, %d plies covered out of %d. "
      "The evaluations are given **from White's point of view**. The "
      "loss is given in centipawns **from the point of view of the side "
      "to move**: positive, it measures what the move played loses "
      "against the first choice of the engine. Negative, it reports no "
      "fault: the move played, evaluated apart when it is not among the "
      "first choices, comes out slightly above the first one, and the "
      "two are worth the same."
      % (masquer_maison(stockfish["binaire"]), stockfish["depth"],
         stockfish["multipv"], len(stockfish["resultats"]),
         len(list(partie.mainline_moves()))))
    a("")
    a("Category: inaccuracy from a loss of %d cp, mistake from %d, "
      "blunder from %d."
      % (SEUIL_IMPRECISION, SEUIL_ERREUR, SEUIL_GAFFE))
    if any(r["played"].get("not_evaluated") for r in stockfish["resultats"]):
        a("Null move `--`: the turn passes without a piece moving. It is "
          "not a chess move, the engine does not evaluate it: its Eval, "
          "W/D/L, CP loss and Category columns carry `-`, the best moves "
          "of the position being still given.")
    a("Mate: `#+2`, White mates in two moves, `#-1`, Black mates in one "
      "move. Like any evaluation of this table, the count reads after "
      "the move of the line: `#+0` or `#-0`, this move gives mate.")
    a("CP loss `mate`: one of the two scores compared is a mate, whether "
      "the move played misses a mate, concedes one, or finds one that the "
      "search of the best moves did not see; the loss is not counted in "
      "centipawns, compare the Eval and 1st columns.")
    if stockfish.get("wdl"):
        a("W/D/L: White's chances of a win, a draw and a loss after the "
          "move played, in whole percentages adding up to 100, according "
          "to the model of Stockfish. This model reflects the play of the "
          "engine: read it as a trend, not as the real probability between "
          "two human players.")
    a("")
    a("| # | Move | Side | Played | Eval | W/D/L | CP loss | Category "
      "| 1st | 2nd | 3rd |")
    a("|---:|---:|---|---|---:|---:|---:|---|---|---|---|")
    for r in stockfish["resultats"]:
        trois = list(r["best"][:3])
        while len(trois) < 3:
            trois.append(None)
        colonnes = ["-" if m is None else "%s (%s)" % (m["san"], m["score"])
                    for m in trois]
        a("| %d | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
          % (r["ply"], r["move_number"], r["side_to_move"], r["played"]["san"],
             r["played"]["score"], _gnp(r["played"].get("wdl")),
             _ecart(r["cp_loss"]),
             r.get("category") or "-",
             colonnes[0], colonnes[1], colonnes[2]))
    a("")

    # Result contrary to the final evaluation: stated here, under the
    # table, so that the analyst does not tell the story of a deserved win.
    contradiction = resultat_contredit(partie, stockfish["resultats"])
    if contradiction:
        a(contradiction)
        a("")

    # The principal variations, replayed from each position, so
    # that the analyst has concrete lines computed by the engine
    # and does not have to make them up. The full variations are
    # in stockfish/evaluations.json.
    a("### 3a. Principal variations of the engine")
    a("")
    if longueur_pv > 0:
        a("Variations cut at %d plies; the full variations are in "
          "`stockfish/evaluations.json`." % longueur_pv)
    else:
        a("Full variations, as returned by the engine.")
    a("")
    plateau = partie.board()
    for r, coup in zip(stockfish["resultats"], partie.mainline_moves(),
                       strict=False):
        a("- Ply %d, %s plays %s (position before the move)"
          % (r["ply"], r["side_to_move"], r["played"]["san"]))
        joue_dans_liste = False
        for k, m in enumerate(r["best"]):
            etiquette = ordinal(k + 1)
            if m["uci"] == r["played"]["uci"]:
                etiquette += ", played"
                joue_dans_liste = True
            a("    - %s (%s): %s" % (etiquette, m["score"],
                                     tronquer_variante(
                                         plateau, m["pv_uci"],
                                         longueur_pv)))
        if r["played"].get("not_evaluated"):
            a("    - played: null move, not evaluated by the engine")
        elif not joue_dans_liste:
            a("    - played (%s): %s" % (r["played"]["score"],
                                         tronquer_variante(
                                             plateau, r["played"]["pv_uci"],
                                             longueur_pv)))
        plateau.push(coup)
    a("")

    # Ranking: the moves that cost the most, per side, with what should
    # have been played and the FEN, direct material for the mandatory
    # comments and the positions to review.
    a("### 3b. Mistakes and blunders by side")
    a("")
    a("Moves whose loss reaches %d cp, from the costliest to the least "
      "costly, %d at most per side; the inaccuracies stay in the table. "
      "The W/D/L chances are those of the side to move, the FEN that of "
      "the position before the move."
      % (SEUIL_ERREUR, PALMARES_MAX))
    a("")
    for camp in ("White", "Black"):
        fautes = sorted((r for r in stockfish["resultats"]
                         if r["side_to_move"] == camp
                         and r["cp_loss"] is not None
                         and r["cp_loss"] >= SEUIL_ERREUR),
                        key=lambda r: -r["cp_loss"])
        a("**%s**" % camp)
        a("")
        if not fautes:
            a("- No mistake and no blunder.")
        pour_noirs = camp == "Black"
        for r in fautes[:PALMARES_MAX]:
            meilleur = r["best"][0] if r["best"] else None
            # From SEUIL_ECART_MAT on, the loss comes from a mate brought down
            # to a bounded value: the figure no longer makes sense, the
            # scores speak for themselves.
            ecart = ("loss of %.0f cp" % r["cp_loss"]
                     if r["cp_loss"] < SEUIL_ECART_MAT else
                     "loss linked to a mate, %s instead of %s"
                     % (r["played"]["score"],
                        meilleur["score"] if meilleur else "?"))
            a("- Move %d, %s plays %s (ply %d): %s, %s."
              % (r["move_number"], r["side_to_move"], r["played"]["san"],
                 r["ply"], r["category"], ecart))
            if meilleur is not None:
                a("  Best move: %s (%s), line %s."
                  % (meilleur["san"], meilleur["score"],
                     tronquer_variante(chess.Board(r["fen"]),
                                       meilleur["pv_uci"], longueur_pv)))
                if meilleur.get("wdl") and r["played"].get("wdl"):
                    a("  W/D/L chances: %s with the best move, %s after "
                      "the move played."
                      % (_gnp(meilleur["wdl"], pour_noirs),
                         _gnp(r["played"]["wdl"], pour_noirs)))
            a("  FEN: `%s`" % r["fen"])
        if len(fautes) > PALMARES_MAX:
            a("- %d more, see the table."
              % (len(fautes) - PALMARES_MAX))
        a("")

    # -- 4. Unusable positions ----------------------------------------------
    a("## 4. Positions with an unusable sample")
    a("")
    if explorateur is None:
        a("Not applicable, explorer collection not done.")
    elif not explorateur["non_exploitables"]:
        a("None: the querying stopped for another reason (%s)."
          % explorateur["arret"])
    else:
        a("| # | Move | Side | Move played | Reason |")
        a("|---:|---:|---|---|---|")
        for n in explorateur["non_exploitables"]:
            a("| %d | %d | %s | %s | %s |"
              % (n["ply"], n["move_number"], n["side_to_move"], n["san"],
                 n["motif"]))
        a("")
        a("Beyond this point, the %s database says nothing usable any "
          "more: any statement about theory will have to come from "
          "elsewhere." % libelle_base)
    a("")

    # -- 5. Reminder of the raw data ----------------------------------------
    a("## 5. Raw data of the archive")
    a("")
    if pgn_complete:
        a("- `game.pgn`: the game with its headers filled in, re-exported "
          "by python-chess, original comments included.")
    else:
        a("- `game.pgn`: the source PGN, with its original comments.")
    for annexe in annexes or []:
        a(annexe)
    if explorateur is not None:
        # Without the explorer, the archive does not have this folder:
        # announcing it would send the analyst looking for files that do not
        # exist.
        a("- `explorer/NNN-<uci>.json`: one raw answer per ply queried, "
          "numbered in the order of the game.")
    a("- `stockfish/evaluations.json`: the full engine evaluations, "
      "with the whole principal variation of each move, in UCI and in "
      "algebraic notation.")
    a("- `collection.json`: the exact parameters of this collection.")
    a("")

    ecrire_texte(chemin, "\n".join(out) + "\n")


# ===========================================================================
# Final archive
# ===========================================================================

def chemin_archive(dossier: pathlib.Path) -> pathlib.Path:
    """
    Path of the archive of a working folder: its name followed by ".zip".

    The name is built by appending and not with with_suffix(), which
    replaces everything after the last dot: for a PGN named
    "game-2026.11.18.pgn", the folder "analysis-game-2026.11.18-..."
    gave "analysis-game-2026.11.zip", whereas shutil.make_archive does
    write "<folder>.zip".
    """
    return dossier.with_name(dossier.name + ".zip")


def archiver(dossier: pathlib.Path, garder: bool) -> pathlib.Path:
    """
    Compresses the working folder into a zip, checks it, then deletes it.

    The folder is only destroyed if the archive reads back without error
    and does contain the summary. When in doubt, everything is kept and
    reported.

    The archive is first written under a temporary name,
    ".<folder>.partial.zip", next to the folder; it only takes its final
    name once checked. An interruption (Ctrl-C) or a failure therefore
    never leaves a truncated zip under the name of an archive: the
    temporary archive is removed, the working folder stays.
    """
    archive = chemin_archive(dossier)
    if archive.exists():
        raise SystemExit("The archive %s already exists, folder kept."
                         % archive)

    # Base of the temporary name: shutil.make_archive appends ".zip" to it.
    # The paths stored in the zip only depend on base_dir, they stay those
    # of the working folder.
    base_partielle = dossier.with_name(".%s.partial" % dossier.name)
    partielle = chemin_archive(base_partielle)

    journal("Creating the archive: %s" % archive)
    try:
        try:
            shutil.make_archive(str(base_partielle), "zip",
                                root_dir=dossier.parent,
                                base_dir=dossier.name)
        except (OSError, shutil.Error) as err:
            raise SystemExit("Failed to create the archive, folder kept: "
                             "%s" % err) from err

        try:
            with zipfile.ZipFile(partielle) as z:
                corrompu = z.testzip()
                noms = z.namelist()
        except (OSError, zipfile.BadZipFile) as err:
            raise SystemExit("Unreadable archive, folder kept: %s"
                             % err) from err

        attendu = "%s/summary.md" % dossier.name
        if corrompu is not None or attendu not in noms:
            raise SystemExit("Incomplete or corrupt archive (%s), folder "
                             "kept." % (corrompu or "summary missing"))

        # Renaming within the same directory: the archive appears all at
        # once, complete and checked.
        try:
            partielle.replace(archive)
        except OSError as err:
            raise SystemExit("Valid archive but cannot rename it to %s, "
                             "folder kept: %s"
                             % (archive, err)) from err
    except BaseException:
        # Any stop before the renaming, Ctrl-C included, removes the
        # temporary archive and then goes up unchanged: the working folder,
        # for its part, is kept for diagnosis.
        with contextlib.suppress(OSError):
            partielle.unlink()
        raise

    if garder:
        journal("Folder kept on request: %s" % dossier)
        return archive

    try:
        shutil.rmtree(dossier)
    except OSError as err:
        raise SystemExit("Valid archive but cannot delete the folder: "
                         "%s" % err) from err
    journal("Working folder deleted.")
    return archive


# ===========================================================================
# Command line
# ===========================================================================

EXEMPLES = """\
usage examples
--------------

  First installation, only once:

      %s
      %s
      ./ianalyze.py --install-venv
      ./ianalyze.py --install-catalog

  Running --install-catalog again from time to time updates the
  opening catalog.

  Common use, on a local PGN:

      ./ianalyze.py my-game.pgn

  On a Lichess game, by URL or by identifier:

      ./ianalyze.py https://lichess.org/<identifier>
      ./ianalyze.py <identifier>

  Without any question, for example from another script, or with all your
  player names so that your side is deduced from the headers:

      ./ianalyze.py my-game.pgn --no-questions
      ./ianalyze.py my-game.pgn --usernames MyUsername,OtherUsername

  For a single run that leaves your settings aside, for example on a
  friend's game, neither reading nor writing the settings file:

      ./ianalyze.py friend-game.pgn --no-settings

  Going as deep as the database answers, without any threshold:

      ./ianalyze.py my-game.pgn --exhaustive

  The database of all Lichess players is queried by default, with the
  filters of https://lichess.org/opening. Restricting it to some speeds
  and rating bands, or querying the masters database:

      ./ianalyze.py my-game.pgn \\
          --speeds rapid,classical,correspondence --ratings 0,1000
      ./ianalyze.py my-game.pgn --database masters

  Covering the first ten moves whatever the frequency of the moves played,
  or on the contrary stopping at the first exit from theory:

      ./ianalyze.py my-game.pgn --min-moves 10
      ./ianalyze.py my-game.pgn --min-moves 0

  Engine only, without network or token:

      ./ianalyze.py my-game.pgn --no-explorer

  Keeping the working folder next to the archive:

      ./ianalyze.py my-game.pgn --keep-folder

  For an LLM that does not open zip files or run code: a short prompt
  that carries the game and the evaluations, to be pasted alone. No
  archive is written:

      ./ianalyze.py my-game.pgn --prompt-only

  Using your own prompt template, or writing no prompt:

      ./ianalyze.py my-game.pgn --prompt ~/my-template.txt
      ./ianalyze.py my-game.pgn --no-prompt

  Deeper engine, or limited to the first fifteen moves:

      ./ianalyze.py my-game.pgn --depth 22
      ./ianalyze.py my-game.pgn --stockfish-moves 15

result
------

  An archive analysis-<label>-<YYYYMMDD-HHMMSS>.zip in the output
  directory, containing summary.md and the raw data. The path of the
  archive is written alone on standard output, everything else goes to
  standard error. On failure, the working folder is kept as it is for
  diagnosis.

  Next to the archive, the analysis prompt of the game, under the name
  analysis-<label>-<YYYYMMDD-HHMMSS>.prompt.txt: paste it into the
  conversation, with the archive as an attachment. It is drawn from the
  template prompt-template.txt, kept next to the script, which you can
  edit.

prerequisites
-------------

  %s
  %s

  python-chess is not packaged by Debian. The --install-venv option
  creates a dedicated virtual environment and installs the module in it.
  By default:
  %s
  The script then restarts in it by itself, you can keep calling it with
  the system's python.

  The catalog of the named openings of Lichess (public domain, CC0) is
  kept locally in %s,
  installed and updated by --install-catalog. It is not required
  with --no-explorer.

  The personal Lichess token is read from %s, in mode 600,
  this file containing only the token. It never appears in the output,
  nor in the files produced, nor in the command line.

  Your username, your usual time control and your rating are asked only
  once, on the first run in a terminal, then kept in
  %s, which you can edit by hand.

  No other dependency: HTTP goes through urllib from the standard
  library, the archive through zipfile. The stockfish package is
  mandatory, the engine is driven over UCI.
""" % (CMD_PAQUET_VENV, CMD_PAQUET_STOCKFISH,
       CMD_PAQUET_VENV, CMD_PAQUET_STOCKFISH,
       VENV_DEFAUT, CATALOGUE_DEFAUT, JETON_DEFAUT,
       os.path.join(DOSSIER_APPLICATION, REGLAGES_DEFAUT))


def valider_liste(p: argparse.ArgumentParser, option: str, valeur: str,
                  admises: tuple[str, ...]) -> str:
    """
    Checks a comma-separated list and returns it normalized.

    Case is tolerated on input ("ultrabullet" is accepted) but the value
    passed on uses the exact spelling of the API. Stray spaces and
    duplicates are removed, and the list is put back in the order of the
    enumeration, so that collection.json and the summary stay comparable
    from one collection to the next. An unknown value is rejected here,
    before any folder is created, rather than finding out its effect at
    the first ply queried.
    """
    canoniques = {v.lower(): v for v in admises}
    retenues: list[str] = []
    for brut in valeur.split(","):
        element = brut.strip()
        if not element:
            continue
        canonique = canoniques.get(element.lower())
        if canonique is None:
            p.error("%s: unknown value \"%s\", accepted values: %s"
                    % (option, element, ", ".join(admises)))
        if canonique not in retenues:
            retenues.append(canonique)
    if not retenues:
        p.error("%s: empty list" % option)
    retenues.sort(key=admises.index)
    return ",".join(retenues)


#: Key of each option in collection.json: the English name of the option,
#: without its dashes. The dest of argparse stay French in the code,
#: the archive is in English. A test checks that every option has its
#: key: a dest missing from this table would stop the collection.
CLEFS_COLLECTE = {
    "source": "source",
    "installer_venv": "install_venv",
    "venv": "venv",
    "sans_questions": "no_questions",
    "pseudos": "usernames",
    "reglages": "settings",
    "sans_reglages": "no_settings",
    "purge_reglages": "purge_settings",
    "installer_catalogue": "install_catalog",
    "catalogue": "catalog",
    "sortie": "output_dir",
    "garder_dossier": "keep_folder",
    "prompt": "prompt",
    "sans_prompt": "no_prompt",
    "prompt_seul": "prompt_only",
    "base": "database",
    "cadences": "speeds",
    "classements": "ratings",
    "jeton_fichier": "token_file",
    "seuil_parties": "min_games",
    "seuil_frequence": "min_frequency",
    "jusqu_a_epuisement": "exhaustive",
    "coups_min": "min_moves",
    "max_demicoups": "max_plies",
    "pause": "pause",
    "sans_explorateur": "no_explorer",
    "coups_stockfish": "stockfish_moves",
    "profondeur": "depth",
    "multipv": "multipv",
    "fils": "threads",
    "hachage": "hash",
    "stockfish": "stockfish",
    "longueur_pv": "pv_length",
    "delai": "timeout",
    "debug": "debug",
}


def analyser_arguments(argv: list[str]) -> argparse.Namespace:
    """Defines and reads the command line options."""
    p = argparse.ArgumentParser(
        prog="ianalyze.py",
        # The line breaks are written here: with this formatter, argparse
        # does not wrap the description, which fitted on a line of 250
        # columns.
        description="Gathers the material for the analysis of a chess game: "
                    "PGN, statistics\n"
                    "of the Lichess explorer (database of all players, or "
                    "masters database\n"
                    "with --database masters) to find the exit from theory, "
                    "and Stockfish\n"
                    "evaluations of the game. Produces no analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXEMPLES)

    p.add_argument("source", nargs="?",
                   help="local PGN file, Lichess URL, or game identifier of "
                        "eight or twelve characters")

    g = p.add_argument_group("virtual environment")
    g.add_argument("--install-venv", dest="installer_venv",
                   action="store_true",
                   help="creates the virtual environment if it is missing, "
                        "installs python-chess in it, then exits")
    g.add_argument("--venv", default=VENV_DEFAUT, metavar="PATH",
                   help="location of the virtual environment (default: "
                        "%(default)s)")

    g = p.add_argument_group("startup questions")
    g.add_argument("--no-questions", dest="sans_questions",
                   action="store_true",
                   help="asks no question, neither side nor context; implied "
                        "outside an interactive terminal")
    g.add_argument("--usernames", dest="pseudos", default=None, metavar="LIST",
                   help="your player names, comma-separated, looked up "
                        "ignoring case in White and Black to deduce your "
                        "side, each one as the whole name or as a run of "
                        "its words, not as a part of a word (default: those "
                        "of your settings)")
    # --settings and --no-settings exclude each other: argparse refuses
    # the pair whatever the order, the spelling (--settings=FILE) or the
    # path given, even the default one.
    m = g.add_mutually_exclusive_group()
    m.add_argument("--settings", dest="reglages",
                   default=REGLAGES_DEFAUT, metavar="NAME",
                   help="name of the settings file, ending in .ini, not "
                        "starting with a dot, and kept in the folder of the "
                        "application, where your "
                        "username, your usual time control and your rating "
                        "are kept, asked only once in a terminal (default: "
                        "%(default)s)")
    m.add_argument("--no-settings", dest="sans_reglages",
                   action="store_true",
                   help="for this run only, neither reads nor writes the "
                        "settings file, nor asks its questions: your side is "
                        "asked, or deduced from --usernames, and your rating "
                        "read from the Elo tags of the game")
    g.add_argument("--purge-settings", dest="purge_reglages",
                   action="store_true",
                   help="deletes the settings file, the one of --settings if "
                        "given, then exits; your answers will be asked again "
                        "at the next collection")

    g = p.add_argument_group("opening catalog")
    g.add_argument("--install-catalog", dest="installer_catalogue",
                   action="store_true",
                   help="downloads or updates the catalog of the named "
                        "openings of Lichess, validates it, then exits")
    g.add_argument("--catalog", dest="catalogue",
                   default=CATALOGUE_DEFAUT, metavar="DIR",
                   help="directory of the local catalog (default: "
                        "%(default)s)")

    g = p.add_argument_group("output")
    g.add_argument("--output-dir", dest="sortie", default=".", metavar="DIR",
                   help="directory where the archive is written (default: "
                        "%(default)s)")
    g.add_argument("--keep-folder", dest="garder_dossier", action="store_true",
                   help="does not delete the working folder after the archive "
                        "is created, or the prompt with --prompt-only")
    g.add_argument("--prompt", metavar="FILE",
                   help="template of the analysis prompt, written next to the "
                        "archive under the name <archive>%s (default: %s next "
                        "to the script)" % (PROMPT_SUFFIXE, PROMPT_MODELE))
    g.add_argument("--no-prompt", dest="sans_prompt", action="store_true",
                   help="does not write the analysis prompt")
    g.add_argument("--prompt-only", dest="prompt_seul", action="store_true",
                   help="writes a short prompt that carries the game and the "
                        "Stockfish evaluations, to be pasted alone into the "
                        "conversation, without an attachment: for an LLM that "
                        "does not open zip files or run code. Its template is "
                        "%s. No archive is written, and the working folder is "
                        "deleted, except with "
                        "--keep-folder" % PROMPT_SEUL_MODELE)

    g = p.add_argument_group("explorer")
    g.add_argument("--database", dest="base",
                   choices=sorted(BASES_EXPLORATEUR),
                   default="lichess",
                   help="database queried: lichess, the rated games of all "
                        "the players of the site, the one of "
                        "https://lichess.org/opening, or masters (default: "
                        "%(default)s)")
    g.add_argument("--speeds", dest="cadences", metavar="LIST",
                   help="with --database lichess, speeds kept, "
                        "comma-separated, among: %s (default: %s)"
                        % (", ".join(CADENCES_LICHESS), CADENCES_DEFAUT))
    g.add_argument("--ratings", dest="classements", metavar="LIST",
                   help="with --database lichess, rating bands kept, "
                        "comma-separated, among: %s; 0 covers 0 to 999, 2500 "
                        "everything above (default: %s)"
                        % (", ".join(CLASSEMENTS_LICHESS),
                           CLASSEMENTS_DEFAUT))
    g.add_argument("--token-file", dest="jeton_fichier",
                   default=JETON_DEFAUT, metavar="FILE",
                   help="file containing the personal token (default: "
                        "%(default)s)")
    g.add_argument("--min-games", dest="seuil_parties",
                   type=int, default=50, metavar="N",
                   help="stop below N games for the position (default: "
                        "%(default)s)")
    g.add_argument("--min-frequency", dest="seuil_frequence",
                   type=float, default=10.0, metavar="P",
                   help="stop as soon as the played move falls below P "
                        "percent of frequency and leaves the opening catalog, "
                        "0 to disable this criterion (default: %(default)s)")
    g.add_argument("--exhaustive", dest="jusqu_a_epuisement",
                   action="store_true",
                   help="ignores both thresholds and queries the database as "
                        "long as it answers, the stop then only happening on "
                        "an HTTP error, on a position missing from the "
                        "database, on a null move, at the --max-plies cap "
                        "or at the end of the game")
    g.add_argument("--min-moves", dest="coups_min",
                   type=int, default=6, metavar="N",
                   help="no stop on frequency before the end of move N, the "
                        "game threshold staying active; the table thus covers "
                        "the start of the game even after an early exit from "
                        "theory, 0 to stop at the first exit (default: "
                        "%(default)s)")
    g.add_argument("--max-plies", dest="max_demicoups",
                   type=int, default=60, metavar="N",
                   help="cap on the plies queried, a safeguard always active "
                        "(default: %(default)s)")
    g.add_argument("--pause", type=float, default=2.0, metavar="S",
                   help="pause between two requests, in seconds, minimum 2 "
                        "required by the API (default: %(default)s)")
    g.add_argument("--no-explorer", dest="sans_explorateur",
                   action="store_true",
                   help="skips the explorer collection entirely")

    g = p.add_argument_group("engine")
    g.add_argument("--stockfish-moves", dest="coups_stockfish",
                   type=int, default=0, metavar="N",
                   help="limits the engine analysis to the first N full "
                        "moves, that is 2N plies; 0 analyzes the whole game "
                        "(default: %(default)s)")
    g.add_argument("--depth", dest="profondeur",
                   type=int, default=18, metavar="D",
                   help="search depth, from 1 to 60 (default: %(default)s)")
    g.add_argument("--multipv", type=int, default=3, metavar="K",
                   help="number of variations requested per position "
                        "(default: %(default)s)")
    g.add_argument("--threads", dest="fils",
                   type=int, default=os.cpu_count() or 1,
                   metavar="N",
                   help="Stockfish threads (default: number of processors)")
    g.add_argument("--hash", dest="hachage",
                   type=int, default=256, metavar="MB",
                   help="hash table in megabytes (default: %(default)s)")
    g.add_argument("--stockfish", default=STOCKFISH_DEFAUT, metavar="PATH",
                   help="engine binary (default: %(default)s)")
    g.add_argument("--pv-length", dest="longueur_pv",
                   type=int, default=5, metavar="N",
                   help="plies of the principal variation reproduced in the "
                        "summary, 0 for the whole variation (default: "
                        "%(default)s)")

    p.add_argument("--timeout", dest="delai",
                   type=int, default=30, metavar="S",
                   help="maximum network delay, in seconds (default: "
                        "%(default)s)")
    p.add_argument("--debug", action="store_true",
                   help="lets the full traceback of unexpected errors come up")

    options = p.parse_args(argv)

    if options.purge_reglages and options.sans_reglages:
        # Opposite requests: one deletes the settings file, the other
        # leaves it alone for this run.
        p.error("--purge-settings and --no-settings are mutually exclusive")
    if not options.sans_reglages:
        # A name, never a path: checked before any reading, writing or
        # purge, so that nothing outside the application folder is
        # touched. With --no-settings, the file plays no part.
        refus = verifier_nom_reglages(options.reglages)
        if refus is not None:
            p.error(refus)
    if options.purge_reglages and (options.installer_venv
                                   or options.installer_catalogue
                                   or options.source):
        # The purge is done alone: combined, it was ignored without a
        # word in favor of the other action.
        p.error("--purge-settings is used alone, without a game or another "
                "action")
    if options.prompt is not None and not options.prompt.strip():
        # Case of an empty variable in a script: --prompt "$MODELE".
        p.error("--prompt: empty path")
    # --install-catalog downloads too: its timeout is checked before the
    # early return of the installations. A negative one ended there in
    # an unexpected error, a null one in an unreachable catalog.
    if options.delai < 1:
        p.error("--timeout must be at least 1")
    if (options.installer_venv or options.installer_catalogue
            or options.purge_reglages):
        return options
    if not options.source:
        p.error("a PGN file, a URL or a game identifier is required")
    if options.prompt and options.sans_prompt:
        p.error("--prompt and --no-prompt are mutually exclusive")
    if options.prompt_seul and options.sans_prompt:
        p.error("--prompt-only and --no-prompt are mutually exclusive")
    # nan and inf are valid floats for argparse, but nan escapes any
    # comparison and time.sleep() rejects both: they are ruled out
    # here, before any folder is created.
    for nom, option in (("pause", "--pause"),
                        ("seuil_frequence", "--min-frequency")):
        if not math.isfinite(getattr(options, nom)):
            p.error("%s must be a finite number" % option)
    if options.pause < 2.0:
        p.error("--pause must not go below 2 seconds")
    for nom, option in (("seuil_parties", "--min-games"),
                        ("max_demicoups", "--max-plies"),
                        ("profondeur", "--depth"),
                        ("multipv", "--multipv"),
                        ("fils", "--threads"),
                        ("hachage", "--hash"),
                        ("delai", "--timeout")):
        if getattr(options, nom) < 1:
            p.error("%s must be at least 1" % option)
    # Paths: the shell only expands the tilde if it starts the word,
    # not in the form --output-dir=~/analyses.
    options.sortie = os.path.expanduser(options.sortie)
    options.stockfish = resoudre_moteur(options.stockfish)
    if options.profondeur > PROFONDEUR_MAX:
        p.error("--depth must not exceed %d" % PROFONDEUR_MAX)
    if options.coups_stockfish < 0:
        p.error("--stockfish-moves must be 0 or more")
    if options.coups_min < 0:
        p.error("--min-moves must be 0 or more")
    # Without --usernames, the value stays None: the usernames will then
    # come from the settings. The option, when given, must carry one.
    if options.pseudos is not None:
        options.pseudos = decouper_pseudos(options.pseudos)
        if not options.pseudos:
            p.error("--usernames: empty list")
    if options.seuil_frequence < 0 or options.seuil_frequence > 100:
        p.error("--min-frequency must be between 0 and 100")
    if options.longueur_pv < 0:
        p.error("--pv-length must be 0 or more")
    if options.base == "masters":
        # Same principle as for the engine options: a filter that the masters
        # database does not know would be silently ignored, so it is refused.
        for nom, option in (("cadences", "--speeds"),
                            ("classements", "--ratings")):
            if getattr(options, nom) is not None:
                p.error("%s only has an effect with --database lichess"
                        % option)
    else:
        # The default values are only set here, and only for the Lichess
        # database: collection.json thus records the filters actually
        # applied, and nothing for the masters database.
        if options.cadences is None:
            options.cadences = CADENCES_DEFAUT
        if options.classements is None:
            options.classements = CLASSEMENTS_DEFAUT
        options.cadences = valider_liste(p, "--speeds", options.cadences,
                                         CADENCES_LICHESS)
        options.classements = valider_liste(p, "--ratings",
                                            options.classements,
                                            CLASSEMENTS_LICHESS)
    return options


def main(argv: list[str]) -> int:
    """Entry point: orchestrates the collection and writes the summary."""
    global DEBUG, JETON_COURANT

    options = analyser_arguments(argv)
    DEBUG = options.debug

    # -- Virtual environment ------------------------------------------------
    if options.installer_venv:
        installer_venv(options.venv)
        return 0
    # -- Purge of the settings ----------------------------------------------
    # Placed before the restart: it needs neither python-chess nor a game.
    if options.purge_reglages:
        purger_reglages(options.reglages)
        return 0
    if not CHESS_DISPONIBLE:
        relancer_dans_venv(options.venv, argv)

    # -- Opening catalog, installation or update -----------------------------
    # Placed after the restart: the catalog is validated with python-chess.
    if options.installer_catalogue:
        installer_catalogue(options.catalogue, options.delai)
        return 0

    # Text of the "Analysis instructions" section of the summary: the
    # answers to the startup questions, when they are asked.
    consignes = None

    # -- User settings, read early as well ----------------------------------
    # With --no-settings, empty settings stand in for the file, which is
    # neither read nor written during this run.
    if options.sans_reglages:
        reglages = reglages_vides()
        journal("Settings neither read nor written: option --no-settings.")
    else:
        reglages = lire_reglages(options.reglages)

    # -- Prompt template, read and checked before the collection ------------
    # A template named by --prompt must exist. The default template, for
    # its part, may be missing when the script was copied alone: the
    # collection is then done without a prompt, and the log says so.
    modele_prompt = None
    if not options.sans_prompt:
        fichier_modele = chemin_modele(options.prompt, options.prompt_seul)
        if est_fichier(fichier_modele):
            modele_prompt = lire_texte(fichier_modele, "prompt template")
            verifier_modele(modele_prompt, str(fichier_modele))
            # A prompt to be pasted alone must carry the game: a personal
            # template that does not place it is refused before the collection.
            # The marker is looked up in the text lines: placed in a
            # note, it would put nothing into the prompt.
            if options.prompt_seul and not any(
                    PROMPT_DONNEES in ligne
                    for ligne in lignes_de_texte(modele_prompt)):
                raise SystemExit(
                    "--prompt-only: the template %s does not contain %s, the "
                    "prompt would not carry the game. Start from %s."
                    % (fichier_modele, PROMPT_DONNEES, PROMPT_SEUL_MODELE))
        elif options.prompt or options.prompt_seul:
            # --prompt-only asks for a prompt: without a template, it is better
            # to stop here than after the collection.
            raise SystemExit("Prompt template not found: %s"
                             % fichier_modele)
        else:
            journal("Warning: prompt template not found (%s), no prompt will "
                    "be written. See --prompt and --no-prompt."
                    % fichier_modele)

    # -- Fetching the PGN ---------------------------------------------------
    # Encoding chosen for the PGN and decoding remarks, recorded in
    # collection.json and, if need be, in section 5 of the summary.
    encodage_pgn = "utf-8"
    remarques_pgn: list[str] = []
    chemin_local = pathlib.Path(os.path.expanduser(options.source))
    if est_fichier(chemin_local):
        journal("Reading the local PGN: %s" % chemin_local)
        texte_pgn, encodage_pgn, remarques_pgn = lire_fichier_texte(
            chemin_local, "PGN")
        if encodage_pgn == "latin-1":
            # The fallback on latin-1 only happens if the file contains a
            # byte that cp1252 does not define: this is the sign of another
            # encoding, cp850 for example, whose accented letters would be
            # removed like control characters. Rather than silently
            # damaging the names, the script stops. A MacRoman file almost
            # never gets here: nearly all its bytes are defined in cp1252,
            # and it is read as such, its accents wrong, which only the
            # remark on the encoding reports.
            raise SystemExit(
                "PGN encoding not recognized: neither UTF-8, nor UTF-16, nor "
                "cp1252. Convert the file to UTF-8, for example with iconv, "
                "then run again.")
        if REMARQUE_SEQUENCES % encodage_pgn in remarques_pgn:
            # In UTF-16 or UTF-32, a character takes two or four bytes: a
            # single byte lost, by a cut transfer for example, shifts the
            # whole text that follows. The lexical check then blamed a
            # U+FFFD for not being a move, or a brace for never being
            # closed, the cause staying in the remark on the encoding.
            raise SystemExit(
                "Corrupt PGN: the file is in %s, but some of its bytes form "
                "no character: it is truncated or damaged, and in this "
                "encoding a single byte lost shifts the whole text that "
                "follows. Export it again from its source, then run again."
                % encodage_pgn)
        etiquette = etiquette_sure(chemin_local.stem)
        if etiquette != chemin_local.stem:
            journal("Folder name sanitized: %s" % etiquette)
    elif options.source.strip() and est_repertoire(chemin_local):
        # A directory whose name has eight letters would otherwise pass for
        # an identifier, and a request would go to Lichess.
        raise SystemExit("%s is a directory, not a PGN file."
                         % chemin_local)
    else:
        identifiant = extraire_id(options.source)
        if identifiant is None:
            # Outside a URL, a dot, a slash or a tilde betray a path: the
            # file aimed at does not exist, we might as well say so.
            if (not options.source.strip().lower().startswith(
                    ("http://", "https://"))
                    and any(c in options.source for c in "./~")):
                raise SystemExit("PGN file not found: %s"
                                 % chemin_local)
            if options.source.strip().lower().startswith(
                    ("http://", "https://")):
                # Message specific to URLs: stating the expected form is better
                # than a general refusal.
                raise SystemExit("URL not recognized as a Lichess game: %s\n"
                                 "Expected form: "
                                 "https://lichess.org/<identifier>, the "
                                 "identifier being 8 or 12 alphanumeric "
                                 "characters."
                                 % nettoyer_valeur(options.source))
            raise SystemExit("Source not understood: neither an existing "
                             "file, nor a valid Lichess URL or identifier.")
        texte_pgn = telecharger_pgn(identifiant, options.delai)
        etiquette = identifiant

    partie = charger_partie(texte_pgn)

    # -- Preliminary checks, to fail before anything has been written -------
    catalogue = None
    motif_sans_explorateur = None
    if options.sans_explorateur:
        motif_sans_explorateur = "disabled by --no-explorer"
    else:
        # The token is only read here and is neither written nor logged.
        JETON_COURANT = lire_jeton(options.jeton_fichier)
        # Catalog loaded before any writing: missing or damaged, we stop
        # here, giving the command to run.
        catalogue = lire_catalogue(options.catalogue)
        journal("Opening catalog: %s known positions, from %s"
                % (catalogue.meta.get("known"), catalogue.meta.get("date")))
    # The engine has been mandatory since version 4.0.0: it is checked
    # before any writing and before the slightest request.
    verifier_moteur(options.stockfish)
    # The engine options are checked here, with the engine, and not at
    # its configuration, which only happens after the explorer phase.
    verifier_options_moteur(options.stockfish, options.fils,
                            options.hachage, options.multipv)

    # -- Startup questions --------------------------------------------------
    # Asked after the checks, so as to ask nothing of someone who is going
    # to fail anyway, and before the collection, which may take a while.
    camp = None
    contexte = None
    interactif = questions_possibles(options.sans_questions)
    if interactif and not options.sans_reglages:
        # A name given with --settings whose file does not exist yet is
        # confirmed first: a typo must not start a new file.
        if (options.reglages != REGLAGES_DEFAUT
                and not os.path.lexists(chemin_reglages(options.reglages))):
            confirmer_nouveaux_reglages(options.reglages)
        # Missing settings: asked for here, once and for all, before the
        # questions specific to the game. Not with --no-settings, which
        # leaves the file alone: its questions would write it.
        completer_reglages(options.reglages, reglages, options.pseudos)
    # --usernames wins over the settings. The list kept replaces the
    # option: collection.json thus records the usernames actually used,
    # and it may be empty.
    if options.pseudos is None:
        options.pseudos = decouper_pseudos(reglage(reglages, "usernames"))
    if interactif:
        journal("Startup questions, Enter keeps the suggested value.")
        camp = completer_entetes(partie, options.pseudos)
        contexte = recueillir_contexte(
            partie, camp,
            analyser_cadence(reglage(reglages, "time_control")))
        consignes = contexte
    else:
        journal("Startup questions skipped: %s."
                % ("option --no-questions" if options.sans_questions
                   else "non-interactive terminal"))

    # -- Creation of the working folder -------------------------------------
    # The name is timestamped to the second; two runs within the same
    # second, or a folder left by a previous failure, get a suffix rather
    # than an error. The prompt counts too: with --prompt-only it is the
    # only file that remains, and a second run within the same second
    # overwrote it.
    horodatage = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dossier_horodate = (pathlib.Path(options.sortie)
                        / ("analysis-%s-%s" % (etiquette, horodatage)))
    dossier = dossier_horodate
    suffixe = 1
    while True:
        try:
            if not (chemin_archive(dossier).exists()
                    or dossier.with_name(dossier.name
                                         + PROMPT_SUFFIXE).exists()):
                dossier.mkdir(parents=True, exist_ok=False)
                break
        except FileExistsError:
            pass
        except OSError as err:
            raise SystemExit("Cannot create the working folder %s: "
                             "%s" % (dossier, err)) from err
        suffixe += 1
        if suffixe > 100:
            raise SystemExit("Too many folders with the same name in %s."
                             % dossier_horodate.parent)
        dossier = dossier_horodate.with_name(
            "%s-%d" % (dossier_horodate.name, suffixe))
    annexes: list[str] = []
    try:
        if camp and camp["modified_tags"]:
            # The PGN given is kept as it is; game.pgn holds the game,
            # re-exported by python-chess, with its headers filled in.
            ecrire_texte(dossier / "game-original.pgn", texte_pgn)
            ecrire_texte(dossier / "game.pgn", str(partie) + "\n")
            annexes.append("- `game-original.pgn`: the PGN as given, "
                           "before the tags %s were added."
                           % ", ".join(camp["modified_tags"]))
        else:
            ecrire_texte(dossier / "game.pgn", texte_pgn)
        if remarques_pgn:
            # The PGN kept in the archive is no longer, byte for byte, the
            # file given: the analyst must know it.
            annexes.append("- Encoding: the PGN given was converted to "
                           "UTF-8 before being stored in the archive (%s)."
                           % "; ".join(remarques_pgn))
        if contexte is not None:
            ecrire_texte(dossier / "context.md", contexte)
            annexes.append("- `context.md`: the answers to the startup "
                           "questions, repeated at the top of this "
                           "summary.")
    except OSError as err:
        raise SystemExit("Cannot write in %s: %s"
                         % (dossier, err)) from err
    journal("Working folder: %s" % dossier)

    # -- Explorer -----------------------------------------------------------
    # Database and filters are set even without a collection, so that the
    # title of section 2 names the database requested in every case.
    base = BASES_EXPLORATEUR[options.base]
    filtres = None
    if options.base == "lichess":
        # recentGames at 0, like topGames: only the statistics are used,
        # there is no point in fetching game references.
        filtres = {
            "variant": "standard",
            "speeds": options.cadences,
            "ratings": options.classements,
            "since": DEPUIS_LICHESS,
            "recentGames": "0",
        }
    resume_explorateur = None
    if JETON_COURANT is not None:
        journal("Explorer: database %s, %s" % (base["libelle"], base["url"]))
        client = Explorateur(JETON_COURANT, options.pause, options.delai,
                             base["url"], filtres)
        resume_explorateur = collecter_explorateur(
            partie, dossier, client, options.seuil_parties,
            options.seuil_frequence, options.max_demicoups,
            options.jusqu_a_epuisement, catalogue, options.coups_min * 2)

    # -- Stockfish ----------------------------------------------------------
    resume_stockfish = collecter_stockfish(
        partie, dossier, options.stockfish,
        options.coups_stockfish * 2, options.profondeur,
        options.multipv, options.fils, options.hachage)

    # -- Record of the parameters, redacted of any sensitive data -----------
    # The paths under the home folder are written with "~" (masquer_maison).
    parametres = {CLEFS_COLLECTE[nom]: (masquer_maison(valeur)
                                        if isinstance(valeur, str)
                                        else valeur)
                  for nom, valeur in vars(options).items()}
    parametres["token_present"] = JETON_COURANT is not None
    parametres["catalog_used"] = (catalogue.meta if catalogue is not None
                                  else None)
    parametres["side"] = camp
    parametres["context_collected"] = contexte is not None
    parametres["pgn_encoding"] = encodage_pgn
    parametres["pgn_remarks"] = remarques_pgn
    # Name of the prompt written next to the archive, or nothing if there
    # is none.
    parametres["prompt_written"] = (dossier.name + PROMPT_SUFFIXE
                                    if modele_prompt is not None else None)
    ecrire_texte(dossier / "collection.json",
                 json.dumps(parametres, ensure_ascii=False, indent=1,
                            default=str))

    # -- Summary ------------------------------------------------------------
    synthese = dossier / "summary.md"
    ecrire_synthese(synthese, partie, options.source, consignes,
                    resume_explorateur, motif_sans_explorateur,
                    resume_stockfish, options.longueur_pv,
                    base["libelle"], filtres, annexes,
                    bool(camp and camp["modified_tags"]))
    journal("Summary written: %s" % synthese)

    # The prompt may include the PGN: it is read back here, before the
    # archiving that deletes the working folder.
    texte_partie = ""
    if modele_prompt is not None:
        texte_partie = (dossier / "game.pgn").read_text(encoding="utf-8")

    # -- Archive and cleanup ------------------------------------------------
    # With --prompt-only, the prompt is all that the player asks for: no
    # archive is written, and the working folder is deleted further down,
    # once the prompt is on disk. The name that the archive would have
    # borne still serves to name the prompt.
    if options.prompt_seul:
        archive = chemin_archive(dossier)
    else:
        archive = archiver(dossier, options.garder_dossier)

    # -- Analysis prompt, written next to the archive -----------------------
    # After the archiving: a failure does not leave a prompt without an
    # archive. The prompt does not go into the zip, it is pasted into the
    # conversation.
    if modele_prompt is not None:
        camp_joueur = ((camp or {}).get("side")
                       or deduire_camp(partie, options.pseudos))
        niveau = analyser_niveau(reglage(reglages, "rating")) or 0
        habituelle = (analyser_cadence(reglage(reglages, "time_control"))
                      or dict(CADENCE_INCONNUE))
        # Data of the short prompt: computed in every case, as a personal
        # template may place them too.
        alerte = (resultat_contredit(partie, resume_stockfish["resultats"])
                  or "").replace("**", "")
        precisions = consignes_joueur(contexte)
        ouverture = phrase_ouverture(resume_explorateur, base["libelle"])
        coups_partie = list(partie.mainline_moves())
        evalues = len(resume_stockfish["resultats"])
        faibles = coups_faibles_joueur(resume_stockfish["resultats"],
                                       camp_joueur)
        conditions = {
            # Always true since version 4.0.0, kept for the personal
            # templates that use it.
            "STOCKFISH": True,
            "EXPLORER": resume_explorateur is not None,
            "LICHESS_DATABASE": options.base == "lichess",
            "MASTERS_DATABASE": options.base == "masters",
            "ANSWERS": contexte is not None,
            "SIDE_KNOWN": camp_joueur is not None,
            "USERNAME_KNOWN": bool(options.pseudos),
            "RATING_DECLARED": bool(niveau),
            "RESULT_CONTRADICTED": bool(alerte),
            "INSTRUCTIONS_GIVEN": bool(precisions),
            "OPENING_KNOWN": bool(ouverture),
            # --stockfish-moves limited the engine to the first moves: the
            # prompt must say so, otherwise it promises a figure for every
            # move.
            "PARTIAL_COVERAGE": evalues < len(coups_partie),
            "NULL_MOVE": any(not coup for coup in coups_partie),
            # The review of both prompts asks for three errors: when the
            # table marks fewer of them for the player, the prompt says so, so
            # that the LLM does not make one up.
            "FEW_WEAK_MOVES": (faibles is not None
                               and faibles < ERREURS_DU_BILAN),
            # Without a single weak move, "Keep to those" makes no sense:
            # both templates have a sentence for this case.
            "NO_WEAK_MOVE": faibles == 0,
        }
        valeurs = {
            "VERSION": VERSION,
            "REPOSITORY": DEPOT,
            "ARCHIVE": archive.name,
            "USERNAMES": ", ".join(options.pseudos),
            "SIDE": camp_joueur or "unknown",
            "RATING": decrire_niveau(niveau, partie, camp_joueur),
            "TIME_CONTROL": decrire_cadence(habituelle),
            "ANNOTATOR": (nettoyer_valeur(reglage(reglages, "annotator"))
                          or ANNOTATEUR_DEFAUT),
            "DATABASE": base["libelle"],
            "INACCURACY_THRESHOLD": str(SEUIL_IMPRECISION),
            "MISTAKE_THRESHOLD": str(SEUIL_ERREUR),
            "BLUNDER_THRESHOLD": str(SEUIL_GAFFE),
            "DEPTH": str(options.profondeur),
            "MULTIPV": str(options.multipv),
            "GAME_PGN": texte_partie.strip("\n"),
            "ENGINE_TABLE": tableau_compact(
                partie, resume_stockfish["resultats"], options.longueur_pv),
            "RESULT_ALERT": alerte,
            "PLAYER_INSTRUCTIONS": precisions,
            "OPENING": ouverture,
            "PLIES": str(len(coups_partie)),
            "PLIES_EVALUATED": str(evalues),
            "PLAYER_WEAK_MOVES": ("unknown" if faibles is None
                                  else str(faibles)),
            "FENCE": cloture_de_bloc(texte_partie),
        }
        prompt = archive.with_name(dossier.name + PROMPT_SUFFIXE)
        try:
            rendu = rendre_modele(
                modele_prompt, conditions, valeurs,
                str(chemin_modele(options.prompt, options.prompt_seul)))
            ecrire_texte(prompt, rendu)
            # rendre_modele removes the trailing spaces of the lines: a PGN
            # ending with a space is therefore compared without it.
            if (options.prompt_seul
                    and valeurs["GAME_PGN"].rstrip() not in rendu):
                # The marker exists in the template, but under a condition that
                # is false for this game: say so rather than announce a
                # complete prompt.
                journal("Warning: the prompt %s does not carry the game, the "
                        "template places it under a condition that does not "
                        "apply here. It cannot be pasted alone." % prompt)
            elif options.prompt_seul:
                journal("Analysis prompt written: %s, to be pasted alone into "
                        "the conversation: it carries the game and the "
                        "evaluations, no attachment is needed." % prompt)
            else:
                journal("Analysis prompt written: %s, to be pasted into the "
                        "conversation, with the archive as an "
                        "attachment." % prompt)
        except OSError as err:
            if options.prompt_seul:
                # The prompt was the only product expected: its failure is that
                # of the command. The working folder stays.
                raise SystemExit("Prompt not written (%s), working folder "
                                 "kept: %s" % (prompt, err)) from err
            # The archive is made: a prompt that cannot be written must
            # not make the collection fail.
            journal("Warning: prompt not written (%s): %s" % (prompt, err))

    if options.prompt_seul:
        # The prompt is written: the working folder has no more use,
        # unless the player asked to keep it, for example to pass it
        # to verify-analysis.py.
        prompt = archive.with_name(dossier.name + PROMPT_SUFFIXE)
        if options.garder_dossier:
            journal("Folder kept on request: %s" % dossier)
        else:
            try:
                shutil.rmtree(dossier)
            except OSError as err:
                raise SystemExit("Prompt written but cannot delete the "
                                 "folder: %s" % err) from err
            journal("Working folder deleted, no archive is written with "
                    "--prompt-only.")
        # The path written alone on standard output is that of the prompt.
        annoncer_archive(prompt)
        return 0

    annoncer_archive(archive)
    return 0


if __name__ == "__main__":
    # Before any display, including that of --help by argparse.
    configurer_console()
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.stderr.write("\n"
                         "Interrupted.\n")
        raise SystemExit(130) from None
    except SystemExit as fin:
        # A stop message is displayed here rather than by the interpreter,
        # so as to remove the control characters from it. The text and the
        # exit code, 1, stay those that the interpreter produced.
        if isinstance(fin.code, str):
            sys.stderr.write(RE_CONTROLES.sub("", fin.code) + "\n")
            raise SystemExit(1) from None
        raise
    except Exception as err:  # noqa: BLE001 - deliberate last resort
        # No exception must come out raw: we display a message redacted
        # of the token, and the full traceback, also redacted, only with
        # --debug.
        if DEBUG:
            sys.stderr.write(expurger(traceback.format_exc(), JETON_COURANT))
        else:
            sys.stderr.write("Unexpected error (%s): %s\n"
                             "Run again with --debug for the full traceback.\n"
                             % (type(err).__name__,
                                expurger(str(err), JETON_COURANT)))
        raise SystemExit(1) from None
