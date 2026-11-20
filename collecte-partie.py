#!/usr/bin/env python3
"""
Collecte du matériel d'analyse d'une partie d'échecs.

Ce programme ne produit aucune analyse. Il rassemble et met en forme :

  1. le PGN de la partie, lu depuis un fichier local ou téléchargé
     depuis Lichess ;
  2. les statistiques de l'explorateur Lichess, position par position,
     afin de déterminer où la partie quitte la théorie : base de
     l'ensemble des joueurs Lichess par défaut, ou base maîtres avec
     --base maitres. Un coup rare qui reste dans une ligne du catalogue
     des ouvertures nommées, gardé en local, ne compte pas comme une
     sortie ;
  3. l'évaluation Stockfish de la partie en multipv, calculée en local
     pour épargner ce travail à l'analyste. Le moteur est obligatoire.

Avant la collecte, sur un terminal interactif, le script demande votre
camp si les en-têtes ne le donnent pas, puis vos réponses aux questions
de démarrage du projet d'analyse, rangées dans contexte.md et reprises en
tête de la synthèse.

Votre pseudo, votre cadence habituelle et votre niveau ne sont pas dans
le code : ils vous sont demandés une seule fois, au premier lancement sur
un terminal, puis gardés dans un fichier de réglages que vous pouvez
modifier à la main.

À côté de l'archive, le script écrit le prompt d'analyse de la partie,
tiré du modèle prompt-modele.txt : vous le collez dans la conversation,
l'archive en pièce jointe.

Le résultat est une archive zip contenant les données brutes ainsi qu'un
fichier de synthèse unique, destiné à être joint à une conversation
d'annotation. Le dossier de travail est supprimé une fois l'archive
vérifiée, sauf demande contraire.

Lancez-le avec --help pour la liste des options et des exemples
d'utilisation.
"""

from __future__ import annotations

import argparse
import codecs
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
# Amorçage de l'environnement virtuel
#
# Le module python-chess n'est pas empaqueté par Debian. Vous devez donc
# l'installer dans un environnement virtuel dédié plutôt que dans
# l'environnement Python du système. Ce bloc gère trois cas :
#
#   - le module est disponible, on continue normalement ;
#   - il ne l'est pas mais l'environnement virtuel existe, on se relance
#     automatiquement avec l'interpréteur de cet environnement ;
#   - il ne l'est pas et l'environnement n'existe pas, on vous indique la
#     marche à suivre, ou on le crée si vous avez passé --installer-venv.
# ===========================================================================

#: Vrai sous macOS. Les commandes d'installation proposées dans les
#: messages et l'emplacement du moteur en dépendent.
EST_MACOS = sys.platform == "darwin"

#: Répertoire des données du script, dans le répertoire personnel sous
#: Debian comme sous macOS : l'environnement virtuel et le catalogue y
#: vont, et vous n'avez besoin d'aucun droit root pour les installer.
#: Jusqu'à la version 3.8.0, Debian les rangeait dans /opt/venv/lichess
#: et dans /usr/local/share.
DONNEES = "~/.local/share/IAnalyze"

#: Commandes d'installation des prérequis, reprises dans les messages et
#: dans l'aide. Sous macOS, le Python de Homebrew fournit déjà le module
#: venv : il n'existe pas de paquet séparé à installer.
if EST_MACOS:
    CMD_PAQUET_VENV = "brew install python"
    CMD_PAQUET_STOCKFISH = "brew install stockfish"
else:
    CMD_PAQUET_VENV = "apt install python3-venv"
    CMD_PAQUET_STOCKFISH = "apt install stockfish"

#: Emplacement par défaut de l'environnement virtuel dédié.
VENV_DEFAUT = DONNEES + "/venv"

#: Variable d'environnement servant de garde-fou contre une relance en
#: boucle si l'environnement virtuel existe mais reste incomplet.
MARQUEUR_RELANCE = "COLLECTE_PARTIE_DEJA_RELANCE"

#: Jeton en cours d'utilisation, conservé uniquement pour que le gestionnaire
#: d'erreurs de dernier recours puisse l'expurger d'un message inattendu.
JETON_COURANT: str | None = None

#: Avec --debug, les erreurs inattendues remontent avec leur trace complète.
DEBUG = False

try:
    import chess
    import chess.engine
    import chess.pgn
    CHESS_DISPONIBLE = True
except ImportError:
    CHESS_DISPONIBLE = False

#: Sur une partie qui contient un coup nul, python-chess écrit à chaque
#: position suivante "Not transmitting history with null moves to UCI
#: engine" : il prévient qu'il donne au moteur la position seule, sans
#: l'historique des coups. Les évaluations n'en dépendent pas, et le coup
#: nul est déjà signalé dans le journal et dans la synthèse : ce message,
#: en anglais et répété, est écarté. Les autres avis de la bibliothèque
#: continuent de s'afficher.
logging.getLogger("chess.engine").addFilter(
    lambda avis: "null moves" not in avis.getMessage())


def python_du_venv(venv: str) -> pathlib.Path:
    """Renvoie le chemin de l'interpréteur d'un environnement virtuel."""
    return pathlib.Path(os.path.expanduser(venv)) / "bin" / "python3"


def venv_operationnel(venv: str) -> bool:
    """
    Indique si l'environnement virtuel existe et fournit bien python-chess.

    La vérification est faite en lançant réellement l'interpréteur de
    l'environnement, et non en supposant qu'un répertoire présent est un
    environnement fonctionnel.
    """
    interpreteur = python_du_venv(venv)
    if not interpreteur.is_file():
        return False
    try:
        subprocess.run([str(interpreteur), "-c", "import chess"],
                       check=True, capture_output=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False
    return True


def installer_venv(venv: str) -> None:
    """
    Crée l'environnement virtuel s'il manque, puis y installe python-chess.

    L'opération est idempotente : vous pouvez la relancer sans risque sur
    un environnement déjà en place, elle se contentera alors de mettre le
    module à jour.
    """
    racine = pathlib.Path(os.path.expanduser(venv))
    interpreteur = python_du_venv(venv)

    if not interpreteur.is_file():
        journal("Création de l'environnement virtuel : %s" % racine)
        try:
            racine.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, "-m", "venv", str(racine)],
                           check=True)
        except OSError as err:
            raise SystemExit("Impossible de créer %s : %s" % (racine, err)) \
                from err
        except subprocess.CalledProcessError as err:
            # Le texte affiché sous Debian est celui d'origine ; sous macOS
            # il n'existe pas de paquet python3-venv à suggérer.
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
    Se relance avec l'interpréteur de l'environnement virtuel.

    Cette fonction ne rend jamais la main en cas de succès : le processus
    courant est remplacé. Si l'environnement est absent ou incomplet, elle
    interrompt le programme avec les instructions à suivre.
    """
    interpreteur = python_du_venv(venv)
    script = os.path.abspath(__file__)

    if os.environ.get(MARQUEUR_RELANCE) == "1":
        raise SystemExit(
            "L'environnement %s ne fournit pas le module chess.\n"
            "Réparez-le avec : %s --installer-venv --venv %s"
            % (venv, script, venv))

    if interpreteur.is_file():
        journal("Module chess absent, relance via %s" % interpreteur)
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
# Constantes
# ===========================================================================

#: Hôte de l'explorateur. L'ancien nom explorer.lichess.ovh ne répond plus.
EXPLORER_URL = "https://explorer.lichess.org/masters"

#: Base de l'ensemble des joueurs Lichess, parties classées uniquement. Même
#: hôte et même exigence de jeton que la base maîtres. C'est cette base
#: qu'affiche la page https://lichess.org/opening.
EXPLORER_LICHESS_URL = "https://explorer.lichess.org/lichess"

#: Bases interrogeables avec --base : endpoint, et libellé repris dans la
#: synthèse. Le libellé de la base maîtres redonne à l'identique les titres
#: des synthèses produites avant l'ajout de cette option.
BASES_EXPLORATEUR = {
    "maitres": {"url": EXPLORER_URL, "libelle": "maîtres"},
    "lichess": {"url": EXPLORER_LICHESS_URL,
                "libelle": "Lichess (tous joueurs)"},
}

#: Cadences admises par l'endpoint /lichess, schéma Speed de l'API.
CADENCES_LICHESS = ("ultraBullet", "bullet", "blitz", "rapid", "classical",
                    "correspondence")

#: Tranches de classement admises par l'endpoint /lichess. Chacune court de
#: sa valeur jusqu'à la suivante : 0 couvre 0 à 999 (tranche affichée "400"
#: sur le site), 2500 couvre tout ce qui dépasse. Le serveur range chaque
#: partie selon la moyenne des classements de ses deux joueurs.
CLASSEMENTS_LICHESS = ("0", "1000", "1200", "1400", "1600", "1800", "2000",
                       "2200", "2500")

#: Filtres par défaut de la base Lichess, repris de la configuration par
#: défaut de https://lichess.org/opening (OpeningConfig.default et
#: OpeningQuery.firstMonth dans le source de lila) : toutes les cadences
#: sauf l'UltraBullet, toutes les tranches sauf la plus basse, et seulement
#: les parties jouées depuis janvier 2017. Vous retrouvez ainsi les mêmes
#: pourcentages que sur cette page.
CADENCES_DEFAUT = "bullet,blitz,rapid,classical,correspondence"
CLASSEMENTS_DEFAUT = "1000,1200,1400,1600,1800,2000,2200,2500"
DEPUIS_LICHESS = "2017-01"

#: Catalogue des ouvertures nommées de Lichess, dans le domaine public
#: (CC0). Ce sont les cinq fichiers que charge aussi le serveur de
#: l'explorateur pour nommer les positions.
CATALOGUE_SOURCE = ("https://raw.githubusercontent.com/lichess-org/"
                    "chess-openings/master/{partie}.tsv")
CATALOGUE_PARTIES = ("a", "b", "c", "d", "e")

#: Répertoire par défaut du catalogue local, et nom de son index.
CATALOGUE_DEFAUT = DONNEES
CATALOGUE_INDEX = "catalogue.tsv"

#: Version du format de l'index, vérifiée au chargement.
CATALOGUE_FORMAT = "1"

#: Numéro de coup dans une ligne du catalogue, "1." ou "12." par exemple.
RE_NUMERO_COUP = re.compile(r"\d+\.+")

#: Fichier de réglages de l'utilisateur, au même endroit sous Debian et
#: sous macOS. Il porte ce qui dépend de la personne et non de la partie :
#: ses pseudos et sa cadence habituelle. Rien de personnel ne figure donc
#: dans ce script, que chacun peut reprendre tel quel.
#: Les répertoires portent le nom du projet, IAnalyze, et non celui du
#: script : il en va de même du catalogue et des données sous macOS.
REGLAGES_DEFAUT = "~/.config/IAnalyze/reglages.ini"

#: Section du fichier de réglages qui décrit le joueur.
REGLAGES_SECTION = "joueur"

#: Clefs connues de cette section, avec les lignes de commentaire écrites
#: au-dessus de chacune dans le fichier. Les pseudos sont cherchés, sans
#: tenir compte de la casse, dans les balises White et Black pour déduire
#: le camp du joueur ; le premier sert à compléter une balise vide.
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

#: Bornes d'un niveau exprimé en points Elo.
NIVEAU_MIN, NIVEAU_MAX = 100, 3500

#: Modèle du prompt d'analyse, cherché à côté du script, et suffixe du
#: prompt écrit à côté de l'archive.
PROMPT_MODELE = "prompt-modele.txt"
PROMPT_SUFFIXE = ".prompt.txt"

#: Repères du modèle. Une ligne commençant par PROMPT_DIRECTIVE est une
#: directive, jamais recopiée ; une valeur s'écrit entre doubles accolades.
PROMPT_DIRECTIVE = "#!"
RE_VALEUR_MODELE = re.compile(r"\{\{([A-Za-z_]+)\}\}")

#: Conditions que connaît une directive "si", et valeurs remplaçables. Un
#: nom absent de ces listes arrête le script avant la collecte.
PROMPT_CONDITIONS = ("STOCKFISH", "EXPLORATEUR", "BASE_LICHESS",
                     "BASE_MAITRES", "REPONSES", "CONSIGNES_LIBRES",
                     "CAMP_CONNU", "PSEUDO_CONNU", "NIVEAU_DECLARE")
PROMPT_VALEURS = ("VERSION", "DEPOT", "ARCHIVE", "PSEUDOS", "CAMP", "NIVEAU",
                  "CADENCE", "ANNOTATEUR", "BASE", "SEUIL_IMPRECISION",
                  "SEUIL_ERREUR", "SEUIL_GAFFE", "PROFONDEUR", "MULTIPV")

#: Valeur de la balise Annotator quand les réglages n'en donnent pas : le
#: script ignore quel modèle rédigera l'analyse.
ANNOTATEUR_DEFAUT = ("votre nom de modèle, suivi de son éditeur entre "
                     "parenthèses")

#: Libellé d'une cadence inconnue, quand ni la balise TimeControl ni les
#: réglages ne la donnent.
CADENCE_DEFAUT = "non précisée"

#: Catégories de cadence de Lichess, de la plus lente à la plus rapide,
#: chacune avec la durée estimée, en secondes, à partir de laquelle elle
#: s'applique. La durée estimée d'une partie vaut le temps initial plus
#: COUPS_ESTIMES fois l'incrément. Bornes et formule reprises du source de
#: Lichess (scalachess : Speed.scala et Clock.scala). Au delà de six
#: heures, Lichess parle de correspondance ; une cadence saisie comme du
#: temps réel reste ici "classique".
CATEGORIES_CADENCE = ((1500, "classique"), (480, "rapide"), (180, "blitz"),
                      (30, "bullet"), (0, "ultrabullet"))
COUPS_ESTIMES = 40

#: Formes de cadence admises dans le fichier de réglages : "15+10", minutes
#: par joueur puis incrément en secondes, à la manière de Lichess, et
#: "14 jours" pour la correspondance. Les autres valeurs de
#: CADENCES_INCONNUES désignent une cadence inconnue.
RE_CADENCE_REELLE = re.compile(r"([0-9]{1,5})\s*\+\s*([0-9]{1,5})")
RE_CADENCE_JOURS = re.compile(r"([0-9]{1,4})\s*(?:j|jour|jours)")

#: Correspondance par période : "10 coups en 50 jours". C'est la cadence
#: dite standard de l'ICCF, le temps économisé sur une période étant
#: reporté sur la suivante.
RE_CADENCE_PERIODE = re.compile(
    r"([0-9]{1,3})\s*coups?\s*en\s*([0-9]{1,4})\s*(?:j|jour|jours)")

#: Correspondance à capital de temps : "5 jours + 36 heures", suivi au
#: besoin de ", plafond 20 jours" et de ", réserve 50 jours". Un capital
#: est donné au départ, un incrément s'y ajoute à chaque coup, un plafond
#: peut le borner, et une réserve peut exister à côté, où le joueur puise
#: à sa guise. chess-mail.com en est la forme simple (5 jours, 36 heures
#: par coup, plafond de 20 jours), le Triple Block de l'ICCF la forme
#: complète (50 jours, un incrément en jours, plafond de 50 jours, réserve
#: de 50 ou 75 jours). L'incrément porte son unité, heures ou jours : un
#: jour et demi ne s'écrit pas en jours entiers.
RE_CADENCE_CAPITAL = re.compile(
    r"([0-9]{1,4})\s*(?:j|jour|jours)\s*\+\s*([0-9]{1,4})\s*"
    r"(h|heure|heures|j|jour|jours)"
    r"(?:\s*,?\s*plafond\s*([0-9]{1,4})\s*(?:j|jour|jours))?"
    r"(?:\s*,?\s*r[ée]serve\s*([0-9]{1,4})\s*(?:j|jour|jours))?")

#: Incrément saisi avec son unité : "36h" ou "3j".
RE_INCREMENT = re.compile(r"([0-9]{1,4})\s*(h|heure|heures|j|jour|jours)")
CADENCES_INCONNUES = ("", "?", "inconnue", "non précisée")

#: Balise TimeControl du standard PGN, dans ses deux formes les plus
#: courantes : "600+5", secondes puis incrément, et "300", temps seul.
RE_TIMECONTROL = re.compile(r"([0-9]{1,6})(?:\+([0-9]{1,5}))?")

#: Cadence inconnue, valeur de repli.
CADENCE_INCONNUE = {"type": "inconnue"}

#: Questions de démarrage du projet d'analyse, avec le défaut que retient
#: une réponse vide : libellé dans contexte.md, question, défaut.
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

#: Nature d'un coup selon son écart au premier choix du moteur, en
#: centipions du point de vue du joueur au trait. 100 est le seuil de
#: commentaire obligatoire des instructions du projet.
SEUIL_IMPRECISION = 50
SEUIL_ERREUR = 100
SEUIL_GAFFE = 300

#: Écart, en centipions, à partir duquel il ne mesure plus rien : l'un des
#: deux scores est un mat, que valeur_pour_trait ramène à une valeur
#: bornée voisine de 100000 pour pouvoir classer les coups. Ce nombre est
#: une convention de calcul, non une évaluation du moteur : il n'est pas
#: affiché.
SEUIL_ECART_MAT = 10000

#: Erreurs et gaffes reprises au plus, par camp, dans le palmarès.
PALMARES_MAX = 5

#: Repère d'entrée en finale : matériel hors pions et rois des deux camps
#: réunis, au plus SEUIL_FINALE avec les valeurs de VALEUR_PIECES. Les
#: lettres sont celles de la FEN, en minuscules.
SEUIL_FINALE = 26
VALEUR_PIECES = {"n": 3, "b": 3, "r": 5, "q": 9}

#: Export PGN public, ne demande aucune authentification.
EXPORT_URL = "https://lichess.org/game/export/{id}"

#: Emplacement du binaire Stockfish sous Debian : il n'est pas dans le PATH.
#: Sous macOS, Homebrew le place dans le PATH : on l'y cherche, avec repli
#: sur l'emplacement de Homebrew pour Apple Silicon s'il est introuvable.
STOCKFISH_DEFAUT = ((shutil.which("stockfish")
                     or "/opt/homebrew/bin/stockfish") if EST_MACOS
                    else "/usr/games/stockfish")

#: Indication d'installation du moteur, reprise dans le message d'erreur.
AIDE_STOCKFISH = (CMD_PAQUET_STOCKFISH if EST_MACOS
                  else CMD_PAQUET_STOCKFISH + ", dans /usr/games")

#: Fichier contenant le jeton personnel, en mode 600, et rien d'autre.
JETON_DEFAUT = "~/.lichess_token"

#: Identifiant tel qu'on le saisit : 8 caractères pour la partie, 12 pour
#: la vue d'un joueur. Exiger la longueur exacte évite de prendre un nom
#: de fichier inexistant, "inexistant.pgn" par exemple, pour l'identifiant
#: "inexista", et de l'envoyer à Lichess.
RE_ID_SOURCE = re.compile(r"[A-Za-z0-9]{8}(?:[A-Za-z0-9]{4})?")

#: Version du script, selon le versionnage sémantique. Elle est reprise
#: dans l'en-tête d'agent : c'est le seul endroit à modifier.
VERSION = "4.0.0"

#: Adresse du dépôt du projet, citée en tête du prompt d'analyse pour
#: que l'analyste, ou toute personne à qui le prompt est transmis,
#: sache d'où viennent le prompt et l'archive.
DEPOT = "https://github.com/deuza/IAnalyze"

#: En-tête d'agent, par politesse envers l'API.
UA = "collecte-partie/%s (analyse personnelle)" % VERSION


# ===========================================================================
# Utilitaires généraux
# ===========================================================================

#: Caractères de contrôle retirés d'un texte avant affichage : jeu C0 hors
#: tabulation et saut de ligne, DEL, puis jeu C1. Une séquence
#: d'échappement venue d'un PGN ou d'un nom de fichier ne doit jamais
#: atteindre votre terminal.
RE_CONTROLES = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


#: Séparateurs qu'une valeur tenant sur une ligne ne doit pas contenir :
#: tabulations, fins de ligne, séparateurs de ligne et de paragraphe
#: Unicode. Ils deviennent une espace.
RE_BLANCS_VALEUR = re.compile(r"[\t\n\x0b\x0c\r\x85\u2028\u2029]")

#: Substituts isolés, traces d'octets que l'encodage attendu n'a pas su
#: décoder (nom de fichier, saisie au clavier).
RE_SUBSTITUTS = re.compile(r"[\ud800-\udfff]")


def nettoyer_valeur(texte: str) -> str:
    """
    Nettoie une valeur courte avant de l'écrire ou de l'afficher : nom de
    joueur, balise Event ou Site, réponse à une question.

    Les séparateurs deviennent une espace, les substituts isolés U+FFFD,
    et les autres caractères de contrôle ainsi que la marque d'ordre des
    octets sont retirés. Une valeur saine ressort inchangée.
    """
    texte = RE_BLANCS_VALEUR.sub(" ", texte)
    texte = RE_SUBSTITUTS.sub("\ufffd", texte)
    return RE_CONTROLES.sub("", texte).replace("\ufeff", "")


def configurer_console() -> None:
    """
    Rend la sortie standard et la sortie d'erreur tolérantes à l'encodage.

    Un caractère que l'encodage du terminal ne sait pas représenter est
    remplacé par "?" au lieu de lever UnicodeEncodeError : c'est le cas
    des accents des messages avec PYTHONIOENCODING=ascii, ou sous une
    locale C quand le mode UTF-8 de Python est désactivé (PYTHONUTF8=0).
    L'encodage lui-même n'est pas modifié, seul le traitement des erreurs
    l'est.

    L'entrée standard passe en "surrogateescape" : un octet que l'encodage
    du terminal ne sait pas décoder, un "é" saisi en latin-1 sur une
    console UTF-8 par exemple, est gardé de côté au lieu de lever
    UnicodeDecodeError, et demander() le redécode ensuite.
    """
    reconfigurer = getattr(sys.stdin, "reconfigure", None)
    if reconfigurer is not None:
        with contextlib.suppress(ValueError, OSError):
            reconfigurer(errors="surrogateescape")
    for flux in (sys.stdout, sys.stderr):
        # Un flux fermé (None) ou remplacé par un objet sans reconfigure()
        # est laissé tel quel : mieux vaut un affichage dégradé qu'un
        # échec avant d'avoir commencé.
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is None:
            continue
        with contextlib.suppress(ValueError, OSError):
            reconfigurer(errors="replace")


def journal(message: str) -> None:
    """
    Écrit une ligne d'avancement horodatée sur la sortie d'erreur.

    Les caractères de contrôle du message sont retirés au passage.
    """
    message = RE_CONTROLES.sub("", message)
    heure = datetime.datetime.now().strftime("%H:%M:%S")
    sys.stderr.write("[%s] %s\n" % (heure, message))
    sys.stderr.flush()


def expurger(texte: str, jeton: str | None) -> str:
    """
    Retire toute occurrence du jeton d'une chaîne avant affichage.

    Aucun message ni aucune exception n'est censé contenir le jeton, mais
    vous ne voulez prendre aucun risque sur une trace d'exécution qui
    finira peut-être dans un rapport de bogue.
    """
    if jeton:
        texte = texte.replace(jeton, "<JETON-EXPURGE>")
    return texte


def entier(valeur) -> int:
    """
    Convertit prudemment une valeur venue d'un JSON externe en entier.

    Une valeur absente, nulle ou d'un type inattendu vaut zéro : on préfère
    un chiffre manquant à une interruption sur un détail de schéma. Il en
    va de même d'un nombre infini : json.loads lit "1e999" comme l'infini,
    que int() refuse par une OverflowError.
    """
    try:
        return int(valeur)
    except (TypeError, ValueError, OverflowError):
        return 0


#: Marques d'ordre des octets reconnues en tête de fichier. Celles de
#: l'UTF-32 passent d'abord : la marque UTF-32 petit-boutiste commence par
#: celle de l'UTF-16 petit-boutiste.
BOMS_LARGES = (
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
)

#: Octets examinés pour reconnaître un UTF-16 sans marque d'ordre.
ECHANTILLON_UTF16 = 4096

#: Octets invalides tolérés, par caractère non ASCII correctement codé,
#: pour qu'un texte soit encore tenu pour de l'UTF-8 abîmé.
UTF8_TOLERANCE = 4


def utf16_sans_bom(brut: bytes) -> str | None:
    """
    Reconnaît un texte UTF-16 dépourvu de marque d'ordre des octets.

    Un texte surtout ASCII codé en UTF-16 porte un octet nul sur deux :
    aux rangs impairs en petit-boutiste, aux rangs pairs en gros-boutiste.
    Renvoie le nom du codec, ou None si le motif n'apparaît pas.
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
    Décode le contenu d'un fichier texte sans jamais lever d'exception.

    Ordre des essais : marque d'ordre des octets (UTF-8, UTF-16, UTF-32),
    UTF-16 sans marque, UTF-8 strict, puis repli sur cp1252 et enfin sur
    latin-1, qui accepte n'importe quel octet. Un texte manifestement en
    UTF-8 mais abîmé par quelques octets invalides reste décodé en UTF-8,
    ces octets devenant U+FFFD : le passer en cp1252 abîmerait tous ses
    accents pour en sauver quelques-uns. Le critère : au moins un
    caractère non ASCII correctement codé, et au plus UTF8_TOLERANCE
    octets invalides pour chacun d'eux. Un texte latin-1 n'y satisfait
    pas, ses lettres accentuées étant presque toutes invalides en UTF-8.

    Les fins de ligne CRLF et CR sont ramenées à LF, et les caractères de
    contrôle sont retirés, NUL compris ; la tabulation verticale et le
    saut de page deviennent une espace.

    Renvoie le texte, le nom de l'encodage retenu et la liste des
    remarques à signaler, vide pour un fichier UTF-8 sans défaut.
    """
    remarques: list[str] = []
    texte: str | None = None
    encodage = "utf-8"

    if brut.startswith(codecs.BOM_UTF8):
        # La marque est retirée, le reste suit le chemin normal : elle ne
        # garantit pas que la suite soit de l'UTF-8 valide.
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
    Lit un fichier texte quel que soit son encodage, et signale ce qui
    s'en écarte de l'UTF-8 par une ligne "Attention" du journal.

    Renvoie le texte, l'encodage retenu et les remarques, comme
    decoder_octets. Seule une erreur d'accès au fichier arrête le script.
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
    Lit un fichier texte, avec un message clair en cas d'échec.

    L'encodage est détecté par lire_fichier_texte ; cette forme courte
    sert quand seul le texte importe, pour les consignes par exemple.
    """
    return lire_fichier_texte(chemin, role)[0]


def ecrire_texte(chemin: pathlib.Path, texte: str) -> None:
    """
    Écrit un fichier texte en UTF-8, quelle que soit la locale.

    Un caractère impossible à coder en UTF-8, un substitut isolé venu
    d'un nom de fichier ou d'une saisie mal encodés par exemple, est
    remplacé par "?" au lieu de lever UnicodeEncodeError au milieu de la
    collecte. Les fins de ligne restent des LF sur toutes les plateformes.
    Les erreurs d'accès (OSError) remontent à l'appelant.

    L'écriture passe par un fichier voisin, ".<nom>.partiel", renommé une
    fois complet : une interruption (Ctrl-C) ou une erreur en cours de
    route ne laisse jamais un fichier tronqué sous son nom définitif. Le
    fichier qui existait déjà, s'il y en avait un, reste alors intact, et
    le fichier partiel est retiré.
    """
    partiel = chemin.with_name(".%s.partiel" % chemin.name)
    try:
        with partiel.open("w", encoding="utf-8", errors="replace",
                          newline="\n") as f:
            f.write(texte)
        partiel.replace(chemin)
    except BaseException:
        # BaseException et non Exception : KeyboardInterrupt doit lui aussi
        # déclencher le ménage, avant de remonter tel quel.
        with contextlib.suppress(OSError):
            partiel.unlink()
        raise


#: Caractères écartés d'un nom de dossier, donc des noms rangés dans le
#: zip : caractères de contrôle, séparateurs de chemin, caractères
#: interdits par Windows, substituts isolés et U+FFFD. Les espaces et les
#: lettres accentuées sont conservés.
RE_NOM_RISQUE = re.compile(
    r'[\x00-\x1f\x7f-\x9f/\\:*?"<>|\ud800-\udfff\ufffd]')

#: Longueur maximale de l'étiquette reprise dans le nom du dossier.
ETIQUETTE_MAX = 80


def etiquette_sure(nom: str) -> str:
    """
    Tire d'un nom de fichier une étiquette sûre pour le dossier de
    travail et pour les chemins de l'archive.

    Chaque caractère à risque devient "_". Les points et les espaces de
    bord sont retirés, la longueur est bornée, et une étiquette vide
    devient "partie".
    """
    sure = RE_NOM_RISQUE.sub("_", nom)[:ETIQUETTE_MAX].strip(" .")
    return sure or "partie"


def annoncer_archive(archive: pathlib.Path) -> None:
    """
    Écrit le chemin de l'archive, seul, sur la sortie standard.

    Le chemin est écrit en octets, tel que le système de fichiers le
    connaît : ARCHIVE=$(...) reçoit ainsi un chemin utilisable même si le
    terminal ne sait pas en afficher tous les caractères. Sans accès aux
    octets de la sortie, l'écriture en texte d'origine est conservée.
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
    Lit le jeton personnel depuis un fichier ne contenant que lui.

    Le fichier n'est pas un script shell, il ne contient aucune affectation
    de variable : on le lit directement, on ne le source pas. Les droits
    sont contrôlés au passage.
    """
    p = pathlib.Path(os.path.expanduser(chemin))
    if not p.is_file():
        raise SystemExit("Jeton absent : %s introuvable." % p)

    try:
        mode = p.stat().st_mode
        brut = p.read_bytes()
    except (OSError, UnicodeDecodeError) as err:
        raise SystemExit("Jeton illisible dans %s : %s" % (p, err)) from err

    # Même décodage que pour le PGN : un fichier enregistré par un éditeur
    # Windows, avec marque d'ordre des octets ou en UTF-16, reste lisible.
    # Les remarques ne citent jamais le contenu du fichier.
    contenu, _encodage, remarques = decoder_octets(brut)
    for remarque in remarques:
        journal("Attention, jeton (%s) : %s." % (p, remarque))

    if mode & 0o077:
        journal("Attention : %s est lisible par d'autres (mode %o)."
                % (p, mode & 0o777))

    jeton = contenu.strip()
    if not jeton or any(c.isspace() for c in jeton):
        raise SystemExit("Le fichier %s doit contenir le jeton seul, sans "
                         "espace ni affectation de variable." % p)
    # Le jeton part dans un en-tête HTTP : hors de l'ASCII imprimable, il
    # serait refusé par http.client avec une erreur d'encodage que rien ne
    # relie au fichier. Le message ne reproduit pas le jeton.
    if not jeton.isascii() or not jeton.isprintable():
        raise SystemExit("Le jeton lu dans %s contient des caractères hors "
                         "de l'ASCII imprimable : recopiez-le depuis "
                         "Lichess, sans rien d'autre dans le fichier." % p)
    return jeton


#: Hôtes dont une URL de partie est acceptée.
HOTES_LICHESS = ("lichess.org", "www.lichess.org")

#: Rubriques du site dont le nom fait huit lettres : elles ont la forme
#: d'un identifiant de partie sans en être un. https://lichess.org/analysis
#: était pris pour la partie "analysis" et demandé à Lichess.
RUBRIQUES_LICHESS = ("analysis", "training", "practice", "streamer")

#: Préfixes de chemin admis devant l'identifiant, en plus de la forme
#: directe /<identifiant> : la partie embarquée et l'export PGN.
PREFIXES_PARTIE = (("embed", "game"), ("embed",), ("game", "export"))


def extraire_id(source: str) -> str | None:
    """
    Extrait l'identifiant de partie d'une URL ou d'une chaîne brute.

    Accepte https://lichess.org/xvoiNy2C, /xvoiNy2C/black, l'identifiant
    seul, ainsi que les identifiants de coup à douze caractères dont seuls
    les huit premiers sont conservés. L'identifiant, seul ou dans l'URL,
    doit faire exactement 8 ou 12 caractères alphanumériques.

    Une URL doit viser lichess.org et porter l'identifiant en tête de
    chemin, ou derrière /embed/game/, /embed/ ou /game/export/. Tout autre
    hôte, toute autre page du site (étude, analyse, exercices) et les
    rubriques de RUBRIQUES_LICHESS donnent None : rien n'est alors demandé
    à Lichess.
    """
    source = source.strip()
    if source.startswith(("http://", "https://")):
        url = urllib.parse.urlparse(source)
        if (url.hostname or "").lower() not in HOTES_LICHESS:
            return None
        morceaux = [m for m in url.path.split("/") if m]
        for prefixe in PREFIXES_PARTIE:
            if tuple(morceaux[:len(prefixe)]) == prefixe:
                morceaux = morceaux[len(prefixe):]
                break
        # Seul le premier segment compte : l'ancienne boucle retenait le
        # premier segment de huit caractères où qu'il soit, l'identifiant
        # d'une étude par exemple.
        if (morceaux and RE_ID_SOURCE.fullmatch(morceaux[0])
                and morceaux[0] not in RUBRIQUES_LICHESS):
            return morceaux[0][:8]
        return None
    if RE_ID_SOURCE.fullmatch(source) and source not in RUBRIQUES_LICHESS:
        return source[:8]
    return None


# ===========================================================================
# Récupération du PGN
# ===========================================================================

def telecharger_pgn(identifiant: str, delai: int) -> str:
    """Télécharge le PGN brut. Cet endpoint répond 200 sans jeton."""
    url = EXPORT_URL.format(id=identifiant)
    requete = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/x-chess-pgn",
    })
    journal("Téléchargement du PGN : %s" % url)
    try:
        with urllib.request.urlopen(requete, timeout=delai) as reponse:
            # Même décodage que pour un fichier local : Lichess répond en
            # UTF-8, mais rien ne doit dépendre de cette hypothèse.
            texte, _encodage, remarques = decoder_octets(reponse.read())
            for remarque in remarques:
                journal("Attention, PGN téléchargé : %s." % remarque)
            return texte
    except urllib.error.HTTPError as err:
        raise SystemExit("Export PGN : HTTP %d pour la partie %s."
                         % (err.code, identifiant)) from err
    except (OSError, http.client.HTTPException) as err:
        # URLError est une sous-classe d'OSError : ce bloc couvre aussi bien
        # une résolution DNS ratée qu'un délai dépassé ou une coupure.
        raise SystemExit("Export PGN injoignable : %s"
                         % getattr(err, "reason", err)) from err


def charger_partie(texte_pgn: str) -> chess.pgn.Game:
    """
    Analyse le PGN et renvoie la première partie qu'il contient.

    Le parseur de python-chess est tolérant : sur un coup illégal il
    s'arrête sans lever d'exception et consigne l'erreur dans la partie. On
    refuse un tel PGN plutôt que d'analyser une partie tronquée en silence.
    """
    flux = io.StringIO(texte_pgn)
    partie = chess.pgn.read_game(flux)
    if partie is None:
        raise SystemExit("PGN illisible ou vide.")
    if partie.errors:
        raise SystemExit("PGN corrompu, coup illégal ou malformé : %s"
                         % "; ".join(nettoyer_valeur(str(e))
                                     for e in partie.errors))
    if not list(partie.mainline_moves()):
        raise SystemExit("PGN sans aucun coup dans la ligne principale.")

    # Les valeurs des balises partent dans les en-têtes de la synthèse et
    # dans le journal : on en retire tabulations et caractères de contrôle
    # dès maintenant, une fois pour toutes. La liste est figée avant la
    # boucle, les balises étant modifiées en cours de route.
    for cle, valeur in list(partie.headers.items()):
        propre = nettoyer_valeur(valeur)
        if propre != valeur:
            partie.headers[cle] = propre

    variante = partie.headers.get("Variant", "Standard")
    if variante.lower() not in ("standard", "from position"):
        raise SystemExit("Variante non prise en charge : %s. Ce script ne "
                         "traite que les échecs standard." % variante)

    if chess.pgn.read_game(flux) is not None:
        journal("Attention : le PGN contient plusieurs parties, seule la "
                "première est traitée.")
    return partie


# ===========================================================================
# Questions de démarrage
#
# Les questions passent par la sortie d'erreur et l'entrée standard, jamais
# par la sortie standard, réservée au chemin de l'archive : la forme
# ARCHIVE=$(./collecte-partie.py ...) continue de fonctionner, questions
# comprises. Elles ne sont posées que sur un terminal interactif.
# ===========================================================================

def questions_possibles(sans_questions: bool) -> bool:
    """Vrai si l'on peut poser des questions : terminal des deux côtés."""
    return (not sans_questions and sys.stdin.isatty()
            and sys.stderr.isatty())


def demander(question: str, defaut: str | None = None) -> str | None:
    """
    Pose une question et renvoie la réponse nettoyée.

    Une réponse vide donne le défaut, ou une chaîne vide sans défaut. La
    fin de flux (Ctrl-D) renvoie None : l'appelant applique alors ses
    défauts sans insister.
    """
    invite = (question if defaut is None
              else "%s (Entrée : %s)" % (question, defaut))
    sys.stderr.write(invite + " ")
    sys.stderr.flush()
    ligne = sys.stdin.readline()
    if not ligne:
        sys.stderr.write("\n")
        return None
    if RE_SUBSTITUTS.search(ligne):
        # Saisie que l'encodage du terminal n'a pas su décoder : on
        # retrouve les octets tapés et on leur applique le même repli que
        # pour un fichier, cp1252 puis latin-1.
        ligne = decoder_octets(
            ligne.encode("utf-8", errors="surrogateescape"))[0]
    return nettoyer_valeur(ligne).strip() or (defaut or "")


# ---------------------------------------------------------------------------
# Cadence
#
# Une cadence est un petit dictionnaire, de l'une de ces cinq formes :
#
#     {"type": "reel", "initial": 900, "increment": 10}    en secondes
#     {"type": "correspondance", "jours": 14}              délai par coup
#     {"type": "correspondance", "coups": 10,              coups par
#      "periode": 50}                                      période, en jours
#     {"type": "correspondance", "capital": 5,             jours au départ,
#      "increment": 36, "plafond": 20, "reserve": 0}       heures par coup,
#                                                          plafond et
#                                                          réserve en jours,
#                                                          0 s'il n'y en a
#                                                          pas
#     {"type": "inconnue"}
#
# La correspondance connaît en effet trois systèmes :
#
#   - un délai fixe pour chaque coup, rien n'étant reporté d'un coup au
#     suivant : Lichess, chess.com ;
#   - un nombre de coups à jouer par période, le temps économisé étant
#     reporté : cadence standard de l'ICCF, "10 coups en 50 jours" ;
#   - un capital de temps qui grossit d'un incrément à chaque coup, avec
#     un plafond et une réserve facultatifs : chess-mail.com, et le Triple
#     Block de l'ICCF.
#
# Les deux derniers suivent les ICCF Rules en vigueur depuis le 1er janvier
# 2026 (section 2.4). Le premier n'existe pas à l'ICCF.
#
# Elle n'est jamais un texte libre : la phrase que lit l'analyste est
# rédigée ici, toujours de la même façon, à partir de nombres vérifiés.
# ---------------------------------------------------------------------------

def analyser_cadence(texte: str) -> dict | None:
    """
    Lit une cadence écrite dans le fichier de réglages.

    Renvoie None si le texte n'a aucune des formes admises, "0+0" compris :
    une partie sans temps ni incrément n'existe pas.
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
    """Incrément en heures, d'après un nombre et son unité, h ou j."""
    return nombre * 24 if unite.startswith("j") else nombre


def duree_increment(heures: int) -> str:
    """ "36 heures", ou "3 jours" quand le compte tombe juste en jours."""
    if heures and heures % 24 == 0:
        return pluriel(heures // 24, "jour")
    return pluriel(heures, "heure")


def cadence_a_capital(capital: int, increment: int, plafond: int,
                      reserve: int = 0) -> dict | None:
    """
    Cadence par correspondance à capital de temps, ou None si elle est
    incohérente : ni capital ni incrément, ou plafond sous le capital de
    départ. `increment` est en heures, les autres durées en jours. Un
    plafond ou une réserve nuls signifient qu'il n'y en a pas.
    """
    if capital == 0 and increment == 0:
        return None
    if plafond and plafond < max(capital, 1):
        return None
    return {"type": "correspondance", "capital": capital,
            "increment": increment, "plafond": plafond, "reserve": reserve}


def cadence_de_balise(controle: str) -> dict | None:
    """
    Lit une balise TimeControl de la forme "600+5" ou "300", en secondes.

    Les autres formes du standard (coups par période, sablier) et les
    valeurs libres donnent None : la balise est alors citée telle quelle.
    """
    trouve = RE_TIMECONTROL.fullmatch(controle.strip())
    if not trouve:
        return None
    initial, increment = int(trouve.group(1)), int(trouve.group(2) or 0)
    if initial == 0 and increment == 0:
        return None
    return {"type": "reel", "initial": initial, "increment": increment}


def noter_cadence(cadence: dict) -> str:
    """Forme d'une cadence dans le fichier de réglages."""
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
    """ "1 jour", "14 jours" : le nombre suivi du mot accordé."""
    return "%d %s%s" % (nombre, mot, "s" if nombre > 1 else "")


def categorie_cadence(initial: int, increment: int) -> str:
    """Catégorie Lichess d'une cadence en temps réel (CATEGORIES_CADENCE)."""
    estimee = initial + COUPS_ESTIMES * increment
    for seuil, nom in CATEGORIES_CADENCE:
        if estimee >= seuil:
            return nom
    return CATEGORIES_CADENCE[-1][1]


def decrire_cadence(cadence: dict) -> str:
    """
    Phrase décrivant une cadence, telle qu'elle part dans contexte.md :
    "rapide, 15 minutes + 10 secondes par coup", "blitz, 5 minutes sans
    incrément", "correspondance, 14 jours par coup", "correspondance,
    10 coups en 50 jours", "correspondance, capital de 5 jours + 36
    heures par coup, plafonné à 20 jours", ou "non précisée".
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
    Demande un nombre entier d'au moins `minimum`, et repose la question
    tant que la réponse n'en est pas un. La fin de flux renvoie None. Si
    `vide` est donné, c'est la valeur que retient la touche Entrée seule.
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
    Demande une cadence en deux ou trois questions, toutes vérifiées.

    Le type d'abord, temps réel, correspondance ou inconnue ; puis les
    minutes par joueur et l'incrément en secondes, ou, par correspondance,
    le système et ses nombres (voir demander_correspondance).
    Entrée, à la première question, retient `defaut`. Renvoie la cadence
    et un booléen disant si c'est le défaut, ou None à la fin de flux.
    Aucun texte libre n'est accepté : une réponse hors des formes prévues
    fait reposer la question.
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
    Lit un niveau écrit dans le fichier de réglages : un nombre de points
    Elo entre NIVEAU_MIN et NIVEAU_MAX. Renvoie 0 pour un niveau inconnu,
    et None pour une valeur d'une autre forme.
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
    Demande le niveau du joueur en points Elo, Entrée valant "inconnu" (0).
    La question est reposée tant que la réponse n'est pas un nombre entier
    dans les bornes. Renvoie None à la fin de flux.
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
    Camp du joueur d'après ses pseudos, sans poser de question : "Blancs",
    "Noirs", ou None si aucune balise, ou les deux, portent un pseudo.
    Sert hors terminal, où completer_entetes n'est pas appelée.
    """
    moi_blancs = est_pseudo(partie.headers.get("White", "?"), pseudos)
    moi_noirs = est_pseudo(partie.headers.get("Black", "?"), pseudos)
    if moi_blancs == moi_noirs:
        return None
    return "Blancs" if moi_blancs else "Noirs"


def demander_correspondance() -> dict | None:
    """
    Demande une cadence par correspondance, dans l'un de ses trois
    systèmes.

    Délai fixe : un nombre de jours pour chaque coup. Coups par période :
    un nombre de coups et une durée en jours. Capital de temps : des jours
    au départ, un incrément par coup saisi avec son unité, puis un plafond
    et une réserve facultatifs. Une saisie incohérente fait reprendre au
    choix du système. Renvoie None à la fin de flux.
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
    Demande l'incrément par coup, avec son unité, et le renvoie en heures :
    "36h" donne 36, "3j" donne 72. La question est reposée tant que la
    réponse n'a pas cette forme. Renvoie None à la fin de flux.
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
    """Vrai si la balise contient l'un des pseudos, casse ignorée."""
    nom = nom.casefold()
    return any(pseudo.casefold() in nom for pseudo in pseudos)


def completer_entetes(partie: chess.pgn.Game, pseudos: list[str]) -> dict:
    """
    Déduit le camp du joueur des balises White et Black, ou le demande.

    Seules les balises vides ou à "?" sont complétées : le premier pseudo
    pour le camp du joueur, le nom donné pour l'adversaire. Un nom déjà
    présent n'est jamais remplacé. Renvoie le camp ("Blancs", "Noirs" ou
    None), l'origine de l'information et la liste des balises modifiées.

    `pseudos` peut être vide, quand ni --pseudos ni les réglages n'en
    donnent : le camp est alors toujours demandé, et le nom du joueur
    aussi si sa balise est vide.
    """
    moi_blancs = est_pseudo(partie.headers.get("White", "?"), pseudos)
    moi_noirs = est_pseudo(partie.headers.get("Black", "?"), pseudos)
    if moi_blancs != moi_noirs:
        return {"camp": "Blancs" if moi_blancs else "Noirs",
                "origine": "déduit des en-têtes", "modifiees": []}

    # Aucun pseudo trouvé, ou les deux : seul le joueur peut trancher. Une
    # réponse illisible fait reposer la question, Ctrl-D y renonce.
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
            # Aucun pseudo connu : pseudos[0] levait IndexError. On demande
            # le nom, comme pour l'adversaire, et "?" laisse la balise.
            nom = demander("Votre nom de joueur ?", "?")
            if nom and nom != "?":
                partie.headers[mienne] = nom
                modifiees.append(mienne)
    if partie.headers.get(autre, "?").strip() in ("", "?"):
        nom = demander("Nom de l'adversaire ?", "?")
        if nom and nom != "?":
            partie.headers[autre] = nom
            modifiees.append(autre)
    return {"camp": camp, "origine": "déclaré", "modifiees": modifiees}


def recueillir_contexte(partie: chess.pgn.Game, camp: dict,
                        cadence_habituelle: dict | None = None) -> str:
    """
    Pose la question de cadence si la balise TimeControl ne la donne pas,
    puis les quatre questions de démarrage du projet, et rédige le texte
    de contexte.md. `cadence_habituelle`, tirée des réglages, est la
    cadence que propose la question ; sans elle, c'est "non précisée".
    Une balise TimeControl de forme courante est citée, puis traduite.

    "(défaut)" signale une réponse validée par Entrée : l'analyste
    distingue ainsi un choix du joueur d'une valeur par défaut. Après une
    fin de flux, les questions restantes prennent leur défaut sans être
    posées.
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

    # "-" est la valeur que prend parfois TimeControl pour une partie par
    # correspondance : elle ne dit pas la cadence réelle, on la demande.
    controle = partie.headers.get("TimeControl", "?").strip()
    if controle not in ("", "?", "-"):
        # "600+5" se lit mal : dix minutes, ou six cents ? La balise est
        # citée telle quelle, puis traduite quand sa forme le permet.
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
# Réglages de l'utilisateur
#
# Ce qui dépend de la personne, et non de la partie, vit dans un petit
# fichier au format INI, lisible et modifiable à la main :
#
#     [joueur]
#     pseudos = MonPseudo, AutrePseudo
#     cadence = rapide, 15 minutes
#
# Il est créé au premier lancement sur un terminal, par deux questions
# posées une seule fois. Hors terminal, rien n'est demandé ni écrit : le
# script se contente de ce que le fichier contient déjà.
# ===========================================================================

def chemin_reglages(chemin: str) -> pathlib.Path:
    """Chemin du fichier de réglages, le tilde étant développé."""
    return pathlib.Path(os.path.expanduser(chemin))


def purger_reglages(chemin: str) -> None:
    """
    Supprime le fichier de réglages, et lui seul : son répertoire reste en
    place, il peut contenir autre chose.

    Les questions de réglages seront reposées au prochain lancement sur un
    terminal. Un fichier absent n'est pas une erreur : le but, ne plus
    avoir de réglages, est déjà atteint. Un répertoire, ou tout ce qui
    n'est pas un fichier, est refusé plutôt que supprimé.
    """
    p = chemin_reglages(chemin)
    if not p.exists() and not p.is_symlink():
        journal("Aucun fichier de réglages à supprimer : %s" % p)
        return
    if not (p.is_file() or p.is_symlink()):
        raise SystemExit("--purge-reglages : %s n'est pas un fichier, rien "
                         "n'est supprimé." % p)
    try:
        p.unlink()
    except OSError as e:
        raise SystemExit("--purge-reglages : suppression de %s impossible : "
                         "%s" % (p, e)) from e
    journal("Réglages supprimés : %s. Ils seront redemandés à la prochaine "
            "collecte lancée sur un terminal." % p)


def lire_reglages(chemin: str) -> configparser.ConfigParser:
    """
    Charge le fichier de réglages, ou des réglages vides s'il n'existe pas.

    Le fichier passe par le même décodage que le PGN : son encodage n'a
    pas d'importance. Un fichier que configparser refuse arrête le script
    par un message clair, plutôt que d'être ignoré en silence. La section
    [joueur] existe toujours dans l'objet renvoyé.
    """
    # interpolation=None : le signe pour cent d'une valeur reste un simple
    # caractère, il ne déclenche aucune substitution.
    reglages = configparser.ConfigParser(interpolation=None)
    p = chemin_reglages(chemin)
    if p.is_file():
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
    """Valeur d'une clef de la section [joueur], vide si elle manque."""
    return reglages.get(REGLAGES_SECTION, clef, fallback="").strip()


def decouper_pseudos(texte: str) -> list[str]:
    """Liste de pseudos tirée d'une chaîne séparée par des virgules."""
    return [x.strip() for x in texte.split(",") if x.strip()]


def ecrire_reglages(chemin: str, reglages: configparser.ConfigParser) -> bool:
    """
    Écrit le fichier de réglages, commentaires compris.

    Les clefs connues viennent d'abord, chacune sous son commentaire ; les
    autres clefs de [joueur] et les autres sections, que vous auriez
    ajoutées, sont recopiées à la suite. Un échec d'écriture n'arrête pas
    la collecte : il est signalé, et la question sera reposée au prochain
    lancement. Renvoie vrai si le fichier a été écrit.
    """
    def ligne(clef: str, valeur: str) -> str:
        # Une valeur sur plusieurs lignes se poursuit par des lignes en
        # retrait : c'est la forme que configparser sait relire.
        valeur = valeur.replace("\n", "\n\t")
        return "%s = %s" % (clef, valeur) if valeur else "%s =" % clef

    out = ["# Réglages de collecte-partie.py.",
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
    Demande, une seule fois, les réglages que le fichier ne donne pas.

    Appelée seulement sur un terminal interactif. Chaque clef absente de
    [joueur] fait l'objet d'une question ; une clef présente, même vide,
    n'est jamais redemandée. Les pseudos passés par --pseudos servent de
    réponse proposée. Une fin de flux (Ctrl-D) abandonne sans rien
    écrire : les questions reviendront au prochain lancement.
    """
    manquantes = [clef for clef, _ in REGLAGES_CLEFS
                  if not reglages.has_option(REGLAGES_SECTION, clef)]
    # Une cadence présente mais illisible, écrite à la main ou héritée
    # d'une version qui acceptait un texte libre, est redemandée elle
    # aussi : elle ne doit pas partir telle quelle vers l'analyste.
    brute = reglages.get(REGLAGES_SECTION, "cadence", fallback=None)
    if brute is not None and analyser_cadence(brute) is None:
        journal("Réglages : la cadence enregistrée, \"%s\", n'est pas "
                "lisible, elle est redemandée." % nettoyer_valeur(brute))
        manquantes.append("cadence")
    # Il en va de même du niveau, qui doit être un nombre de points Elo.
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
                                   ", ".join(pseudos_cli))
            else:
                reponse = demander("Votre pseudo de joueur, ou plusieurs "
                                   "séparés par des virgules ? (Entrée : "
                                   "aucun)")
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
# Prompt d'analyse
#
# Les données de l'archive ne suffisent pas : il faut dire à l'analyste ce
# qu'il doit en faire. Ce texte vit dans un modèle, prompt-modele.txt, que
# vous retouchez sans ouvrir ce script. À chaque collecte, le script en
# tire le prompt de la partie : il remplit les valeurs (pseudo, niveau,
# nom de l'archive) et ne garde que les passages qui s'appliquent (base
# interrogée, moteur présent ou non). Le prompt décrit ainsi, toujours, la
# synthèse que cette version du script vient d'écrire.
#
# Deux repères dans le modèle :
#
#     {{NOM}}             une valeur, remplacée
#     #! si CONDITION     garde ce qui suit si la condition est vraie
#     #! si non CONDITION garde ce qui suit si elle est fausse
#     #! sinon            bascule
#     #! fin              ferme le dernier "si" ouvert
#     #! note ...         commentaire du modèle, jamais recopié
#
# Les "si" peuvent s'emboîter.
# ===========================================================================

def chemin_modele(option: str | None) -> pathlib.Path:
    """
    Chemin du modèle de prompt : celui de --prompt, sinon prompt-modele.txt
    à côté du script. Le chemin réel du script est suivi, afin qu'un lien
    symbolique posé ailleurs retrouve le modèle du dépôt.
    """
    if option:
        return pathlib.Path(os.path.expanduser(option))
    return pathlib.Path(os.path.realpath(__file__)).parent / PROMPT_MODELE


def lire_directive(ligne: str) -> list[str] | None:
    """Mots d'une ligne de directive, ou None pour une ligne ordinaire."""
    ligne = ligne.strip()
    if not ligne.startswith(PROMPT_DIRECTIVE):
        return None
    return ligne[len(PROMPT_DIRECTIVE):].split()


def rendre_modele(texte: str, conditions: dict[str, bool],
                  valeurs: dict[str, str], source: str) -> str:
    """
    Tire un prompt du modèle : applique les directives, remplace les
    valeurs.

    Tout le modèle est contrôlé, passages écartés compris : une directive
    inconnue, un "si" jamais fermé, une condition ou une valeur que le
    script ne connaît pas arrêtent le script avec le numéro de la ligne.
    Les lignes vides en trop que laisse un passage retiré sont resserrées.
    """
    def erreur(numero: int, message: str) -> SystemExit:
        return SystemExit("Modèle de prompt %s, ligne %d : %s"
                          % (source, numero, message))

    sortie: list[str] = []
    # Pile des "si" ouverts : la ligne du "si", la valeur de sa condition,
    # et si un "sinon" a déjà été rencontré.
    pile: list[tuple[int, bool, bool]] = []
    for numero, ligne in enumerate(texte.split("\n"), start=1):
        mots = lire_directive(ligne)
        if mots is None:
            for nom in RE_VALEUR_MODELE.findall(ligne):
                if nom not in PROMPT_VALEURS:
                    raise erreur(numero, "valeur inconnue {{%s}}, valeurs "
                                 "admises : %s"
                                 % (nom, ", ".join(PROMPT_VALEURS)))
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

    # Lignes vides : au plus une de suite, aucune en tête ni en queue.
    resserre: list[str] = []
    for ligne in sortie:
        if ligne or (resserre and resserre[-1]):
            resserre.append(ligne)
    return "\n".join(resserre).strip("\n") + "\n"


def verifier_modele(texte: str, source: str) -> None:
    """
    Contrôle le modèle avant la collecte, pour échouer tôt : un repère
    inconnu ne doit pas se révéler après dix minutes de moteur. Le rendu
    est fait à blanc, son résultat n'est pas gardé.
    """
    rendre_modele(texte, dict.fromkeys(PROMPT_CONDITIONS, False),
                  dict.fromkeys(PROMPT_VALEURS, ""), source)


def decrire_niveau(niveau: int, partie: chess.pgn.Game,
                   camp: str | None) -> str:
    """
    Phrase du niveau du joueur. Le niveau déclaré dans les réglages
    l'emporte ; à défaut, l'Elo de la balise du joueur dans cette partie,
    si son camp est connu ; sinon rien de précis.
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
# Catalogue des ouvertures nommées
#
# Le catalogue sert à distinguer deux sortes de coups rares : celui qui
# reste dans une ligne répertoriée, comme 1.b4, la Polonaise, joué dans
# moins d'un pour cent des parties, et celui qui quitte toute ligne connue.
# Seul le second marque la sortie de théorie. Le catalogue dit "connu",
# jamais "bon" : "Barnes Opening: Fool's Mate" y figure.
#
# Le serveur de l'explorateur ne nomme que la position finale de chaque
# ligne. L'index local retient en plus toutes les positions intermédiaires,
# sans nom : une ligne nommée est ainsi connue sur toute sa longueur.
# ===========================================================================

class Catalogue:
    """
    Index des positions du catalogue, chargé depuis le fichier local.

    Les positions sont repérées par leur EPD, prise en passant comprise
    seulement si elle est jouable, ce qui correspond au hachage du serveur
    (EnPassantMode::Legal). Une position intermédiaire a un nom vide.
    """

    def __init__(self, positions: dict[str, tuple[str, str]],
                 meta: dict[str, str]):
        self.positions = positions
        self.meta = meta

    def connue(self, plateau: chess.Board) -> bool:
        """Indique si la position appartient à une ligne du catalogue."""
        return plateau.epd() in self.positions

    def nom(self, plateau: chess.Board) -> str | None:
        """Renvoie "ECO nom" si la position est nommée, sinon None."""
        eco, nom = self.positions.get(plateau.epd(), ("", ""))
        return "%s %s" % (eco, nom) if nom else None


def chemin_catalogue(repertoire: str) -> pathlib.Path:
    """Chemin de l'index dans le répertoire du catalogue."""
    return pathlib.Path(os.path.expanduser(repertoire)) / CATALOGUE_INDEX


def commande_catalogue(repertoire: str) -> str:
    """Commande d'installation à proposer dans les messages d'erreur."""
    supplement = ("" if repertoire == CATALOGUE_DEFAUT
                  else " --catalogue %s" % repertoire)
    return "%s --installer-catalogue%s" % (os.path.abspath(__file__),
                                           supplement)


def installer_catalogue(repertoire: str, delai: int) -> None:
    """
    Télécharge le catalogue, le valide, puis écrit l'index local.

    Chaque ligne est rejouée avec python-chess : un coup illisible ou
    illégal arrête l'installation, et l'index déjà en place n'est pas
    touché. Comme le serveur, on refuse une position nommée deux fois.

    L'index est écrit dans un fichier temporaire du même répertoire, mis
    sur disque, puis renommé : le remplacement est atomique, une collecte
    lancée pendant une mise à jour lit l'ancien index ou le nouveau, jamais
    un mélange des deux. Relancer l'option met le catalogue à jour.
    """
    positions: dict[str, tuple[str, str]] = {}
    nb_lignes = 0
    for morceau in CATALOGUE_PARTIES:
        url = CATALOGUE_SOURCE.format(partie=morceau)
        journal("Téléchargement du catalogue : %s" % url)
        requete = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(requete, timeout=delai) as reponse:
                # utf-8-sig : une marque d'ordre des octets en tête de
                # fichier est ignorée au lieu de fausser l'en-tête.
                texte = reponse.read().decode("utf-8-sig", errors="strict")
        except urllib.error.HTTPError as err:
            raise SystemExit("Catalogue : HTTP %d pour %s."
                             % (err.code, url)) from err
        except (OSError, http.client.HTTPException) as err:
            # URLError est une sous-classe d'OSError, comme pour l'export PGN.
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
        # La ligne 1 est l'en-tête, la numérotation suit celle du fichier.
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
                # Position intermédiaire : connue, sans nom, à moins qu'une
                # autre ligne ne l'ait déjà nommée.
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
            # Ordre trié : deux installations du même catalogue donnent
            # deux fichiers identiques, faciles à comparer avec diff.
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

    # Relecture complète par le chemin normal : ce qui vient d'être écrit
    # doit se charger exactement comme lors d'une collecte.
    catalogue = lire_catalogue(repertoire)
    journal("Catalogue installé : %s lignes, %s positions nommées, %s "
            "positions connues, dans %s"
            % (catalogue.meta["lignes"], catalogue.meta["nommees"],
               catalogue.meta["connues"], cible))


def lire_catalogue(repertoire: str) -> Catalogue:
    """
    Charge l'index local du catalogue et vérifie son intégrité.

    La première ligne décrit l'index. Un format inconnu, ou un nombre de
    positions différent de celui annoncé, trahit un fichier tronqué ou
    modifié : mieux vaut s'arrêter que de marquer la sortie de théorie sur
    une base incomplète.
    """
    chemin = chemin_catalogue(repertoire)
    if not chemin.is_file():
        raise SystemExit(
            "Catalogue des ouvertures absent : %s introuvable.\n\n"
            "Installez-le en une commande :\n"
            "    %s\n" % (chemin, commande_catalogue(repertoire)))
    reparer = "Réinstallez-le avec : %s" % commande_catalogue(repertoire)

    positions: dict[str, tuple[str, str]] = {}
    try:
        # Encodage et traitement des erreurs explicites, jamais ceux de la
        # locale : un index abîmé doit être refusé, non lu de travers.
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
# Explorateur : accès réseau
# ===========================================================================

class Explorateur:
    """
    Client minimal de l'explorateur Lichess, base maîtres ou base Lichess.

    Les deux endpoints exigent un jeton personnel, sans quoi ils renvoient
    un 401 nginx au format HTML. Le jeton n'est transmis que dans l'en-tête
    Authorization, jamais dans l'URL, afin qu'il n'apparaisse ni dans les
    journaux du serveur ni dans une table de processus.

    `url` désigne l'endpoint interrogé, la base maîtres par défaut afin que
    les appels existants gardent leur comportement. `filtres` contient les
    paramètres propres à la base Lichess (variante, cadences, tranches de
    classement, date de début) ; il reste vide pour la base maîtres, qui ne
    les connaît pas.
    """

    def __init__(self, jeton: str, pause: float, delai: int,
                 url: str = EXPLORER_URL,
                 filtres: dict[str, str] | None = None):
        self.jeton = jeton
        self.pause = pause
        self.delai = delai
        self.url = url
        # Copie défensive : un dictionnaire modifié plus tard par l'appelant
        # ne doit pas changer les requêtes en cours de collecte.
        self.filtres = dict(filtres or {})
        self._premiere = True

    def interroger(self, coups_uci: list[str]) -> tuple[int, dict]:
        """
        Interroge la position atteinte après les coups fournis.

        Renvoie le couple (code HTTP, dictionnaire décodé). Toute réponse
        inexploitable, code différent de 200, corps non JSON ou erreur de
        transport, revient avec un dictionnaire portant la clef "_erreur",
        le code valant 0 quand aucun code HTTP n'a pu être obtenu.
        """
        # Pause de politesse. L'endpoint est strict sur le débit, mais il
        # est inutile d'attendre avant la toute première requête.
        if not self._premiere:
            time.sleep(self.pause)
        self._premiere = False

        # Toutes les réponses connues de la base, et non les dix premières :
        # un coup joué au-delà du dixième rang passait sinon pour absent
        # (0 partie, rang "hors base") alors qu'il était seulement plus
        # rare. Le serveur tronque à cette valeur sans plafond propre, et
        # 256 couvre largement tous les coups légaux d'une position.
        parametres = {"topGames": "0", "moves": "256"}

        # Filtres de la base Lichess. Pour la base maîtres le dictionnaire
        # est vide : la requête reste strictement celle d'avant l'option.
        parametres.update(self.filtres)
        if coups_uci:
            parametres["play"] = ",".join(coups_uci)
        url = self.url + "?" + urllib.parse.urlencode(parametres)

        requete = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/json",
            "Authorization": "Bearer %s" % self.jeton,
        })

        # Une seule reprise, et uniquement sur 429 : au delà, mieux vaut
        # s'arrêter que de se faire bannir.
        for tentative in (1, 2):
            try:
                with urllib.request.urlopen(requete, timeout=self.delai) as r:
                    corps = r.read().decode("utf-8-sig", errors="replace")
                    donnees = json.loads(corps)
                    if not isinstance(donnees, dict):
                        return 0, {"_erreur": "réponse JSON inattendue, "
                                              "objet attendu"}
                    return r.status, donnees
            except urllib.error.HTTPError as err:
                corps = err.read().decode("utf-8-sig", errors="replace")
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
        return 0, {"_erreur": "échec après reprise"}


# ===========================================================================
# Explorateur : exploitation des données
# ===========================================================================

def total_parties(bloc: dict | None) -> int:
    """Nombre de parties d'une position ou d'un coup, nulles comprises."""
    if not isinstance(bloc, dict):
        return 0
    return entier(bloc.get("white")) + entier(bloc.get("draws")) \
        + entier(bloc.get("black"))


def score_blancs(bloc: dict | None) -> float | None:
    """
    Score des Blancs sur un coup, en pourcentage, la nulle valant un demi.
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
    Parcourt la partie et interroge l'explorateur position par position.

    Pour le demi-coup numéro i, c'est la position AVANT ce coup qui est
    interrogée : c'est la seule façon d'obtenir le rang et la fréquence du
    coup réellement joué parmi les réponses connues de la base.

    Trois critères d'arrêt, dans cet ordre de test :

      - une réponse inexploitable, ou un échantillon nul, ce qui signifie
        que la position est inconnue de la base ;
      - un échantillon de position inférieur à `seuil_parties` ;
      - une sortie de théorie : un coup joué dont la fréquence tombe sous
        `seuil_frequence` et qui mène à une position absente du
        `catalogue`. Un coup rare qui reste dans une ligne répertoriée
        n'est pas une sortie.

    Le troisième critère est suspendu pendant les `demicoups_min` premiers
    demi-coups : la table couvre ainsi le début de partie même après une
    sortie précoce, le premier critère et le seuil de parties restant
    actifs. Au delà, l'arrêt reprend au premier coup qui sort. La première
    sortie est notée dans tous les cas, fenêtre comprise.

    Sans catalogue et sans fenêtre, le comportement est celui d'origine :
    tout coup rare est une sortie et arrête la collecte.

    Avec `jusqu_a_epuisement`, seuls le premier critère et le plafond de
    demi-coups s'appliquent : l'interrogation descend aussi loin que la
    base répond.

    Un coup nul, "--" dans le PGN, arrête la collecte avant toute
    interrogation pour ce demi-coup, quel que soit le mode : ce n'est pas
    un coup des échecs, la base ne peut ni le compter ni suivre la partie
    au delà. Il n'est pas tenu pour une sortie de théorie.
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

        # Coup nul : le trait passe sans qu'une pièce ne bouge. La base ne
        # le connaît pas, il ressortait donc à 0 partie, au rang "hors
        # base", et passait pour la première sortie de théorie. Pire, le
        # demi-coup suivant envoyait à l'explorateur une liste de coups
        # contenant "0000", qu'il refuse par un HTTP 400 ("illegal uci") :
        # l'arrêt était alors mis sur le compte d'une erreur réseau. On
        # s'arrête ici, sans rien demander, en donnant la vraie raison.
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

        # L'explorateur note le roque à la manière de Chess960, "roi prend
        # tour" : e1h1 pour le petit roque des Blancs, là où python-chess
        # écrit e1g1. Les deux formes sont admises pour retrouver le coup
        # joué dans la réponse, sans quoi un roque passait pour absent de
        # la base (0 partie, rang "hors base") et déclenchait une fausse
        # sortie de théorie. Pour tout autre coup, elles sont identiques.
        # La liste des coups envoyée à l'explorateur, elle, ne change pas.
        uci_admis = (uci_joue, plateau.uci(coup, chess960=True))

        journal("Explorateur : demi-coup %d (%s)" % (indice + 1, san_joue))
        code, donnees = explorateur.interroger(joues_uci)

        # Sauvegarde systématique du brut, même en cas d'erreur : cela vous
        # évitera de relancer toute la collecte pour comprendre un échec.
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

        # Position inconnue de la base : l'explorateur répond 200 avec un
        # échantillon nul, il n'y a plus rien à en tirer.
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

        # Recherche du coup joué parmi les réponses connues de la base. Les
        # entrées d'un type inattendu sont ignorées plutôt que fatales.
        # Il en va de même d'une clef "moves" qui ne serait pas une liste :
        # un entier ne se parcourt pas, la boucle levait alors TypeError.
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

        # Position atteinte après le coup : appartient-elle à une ligne du
        # catalogue, et porte-t-elle un nom ? Les deux clefs existent
        # toujours, afin que la synthèse n'ait pas à tester leur présence.
        ligne["connue"] = catalogue is not None and catalogue.connue(plateau)
        ligne["ouverture"] = (catalogue.nom(plateau) if catalogue is not None
                              else None)

        # Sortie de théorie : coup rare qui quitte le catalogue. Le coup
        # responsable figure bien dans le tableau, c'est l'interrogation
        # qui s'arrête après lui, et jamais dans la fenêtre de départ.
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

def formater_score(score: chess.engine.PovScore) -> str:
    """Met en forme un score du point de vue des Blancs, en pions ou en mat."""
    blanc = score.white()
    if blanc.is_mate():
        return "#%+d" % blanc.mate()
    return "%+.2f" % (blanc.score() / 100.0)


def valeur_pour_trait(score: chess.engine.PovScore, trait: bool) -> float:
    """
    Valeur en centipions du point de vue du joueur au trait.

    Un mat est ramené à une valeur bornée, suffisante pour classer les
    coups sans faire exploser les écarts affichés.
    """
    return float(score.pov(trait).score(mate_score=100000))


def wdl_blancs(info: dict) -> dict | None:
    """Chances de gain, nulle et perte des Blancs, en pour mille."""
    wdl = info.get("wdl")
    if wdl is None:
        return None
    blancs = wdl.white()
    return {"gain": blancs.wins, "nulle": blancs.draws,
            "perte": blancs.losses}


def nature_coup(ecart: float | None) -> str | None:
    """Imprécision, erreur ou gaffe selon l'écart en centipions."""
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
    Temps restant, d'après la moyenne des demi-coups déjà analysés.

    Les positions de fin de partie vont souvent plus vite que la moyenne :
    l'estimation pèche plutôt par excès. Rien n'est affiché avant trois
    demi-coups, la moyenne n'ayant pas encore de sens.
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


def verifier_moteur(binaire: str) -> None:
    """Vérifie l'existence du binaire avant d'avoir créé quoi que ce soit."""
    if not pathlib.Path(binaire).is_file():
        raise SystemExit("Stockfish introuvable : %s. Installez-le (%s), "
                         "ou indiquez son chemin avec --stockfish. "
                         "L'évaluation du moteur fait partie de toute "
                         "collecte."
                         % (binaire, AIDE_STOCKFISH))
    if not os.access(binaire, os.X_OK):
        raise SystemExit("Stockfish non exécutable : %s" % binaire)


def lancer_moteur(binaire: str) -> chess.engine.SimpleEngine:
    """
    Lance le moteur UCI et renvoie son pilote, ou arrête le script.

    Un binaire non exécutable, absent ou qui n'est pas un moteur UCI se
    manifeste respectivement par une OSError, une OSError et un délai
    dépassé à l'attente de "uciok".
    """
    try:
        return chess.engine.SimpleEngine.popen_uci(binaire)
    except (OSError, TimeoutError, chess.engine.EngineError) as err:
        raise SystemExit("Impossible de lancer le moteur %s : %s"
                         % (binaire, str(err)
                            or "pas de réponse UCI dans le délai")) from err


def fermer_moteur(moteur: chess.engine.SimpleEngine) -> None:
    """
    Arrête le moteur sans jamais lever d'exception.

    quit() échoue si le moteur est déjà mort ; close() est toujours sûr
    et garantit qu'aucun processus Stockfish ne survit au script.
    """
    try:
        moteur.quit()
    except Exception:  # noqa: BLE001 - nettoyage de dernier recours
        pass
    moteur.close()


def verifier_options_moteur(binaire: str, fils: int, hachage: int,
                            multipv: int) -> None:
    """
    Contrôle --fils, --hachage et --multipv auprès du moteur lui-même,
    avant toute collecte.

    Le moteur annonce ses options et leurs bornes dès son lancement : une
    valeur hors bornes, ou une option qu'il ne connaît pas, est refusée
    ici plutôt qu'après toute la phase explorateur, qui peut durer
    plusieurs minutes. Rien n'est configuré, donc aucune table de hachage
    n'est allouée : le moteur est seulement lancé, interrogé, puis arrêté.
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
    Met en forme une ligne renvoyée par le moteur : premier coup, score,
    valeur numérique pour le trait, profondeur atteinte et variante
    principale complète, en UCI et en notation algébrique numérotée.
    """
    pv = list(info.get("pv") or [])
    try:
        pv_san = plateau.variation_san(pv)
    except ValueError:
        # Variante que python-chess refuse de rejouer : on garde l'UCI brut
        # plutôt que de perdre l'information.
        pv_san = " ".join(m.uci() for m in pv)
    return {
        "san": plateau.san(pv[0]),
        "uci": pv[0].uci(),
        "score": formater_score(info["score"]),
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
    Évalue les premiers demi-coups de la partie en multipv.

    Pour chaque position, les `multipv` meilleurs coups sont demandés, avec
    leur variante principale complète. Si le coup effectivement joué ne
    figure pas dans cette liste, une seconde analyse restreinte à ce seul
    coup fournit son évaluation et sa variante, et donc l'écart réel avec
    le premier choix du moteur.
    """
    verifier_moteur(binaire)
    limite = chess.engine.Limit(depth=profondeur)
    plateau = partie.board()
    resultats: list[dict] = []
    coups = list(partie.mainline_moves())
    # Zéro signifie "toute la partie" ; sinon on borne au nombre réel de
    # demi-coups pour que le compteur affiché soit exact.
    if demicoups <= 0 or demicoups > len(coups):
        demicoups = len(coups)

    # Lancement et erreurs de lancement : voir lancer_moteur.
    moteur = lancer_moteur(binaire)

    try:
        moteur.configure({"Threads": fils, "Hash": hachage})
        # Chances de gain, nulle et perte : un moteur qui ne connaît pas
        # cette option laisse simplement la colonne vide.
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
                # Coup nul, "--" dans le PGN : le trait passe sans qu'aucune
                # pièce ne bouge. Ce n'est pas un coup des échecs et le
                # protocole UCI ne sait pas le restreindre : la recherche
                # limitée à "0000" renvoyait un score sans rapport avec lui,
                # d'où une évaluation et un écart inventés. La ligne est
                # gardée, avec les meilleurs coups de la position, mais le
                # coup joué n'est pas évalué.
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
                ecart = meilleurs[0]["valeur_trait"] - eval_joue["valeur_trait"]

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
    finally:
        # Arrêt sûr dans tous les cas : voir fermer_moteur.
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
# Fichier de synthèse
# ===========================================================================

def _cellule(valeur, gabarit="%.1f") -> str:
    """Formate une valeur numérique, ou renvoie un tiret si elle est absente."""
    return "-" if valeur is None else gabarit % valeur


def _ecart(ecart: float | None) -> str:
    """
    Cellule "Écart cp" du tableau Stockfish.

    Un écart absent donne un tiret. À partir de SEUIL_ECART_MAT, l'écart
    vient d'un mat ramené à une valeur bornée, que le coup joué manque un
    mat ou qu'il en concède un : la cellule porte "mat" au lieu d'un
    nombre de centipions qui n'aurait aucun sens, les colonnes Éval et
    1er donnant les deux scores.
    """
    if ecart is None:
        return "-"
    if ecart >= SEUIL_ECART_MAT:
        return "mat"
    return "%.0f" % ecart


def _gnp(wdl: dict | None, pour_noirs: bool = False) -> str:
    """Gain, nulle et perte en pour cent arrondi, des Blancs ou des Noirs."""
    if not wdl:
        return "-"
    gain, nulle, perte = wdl["gain"], wdl["nulle"], wdl["perte"]
    if pour_noirs:
        gain, perte = perte, gain
    return "%d/%d/%d" % (round(gain / 10), round(nulle / 10),
                         round(perte / 10))


def materiel_hors_pions(plateau: chess.Board) -> int:
    """Matériel hors pions et rois des deux camps réunis."""
    return sum(VALEUR_PIECES.get(c.lower(), 0) for c in plateau.board_fen())


def reperes_phase(partie: chess.pgn.Game) -> list[str]:
    """
    Repères objectifs de changement de phase sur la ligne principale :
    roque de chaque camp, disparition des dames, entrée en finale selon
    SEUIL_FINALE. Ils situent les transitions, l'analyste en juge.
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
    Rejoue une variante UCI depuis la position et la rend en notation
    algébrique numérotée, limitée à `longueur` demi-coups (0 = tout).
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


def ecrire_synthese(chemin: pathlib.Path, partie: chess.pgn.Game,
                    source: str, consignes: str | None,
                    explorateur: dict | None, motif_sans_explorateur: str | None,
                    stockfish: dict | None, longueur_pv: int,
                    libelle_base: str = "maîtres",
                    filtres: dict[str, str] | None = None,
                    annexes: list[str] | None = None,
                    pgn_complete: bool = False) -> None:
    """
    Assemble le fichier de synthèse en markdown, dans l'ordre attendu.

    `libelle_base` nomme la base interrogée dans les titres et le texte ;
    sa valeur par défaut redonne mot pour mot la synthèse de la base
    maîtres. `filtres`, fourni seulement pour la base Lichess, est
    reproduit dans la section 2 afin que l'analyste sache sur quelle
    population de parties portent les fréquences. `annexes` ajoute à la
    section 5 les fichiers produits en plus, contexte.md par exemple, et
    `pgn_complete` signale un partie.pgn aux en-têtes complétés.
    """
    out: list[str] = []
    a = out.append

    identifiant = partie.headers.get("Site", "").rstrip("/").split("/")[-1]
    a("# Dossier d'analyse : %s"
      % (nettoyer_valeur(identifiant) or "partie locale"))
    a("")
    a("Collecte du %s. Source : `%s`."
      % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         nettoyer_valeur(source)))
    a("Ce fichier ne contient aucune analyse, uniquement des données "
      "collectées.")
    a("")

    # -- 0. Consignes d'analyse, si fournies --------------------------------
    if consignes is not None:
        a("## Consignes d'analyse")
        a("")
        a("Les consignes ci-dessous accompagnent les données : elles "
          "décrivent l'analyse attendue à partir de ce dossier.")
        a("")
        a(consignes.strip())
        a("")

    # -- 1. En-têtes et coups de la partie ----------------------------------
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
    # La ligne principale est reproduite sans commentaires ni variantes,
    # afin que ce seul fichier suffise à l'analyse. Le PGN brut, avec ses
    # éventuels commentaires d'origine, reste dans partie.pgn.
    exporteur = chess.pgn.StringExporter(headers=False, comments=False,
                                         variations=False, columns=78)
    a("```")
    a(partie.accept(exporteur).strip())
    a("```")
    a("")
    # Repères de phase, calculés sur les roques et le matériel : ils
    # situent les fins de phase que l'analyste doit commenter.
    a("Repères de phase, indicatifs :")
    a("")
    for ligne in reperes_phase(partie):
        a(ligne)
    a("")

    # -- 2. Sortie de théorie -----------------------------------------------
    a("## 2. Explorateur %s, sortie de théorie" % libelle_base)
    a("")
    if explorateur is None:
        a("Collecte de l'explorateur non effectuée : %s."
          % (motif_sans_explorateur or "désactivée"))
        a("")
    else:
        if filtres:
            # Base Lichess : les fréquences dépendent entièrement de la
            # population filtrée, l'analyste doit la connaître.
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
            # Dernière ouverture nommée avant la sortie : elle situe, pour
            # l'analyste, la ligne théorique que la partie vient de quitter.
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
    if stockfish is None:
        a("Aucune évaluation moteur dans ce dossier. L'évaluation de la "
          "partie est à la charge de l'analyste.")
        a("")
    else:
        a("Moteur : `%s`, profondeur %d, multipv %d, %d demi-coups "
          "couverts sur %d. Les évaluations sont exprimées **du point de "
          "vue des Blancs**. L'écart est exprimé en centipions **du point "
          "de vue du joueur au trait** : positif, il mesure ce que le coup "
          "joué perd par rapport au premier choix du moteur."
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
              "trois meilleurs coups de la position restant donnés.")
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

        # Les variantes principales, rejouées depuis chaque position, pour
        # que l'analyste dispose de lignes concrètes calculées par le
        # moteur et n'ait pas à les inventer. Les variantes complètes sont
        # dans stockfish/evaluations.json.
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

        # Palmarès : les coups qui coûtent le plus, par camp, avec ce qu'il
        # fallait jouer et la FEN, matière directe des commentaires
        # obligatoires et des positions à revoir.
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
                # À partir de SEUIL_ECART_MAT, l'écart vient d'un mat ramené
                # à une valeur bornée : le chiffre n'a plus de sens, les
                # scores parlent d'eux-mêmes.
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

    # -- 4. Positions non exploitables --------------------------------------
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

    # -- 5. Rappel des données brutes ---------------------------------------
    a("## 5. Données brutes de l'archive")
    a("")
    if pgn_complete:
        a("- `partie.pgn` : la partie avec ses en-têtes complétés, "
          "réexportée par python-chess, commentaires d'origine compris.")
    else:
        a("- `partie.pgn` : le PGN source, avec ses commentaires d'origine.")
    for annexe in annexes or []:
        a(annexe)
    a("- `explorateur/NNN-<uci>.json` : une réponse brute par demi-coup "
      "interrogé, numérotée dans l'ordre de la partie.")
    if stockfish is not None:
        a("- `stockfish/evaluations.json` : les évaluations moteur "
          "complètes, avec la variante principale entière de chaque coup, "
          "en UCI et en notation algébrique.")
    a("- `collecte.json` : les paramètres exacts de cette collecte.")
    a("")

    ecrire_texte(chemin, "\n".join(out) + "\n")


# ===========================================================================
# Archive finale
# ===========================================================================

def chemin_archive(dossier: pathlib.Path) -> pathlib.Path:
    """
    Chemin de l'archive d'un dossier de travail : son nom suivi de ".zip".

    Le nom est construit par ajout et non par with_suffix(), qui remplace
    tout ce qui suit le dernier point : pour un PGN nommé
    "partie-2026.11.18.pgn", le dossier "analyse-partie-2026.11.18-..."
    donnait "analyse-partie-2026.11.zip", alors que shutil.make_archive
    écrit bien "<dossier>.zip".
    """
    return dossier.with_name(dossier.name + ".zip")


def archiver(dossier: pathlib.Path, garder: bool) -> pathlib.Path:
    """
    Compresse le dossier de travail en zip, le vérifie, puis le supprime.

    Le dossier n'est détruit que si l'archive relit sans erreur et contient
    bien la synthèse. En cas de doute, tout est conservé et signalé.

    L'archive est d'abord écrite sous un nom provisoire,
    ".<dossier>.partiel.zip", à côté du dossier ; elle ne prend son nom
    définitif qu'une fois vérifiée. Une interruption (Ctrl-C) ou un échec
    ne laisse donc jamais, sous le nom d'une archive, un zip tronqué :
    l'archive provisoire est retirée, le dossier de travail reste.
    """
    archive = chemin_archive(dossier)
    if archive.exists():
        raise SystemExit("L'archive %s existe déjà, dossier conservé."
                         % archive)

    # Base du nom provisoire : shutil.make_archive y ajoute ".zip". Les
    # chemins rangés dans le zip ne dépendent que de base_dir, ils restent
    # ceux du dossier de travail.
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

        # Renommage dans le même répertoire : l'archive apparaît d'un
        # coup, complète et vérifiée.
        try:
            partielle.replace(archive)
        except OSError as err:
            raise SystemExit("Archive valide mais impossible à renommer en "
                             "%s, dossier conservé : %s"
                             % (archive, err)) from err
    except BaseException:
        # Tout arrêt avant le renommage, Ctrl-C compris, retire l'archive
        # provisoire puis remonte tel quel : le dossier de travail, lui,
        # est conservé pour diagnostic.
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
# Ligne de commande
# ===========================================================================

EXEMPLES = """\
exemples d'utilisation
----------------------

  Première installation, une seule fois :

      %s
      ./collecte-partie.py --installer-venv
      ./collecte-partie.py --installer-catalogue

  Relancer --installer-catalogue de temps en temps met le catalogue des
  ouvertures à jour.

  Usage courant, sur un PGN local :

      ./collecte-partie.py ma-partie.pgn

  Sur une partie Lichess, par URL ou par identifiant :

      ./collecte-partie.py https://lichess.org/xvoiNy2C
      ./collecte-partie.py xvoiNy2C

  Joindre vos consignes d'analyse en tête de la synthèse, pour n'avoir
  qu'un seul fichier à fournir :

      ./collecte-partie.py ma-partie.pgn --consignes ~/prompt-annotation.md

  Usage hors du projet d'analyse, sans aucune question, ou avec tous vos
  noms de joueur pour que le camp soit déduit des en-têtes :

      ./collecte-partie.py ma-partie.pgn --sans-questions
      ./collecte-partie.py ma-partie.pgn --pseudos MonPseudo,AutrePseudo

  Descendre aussi loin que la base répond, sans aucun seuil :

      ./collecte-partie.py ma-partie.pgn --jusqu-a-epuisement

  La base de tous les joueurs Lichess est interrogée par défaut, avec les
  filtres de https://lichess.org/opening. La restreindre à certaines
  cadences et tranches de classement, ou interroger la base maîtres :

      ./collecte-partie.py ma-partie.pgn \\
          --cadences rapid,classical,correspondence --classements 0,1000
      ./collecte-partie.py ma-partie.pgn --base maitres

  Couvrir les dix premiers coups quelle que soit la fréquence des coups
  joués, ou au contraire s'arrêter dès la première sortie de théorie :

      ./collecte-partie.py ma-partie.pgn --coups-min 10
      ./collecte-partie.py ma-partie.pgn --coups-min 0

  Moteur seul, sans réseau ni jeton :

      ./collecte-partie.py ma-partie.pgn --sans-explorateur

  Conserver le dossier de travail à côté de l'archive :

      ./collecte-partie.py ma-partie.pgn --garder-dossier

  Utiliser votre propre modèle de prompt, ou ne pas écrire de prompt :

      ./collecte-partie.py ma-partie.pgn --prompt ~/mon-modele.txt
      ./collecte-partie.py ma-partie.pgn --sans-prompt

  Moteur plus profond, ou limité aux quinze premiers coups :

      ./collecte-partie.py ma-partie.pgn --profondeur 22
      ./collecte-partie.py ma-partie.pgn --coups-stockfish 15

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
  crée un environnement virtuel dédié (%s par défaut) et y installe le
  module. Le script s'y relance ensuite tout seul, vous pouvez continuer à
  l'appeler avec le python du système.

  Le catalogue des ouvertures nommées de Lichess (domaine public, CC0)
  est gardé en local dans %s, installé et mis à jour par
  --installer-catalogue. Il n'est pas requis avec --sans-explorateur.

  Le jeton personnel Lichess est lu dans %s, en mode 600, ce fichier ne
  contenant que le jeton. Il n'apparaît jamais dans la sortie, ni dans les
  fichiers produits, ni dans la ligne de commande.

  Votre pseudo, votre cadence habituelle et votre niveau sont demandés
  une seule fois, au premier lancement sur un terminal, puis gardés dans
  %s, que vous pouvez modifier à la main.

  Aucune autre dépendance : le HTTP passe par urllib de la bibliothèque
  standard, l'archive par zipfile. Le paquet stockfish est obligatoire,
  le moteur est piloté en UCI.
""" % (CMD_PAQUET_VENV, CMD_PAQUET_VENV, CMD_PAQUET_STOCKFISH,
       VENV_DEFAUT, CATALOGUE_DEFAUT, JETON_DEFAUT, REGLAGES_DEFAUT)


def valider_liste(p: argparse.ArgumentParser, option: str, valeur: str,
                  admises: tuple[str, ...]) -> str:
    """
    Contrôle une liste séparée par des virgules et la renvoie normalisée.

    La casse est tolérée à la saisie ("ultrabullet" est accepté) mais la
    valeur transmise reprend l'orthographe exacte de l'API. Les espaces
    parasites et les doublons sont retirés, et la liste est remise dans
    l'ordre de l'énumération, afin que collecte.json et la synthèse
    restent comparables d'une collecte à l'autre. Une valeur inconnue est
    refusée ici, avant toute création de dossier, plutôt que d'en découvrir
    l'effet au premier demi-coup interrogé.
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
    """Définit et lit les options de la ligne de commande."""
    p = argparse.ArgumentParser(
        prog="collecte-partie.py",
        description="Collecte le matériel d'analyse d'une partie d'échecs : "
                    "PGN, statistiques de l'explorateur Lichess (base de "
                    "tous les joueurs, ou base maîtres avec --base "
                    "maitres) pour déterminer la sortie de théorie, et "
                    "évaluations "
                    "Stockfish de la partie. Ne produit aucune "
                    "analyse.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXEMPLES)

    p.add_argument("source", nargs="?",
                   help="fichier PGN local, URL Lichess, ou identifiant de "
                        "partie à huit caractères")

    g = p.add_argument_group("environnement virtuel")
    g.add_argument("--installer-venv", action="store_true",
                   help="crée l'environnement virtuel s'il manque, y "
                        "installe python-chess, puis quitte")
    g.add_argument("--venv", default=VENV_DEFAUT, metavar="CHEMIN",
                   help="emplacement de l'environnement virtuel "
                        "(défaut : %(default)s)")

    g = p.add_argument_group("questions de démarrage")
    g.add_argument("--sans-questions", action="store_true",
                   help="ne pose aucune question, ni camp ni contexte, pour "
                        "un usage hors du projet d'analyse ; implicite hors "
                        "terminal interactif")
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
    g.add_argument("--consignes", metavar="FICHIER",
                   help="fichier texte ou markdown inséré tel quel en tête "
                        "de la synthèse, sous le titre \"Consignes "
                        "d'analyse\", à la place des questions de contexte")
    g.add_argument("--garder-dossier", action="store_true",
                   help="ne supprime pas le dossier de travail après "
                        "création de l'archive")
    g.add_argument("--prompt", metavar="FICHIER",
                   help="modèle du prompt d'analyse, écrit à côté de "
                        "l'archive sous le nom <archive>%s (défaut : %s à "
                        "côté du script)" % (PROMPT_SUFFIXE, PROMPT_MODELE))
    g.add_argument("--sans-prompt", action="store_true",
                   help="n'écrit pas le prompt d'analyse")

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
                        "de fréquence, 0 pour désactiver ce critère "
                        "(défaut : %(default)s)")
    g.add_argument("--jusqu-a-epuisement", action="store_true",
                   help="ignore les deux seuils et interroge la base tant "
                        "qu'elle répond, l'arrêt n'ayant alors lieu que sur "
                        "une erreur HTTP ou sur une position absente de la "
                        "base")
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
                   help="profondeur de recherche (défaut : %(default)s)")
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

    if (options.installer_venv or options.installer_catalogue
            or options.purge_reglages):
        return options
    if not options.source:
        p.error("il faut un fichier PGN, une URL ou un identifiant de partie")
    if options.prompt and options.sans_prompt:
        p.error("--prompt et --sans-prompt s'excluent")
    # nan et inf sont des flottants valides pour argparse, mais nan échappe
    # à toute comparaison et time.sleep() refuse l'un comme l'autre : on
    # les écarte ici, avant toute création de dossier.
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
    if options.coups_stockfish < 0:
        p.error("--coups-stockfish doit valoir 0 ou plus")
    if options.coups_min < 0:
        p.error("--coups-min doit valoir 0 ou plus")
    # Sans --pseudos, la valeur reste None : les pseudos viendront alors
    # des réglages. L'option, quand elle est donnée, doit en porter un.
    if options.pseudos is not None:
        options.pseudos = decouper_pseudos(options.pseudos)
        if not options.pseudos:
            p.error("--pseudos : liste vide")
    # L'évaluation du moteur fait partie de toute collecte depuis la
    # version 4.0.0 : les options --avec-stockfish et --sans-stockfish ont
    # été retirées. Le reste du script continue de lire avec_stockfish,
    # désormais toujours vrai.
    options.avec_stockfish = True
    if options.seuil_frequence < 0 or options.seuil_frequence > 100:
        p.error("--seuil-frequence doit être compris entre 0 et 100")
    if options.longueur_pv < 0:
        p.error("--longueur-pv doit valoir 0 ou plus")
    if options.base == "maitres":
        # Même principe que pour les options moteur : un filtre que la base
        # maîtres ne connaît pas serait ignoré en silence, on le refuse.
        for nom in ("cadences", "classements"):
            if getattr(options, nom) is not None:
                p.error("--%s n'a d'effet qu'avec --base lichess" % nom)
    else:
        # Les valeurs par défaut ne sont posées qu'ici, et seulement pour la
        # base Lichess : collecte.json enregistre ainsi les filtres
        # réellement appliqués, et rien pour la base maîtres.
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
    """Point d'entrée : orchestre la collecte et écrit la synthèse."""
    global DEBUG, JETON_COURANT

    options = analyser_arguments(argv)
    DEBUG = options.debug

    # -- Environnement virtuel ----------------------------------------------
    if options.installer_venv:
        installer_venv(options.venv)
        return 0
    # -- Purge des réglages -------------------------------------------------
    # Placée avant la relance : elle ne demande ni python-chess ni partie.
    if options.purge_reglages:
        purger_reglages(options.reglages)
        return 0
    if not CHESS_DISPONIBLE:
        relancer_dans_venv(options.venv, argv)

    # -- Catalogue des ouvertures, installation ou mise à jour ---------------
    # Placé après la relance : le catalogue est validé avec python-chess.
    if options.installer_catalogue:
        installer_catalogue(options.catalogue, options.delai)
        return 0

    # -- Consignes d'analyse, lues avant tout pour échouer tôt --------------
    consignes = None
    if options.consignes:
        chemin_consignes = pathlib.Path(os.path.expanduser(options.consignes))
        if not chemin_consignes.is_file():
            raise SystemExit("Fichier de consignes introuvable : %s"
                             % chemin_consignes)
        consignes = lire_texte(chemin_consignes, "consignes")

    # -- Réglages de l'utilisateur, lus tôt eux aussi -----------------------
    reglages = lire_reglages(options.reglages)

    # -- Modèle du prompt, lu et contrôlé avant la collecte -----------------
    # Un modèle désigné par --prompt doit exister. Le modèle par défaut,
    # lui, peut manquer quand le script a été copié seul : la collecte se
    # fait alors sans prompt, et le journal le dit.
    modele_prompt = None
    if not options.sans_prompt:
        fichier_modele = chemin_modele(options.prompt)
        if fichier_modele.is_file():
            modele_prompt = lire_texte(fichier_modele, "modèle de prompt")
            verifier_modele(modele_prompt, str(fichier_modele))
        elif options.prompt:
            raise SystemExit("Modèle de prompt introuvable : %s"
                             % fichier_modele)
        else:
            journal("Attention : modèle de prompt introuvable (%s), aucun "
                    "prompt ne sera écrit. Voir --prompt et --sans-prompt."
                    % fichier_modele)

    # -- Récupération du PGN ------------------------------------------------
    # Encodage retenu pour le PGN et remarques de décodage, consignés dans
    # collecte.json et, s'il y a lieu, dans la section 5 de la synthèse.
    encodage_pgn = "utf-8"
    remarques_pgn: list[str] = []
    chemin_local = pathlib.Path(os.path.expanduser(options.source))
    if chemin_local.is_file():
        journal("Lecture du PGN local : %s" % chemin_local)
        texte_pgn, encodage_pgn, remarques_pgn = lire_fichier_texte(
            chemin_local, "PGN")
        etiquette = etiquette_sure(chemin_local.stem)
        if etiquette != chemin_local.stem:
            journal("Nom du dossier assaini : %s" % etiquette)
    else:
        identifiant = extraire_id(options.source)
        if identifiant is None:
            # Hors URL, un point, une barre oblique ou un tilde trahissent
            # un chemin : le fichier visé n'existe pas, autant le dire.
            if (not options.source.strip().startswith(("http://",
                                                        "https://"))
                    and any(c in options.source for c in "./~")):
                raise SystemExit("Fichier PGN introuvable : %s"
                                 % chemin_local)
            if options.source.strip().startswith(("http://", "https://")):
                # Message propre aux URL : dire la forme attendue vaut
                # mieux qu'un refus général.
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

    # -- Vérifications préalables, pour échouer avant d'avoir rien écrit ----
    catalogue = None
    motif_sans_explorateur = None
    if options.sans_explorateur:
        motif_sans_explorateur = "désactivée par --sans-explorateur"
    elif partie.board().fen() != chess.STARTING_FEN:
        # La base maîtres n'est interrogeable qu'à partir de la position
        # initiale ; une partie "from position" n'a pas de sens ici.
        motif_sans_explorateur = ("la partie ne commence pas à la position "
                                  "initiale, l'explorateur est inapplicable")
        journal("Explorateur ignoré : %s." % motif_sans_explorateur)
    else:
        # Le jeton n'est lu qu'ici et n'est ni écrit ni journalisé.
        JETON_COURANT = lire_jeton(options.jeton_fichier)
        # Catalogue chargé avant toute écriture : absent ou abîmé, on
        # s'arrête ici en donnant la commande à lancer.
        catalogue = lire_catalogue(options.catalogue)
        journal("Catalogue des ouvertures : %s positions connues, du %s"
                % (catalogue.meta.get("connues"), catalogue.meta.get("date")))
    if options.avec_stockfish:
        verifier_moteur(options.stockfish)
        # Les options moteur sont contrôlées ici, auprès du moteur, et non
        # à sa configuration, qui n'a lieu qu'après la phase explorateur.
        verifier_options_moteur(options.stockfish, options.fils,
                                options.hachage, options.multipv)

    # -- Questions de démarrage ---------------------------------------------
    # Posées après les vérifications, pour ne rien demander à qui va de
    # toute façon échouer, et avant la collecte, qui peut durer.
    camp = None
    contexte = None
    interactif = questions_possibles(options.sans_questions)
    if interactif:
        # Réglages manquants : demandés ici, une fois pour toutes, avant
        # les questions propres à la partie.
        completer_reglages(options.reglages, reglages, options.pseudos)
    # --pseudos l'emporte sur les réglages. La liste retenue remplace
    # l'option : collecte.json enregistre ainsi les pseudos réellement
    # utilisés, et elle peut être vide.
    if options.pseudos is None:
        options.pseudos = decouper_pseudos(reglage(reglages, "pseudos"))
    if interactif:
        journal("Questions de démarrage, Entrée retient la valeur proposée.")
        camp = completer_entetes(partie, options.pseudos)
        if consignes is None:
            contexte = recueillir_contexte(
                partie, camp, analyser_cadence(reglage(reglages, "cadence")))
            consignes = contexte
    else:
        journal("Questions de démarrage sautées : %s."
                % ("option --sans-questions" if options.sans_questions
                   else "terminal non interactif"))

    # -- Création du dossier de travail -------------------------------------
    # Le nom est horodaté à la seconde ; deux lancements dans la même
    # seconde, ou un dossier laissé par un échec précédent, reçoivent un
    # suffixe plutôt qu'une erreur.
    horodatage = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = pathlib.Path(options.sortie) / ("analyse-%s-%s"
                                           % (etiquette, horodatage))
    dossier = base
    suffixe = 1
    while True:
        try:
            if not chemin_archive(dossier).exists():
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
            # Le PGN fourni est gardé tel quel ; partie.pgn reprend la
            # partie, réexportée par python-chess, en-têtes complétés.
            ecrire_texte(dossier / "partie-origine.pgn", texte_pgn)
            ecrire_texte(dossier / "partie.pgn", str(partie) + "\n")
            annexes.append("- `partie-origine.pgn` : le PGN tel que "
                           "fourni, avant ajout des balises %s."
                           % ", ".join(camp["modifiees"]))
        else:
            ecrire_texte(dossier / "partie.pgn", texte_pgn)
        if remarques_pgn:
            # Le PGN gardé dans l'archive n'est plus, octet pour octet, le
            # fichier fourni : l'analyste doit le savoir.
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

    # -- Explorateur --------------------------------------------------------
    # Base et filtres sont fixés même sans collecte, pour que le titre de la
    # section 2 nomme la base demandée dans tous les cas.
    base = BASES_EXPLORATEUR[options.base]
    filtres = None
    if options.base == "lichess":
        # recentGames à 0, comme topGames : seules les statistiques servent,
        # inutile de rapatrier des références de parties.
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
    resume_stockfish = None
    if options.avec_stockfish:
        resume_stockfish = collecter_stockfish(
            partie, dossier, options.stockfish,
            options.coups_stockfish * 2, options.profondeur,
            options.multipv, options.fils, options.hachage)

    # -- Trace des paramètres, expurgée de toute donnée sensible ------------
    parametres = dict(vars(options))
    parametres["jeton_present"] = JETON_COURANT is not None
    parametres["catalogue_utilise"] = (catalogue.meta if catalogue is not None
                                       else None)
    parametres["camp"] = camp
    parametres["contexte_recueilli"] = contexte is not None
    parametres["pgn_encodage"] = encodage_pgn
    parametres["pgn_remarques"] = remarques_pgn
    # Nom du prompt écrit à côté de l'archive, ou rien s'il n'y en a pas.
    parametres["prompt_ecrit"] = (dossier.name + PROMPT_SUFFIXE
                                  if modele_prompt is not None else None)
    ecrire_texte(dossier / "collecte.json",
                 json.dumps(parametres, ensure_ascii=False, indent=1,
                            default=str))

    # -- Synthèse -----------------------------------------------------------
    synthese = dossier / "synthese.md"
    ecrire_synthese(synthese, partie, options.source, consignes,
                    resume_explorateur, motif_sans_explorateur,
                    resume_stockfish, options.longueur_pv,
                    base["libelle"], filtres, annexes,
                    bool(camp and camp["modifiees"]))
    journal("Synthèse écrite : %s" % synthese)

    # -- Archive et nettoyage -----------------------------------------------
    archive = archiver(dossier, options.garder_dossier)

    # -- Prompt d'analyse, écrit à côté de l'archive ------------------------
    # Après l'archivage : un échec ne laisse pas un prompt sans archive. Le
    # prompt n'entre pas dans le zip, il se colle dans la conversation.
    if modele_prompt is not None:
        camp_joueur = ((camp or {}).get("camp")
                       or deduire_camp(partie, options.pseudos))
        niveau = analyser_niveau(reglage(reglages, "niveau")) or 0
        habituelle = (analyser_cadence(reglage(reglages, "cadence"))
                      or dict(CADENCE_INCONNUE))
        conditions = {
            "STOCKFISH": resume_stockfish is not None,
            "EXPLORATEUR": resume_explorateur is not None,
            "BASE_LICHESS": options.base == "lichess",
            "BASE_MAITRES": options.base == "maitres",
            "REPONSES": contexte is not None,
            "CONSIGNES_LIBRES": bool(options.consignes),
            "CAMP_CONNU": camp_joueur is not None,
            "PSEUDO_CONNU": bool(options.pseudos),
            "NIVEAU_DECLARE": bool(niveau),
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
        }
        prompt = archive.with_name(dossier.name + PROMPT_SUFFIXE)
        try:
            ecrire_texte(prompt, rendre_modele(
                modele_prompt, conditions, valeurs,
                str(chemin_modele(options.prompt))))
            journal("Prompt d'analyse écrit : %s, à coller dans la "
                    "conversation, l'archive en pièce jointe." % prompt)
        except OSError as err:
            # L'archive est faite : un prompt impossible à écrire ne doit
            # pas faire échouer la collecte.
            journal("Attention : prompt non écrit (%s) : %s" % (prompt, err))

    annoncer_archive(archive)
    return 0


if __name__ == "__main__":
    # Avant tout affichage, y compris celui de --help par argparse.
    configurer_console()
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrompu.\n")
        raise SystemExit(130) from None
    except SystemExit as fin:
        # Un message d'arrêt est affiché ici plutôt que par l'interpréteur,
        # afin d'en retirer les caractères de contrôle. Le texte et le code
        # de retour, 1, restent ceux que produisait l'interpréteur.
        if isinstance(fin.code, str):
            sys.stderr.write(RE_CONTROLES.sub("", fin.code) + "\n")
            raise SystemExit(1) from None
        raise
    except Exception as err:  # noqa: BLE001 - dernier recours volontaire
        # Aucune exception ne doit sortir brute : on affiche un message
        # expurgé du jeton, et la trace complète, elle aussi expurgée,
        # seulement sur --debug.
        if DEBUG:
            sys.stderr.write(expurger(traceback.format_exc(), JETON_COURANT))
        else:
            sys.stderr.write("Erreur inattendue (%s) : %s\n"
                             "Relancez avec --debug pour la trace complète.\n"
                             % (type(err).__name__,
                                expurger(str(err), JETON_COURANT)))
        raise SystemExit(1) from None
