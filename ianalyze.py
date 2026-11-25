#!/usr/bin/env python3
"""
Gathers the material for the analysis of a chess game.

This program produces no analysis. It collects and formats:

  1. the PGN of the game, read from a local file or downloaded
     from Lichess;
  2. the statistics of the Lichess explorer, position by position,
     to find where the game leaves theory: the database of all
     Lichess players by default, or the masters database with
     --base maitres. A rare move that stays within a line of the
     catalog of named openings, kept locally, does not count as
     leaving theory;
  3. the Stockfish evaluation of the game in multipv, computed locally
     to spare the analyst this work. The engine is mandatory.

Before the collection, on an interactive terminal, the script asks for
your side if the headers do not give it, then for your answers to the
startup questions, stored in contexte.md and repeated at the top of
the summary.

Your username, your usual time control and your rating are not in the
code: you are asked for them only once, on the first run in a
terminal, and they are then kept in a settings file that you can edit
by hand.

Next to the archive, the script writes the analysis prompt for the
game, drawn from the template prompt-modele.txt: you paste it into the
conversation, with the archive as an attachment. With --prompt-seul,
it is a short prompt, drawn from prompt-seul-modele.txt, that carries
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
#     do, or we create it if you passed --installer-venv.
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

#: Data directory of the script, in the home directory on Debian as on
#: macOS: the virtual environment and the catalog go there, and you need
#: no root rights to install them. Up to version 3.8.0, Debian kept them
#: in /opt/venv/lichess and in /usr/local/share.
DONNEES = "~/.local/share/IAnalyze"

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
MARQUEUR_RELANCE = "IANALYZE_DEJA_RELANCE"

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
#: move is already reported in the log and in the summary: this message,
#: in English and repeated, is filtered out. The other notices of the
#: library are still displayed.
logging.getLogger("chess.engine").addFilter(
    lambda avis: "null moves" not in avis.getMessage())


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


def installer_venv(venv: str) -> None:
    """
    Creates the virtual environment if missing, then installs python-chess.

    The operation is idempotent: you can safely run it again on an
    environment already in place, it will then simply update the module.
    """
    racine = pathlib.Path(os.path.expanduser(venv))
    interpreteur = python_du_venv(venv)

    if not est_fichier(interpreteur):
        journal("Création de l'environnement virtuel : %s" % racine)
        try:
            racine.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, "-m", "venv", str(racine)],
                           check=True)
        except OSError as err:
            raise SystemExit("Impossible de créer %s : %s" % (racine, err)) \
                from err
        except subprocess.CalledProcessError as err:
            # The text displayed on Debian is the original one; on macOS
            # there is no python3-venv package to suggest.
            raise SystemExit(
                "Échec de la création de l'environnement virtuel. %s (%s)"
                % ("Le Python installé fournit-il le module venv ?"
                   if EST_MACOS else
                   "Le paquet python3-venv est-il installé ?",
                   CMD_PAQUET_VENV)
            ) from err
    else:
        journal("Environnement virtuel déjà présent : %s" % racine)

    journal("Installation de python-chess dans l'environnement virtuel.")
    try:
        subprocess.run([str(interpreteur), "-m", "pip", "install",
                        "--quiet", "--upgrade", "pip"], check=True)
        subprocess.run([str(interpreteur), "-m", "pip", "install",
                        "--quiet", "--upgrade", "chess"], check=True)
    except (subprocess.CalledProcessError, OSError) as err:
        raise SystemExit("Échec de l'installation de python-chess dans %s : %s"
                         % (racine, err)) from err

    if not venv_operationnel(venv):
        raise SystemExit("L'environnement %s ne fournit toujours pas le "
                         "module chess après installation." % venv)
    journal("Environnement virtuel opérationnel : %s" % interpreteur)


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
            "L'environnement %s ne fournit pas le module chess.\n"
            "Réparez-le avec : %s --installer-venv --venv %s"
            % (venv, script, venv))

    if est_fichier(interpreteur):
        journal("Environnement virtuel : relance via %s" % interpreteur)
        os.environ[MARQUEUR_RELANCE] = "1"
        try:
            os.execv(str(interpreteur), [str(interpreteur), script] + argv)
        except OSError as err:
            raise SystemExit("Relance impossible via %s : %s"
                             % (interpreteur, err)) from err

    supplement = "" if venv == VENV_DEFAUT else " --venv %s" % venv
    raise SystemExit(
        "Le module python-chess est introuvable et l'environnement virtuel "
        "%s n'existe pas.\n\n"
        "Créez-le en une commande :\n"
        "    %s\n"
        "    %s --installer-venv%s\n"
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

#: Databases that --base can query: endpoint, and label repeated in the
#: summary. The label of the masters database reproduces exactly the
#: titles of the summaries produced before this option was added.
BASES_EXPLORATEUR = {
    "maitres": {"url": EXPLORER_URL, "libelle": "maîtres"},
    "lichess": {"url": EXPLORER_LICHESS_URL,
                "libelle": "Lichess (tous joueurs)"},
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
                    "chess-openings/master/{partie}.tsv")
CATALOGUE_PARTIES = ("a", "b", "c", "d", "e")

#: Default directory of the local catalog, and name of its index.
CATALOGUE_DEFAUT = DONNEES
CATALOGUE_INDEX = "catalogue.tsv"

#: Version of the index format, checked on loading.
CATALOGUE_FORMAT = "1"

#: Move number in a catalog line, "1." or "12." for example.
RE_NUMERO_COUP = re.compile(r"\d+\.+")

#: User settings file, at the same place on Debian and on macOS. It holds
#: what depends on the person and not on the game: their usernames and
#: their usual time control. Nothing personal therefore appears in this
#: script, which anyone can reuse as it is.
#: The directories bear the name of the project, IAnalyze, and not that
#: of the script: the same goes for the catalog and the data on macOS.
REGLAGES_DEFAUT = "~/.config/IAnalyze/reglages.ini"

#: Section of the settings file that describes the player.
REGLAGES_SECTION = "joueur"

#: Known keys of this section, with the comment lines written above each
#: one in the file. The usernames are looked up, ignoring case, in the
#: White and Black tags to deduce the player's side; the first one is
#: used to fill in an empty tag.
REGLAGES_CLEFS = (
    ("pseudos",
     ("Vos noms de joueur, séparés par des virgules. Ils sont cherchés,",
      "sans tenir compte de la casse, dans les balises White et Black",
      "pour déduire votre camp. L'option --pseudos les remplace le temps",
      "d'un lancement.")),
    ("cadence",
     ("Votre cadence habituelle, proposée quand la balise TimeControl",
      "d'une partie ne la donne pas. Formes admises :",
      "  15+10                 temps réel, minutes puis incrément en",
      "                        secondes",
      "  14 jours              correspondance, délai fixe par coup",
      "  10 coups en 50 jours  correspondance, coups par période",
      "  5 jours + 36 heures   correspondance, capital de départ puis",
      "                        incrément par coup, en heures ou en",
      "                        jours ; ajoutez au besoin \", plafond 20",
      "                        jours\" et \", réserve 50 jours\"",
      "  inconnue")),
    ("niveau",
     ("Votre niveau, en points Elo approximatifs, ou inconnu. Il est",
      "transmis à l'analyste, qui y adapte ses explications. Sans lui,",
      "c'est l'Elo de votre balise dans la partie qui sert.")),
)

#: Bounds of a rating expressed in Elo points.
NIVEAU_MIN, NIVEAU_MAX = 100, 3500

#: Template of the analysis prompt, looked up next to the script, and
#: suffix of the prompt written next to the archive.
PROMPT_MODELE = "prompt-modele.txt"
PROMPT_SUFFIXE = ".prompt.txt"

#: Template of the short prompt of --prompt-seul: a few instructions, the
#: game and the engine evaluations, to be pasted alone, without an
#: attachment.
PROMPT_SEUL_MODELE = "prompt-seul-modele.txt"

#: Value through which a template places the game. With --prompt-seul, a
#: template that did not place it would give nothing to analyze.
PROMPT_DONNEES = "{{PARTIE_PGN}}"

#: Markers of the template. A line starting with PROMPT_DIRECTIVE is a
#: directive, never copied; a value is written between double braces.
PROMPT_DIRECTIVE = "#!"
RE_VALEUR_MODELE = re.compile(r"\{\{([A-Za-z_]+)\}\}")

#: Conditions known to a "si" directive, and replaceable values. A name
#: missing from these lists stops the script before the collection.
PROMPT_CONDITIONS = ("STOCKFISH", "EXPLORATEUR", "BASE_LICHESS",
                     "BASE_MAITRES", "REPONSES",
                     "CAMP_CONNU", "PSEUDO_CONNU", "NIVEAU_DECLARE",
                     "RESULTAT_CONTREDIT", "CONSIGNES_DONNEES",
                     "OUVERTURE_CONNUE", "COUVERTURE_PARTIELLE", "COUP_NUL",
                     "PEU_DE_COUPS_FAIBLES", "AUCUN_COUP_FAIBLE")
PROMPT_VALEURS = ("VERSION", "DEPOT", "ARCHIVE", "PSEUDOS", "CAMP", "NIVEAU",
                  "CADENCE", "ANNOTATEUR", "BASE", "SEUIL_IMPRECISION",
                  "SEUIL_ERREUR", "SEUIL_GAFFE", "PROFONDEUR", "MULTIPV",
                  "PARTIE_PGN", "TABLEAU_MOTEUR", "ALERTE_RESULTAT",
                  "CONSIGNES_JOUEUR", "OUVERTURE", "DEMI_COUPS",
                  "DEMI_COUPS_EVALUES", "COUPS_FAIBLES_JOUEUR")

#: Number of errors that the short prompt asks for in its review. When
#: the engine table marks fewer of them for the player, the prompt gives
#: their real number: an LLM asked for three makes one up.
ERREURS_DU_BILAN = 3

#: Value of the Annotator tag when the settings do not give one: the
#: script does not know which model will write the analysis.
ANNOTATEUR_DEFAUT = ("votre nom de modèle, suivi de son éditeur entre "
                     "parenthèses")

#: Label of an unknown time control, when neither the TimeControl tag
#: nor the settings give it.
CADENCE_DEFAUT = "non précisée"

#: Lichess time control categories, from the slowest to the fastest, each
#: with the estimated duration, in seconds, from which it applies. The
#: estimated duration of a game is the initial time plus COUPS_ESTIMES
#: times the increment. Bounds and formula taken from the Lichess source
#: (scalachess: Speed.scala and Clock.scala). Beyond six hours, Lichess
#: speaks of correspondence; a time control entered as real time stays
#: "classique" here.
CATEGORIES_CADENCE = ((1500, "classique"), (480, "rapide"), (180, "blitz"),
                      (30, "bullet"), (0, "ultrabullet"))
COUPS_ESTIMES = 40

#: Time control forms accepted in the settings file: "15+10", minutes per
#: player then increment in seconds, the Lichess way, and "14 jours" for
#: correspondence. The other values of CADENCES_INCONNUES denote an
#: unknown time control.
RE_CADENCE_REELLE = re.compile(r"([0-9]{1,5})\s*\+\s*([0-9]{1,5})")
RE_CADENCE_JOURS = re.compile(r"([0-9]{1,4})\s*(?:j|jour|jours)")

#: Correspondence by period: "10 coups en 50 jours". This is the
#: so-called standard ICCF time control, the time saved over a period
#: being carried over to the next one.
RE_CADENCE_PERIODE = re.compile(
    r"([0-9]{1,3})\s*coups?\s*en\s*([0-9]{1,4})\s*(?:j|jour|jours)")

#: Correspondence with a clock: "5 jours + 36 heures", followed if need be
#: by ", plafond 20 jours" and by ", réserve 50 jours". A clock is given at
#: the start, an increment is added to it at each move, a maximum may cap
#: it, and a bank may exist beside it, which the player draws from at
#: will. chess-mail.com is its simple form (5 days, 36 hours per move,
#: maximum of 20 days), the ICCF Triple Block its full form (50 days, an
#: increment in days, maximum of 50 days, bank of 50 or 75 days). The
#: increment carries its unit, hours or days: a day and a half cannot be
#: written in whole days.
RE_CADENCE_CAPITAL = re.compile(
    r"([0-9]{1,4})\s*(?:j|jour|jours)\s*\+\s*([0-9]{1,4})\s*"
    r"(h|heure|heures|j|jour|jours)"
    r"(?:\s*,?\s*plafond\s*([0-9]{1,4})\s*(?:j|jour|jours))?"
    r"(?:\s*,?\s*r[ée]serve\s*([0-9]{1,4})\s*(?:j|jour|jours))?")

#: Increment entered with its unit: "36h" or "3j".
RE_INCREMENT = re.compile(r"([0-9]{1,4})\s*(h|heure|heures|j|jour|jours)")
CADENCES_INCONNUES = ("", "?", "inconnue", "non précisée")

#: TimeControl tag of the PGN standard, in its two most common forms:
#: "600+5", seconds then increment, and "300", time only.
RE_TIMECONTROL = re.compile(r"([0-9]{1,6})(?:\+([0-9]{1,5}))?")

#: Unknown time control, fallback value.
CADENCE_INCONNUE = {"type": "inconnue"}

#: Startup questions, with the default that an empty answer keeps: label
#: in contexte.md, question, default.
QUESTIONS_CONTEXTE = (
    ("a. Périmètre",
     "Périmètre : les N premiers coups, ou la partie complète ?",
     "la partie complète"),
    ("b. Ce que le joueur cherche à comprendre",
     "Ce que vous cherchez à comprendre dans cette partie ?",
     "laissé ouvert"),
    ("c. Contexte particulier",
     ("Contexte particulier : zeitnot, fatigue, ouverture inconnue, "
      "adversaire particulier ?"),
     "rien"),
    ("d. Autres commentaires à inclure dans le PGN final",
     "Autres commentaires à inclure dans le PGN final ?",
     "rien"),
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

#: Location of the Stockfish binary on Debian: it is not in the PATH. On
#: macOS, Homebrew puts it in the PATH: we look for it there, falling
#: back on the Homebrew location for Apple Silicon if it cannot be found.
STOCKFISH_DEFAUT = ((shutil.which("stockfish")
                     or "/opt/homebrew/bin/stockfish") if EST_MACOS
                    else "/usr/games/stockfish")

#: Hint for installing the engine, repeated in the error message.
AIDE_STOCKFISH = (CMD_PAQUET_STOCKFISH if EST_MACOS
                  else CMD_PAQUET_STOCKFISH + ", dans /usr/games")

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
        texte = texte.replace(jeton, "<JETON-EXPURGE>")
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

#: Bytes examined to recognize UTF-16 without a byte order mark.
ECHANTILLON_UTF16 = 4096

#: Invalid bytes tolerated, per correctly encoded non-ASCII character,
#: for a text to still be held as damaged UTF-8.
UTF8_TOLERANCE = 4


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
        remarques.append("marque d'ordre des octets (BOM) UTF-8 retirée")
    else:
        large = None
        for marque, codec in BOMS_LARGES:
            if brut.startswith(marque):
                brut = brut[len(marque):]
                large = codec
                remarques.append("marque d'ordre des octets (BOM) détectée, "
                                 "encodage retenu : %s" % codec)
                break
        if large is None:
            large = utf16_sans_bom(brut)
            if large is not None:
                remarques.append("un octet nul sur deux et pas de marque "
                                 "d'ordre des octets, encodage retenu : %s"
                                 % large)
        if large is not None:
            encodage = large
            try:
                texte = brut.decode(large)
            except UnicodeDecodeError:
                texte = brut.decode(large, errors="replace")
                remarques.append("séquences %s invalides remplacées par "
                                 "U+FFFD" % large)

    if texte is None:
        try:
            texte = brut.decode("utf-8")
        except UnicodeDecodeError:
            essai = brut.decode("utf-8", errors="replace")
            invalides = essai.count("\ufffd")
            valides = sum(1 for c in essai if ord(c) > 127) - invalides
            if valides > 0 and invalides <= UTF8_TOLERANCE * valides:
                texte = essai
                remarques.append("UTF-8 abîmé, %d octet(s) invalide(s) "
                                 "remplacé(s) par U+FFFD, encodage retenu : "
                                 "utf-8" % invalides)
            else:
                try:
                    texte = brut.decode("cp1252")
                    encodage = "cp1252"
                except UnicodeDecodeError:
                    texte = brut.decode("latin-1")
                    encodage = "latin-1"
                remarques.append("le contenu n'est pas en UTF-8, encodage "
                                 "retenu : %s" % encodage)

    texte = texte.replace("\r\n", "\n").replace("\r", "\n")
    controles = RE_CONTROLES.findall(texte)
    if controles:
        texte = RE_CONTROLES.sub(
            lambda m: " " if m.group() in "\x0b\x0c" else "", texte)
        remarques.append("%d caractère(s) de contrôle retiré(s), dont %d NUL"
                         % (len(controles), controles.count("\x00")))
    return texte, encodage, remarques


def lire_fichier_texte(chemin: pathlib.Path,
                       role: str) -> tuple[str, str, list[str]]:
    """
    Reads a text file whatever its encoding, and reports what departs from
    UTF-8 with an "Attention" line in the log.

    Returns the text, the encoding chosen and the remarks, like
    decoder_octets. Only an error accessing the file stops the script.
    """
    try:
        brut = chemin.read_bytes()
    except OSError as err:
        raise SystemExit("Lecture impossible (%s) : %s" % (role, err)) from err
    texte, encodage, remarques = decoder_octets(brut)
    for remarque in remarques:
        journal("Attention, %s : %s." % (role, remarque))
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

    The writing goes through a neighboring file, ".<name>.partiel", renamed
    once complete: an interruption (Ctrl-C) or an error along the way
    never leaves a truncated file under its final name. The file that
    already existed, if there was one, then stays intact, and the partial
    file is removed.
    """
    partiel = chemin.with_name(".%s.partiel" % chemin.name)
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


def etiquette_sure(nom: str) -> str:
    """
    Derives from a file name a safe label for the working folder and for
    the paths of the archive.

    Each risky character becomes "_", each run of spaces a hyphen: an
    archive name without spaces needs no quotes in a command line. Dots
    and hyphens at the edges are removed, and an empty label becomes
    "partie".

    The length is bounded in bytes, not in characters: the file system
    counts in bytes, and eighty ideograms make two hundred and forty of
    them. Bounded in characters, the label let through names that the
    archive, once the timestamp was added, could no longer carry.
    """
    sure = RE_NOM_RISQUE.sub("_", re.sub(r"\s+", "-", nom.strip()))
    sure = sure.encode("utf-8", errors="surrogateescape")[:ETIQUETTE_MAX]
    # A cut in the middle of a character leaves orphan bytes: they are
    # dropped at decoding.
    sure = sure.decode("utf-8", errors="ignore").strip("-.")
    return sure or "partie"


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
        raise SystemExit("Jeton absent : %s introuvable." % p)

    try:
        mode = p.stat().st_mode
        brut = p.read_bytes()
    except (OSError, UnicodeDecodeError) as err:
        raise SystemExit("Jeton illisible dans %s : %s" % (p, err)) from err

    # Same decoding as for the PGN: a file saved by a Windows editor, with a
    # byte order mark or in UTF-16, stays readable. The remarks never quote
    # the content of the file.
    contenu, _encodage, remarques = decoder_octets(brut)
    for remarque in remarques:
        journal("Attention, jeton (%s) : %s." % (p, remarque))

    if mode & 0o077:
        journal("Attention : %s est lisible par d'autres (mode %o)."
                % (p, mode & 0o777))

    jeton = contenu.strip()
    # An assignment, LICHESS_TOKEN=lip_..., or quotes around the token fit in
    # a single word: without this check, they got through, and Lichess
    # answered 401 without anything pointing to the file.
    if (not jeton or any(c.isspace() for c in jeton)
            or any(c in jeton for c in "=\"'")):
        raise SystemExit("Le fichier %s doit contenir le jeton seul, sans "
                         "espace ni affectation de variable." % p)
    # The token goes into an HTTP header: outside printable ASCII, it would
    # be rejected by http.client with an encoding error that nothing links
    # to the file. The message does not reproduce the token.
    if not jeton.isascii() or not jeton.isprintable():
        raise SystemExit("Le jeton lu dans %s contient des caractères hors "
                         "de l'ASCII imprimable : recopiez-le depuis "
                         "Lichess, sans rien d'autre dans le fichier." % p)
    return jeton


#: Hosts from which a game URL is accepted.
HOTES_LICHESS = ("lichess.org", "www.lichess.org")

#: Sections of the site whose name has eight letters: they look like a
#: game identifier without being one. https://lichess.org/analysis was
#: taken for the game "analysis" and requested from Lichess.
RUBRIQUES_LICHESS = ("analysis", "training", "practice", "streamer",
                     "features", "insights", "learning", "username",
                     "patron", "calendar", "storm", "racer", "coach",
                     "broadcast", "tournament", "simul", "swiss", "team",
                     "forum", "player", "games", "editor", "variant",
                     "paste", "contact", "mobile", "about", "account")

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
    journal("Téléchargement du PGN : %s" % url)
    try:
        with urllib.request.urlopen(requete, timeout=delai) as reponse:
            # Same decoding as for a local file: Lichess answers in UTF-8, but
            # nothing must depend on this assumption.
            texte, _encodage, remarques = decoder_octets(reponse.read())
            for remarque in remarques:
                journal("Attention, PGN téléchargé : %s." % remarque)
            return texte
    except urllib.error.HTTPError as err:
        raise SystemExit("Export PGN : HTTP %d pour la partie %s."
                         % (err.code, identifiant)) from err
    except (OSError, http.client.HTTPException) as err:
        # URLError is a subclass of OSError: this block covers a failed DNS
        # resolution as well as a timeout or a dropped connection.
        raise SystemExit("Export PGN injoignable : %s"
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

    Accepted outside the comments: the tags at the start of a line, the
    move numbers, the moves in English notation, the NAGs, the annotation
    symbols, the variation parentheses and the result.
    """
    i, n = 0, len(texte_pgn)
    profondeur = 0
    ligne = 1
    debut_de_ligne = True
    while i < n:
        c = texte_pgn[i]
        if c == "\n":
            ligne += 1
            debut_de_ligne = True
            i += 1
        elif c.isspace():
            i += 1
        elif c == "{":
            fin = texte_pgn.find("}", i)
            if fin < 0:
                raise SystemExit(
                    "PGN corrompu : le commentaire ouvert par une accolade "
                    "à la ligne %d n'est jamais fermé." % ligne)
            ligne += texte_pgn.count("\n", i, fin)
            i = fin + 1
            debut_de_ligne = False
        elif c == ";" or (debut_de_ligne and c in "[%"):
            # End-of-line comment, tag, or escape line: everything runs
            # to the line feed.
            fin = texte_pgn.find("\n", i)
            i = n if fin < 0 else fin
        elif c == "(":
            profondeur += 1
            i += 1
            debut_de_ligne = False
        elif c == ")":
            if profondeur == 0:
                raise SystemExit(
                    "PGN corrompu : parenthèse fermante sans variante "
                    "ouverte, ligne %d." % ligne)
            profondeur -= 1
            i += 1
            debut_de_ligne = False
        else:
            m = RE_JETON_PGN.match(texte_pgn, i)
            if m is None:
                mot = re.match(r"\S+", texte_pgn[i:i + 40])
                raise SystemExit(
                    "PGN corrompu : \"%s\", ligne %d, n'est ni un coup en "
                    "notation anglaise (K, Q, R, B, N) ni un autre élément "
                    "de PGN. Une partie notée en français ou en figurines "
                    "doit être convertie, un texte libre placé entre "
                    "accolades."
                    % (nettoyer_valeur(mot.group(0) if mot else c)[:20],
                       ligne))
            i = m.end()
            debut_de_ligne = False
    if profondeur:
        raise SystemExit("PGN corrompu : %d variante(s) ouverte(s) par une "
                         "parenthèse et jamais fermée(s)." % profondeur)


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
        raise SystemExit("PGN corrompu : python-chess n'a pas pu le lire "
                         "(%s)." % type(err).__name__) from err
    if partie is None:
        raise SystemExit("PGN illisible ou vide.")
    if partie.errors:
        raise SystemExit("PGN corrompu, coup illégal ou malformé : %s"
                         % "; ".join(nettoyer_valeur(str(e))
                                     for e in partie.errors))
    if not list(partie.mainline_moves()):
        raise SystemExit("PGN sans aucun coup dans la ligne principale.")
    # IAnalyze analyzes a whole game, from the first move to the last: the
    # explorer, the opening catalog and the instructions of the prompt all
    # assume the initial position. A game resumed from a position, given by
    # a FEN tag, is therefore rejected here, rather than half analyzed with
    # a prompt that does not fit it.
    if partie.board().fen() != chess.STARTING_FEN:
        raise SystemExit(
            "La partie ne commence pas à la position initiale, elle part "
            "d'une balise FEN. IAnalyze analyse une partie entière, du "
            "premier coup au dernier : pour étudier une position, "
            "chargez-la dans un échiquier d'analyse.")

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
        raise SystemExit("Variante non prise en charge : %s. Ce script ne "
                         "traite que les échecs standard." % variante)

    # A single game per file. Analyzing the first one of a series would make
    # no sense: nothing says it is the one you wanted, and partie.pgn,
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
        journal("Résultat répété en fin de fichier, après la partie : "
                "ignoré.")
    if autres:
        raise SystemExit("Le PGN contient %d parties : isolez celle à "
                         "analyser dans un fichier à part." % (autres + 1))
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
              else "%s (Entrée : %s)" % (question, defaut))
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
            sys.stderr.write("  Réponse trop longue : %d caractères au "
                             "plus.\n" % REPONSE_MAX)
            continue
        if nom and any(c in SIGNES_INTERDITS_NOM for c in reponse):
            sys.stderr.write("  Un nom ne peut contenir ni guillemet, ni "
                             "barre oblique inversée, ni crochet, ni "
                             "accolade.\n")
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
#     over: standard ICCF time control, "10 coups en 50 jours";
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
    """Increment in hours, from a number and its unit, h or j."""
    return nombre * 24 if unite.startswith("j") else nombre


def duree_increment(heures: int) -> str:
    """ "36 heures", or "3 jours" when the count falls exactly in days."""
    if heures and heures % 24 == 0:
        return pluriel(heures // 24, "jour")
    return pluriel(heures, "heure")


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
        note = "%s + %s" % (pluriel(cadence["capital"], "jour"),
                            duree_increment(cadence["increment"]))
        if cadence["plafond"]:
            note += ", plafond %s" % pluriel(cadence["plafond"], "jour")
        if cadence["reserve"]:
            note += ", réserve %s" % pluriel(cadence["reserve"], "jour")
        return note
    if cadence["type"] == "correspondance" and "coups" in cadence:
        return "%s en %s" % (pluriel(cadence["coups"], "coup"),
                             pluriel(cadence["periode"], "jour"))
    if cadence["type"] == "correspondance":
        return pluriel(cadence["jours"], "jour")
    return "inconnue"


def pluriel(nombre: int, mot: str) -> str:
    """ "1 jour", "14 jours": the number followed by the word, in agreement."""
    return "%d %s%s" % (nombre, mot, "s" if nombre > 1 else "")


def categorie_cadence(initial: int, increment: int) -> str:
    """Lichess category of a real-time time control (CATEGORIES_CADENCE)."""
    estimee = initial + COUPS_ESTIMES * increment
    for seuil, nom in CATEGORIES_CADENCE:
        if estimee >= seuil:
            return nom
    return CATEGORIES_CADENCE[-1][1]


def decrire_cadence(cadence: dict) -> str:
    """
    Sentence describing a time control, as it goes into contexte.md:
    "rapide, 15 minutes + 10 secondes par coup", "blitz, 5 minutes sans
    incrément", "correspondance, 14 jours par coup", "correspondance,
    10 coups en 50 jours", "correspondance, capital de 5 jours + 36
    heures par coup, plafonné à 20 jours", or "non précisée".
    """
    if cadence["type"] == "correspondance" and "capital" in cadence:
        phrase = ("correspondance, capital de %s + %s par coup"
                  % (pluriel(cadence["capital"], "jour"),
                     duree_increment(cadence["increment"])))
        if cadence["plafond"]:
            phrase += ", plafonné à %s" % pluriel(cadence["plafond"], "jour")
        if cadence["reserve"]:
            phrase += ", réserve de %s" % pluriel(cadence["reserve"], "jour")
        return phrase
    if cadence["type"] == "correspondance" and "coups" in cadence:
        return "correspondance, %s en %s" % (
            pluriel(cadence["coups"], "coup"),
            pluriel(cadence["periode"], "jour"))
    if cadence["type"] == "correspondance":
        return "correspondance, %s par coup" % pluriel(cadence["jours"],
                                                       "jour")
    if cadence["type"] != "reel":
        return CADENCE_DEFAUT
    minutes, secondes = divmod(cadence["initial"], 60)
    duree = []
    if minutes or not secondes:
        duree.append(pluriel(minutes, "minute"))
    if secondes:
        duree.append(pluriel(secondes, "seconde"))
    increment = (" + %s par coup" % pluriel(cadence["increment"], "seconde")
                 if cadence["increment"] else " sans incrément")
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
        sys.stderr.write("  Réponse attendue : un nombre entier, %d ou plus.\n"
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
        reponse = demander("%s : [t]emps réel, [c]orrespondance ou "
                           "[i]nconnue ?" % libelle, propose)
        if reponse is None:
            return None
        if reponse == propose:
            return defaut, True
        choix = reponse.casefold()
        if choix in ("t", "temps", "temps réel", "temps reel", "r", "reel",
                     "réel"):
            minutes = demander_entier("  Minutes par joueur ?", 0)
            if minutes is None:
                return None
            increment = demander_entier("  Incrément en secondes ?", 0)
            if increment is None:
                return None
            if minutes == 0 and increment == 0:
                sys.stderr.write("  Une cadence sans temps ni incrément "
                                 "n'existe pas.\n")
                continue
            return ({"type": "reel", "initial": 60 * minutes,
                     "increment": increment}, False)
        if choix in ("c", "corr", "correspondance"):
            saisie = demander_correspondance()
            if saisie is None:
                return None
            return saisie, False
        if choix in ("i", "inconnue", "?"):
            return dict(CADENCE_INCONNUE), False
        sys.stderr.write("  Réponse attendue : t, c ou i.\n")


def analyser_niveau(texte: str) -> int | None:
    """
    Reads a rating written in the settings file: a number of Elo points
    between NIVEAU_MIN and NIVEAU_MAX. Returns 0 for an unknown rating,
    and None for a value of another form.
    """
    texte = texte.strip().casefold()
    if texte in ("", "?", "inconnu"):
        return 0
    if (re.fullmatch(r"[0-9]{1,4}", texte)
            and NIVEAU_MIN <= int(texte) <= NIVEAU_MAX):
        return int(texte)
    return None


def demander_niveau() -> int | None:
    """
    Asks for the player's rating in Elo points, Enter meaning "inconnu"
    (0). The question is asked again as long as the answer is not an
    integer within the bounds. Returns None at the end of the stream.
    """
    while True:
        reponse = demander("Votre niveau, en points Elo approximatifs ? "
                           "(Entrée : inconnu)")
        if reponse is None:
            return None
        niveau = analyser_niveau(reponse)
        if niveau is not None:
            return niveau
        sys.stderr.write("  Réponse attendue : un nombre entier entre %d et "
                         "%d, ou Entrée.\n" % (NIVEAU_MIN, NIVEAU_MAX))


def deduire_camp(partie: chess.pgn.Game, pseudos: list[str]) -> str | None:
    """
    Side of the player from their usernames, without asking any question:
    "Blancs", "Noirs", or None if no tag, or both, carry a username.
    Used outside a terminal, where completer_entetes is not called.
    """
    moi_blancs = est_pseudo(partie.headers.get("White", "?"), pseudos)
    moi_noirs = est_pseudo(partie.headers.get("Black", "?"), pseudos)
    if moi_blancs == moi_noirs:
        return None
    return "Blancs" if moi_blancs else "Noirs"


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
        reponse = demander("  Correspondance : [d]élai fixe par coup, "
                           "[p]ériode pour un nombre de coups, ou [c]apital "
                           "de temps avec incrément ?")
        if reponse is None:
            return None
        choix = reponse.casefold()
        if choix in ("d", "delai", "délai"):
            jours = demander_entier("  Jours par coup ?", 1)
            if jours is None:
                return None
            return {"type": "correspondance", "jours": jours}
        if choix in ("p", "periode", "période"):
            coups = demander_entier("  Nombre de coups par période ?", 1)
            if coups is None:
                return None
            periode = demander_entier("  Durée de la période, en jours ?", 1)
            if periode is None:
                return None
            return {"type": "correspondance", "coups": coups,
                    "periode": periode}
        if choix in ("c", "capital"):
            capital = demander_entier("  Capital de départ, en jours ?", 0)
            if capital is None:
                return None
            increment = demander_increment()
            if increment is None:
                return None
            plafond = demander_entier("  Plafond du capital, en jours ? "
                                      "(Entrée : aucun)", 1, vide=0)
            if plafond is None:
                return None
            reserve = demander_entier("  Réserve à côté du capital, en "
                                      "jours ? (Entrée : aucune)", 1, vide=0)
            if reserve is None:
                return None
            cadence = cadence_a_capital(capital, increment, plafond, reserve)
            if cadence is not None:
                return cadence
            sys.stderr.write("  Cadence incohérente : il faut un capital ou "
                             "un incrément, et un plafond au moins égal au "
                             "capital de départ.\n")
            continue
        sys.stderr.write("  Réponse attendue : d, p ou c.\n")


def demander_increment() -> int | None:
    """
    Asks for the increment per move, with its unit, and returns it in
    hours: "36h" gives 36, "3j" gives 72. The question is asked again as
    long as the answer does not have this form. Returns None at the end of
    the stream.
    """
    while True:
        reponse = demander("  Incrément par coup, avec son unité, 36h ou 3j "
                           "par exemple ?")
        if reponse is None:
            return None
        trouve = RE_INCREMENT.fullmatch(reponse.casefold())
        if trouve:
            return heures_increment(int(trouve.group(1)), trouve.group(2))
        sys.stderr.write("  Réponse attendue : un nombre entier suivi de h "
                         "ou de j.\n")


def est_pseudo(nom: str, pseudos: list[str]) -> bool:
    """True if the tag contains one of the usernames, ignoring case."""
    nom = nom.casefold()
    return any(pseudo.casefold() in nom for pseudo in pseudos)


def completer_entetes(partie: chess.pgn.Game, pseudos: list[str]) -> dict:
    """
    Gets the player's side from the White and Black tags, or asks for it.

    Only empty tags or tags set to "?" are filled in: the first username
    for the player's side, the name given for the opponent. A name already
    present is never replaced. Returns the side ("Blancs", "Noirs" or
    None), the origin of the information and the list of modified tags.

    `pseudos` may be empty, when neither --pseudos nor the settings give
    any: the side is then always asked, and so is the player's name if
    its tag is empty.
    """
    moi_blancs = est_pseudo(partie.headers.get("White", "?"), pseudos)
    moi_noirs = est_pseudo(partie.headers.get("Black", "?"), pseudos)
    if moi_blancs != moi_noirs:
        return {"camp": "Blancs" if moi_blancs else "Noirs",
                "origine": "déduit des en-têtes", "modifiees": []}

    # No username found, or both: only the player can decide. An unreadable
    # answer makes the question come again, Ctrl-D gives up on it.
    camp = None
    while camp is None:
        reponse = demander("Avez-vous joué les Blancs ou les Noirs ? [b/n]")
        if reponse is None:
            return {"camp": None, "origine": "non déclaré", "modifiees": []}
        choix = reponse.casefold()
        if choix in ("b", "blanc", "blancs", "w", "white"):
            camp = "Blancs"
        elif choix in ("n", "noir", "noirs", "black"):
            camp = "Noirs"

    modifiees = []
    mienne, autre = (("White", "Black") if camp == "Blancs"
                     else ("Black", "White"))
    if partie.headers.get(mienne, "?").strip() in ("", "?"):
        if pseudos:
            partie.headers[mienne] = pseudos[0]
            modifiees.append(mienne)
        else:
            # No known username: pseudos[0] raised IndexError. We ask
            # for the name, as for the opponent, and "?" leaves the tag
            # as it is.
            nom = demander("Votre nom de joueur ?", "?", nom=True)
            if nom and nom != "?":
                partie.headers[mienne] = nom
                modifiees.append(mienne)
    if partie.headers.get(autre, "?").strip() in ("", "?"):
        nom = demander("Nom de l'adversaire ?", "?", nom=True)
        if nom and nom != "?":
            partie.headers[autre] = nom
            modifiees.append(autre)
    return {"camp": camp, "origine": "déclaré", "modifiees": modifiees}


def recueillir_contexte(partie: chess.pgn.Game, camp: dict,
                        cadence_habituelle: dict | None = None) -> str:
    """
    Asks the time control question if the TimeControl tag does not give
    it, then the four startup questions of the project, and writes the
    text of contexte.md. `cadence_habituelle`, taken from the settings, is
    the time control that the question suggests; without it, it is "non
    précisée". A TimeControl tag of a common form is quoted, then
    translated.

    "(défaut)" marks an answer confirmed with Enter: the analyst thus
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

    lignes = [("Réponses du joueur aux questions de démarrage, recueillies "
               "par le script avant la collecte. \"(défaut)\" signale une "
               "réponse validée par Entrée."), ""]
    if camp.get("camp"):
        lignes.append("- Camp du joueur : %s, %s"
                      % (camp["camp"], camp["origine"]))
    else:
        lignes.append("- Camp du joueur : inconnu, non déclaré")

    # "-" is the value that TimeControl sometimes takes for a correspondence
    # game: it does not tell the real time control, so we ask for it.
    controle = partie.headers.get("TimeControl", "?").strip()
    if controle not in ("", "?", "-"):
        # "600+5" reads badly: ten minutes, or six hundred? The tag is
        # quoted as it is, then translated when its form allows it.
        lue = cadence_de_balise(controle)
        lignes.append("- Cadence : balise TimeControl `%s`%s"
                      % (controle,
                         ", soit %s" % decrire_cadence(lue) if lue else ""))
    else:
        habituelle = cadence_habituelle or dict(CADENCE_INCONNUE)
        saisie = (None if fin_de_flux
                  else demander_cadence("Cadence de la partie", habituelle))
        if saisie is None:
            fin_de_flux = True
            saisie = (habituelle, True)
        lignes.append("- Cadence : %s%s"
                      % (decrire_cadence(saisie[0]),
                         " (défaut)" if saisie[1] else ""))
    for libelle, question, valeur in QUESTIONS_CONTEXTE:
        reponse, defaut = poser(question, valeur)
        lignes.append("- %s : %s%s"
                      % (libelle, reponse, " (défaut)" if defaut else ""))
    return "\n".join(lignes) + "\n"


# ===========================================================================
# User settings
#
# What depends on the person, and not on the game, lives in a small file
# in INI format, readable and editable by hand:
#
#     [joueur]
#     pseudos = MonPseudo, AutrePseudo
#     cadence = rapide, 15 minutes
#
# It is created on the first run in a terminal, by two questions asked
# only once. Outside a terminal, nothing is asked or written: the script
# makes do with what the file already contains.
# ===========================================================================

def chemin_reglages(chemin: str) -> pathlib.Path:
    """Path of the settings file, with the tilde expanded."""
    return pathlib.Path(os.path.expanduser(chemin))


def purger_reglages(chemin: str) -> None:
    """
    Deletes the settings file, and that file only: its directory stays in
    place, it may contain something else.

    The settings questions will be asked again on the next run in a
    terminal. A missing file is not an error: the goal, having no settings
    any more, is already reached. A directory, or anything that is not a
    file, is refused rather than deleted.

    With --reglages, the path comes from the command line: a typo must not
    destroy another file. Only a file that carries the [joueur] section,
    or an empty file, is deleted. The section is looked up in the raw
    text: a damaged settings file, which configparser would reject, thus
    stays deletable.
    """
    p = chemin_reglages(chemin)
    if not p.exists() and not p.is_symlink():
        journal("Aucun fichier de réglages à supprimer : %s" % p)
        return
    if not (est_fichier(p) or p.is_symlink()):
        raise SystemExit("--purge-reglages : %s n'est pas un fichier, rien "
                         "n'est supprimé." % p)
    try:
        brut = p.read_bytes()
    except OSError as e:
        raise SystemExit("--purge-reglages : lecture de %s impossible : %s. "
                         "Rien n'est supprimé." % (p, e)) from e
    en_tete = re.compile(rb"^[ \t]*\[%s\][ \t]*\r?$"
                         % re.escape(REGLAGES_SECTION).encode("ascii"),
                         re.MULTILINE)
    if brut.strip() and not en_tete.search(brut):
        raise SystemExit("--purge-reglages : %s n'est pas un fichier de "
                         "réglages, il ne porte pas la section [%s]. Rien "
                         "n'est supprimé." % (p, REGLAGES_SECTION))
    try:
        p.unlink()
    except OSError as e:
        raise SystemExit("--purge-reglages : suppression de %s impossible : "
                         "%s" % (p, e)) from e
    journal("Réglages supprimés : %s. Ils seront redemandés à la prochaine "
            "collecte lancée sur un terminal." % p)


def lire_reglages(chemin: str) -> configparser.ConfigParser:
    """
    Loads the settings file, or empty settings if it does not exist.

    The file goes through the same decoding as the PGN: its encoding does
    not matter. A file that configparser rejects stops the script with a
    clear message, rather than being silently ignored. The [joueur]
    section always exists in the returned object.
    """
    # interpolation=None: the percent sign of a value stays a plain
    # character, it triggers no substitution.
    reglages = configparser.ConfigParser(interpolation=None)
    p = chemin_reglages(chemin)
    if est_fichier(p):
        texte = lire_fichier_texte(p, "réglages")[0]
        try:
            reglages.read_string(texte, source=str(p))
        except configparser.Error as err:
            raise SystemExit(
                "Réglages illisibles : %s\n"
                "Corrigez %s, ou supprimez-le : il sera recréé au prochain "
                "lancement sur un terminal."
                % (nettoyer_valeur(str(err)), p)) from err
    if not reglages.has_section(REGLAGES_SECTION):
        reglages.add_section(REGLAGES_SECTION)
    return reglages


def reglage(reglages: configparser.ConfigParser, clef: str) -> str:
    """Value of a key of the [joueur] section, empty if it is missing."""
    return reglages.get(REGLAGES_SECTION, clef, fallback="").strip()


def decouper_pseudos(texte: str) -> list[str]:
    """List of usernames taken from a comma-separated string."""
    return [x.strip() for x in texte.split(",") if x.strip()]


def ecrire_reglages(chemin: str, reglages: configparser.ConfigParser) -> bool:
    """
    Writes the settings file, comments included.

    The known keys come first, each one under its comment; the other keys
    of [joueur] and the other sections, which you may have added, are
    copied after them. A failure to write does not stop the collection: it
    is reported, and the question will be asked again on the next run.
    Returns true if the file was written.
    """
    def ligne(clef: str, valeur: str) -> str:
        # A value on several lines continues with indented lines: this is
        # the form that configparser can read back.
        valeur = valeur.replace("\n", "\n\t")
        return "%s = %s" % (clef, valeur) if valeur else "%s =" % clef

    out = ["# Réglages de ianalyze.py.",
           "# Vous pouvez modifier ce fichier à la main. Une clef supprimée",
           "# sera redemandée au prochain lancement sur un terminal.",
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
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        ecrire_texte(p, "\n".join(out) + "\n")
    except OSError as err:
        journal("Attention : réglages non enregistrés dans %s : %s"
                % (p, err))
        return False
    return True


def completer_reglages(chemin: str, reglages: configparser.ConfigParser,
                       pseudos_cli: list[str] | None) -> None:
    """
    Asks, only once, for the settings that the file does not give.

    Called only on an interactive terminal. Each key missing from
    [joueur] gets a question; a key that is present, even empty, is never
    asked for again. The usernames passed with --pseudos serve as the
    suggested answer. An end of stream (Ctrl-D) gives up without writing
    anything: the questions will come back on the next run.
    """
    manquantes = [clef for clef, _ in REGLAGES_CLEFS
                  if not reglages.has_option(REGLAGES_SECTION, clef)]
    # A time control that is present but unreadable, written by hand or
    # inherited from a version that accepted free text, is asked for
    # again too: it must not go to the analyst as it is.
    brute = reglages.get(REGLAGES_SECTION, "cadence", fallback=None)
    if brute is not None and analyser_cadence(brute) is None:
        journal("Réglages : la cadence enregistrée, \"%s\", n'est pas "
                "lisible, elle est redemandée." % nettoyer_valeur(brute))
        manquantes.append("cadence")
    # The same goes for the rating, which must be a number of Elo points.
    brute = reglages.get(REGLAGES_SECTION, "niveau", fallback=None)
    if brute is not None and analyser_niveau(brute) is None:
        journal("Réglages : le niveau enregistré, \"%s\", n'est pas "
                "lisible, il est redemandé." % nettoyer_valeur(brute))
        manquantes.append("niveau")
    if not manquantes:
        return

    journal("Réglages : %d réponse(s) à donner une seule fois, gardée(s) "
            "dans %s." % (len(manquantes), chemin_reglages(chemin)))
    for clef in manquantes:
        if clef == "pseudos":
            if pseudos_cli:
                reponse = demander("Votre pseudo de joueur, ou plusieurs "
                                   "séparés par des virgules ?",
                                   ", ".join(pseudos_cli), nom=True)
            else:
                reponse = demander("Votre pseudo de joueur, ou plusieurs "
                                   "séparés par des virgules ? (Entrée : "
                                   "aucun)", nom=True)
            if reponse is not None:
                reponse = ", ".join(decouper_pseudos(reponse))
        elif clef == "niveau":
            niveau = demander_niveau()
            if niveau is None:
                reponse = None
            else:
                reponse = str(niveau) if niveau else "inconnu"
        else:
            saisie = demander_cadence("Votre cadence habituelle",
                                      dict(CADENCE_INCONNUE))
            reponse = None if saisie is None else noter_cadence(saisie[0])
        if reponse is None:
            journal("Réglages non enregistrés : saisie interrompue.")
            return
        reglages.set(REGLAGES_SECTION, clef, reponse)

    if ecrire_reglages(chemin, reglages):
        journal("Réglages enregistrés : %s" % chemin_reglages(chemin))


# ===========================================================================
# Analysis prompt
#
# The data of the archive are not enough: the analyst must be told what
# to do with them. This text lives in a template, prompt-modele.txt,
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
#     #! si CONDITION     keeps what follows if the condition is true
#     #! si non CONDITION keeps what follows if it is false
#     #! sinon            switches
#     #! fin              closes the last open "si"
#     #! note ...         comment of the template, never copied
#
# The "si" can be nested.
# ===========================================================================

def chemin_modele(option: str | None, seul: bool = False) -> pathlib.Path:
    """
    Path of the prompt template: the one of --prompt, otherwise, next to
    the script, prompt-modele.txt or, with --prompt-seul, the short
    template prompt-seul-modele.txt. The real path of the script is
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
    unknown directive, a "si" never closed, a condition or a value that
    the script does not know stop the script with the line number. The
    extra blank lines left by a removed passage are tightened.
    """
    def erreur(numero: int, message: str) -> SystemExit:
        return SystemExit("Modèle de prompt %s, ligne %d : %s"
                          % (source, numero, message))

    sortie: list[str] = []
    # Stack of the open "si": the line of the "si", the value of its
    # condition, and whether a "sinon" has already been met.
    pile: list[tuple[int, bool, bool]] = []
    for numero, ligne in enumerate(texte.split("\n"), start=1):
        mots = lire_directive(ligne)
        if mots is None:
            for nom in RE_VALEUR_MODELE.findall(ligne):
                if nom not in PROMPT_VALEURS:
                    raise erreur(numero, "valeur inconnue {{%s}}, valeurs "
                                 "admises : %s"
                                 % (nom, ", ".join(PROMPT_VALEURS)))
            # Double braces that remain once the recognized markers
            # are removed: a badly written marker, {{ NIVEAU }} or
            # {{CAMP1}}, which would go as it is into the prompt.
            reste = RE_VALEUR_MODELE.sub("", ligne)
            if "{{" in reste or "}}" in reste:
                raise erreur(numero, "repère mal formé, forme attendue : "
                             "{{NOM}}, en majuscules et sans espace")
            if all(vrai for _, vrai, _ in pile):
                sortie.append(RE_VALEUR_MODELE.sub(
                    lambda m: valeurs[m.group(1)], ligne).rstrip())
            continue
        if not mots or mots[0] == "note":
            continue
        if mots[0] == "si":
            negation = len(mots) == 3 and mots[1] == "non"
            if len(mots) != (3 if negation else 2):
                raise erreur(numero, "forme attendue : \"si CONDITION\" ou "
                             "\"si non CONDITION\"")
            if mots[-1] not in PROMPT_CONDITIONS:
                raise erreur(numero, "condition inconnue %s, conditions "
                             "admises : %s"
                             % (mots[-1], ", ".join(PROMPT_CONDITIONS)))
            pile.append((numero, conditions[mots[-1]] != negation, False))
        elif mots == ["sinon"]:
            if not pile or pile[-1][2]:
                raise erreur(numero, "\"sinon\" sans \"si\" ouvert, ou en "
                             "double")
            pile[-1] = (pile[-1][0], not pile[-1][1], True)
        elif mots == ["fin"]:
            if not pile:
                raise erreur(numero, "\"fin\" sans \"si\" ouvert")
            pile.pop()
        else:
            raise erreur(numero, "directive inconnue \"%s\", directives "
                         "admises : si, sinon, fin, note" % " ".join(mots))
    if pile:
        raise erreur(pile[-1][0], "ce \"si\" n'est jamais fermé par \"fin\"")

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
        raise SystemExit("Modèle de prompt %s : il ne contient aucune "
                         "ligne de texte." % source)


def decrire_niveau(niveau: int, partie: chess.pgn.Game,
                   camp: str | None) -> str:
    """
    Sentence of the player's rating. The rating declared in the settings
    wins; failing that, the Elo of the player's tag in this game, if their
    side is known; otherwise nothing precise.
    """
    if niveau:
        return "environ %d Elo, déclaré par le joueur" % niveau
    balise = {"Blancs": "WhiteElo", "Noirs": "BlackElo"}.get(camp or "")
    if balise:
        elo = partie.headers.get(balise, "").strip()
        if re.fullmatch(r"[0-9]{3,4}", elo):
            return "%s Elo, d'après la balise %s de la partie" % (elo, balise)
    return ("non précisé : jugez-en d'après la partie, et restez "
            "accessible")


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
                  else " --catalogue %s" % repertoire)
    return "%s --installer-catalogue%s" % (os.path.abspath(__file__),
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
        url = CATALOGUE_SOURCE.format(partie=morceau)
        journal("Téléchargement du catalogue : %s" % url)
        requete = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(requete, timeout=delai) as reponse:
                # utf-8-sig: a byte order mark at the start of the
                # file is ignored instead of corrupting the header.
                texte = reponse.read().decode("utf-8-sig", errors="strict")
        except urllib.error.HTTPError as err:
            raise SystemExit("Catalogue : HTTP %d pour %s."
                             % (err.code, url)) from err
        except (OSError, http.client.HTTPException) as err:
            # URLError is a subclass of OSError, as for the PGN export.
            raise SystemExit("Catalogue injoignable : %s"
                             % getattr(err, "reason", err)) from err
        except UnicodeDecodeError as err:
            raise SystemExit("Catalogue : %s n'est pas en UTF-8." % url) \
                from err

        lecteur = csv.DictReader(io.StringIO(texte), delimiter="\t")
        if lecteur.fieldnames != ["eco", "name", "pgn"]:
            raise SystemExit("Catalogue : en-tête inattendu dans %s : %s"
                             % (url, lecteur.fieldnames))

        lignes_fichier = 0
        # Line 1 is the header, the numbering follows that of the file.
        for numero, ligne in enumerate(lecteur, start=2):
            eco = (ligne.get("eco") or "").strip()
            nom = (ligne.get("name") or "").strip()
            coups = [j for j in (ligne.get("pgn") or "").split()
                     if not RE_NUMERO_COUP.fullmatch(j)]
            if not eco or not nom or not coups:
                raise SystemExit("Catalogue : ligne %d de %s incomplète."
                                 % (numero, url))

            plateau = chess.Board()
            for san in coups:
                try:
                    plateau.push_san(san)
                except ValueError as err:
                    raise SystemExit("Catalogue : coup %s illisible ou "
                                     "illégal, ligne %d de %s : %s"
                                     % (san, numero, url, err)) from err
                # Intermediate position: known, without a name, unless another
                # line has already named it.
                positions.setdefault(plateau.epd(), ("", ""))

            epd = plateau.epd()
            if positions[epd][1]:
                raise SystemExit("Catalogue : position nommée deux fois, "
                                 "%s et %s (ligne %d de %s)."
                                 % (positions[epd][1], nom, numero, url))
            positions[epd] = (eco, nom)
            lignes_fichier += 1

        if lignes_fichier == 0:
            raise SystemExit("Catalogue : %s ne contient aucune ligne." % url)
        nb_lignes += lignes_fichier

    nommees = sum(1 for _, nom in positions.values() if nom)
    date = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    entete = "\t".join(("#format=%s" % CATALOGUE_FORMAT, "date=%s" % date,
                        "lignes=%d" % nb_lignes, "nommees=%d" % nommees,
                        "connues=%d" % len(positions),
                        "source=%s" % CATALOGUE_SOURCE))

    cible = chemin_catalogue(repertoire)
    temporaire: pathlib.Path | None = None
    try:
        cible.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         dir=cible.parent,
                                         prefix=".catalogue-",
                                         suffix=".tmp",
                                         delete=False) as tmp:
            temporaire = pathlib.Path(tmp.name)
            tmp.write(entete + "\n")
            tmp.write("epd\teco\tnom\n")
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
        raise SystemExit("Écriture du catalogue impossible dans %s : %s"
                         % (cible.parent, err)) from err

    # Full read-back through the normal path: what has just been written
    # must load exactly as it does during a collection.
    catalogue = lire_catalogue(repertoire)
    journal("Catalogue installé : %s lignes, %s positions nommées, %s "
            "positions connues, dans %s"
            % (catalogue.meta["lignes"], catalogue.meta["nommees"],
               catalogue.meta["connues"], cible))


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
            "Catalogue des ouvertures absent : %s introuvable.\n\n"
            "Installez-le en une commande :\n"
            "    %s\n" % (chemin, commande_catalogue(repertoire)))
    reparer = "Réinstallez-le avec : %s" % commande_catalogue(repertoire)

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
                    raise SystemExit("Catalogue corrompu, ligne %d de %s.\n%s"
                                     % (numero, chemin, reparer))
                positions[champs[0]] = (champs[1], champs[2])
    except (OSError, UnicodeDecodeError) as err:
        raise SystemExit("Catalogue illisible (%s) : %s\n%s"
                         % (chemin, err, reparer)) from err

    if not premiere.startswith("#"):
        raise SystemExit("Catalogue sans description, %s.\n%s"
                         % (chemin, reparer))
    meta = dict(champ.partition("=")[::2]
                for champ in premiere[1:].split("\t"))
    if meta.get("format") != CATALOGUE_FORMAT or entete != "epd\teco\tnom":
        raise SystemExit("Catalogue de format inconnu, %s.\n%s"
                         % (chemin, reparer))
    if meta.get("connues") != str(len(positions)):
        raise SystemExit("Catalogue tronqué : %s positions annoncées, %d "
                         "lues dans %s.\n%s"
                         % (meta.get("connues"), len(positions), chemin,
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
        a dictionary carrying the key "_erreur", the code being 0 when no HTTP
        code could be obtained.
        """
        # Courtesy pause. The endpoint is strict about the rate, but there
        # is no point in waiting before the very first request.
        if not self._premiere:
            time.sleep(self.pause)
        self._premiere = False

        # All the moves of the database, and not the first ten: a move
        # played beyond the tenth rank otherwise passed for absent (0
        # games, rank "hors base") while it was only rarer. The server
        # truncates at this value without a cap of its own, and 256
        # amply covers all the legal moves of a position.
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
                        return 0, {"_erreur": "réponse JSON inattendue, "
                                              "objet attendu"}
                    return r.status, donnees
            except urllib.error.HTTPError as err:
                if 300 <= err.code < 400:
                    return err.code, {"_erreur": "redirection refusée : le "
                                      "jeton n'est envoyé qu'à l'adresse "
                                      "de l'explorateur"}
                # The body of the error is only read for the message: if it
                # is cut or too slow, the HTTP error stays what it
                # is, and only the query stops.
                try:
                    corps = err.read().decode("utf-8-sig", errors="replace")
                except (OSError, http.client.HTTPException):
                    corps = ""
                if err.code == 429 and tentative == 1:
                    journal("429 reçu, pause de 60 secondes.")
                    time.sleep(60)
                    continue
                return err.code, {"_erreur": expurger(corps, self.jeton)[:500]}
            except (OSError, http.client.HTTPException) as err:
                return 0, {"_erreur": expurger(
                    str(getattr(err, "reason", err)), self.jeton)}
            except ValueError as err:
                return 0, {"_erreur": "réponse non JSON : %s" % err}
            except RecursionError:
                # A JSON nested thousands of levels deep.
                return 0, {"_erreur": "réponse non JSON : imbrication "
                                      "démesurée"}
        return 0, {"_erreur": "échec après reprise"}


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
    if n == 0:
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

      - an unusable answer, or an empty sample, which means that the
        position is unknown to the database;
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
    """
    brut = dossier / "explorateur"
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
            arret = ("plafond de %d demi-coups atteint (option "
                     "--max-demicoups)" % plafond_demicoups)
            break

        numero = plateau.fullmove_number
        trait = "Blancs" if plateau.turn == chess.WHITE else "Noirs"
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
            arret = ("coup nul au demi-coup %d : ce n'est pas un coup des "
                     "échecs, l'explorateur ne peut pas suivre la partie au "
                     "delà" % (indice + 1))
            journal("Explorateur : %s." % arret)
            non_exploitables.append({
                "demicoup": indice + 1, "numero": numero, "trait": trait,
                "san": san_joue, "motif": "coup nul, non interrogé",
            })
            break

        # The explorer writes castling the Chess960 way, "king takes rook":
        # e1h1 for White's short castling, where python-chess writes e1g1.
        # Both forms are accepted to find the played move in the answer,
        # otherwise a castling move passed for absent from the database (0
        # games, rank "hors base") and triggered a false exit from theory.
        # For any other move, they are identical. The move list sent to
        # the explorer, for its part, does not change.
        uci_admis = (uci_joue, plateau.uci(coup, chess960=True))

        journal("Explorateur : demi-coup %d (%s)" % (indice + 1, san_joue))
        code, donnees = explorateur.interroger(joues_uci)

        # Systematic saving of the raw data, even on error: this will save
        # you from running the whole collection again to understand a failure.
        fichier = brut / ("%03d-%s.json" % (indice + 1, uci_joue))
        ecrire_texte(fichier,
                     json.dumps(donnees, ensure_ascii=False, indent=1))

        if code != 200:
            if code == 0:
                motif = "réponse inexploitable : %s" % donnees.get("_erreur")
            else:
                motif = "HTTP %s" % code
            arret = "%s au demi-coup %d" % (motif, indice + 1)
            journal("Explorateur : %s, arrêt de la collecte." % arret)
            non_exploitables.append({
                "demicoup": indice + 1, "numero": numero, "trait": trait,
                "san": san_joue, "motif": motif,
            })
            break

        total = total_parties(donnees)

        # Position unknown to the database: the explorer answers 200 with an
        # empty sample, there is nothing more to get from it.
        if total == 0:
            arret = ("position inconnue de la base au demi-coup %d, "
                     "échantillon nul" % (indice + 1))
            journal("Explorateur : %s." % arret)
            non_exploitables.append({
                "demicoup": indice + 1, "numero": numero, "trait": trait,
                "san": san_joue, "motif": "position absente de la base",
            })
            break

        if not jusqu_a_epuisement and total < seuil_parties:
            non_exploitables.append({
                "demicoup": indice + 1, "numero": numero, "trait": trait,
                "san": san_joue,
                "motif": "%d parties, seuil %d" % (total, seuil_parties),
            })
            arret = ("échantillon insuffisant au demi-coup %d : %d parties "
                     "pour un seuil de %d"
                     % (indice + 1, total, seuil_parties))
            journal("Explorateur : %s." % arret)
            break

        # Search for the played move among the moves known to the database.
        # Entries of an unexpected type are ignored rather than fatal.
        # The same goes for a "moves" key that would not be a list:
        # an integer cannot be iterated, and the loop then raised TypeError.
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
            "demicoup": indice + 1,
            "numero": numero,
            "trait": trait,
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
                arret = ("sortie de théorie au demi-coup %d : %s joué à "
                         "%.1f %%, seuil %.1f %%%s"
                         % (indice + 1, san_joue, frequence, seuil_frequence,
                            ", hors catalogue" if catalogue is not None
                            else ""))
                journal("Explorateur : %s." % arret)
                break

    if arret is None:
        arret = "fin de la partie"

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
    if blanc.is_mate():
        coups = blanc.mate()
        if trait is not None and (coups > 0) == (trait == chess.WHITE):
            coups += -1 if coups > 0 else 1
            if coups == 0:
                return "#+0" if trait == chess.WHITE else "#-0"
        return "#%+d" % coups
    return "%+.2f" % (blanc.score() / 100.0)


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


def wdl_blancs(info: dict) -> dict | None:
    """White's chances of winning, drawing and losing, per thousand."""
    wdl = info.get("wdl")
    if wdl is None:
        return None
    blancs = wdl.white()
    return {"gain": blancs.wins, "nulle": blancs.draws,
            "perte": blancs.losses}


def nature_coup(ecart: float | None) -> str | None:
    """Inaccuracy, mistake or blunder according to the loss in centipawns."""
    if ecart is None:
        return None
    if ecart >= SEUIL_GAFFE:
        return "gaffe"
    if ecart >= SEUIL_ERREUR:
        return "erreur"
    if ecart >= SEUIL_IMPRECISION:
        return "imprécision"
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
        return ", reste moins d'une minute"
    minutes = int(reste / 60 + 0.5)
    if minutes < 60:
        return ", reste environ %d min" % minutes
    return ", reste environ %d h %02d" % divmod(minutes, 60)


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
        raise SystemExit("Stockfish introuvable : %s. Installez-le (%s), "
                         "ou indiquez son chemin avec --stockfish. "
                         "L'évaluation du moteur fait partie de toute "
                         "collecte."
                         % (binaire, AIDE_STOCKFISH))
    if not os.access(binaire, os.X_OK):
        raise SystemExit("Stockfish non exécutable : %s" % binaire)


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
        raise SystemExit("Impossible de lancer le moteur %s : %s"
                         % (binaire, str(err)
                            or "pas de réponse UCI dans le délai")) from err


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
    Checks --fils, --hachage and --multipv with the engine itself, before
    any collection.

    The engine announces its options and their bounds as soon as it
    starts: a value out of bounds, or an option it does not know, is
    refused here rather than after the whole explorer phase, which may
    last several minutes. Nothing is configured, so no hash table is
    allocated: the engine is only started, queried, then stopped.
    """
    moteur = lancer_moteur(binaire)
    try:
        for drapeau, option, valeur in (("--fils", "Threads", fils),
                                        ("--hachage", "Hash", hachage),
                                        ("--multipv", "MultiPV", multipv)):
            annonce = moteur.options.get(option)
            if annonce is None:
                raise SystemExit("Le moteur %s ne connaît pas l'option UCI "
                                 "%s, requise par %s."
                                 % (binaire, option, drapeau))
            mini, maxi = annonce.min, annonce.max
            if ((mini is not None and valeur < mini)
                    or (maxi is not None and valeur > maxi)):
                raise SystemExit("%s : %d est hors des bornes du moteur %s, "
                                 "qui admet de %s à %s pour %s."
                                 % (drapeau, valeur, binaire, mini, maxi,
                                    option))
    finally:
        fermer_moteur(moteur)


def decrire_variante(plateau: chess.Board, info: dict, trait: bool) -> dict:
    """
    Formats a line returned by the engine: first move, score, numeric
    value for the side to move, depth reached and full principal
    variation, in UCI and in numbered algebraic notation.
    """
    pv = list(info.get("pv") or [])
    try:
        pv_san = plateau.variation_san(pv)
    except ValueError:
        # Variation that python-chess refuses to replay: we keep the raw UCI
        # rather than lose the information.
        pv_san = " ".join(m.uci() for m in pv)
    return {
        "san": plateau.san(pv[0]),
        "uci": pv[0].uci(),
        "score": formater_score(info["score"], trait),
        "valeur_trait": valeur_pour_trait(info["score"], trait),
        "profondeur": info.get("depth"),
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
        journal("Stockfish : évaluation de %d demi-coups, profondeur %d, "
                "multipv %d, threads %d. C'est la phase la plus longue."
                % (demicoups, profondeur, multipv, fils))
        debut = time.monotonic()
        for indice, coup in enumerate(coups[:demicoups]):
            trait = plateau.turn
            numero = plateau.fullmove_number
            san_joue = plateau.san(coup)
            fen = plateau.fen()

            journal("Stockfish : demi-coup %d/%d (%s)%s"
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
                    "valeur_trait": None, "profondeur": None,
                    "pv_uci": [], "pv_san": "", "wdl": None,
                    "non_evalue": True,
                }
            if eval_joue is None:
                info = moteur.analyse(plateau, limite, root_moves=[coup])
                if isinstance(info, list):
                    info = info[0]
                if "score" not in info:
                    raise SystemExit("Le moteur n'a renvoyé aucune "
                                     "évaluation pour %s au demi-coup %d."
                                     % (san_joue, indice + 1))
                if not info.get("pv"):
                    info = dict(info, pv=[coup])
                eval_joue = decrire_variante(plateau, info, trait)

            ecart = None
            if meilleurs and eval_joue["valeur_trait"] is not None:
                ecart = ecart_au_meilleur(meilleurs[0]["valeur_trait"],
                                          eval_joue["valeur_trait"])

            resultats.append({
                "demicoup": indice + 1,
                "numero": numero,
                "trait": "Blancs" if trait == chess.WHITE else "Noirs",
                "joue": eval_joue,
                "meilleurs": meilleurs,
                "ecart_cp": ecart,
                "nature": nature_coup(ecart),
                "fen": fen,
            })
            plateau.push(coup)
        journal("Stockfish : terminé en %d min %02d s."
                % divmod(int(time.monotonic() - debut), 60))
    except chess.engine.EngineError as err:
        raise SystemExit("Le moteur a échoué en cours d'analyse : %s"
                         % (err or type(err).__name__)) from err
    except concurrent.futures.CancelledError as err:
        # The engine died outside a search, during a setting for
        # example: python-chess then cancels the pending command instead
        # of raising an EngineError. The most common cause is a hash
        # table that the system refuses to allocate.
        raise SystemExit("Le moteur a échoué en cours d'analyse : il s'est "
                         "arrêté sans répondre. Si --hachage ou --fils "
                         "sont élevés, la mémoire a pu manquer.") from err
    finally:
        # Safe stop in every case: see fermer_moteur.
        fermer_moteur(moteur)

    brut = dossier / "stockfish"
    brut.mkdir(parents=True, exist_ok=True)
    ecrire_texte(brut / "evaluations.json",
                 json.dumps(resultats, ensure_ascii=False, indent=1))

    return {
        "resultats": resultats,
        "profondeur": profondeur,
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
    vainqueur = {"1-0": "Blancs", "0-1": "Noirs"}.get(
        partie.headers.get("Result", ""))
    if vainqueur is None or not resultats:
        return None
    dernier = resultats[-1]
    valeur = dernier["joue"].get("valeur_trait")
    # The rank of the ply is compared with the number of moves played,
    # counted right here, and not with a numbering taken from the PGN.
    joues = sum(1 for _ in partie.mainline_moves())
    if valeur is None or dernier["demicoup"] != joues:
        return None
    # valeur_trait is read from the side of the one who has just played.
    pour_blancs = valeur if dernier["trait"] == "Blancs" else -valeur
    pour_vainqueur = pour_blancs if vainqueur == "Blancs" else -pour_blancs
    if pour_vainqueur > -SEUIL_GAFFE:
        return None
    perdant = "Noirs" if vainqueur == "Blancs" else "Blancs"
    phrase = (
        "**Résultat et évaluation finale se contredisent.** La partie est "
        "notée `%s`, victoire des %s, alors que Stockfish donne %s après "
        "le dernier coup, %d%s %s, soit un net avantage aux %s. Le "
        "résultat ne vient donc pas de la position sur l'échiquier : "
        "abandon, temps écoulé, ou autre cause que le PGN ne dit pas."
        % (partie.headers["Result"], vainqueur, dernier["joue"]["score"],
           dernier["numero"], "." if dernier["trait"] == "Blancs" else "...",
           dernier["joue"]["san"], perdant))
    fin = nettoyer_valeur(partie.headers.get("Termination", ""))
    if fin and fin != "?":
        phrase += " La balise Termination vaut `%s`." % fin
    return phrase


def _ecart(ecart: float | None) -> str:
    """
    "Écart cp" cell of the Stockfish table.

    A missing loss gives a dash. From SEUIL_ECART_MAT on, the loss comes
    from a mate brought down to a bounded value, whether the played move
    misses a mate or concedes one: the cell carries "mat" instead of a
    number of centipawns that would make no sense, the Éval and 1er
    columns giving both scores.
    """
    if ecart is None:
        return "-"
    if ecart >= SEUIL_ECART_MAT:
        return "mat"
    return "%.0f" % ecart


def _gnp(wdl: dict | None, pour_noirs: bool = False) -> str:
    """Win, draw and loss as a rounded percentage, for White or for Black."""
    if not wdl:
        return "-"
    gain, nulle, perte = wdl["gain"], wdl["nulle"], wdl["perte"]
    if pour_noirs:
        gain, perte = perte, gain
    return "%d/%d/%d" % (round(gain / 10), round(nulle / 10),
                         round(perte / 10))


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
    for couleur, nom in ((chess.WHITE, "Blancs"), (chess.BLACK, "Noirs")):
        r = roques[couleur]
        lignes.append("- Roque des %s : %s au coup %d (demi-coup %d)."
                      % (nom, r[2], r[1], r[0]) if r
                      else "- Les %s n'ont pas roqué." % nom)
    lignes.append("- Plus aucune dame sur l'échiquier après le coup %d "
                  "(demi-coup %d)." % (sans_dames[1], sans_dames[0])
                  if sans_dames
                  else "- Des dames restent sur l'échiquier jusqu'à la fin.")
    lignes.append("- Entrée en finale après le coup %d (demi-coup %d), "
                  "matériel hors pions de %d." % (finale[1], finale[0],
                                                  finale[2])
                  if finale else
                  "- Pas d'entrée en finale selon ce repère.")
    lignes.append("")
    lignes.append("Repère de finale : matériel hors pions et rois des deux "
                  "camps réunis à %d ou moins, avec N = B = 3, R = 5, "
                  "Q = 9." % SEUIL_FINALE)
    return lignes


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
        return plateau.variation_san(coups)
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
        tete = "%d%s %s" % (r["numero"],
                            "." if r["trait"] == "Blancs" else "...",
                            r["joue"]["san"])
        ligne = "%-13s %7s" % (tete, r["joue"]["score"])
        if r.get("nature") and r["meilleurs"]:
            meilleur = r["meilleurs"][0]
            ligne += "   %s (%s) : mieux %s (%s)" % (
                r["nature"], _ecart(r["ecart_cp"]),
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
               if r["trait"] == camp and r.get("nature") and r["meilleurs"])


def phrase_ouverture(explorateur: dict | None, libelle_base: str) -> str:
    """
    For the short prompt, the opening and the exit from theory in one
    sentence, taken from the explorer. Empty string if it gave nothing.
    """
    if explorateur is None:
        return ""
    sortie = explorateur["premiere_sortie"]
    limite = sortie["demicoup"] if sortie else len(explorateur["lignes"]) + 1
    nommees = [lg["ouverture"] for lg in explorateur["lignes"]
               if lg["demicoup"] < limite and lg.get("ouverture")]
    phrases = []
    if nommees:
        phrases.append("Ouverture : %s." % nommees[-1])
    if sortie:
        phrases.append(
            "La théorie est quittée au coup %d par les %s, avec %s, joué "
            "dans %s %% des parties de la base %s."
            % (sortie["numero"], sortie["trait"], sortie["san"],
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
        if ligne.startswith("- ") and not ligne.endswith("(défaut)")
        and not ligne.startswith(("- Camp du joueur",
                                  "- Cadence : balise TimeControl",
                                  "- Cadence : non précisée")))


def ecrire_synthese(chemin: pathlib.Path, partie: chess.pgn.Game,
                    source: str, consignes: str | None,
                    explorateur: dict | None, motif_sans_explorateur: str | None,
                    stockfish: dict, longueur_pv: int,
                    libelle_base: str = "maîtres",
                    filtres: dict[str, str] | None = None,
                    annexes: list[str] | None = None,
                    pgn_complete: bool = False) -> None:
    """
    Assembles the summary file in markdown, in the expected order.

    `libelle_base` names the database queried in the titles and the text;
    its default value reproduces word for word the summary of the masters
    database. `filtres`, given only for the Lichess database, is
    reproduced in section 2 so that the analyst knows which population of
    games the frequencies are about. `annexes` adds to section 5 the files
    produced in addition, contexte.md for example, and `pgn_complete`
    reports a partie.pgn whose headers were filled in.
    """
    out: list[str] = []
    a = out.append

    identifiant = partie.headers.get("Site", "").rstrip("/").split("/")[-1]
    if identifiant == "?":
        # python-chess gives "?" to a missing Site tag.
        identifiant = ""
    a("# Dossier d'analyse : %s"
      % (nettoyer_valeur(identifiant) or "partie locale"))
    a("")
    a("Collecte du %s. Source : `%s`."
      % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         nettoyer_valeur(source)))
    a("Ce fichier ne contient aucune analyse, uniquement des données "
      "collectées.")
    a("")

    # -- 0. Analysis instructions, if given ---------------------------------
    if consignes is not None:
        a("## Consignes d'analyse")
        a("")
        a("Les consignes ci-dessous accompagnent les données : elles "
          "décrivent l'analyse attendue à partir de ce dossier.")
        a("")
        a(consignes.strip())
        a("")

    # -- 1. Headers and moves of the game -----------------------------------
    a("## 1. En-têtes et coups de la partie")
    a("")
    a("| Champ | Valeur |")
    a("|---|---|")
    for cle, valeur in partie.headers.items():
        a("| %s | %s |" % (cle, nettoyer_valeur(valeur).replace("|", "\\|")))
    a("")
    a("Nombre de demi-coups dans la ligne principale : %d."
      % len(list(partie.mainline_moves())))
    a("")
    # The main line is reproduced without comments or variations, so
    # that this single file is enough for the analysis. The raw PGN, with
    # its possible original comments, stays in partie.pgn.
    exporteur = chess.pgn.StringExporter(headers=False, comments=False,
                                         variations=False, columns=78)
    a("```")
    a(partie.accept(exporteur).strip())
    a("```")
    a("")
    # Phase markers, computed from castling and material: they locate
    # the ends of phases that the analyst must comment on.
    a("Repères de phase, indicatifs :")
    a("")
    for ligne in reperes_phase(partie):
        a(ligne)
    a("")

    # -- 2. Exit from theory ------------------------------------------------
    a("## 2. Explorateur %s, sortie de théorie" % libelle_base)
    a("")
    if explorateur is None:
        a("Collecte de l'explorateur non effectuée : %s."
          % (motif_sans_explorateur or "désactivée"))
        a("")
    else:
        if filtres:
            # Lichess database: the frequencies depend entirely on the
            # filtered population, the analyst must know it.
            a("Base interrogée : **Lichess**, parties classées de "
              "l'ensemble des joueurs du site, et non la base maîtres. "
              "Cadences : `%s`. Tranches de classement : `%s` (moyenne des "
              "deux joueurs ; chaque tranche court de sa valeur à la "
              "suivante, `0` couvre 0 à 999, `2500` tout ce qui dépasse). "
              "Parties jouées depuis : `%s`."
              % (filtres.get("speeds", "toutes"),
                 filtres.get("ratings", "toutes"),
                 filtres.get("since", "le début")))
            a("")
        a("La base de l'explorateur est indexée **par position** et non par "
          "ordre des coups. Les transpositions sont donc fusionnées, et le "
          "nombre de parties peut parfaitement **augmenter** d'un demi-coup "
          "au suivant. Ne lisez pas la colonne des parties comme une suite "
          "décroissante.")
        a("")
        if explorateur["jusqu_a_epuisement"]:
            a("Mode `--jusqu-a-epuisement` : aucun seuil n'a été appliqué, "
              "l'interrogation est descendue aussi loin que la base a "
              "répondu.")
        else:
            a("Seuils appliqués : arrêt sous **%d parties** pour la "
              "position, et arrêt sous **%.1f %%** de fréquence pour le coup "
              "joué%s."
              % (explorateur["seuil_parties"], explorateur["seuil_frequence"],
                 ", sauf si ce coup reste dans une ligne du catalogue des "
                 "ouvertures nommées" if explorateur.get("catalogue")
                 else ""))
            if explorateur.get("demicoups_min", 0) > 0:
                a("")
                a("Fenêtre de départ (`--coups-min`) : aucun arrêt sur la "
                  "fréquence avant la fin du coup %d (demi-coup %d), le seuil "
                  "de parties restant actif. La table peut donc continuer "
                  "après la première sortie de théorie."
                  % ((explorateur["demicoups_min"] + 1) // 2,
                     explorateur["demicoups_min"]))
        cat = explorateur.get("catalogue")
        if cat:
            a("")
            a("Catalogue des ouvertures de Lichess, téléchargé le %s : %s "
              "positions nommées, %s positions connues en comptant les "
              "positions intermédiaires des lignes. La colonne Ouverture "
              "nomme la position atteinte par le coup joué ; "
              "`(intermédiaire)` signale une position de passage d'une "
              "ligne nommée, `-` une position hors catalogue."
              % (cat.get("date", "?"), cat.get("nommees", "?"),
                 cat.get("connues", "?")))
        a("")
        a("| # | Coup | Trait | Parties pos. | Joué | Rang | Fréq. | "
          "Score B. | Majoritaire | Fréq. majo | Score B. majo | "
          "Ouverture |")
        a("|---:|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|")
        for lg in explorateur["lignes"]:
            if lg.get("ouverture"):
                ouverture = lg["ouverture"].replace("|", "\\|")
            elif lg.get("connue"):
                ouverture = "(intermédiaire)"
            else:
                ouverture = "-"
            a("| %d | %d | %s | %d | %s | %s | %s %% | %s | %s | %s %% | %s "
              "| %s |"
              % (lg["demicoup"], lg["numero"], lg["trait"],
                 lg["parties_position"], lg["san"],
                 "-" if lg["rang"] is None else str(lg["rang"]),
                 _cellule(lg["frequence"]),
                 _cellule(lg["score_blancs"], "%.1f %%"),
                 lg["majo_san"] or "-",
                 _cellule(lg["majo_frequence"]),
                 _cellule(lg["majo_score_blancs"], "%.1f %%"),
                 ouverture))
        a("")
        a("Arrêt de l'interrogation : %s." % explorateur["arret"])
        a("")

        ps = explorateur["premiere_sortie"]
        a("### Première sortie de théorie")
        a("")
        hors_cat = " hors catalogue" if explorateur.get("catalogue") else ""
        if ps is None:
            a("Aucun coup interrogé ne passe sous le seuil de %.1f %%%s."
              % (explorateur["seuil_frequence"], hors_cat))
        else:
            a("Premier coup sous le seuil de %.1f %%%s : **%s joue %s** au "
              "coup **%d** (demi-coup %d)."
              % (explorateur["seuil_frequence"], hors_cat, ps["trait"],
                 ps["san"], ps["numero"], ps["demicoup"]))
            a("")
            # Last named opening before the exit: it locates, for the
            # analyst, the theoretical line that the game has just left.
            nommees = [lg["ouverture"] for lg in explorateur["lignes"]
                       if lg["demicoup"] < ps["demicoup"]
                       and lg.get("ouverture")]
            if nommees:
                a("- dernière position nommée avant la sortie : %s"
                  % nommees[-1])
            a("- fréquence du coup joué : %s %% (%d parties sur %d)"
              % (_cellule(ps["frequence"]), ps["parties_coup"],
                 ps["parties_position"]))
            a("- rang parmi les réponses : %s"
              % ("hors base" if ps["rang"] is None else ps["rang"]))
            a("- coup majoritaire : %s à %s %%"
              % (ps["majo_san"] or "-", _cellule(ps["majo_frequence"])))
        a("")

    # -- 3. Stockfish -------------------------------------------------------
    a("## 3. Évaluations Stockfish")
    a("")
    a("Moteur : `%s`, profondeur %d, multipv %d, %d demi-coups "
      "couverts sur %d. Les évaluations sont exprimées **du point de "
      "vue des Blancs**. L'écart est exprimé en centipions **du point "
      "de vue du joueur au trait** : positif, il mesure ce que le coup "
      "joué perd par rapport au premier choix du moteur. Négatif, il ne "
      "signale aucune faute : le coup joué, évalué à part quand il n'est "
      "pas parmi les premiers choix, sort un peu au-dessus du premier, "
      "et les deux se valent."
      % (stockfish["binaire"], stockfish["profondeur"],
         stockfish["multipv"], len(stockfish["resultats"]),
         len(list(partie.mainline_moves()))))
    a("")
    a("Nature : imprécision à partir de %d cp d'écart, erreur à partir "
      "de %d, gaffe à partir de %d."
      % (SEUIL_IMPRECISION, SEUIL_ERREUR, SEUIL_GAFFE))
    if any(r["joue"].get("non_evalue") for r in stockfish["resultats"]):
        a("Coup nul `--` : le trait passe sans qu'une pièce ne bouge. Ce "
          "n'est pas un coup des échecs, le moteur ne l'évalue pas : "
          "ses colonnes Éval, G/N/P, Écart et Nature portent `-`, les "
          "meilleurs coups de la position restant donnés.")
    a("Mat : `#+2`, les Blancs matent en deux coups, `#-1`, les Noirs "
      "matent en un coup. Comme toute évaluation de ce tableau, le compte "
      "se lit après le coup de la ligne : `#+0` ou `#-0`, ce coup donne "
      "mat.")
    a("Écart `mat` : l'un des deux scores comparés est un mat, que le "
      "coup joué manque un mat ou qu'il en concède un ; l'écart ne se "
      "chiffre pas en centipions, comparez les colonnes Éval et 1er.")
    if stockfish.get("wdl"):
        a("G/N/P : chances de gain, de nulle et de perte des Blancs "
          "après le coup joué, en pour cent arrondi, selon le modèle de "
          "Stockfish. Ce modèle reflète le jeu du moteur : lisez-le "
          "comme une tendance, non comme la probabilité réelle entre "
          "deux joueurs humains.")
    a("")
    a("| # | Coup | Trait | Joué | Éval | G/N/P | Écart cp | Nature "
      "| 1er | 2e | 3e |")
    a("|---:|---:|---|---|---:|---:|---:|---|---|---|---|")
    for r in stockfish["resultats"]:
        trois = list(r["meilleurs"][:3])
        while len(trois) < 3:
            trois.append(None)
        colonnes = ["-" if m is None else "%s (%s)" % (m["san"], m["score"])
                    for m in trois]
        a("| %d | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
          % (r["demicoup"], r["numero"], r["trait"], r["joue"]["san"],
             r["joue"]["score"], _gnp(r["joue"].get("wdl")),
             _ecart(r["ecart_cp"]),
             r.get("nature") or "-",
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
    a("### 3 bis. Variantes principales du moteur")
    a("")
    if longueur_pv > 0:
        a("Variantes tronquées à %d demi-coups ; les variantes complètes "
          "sont dans `stockfish/evaluations.json`." % longueur_pv)
    else:
        a("Variantes complètes, telles que renvoyées par le moteur.")
    a("")
    plateau = partie.board()
    for r, coup in zip(stockfish["resultats"], partie.mainline_moves(),
                       strict=False):
        a("- Demi-coup %d, %s jouent %s (position avant le coup)"
          % (r["demicoup"], r["trait"], r["joue"]["san"]))
        rangs = ("1er", "2e", "3e", "4e", "5e")
        joue_dans_liste = False
        for k, m in enumerate(r["meilleurs"]):
            etiquette = rangs[k] if k < len(rangs) else "%de" % (k + 1)
            if m["uci"] == r["joue"]["uci"]:
                etiquette += ", joué"
                joue_dans_liste = True
            a("    - %s (%s) : %s" % (etiquette, m["score"],
                                      tronquer_variante(
                                          plateau, m["pv_uci"],
                                          longueur_pv)))
        if r["joue"].get("non_evalue"):
            a("    - joué : coup nul, non évalué par le moteur")
        elif not joue_dans_liste:
            a("    - joué (%s) : %s" % (r["joue"]["score"],
                                        tronquer_variante(
                                            plateau, r["joue"]["pv_uci"],
                                            longueur_pv)))
        plateau.push(coup)
    a("")

    # Ranking: the moves that cost the most, per side, with what should
    # have been played and the FEN, direct material for the mandatory
    # comments and the positions to review.
    a("### 3 ter. Erreurs et gaffes par camp")
    a("")
    a("Coups dont l'écart atteint %d cp, du plus coûteux au moins "
      "coûteux, %d au plus par camp ; les imprécisions restent dans le "
      "tableau. Les chances G/N/P sont celles du camp au trait, la FEN "
      "celle de la position avant le coup."
      % (SEUIL_ERREUR, PALMARES_MAX))
    a("")
    for camp in ("Blancs", "Noirs"):
        fautes = sorted((r for r in stockfish["resultats"]
                         if r["trait"] == camp
                         and r["ecart_cp"] is not None
                         and r["ecart_cp"] >= SEUIL_ERREUR),
                        key=lambda r: -r["ecart_cp"])
        a("**%s**" % camp)
        a("")
        if not fautes:
            a("- Aucune erreur ni gaffe.")
        pour_noirs = camp == "Noirs"
        for r in fautes[:PALMARES_MAX]:
            meilleur = r["meilleurs"][0] if r["meilleurs"] else None
            # From SEUIL_ECART_MAT on, the loss comes from a mate brought down
            # to a bounded value: the figure no longer makes sense, the
            # scores speak for themselves.
            ecart = ("écart %.0f cp" % r["ecart_cp"]
                     if r["ecart_cp"] < SEUIL_ECART_MAT else
                     "écart lié à un mat, %s au lieu de %s"
                     % (r["joue"]["score"],
                        meilleur["score"] if meilleur else "?"))
            a("- Coup %d, %s jouent %s (demi-coup %d) : %s, %s."
              % (r["numero"], r["trait"], r["joue"]["san"],
                 r["demicoup"], r["nature"], ecart))
            if meilleur is not None:
                a("  Meilleur coup : %s (%s), ligne %s."
                  % (meilleur["san"], meilleur["score"],
                     tronquer_variante(chess.Board(r["fen"]),
                                       meilleur["pv_uci"], longueur_pv)))
                if meilleur.get("wdl") and r["joue"].get("wdl"):
                    a("  Chances G/N/P : %s avec le meilleur coup, %s "
                      "après le coup joué."
                      % (_gnp(meilleur["wdl"], pour_noirs),
                         _gnp(r["joue"]["wdl"], pour_noirs)))
            a("  FEN : `%s`" % r["fen"])
        if len(fautes) > PALMARES_MAX:
            a("- %d autres, voir le tableau."
              % (len(fautes) - PALMARES_MAX))
        a("")

    # -- 4. Unusable positions ----------------------------------------------
    a("## 4. Positions à échantillon non exploitable")
    a("")
    if explorateur is None:
        a("Sans objet, collecte de l'explorateur non effectuée.")
    elif not explorateur["non_exploitables"]:
        a("Aucune : l'interrogation s'est arrêtée pour une autre raison "
          "(%s)." % explorateur["arret"])
    else:
        a("| # | Coup | Trait | Coup joué | Motif |")
        a("|---:|---:|---|---|---|")
        for n in explorateur["non_exploitables"]:
            a("| %d | %d | %s | %s | %s |"
              % (n["demicoup"], n["numero"], n["trait"], n["san"], n["motif"]))
        a("")
        a("Au delà de ce point, la base %s ne dit plus rien "
          "d'exploitable : toute affirmation sur la théorie devra venir "
          "d'ailleurs." % libelle_base)
    a("")

    # -- 5. Reminder of the raw data ----------------------------------------
    a("## 5. Données brutes de l'archive")
    a("")
    if pgn_complete:
        a("- `partie.pgn` : la partie avec ses en-têtes complétés, "
          "réexportée par python-chess, commentaires d'origine compris.")
    else:
        a("- `partie.pgn` : le PGN source, avec ses commentaires d'origine.")
    for annexe in annexes or []:
        a(annexe)
    if explorateur is not None:
        # Without the explorer, the archive does not have this folder:
        # announcing it would send the analyst looking for files that do not
        # exist.
        a("- `explorateur/NNN-<uci>.json` : une réponse brute par "
          "demi-coup interrogé, numérotée dans l'ordre de la partie.")
    a("- `stockfish/evaluations.json` : les évaluations moteur "
      "complètes, avec la variante principale entière de chaque coup, "
      "en UCI et en notation algébrique.")
    a("- `collecte.json` : les paramètres exacts de cette collecte.")
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
    "partie-2026.11.18.pgn", the folder "analyse-partie-2026.11.18-..."
    gave "analyse-partie-2026.11.zip", whereas shutil.make_archive does
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
    ".<folder>.partiel.zip", next to the folder; it only takes its final
    name once checked. An interruption (Ctrl-C) or a failure therefore
    never leaves a truncated zip under the name of an archive: the
    temporary archive is removed, the working folder stays.
    """
    archive = chemin_archive(dossier)
    if archive.exists():
        raise SystemExit("L'archive %s existe déjà, dossier conservé."
                         % archive)

    # Base of the temporary name: shutil.make_archive appends ".zip" to it.
    # The paths stored in the zip only depend on base_dir, they stay those
    # of the working folder.
    base_partielle = dossier.with_name(".%s.partiel" % dossier.name)
    partielle = chemin_archive(base_partielle)

    journal("Création de l'archive : %s" % archive)
    try:
        try:
            shutil.make_archive(str(base_partielle), "zip",
                                root_dir=dossier.parent,
                                base_dir=dossier.name)
        except (OSError, shutil.Error) as err:
            raise SystemExit("Échec de la création de l'archive, dossier "
                             "conservé : %s" % err) from err

        try:
            with zipfile.ZipFile(partielle) as z:
                corrompu = z.testzip()
                noms = z.namelist()
        except (OSError, zipfile.BadZipFile) as err:
            raise SystemExit("Archive illisible, dossier conservé : %s"
                             % err) from err

        attendu = "%s/synthese.md" % dossier.name
        if corrompu is not None or attendu not in noms:
            raise SystemExit("Archive incomplète ou corrompue (%s), dossier "
                             "conservé." % (corrompu or "synthèse absente"))

        # Renaming within the same directory: the archive appears all at
        # once, complete and checked.
        try:
            partielle.replace(archive)
        except OSError as err:
            raise SystemExit("Archive valide mais impossible à renommer en "
                             "%s, dossier conservé : %s"
                             % (archive, err)) from err
    except BaseException:
        # Any stop before the renaming, Ctrl-C included, removes the
        # temporary archive and then goes up unchanged: the working folder,
        # for its part, is kept for diagnosis.
        with contextlib.suppress(OSError):
            partielle.unlink()
        raise

    if garder:
        journal("Dossier conservé sur demande : %s" % dossier)
        return archive

    try:
        shutil.rmtree(dossier)
    except OSError as err:
        raise SystemExit("Archive valide mais suppression du dossier "
                         "impossible : %s" % err) from err
    journal("Dossier de travail supprimé.")
    return archive


# ===========================================================================
# Command line
# ===========================================================================

EXEMPLES = """\
exemples d'utilisation
----------------------

  Première installation, une seule fois :

      %s
      %s
      ./ianalyze.py --installer-venv
      ./ianalyze.py --installer-catalogue

  Relancer --installer-catalogue de temps en temps met le catalogue des
  ouvertures à jour.

  Usage courant, sur un PGN local :

      ./ianalyze.py ma-partie.pgn

  Sur une partie Lichess, par URL ou par identifiant :

      ./ianalyze.py https://lichess.org/<identifiant>
      ./ianalyze.py <identifiant>

  Sans aucune question, par exemple depuis un autre script, ou avec tous vos
  noms de joueur pour que le camp soit déduit des en-têtes :

      ./ianalyze.py ma-partie.pgn --sans-questions
      ./ianalyze.py ma-partie.pgn --pseudos MonPseudo,AutrePseudo

  Descendre aussi loin que la base répond, sans aucun seuil :

      ./ianalyze.py ma-partie.pgn --jusqu-a-epuisement

  La base de tous les joueurs Lichess est interrogée par défaut, avec les
  filtres de https://lichess.org/opening. La restreindre à certaines
  cadences et tranches de classement, ou interroger la base maîtres :

      ./ianalyze.py ma-partie.pgn \\
          --cadences rapid,classical,correspondence --classements 0,1000
      ./ianalyze.py ma-partie.pgn --base maitres

  Couvrir les dix premiers coups quelle que soit la fréquence des coups
  joués, ou au contraire s'arrêter dès la première sortie de théorie :

      ./ianalyze.py ma-partie.pgn --coups-min 10
      ./ianalyze.py ma-partie.pgn --coups-min 0

  Moteur seul, sans réseau ni jeton :

      ./ianalyze.py ma-partie.pgn --sans-explorateur

  Conserver le dossier de travail à côté de l'archive :

      ./ianalyze.py ma-partie.pgn --garder-dossier

  Pour un LLM qui n'ouvre pas les zip ou n'exécute pas de code : un
  prompt court qui porte la partie et les évaluations, à coller seul.
  Aucune archive n'est écrite :

      ./ianalyze.py ma-partie.pgn --prompt-seul

  Utiliser votre propre modèle de prompt, ou ne pas écrire de prompt :

      ./ianalyze.py ma-partie.pgn --prompt ~/mon-modele.txt
      ./ianalyze.py ma-partie.pgn --sans-prompt

  Moteur plus profond, ou limité aux quinze premiers coups :

      ./ianalyze.py ma-partie.pgn --profondeur 22
      ./ianalyze.py ma-partie.pgn --coups-stockfish 15

résultat
--------

  Une archive analyse-<partie>-<horodatage>.zip dans le répertoire de
  sortie, contenant synthese.md et les données brutes. Le chemin de
  l'archive est écrit seul sur la sortie standard, tout le reste va sur la
  sortie d'erreur. En cas d'échec, le dossier de travail est conservé tel
  quel pour diagnostic.

  À côté de l'archive, le prompt d'analyse de la partie, sous le nom
  analyse-<partie>-<horodatage>.prompt.txt : collez-le dans la
  conversation, l'archive en pièce jointe. Il est tiré du modèle
  prompt-modele.txt, rangé à côté du script, que vous pouvez modifier.

prérequis
---------

  %s
  %s

  python-chess n'est pas empaqueté par Debian. L'option --installer-venv
  crée un environnement virtuel dédié et y installe le module. Par défaut :
  %s
  Le script s'y relance ensuite tout seul, vous pouvez continuer à
  l'appeler avec le python du système.

  Le catalogue des ouvertures nommées de Lichess (domaine public, CC0)
  est gardé en local dans %s,
  installé et mis à jour par --installer-catalogue. Il n'est pas requis
  avec --sans-explorateur.

  Le jeton personnel Lichess est lu dans %s, en mode 600,
  ce fichier ne contenant que le jeton. Il n'apparaît jamais dans la
  sortie, ni dans les fichiers produits, ni dans la ligne de commande.

  Votre pseudo, votre cadence habituelle et votre niveau sont demandés
  une seule fois, au premier lancement sur un terminal, puis gardés dans
  %s, que vous pouvez modifier à la main.

  Aucune autre dépendance : le HTTP passe par urllib de la bibliothèque
  standard, l'archive par zipfile. Le paquet stockfish est obligatoire,
  le moteur est piloté en UCI.
""" % (CMD_PAQUET_VENV, CMD_PAQUET_STOCKFISH,
       CMD_PAQUET_VENV, CMD_PAQUET_STOCKFISH,
       VENV_DEFAUT, CATALOGUE_DEFAUT, JETON_DEFAUT, REGLAGES_DEFAUT)


def valider_liste(p: argparse.ArgumentParser, option: str, valeur: str,
                  admises: tuple[str, ...]) -> str:
    """
    Checks a comma-separated list and returns it normalized.

    Case is tolerated on input ("ultrabullet" is accepted) but the value
    passed on uses the exact spelling of the API. Stray spaces and
    duplicates are removed, and the list is put back in the order of the
    enumeration, so that collecte.json and the summary stay comparable
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
            p.error('%s : valeur inconnue "%s", valeurs admises : %s'
                    % (option, element, ", ".join(admises)))
        if canonique not in retenues:
            retenues.append(canonique)
    if not retenues:
        p.error("%s : liste vide" % option)
    retenues.sort(key=admises.index)
    return ",".join(retenues)


def analyser_arguments(argv: list[str]) -> argparse.Namespace:
    """Defines and reads the command line options."""
    p = argparse.ArgumentParser(
        prog="ianalyze.py",
        # The line breaks are written here: with this formatter, argparse
        # does not wrap the description, which fitted on a line of 250
        # columns.
        description="Collecte le matériel d'analyse d'une partie d'échecs : "
                    "PGN, statistiques\n"
                    "de l'explorateur Lichess (base de tous les joueurs, "
                    "ou base maîtres avec\n"
                    "--base maitres) pour déterminer la sortie de théorie, "
                    "et évaluations\n"
                    "Stockfish de la partie. Ne produit aucune analyse.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXEMPLES)

    p.add_argument("source", nargs="?",
                   help="fichier PGN local, URL Lichess, ou identifiant de "
                        "partie à huit ou douze caractères")

    g = p.add_argument_group("environnement virtuel")
    g.add_argument("--installer-venv", action="store_true",
                   help="crée l'environnement virtuel s'il manque, y "
                        "installe python-chess, puis quitte")
    g.add_argument("--venv", default=VENV_DEFAUT, metavar="CHEMIN",
                   help="emplacement de l'environnement virtuel "
                        "(défaut : %(default)s)")

    g = p.add_argument_group("questions de démarrage")
    g.add_argument("--sans-questions", action="store_true",
                   help="ne pose aucune question, ni camp ni contexte ; "
                        "implicite hors terminal interactif")
    g.add_argument("--pseudos", default=None, metavar="LISTE",
                   help="vos noms de joueur, séparés par des virgules, "
                        "cherchés sans tenir compte de la casse dans White "
                        "et Black pour déduire votre camp "
                        "(défaut : ceux de vos réglages)")
    g.add_argument("--reglages", default=REGLAGES_DEFAUT, metavar="FICHIER",
                   help="fichier de réglages, où sont gardés votre pseudo, "
                        "votre cadence habituelle et votre niveau, demandés "
                        "une seule fois sur un terminal "
                        "(défaut : %(default)s)")
    g.add_argument("--purge-reglages", action="store_true",
                   help="supprime le fichier de réglages, celui de "
                        "--reglages s'il est donné, puis quitte ; vos "
                        "réponses seront redemandées à la prochaine "
                        "collecte")

    g = p.add_argument_group("catalogue des ouvertures")
    g.add_argument("--installer-catalogue", action="store_true",
                   help="télécharge ou met à jour le catalogue des ouvertures "
                        "nommées de Lichess, le valide, puis quitte")
    g.add_argument("--catalogue", default=CATALOGUE_DEFAUT, metavar="REP",
                   help="répertoire du catalogue local "
                        "(défaut : %(default)s)")

    g = p.add_argument_group("sortie")
    g.add_argument("--sortie", default=".", metavar="REP",
                   help="répertoire où écrire l'archive "
                        "(défaut : %(default)s)")
    g.add_argument("--garder-dossier", action="store_true",
                   help="ne supprime pas le dossier de travail après "
                        "création de l'archive, ou du prompt avec "
                        "--prompt-seul")
    g.add_argument("--prompt", metavar="FICHIER",
                   help="modèle du prompt d'analyse, écrit à côté de "
                        "l'archive sous le nom <archive>%s (défaut : %s à "
                        "côté du script)" % (PROMPT_SUFFIXE, PROMPT_MODELE))
    g.add_argument("--sans-prompt", action="store_true",
                   help="n'écrit pas le prompt d'analyse")
    g.add_argument("--prompt-seul", action="store_true",
                   help="écrit un prompt court qui porte la partie et les "
                        "évaluations de Stockfish, à coller seul dans la "
                        "conversation, sans pièce jointe : pour un LLM qui "
                        "n'ouvre pas les zip ou n'exécute pas de code. Son "
                        "modèle est %s. Aucune archive n'est écrite, et le "
                        "dossier de travail est supprimé, sauf avec "
                        "--garder-dossier" % PROMPT_SEUL_MODELE)

    g = p.add_argument_group("explorateur")
    g.add_argument("--base", choices=sorted(BASES_EXPLORATEUR),
                   default="lichess",
                   help="base interrogée : lichess, les parties classées de "
                        "tous les joueurs du site, celle de "
                        "https://lichess.org/opening, ou maitres "
                        "(défaut : %(default)s)")
    g.add_argument("--cadences", metavar="LISTE",
                   help="avec --base lichess, cadences retenues, séparées "
                        "par des virgules, parmi : %s (défaut : %s)"
                        % (", ".join(CADENCES_LICHESS), CADENCES_DEFAUT))
    g.add_argument("--classements", metavar="LISTE",
                   help="avec --base lichess, tranches de classement "
                        "retenues, séparées par des virgules, parmi : %s ; "
                        "0 couvre 0 à 999, 2500 tout ce qui dépasse "
                        "(défaut : %s)"
                        % (", ".join(CLASSEMENTS_LICHESS),
                           CLASSEMENTS_DEFAUT))
    g.add_argument("--jeton-fichier", default=JETON_DEFAUT, metavar="FICHIER",
                   help="fichier contenant le jeton personnel "
                        "(défaut : %(default)s)")
    g.add_argument("--seuil-parties", type=int, default=50, metavar="N",
                   help="arrêt sous N parties pour la position "
                        "(défaut : %(default)s)")
    g.add_argument("--seuil-frequence", type=float, default=10.0, metavar="P",
                   help="arrêt dès que le coup joué tombe sous P pour cent "
                        "de fréquence et sort du catalogue des ouvertures, "
                        "0 pour désactiver ce critère "
                        "(défaut : %(default)s)")
    g.add_argument("--jusqu-a-epuisement", action="store_true",
                   help="ignore les deux seuils et interroge la base tant "
                        "qu'elle répond, l'arrêt n'ayant alors lieu que sur "
                        "une erreur HTTP, sur une position absente de la "
                        "base, sur un coup nul, au plafond "
                        "--max-demicoups ou à la fin de la partie")
    g.add_argument("--coups-min", type=int, default=6, metavar="N",
                   help="aucun arrêt sur la fréquence avant la fin du coup "
                        "N, le seuil de parties restant actif ; la table "
                        "couvre ainsi le début de partie même après une "
                        "sortie précoce, 0 pour s'arrêter dès la première "
                        "sortie (défaut : %(default)s)")
    g.add_argument("--max-demicoups", type=int, default=60, metavar="N",
                   help="plafond de demi-coups interrogés, garde-fou "
                        "toujours actif (défaut : %(default)s)")
    g.add_argument("--pause", type=float, default=2.0, metavar="S",
                   help="pause entre deux requêtes, en secondes, minimum 2 "
                        "imposé par l'API (défaut : %(default)s)")
    g.add_argument("--sans-explorateur", action="store_true",
                   help="saute entièrement la collecte explorateur")

    g = p.add_argument_group("moteur")
    g.add_argument("--coups-stockfish", type=int, default=0, metavar="N",
                   help="limite l'analyse moteur aux N premiers coups "
                        "entiers, soit 2N demi-coups ; 0 analyse toute la "
                        "partie (défaut : %(default)s)")
    g.add_argument("--profondeur", type=int, default=18, metavar="D",
                   help="profondeur de recherche, de 1 à 60 "
                        "(défaut : %(default)s)")
    g.add_argument("--multipv", type=int, default=3, metavar="K",
                   help="nombre de variantes demandées par position "
                        "(défaut : %(default)s)")
    g.add_argument("--fils", type=int, default=os.cpu_count() or 1,
                   metavar="N",
                   help="threads Stockfish (défaut : nombre de processeurs)")
    g.add_argument("--hachage", type=int, default=256, metavar="MO",
                   help="table de hachage en mégaoctets "
                        "(défaut : %(default)s)")
    g.add_argument("--stockfish", default=STOCKFISH_DEFAUT, metavar="CHEMIN",
                   help="binaire du moteur (défaut : %(default)s)")
    g.add_argument("--longueur-pv", type=int, default=5, metavar="N",
                   help="demi-coups de variante principale reproduits dans "
                        "la synthèse, 0 pour la variante entière "
                        "(défaut : %(default)s)")

    p.add_argument("--delai", type=int, default=30, metavar="S",
                   help="délai réseau maximal, en secondes "
                        "(défaut : %(default)s)")
    p.add_argument("--debug", action="store_true",
                   help="laisse remonter la trace complète des erreurs "
                        "inattendues")

    options = p.parse_args(argv)

    if options.purge_reglages and (options.installer_venv
                                   or options.installer_catalogue
                                   or options.source):
        # The purge is done alone: combined, it was ignored without a
        # word in favor of the other action.
        p.error("--purge-reglages s'emploie seule, sans partie ni autre "
                "action")
    if options.prompt is not None and not options.prompt.strip():
        # Case of an empty variable in a script: --prompt "$MODELE".
        p.error("--prompt : chemin vide")
    if (options.installer_venv or options.installer_catalogue
            or options.purge_reglages):
        return options
    if not options.source:
        p.error("il faut un fichier PGN, une URL ou un identifiant de partie")
    if options.prompt and options.sans_prompt:
        p.error("--prompt et --sans-prompt s'excluent")
    if options.prompt_seul and options.sans_prompt:
        p.error("--prompt-seul et --sans-prompt s'excluent")
    # nan and inf are valid floats for argparse, but nan escapes any
    # comparison and time.sleep() rejects both: they are ruled out
    # here, before any folder is created.
    for nom in ("pause", "seuil_frequence"):
        if not math.isfinite(getattr(options, nom)):
            p.error("--%s doit être un nombre fini"
                    % nom.replace("_", "-"))
    if options.pause < 2.0:
        p.error("--pause ne doit pas descendre sous 2 secondes")
    for nom in ("seuil_parties", "max_demicoups", "profondeur", "multipv",
                "fils", "hachage", "delai"):
        if getattr(options, nom) < 1:
            p.error("--%s doit valoir au moins 1" % nom.replace("_", "-"))
    # Paths: the shell only expands the tilde if it starts the word,
    # not in the form --sortie=~/analyses.
    options.sortie = os.path.expanduser(options.sortie)
    options.stockfish = resoudre_moteur(options.stockfish)
    if options.profondeur > PROFONDEUR_MAX:
        p.error("--profondeur ne doit pas dépasser %d" % PROFONDEUR_MAX)
    if options.coups_stockfish < 0:
        p.error("--coups-stockfish doit valoir 0 ou plus")
    if options.coups_min < 0:
        p.error("--coups-min doit valoir 0 ou plus")
    # Without --pseudos, the value stays None: the usernames will then
    # come from the settings. The option, when given, must carry one.
    if options.pseudos is not None:
        options.pseudos = decouper_pseudos(options.pseudos)
        if not options.pseudos:
            p.error("--pseudos : liste vide")
    if options.seuil_frequence < 0 or options.seuil_frequence > 100:
        p.error("--seuil-frequence doit être compris entre 0 et 100")
    if options.longueur_pv < 0:
        p.error("--longueur-pv doit valoir 0 ou plus")
    if options.base == "maitres":
        # Same principle as for the engine options: a filter that the masters
        # database does not know would be silently ignored, so it is refused.
        for nom in ("cadences", "classements"):
            if getattr(options, nom) is not None:
                p.error("--%s n'a d'effet qu'avec --base lichess" % nom)
    else:
        # The default values are only set here, and only for the Lichess
        # database: collecte.json thus records the filters actually
        # applied, and nothing for the masters database.
        if options.cadences is None:
            options.cadences = CADENCES_DEFAUT
        if options.classements is None:
            options.classements = CLASSEMENTS_DEFAUT
        options.cadences = valider_liste(p, "--cadences", options.cadences,
                                         CADENCES_LICHESS)
        options.classements = valider_liste(p, "--classements",
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

    # Text of the "Consignes d'analyse" section of the summary: the answers
    # to the startup questions, when they are asked.
    consignes = None

    # -- User settings, read early as well ----------------------------------
    reglages = lire_reglages(options.reglages)

    # -- Prompt template, read and checked before the collection ------------
    # A template named by --prompt must exist. The default template, for
    # its part, may be missing when the script was copied alone: the
    # collection is then done without a prompt, and the log says so.
    modele_prompt = None
    if not options.sans_prompt:
        fichier_modele = chemin_modele(options.prompt, options.prompt_seul)
        if est_fichier(fichier_modele):
            modele_prompt = lire_texte(fichier_modele, "modèle de prompt")
            verifier_modele(modele_prompt, str(fichier_modele))
            # A prompt to be pasted alone must carry the game: a personal
            # template that does not place it is refused before the collection.
            # The marker is looked up in the text lines: placed in a
            # note, it would put nothing into the prompt.
            if options.prompt_seul and not any(
                    PROMPT_DONNEES in ligne
                    for ligne in lignes_de_texte(modele_prompt)):
                raise SystemExit(
                    "--prompt-seul : le modèle %s ne contient pas %s, le "
                    "prompt ne porterait pas la partie. Partez de %s."
                    % (fichier_modele, PROMPT_DONNEES, PROMPT_SEUL_MODELE))
        elif options.prompt or options.prompt_seul:
            # --prompt-seul asks for a prompt: without a template, it is better
            # to stop here than after the collection.
            raise SystemExit("Modèle de prompt introuvable : %s"
                             % fichier_modele)
        else:
            journal("Attention : modèle de prompt introuvable (%s), aucun "
                    "prompt ne sera écrit. Voir --prompt et --sans-prompt."
                    % fichier_modele)

    # -- Fetching the PGN ---------------------------------------------------
    # Encoding chosen for the PGN and decoding remarks, recorded in
    # collecte.json and, if need be, in section 5 of the summary.
    encodage_pgn = "utf-8"
    remarques_pgn: list[str] = []
    chemin_local = pathlib.Path(os.path.expanduser(options.source))
    if est_fichier(chemin_local):
        journal("Lecture du PGN local : %s" % chemin_local)
        texte_pgn, encodage_pgn, remarques_pgn = lire_fichier_texte(
            chemin_local, "PGN")
        if encodage_pgn == "latin-1":
            # The fallback on latin-1 only happens if the file contains a
            # byte that cp1252 does not define: this is the sign of another
            # encoding, cp850 or MacRoman for example, whose accented
            # letters would be removed like control characters. Rather
            # than silently damaging the names, the script
            # stops.
            raise SystemExit(
                "Encodage du PGN non reconnu : ni UTF-8, ni UTF-16, ni "
                "cp1252. Convertissez le fichier en UTF-8, par exemple "
                "avec iconv, puis relancez.")
        etiquette = etiquette_sure(chemin_local.stem)
        if etiquette != chemin_local.stem:
            journal("Nom du dossier assaini : %s" % etiquette)
    elif options.source.strip() and est_repertoire(chemin_local):
        # A directory whose name has eight letters would otherwise pass for
        # an identifier, and a request would go to Lichess.
        raise SystemExit("%s est un répertoire, pas un fichier PGN."
                         % chemin_local)
    else:
        identifiant = extraire_id(options.source)
        if identifiant is None:
            # Outside a URL, a dot, a slash or a tilde betray a path: the
            # file aimed at does not exist, we might as well say so.
            if (not options.source.strip().lower().startswith(
                    ("http://", "https://"))
                    and any(c in options.source for c in "./~")):
                raise SystemExit("Fichier PGN introuvable : %s"
                                 % chemin_local)
            if options.source.strip().lower().startswith(
                    ("http://", "https://")):
                # Message specific to URLs: stating the expected form is better
                # than a general refusal.
                raise SystemExit("URL non reconnue comme une partie Lichess "
                                 ": %s\nForme attendue : "
                                 "https://lichess.org/<identifiant>, "
                                 "l'identifiant faisant 8 ou 12 caractères "
                                 "alphanumériques."
                                 % nettoyer_valeur(options.source))
            raise SystemExit("Source incomprise : ni fichier existant, ni "
                             "URL ou identifiant Lichess valide.")
        texte_pgn = telecharger_pgn(identifiant, options.delai)
        etiquette = identifiant

    partie = charger_partie(texte_pgn)

    # -- Preliminary checks, to fail before anything has been written -------
    catalogue = None
    motif_sans_explorateur = None
    if options.sans_explorateur:
        motif_sans_explorateur = "désactivée par --sans-explorateur"
    else:
        # The token is only read here and is neither written nor logged.
        JETON_COURANT = lire_jeton(options.jeton_fichier)
        # Catalog loaded before any writing: missing or damaged, we stop
        # here, giving the command to run.
        catalogue = lire_catalogue(options.catalogue)
        journal("Catalogue des ouvertures : %s positions connues, du %s"
                % (catalogue.meta.get("connues"), catalogue.meta.get("date")))
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
    if interactif:
        # Missing settings: asked for here, once and for all, before the
        # questions specific to the game.
        completer_reglages(options.reglages, reglages, options.pseudos)
    # --pseudos wins over the settings. The list kept replaces the
    # option: collecte.json thus records the usernames actually used,
    # and it may be empty.
    if options.pseudos is None:
        options.pseudos = decouper_pseudos(reglage(reglages, "pseudos"))
    if interactif:
        journal("Questions de démarrage, Entrée retient la valeur proposée.")
        camp = completer_entetes(partie, options.pseudos)
        contexte = recueillir_contexte(
            partie, camp, analyser_cadence(reglage(reglages, "cadence")))
        consignes = contexte
    else:
        journal("Questions de démarrage sautées : %s."
                % ("option --sans-questions" if options.sans_questions
                   else "terminal non interactif"))

    # -- Creation of the working folder -------------------------------------
    # The name is timestamped to the second; two runs within the same
    # second, or a folder left by a previous failure, get a suffix rather
    # than an error. The prompt counts too: with --prompt-seul it is the
    # only file that remains, and a second run within the same second
    # overwrote it.
    horodatage = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = pathlib.Path(options.sortie) / ("analyse-%s-%s"
                                           % (etiquette, horodatage))
    dossier = base
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
            raise SystemExit("Impossible de créer le dossier de travail %s : "
                             "%s" % (dossier, err)) from err
        suffixe += 1
        if suffixe > 100:
            raise SystemExit("Trop de dossiers homonymes dans %s."
                             % base.parent)
        dossier = base.with_name("%s-%d" % (base.name, suffixe))
    annexes: list[str] = []
    try:
        if camp and camp["modifiees"]:
            # The PGN given is kept as it is; partie.pgn holds the game,
            # re-exported by python-chess, with its headers filled in.
            ecrire_texte(dossier / "partie-origine.pgn", texte_pgn)
            ecrire_texte(dossier / "partie.pgn", str(partie) + "\n")
            annexes.append("- `partie-origine.pgn` : le PGN tel que "
                           "fourni, avant ajout des balises %s."
                           % ", ".join(camp["modifiees"]))
        else:
            ecrire_texte(dossier / "partie.pgn", texte_pgn)
        if remarques_pgn:
            # The PGN kept in the archive is no longer, byte for byte, the
            # file given: the analyst must know it.
            annexes.append("- Encodage : le PGN fourni a été converti en "
                           "UTF-8 avant d'être rangé dans l'archive (%s)."
                           % " ; ".join(remarques_pgn))
        if contexte is not None:
            ecrire_texte(dossier / "contexte.md", contexte)
            annexes.append("- `contexte.md` : les réponses aux questions de "
                           "démarrage, reprises en tête de cette synthèse.")
    except OSError as err:
        raise SystemExit("Écriture impossible dans %s : %s"
                         % (dossier, err)) from err
    journal("Dossier de travail : %s" % dossier)

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
        journal("Explorateur : base %s, %s" % (base["libelle"], base["url"]))
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
    parametres = dict(vars(options))
    parametres["jeton_present"] = JETON_COURANT is not None
    parametres["catalogue_utilise"] = (catalogue.meta if catalogue is not None
                                       else None)
    parametres["camp"] = camp
    parametres["contexte_recueilli"] = contexte is not None
    parametres["pgn_encodage"] = encodage_pgn
    parametres["pgn_remarques"] = remarques_pgn
    # Name of the prompt written next to the archive, or nothing if there
    # is none.
    parametres["prompt_ecrit"] = (dossier.name + PROMPT_SUFFIXE
                                  if modele_prompt is not None else None)
    ecrire_texte(dossier / "collecte.json",
                 json.dumps(parametres, ensure_ascii=False, indent=1,
                            default=str))

    # -- Summary ------------------------------------------------------------
    synthese = dossier / "synthese.md"
    ecrire_synthese(synthese, partie, options.source, consignes,
                    resume_explorateur, motif_sans_explorateur,
                    resume_stockfish, options.longueur_pv,
                    base["libelle"], filtres, annexes,
                    bool(camp and camp["modifiees"]))
    journal("Synthèse écrite : %s" % synthese)

    # The prompt may include the PGN: it is read back here, before the
    # archiving that deletes the working folder.
    texte_partie = ""
    if modele_prompt is not None:
        texte_partie = (dossier / "partie.pgn").read_text(encoding="utf-8")

    # -- Archive and cleanup ------------------------------------------------
    # With --prompt-seul, the prompt is all that the player asks for: no
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
        camp_joueur = ((camp or {}).get("camp")
                       or deduire_camp(partie, options.pseudos))
        niveau = analyser_niveau(reglage(reglages, "niveau")) or 0
        habituelle = (analyser_cadence(reglage(reglages, "cadence"))
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
            "EXPLORATEUR": resume_explorateur is not None,
            "BASE_LICHESS": options.base == "lichess",
            "BASE_MAITRES": options.base == "maitres",
            "REPONSES": contexte is not None,
            "CAMP_CONNU": camp_joueur is not None,
            "PSEUDO_CONNU": bool(options.pseudos),
            "NIVEAU_DECLARE": bool(niveau),
            "RESULTAT_CONTREDIT": bool(alerte),
            "CONSIGNES_DONNEES": bool(precisions),
            "OUVERTURE_CONNUE": bool(ouverture),
            # --coups-stockfish limited the engine to the first moves: the
            # prompt must say so, otherwise it promises a figure for every
            # move.
            "COUVERTURE_PARTIELLE": evalues < len(coups_partie),
            "COUP_NUL": any(not coup for coup in coups_partie),
            # The review of the short prompt asks for three errors: when the
            # table marks fewer of them for the player, the prompt says so, so
            # that the LLM does not make one up.
            "PEU_DE_COUPS_FAIBLES": (faibles is not None
                                     and faibles < ERREURS_DU_BILAN),
            # Without a single weak move, "tenez-vous-en à ceux-là" makes no
            # sense: the short template has a sentence for this case.
            "AUCUN_COUP_FAIBLE": faibles == 0,
        }
        valeurs = {
            "VERSION": VERSION,
            "DEPOT": DEPOT,
            "ARCHIVE": archive.name,
            "PSEUDOS": ", ".join(options.pseudos),
            "CAMP": camp_joueur or "inconnu",
            "NIVEAU": decrire_niveau(niveau, partie, camp_joueur),
            "CADENCE": decrire_cadence(habituelle),
            "ANNOTATEUR": (nettoyer_valeur(reglage(reglages, "annotateur"))
                           or ANNOTATEUR_DEFAUT),
            "BASE": base["libelle"],
            "SEUIL_IMPRECISION": str(SEUIL_IMPRECISION),
            "SEUIL_ERREUR": str(SEUIL_ERREUR),
            "SEUIL_GAFFE": str(SEUIL_GAFFE),
            "PROFONDEUR": str(options.profondeur),
            "MULTIPV": str(options.multipv),
            "PARTIE_PGN": texte_partie.strip("\n"),
            "TABLEAU_MOTEUR": tableau_compact(
                partie, resume_stockfish["resultats"], options.longueur_pv),
            "ALERTE_RESULTAT": alerte,
            "CONSIGNES_JOUEUR": precisions,
            "OUVERTURE": ouverture,
            "DEMI_COUPS": str(len(coups_partie)),
            "DEMI_COUPS_EVALUES": str(evalues),
            "COUPS_FAIBLES_JOUEUR": ("inconnu" if faibles is None
                                     else str(faibles)),
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
                    and valeurs["PARTIE_PGN"].rstrip() not in rendu):
                # The marker exists in the template, but under a condition that
                # is false for this game: say so rather than announce a
                # complete prompt.
                journal("Attention : le prompt %s ne porte pas la partie, "
                        "le modèle la place sous une condition qui ne "
                        "s'applique pas ici. Il ne peut pas être collé "
                        "seul." % prompt)
            elif options.prompt_seul:
                journal("Prompt d'analyse écrit : %s, à coller seul dans "
                        "la conversation : il porte la partie et les "
                        "évaluations, aucune pièce jointe n'est "
                        "nécessaire." % prompt)
            else:
                journal("Prompt d'analyse écrit : %s, à coller dans la "
                        "conversation, l'archive en pièce jointe." % prompt)
        except OSError as err:
            if options.prompt_seul:
                # The prompt was the only product expected: its failure is that
                # of the command. The working folder stays.
                raise SystemExit("Prompt non écrit (%s), dossier de travail "
                                 "conservé : %s" % (prompt, err)) from err
            # The archive is made: a prompt that cannot be written must
            # not make the collection fail.
            journal("Attention : prompt non écrit (%s) : %s" % (prompt, err))

    if options.prompt_seul:
        # The prompt is written: the working folder has no more use,
        # unless the player asked to keep it, for example to pass it
        # to verifier-analyse.py.
        prompt = archive.with_name(dossier.name + PROMPT_SUFFIXE)
        if options.garder_dossier:
            journal("Dossier conservé sur demande : %s" % dossier)
        else:
            try:
                shutil.rmtree(dossier)
            except OSError as err:
                raise SystemExit("Prompt écrit mais suppression du dossier "
                                 "impossible : %s" % err) from err
            journal("Dossier de travail supprimé, aucune archive n'est "
                    "écrite avec --prompt-seul.")
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
        sys.stderr.write("\nInterrompu.\n")
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
            sys.stderr.write("Erreur inattendue (%s) : %s\n"
                             "Relancez avec --debug pour la trace complète.\n"
                             % (type(err).__name__,
                                expurger(str(err), JETON_COURANT)))
        raise SystemExit(1) from None
