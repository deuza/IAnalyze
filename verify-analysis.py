#!/usr/bin/env python3
"""
verify-analysis.py: checks the annotated PGN returned by an LLM.

The script compares what an LLM produced with the IAnalyze archive it
received, and gives the same report for each LLM tried. It does not
judge the quality of the commentary: it checks what a machine can
check.

    ./verify-analysis.py ARCHIVE PGN [--summary FILE] [--name NAME]
                          [--prompt-only] [--scope N]

    ARCHIVE     the zip produced by ianalyze.py, or its unzipped
                folder. A folder that contains the latter also does,
                if it contains only one complete collection
    PGN         the .pgn file returned by the LLM, or a dash, "-", if
                the LLM returned no file: only the summary is then
                checked
    --summary   optional: the final summary of the LLM, copied from the
                conversation into a text file. The FEN and the
                evaluations it quotes are then checked too
    --name      optional: name of the model tried, repeated at the top
                of the report
    --prompt-only
                the PGN answers the short prompt of ianalyze.py
                --prompt-only. This prompt asks for less: the checks it
                does not ground are skipped (lines of 79 characters,
                summary before move 1, NAG, percent, em dash, Annotator
                and PlyCount tags, length of the variations, number of
                FEN)
    --scope N
                scope agreed with the LLM, in moves: the mistakes and
                blunders played after move N are not expected. Without
                this option, the scope is the one that the player gave
                to the script, read in the instructions of the archive

What is checked:

  1. the PGN reads, in UTF-8, without an illegal move, variations
     included;
  2. the main line is that of the original game;
  3. the format requested by the prompt: line length, braces, percent,
     em dash, suffix notation, tags, result;
  4. each mistake and each blunder found by Stockfish is commented on,
     within the agreed scope;
  5. each evaluation quoted does exist in the engine data;
  6. the variations: number, length, support from an engine line, and
     those that an LLM wrongly writes inside a comment;
  7. with --summary: the FEN quoted are valid and come from the folder;
  8. with --summary: the evaluations quoted in the conversation exist
     in the engine data.

Three traps found in real LLM PGNs are named plainly: a blank line in
the body of the game, where python-chess stops reading, a variation
written inside a comment, which is then only text, and a position NAG
contrary to the engine evaluation.

Each line of the report carries one of these markers:

    OK       compliant
    FAIL     contrary to a mandatory instruction of the prompt
    WARNING  to be looked at closely, without being necessarily wrong
    INFO     measure given to compare the LLMs with one another

Exit code: 0 without FAIL, 1 with at least one FAIL, 2 if a file
cannot be read or if the archive is not an IAnalyze one.

The script needs python-chess. If it does not find it, it restarts
with the virtual environment of IAnalyze, local/venv in the folder of
the application.
"""

from __future__ import annotations

import argparse
import contextlib
import decimal
import io
import json
import logging
import os
import pathlib
import re
import sys
import zipfile
import zlib

#: Interpreter of the virtual environment of IAnalyze, in the local/
#: folder of the application, next to this script: the same place as
#: in ianalyze.py, whose real path is followed in the same way.
VENV_IANALYZE = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             "local", "venv", "bin", "python3")

try:
    import chess
    import chess.pgn
except ImportError:
    # Same principle as ianalyze.py: python-chess lives in a dedicated
    # virtual environment, never in the system's Python.
    interpreteur = os.path.expanduser(VENV_IANALYZE)
    if os.path.exists(interpreteur) and sys.executable != interpreteur:
        os.execv(interpreteur, [interpreteur] + sys.argv)
    raise SystemExit(
        "Module chess not found. First run, from the IAnalyze repository: "
        "./ianalyze.py --install-venv")

# python-chess itself writes each illegal move on standard error, in
# English. The report repeats all of them: these lines would be
# duplicates.
logging.getLogger("chess.pgn").setLevel(logging.CRITICAL)

#: Control characters, line feed and tab set aside. The report quotes the
#: PGN and the text returned by the LLM: an escape sequence there would be
#: played by the terminal. Each one is shown as "?".
RE_CONTROLES = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")

#: The seven mandatory tags of the PGN standard, in their order.
SEPT_BALISES = ("Event", "Site", "Date", "Round", "White", "Black", "Result")

#: Maximum length of a line, requested by the prompt.
LONGUEUR_MAX = 79

#: Ranges given by the prompt, repeated here to situate an LLM.
VARIANTE_MAX = 5

#: Key under which lire_archive stores the name of the collection chosen,
#: when the archive given is the parent folder of that collection.
COLLECTE = "chosen collection"
COMMENTES_MIN, COMMENTES_MAX = 15, 25

#: An evaluation written in a comment: "+0.35", "-1,20", "#-3". Also
#: recognized: the sign followed by a space, "+ 0.35", the typographic
#: minus sign, and a third decimal. A number without a sign is not taken
#: for an evaluation: that would confuse "7.5 minutes" with a score. A
#: mate is the exception: IAnalyze writes White's as "#+2", and an LLM
#: quotes it as "#2" just as well.
RE_EVALUATION = re.compile(
    r"(?<![\w.,])([+\-\u2212\u2013][ \u00a0]?\d+[.,]\d{1,3}"
    r"|#[+\-\u2212\u2013]?\d+)(?![\d])")

#: A variation written in a comment: "(12... Nd4 13. Qd2 Nxe2)". It is
#: then only text, which SCID cannot replay.
RE_VARIANTE_TEXTE = re.compile(r"\(\s*(\d+)\s*(\.{1,3})\s*([^()]*)\)")

#: A move in algebraic notation, check and annotation signs included.
RE_SAN = re.compile(
    r"(O-O(?:-O)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?)[+#]?[!?]*$")

#: What the body of the PGN returned may hold outside the comments: a
#: result, a move number, a NAG, a move in standard notation or an
#: annotation symbol, the null move "--" of the original game included.
#: Stricter than the check of ianalyze.py, which reads the PGNs of every
#: site: castling with the letter O only, no P before a pawn move, no
#: hyphen between two squares, a promotion with "=". The suffixes,
#: "Qxa8?", have their own check. The result comes first, then
#: castling, before the move number, which also starts with a digit.
RE_JETON_RENDU = re.compile(
    r"(?:1-0|0-1|1/2-1/2|\*)(?![\w/-])"
    r"|(?:O-O-O|O-O|--|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?)"
    r"[+#]?[!?]{0,2}(?![\w=-])"
    r"|\d+\.*"
    r"|\$\d+"
    r"|[!?]{1,2}")

#: A word of the body, up to a space, a brace, a parenthesis or a
#: semicolon.
RE_MOT_RENDU = re.compile(r"[^\s{}();]+")

#: Castling written with the digit zero, which python-chess reads
#: without a word. It is looked for before RE_JETON_RENDU, which would
#: take its first zero for a move number.
RE_ROQUE_ZERO = re.compile(r"0-0(?:-0)?[+#]?[!?]{0,2}(?![\w=-])")

#: Position evaluation NAGs, according to the side they give as better.
NAG_BLANCS_MIEUX = {14, 16, 18, 20}
NAG_NOIRS_MIEUX = {15, 17, 19, 21}

#: NAG expected by default for each category of move, from the prompt.
NAG_NATURE = {"inaccuracy": 6, "mistake": 2, "blunder": 4}

#: Quality NAGs that praise a move, "!" and "!!": put on a mistake or a
#: blunder of the engine, they give another opinion than its category.
NAG_ELOGE = {1, 3}

#: A FEN position in a text: six fields, the first one with eight ranks.
RE_FEN = re.compile(
    r"((?:[pnbrqkPNBRQK1-8]{1,8}/){7}[pnbrqkPNBRQK1-8]{1,8}"
    r" [wb] (?:-|[KQkq]{1,4}) (?:-|[a-h][36]) \d+ \d+)")


def accorder(nombre: int, singulier: str, pluriel: str) -> str:
    """
    The singular form for one, the plural form otherwise, zero included,
    as English writes it: "1 variation starts", "0 variations start".

    The messages whose count governs a noun or a verb go through it: "the
    1 variations are written" and "1 are the LLM's own" came out of the
    report. The forms in "(s)", such as "3 move(s) commented", stay as
    they are.
    """
    return singulier if nombre == 1 else pluriel


class ArchiveInutilisable(Exception):
    """The archive reads, but its content is not that of IAnalyze."""


class Bilan:
    """Gathers the lines of the report and counts the failures."""

    def __init__(self) -> None:
        self.lignes: list[str] = []
        self.echecs = 0
        self.attentions = 0

    def titre(self, texte: str) -> None:
        self.lignes.append("")
        self.lignes.append("=== %s ===" % texte)

    def noter(self, repere: str, texte: str, details=None) -> None:
        if repere == "FAIL":
            self.echecs += 1
        elif repere == "WARNING":
            self.attentions += 1
        self.lignes.append("  %-9s %s" % (repere, texte))
        # Ten details at most: beyond that, the report becomes unreadable.
        details = list(details or [])
        for d in details[:10]:
            self.lignes.append("            - %s" % d)
        if len(details) > 10:
            self.lignes.append("            - ... and %d more"
                               % (len(details) - 10))

    def controle(self, vrai: bool, texte: str, details=None,
                 grave: bool = True) -> None:
        """OK if true, otherwise FAIL, or WARNING if grave is false."""
        if vrai:
            self.noter("OK", texte)
        else:
            self.noter("FAIL" if grave else "WARNING", texte, details)


# ---------------------------------------------------------------------------
# Reading the archive
# ---------------------------------------------------------------------------

def lire_archive(chemin: pathlib.Path) -> dict[str, str]:
    """
    Returns the useful files of the archive: game.pgn, summary.md and
    stockfish/evaluations.json, from a zip or an unzipped folder.
    """
    voulus = ("game.pgn", "summary.md", "stockfish/evaluations.json")
    trouves: dict[str, str] = {}
    if chemin.is_dir():
        # The folder may be that of the collection or its parent. The
        # three files always come from the same folder: taken one by
        # one, they mixed the game of an interrupted collection with
        # the evaluations of another one.
        dossier = chemin
        if not any((chemin / nom).is_file() for nom in voulus):
            completes = [d for d in sorted(chemin.iterdir()) if d.is_dir()
                         and all((d / nom).is_file() for nom in voulus)]
            if len(completes) > 1:
                raise ArchiveInutilisable(
                    "%s holds %d complete collections: %s. Give the folder of "
                    "the one that the LLM received."
                    % (chemin, len(completes),
                       ", ".join(d.name for d in completes)))
            if completes:
                dossier = completes[0]
                trouves[COLLECTE] = dossier.name
        for nom in voulus:
            if (dossier / nom).is_file():
                trouves[nom] = (dossier / nom).read_text(encoding="utf-8")
    else:
        with zipfile.ZipFile(chemin) as z:
            for membre in z.namelist():
                for nom in voulus:
                    if membre.endswith("/" + nom) or membre == nom:
                        trouves[nom] = z.read(membre).decode("utf-8")
    manquants = [n for n in voulus if n not in trouves]
    if manquants:
        raise ArchiveInutilisable("incomplete "
                                  "archive, missing "
                                  "file(s): %s" % ", ".join(manquants))
    return trouves


def ligne_principale(partie: chess.pgn.Game) -> list[str]:
    """Moves of the main line, in UCI."""
    return [coup.uci() for coup in partie.mainline_moves()]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def retirer_lignes_vides(texte: str) -> tuple[str, list[int]]:
    """
    Removes the blank lines from the body of the game, after the tags.

    Returns the text thus repaired and the numbers of the lines removed.
    The blank lines at the end of the file do not count.

    The body of the first game ends where the tags of another game
    start: a bracket in the first column after a blank line, outside a
    comment. That blank line separates two games, it is kept, and so is
    what follows it: removing it merged the second game into the first,
    whose moves then became illegal.
    """
    lignes = texte.split("\n")
    debut = 0
    while debut < len(lignes) and (lignes[debut].startswith("[")
                                   or not lignes[debut].strip()):
        debut += 1
    dedans = lignes_en_commentaire(texte)
    limite = len(lignes)
    for k in range(debut + 1, len(lignes)):
        if (lignes[k].startswith("[") and not lignes[k - 1].strip()
                and k + 1 not in dedans):
            limite = k
            break
    fin = limite
    while fin > debut and not lignes[fin - 1].strip():
        fin -= 1
    retirees = [n + 1 for n in range(debut, fin) if not lignes[n].strip()]
    corps = [x for x in lignes[debut:fin] if x.strip()]
    repare = "\n".join(lignes[:debut] + corps) + "\n"
    if limite < len(lignes):
        repare += "\n" + "\n".join(lignes[limite:])
    return repare, retirees


def lire_partie(texte: str) -> chess.pgn.Game | None:
    """
    Reads the first game of the text, or returns None.

    On some damaged PGNs, an illegal move followed by a closing
    parenthesis for example, python-chess does not record the error: it
    raises IndexError. The file is then held as unreadable, which gives a
    FAIL in the report and not a Python traceback.
    """
    try:
        return chess.pgn.read_game(io.StringIO(texte))
    except (IndexError, ValueError):
        return None


def resultat_seul(partie: chess.pgn.Game) -> bool:
    """
    True for a "game" that python-chess derives from a lone result: no
    move, no comment, no variation, no tag filled in except Result. Some
    sites write the result again after a blank line: this is not a
    game, the rule of ianalyze.py.
    """
    if partie.variations or partie.comment.strip():
        return False
    return all(valeur in ("?", "????.??.??", "")
               for cle, valeur in partie.headers.items() if cle != "Result")


def parties_en_plus(texte: str) -> int:
    """
    Number of games that follow the first one in the text, a result
    repeated alone not counting. A reading error stops the count where
    it happens.
    """
    flux = io.StringIO(texte)
    autres = 0
    try:
        chess.pgn.read_game(flux)
        while True:
            suivante = chess.pgn.read_game(flux)
            if suivante is None:
                return autres
            if not resultat_seul(suivante):
                autres += 1
    except (IndexError, ValueError):
        return autres


def san_ou_uci(noeud: chess.pgn.ChildNode) -> str:
    """
    The move in algebraic notation, or in UCI if it cannot be played.

    After a reading error, python-chess may leave in the tree a move that
    is illegal in its position: san() then stops on an assertion.
    """
    try:
        return noeud.san()
    except (AssertionError, ValueError):
        return noeud.move.uci()


def controler_lecture(b: Bilan, brut: bytes) -> tuple[str, chess.pgn.Game]:
    """Encoding, then reading by python-chess."""
    b.titre("1. Reading the PGN")
    try:
        texte = brut.decode("utf-8")
        b.noter("OK", "file in UTF-8")
    except UnicodeDecodeError:
        texte = brut.decode("latin-1")
        b.noter("FAIL", "the file is not in UTF-8, read as latin-1")
    if texte.startswith("\ufeff"):
        texte = texte[1:]
        b.noter("WARNING", "byte order mark at the start of the file")
    # Line ends turned into LF: a file coming from Windows would otherwise
    # keep a carriage return at the end of each line, counted as one more
    # character in the check of the 79 columns.
    texte = texte.replace("\r\n", "\n").replace("\r", "\n")
    partie = lire_partie(texte)
    if partie is None:
        b.noter("FAIL", "no readable game in the file")
        raise SystemExit(afficher(b, 1))
    # A blank line in the body of the game: the PGN specification makes it,
    # in export format, the end of the body, and python-chess stops reading
    # there. The rest of the file becomes a second game, without tags. The
    # flaw is named, then the checks go on with the repaired file, to
    # measure the work returned all the same.
    #
    # Every blank line of the body is reported, and not only the one that
    # shortens the main line: placed before a variation or before the end
    # marker, it hides what follows without changing the move count, and
    # what follows it would never be checked.
    repare, retirees = retirer_lignes_vides(texte)
    if retirees:
        relue = lire_partie(repare)
        lus = len(ligne_principale(partie))
        constat = "blank line in the body of the game"
        if relue is not None and len(ligne_principale(relue)) > lus:
            total = len(ligne_principale(relue))
            constat += (": python-chess stops reading there and only sees %d "
                        "of the %d %s"
                        % (lus, total, accorder(total, "ply", "plies")))
        elif set(retirees) <= lignes_en_commentaire(texte):
            # python-chess reads a comment up to its closing brace, blank
            # lines included: the game is read whole. The fault stays, the
            # prompt forbidding it: another reader may stop there.
            constat += (": inside a comment, python-chess reads on, but "
                        "another PGN reader may take it for the end of the "
                        "game")
        else:
            constat += (": python-chess stops reading there, what follows is "
                        "not read")
        b.noter("FAIL", constat, ["line %d" % n for n in retirees])
        if relue is not None:
            b.noter("INFO", "the following checks are made on the file once "
                    "these lines are removed")
            texte, partie = repare, relue
    # A second game in the file: python-chess reads only the first one,
    # and nothing of the others would be checked. Looked for once the
    # blank lines are removed, which would otherwise cut the game in two.
    autres = parties_en_plus(texte)
    b.controle(not autres, "a single game in the file",
               ["%d more %s after the first one, which alone is checked"
                % (autres, accorder(autres, "game", "games"))])
    # python-chess does not stop reading on an illegal move: it records
    # it in errors and gives up on the variation at that point.
    erreurs = [str(e).split(" while parsing")[0] for e in partie.errors]
    b.controle(not erreurs, "no illegal move, variations included (%d reading "
               "error(s))" % len(erreurs), erreurs)
    return texte, partie


def controler_partie(b: Bilan, partie: chess.pgn.Game,
                     origine: chess.pgn.Game) -> bool:
    """The main line must be that of the original game."""
    b.titre("2. Main line")
    rendue, attendue = ligne_principale(partie), ligne_principale(origine)
    identique = rendue == attendue
    details = []
    if not identique:
        commun = 0
        for x, y in zip(rendue, attendue):
            if x != y:
                break
            commun += 1
        details.append("identical up to ply %d, then %s instead of %s"
                       % (commun,
                          rendue[commun] if commun < len(rendue) else "end",
                          attendue[commun] if commun < len(attendue)
                          else "end"))
        details.append("%d %s returned, %d expected"
                       % (len(rendue), accorder(len(rendue), "ply", "plies"),
                          len(attendue)))
        if partie.errors:
            # On an illegal move, python-chess gives up reading what
            # follows: the main line may come out truncated.
            details.append("may come from an illegal move found in 1")
    b.controle(identique, "main line identical to the original "
               "game (%d %s)" % (len(attendue),
                                 accorder(len(attendue), "ply", "plies")),
               details)
    return identique


def commentaires(partie: chess.pgn.Game) -> list[tuple[str, str]]:
    """All the comments of the PGN, with the place where they are."""
    trouves = []
    if partie.comment:
        trouves.append(("before move 1", partie.comment))

    def parcourir(noeud: chess.pgn.GameNode) -> None:
        for enfant in noeud.variations:
            lieu = "%d%s %s" % (
                noeud.board().fullmove_number,
                "." if noeud.board().turn == chess.WHITE else "...",
                san_ou_uci(enfant))
            for texte in (enfant.starting_comment, enfant.comment):
                if texte:
                    trouves.append((lieu, texte))
            parcourir(enfant)

    parcourir(partie)
    return trouves


def accolades_orphelines(texte: str) -> list[str]:
    """
    Lines where a closing brace appears outside any comment.

    A closing brace written in a comment ends it too early: the end of the
    comment falls into the body of the game, where python-chess ignores it
    word after word, without an error. What remains of it is a second
    closing brace, which nothing opened: that is the one we look for, in
    the raw text.
    """
    trouvees = []
    ouvert = False
    for n, ligne in enumerate(texte.split("\n"), 1):
        if not ouvert and ligne.startswith("["):
            continue
        for c in ligne:
            if ouvert:
                ouvert = c != "}"
            elif c == "{":
                ouvert = True
            elif c == ";":
                # End-of-line comment.
                break
            elif c == "}":
                trouvees.append("line %d: extra closing brace" % n)
    return trouvees


def mots_hors_commentaires(texte: str) -> tuple[list[str], list[str]]:
    """
    Castlings written with zeros, and words of the body that are neither
    a PGN element nor in a comment, each list grouped by line.

    python-chess skips without an error what it does not recognize:
    free text written outside the braces is lost for the reader, a move
    written "Pg2xf3" is read as g2xf3 and castling written "0-0" as
    O-O, which hides the flaw. Skipped like python-chess does: the tag
    lines and the escape lines in the first column, the comments between
    braces and those of a semicolon, up to the end of the line. An
    unclosed brace ends the search: the rest of the file is a comment
    for python-chess, and the reading of the game reports it.

    A closing brace written in a comment ends it too early: the end of
    the comment falls outside the braces, up to the closing brace left
    over. These words belong to the flaw of the brace, which has its own
    check: they are not reported a second time.
    """
    zeros: dict[int, list[str]] = {}
    etrangers: list[tuple[int, str]] = []
    # Foreign words met since the end of the last comment: they are the
    # tail of that comment if a closing brace left over follows them.
    depuis = 0
    i, n = 0, len(texte)
    ligne = 1
    while i < n:
        c = texte[i]
        colonne_un = i == 0 or texte[i - 1] == "\n"
        if c == "\n":
            ligne += 1
            i += 1
        elif c.isspace() or c in "()":
            i += 1
        elif c == "{":
            fin = texte.find("}", i)
            if fin < 0:
                break
            ligne += texte.count("\n", i, fin)
            i = fin + 1
            depuis = len(etrangers)
        elif c == "}":
            # Closing brace left over, which accolades_orphelines reports.
            del etrangers[depuis:]
            i += 1
        elif c == ";" or (c in "[%" and colonne_un):
            fin = texte.find("\n", i)
            i = n if fin < 0 else fin
        else:
            m = RE_ROQUE_ZERO.match(texte, i)
            if m:
                zeros.setdefault(ligne, []).append(m.group(0))
                i = m.end()
                continue
            m = RE_JETON_RENDU.match(texte, i)
            if m:
                i = m.end()
                continue
            m = RE_MOT_RENDU.match(texte, i)
            if m is None:
                i += 1
                continue
            etrangers.append((ligne, m.group(0)))
            i = m.end()

    def regrouper(trouves: dict[int, list[str]]) -> list[str]:
        return ["line %d: %s" % (k, " ".join(v)[:60])
                for k, v in sorted(trouves.items())]

    par_ligne: dict[int, list[str]] = {}
    for k, mot in etrangers:
        par_ligne.setdefault(k, []).append(mot)
    return regrouper(zeros), regrouper(par_ligne)


def lignes_en_commentaire(texte: str) -> set[int]:
    """
    Numbers of the lines that start inside a comment between braces.

    python-chess reads a comment up to its closing brace, blank lines
    included: a blank line there does not end the game for it.
    """
    dedans: set[int] = set()
    ouvert = False
    for n, ligne in enumerate(texte.split("\n"), 1):
        if ouvert:
            dedans.add(n)
        elif ligne.startswith("["):
            continue
        for c in ligne:
            if ouvert:
                ouvert = c != "}"
            elif c == "{":
                ouvert = True
            elif c == ";":
                break
    return dedans


def balises_du_texte(texte: str) -> list[str]:
    """
    Names of the tags in the order in which the file writes them.

    python-chess always puts the seven mandatory tags first, whatever the
    order of the file, and creates the missing ones: its dictionary
    therefore says nothing of what the LLM wrote.
    """
    noms = []
    for ligne in texte.split("\n"):
        m = re.match(r'\[\s*([A-Za-z0-9_]+)\s+"', ligne)
        if m:
            noms.append(m.group(1))
        elif ligne.strip():
            break
    return noms


def controler_format(b: Bilan, texte: str, partie: chess.pgn.Game,
                     origine: chess.pgn.Game, demi_coups: int,
                     court: bool = False,
                     balises_origine: list[str] | None = None) -> None:
    """
    Mandatory format constraints of the prompt.

    `court` is true for a PGN returned from the short prompt of
    --prompt-only: only the checks that this prompt grounds remain, the
    braces, the tags copied and the end marker.
    `balises_origine` then gives the names of the tags of the original
    game, in the order in which its file writes them: among the seven
    mandatory tags of the standard, only those are expected.
    """
    b.titre("3. Format")
    lignes = texte.split("\n")
    if not court:
        longues = ["line %d: %d characters" % (n + 1, len(x))
                   for n, x in enumerate(lignes) if len(x) > LONGUEUR_MAX]
        b.controle(not longues, "no line of more than %d characters"
                   % LONGUEUR_MAX, longues)

    notes = commentaires(partie)
    # An opening brace in a comment stays in its text; a closing one
    # ends it too early, and only shows in the raw text.
    accolades = [lieu for lieu, t in notes if "{" in t or "}" in t]
    accolades += accolades_orphelines(texte)
    b.controle(not accolades, "no brace in a comment",
               accolades)
    # Outside the comments, nothing but the game: python-chess skips the
    # rest without a word, and reads "Pg2xf3" or "0-0" all the same.
    # Castling with zeros is only a fault for the full prompt, which
    # forbids it: the short one asks to copy the moves as they are.
    zeros, etrangers = mots_hors_commentaires(texte)
    b.controle(not etrangers, "outside the braces, only moves in standard "
               "notation, move numbers, NAGs and the result", etrangers)
    if not court:
        b.controle(not zeros, "castling written with the letter O, never "
                   "the digit zero", zeros)
    corps = "\n".join(x for x in lignes if not x.startswith("["))
    hors_commentaires = re.sub(r"\{[^}]*\}", " ", corps)
    if not court:
        pourcents = [lieu for lieu, t in notes if "%" in t]
        b.controle(not pourcents, "no % character in a comment",
                   pourcents)
        cadratins = [lieu for lieu, t in notes if "\u2014" in t]
        b.controle(not cadratins, "no em dash", cadratins)
        virgules = [lieu for lieu, t in notes if ";" in t]
        b.controle(not virgules, "no semicolon in a comment",
                   virgules, grave=False)

        # Suffix notation (Qxa8?): looked for outside the comments, where
        # a question mark is simply punctuation.
        suffixes = sorted(set(re.findall(
            r"\b(?:[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?"
            r"|O-O(?:-O)?)[+#]?[!?]+", hors_commentaires)))
        b.controle(not suffixes, "no suffix notation, NAGs only",
                   suffixes)

    # Tags: the seven mandatory ones first, the others in alphabetical
    # order, and their values taken from the original game.
    noms = balises_du_texte(texte)
    if court:
        # The short prompt asks to copy the tags, nothing more:
        # among the seven of the standard, only those that the original
        # game carries are expected, in the order in which it writes them.
        # Requiring all of them gave a failure to a faithful PGN when the
        # game given carried only three.
        attendues = [n for n in (balises_origine or [])
                     if n in SEPT_BALISES]
        rendues = [n for n in noms if n in attendues]
        absentes = [n for n in attendues if n not in noms]
        b.controle(rendues == attendues,
                   "the mandatory tags of the original game, in the same "
                   "order",
                   ["order returned: %s" % ", ".join(noms)]
                   + ["missing: %s" % n for n in absentes])
    else:
        absentes = [n for n in SEPT_BALISES if n not in noms]
        b.controle(tuple(noms[:7]) == SEPT_BALISES,
                   "the seven mandatory tags, in order",
                   ["order returned: %s" % ", ".join(noms[:7])]
                   + ["missing: %s" % n for n in absentes])
    autres = noms[7:]
    if not court:
        b.controle(autres == sorted(autres),
                   "the other tags in alphabetical order",
                   ["order returned: %s" % ", ".join(autres)], grave=False)
    differentes = [
        '%s: "%s" instead of "%s"'
        % (n, partie.headers.get(n), origine.headers.get(n))
        for n in SEPT_BALISES
        if partie.headers.get(n) != origine.headers.get(n)]
    b.controle(not differentes, "values of the seven tags taken from the "
               "original game", differentes)
    if not court:
        b.controle(bool(partie.headers.get("Annotator", "").strip("? ")),
                   'Annotator tag filled in: "%s"'
                   % partie.headers.get("Annotator", ""), grave=False)
        compte = partie.headers.get("PlyCount", "")
        b.controle(compte == str(demi_coups),
                   'PlyCount tag: "%s", expected "%d"'
                   % (compte, demi_coups), grave=False)

    # End marker: the last word of the file, outside the comments.
    mots = hors_commentaires.split()
    marqueur = mots[-1] if mots else ""
    b.controle(marqueur == partie.headers.get("Result"),
               'end marker "%s" identical to the Result tag "%s"'
               % (marqueur, partie.headers.get("Result")))


def perimetre_convenu(synthese_archive: str) -> int | None:
    """
    Number of moves of the scope that the player gave to the script, or
    None for the whole game.

    The answer is in the instructions of summary.md, on the line
    "- a. Scope: ...", which ianalyze.py writes from the label of its
    first startup question (QUESTIONS_CONTEXTE): the label carries its
    letter, and a pattern without it never matched a real summary. It
    is free text: the first number it carries is taken for the number
    of moves, "the first 20 moves" giving 20. An answer left at its
    default, or without a number, means the whole game.
    """
    m = re.search(r"(?m)^- a\. Scope: (.*)$", synthese_archive)
    if m is None or m.group(1).rstrip().endswith("(default)"):
        return None
    nombre = re.search(r"\d+", m.group(1))
    return int(nombre.group()) if nombre and int(nombre.group()) else None


def controler_couverture(b: Bilan, partie: chess.pgn.Game,
                         evaluations: list[dict],
                         court: bool = False,
                         perimetre: int | None = None) -> None:
    """
    Each mistake and each blunder must be commented on.

    The short prompt asks for neither a summary before the first move nor
    NAGs: with `court`, these two points are not checked.

    The prompt limits the comments to the scope agreed with the player:
    with `perimetre`, in moves, a mistake played beyond it is not
    expected, and its absence is not a fault.

    The quality NAGs are compared with the category of the engine, for
    information: another opinion is a NAG other than the one of the
    category, "!" or "!!" on a mistake or a blunder, or "?!", "?" or
    "??" on a move that the engine does not classify, its loss staying
    under the threshold of an inaccuracy.
    """
    b.titre("4. Commented moves")
    if not court:
        resume = partie.comment.strip()
        b.controle(bool(resume), "overview of the game before move 1 (%d "
                   "line(s), 6 to 10 requested)"
                   % (resume.count("\n") + 1 if resume else 0))

    noeuds = list(partie.mainline())
    commentes = [n for n in noeuds if n.comment.strip()]
    if court:
        b.noter("INFO", "%d move(s) commented out of %d"
                % (len(commentes), len(noeuds)))
    else:
        b.noter("INFO", "%d move(s) commented out of %d, %d to %d aimed for "
                "over a whole game" % (len(commentes), len(noeuds),
                                       COMMENTES_MIN, COMMENTES_MAX))
    b.noter("INFO", "%d move(s) carrying a NAG"
            % sum(1 for n in noeuds if n.nags))

    if perimetre:
        b.noter("INFO", "agreed scope: %s, the mistakes and blunders played "
                "beyond are not expected"
                % ("the first move" if perimetre == 1
                   else "the first %d moves" % perimetre))
    oublies, sans_nag, fautes = [], [], 0
    for e in evaluations:
        if e.get("category") not in ("mistake", "blunder"):
            continue
        if perimetre and e["move_number"] > perimetre:
            continue
        fautes += 1
        indice = e["ply"] - 1
        if indice >= len(noeuds):
            continue
        lieu = "%d%s %s (%s)" % (
            e["move_number"], "." if e["side_to_move"] == "White" else "...",
            e["played"]["san"], e["category"])
        if not noeuds[indice].comment.strip():
            oublies.append(lieu)
        elif not noeuds[indice].nags:
            sans_nag.append(lieu)
    b.controle(not oublies, "the %d mistake(s) and blunder(s) of Stockfish "
               "are all commented on (%d missed)" % (fautes, len(oublies)),
               oublies)
    if fautes > len(oublies) and not court:
        b.controle(not sans_nag, "each mistake or blunder commented on "
                   "carries a NAG", sans_nag, grave=False)

    if court:
        # The short prompt asks for no NAG: neither their agreement with the
        # engine nor their category is checked.
        return
    # Position NAG contrary to the engine: "slight advantage for Black" put
    # on a move after which Stockfish gives White as clearly better.
    contraires, accords, ecarts = [], 0, []
    for e in evaluations:
        indice = e["ply"] - 1
        if indice >= len(noeuds):
            continue
        nags = noeuds[indice].nags
        lieu = "%d%s %s" % (
            e["move_number"], "." if e["side_to_move"] == "White" else "...",
            e["played"]["san"])
        score = e["played"].get("score") or ""
        signe = 0
        if score.startswith("#"):
            signe = -1 if "-" in score else 1
        elif re.fullmatch(r"[+-]\d+\.\d+", score) and abs(float(score)) >= 0.5:
            signe = 1 if float(score) > 0 else -1
        if (signe < 0 and nags & NAG_BLANCS_MIEUX) or (
                signe > 0 and nags & NAG_NOIRS_MIEUX):
            contraires.append("%s: NAG $%d, engine %s"
                              % (lieu, min(nags & (NAG_BLANCS_MIEUX
                                                   | NAG_NOIRS_MIEUX)),
                                 score))
        attendu = NAG_NATURE.get(e.get("category") or "")
        negatifs = nags & set(NAG_NATURE.values())
        if attendu and negatifs:
            if attendu in nags:
                accords += 1
            else:
                ecarts.append("%s: %s for the engine, NAG $%d"
                              % (lieu, e["category"], min(negatifs)))
        elif attendu and nags & NAG_ELOGE:
            # A mistake or a blunder praised as a good move.
            ecarts.append("%s: %s for the engine, NAG $%d"
                          % (lieu, e["category"], min(nags & NAG_ELOGE)))
        elif negatifs and e.get("cp_loss") is not None:
            # A move that the engine does not classify, marked dubious,
            # poor or blunder: on 25 November 2026, an LLM put "?!" on
            # seven moves that lost less than 50 cp, which the count of
            # the other opinions did not show. A null move, which the
            # engine does not evaluate, has no loss and is set aside.
            # The loss is written as in the summary, "17" and not "17.0".
            ecarts.append("%s: no category for the engine (%g cp), NAG $%d"
                          % (lieu, e["cp_loss"], min(negatifs)))
    b.controle(not contraires, "no position NAG contrary to the evaluation of "
               "the engine", contraires)
    b.noter("INFO", "quality NAGs: %d matching the category given by the "
            "engine, %d of another opinion" % (accords, len(ecarts)), ecarts)


def controler_chiffres(b: Bilan, textes: list[tuple[str, str]],
                       evaluations: list[dict], titre: str) -> None:
    """A quoted evaluation must exist in the engine data."""
    b.titre(titre)
    connues = set()
    for e in evaluations:
        for coup in [e["played"]] + e["best"]:
            score = coup.get("score") or ""
            connues.add(score)
            # An LLM readily rounds to one decimal: "+0.35" quoted as
            # "+0.4" or "+0.3" stays faithful to the folder. The computation is
            # done in decimal: in floating point, round(0.35, 1) returns 0.3.
            m = re.fullmatch(r"([+-])(\d+\.\d\d)", score)
            if m:
                valeur = decimal.Decimal(m.group(2))
                for mode in (decimal.ROUND_HALF_UP, decimal.ROUND_DOWN):
                    connues.add("%s%s" % (m.group(1), valeur.quantize(
                        decimal.Decimal("0.1"), rounding=mode)))
    citees = 0
    inconnues: list[str] = []
    douteuses: list[str] = []
    for lieu, texte in textes:
        for brut in RE_EVALUATION.findall(texte):
            citees += 1
            # Same writing as the folder before comparing: ASCII sign
            # stuck to the number, decimal point.
            lu = re.sub(r"[ \u00a0]", "", brut.replace(",", "."))
            lu = lu.replace("\u2212", "-").replace("\u2013", "-")
            # A third decimal at zero adds nothing: "+1.910" is the "+1.91"
            # of the folder. Any other third decimal is a precision that
            # the engine did not give.
            lu = re.sub(r"^([+-]\d+\.\d\d)0$", r"\1", lu)
            # A mate quoted without a sign is White's: "#2" means
            # "#+2", the form of the folder.
            sans_signe = re.match(r"#\d", lu) is not None
            lu = re.sub(r"^#(\d)", r"#+\1", lu)
            if lu in connues:
                continue
            # Without a sign, "#7" may be a rank, "mistake #7", as well as
            # a mate: not found, it is only a warning.
            (douteuses if sans_signe else inconnues).append(
                "%s: %s" % (lieu, brut))
    b.noter("INFO", "%d evaluation(s) quoted" % citees)
    b.controle(not inconnues, "all are found in the data of the engine (%d "
               "not found)" % len(inconnues), inconnues)
    if douteuses:
        b.noter("WARNING", "%d \"#N\" written without a sign and not found "
                "in the data of the engine: a rank, \"mistake #7\", rather "
                "than a mate?" % len(douteuses), douteuses)


def lignes_du_moteur(evaluations: list[dict]) -> dict[int, list[list[str]]]:
    """For each ply, the principal variations of the engine, in UCI."""
    lignes: dict[int, list[list[str]]] = {}
    for e in evaluations:
        lignes[e["ply"]] = [
            c["pv_uci"] for c in [e["played"]] + e["best"] if c["pv_uci"]]
    return lignes


def controler_variantes_en_texte(b: Bilan, partie: chess.pgn.Game,
                                 evaluations: list[dict],
                                 jouables: int,
                                 court: bool = False) -> None:
    """
    Variations written inside a comment.

    Between braces, a sequence of moves in parentheses is only text: SCID
    does not replay it, and nothing guarantees its legality. The script
    therefore replays it itself, from the position that its move number
    designates.
    """
    lignes_moteur = lignes_du_moteur(evaluations)
    trouvees, illegales, perdues, longues = 0, [], [], []
    legales, appuyees = 0, 0
    for demicoup, noeud in enumerate(partie.mainline(), start=1):
        for m in RE_VARIANTE_TEXTE.finditer(noeud.comment):
            mots = []
            for mot in m.group(3).split():
                mot = re.sub(r"^\d+\.+", "", mot)
                if mot and not mot.startswith("$"):
                    mots.append(mot)
            if not mots or not all(RE_SAN.match(x) for x in mots):
                # A prose parenthesis, "(15 to 20 moves)" for example.
                continue
            trouvees += 1
            numero = int(m.group(1))
            trait = chess.BLACK if len(m.group(2)) > 1 else chess.WHITE
            texte = "(%s%s %s)" % (m.group(1), m.group(2), " ".join(mots))
            # The variation replaces the played move, or extends it.
            depart, moteur = None, []
            for plateau, indice in ((noeud.parent.board(), demicoup),
                                    (noeud.board(), demicoup + 1)):
                if (plateau.fullmove_number == numero
                        and plateau.turn == trait):
                    depart, moteur = plateau, lignes_moteur.get(indice, [])
                    break
            if depart is None:
                perdues.append(texte)
                continue
            joues, fautif = [], None
            for mot in mots:
                try:
                    coup = depart.parse_san(mot.rstrip("!?"))
                except ValueError:
                    fautif = mot
                    break
                joues.append(coup.uci())
                depart.push(coup)
            if fautif:
                illegales.append("%s: %s is illegal" % (texte, fautif))
                continue
            legales += 1
            if len(joues) > VARIANTE_MAX:
                longues.append("%s: %d plies" % (texte, len(joues)))
            if any(pv[:2] == joues[:2] for pv in moteur):
                appuyees += 1
    if not trouvees:
        return
    if jouables:
        constat = ("%d %s written inside a comment: %s only text, SCID "
                   "does not replay %s"
                   % (trouvees,
                      accorder(trouvees, "variation", "variations"),
                      accorder(trouvees, "it is", "they are"),
                      accorder(trouvees, "it", "them")))
    elif trouvees == 1:
        constat = ("no playable variation: the only variation is written "
                   "inside a comment, where it is only text")
    else:
        constat = ("no playable variation: the %d variations are written "
                   "inside the comments, where they are only text" % trouvees)
    b.controle(False, constat, grave=not jouables)
    b.controle(not illegales, "replayed by the script, these variations are "
               "all legal (%d illegal)" % len(illegales), illegales)
    if perdues:
        b.noter("WARNING", "%d variation(s) whose move number matches no "
                "nearby position" % len(perdues),
                perdues)
    if longues and not court:
        b.noter("WARNING", "variation(s) of more than %d plies"
                % VARIANTE_MAX, longues)
    b.noter("INFO", "%d legal, %d of which %s from a line of the engine"
            % (legales, appuyees, accorder(appuyees, "starts", "start")))


def controler_variantes(b: Bilan, partie: chess.pgn.Game,
                        evaluations: list[dict],
                        court: bool = False) -> None:
    """
    Number and length of the variations, support from an engine line.

    The short prompt sets no length: with `court`, a variation of more
    than five plies is not reported.
    """
    b.titre("6. Variations")
    lignes_moteur = lignes_du_moteur(evaluations)

    variantes = []      # (place, length, backed by the engine?)
    for indice, noeud in enumerate([partie] + list(partie.mainline())):
        for autre in noeud.variations[1:]:
            coups, n = [], autre
            while True:
                coups.append(n.move.uci())
                if not n.variations:
                    break
                n = n.variations[0]
            lieu = "%d%s %s" % (
                noeud.board().fullmove_number,
                "." if noeud.board().turn == chess.WHITE else "...",
                san_ou_uci(autre))
            # Backed: its first moves, two at most, are those of a line
            # that the engine gives for this ply.
            debut = coups[:2]
            appuyee = any(pv[:len(debut)] == debut
                          for pv in lignes_moteur.get(indice + 1, []))
            variantes.append((lieu, len(coups), appuyee))

    b.noter("INFO", "%d playable variation(s) on the main line"
            % len(variantes))
    controler_variantes_en_texte(b, partie, evaluations, len(variantes),
                                 court)
    if not variantes:
        return
    if not court:
        longues = ["%s: %d plies" % (lieu, n)
                   for lieu, n, _ in variantes if n > VARIANTE_MAX]
        b.controle(not longues, "no variation of more than %d plies"
                   % VARIANTE_MAX, longues, grave=False)
    libres = [lieu for lieu, _, appuyee in variantes if not appuyee]
    du_moteur = len(variantes) - len(libres)
    b.noter("INFO", "%d %s from a line of the engine, %d %s the LLM's own"
            % (du_moteur,
               accorder(du_moteur, "variation starts", "variations start"),
               len(libres), accorder(len(libres), "is", "are")),
            libres)


def controler_synthese(b: Bilan, texte: str, evaluations: list[dict],
                       synthese_archive: str,
                       origine: chess.pgn.Game,
                       court: bool = False) -> None:
    """
    FEN quoted in the final summary of the LLM, and em dash.

    The short prompt asks for neither FEN nor typography: with `court`,
    the em dash and the number of FEN are not checked. A FEN quoted
    anyway must stay valid and come from the game.
    """
    b.titre("7. Conversation: positions quoted, language")
    # A FEN of the folder is recognized by its first four fields: the
    # move counters do not identify the position.

    def clef(fen: str) -> str:
        return " ".join(fen.split()[:4])

    connues = {clef(e["fen"]) for e in evaluations}
    # All the positions of the game, the last one included, which the
    # evaluations do not carry: they give the position before
    # each move.
    plateau = origine.board()
    connues.add(clef(plateau.fen()))
    for coup in origine.mainline_moves():
        plateau.push(coup)
        connues.add(clef(plateau.fen()))
    connues |= {clef(f) for f in RE_FEN.findall(synthese_archive)}
    citees = RE_FEN.findall(texte)
    if court:
        b.noter("INFO", "%d FEN quoted" % len(citees))
    else:
        b.controle("\u2014" not in texte, "no em dash in the conversation (%d "
                   "found)" % texte.count("\u2014"))
        b.controle(len(citees) >= 2, "%d FEN quoted, two requested"
                   % len(citees), grave=False)
    if not citees:
        return
    invalides, etrangeres = [], []
    for fen in citees:
        try:
            plateau = chess.Board(fen)
        except ValueError:
            invalides.append(fen)
            continue
        if not plateau.is_valid():
            invalides.append(fen)
        # The standard writes the en passant square after any double
        # step of a pawn, python-chess only when the capture can be
        # played: the FEN quoted is compared in the writing of the folder.
        elif clef(plateau.fen()) not in connues:
            etrangeres.append(fen)
    b.controle(not invalides, "all the FEN are valid positions",
               invalides)
    b.controle(not etrangeres, "all come from a position of the game",
               etrangeres)


# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------

def afficher(b: Bilan, code: int) -> int:
    """Writes the report and returns the exit code."""
    print("\n".join(RE_CONTROLES.sub("?", ligne) for ligne in b.lignes))
    print()
    print("=== Totals ===")
    print("  failures : %d" % b.echecs)
    print("  warnings : %d" % b.attentions)
    return code


def configurer_sortie() -> None:
    """
    A character that the output encoding cannot represent, the "é" of a
    name under PYTHONIOENCODING=ascii for example, becomes "?" instead of
    stopping the report on UnicodeEncodeError: the rule of ianalyze.py.
    """
    for flux in (sys.stdout, sys.stderr):
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is not None:
            with contextlib.suppress(ValueError, OSError):
                reconfigurer(errors="replace")


def main(argv: list[str]) -> int:
    configurer_sortie()
    p = argparse.ArgumentParser(
        description="Checks the annotated PGN returned by an LLM from an "
                    "IAnalyze archive.")
    p.add_argument("archive", help="zip of ianalyze.py, or its unzipped "
                                   "folder")
    p.add_argument("pgn", help="annotated PGN returned by the LLM, or - if it "
                               "returned none")
    p.add_argument("--summary", dest="synthese", metavar="FILE",
                   help="final summary of the LLM, copied into a text file")
    p.add_argument("--name", dest="nom", metavar="NAME",
                   default="", help="name of the model tried")
    p.add_argument("--prompt-only", dest="prompt_seul", action="store_true",
                   help="the PGN answers the short prompt of ianalyze.py "
                        "--prompt-only: the checks that this prompt does not "
                        "ask for are skipped")
    p.add_argument("--scope", dest="perimetre", metavar="N", type=int,
                   help="scope agreed with the LLM, in moves: the mistakes "
                        "and blunders played after move N are not expected. "
                        "Without this option, the scope is the one that the "
                        "player gave to the script, read in the archive")
    options = p.parse_args(argv)
    if options.perimetre is not None and options.perimetre < 1:
        p.error("--scope expects a number of moves, 1 at least")

    try:
        fichiers = lire_archive(pathlib.Path(options.archive))
        brut = (None if options.pgn == "-"
                else pathlib.Path(options.pgn).read_bytes())
        synthese_llm = None
        if options.synthese:
            synthese_llm = pathlib.Path(options.synthese).read_text(
                encoding="utf-8", errors="replace")
        origine = lire_partie(fichiers["game.pgn"])
        evaluations = json.loads(fichiers["stockfish/evaluations.json"])
        if origine is None or not ligne_principale(origine):
            raise ArchiveInutilisable("game.pgn of the archive holds no game")
        if not (isinstance(evaluations, list) and all(
                isinstance(e, dict) and isinstance(e.get("played"), dict)
                and isinstance(e.get("best"), list)
                and "ply" in e for e in evaluations)):
            raise ArchiveInutilisable("stockfish/evaluations.json does not "
                                      "have the form written by IAnalyze")
    except (OSError, zipfile.BadZipFile, zlib.error, ValueError,
            ArchiveInutilisable) as e:
        # ValueError covers a file that is not in UTF-8 and an invalid JSON.
        # In all these cases no check could start: the code 2 tells it
        # apart from a report with failures.
        print("Cannot read: %s" % e, file=sys.stderr)
        return 2

    b = Bilan()
    b.lignes.append("Check of an analysis returned by an LLM")
    if options.nom:
        b.lignes.append("  model      : %s" % options.nom)
    # The name of a path such as "." is empty: the path given is then
    # used as it is.
    b.lignes.append("  archive    : %s" % (pathlib.Path(options.archive).name
                                           or options.archive))
    if COLLECTE in fichiers:
        b.lignes.append("  collection : %s, the only complete collection of "
                        "the folder"
                        % fichiers[COLLECTE])
    b.lignes.append("  PGN        : %s" % pathlib.Path(options.pgn).name)
    if options.prompt_seul:
        b.lignes.append("  prompt     : short (--prompt-only), checks limited "
                        "to what it asks for")

    if brut is None:
        # The LLM returned no file, and no PGN in the conversation.
        b.titre("1. Reading the PGN")
        b.noter("FAIL", "no PGN returned: checks 2 to 6 do not apply")
        if synthese_llm is not None:
            controler_synthese(b, synthese_llm, evaluations,
                               fichiers["summary.md"], origine,
                               options.prompt_seul)
            controler_chiffres(b, [("conversation", synthese_llm)],
                               evaluations,
                               "8. Evaluations quoted in the conversation")
        return afficher(b, 1)

    texte, partie = controler_lecture(b, brut)
    identique = controler_partie(b, partie, origine)
    controler_format(b, texte, partie, origine,
                     len(ligne_principale(origine)), options.prompt_seul,
                     balises_du_texte(fichiers["game.pgn"]))
    if identique:
        controler_couverture(
            b, partie, evaluations, options.prompt_seul,
            options.perimetre or perimetre_convenu(fichiers["summary.md"]))
    else:
        # Without the same main line, the plies no longer
        # match: these checks would make no sense.
        b.titre("4. Commented moves")
        b.noter("WARNING", "not checked, the main line differs")
    controler_chiffres(b, commentaires(partie), evaluations,
                       "5. Evaluations quoted in the PGN")
    if identique:
        controler_variantes(b, partie, evaluations, options.prompt_seul)
    if synthese_llm is not None:
        controler_synthese(b, synthese_llm, evaluations,
                           fichiers["summary.md"], origine,
                           options.prompt_seul)
        controler_chiffres(b, [("conversation", synthese_llm)],
                           evaluations,
                           "8. Evaluations quoted in the conversation")
    return afficher(b, 1 if b.echecs else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
