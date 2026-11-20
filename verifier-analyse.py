#!/usr/bin/env python3
"""
verifier-analyse.py : contrôle le PGN annoté rendu par un LLM.

Le script compare ce qu'un LLM a produit à l'archive d'IAnalyze qu'il a
reçue, et sort le même bilan pour chaque LLM essayé. Il ne juge pas la
qualité du commentaire : il vérifie ce qui se vérifie à la machine.

    ./verifier-analyse.py ARCHIVE PGN [--synthese FICHIER] [--nom NOM]
                          [--prompt-seul]

    ARCHIVE     le zip produit par ianalyze.py, ou son dossier
                décompressé
    PGN         le fichier .pgn rendu par le LLM, ou un tiret, "-", si le
                LLM n'a rendu aucun fichier : seule la synthèse est alors
                contrôlée
    --synthese  facultatif : la synthèse finale du LLM, copiée de la
                conversation dans un fichier texte. Les FEN et les
                évaluations qu'elle cite sont alors contrôlées aussi
    --nom       facultatif : nom du modèle essayé, repris en tête du bilan
    --prompt-seul
                le PGN répond au prompt court de ianalyze.py --prompt-seul.
                Ce prompt demande moins : les contrôles qu'il ne fonde pas
                sont sautés (lignes de 79 caractères, résumé avant le coup
                1, NAG, pour cent, balises Annotator et PlyCount)

Ce qui est contrôlé :

  1. le PGN se lit, en UTF-8, sans coup illégal, variantes comprises ;
  2. la ligne principale est celle de la partie d'origine ;
  3. le format demandé par le prompt : longueur des lignes, accolades,
     pour cent, tiret cadratin, notation suffixe, balises, résultat ;
  4. chaque erreur et chaque gaffe relevée par Stockfish est commentée ;
  5. chaque évaluation citée existe bien dans les données du moteur ;
  6. les variantes : nombre, longueur, appui sur une ligne du moteur,
     et celles qu'un LLM écrit à tort à l'intérieur d'un commentaire ;
  7. avec --synthese : les FEN citées sont valides et viennent du dossier ;
  8. avec --synthese : les évaluations citées dans la conversation
     existent dans les données du moteur.

Trois pièges relevés sur de vrais PGN de LLM sont nommés en clair : une
ligne vide dans le corps de la partie, où python-chess arrête sa lecture,
une variante écrite à l'intérieur d'un commentaire, qui n'est alors que
du texte, et un NAG de position contraire à l'évaluation du moteur.

Chaque ligne du bilan porte l'un de ces repères :

    OK         conforme
    ECHEC      contraire à une consigne impérative du prompt
    ATTENTION  à regarder de près, sans être forcément fautif
    INFO       mesure donnée pour comparer les LLM entre eux

Code de retour : 0 sans ECHEC, 1 avec au moins un ECHEC, 2 si un fichier
ne peut pas être lu ou si l'archive n'est pas celle d'IAnalyze.

Le script demande python-chess. S'il ne le trouve pas, il se relance avec
l'environnement virtuel d'IAnalyze, ~/.local/share/IAnalyze/venv.
"""

from __future__ import annotations

import argparse
import decimal
import io
import json
import logging
import os
import pathlib
import re
import sys
import zlib
import zipfile

VENV_IANALYZE = "~/.local/share/IAnalyze/venv/bin/python3"

try:
    import chess
    import chess.pgn
except ImportError:
    # Même principe que ianalyze.py : python-chess vit dans un
    # environnement virtuel dédié, jamais dans le Python du système.
    interpreteur = os.path.expanduser(VENV_IANALYZE)
    if os.path.exists(interpreteur) and sys.executable != interpreteur:
        os.execv(interpreteur, [interpreteur] + sys.argv)
    raise SystemExit(
        "Module chess introuvable. Lancez d'abord, depuis le dépôt "
        "IAnalyze : ./ianalyze.py --installer-venv")

# python-chess écrit lui-même chaque coup illégal sur la sortie d'erreur,
# en anglais. Le bilan les reprend tous : ces lignes feraient doublon.
logging.getLogger("chess.pgn").setLevel(logging.CRITICAL)

#: Les sept balises obligatoires du standard PGN, dans leur ordre.
SEPT_BALISES = ("Event", "Site", "Date", "Round", "White", "Black", "Result")

#: Longueur maximale d'une ligne, demandée par le prompt.
LONGUEUR_MAX = 79

#: Fourchettes données par le prompt, reprises ici pour situer un LLM.
VARIANTE_MAX = 5
COMMENTES_MIN, COMMENTES_MAX = 15, 25

#: Une évaluation écrite dans un commentaire : "+0.35", "-1,20", "#-3".
#: Sont reconnus aussi le signe suivi d'une espace, "+ 0.35", le signe
#: moins typographique, et une troisième décimale. Un nombre sans signe
#: n'est pas pris pour une évaluation : ce serait confondre "7.5 minutes"
#: avec un score.
RE_EVALUATION = re.compile(
    r"(?<![\w.,])([+\-\u2212\u2013][ \u00a0]?\d+[.,]\d{1,3}|#-?\d+)(?![\d])")

#: Une variante écrite dans un commentaire : "(12... Nd4 13. Qd2 Nxe2)". Ce
#: n'est alors que du texte, que SCID ne permet pas de rejouer.
RE_VARIANTE_TEXTE = re.compile(r"\(\s*(\d+)\s*(\.{1,3})\s*([^()]*)\)")

#: Un coup en notation algébrique, signes d'échec et d'appréciation compris.
RE_SAN = re.compile(
    r"(O-O(?:-O)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?)[+#]?[!?]*$")

#: NAG d'évaluation de la position, selon le camp qu'ils donnent mieux.
NAG_BLANCS_MIEUX = {14, 16, 18, 20}
NAG_NOIRS_MIEUX = {15, 17, 19, 21}

#: NAG attendu par défaut pour chaque nature de coup, d'après le prompt.
NAG_NATURE = {"imprécision": 6, "erreur": 2, "gaffe": 4}

#: Une position FEN dans un texte : six champs, le premier à huit rangées.
RE_FEN = re.compile(
    r"((?:[pnbrqkPNBRQK1-8]{1,8}/){7}[pnbrqkPNBRQK1-8]{1,8}"
    r" [wb] (?:-|[KQkq]{1,4}) (?:-|[a-h][36]) \d+ \d+)")


class ArchiveInutilisable(Exception):
    """L'archive se lit, mais son contenu n'est pas celui d'IAnalyze."""


class Bilan:
    """Recueille les lignes du bilan et compte les échecs."""

    def __init__(self) -> None:
        self.lignes: list[str] = []
        self.echecs = 0
        self.attentions = 0

    def titre(self, texte: str) -> None:
        self.lignes.append("")
        self.lignes.append("=== %s ===" % texte)

    def noter(self, repere: str, texte: str, details=None) -> None:
        if repere == "ECHEC":
            self.echecs += 1
        elif repere == "ATTENTION":
            self.attentions += 1
        self.lignes.append("  %-9s %s" % (repere, texte))
        # Dix détails au plus : au delà, le bilan devient illisible.
        details = list(details or [])
        for d in details[:10]:
            self.lignes.append("            - %s" % d)
        if len(details) > 10:
            self.lignes.append("            - ... et %d de plus"
                               % (len(details) - 10))

    def controle(self, vrai: bool, texte: str, details=None,
                 grave: bool = True) -> None:
        """OK si vrai, sinon ECHEC, ou ATTENTION si grave est faux."""
        if vrai:
            self.noter("OK", texte)
        else:
            self.noter("ECHEC" if grave else "ATTENTION", texte, details)


# ---------------------------------------------------------------------------
# Lecture de l'archive
# ---------------------------------------------------------------------------

def lire_archive(chemin: pathlib.Path) -> dict[str, str]:
    """
    Rend les fichiers utiles de l'archive : partie.pgn, synthese.md et
    stockfish/evaluations.json, depuis un zip ou un dossier décompressé.
    """
    voulus = ("partie.pgn", "synthese.md", "stockfish/evaluations.json")
    trouves: dict[str, str] = {}
    if chemin.is_dir():
        for nom in voulus:
            # Le dossier peut être celui de la collecte ou son parent.
            candidats = [chemin / nom] + sorted(chemin.glob("*/" + nom))
            for c in candidats:
                if c.is_file():
                    trouves[nom] = c.read_text(encoding="utf-8")
                    break
    else:
        with zipfile.ZipFile(chemin) as z:
            for membre in z.namelist():
                for nom in voulus:
                    if membre.endswith("/" + nom) or membre == nom:
                        trouves[nom] = z.read(membre).decode("utf-8")
    manquants = [n for n in voulus if n not in trouves]
    if manquants:
        raise ArchiveInutilisable("archive incomplète, fichier(s) "
                                  "absent(s) : %s" % ", ".join(manquants))
    return trouves


def ligne_principale(partie: chess.pgn.Game) -> list[str]:
    """Coups de la ligne principale, en UCI."""
    return [coup.uci() for coup in partie.mainline_moves()]


# ---------------------------------------------------------------------------
# Contrôles
# ---------------------------------------------------------------------------

def retirer_lignes_vides(texte: str) -> tuple[str, list[int]]:
    """
    Retire les lignes vides du corps de la partie, après les balises.

    Rend le texte ainsi réparé et les numéros des lignes retirées. Les
    lignes vides de fin de fichier ne comptent pas.
    """
    lignes = texte.split("\n")
    debut = 0
    while debut < len(lignes) and (lignes[debut].startswith("[")
                                   or not lignes[debut].strip()):
        debut += 1
    fin = len(lignes)
    while fin > debut and not lignes[fin - 1].strip():
        fin -= 1
    retirees = [n + 1 for n in range(debut, fin) if not lignes[n].strip()]
    corps = [x for x in lignes[debut:fin] if x.strip()]
    return "\n".join(lignes[:debut] + corps) + "\n", retirees


def lire_partie(texte: str) -> chess.pgn.Game | None:
    """
    Lit la première partie du texte, ou rend None.

    Sur certains PGN abîmés, un coup illégal suivi d'une parenthèse
    fermante par exemple, python-chess ne consigne pas l'erreur : il
    lève IndexError. Le fichier est alors tenu pour illisible, ce qui
    donne un ECHEC au bilan et non une trace Python.
    """
    try:
        return chess.pgn.read_game(io.StringIO(texte))
    except (IndexError, ValueError):
        return None


def san_ou_uci(noeud: chess.pgn.ChildNode) -> str:
    """
    Le coup en notation algébrique, ou en UCI s'il n'est pas jouable.

    Après une erreur de lecture, python-chess peut laisser dans l'arbre un
    coup illégal dans sa position : san() s'arrête alors sur une
    assertion.
    """
    try:
        return noeud.san()
    except (AssertionError, ValueError):
        return noeud.move.uci()


def controler_lecture(b: Bilan, brut: bytes) -> tuple[str, chess.pgn.Game]:
    """Encodage, puis lecture par python-chess."""
    b.titre("1. Lecture du PGN")
    try:
        texte = brut.decode("utf-8")
        b.noter("OK", "fichier en UTF-8")
    except UnicodeDecodeError:
        texte = brut.decode("latin-1")
        b.noter("ECHEC", "le fichier n'est pas en UTF-8, lu en latin-1")
    if texte.startswith("\ufeff"):
        texte = texte[1:]
        b.noter("ATTENTION", "marque d'ordre des octets en tête de fichier")
    # Fins de ligne ramenées à LF : un fichier venu de Windows garderait
    # sinon un retour chariot en bout de chaque ligne, compté comme un
    # caractère de plus dans le contrôle des 79 colonnes.
    texte = texte.replace("\r\n", "\n").replace("\r", "\n")
    partie = lire_partie(texte)
    if partie is None:
        b.noter("ECHEC", "aucune partie lisible dans le fichier")
        raise SystemExit(afficher(b, 1))
    # Une ligne vide dans le corps de la partie : la spécification PGN en
    # fait, au format d'export, la fin du corps, et python-chess y arrête
    # sa lecture. Le reste du fichier devient une seconde partie, sans
    # balises. Le défaut est nommé, puis les contrôles continuent sur le
    # fichier réparé, pour mesurer tout de même le travail rendu.
    #
    # Toute ligne vide du corps est relevée, et pas seulement celle qui
    # raccourcit la ligne principale : placée avant une variante ou avant
    # le marqueur de fin, elle cache la suite sans changer le compte des
    # coups, et ce qui la suit ne serait jamais contrôlé.
    repare, retirees = retirer_lignes_vides(texte)
    if retirees:
        relue = lire_partie(repare)
        lus = len(ligne_principale(partie))
        constat = "ligne vide dans le corps de la partie"
        if relue is not None and len(ligne_principale(relue)) > lus:
            constat += (" : python-chess y arrête sa lecture et ne voit "
                        "que %d demi-coup(s) sur %d"
                        % (lus, len(ligne_principale(relue))))
        else:
            constat += (" : python-chess y arrête sa lecture, ce qui la "
                        "suit n'est pas lu")
        b.noter("ECHEC", constat, ["ligne %d" % n for n in retirees])
        if relue is not None:
            b.noter("INFO", "les contrôles suivants portent sur le fichier "
                    "une fois ces lignes retirées")
            texte, partie = repare, relue
    # python-chess n'arrête pas la lecture sur un coup illégal : il le
    # consigne dans errors et abandonne la variante à cet endroit.
    erreurs = [str(e).split(" while parsing")[0] for e in partie.errors]
    b.controle(not erreurs, "aucun coup illégal, variantes comprises "
               "(%d erreur(s) de lecture)" % len(erreurs), erreurs)
    return texte, partie


def controler_partie(b: Bilan, partie: chess.pgn.Game,
                     origine: chess.pgn.Game) -> bool:
    """La ligne principale doit être celle de la partie d'origine."""
    b.titre("2. Ligne principale")
    rendue, attendue = ligne_principale(partie), ligne_principale(origine)
    identique = rendue == attendue
    details = []
    if not identique:
        commun = 0
        for x, y in zip(rendue, attendue):
            if x != y:
                break
            commun += 1
        details.append("identique sur %d demi-coup(s), puis %s au lieu de %s"
                       % (commun,
                          rendue[commun] if commun < len(rendue) else "fin",
                          attendue[commun] if commun < len(attendue)
                          else "fin"))
        details.append("%d demi-coups rendus, %d attendus"
                       % (len(rendue), len(attendue)))
        if partie.errors:
            # Sur un coup illégal, python-chess abandonne la lecture de
            # la suite : la ligne principale peut en sortir tronquée.
            details.append("peut découler d'un coup illégal relevé en 1")
    b.controle(identique, "ligne principale identique à la partie d'origine "
               "(%d demi-coups)" % len(attendue), details)
    return identique


def commentaires(partie: chess.pgn.Game) -> list[tuple[str, str]]:
    """Tous les commentaires du PGN, avec l'endroit où ils se trouvent."""
    trouves = []
    if partie.comment:
        trouves.append(("avant le coup 1", partie.comment))

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
    Lignes où une accolade fermante apparaît hors de tout commentaire.

    Une accolade fermante écrite dans un commentaire le termine trop
    tôt : la fin du commentaire tombe dans le corps de la partie, où
    python-chess l'ignore mot après mot, sans erreur. Ce qui reste d'elle
    est une seconde accolade fermante, que rien n'a ouverte : c'est elle
    que l'on cherche, dans le texte brut.
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
                # Commentaire de fin de ligne.
                break
            elif c == "}":
                trouvees.append("ligne %d : accolade fermante en trop" % n)
    return trouvees


def balises_du_texte(texte: str) -> list[str]:
    """
    Noms des balises dans l'ordre où le fichier les écrit.

    python-chess range toujours les sept balises obligatoires en tête,
    quel que soit l'ordre du fichier, et crée celles qui manquent : son
    dictionnaire ne dit donc rien de ce que le LLM a écrit.
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
                     court: bool = False) -> None:
    """
    Contraintes de format impératives du prompt.

    `court` vaut vrai pour un PGN rendu d'après le prompt court de
    --prompt-seul : seuls restent les contrôles que ce prompt fonde, les
    accolades, les balises recopiées et le marqueur de fin.
    """
    b.titre("3. Format")
    lignes = texte.split("\n")
    if not court:
        longues = ["ligne %d : %d caractères" % (n + 1, len(x))
                   for n, x in enumerate(lignes) if len(x) > LONGUEUR_MAX]
        b.controle(not longues, "aucune ligne de plus de %d caractères"
                   % LONGUEUR_MAX, longues)

    notes = commentaires(partie)
    # Une accolade ouvrante dans un commentaire reste dans son texte ; une
    # fermante le termine trop tôt, et ne se voit que dans le texte brut.
    accolades = [lieu for lieu, t in notes if "{" in t or "}" in t]
    accolades += accolades_orphelines(texte)
    b.controle(not accolades, "aucune accolade dans un commentaire",
               accolades)
    corps = "\n".join(x for x in lignes if not x.startswith("["))
    hors_commentaires = re.sub(r"\{[^}]*\}", " ", corps)
    if not court:
        pourcents = [lieu for lieu, t in notes if "%" in t]
        b.controle(not pourcents, "aucun caractère % dans un commentaire",
                   pourcents)
        cadratins = [lieu for lieu, t in notes if "\u2014" in t]
        b.controle(not cadratins, "aucun tiret cadratin", cadratins)
        virgules = [lieu for lieu, t in notes if ";" in t]
        b.controle(not virgules, "aucun point-virgule dans un commentaire",
                   virgules, grave=False)

        # Notation suffixe (Qxa8?) : cherchée hors des commentaires, où
        # un point d'interrogation est simplement de la ponctuation.
        suffixes = sorted(set(re.findall(
            r"\b(?:[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?"
            r"|O-O(?:-O)?)[+#]?[!?]+", hors_commentaires)))
        b.controle(not suffixes, "pas de notation suffixe, les NAG seuls",
                   suffixes)

    # Balises : les sept obligatoires d'abord, les autres par ordre
    # alphabétique, et leurs valeurs reprises de la partie d'origine.
    noms = balises_du_texte(texte)
    absentes = [n for n in SEPT_BALISES if n not in noms]
    b.controle(tuple(noms[:7]) == SEPT_BALISES,
               "les sept balises obligatoires, dans l'ordre",
               ["ordre rendu : %s" % ", ".join(noms[:7])]
               + ["absente : %s" % n for n in absentes])
    autres = noms[7:]
    if not court:
        b.controle(autres == sorted(autres),
                   "les autres balises par ordre alphabétique",
                   ["ordre rendu : %s" % ", ".join(autres)], grave=False)
    differentes = [
        "%s : \"%s\" au lieu de \"%s\""
        % (n, partie.headers.get(n), origine.headers.get(n))
        for n in SEPT_BALISES
        if partie.headers.get(n) != origine.headers.get(n)]
    b.controle(not differentes, "valeurs des sept balises reprises de la "
               "partie d'origine", differentes)
    if not court:
        b.controle(bool(partie.headers.get("Annotator", "").strip("? ")),
                   "balise Annotator renseignée : \"%s\""
                   % partie.headers.get("Annotator", ""), grave=False)
        compte = partie.headers.get("PlyCount", "")
        b.controle(compte == str(demi_coups),
                   "balise PlyCount : \"%s\", attendu \"%d\""
                   % (compte, demi_coups), grave=False)

    # Marqueur de fin : le dernier mot du fichier, hors commentaires.
    mots = hors_commentaires.split()
    marqueur = mots[-1] if mots else ""
    b.controle(marqueur == partie.headers.get("Result"),
               "marqueur de fin \"%s\" identique à la balise Result \"%s\""
               % (marqueur, partie.headers.get("Result")))


def controler_couverture(b: Bilan, partie: chess.pgn.Game,
                         evaluations: list[dict],
                         court: bool = False) -> None:
    """
    Chaque erreur et chaque gaffe doit être commentée.

    Le prompt court ne demande ni résumé avant le premier coup ni NAG :
    avec `court`, ces deux points ne sont pas contrôlés.
    """
    b.titre("4. Coups commentés")
    if not court:
        resume = partie.comment.strip()
        b.controle(bool(resume), "résumé de la partie avant le coup 1 "
                   "(%d ligne(s), 6 à 10 demandées)"
                   % (resume.count("\n") + 1 if resume else 0))

    noeuds = list(partie.mainline())
    commentes = [n for n in noeuds if n.comment.strip()]
    b.noter("INFO", "%d coup(s) commenté(s) sur %d, %d à %d visés sur une "
            "partie complète" % (len(commentes), len(noeuds),
                                 COMMENTES_MIN, COMMENTES_MAX))
    b.noter("INFO", "%d coup(s) porteur(s) d'un NAG"
            % sum(1 for n in noeuds if n.nags))

    oublies, sans_nag, fautes = [], [], 0
    for e in evaluations:
        if e.get("nature") not in ("erreur", "gaffe"):
            continue
        fautes += 1
        indice = e["demicoup"] - 1
        if indice >= len(noeuds):
            continue
        lieu = "%d%s %s (%s)" % (
            e["numero"], "." if e["trait"] == "Blancs" else "...",
            e["joue"]["san"], e["nature"])
        if not noeuds[indice].comment.strip():
            oublies.append(lieu)
        elif not noeuds[indice].nags:
            sans_nag.append(lieu)
    b.controle(not oublies, "les %d erreur(s) et gaffe(s) de Stockfish sont "
               "toutes commentées (%d oubliée(s))" % (fautes, len(oublies)),
               oublies)
    if fautes > len(oublies) and not court:
        b.controle(not sans_nag, "chaque erreur ou gaffe commentée porte un "
                   "NAG", sans_nag, grave=False)

    # NAG de position contraire au moteur : "léger avantage noir" posé sur
    # un coup après lequel Stockfish donne les Blancs nettement mieux.
    contraires, accords, ecarts = [], 0, []
    for e in evaluations:
        indice = e["demicoup"] - 1
        if indice >= len(noeuds):
            continue
        nags = noeuds[indice].nags
        lieu = "%d%s %s" % (
            e["numero"], "." if e["trait"] == "Blancs" else "...",
            e["joue"]["san"])
        score = e["joue"].get("score") or ""
        signe = 0
        if score.startswith("#"):
            signe = -1 if "-" in score else 1
        elif re.fullmatch(r"[+-]\d+\.\d+", score) and abs(float(score)) >= 0.5:
            signe = 1 if float(score) > 0 else -1
        if (signe < 0 and nags & NAG_BLANCS_MIEUX) or (
                signe > 0 and nags & NAG_NOIRS_MIEUX):
            contraires.append("%s : NAG $%d, moteur %s"
                              % (lieu, min(nags & (NAG_BLANCS_MIEUX
                                                   | NAG_NOIRS_MIEUX)),
                                 score))
        attendu = NAG_NATURE.get(e.get("nature") or "")
        if attendu and nags & set(NAG_NATURE.values()):
            if attendu in nags:
                accords += 1
            else:
                ecarts.append("%s : %s pour le moteur, NAG $%d"
                              % (lieu, e["nature"],
                                 min(nags & set(NAG_NATURE.values()))))
    b.controle(not contraires, "aucun NAG de position contraire à "
               "l'évaluation du moteur", contraires)
    b.noter("INFO", "NAG de qualité : %d conforme(s) à la nature donnée par "
            "le moteur, %d d'un autre avis" % (accords, len(ecarts)), ecarts)


def controler_chiffres(b: Bilan, textes: list[tuple[str, str]],
                       evaluations: list[dict], titre: str) -> None:
    """Une évaluation citée doit exister dans les données du moteur."""
    b.titre(titre)
    connues = set()
    for e in evaluations:
        for coup in [e["joue"]] + e["meilleurs"]:
            score = coup.get("score") or ""
            connues.add(score)
            # Un LLM arrondit volontiers à une décimale : "+0.35" cité
            # "+0.4" ou "+0.3" reste fidèle au dossier. Le calcul se fait
            # en décimal : en flottant, round(0.35, 1) rend 0.3.
            m = re.fullmatch(r"([+-])(\d+\.\d\d)", score)
            if m:
                valeur = decimal.Decimal(m.group(2))
                for mode in (decimal.ROUND_HALF_UP, decimal.ROUND_DOWN):
                    connues.add("%s%s" % (m.group(1), valeur.quantize(
                        decimal.Decimal("0.1"), rounding=mode)))
    citees, inconnues = 0, []
    for lieu, texte in textes:
        for brut in RE_EVALUATION.findall(texte):
            citees += 1
            # Même écriture que le dossier avant de comparer : signe
            # ASCII collé au nombre, point décimal.
            lu = re.sub(r"[ \u00a0]", "", brut.replace(",", "."))
            lu = lu.replace("\u2212", "-").replace("\u2013", "-")
            if lu not in connues:
                inconnues.append("%s : %s" % (lieu, brut))
    b.noter("INFO", "%d évaluation(s) citée(s)" % citees)
    b.controle(not inconnues, "toutes se retrouvent dans les données du "
               "moteur (%d introuvable(s))" % len(inconnues), inconnues)


def lignes_du_moteur(evaluations: list[dict]) -> dict[int, list[list[str]]]:
    """Pour chaque demi-coup, les variantes principales du moteur, en UCI."""
    lignes: dict[int, list[list[str]]] = {}
    for e in evaluations:
        lignes[e["demicoup"]] = [
            c["pv_uci"] for c in [e["joue"]] + e["meilleurs"] if c["pv_uci"]]
    return lignes


def controler_variantes_en_texte(b: Bilan, partie: chess.pgn.Game,
                                 evaluations: list[dict],
                                 jouables: int) -> None:
    """
    Variantes écrites à l'intérieur d'un commentaire.

    Entre accolades, une suite de coups entre parenthèses n'est que du
    texte : SCID ne la rejoue pas, et rien n'en garantit la légalité. Le
    script la rejoue donc lui-même, depuis la position que son numéro de
    coup désigne.
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
                # Une parenthèse de prose, "(15 à 20 coups)" par exemple.
                continue
            trouvees += 1
            numero = int(m.group(1))
            trait = chess.BLACK if len(m.group(2)) > 1 else chess.WHITE
            texte = "(%s%s %s)" % (m.group(1), m.group(2), " ".join(mots))
            # La variante remplace le coup joué, ou le prolonge.
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
                illegales.append("%s : %s est illégal" % (texte, fautif))
                continue
            legales += 1
            if len(joues) > VARIANTE_MAX:
                longues.append("%s : %d demi-coups" % (texte, len(joues)))
            if any(pv[:2] == joues[:2] for pv in moteur):
                appuyees += 1
    if not trouvees:
        return
    b.controle(False, "%d variante(s) écrite(s) à l'intérieur d'un "
               "commentaire : ce n'est que du texte, SCID ne les rejoue pas"
               % trouvees if jouables else
               "aucune variante jouable : les %d variantes sont écrites à "
               "l'intérieur des commentaires, où elles ne sont que du texte"
               % trouvees, grave=not jouables)
    b.controle(not illegales, "rejouées par le script, ces variantes sont "
               "toutes légales (%d illégale(s))" % len(illegales), illegales)
    if perdues:
        b.noter("ATTENTION", "%d variante(s) dont le numéro de coup ne "
                "correspond à aucune position voisine" % len(perdues),
                perdues)
    if longues:
        b.noter("ATTENTION", "variante(s) de plus de %d demi-coups"
                % VARIANTE_MAX, longues)
    b.noter("INFO", "%d légale(s), dont %d partent d'une ligne du moteur"
            % (legales, appuyees))


def controler_variantes(b: Bilan, partie: chess.pgn.Game,
                        evaluations: list[dict]) -> None:
    """Nombre et longueur des variantes, appui sur une ligne du moteur."""
    b.titre("6. Variantes")
    lignes_moteur = lignes_du_moteur(evaluations)

    variantes = []      # (lieu, longueur, appuyée sur le moteur ?)
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
            # Appuyée : ses premiers coups, deux au plus, sont ceux d'une
            # ligne que le moteur donne pour ce demi-coup.
            debut = coups[:2]
            appuyee = any(pv[:len(debut)] == debut
                          for pv in lignes_moteur.get(indice + 1, []))
            variantes.append((lieu, len(coups), appuyee))

    b.noter("INFO", "%d variante(s) jouable(s) sur la ligne principale"
            % len(variantes))
    controler_variantes_en_texte(b, partie, evaluations, len(variantes))
    if not variantes:
        return
    longues = ["%s : %d demi-coups" % (lieu, n)
               for lieu, n, _ in variantes if n > VARIANTE_MAX]
    b.controle(not longues, "aucune variante de plus de %d demi-coups"
               % VARIANTE_MAX, longues, grave=False)
    libres = [lieu for lieu, _, appuyee in variantes if not appuyee]
    b.noter("INFO", "%d variante(s) partent d'une ligne du moteur, %d sont "
            "du cru du LLM" % (len(variantes) - len(libres), len(libres)),
            libres)


def controler_synthese(b: Bilan, texte: str, evaluations: list[dict],
                       synthese_archive: str,
                       origine: chess.pgn.Game) -> None:
    """FEN citées dans la synthèse finale du LLM, et tiret cadratin."""
    b.titre("7. Conversation : positions citées, langue")
    # Une FEN du dossier se reconnaît à ses quatre premiers champs : les
    # compteurs de coups n'identifient pas la position.

    def clef(fen: str) -> str:
        return " ".join(fen.split()[:4])

    connues = {clef(e["fen"]) for e in evaluations}
    # Toutes les positions de la partie, la dernière comprise, que les
    # évaluations ne portent pas : elles donnent la position d'avant
    # chaque coup.
    plateau = origine.board()
    connues.add(clef(plateau.fen()))
    for coup in origine.mainline_moves():
        plateau.push(coup)
        connues.add(clef(plateau.fen()))
    connues |= {clef(f) for f in RE_FEN.findall(synthese_archive)}
    citees = RE_FEN.findall(texte)
    b.controle("\u2014" not in texte, "aucun tiret cadratin dans la "
               "conversation (%d relevé(s))" % texte.count("\u2014"))
    b.controle(len(citees) >= 2, "%d FEN citée(s), deux demandées"
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
        elif clef(fen) not in connues:
            etrangeres.append(fen)
    b.controle(not invalides, "toutes les FEN sont des positions valides",
               invalides)
    b.controle(not etrangeres, "toutes viennent d'une position de la partie",
               etrangeres)


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------

def afficher(b: Bilan, code: int) -> int:
    """Écrit le bilan et rend le code de retour."""
    print("\n".join(b.lignes))
    print("")
    print("=== Bilan ===")
    print("  échecs     : %d" % b.echecs)
    print("  attentions : %d" % b.attentions)
    return code


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        description="Contrôle le PGN annoté rendu par un LLM à partir "
                    "d'une archive d'IAnalyze.")
    p.add_argument("archive", help="zip de ianalyze.py, ou son "
                                   "dossier décompressé")
    p.add_argument("pgn", help="PGN annoté rendu par le LLM, ou - s'il "
                               "n'en a rendu aucun")
    p.add_argument("--synthese", metavar="FICHIER",
                   help="synthèse finale du LLM, copiée dans un fichier "
                        "texte")
    p.add_argument("--nom", default="", help="nom du modèle essayé")
    p.add_argument("--prompt-seul", action="store_true",
                   help="le PGN répond au prompt court de ianalyze.py "
                        "--prompt-seul : les contrôles que ce prompt ne "
                        "fonde pas sont sautés")
    options = p.parse_args(argv)

    try:
        fichiers = lire_archive(pathlib.Path(options.archive))
        brut = (None if options.pgn == "-"
                else pathlib.Path(options.pgn).read_bytes())
        synthese_llm = None
        if options.synthese:
            synthese_llm = pathlib.Path(options.synthese).read_text(
                encoding="utf-8", errors="replace")
        origine = lire_partie(fichiers["partie.pgn"])
        evaluations = json.loads(fichiers["stockfish/evaluations.json"])
        if origine is None or not ligne_principale(origine):
            raise ArchiveInutilisable("partie.pgn de l'archive ne "
                                      "contient aucune partie")
        if not (isinstance(evaluations, list) and all(
                isinstance(e, dict) and isinstance(e.get("joue"), dict)
                and isinstance(e.get("meilleurs"), list)
                and "demicoup" in e for e in evaluations)):
            raise ArchiveInutilisable("stockfish/evaluations.json n'a pas "
                                      "la forme écrite par IAnalyze")
    except (OSError, zipfile.BadZipFile, zlib.error, ValueError,
            ArchiveInutilisable) as e:
        # ValueError couvre un fichier qui n'est pas en UTF-8 et un JSON
        # invalide. Dans tous ces cas aucun contrôle n'a pu commencer :
        # le code 2 le distingue d'un bilan avec des échecs.
        print("Lecture impossible : %s" % e, file=sys.stderr)
        return 2

    b = Bilan()
    b.lignes.append("Contrôle d'une analyse rendue par un LLM")
    if options.nom:
        b.lignes.append("  modèle  : %s" % options.nom)
    b.lignes.append("  archive : %s" % pathlib.Path(options.archive).name)
    b.lignes.append("  PGN     : %s" % pathlib.Path(options.pgn).name)
    if options.prompt_seul:
        b.lignes.append("  prompt  : court (--prompt-seul), contrôles "
                        "réduits à ce qu'il demande")

    if brut is None:
        # Le LLM n'a rendu aucun fichier, ni aucun PGN dans la conversation.
        b.titre("1. Lecture du PGN")
        b.noter("ECHEC", "aucun PGN rendu : les contrôles 2 à 6 sont sans "
                "objet")
        if synthese_llm is not None:
            controler_synthese(b, synthese_llm, evaluations,
                               fichiers["synthese.md"], origine)
            controler_chiffres(b, [("conversation", synthese_llm)],
                               evaluations,
                               "8. Évaluations citées dans la conversation")
        return afficher(b, 1)

    texte, partie = controler_lecture(b, brut)
    identique = controler_partie(b, partie, origine)
    controler_format(b, texte, partie, origine,
                     len(ligne_principale(origine)), options.prompt_seul)
    if identique:
        controler_couverture(b, partie, evaluations, options.prompt_seul)
    else:
        # Sans la même ligne principale, les demi-coups ne se
        # correspondent plus : ces contrôles n'auraient aucun sens.
        b.titre("4. Coups commentés")
        b.noter("ATTENTION", "non contrôlé, la ligne principale diffère")
    controler_chiffres(b, commentaires(partie), evaluations,
                       "5. Évaluations citées dans le PGN")
    if identique:
        controler_variantes(b, partie, evaluations)
    if synthese_llm is not None:
        controler_synthese(b, synthese_llm, evaluations,
                           fichiers["synthese.md"], origine)
        controler_chiffres(b, [("conversation", synthese_llm)],
                           evaluations,
                           "8. Évaluations citées dans la conversation")
    return afficher(b, 1 if b.echecs else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
