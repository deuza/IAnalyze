#!/bin/sh
# ===========================================================================
# test-app.sh : tests de ianalyze.py, sous macOS et sous Debian
#
# Ce script joue tous les tests du projet, décrits un par un dans
# TESTS.md, puis écrit un rapport que vous pouvez renvoyer tel quel.
#
#     sh test-app.sh             tests hors réseau : encodages, archive,
#                                réglages, cadence, moteur, vérification
#                                du PGN rendu. Ni jeton ni Lichess.
#                                Environ 3 minutes sur un Mac récent, 6
#                                sur un Raspberry Pi.
#     sh test-app.sh --reseau    les mêmes, puis les tests qui demandent le
#                                réseau et votre jeton : catalogue,
#                                explorateur. Environ 3 minutes de plus.
#     sh test-app.sh --reseau PARTIE
#                                de même, avec en plus T24, qui télécharge
#                                une partie depuis Lichess. PARTIE est
#                                l'identifiant ou l'adresse de n'importe
#                                quelle partie du site. Le dépôt n'en
#                                fournit aucune : sans elle, T24 est sauté.
#
# Rien n'est écrit dans le dépôt, sauf le rapport, ni dans vos
# répertoires : tout se passe dans un répertoire temporaire, supprimé à
# la fin. Les tests désignent
# leur propre fichier de réglages et, avec --reseau, leur propre catalogue :
# les vôtres ne sont ni lus ni modifiés.
#
# Votre jeton, avec --reseau : ce script ne l'affiche pas, ne le copie pas
# et ne le passe dans aucune ligne de commande. C'est ianalyze.py
# qui le lit. Le script ne s'en sert lui-même que comme fichier de motifs
# pour grep (option -f), afin de vérifier qu'il n'apparaît ni dans une
# archive ni dans le rapport. S'il était trouvé dans le rapport, celui-ci
# ne serait pas écrit.
#
# Charge sur Lichess, avec --reseau : environ 70 requêtes à l'explorateur,
# espacées de 2 secondes par ianalyze.py, 10 fichiers du catalogue chez
# GitHub et, si vous donnez une partie, 2 exports de cette partie.
#
# Variables facultatives :
#
#     VENV=/chemin/du/venv       environnement virtuel de python-chess
#     STOCKFISH=/chemin/binaire  moteur utilisé par les tests du moteur
#     JETON=/chemin/du/fichier   fichier du jeton (défaut : ~/.lichess_token)
#     GARDER=1                   conserve le répertoire temporaire
#
# Le script est écrit en shell POSIX : pas de tableau, pas de [[ ]], pas de
# "local". Il a été vérifié avec dash et bash, ainsi qu'avec deux outils
# de contrôle : shellcheck et checkbashisms.
# ===========================================================================

# Trois avis de shellcheck sont écartés pour tout le fichier, à dessein :
# SC2086, les variables d'options ($O, $P, $MOTEUR, $EXPL) devant être
# découpées en plusieurs mots ; SC2012, ls ne servant ici qu'à afficher les
# droits d'un fichier au nom connu ; SC2016, les accents graves cherchés
# dans la synthèse étant du texte markdown et non une commande.
# shellcheck disable=SC2086,SC2012,SC2016

set -u

# --- Arguments --------------------------------------------------------------

RESEAU=0
PARTIE=""
# Vrai juste après --reseau : l'argument suivant, s'il n'est pas une
# option, est la partie de T24.
APRES_RESEAU=0
for argument in "$@"; do
    if [ "$APRES_RESEAU" = 1 ]; then
        APRES_RESEAU=0
        case $argument in
            -*) ;;
            *)
                PARTIE=$argument
                continue
                ;;
        esac
    fi
    case $argument in
        --reseau)
            RESEAU=1
            APRES_RESEAU=1
            ;;
        -h | --help)
            sed -n '2,/^# =====.*=$/p' "$0" | sed -n '2,$p' | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Argument inconnu : $argument" >&2
            echo "Usage : sh test-app.sh [--reseau [PARTIE]]" >&2
            exit 2
            ;;
    esac
done


# --- Emplacements -----------------------------------------------------------

DEPOT=$(pwd)
SCRIPT="$DEPOT/ianalyze.py"

if [ ! -f "$SCRIPT" ]; then
    echo "ianalyze.py introuvable dans $DEPOT." >&2
    echo "Lancez ce script depuis le répertoire du dépôt." >&2
    exit 2
fi

SYSTEME=$(uname -s)

# Environnement virtuel par défaut, selon la plateforme : les mêmes valeurs
# que dans ianalyze.py.
if [ -z "${VENV:-}" ]; then
    VENV="$HOME/.local/share/IAnalyze/venv"
fi
PYVENV="$VENV/bin/python3"

if ! "$PYVENV" -c "import chess" >/dev/null 2>&1; then
    echo "python-chess introuvable dans $VENV." >&2
    echo "Créez l'environnement : ./ianalyze.py --installer-venv" >&2
    echo "ou indiquez-le : VENV=/chemin sh test-app.sh" >&2
    exit 2
fi

# Moteur : celui que vous indiquez, sinon celui du PATH, sinon les
# emplacements habituels de Homebrew et de Debian.
if [ -z "${STOCKFISH:-}" ]; then
    STOCKFISH=$(command -v stockfish 2>/dev/null || true)
    for candidat in /opt/homebrew/bin/stockfish /usr/local/bin/stockfish \
                    /usr/games/stockfish; do
        if [ -z "$STOCKFISH" ] && [ -x "$candidat" ]; then
            STOCKFISH=$candidat
        fi
    done
fi

# Sans moteur, aucune collecte n'aboutit : le moteur est obligatoire depuis
# la version 4.0.0. Mieux vaut s'arrêter ici que d'afficher des centaines
# d'échecs qui ne disent rien du script.
if [ -z "$STOCKFISH" ] || [ ! -x "$STOCKFISH" ]; then
    echo "Stockfish introuvable : les tests ne peuvent pas tourner sans lui." >&2
    echo "Installez-le, ou indiquez-le : STOCKFISH=/chemin sh test-app.sh" >&2
    exit 2
fi

JETON=${JETON:-$HOME/.lichess_token}
if [ "$RESEAU" = 1 ] && [ ! -f "$JETON" ]; then
    echo "Fichier de jeton introuvable : $JETON" >&2
    echo "Indiquez-le : JETON=/chemin sh test-app.sh --reseau" >&2
    exit 2
fi
# Identifiant de la partie de T24, tiré de ce que vous avez donné par la
# fonction même du script : une adresse et un identifiant sont admis.
ID_PARTIE=""
if [ -n "$PARTIE" ]; then
    ID_PARTIE=$(SCRIPT="$SCRIPT" PARTIE="$PARTIE" "$PYVENV" -c '
import importlib.util
import os

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
print(cp.extraire_id(os.environ["PARTIE"]) or "")
' 2>/dev/null)
    rm -rf "$DEPOT/__pycache__"
    if [ -z "$ID_PARTIE" ]; then
        echo "Ce n'est pas une partie de Lichess : $PARTIE" >&2
        echo "Donnez son identifiant, 8 caractères, ou son adresse :" >&2
        echo "    sh test-app.sh --reseau https://lichess.org/<identifiant>" >&2
        exit 2
    fi
elif [ "$RESEAU" = 1 ]; then
    echo "Aucune partie donnée : T24, le téléchargement d'une partie, sera sauté." >&2
    echo "Pour le jouer, donnez n'importe quelle partie de Lichess :" >&2
    echo "    sh test-app.sh --reseau <identifiant ou adresse de la partie>" >&2
fi

RAPPORT="$DEPOT/rapport-tests-$SYSTEME-$(date +%Y%m%d-%H%M%S).txt"
TRAVAIL=$(mktemp -d "${TMPDIR:-/tmp}/ianalyze-tests.XXXXXX") || exit 2
# Chemin remis au propre : sous macOS, TMPDIR se termine par une barre et
# le chemin fabriqué en porte deux, ce qui empêchait de le masquer dans le
# rapport.
TRAVAIL=$(cd "$TRAVAIL" && pwd)

nettoyer() {
    if [ "${GARDER:-0}" = "1" ]; then
        echo "Répertoire temporaire conservé : $TRAVAIL" >&2
    else
        rm -rf "$TRAVAIL"
    fi
}
trap nettoyer EXIT
trap 'exit 130' INT TERM

cd "$TRAVAIL" || exit 2

# Options communes aux tests qui ne portent ni sur l'explorateur ni sur le
# moteur. La variable est volontairement développée sans guillemets.
O="--sans-explorateur --profondeur 1 --sans-questions --stockfish $STOCKFISH"

# Fichier de réglages propre aux tests : le vôtre n'est ni lu ni modifié.
# Il porte un pseudo, pour que les tests qui passent par un terminal ne
# reçoivent pas les questions du premier lancement.
REGL="$TRAVAIL/reglages-tests.ini"
printf '[joueur]\npseudos = Moi\ncadence = 14 jours\nniveau = 1300\n' \
    > "$REGL"

NB_OK=0
NB_ECHEC=0
NB_SAUTE=0
BRUT="$TRAVAIL/rapport.brut"
: > "$BRUT"

# --- Outils du rapport ------------------------------------------------------

# Écrit une ligne dans le rapport et, en abrégé, sur le terminal.
noter() {
    printf '%s\n' "$*" >> "$BRUT"
}

titre() {
    noter ""
    noter "=== $* ==="
    printf '%s\n' "$*" >&2
}

# Le shell POSIX n'a pas de variables locales : une variable affectée dans
# une fonction est celle du script entier. Les fonctions qui suivent
# préfixent donc les leurs, pour qu'aucun test ne voie l'une des siennes
# changer de valeur en les appelant. T75 lisait la cause attendue dans une
# variable "attendu", que la fonction egal écrasait : il cherchait ensuite
# le chiffre 1 dans le journal, et le trouvait ou non selon l'heure.

# verifier "libellé" commande... : la commande réussit-elle ?
verifier() {
    verifier_libelle=$1
    shift
    if "$@" >/dev/null 2>&1; then
        NB_OK=$((NB_OK + 1))
        noter "  OK     $verifier_libelle"
    else
        NB_ECHEC=$((NB_ECHEC + 1))
        noter "  ECHEC  $verifier_libelle"
        printf '    ECHEC : %s\n' "$verifier_libelle" >&2
        # Un texte attendu qui manque : le fichier fouillé est joint au
        # rapport, pour que l'échec se lise sans rejouer le test.
        if [ "$1" = contient ] && [ -f "$2" ]; then
            joindre "$2" 8
        fi
    fi
}

# egal "libellé" attendu obtenu : comparaison de deux valeurs. Les espaces
# de bord sont ignorées (wc en ajoute sous macOS) et toute suite d'espaces
# ou de tabulations vaut une seule espace. Les espaces intérieures comptent :
# "1 0" n'est pas "10".
egal() {
    egal_obtenu=$(printf '%s' "$3" | tr -s ' \t' '  ')
    egal_obtenu=${egal_obtenu# }
    egal_obtenu=${egal_obtenu% }
    egal_attendu=$(printf '%s' "$2" | tr -s ' \t' '  ')
    egal_attendu=${egal_attendu# }
    egal_attendu=${egal_attendu% }
    if [ "$egal_obtenu" = "$egal_attendu" ]; then
        NB_OK=$((NB_OK + 1))
        noter "  OK     $1"
    else
        NB_ECHEC=$((NB_ECHEC + 1))
        noter "  ECHEC  $1 : attendu [$2], obtenu [$3]"
        printf '    ECHEC : %s\n' "$1" >&2
    fi
}

sauter() {
    NB_SAUTE=$((NB_SAUTE + 1))
    noter "  SAUTE  $*"
    printf '    sauté : %s\n' "$*" >&2
}

# Recopie un fichier dans le rapport, en retrait, limité à N lignes
# (vingt par défaut), chaque ligne étant coupée à 200 caractères.
joindre() {
    if [ -s "$1" ]; then
        head -n "${2:-20}" "$1" | LC_ALL=C cut -c1-200 | LC_ALL=C sed 's/^/      | /' >> "$BRUT"
    fi
}

# lancer options... : lance le script, range la sortie standard dans
# "sortie", le journal dans "journal", et le code de retour dans RC. --venv
# est toujours passé : le script se relance ainsi dans l'environnement
# virtuel contrôlé plus haut, même si ce n'est pas celui par défaut.
lancer() {
    "$SCRIPT" "$@" --venv "$VENV" --reglages "$REGL" > sortie 2> journal
    RC=$?
    ARCH=$(head -n 1 sortie)
}

# Nombre de lignes d'un fichier, sans les espaces que wc ajoute sous macOS.
lignes() {
    wc -l < "$1" | tr -d ' '
}

# Le fichier contient-il la chaîne, prise littéralement ?
contient() {
    grep -F -q -- "$2" "$1"
}

# Extrait un fichier de l'archive courante vers le fichier "extrait".
extraire() {
    unzip -p "$ARCH" "$1" > extrait 2>/dev/null
}

# --- En-tête du rapport -----------------------------------------------------

titre "Environnement"
noter "  date            : $(date '+%Y-%m-%d %H:%M:%S %z')"
noter "  système         : $(uname -srm)"
if command -v sw_vers >/dev/null 2>&1; then
    noter "  macOS           : $(sw_vers -productVersion 2>/dev/null)"
fi
if [ -r /etc/os-release ]; then
    noter "  distribution    : $(sed -n 's/^PRETTY_NAME=//p' /etc/os-release)"
fi
noter "  shell           : $(ls -l /bin/sh | sed 's/.* \/bin\/sh/\/bin\/sh/')"
noter "  python3 système : $(python3 --version 2>&1) ($(command -v python3))"
noter "  python du venv  : $("$PYVENV" --version 2>&1)"
noter "  python-chess    : $("$PYVENV" -c 'import chess; print(chess.__version__)')"
noter "  venv            : $VENV"
noter "  stockfish       : $STOCKFISH"
noter "                    $(printf 'quit\n' | "$STOCKFISH" 2>/dev/null | head -n 1)"
noter "  locale          : LANG=${LANG:-} LC_ALL=${LC_ALL:-} LC_CTYPE=${LC_CTYPE:-}"
noter "  encodages Python: $("$PYVENV" -c 'import sys, locale; print(sys.stdout.encoding, sys.getfilesystemencoding(), locale.getpreferredencoding(False))')"
noter "  version script  : $(sed -n 's/^VERSION = //p' "$SCRIPT")"
if [ "$RESEAU" = 1 ]; then
    noter "  mode            : hors réseau, puis réseau et jeton (--reseau)"
    noter "  fichier du jeton: $JETON, droits $(ls -l "$JETON" | cut -c1-10)"
    if [ -n "$ID_PARTIE" ]; then
        noter "  partie de T24   : donnée, masquée dans ce rapport"
    else
        noter "  partie de T24   : aucune, T24 sera sauté"
    fi
else
    noter "  mode            : hors réseau seulement"
fi
if command -v git >/dev/null 2>&1; then
    noter "  commit          : $(git -C "$DEPOT" log -1 --format='%h %s' 2>/dev/null)"
    noter "  mode du script  : $(ls -l "$SCRIPT" | cut -c1-10)"
fi

printf '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 *\n' > italienne.pgn

# --- Plateforme -------------------------------------------------------------

titre "T01, T02 : compilation et aide"
verifier "T01 py_compile" python3 -m py_compile "$SCRIPT"
rm -rf "$DEPOT/__pycache__"
"$SCRIPT" --help > aide 2> journal
egal "T02 --help, code de retour" 0 $?
egal "T02 --coups-min cité 4 fois" 4 "$(grep -c -- --coups-min aide)"

titre "T31, T32 : commandes d'installation selon la plateforme"
if [ "$SYSTEME" = "Darwin" ]; then
    egal "T31 brew install cité 4 fois" 4 "$(grep -c 'brew install' aide)"
    egal "T32 apt install absent" 0 "$(grep -c 'apt install' aide)"
else
    egal "T31 brew install absent" 0 "$(grep -c 'brew install' aide)"
    egal "T32 apt install cité 4 fois" 4 "$(grep -c 'apt install' aide)"
fi
verifier "défaut de --venv sous le répertoire utilisateur" \
    contient aide ".local/share/IAnalyze/venv"
verifier "défaut de --catalogue sous le répertoire utilisateur" \
    contient aide ".local/share/IAnalyze)"

titre "T05 : collecte minimale"
lancer italienne.pgn $O
egal "T05 code de retour" 0 "$RC"
egal "T05 une seule ligne sur la sortie standard" 1 "$(wc -l < sortie)"
verifier "T05 l'archive existe" test -f "$ARCH"
unzip -l "$ARCH" > liste 2>/dev/null
verifier "T05 synthese.md dans l'archive" contient liste "/synthese.md"
verifier "T05 collecte.json dans l'archive" contient liste "/collecte.json"
egal "T05 aucun fichier .partiel dans l'archive" 0 "$(grep -c partiel liste)"

titre "T26 : moteur introuvable"
lancer italienne.pgn --sans-explorateur --sans-questions --stockfish /nulle/part
egal "T26 code de retour" 1 "$RC"
verifier "T26 message Stockfish introuvable" \
    contient journal "Stockfish introuvable : /nulle/part"
if [ "$SYSTEME" = "Darwin" ]; then
    verifier "T26 conseil brew install stockfish" \
        contient journal "(brew install stockfish)"
fi
joindre journal

# --- Encodages --------------------------------------------------------------

titre "T34 : PGN en latin-1, puis dans un encodage non reconnu"
# Un texte latin-1 se lit comme du cp1252 : les deux ne diffèrent que sur
# des octets qu'aucun texte n'emploie.
printf '[White "Jos\351"]\n[Black "M\374ller"]\n\n' > t-latin1.pgn
printf '1. e4 e5 *\n' >> t-latin1.pgn
lancer t-latin1.pgn $O
egal "T34 code de retour" 0 "$RC"
verifier "T34 encodage retenu : cp1252" \
    contient journal "encodage retenu : cp1252"
# Le même en cp850 : "é" y vaut l'octet 0x82 et "ü" l'octet 0x81, que
# cp1252 ne définit pas. Le script s'arrête au lieu de retirer les
# lettres accentuées comme des caractères de contrôle.
printf '[White "Jos\202"]\n[Black "M\201ller"]\n\n1. e4 e5 *\n' > t-cp850.pgn
lancer t-cp850.pgn $O
egal "T34 cp850, code de retour" 1 "$RC"
verifier "T34 cp850, encodage non reconnu" \
    contient journal "Encodage du PGN non reconnu"
egal "T34 cp850, rien n'est écrit" 0 \
    "$(ls -d analyse-t-cp850* 2>/dev/null | wc -l)"
lancer t-latin1.pgn $O
extraire '*/synthese.md'
verifier "T34 White José" contient extrait "| White | José |"
verifier "T34 Black Müller" contient extrait "| Black | Müller |"
verifier "T34 ligne Encodage en section 5" contient extrait "- Encodage : le PGN"
joindre journal

titre "T35 : PGN en cp1252"
printf '[White "Jos\351"]\n[Event "Coupe d\222\351t\351 \226 5 \200"]\n' > t-cp1252.pgn
printf '\n1. e4 e5 *\n' >> t-cp1252.pgn
lancer t-cp1252.pgn $O
egal "T35 code de retour" 0 "$RC"
verifier "T35 encodage retenu : cp1252" \
    contient journal "encodage retenu : cp1252"
extraire '*/synthese.md'
verifier "T35 apostrophe courbe, tiret et euro" \
    contient extrait "| Event | Coupe d’été – 5 € |"
grep -F 'Event' extrait > ligne 2>/dev/null
joindre ligne

titre "T36 : marque d'ordre des octets UTF-8"
printf '\357\273\277[White "Jos\303\251"]\n\n1. e4 e5 *\n' > t-bom.pgn
lancer t-bom.pgn $O
egal "T36 code de retour" 0 "$RC"
verifier "T36 BOM UTF-8 retirée" contient journal "(BOM) UTF-8 retirée"
extraire '*/partie.pgn'
egal "T36 partie.pgn commence par un crochet" "[" "$(head -c 1 extrait)"

titre "T37 : UTF-16 avec et sans marque d'ordre"
if command -v iconv >/dev/null 2>&1; then
    printf '[White "Jos\303\251"]\n\n1. e4 e5 *\n' \
        | iconv -f UTF-8 -t UTF-16LE > t-utf16.pgn
    { printf '\377\376'; cat t-utf16.pgn; } > t-utf16-bom.pgn
    lancer t-utf16-bom.pgn $O
    egal "T37 avec BOM, code de retour" 0 "$RC"
    verifier "T37 avec BOM, utf-16-le annoncé" \
        contient journal "(BOM) détectée, encodage retenu : utf-16-le"
    extraire '*/synthese.md'
    verifier "T37 avec BOM, White José" contient extrait "| White | José |"
    lancer t-utf16.pgn $O
    egal "T37 sans BOM, code de retour" 0 "$RC"
    verifier "T37 sans BOM, utf-16-le reconnu" \
        contient journal "un octet nul sur deux"
    extraire '*/synthese.md'
    verifier "T37 sans BOM, White José" contient extrait "| White | José |"
    joindre journal
else
    sauter "T37 : iconv introuvable"
fi

titre "T38 : UTF-8 abîmé"
printf '[White "Jos\303\251"]\n\n1. e4 {tr\377\376s bon} e5 *\n' > t-abime.pgn
lancer t-abime.pgn $O
egal "T38 code de retour" 0 "$RC"
verifier "T38 deux octets invalides remplacés" \
    contient journal "UTF-8 abîmé, 2 octet(s) invalide(s)"
extraire '*/synthese.md'
verifier "T38 White José intact" contient extrait "| White | José |"
extraire '*/partie.pgn'
egal "T38 commentaire conservé" 1 "$(grep -c 's bon}' extrait)"

titre "T39 : octets NUL"
printf '[White "Jo\000s"]\n\n1. e4\000 e5 *\n' > t-nul.pgn
lancer t-nul.pgn $O
egal "T39 code de retour" 0 "$RC"
verifier "T39 deux NUL retirés" contient journal "dont 2 NUL"
egal "T39 aucun NUL dans l'archive" 0 \
    "$(unzip -p "$ARCH" | od -c | grep -c '\\0')"
joindre journal

titre "T40 : fins de ligne CRLF"
printf '[White "A"]\r\n\r\n1. e4 e5 *\r\n' > t-crlf.pgn
lancer t-crlf.pgn $O
egal "T40 code de retour" 0 "$RC"
egal "T40 aucun avertissement" 0 "$(grep -c Attention journal)"
egal "T40 aucun retour chariot dans partie.pgn" 0 \
    "$(unzip -p "$ARCH" '*/partie.pgn' | od -c | grep -c '\\r')"

titre "T41 : locale C et sortie ASCII"
LANG=C "$SCRIPT" t-latin1.pgn $O --venv "$VENV" --reglages "$REGL" \
    > sortie 2> journal
egal "T41 LANG=C, code de retour" 0 $?
LC_ALL=C PYTHONUTF8=0 "$SCRIPT" --help > aide-c 2> journal
egal "T41 LC_ALL=C PYTHONUTF8=0 --help, code de retour" 0 $?
grep 'questions de d' aide-c > ligne 2>/dev/null
noter "  note   ligne de l'aide sous LC_ALL=C PYTHONUTF8=0 :"
joindre ligne
PYTHONIOENCODING=ascii "$SCRIPT" --help > aide-ascii 2> journal
egal "T41 PYTHONIOENCODING=ascii --help, code de retour" 0 $?
verifier "T41 accents remplacés par ? en ASCII" \
    contient aide-ascii "questions de d?marrage"

titre "T42 : caractères de contrôle dans les balises"
printf '[Event "Tour\tnoi"]\n[Site "\033[31mParis\007"]\n\n' > t-ctrl.pgn
printf '1. e4 e5 *\n' >> t-ctrl.pgn
lancer t-ctrl.pgn $O
egal "T42 code de retour" 0 "$RC"
verifier "T42 deux caractères de contrôle retirés" \
    contient journal "2 caractère(s) de contrôle retiré(s), dont 0 NUL"
extraire '*/synthese.md'
verifier "T42 tabulation devenue une espace" contient extrait "| Event | Tour noi |"
verifier "T42 ESC retiré du Site" contient extrait "| Site | [31mParis |"
egal "T42 ni ESC ni BEL dans l'archive" 0 \
    "$(unzip -p "$ARCH" | tr -d -c '\033\007' | wc -c)"

titre "T43 : fichier de jeton factice"
printf '\357\273\277lip_factice\r\n' > t-jeton
chmod 600 t-jeton
lancer italienne.pgn --profondeur 1 --sans-questions \
    --jeton-fichier t-jeton --catalogue /nulle/part
verifier "T43 BOM du jeton retirée" contient journal "(BOM) UTF-8 retirée"
verifier "T43 jeton accepté, arrêt sur le catalogue" \
    contient journal "Catalogue des ouvertures absent"
egal "T43 le jeton n'est pas affiché" 0 "$(grep -c lip_factice journal)"
printf 'lip_factic\351\n' > t-jeton
lancer italienne.pgn --profondeur 1 --sans-questions \
    --jeton-fichier t-jeton --catalogue /nulle/part
egal "T43 jeton non ASCII, code de retour" 1 "$RC"
verifier "T43 jeton non ASCII refusé" \
    contient journal "hors de l'ASCII imprimable"
joindre journal

titre "T44 : noms de fichiers"
cp italienne.pgn 't-a:b?.pgn'
lancer 't-a:b?.pgn' $O
egal "T44 deux-points et point d'interrogation, code de retour" 0 "$RC"
verifier "T44 dossier assaini en t-a_b_" \
    contient journal "Nom du dossier assaini : t-a_b_"
verifier "T44 l'archive existe" test -f "$ARCH"
# Nom non UTF-8 : le système de fichiers de macOS le refuse en principe.
NOM_LATIN=$(printf 't-\351t\351.pgn')
if cp italienne.pgn "$NOM_LATIN" 2> journal-cp; then
    lancer "$NOM_LATIN" $O
    egal "T44 nom non UTF-8, code de retour" 0 "$RC"
    verifier "T44 nom non UTF-8, dossier assaini" \
        contient journal "Nom du dossier assaini"
    joindre journal
else
    sauter "T44 nom non UTF-8 : création refusée par le système de fichiers"
    joindre journal-cp
fi

titre "M1 : nom accentué, chemin de sortie avec espace et accent"
cp italienne.pgn "t-été à Paris.pgn"
lancer "t-été à Paris.pgn" $O --sortie "$TRAVAIL/sorties d'été"
egal "M1 code de retour" 0 "$RC"
verifier "M1 le chemin affiché désigne bien l'archive" test -f "$ARCH"
# Les espaces du nom du PGN deviennent des tirets dans celui de l'archive,
# ceux du répertoire de sortie sont gardés : il est à vous.
case "$ARCH" in
    "$TRAVAIL/sorties d'été/analyse-t-été-à-Paris-"*.zip) vu=oui ;;
    *) vu=non ;;
esac
egal "M1 espaces du nom devenus des tirets" oui "$vu"
noter "  note   chemin affiché : $ARCH"
PYTHONIOENCODING=ascii "$SCRIPT" "t-été à Paris.pgn" $O \
    --sortie "$TRAVAIL/sorties d'été" --venv "$VENV" --reglages "$REGL" \
    > sortie 2> journal
ARCH=$(head -n 1 sortie)
verifier "M1 chemin exact même avec une sortie ASCII" test -f "$ARCH"

titre "T45 : réponse saisie en latin-1 sur un pseudo-terminal"
rm -rf analyse-italienne-*
SCRIPT="$SCRIPT" VENV="$VENV" REGL="$REGL" python3 - > sortie-pty 2>&1 \
    <<'EOF'
import os
import pty
import time

script = os.environ["SCRIPT"]
pid, fd = pty.fork()
if pid == 0:
    os.execv(script, [script, "italienne.pgn", "--sans-explorateur",
                      "--profondeur", "1", "--garder-dossier",
                      "--venv", os.environ["VENV"],
                      "--reglages", os.environ["REGL"]])
for reponse in (b"b", b"Zo\xe9", b"", b"", b"", b"", b""):
    time.sleep(1)
    os.write(fd, reponse + b"\n")
time.sleep(3)
try:
    print(os.read(fd, 65536).decode("utf-8", "replace")[-300:])
except OSError as err:
    print("lecture du pseudo-terminal :", err)
os.waitpid(pid, 0)
EOF
cat analyse-italienne-*/partie.pgn > extrait 2>/dev/null
verifier "T45 partie.pgn porte [Black \"Zoé\"]" contient extrait '[Black "Zoé"]'
egal "T45 pas d'erreur inattendue" 0 "$(grep -c 'Erreur inattendue' sortie-pty)"
joindre sortie-pty
rm -rf analyse-italienne-*

titre "T79 : réponses refusées, trop longues ou porteuses de signes du PGN"
# Le nom de l'adversaire part dans une balise du PGN : un guillemet ou un
# crochet la fermerait trop tôt. Les deux premières réponses sont
# refusées et la question reposée, la troisième est gardée.
rm -rf analyse-italienne-*
SCRIPT="$SCRIPT" VENV="$VENV" REGL="$REGL" python3 - > sortie-pty 2>&1 \
    <<'EOF'
import os
import pty
import time

script = os.environ["SCRIPT"]
pid, fd = pty.fork()
if pid == 0:
    os.execv(script, [script, "italienne.pgn", "--sans-explorateur",
                      "--profondeur", "1", "--garder-dossier",
                      "--venv", os.environ["VENV"],
                      "--reglages", os.environ["REGL"]])
recu = b""
for reponse in (b"b", b'Ev"il] [White "Pirate"] {x}', b"a" * 300, b"Bob",
                b"", b"", b"", b"", b""):
    time.sleep(1)
    os.write(fd, reponse + b"\n")
time.sleep(3)
try:
    while True:
        morceau = os.read(fd, 65536)
        if not morceau:
            break
        recu += morceau
except OSError:
    pass
os.waitpid(pid, 0)
texte = recu.decode("utf-8", "replace")
print(texte.count("Un nom ne peut contenir"),
      texte.count("Réponse trop longue : 255"),
      texte.count("Erreur inattendue"))
EOF
cat analyse-italienne-*/partie.pgn > extrait 2>/dev/null
verifier "T79 nom gardé après deux refus" contient extrait '[Black "Bob"]'
egal "T79 une seule balise White, aucun signe en trop" "1 0" \
    "$(grep -c '^\[White ' extrait) $(grep -c 'Pirate' extrait)"
egal "T79 un refus de signe, un refus de longueur, pas d'erreur" "1 1 0" \
    "$(tail -n 1 sortie-pty)"
joindre sortie-pty
rm -rf analyse-italienne-*

titre "T80 : nom de PGN long, en caractères de plusieurs octets"
# Cent idéogrammes, trois cents octets : l'étiquette est bornée en octets,
# faute de quoi l'archive échouait sur un nom trop long après l'analyse.
SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t80 2> journal-t80 <<'EOF'
import importlib.util
import os

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
longue = cp.etiquette_sure("日" * 100)
print(len(longue.encode("utf-8")) <= cp.ETIQUETTE_MAX, len(longue))
print(cp.etiquette_sure("  partie  contre\tmachin  "))
print(cp.etiquette_sure(" . "), cp.etiquette_sure("a:b?"))
EOF
printf 'True 26\npartie-contre-machin\npartie a_b_\n' > attendu-t80
verifier "T80 étiquette bornée en octets, espaces en tirets" \
    cmp -s attendu-t80 sortie-t80
joindre sortie-t80
joindre journal-t80 5
rm -rf "$DEPOT/__pycache__"

titre "T46, T47 : PGN sain et version"
lancer italienne.pgn $O
egal "T46 aucun avertissement" 0 "$(grep -c Attention journal)"
extraire '*/collecte.json'
verifier "T46 pgn_encodage utf-8" contient extrait '"pgn_encodage": "utf-8"'
verifier "T46 pgn_remarques vide" contient extrait '"pgn_remarques": []'
noter "  note   T47 $(grep -n '^VERSION' "$SCRIPT")"
SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t47 2> journal-t47 <<'EOF'
import importlib.util
import os
import re

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
print(bool(re.fullmatch(r"\d+\.\d+\.\d+", cp.VERSION)),
      cp.UA.startswith("IAnalyze/%s " % cp.VERSION))
EOF
egal "T47 version au format X.Y.Z, reprise dans l'en-tête d'agent" \
    "True True" "$(cat sortie-t47)"
joindre journal-t47 5
rm -rf "$DEPOT/__pycache__"

# --- Archive ----------------------------------------------------------------

titre "T48 : point dans le nom du PGN"
cp italienne.pgn t-2026.11.18_A_vs_B.pgn
lancer t-2026.11.18_A_vs_B.pgn $O
egal "T48 code de retour" 0 "$RC"
case $ARCH in
    analyse-t-2026.11.18_A_vs_B-*.zip) NOM_OK=oui ;;
    *) NOM_OK=non ;;
esac
egal "T48 nom complet de l'archive" oui "$NOM_OK"
egal "T48 synthese.md dans l'archive" 1 \
    "$(unzip -l "$ARCH" 2>/dev/null | grep -c synthese.md)"
egal "T48 dossier de travail supprimé" 0 \
    "$(find . -maxdepth 1 -type d -name 'analyse-t-2026*' | wc -l)"

titre "T53 : interruption pendant l'archivage, écriture qui échoue"
mkdir t-r1
(
    cd t-r1 || exit 1
    SCRIPT="$SCRIPT" "$PYVENV" - > ../sortie-r1 2> ../journal-r1 <<'EOF'
import importlib.util
import os
import pathlib
import zipfile

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
d = pathlib.Path("analyse-essai-1")
d.mkdir()
for nom in ("partie.pgn", "synthese.md", "collecte.json"):
    (d / nom).write_text("x" * 5000, encoding="utf-8")
origine = zipfile.ZipFile.write
appels = [0]


def ecriture(self, *a, **k):
    appels[0] += 1
    if appels[0] == 3:
        raise KeyboardInterrupt
    return origine(self, *a, **k)


zipfile.ZipFile.write = ecriture
try:
    cp.archiver(d, False)
except KeyboardInterrupt:
    print("archivage interrompu")
zipfile.ZipFile.write = origine
print(sorted(p.name for p in pathlib.Path(".").iterdir()))
try:
    cp.ecrire_texte(d / "synthese.md", 12345)
except TypeError:
    print((d / "synthese.md").stat().st_size)
print(sorted(p.name for p in d.iterdir()))
print(cp.archiver(d, False))
print(sorted(p.name for p in pathlib.Path(".").iterdir()))
EOF
)
cat > attendu-r1 <<'EOF'
archivage interrompu
['analyse-essai-1']
5000
['collecte.json', 'partie.pgn', 'synthese.md']
analyse-essai-1.zip
['analyse-essai-1.zip']
EOF
verifier "T53 six lignes attendues" cmp -s attendu-r1 sortie-r1
joindre sortie-r1
rm -rf "$DEPOT/__pycache__"

# --- Explorateur simulé et options -----------------------------------------

titre "T49 : réponses inattendues de l'explorateur, simulé"
SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t49 2> journal-t49 <<'EOF'
import importlib.util
import io
import json
import os
import pathlib
import tempfile

import chess.pgn

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
partie = chess.pgn.read_game(io.StringIO("1. e4 e5 *"))


class Faux:
    def __init__(self, reponse):
        self.reponse = reponse

    def interroger(self, coups):
        return 200, self.reponse


for texte in ('{"white": 10, "draws": 5, "black": 5, "moves": 5}',
              '{"white": 1e999, "draws": 5, "black": 5}'):
    with tempfile.TemporaryDirectory() as d:
        r = cp.collecter_explorateur(
            partie, pathlib.Path(d), Faux(json.loads(texte)),
            1, 0.0, 60, False)
    print(len(r["lignes"]), r["lignes"][0]["parties_position"],
          r["lignes"][0]["rang"])
EOF
printf '2 20 None\n2 10 None\n' > attendu-t49
verifier "T49 deux lignes attendues" cmp -s attendu-t49 sortie-t49
joindre sortie-t49
rm -rf "$DEPOT/__pycache__"

titre "T76 : le jeton ne quitte pas l'explorateur, serveurs simulés"
# Deux serveurs locaux. Le premier tient lieu d'explorateur : il redirige
# vers le second, puis renvoie dans sa réponse l'en-tête Authorization
# qu'il a reçu. Le jeton, factice, ne doit ni suivre la redirection ni
# entrer dans la réponse gardée.
SCRIPT="$SCRIPT" no_proxy='*' NO_PROXY='*' "$PYVENV" - > sortie-t76 2> journal-t76 <<'EOF'
import http.server
import importlib.util
import json
import os
import threading

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
JETON = "lip_factice"
recu = []


class Tiers(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        recu.append(self.headers.get("Authorization"))
        corps = b'{"white": 1, "draws": 1, "black": 1, "moves": []}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *args):
        pass


class Faux(http.server.BaseHTTPRequestHandler):
    code = 302

    def do_GET(self):
        if self.path.startswith("/echo"):
            corps = json.dumps({
                "white": 1, "draws": 1, "black": 1, "moves": [],
                "vu": self.headers.get("Authorization")}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)
            return
        if self.path.startswith("/coupe"):
            # Erreur 500 dont le corps annoncé n'arrive jamais en entier.
            self.send_response(500)
            self.send_header("Content-Length", "1000")
            self.end_headers()
            self.wfile.write(b"abc")
            return
        if self.path.startswith("/profond"):
            corps = b"[" * 100000
            self.send_response(200)
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)
            return
        self.send_response(Faux.code)
        self.send_header("Location",
                         "http://localhost:%d/vol" % tiers.server_port)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


tiers = http.server.HTTPServer(("127.0.0.1", 0), Tiers)
faux = http.server.HTTPServer(("127.0.0.1", 0), Faux)
for serveur in (tiers, faux):
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
base = "http://127.0.0.1:%d" % faux.server_port
for code in (301, 302, 303, 307, 308):
    Faux.code = code
    statut, donnees = cp.Explorateur(
        JETON, 2.0, 5, base + "/lichess", {}).interroger(["e2e4"])
    print(code, statut, "redirection" in donnees.get("_erreur", ""))
print("tiers", len(recu))
statut, donnees = cp.Explorateur(
    JETON, 2.0, 5, base + "/echo", {}).interroger(["e2e4"])
print(statut, JETON in json.dumps(donnees), donnees.get("vu"))
# Réponses qui faisaient avorter toute la collecte : erreur HTTP au corps
# coupé, JSON imbriqué à l'excès. Puis les comptes aberrants.
for chemin in ("/coupe", "/profond"):
    statut, donnees = cp.Explorateur(
        JETON, 2.0, 5, base + chemin, {}).interroger(["e2e4"])
    print(chemin, statut, sorted(donnees))
print(cp.entier(10 ** 400), cp.entier(-5), cp.entier("12"), cp.entier(7.9))
EOF
cat > attendu-t76 <<'EOF'
301 301 True
302 302 True
303 303 True
307 307 True
308 308 True
tiers 0
200 False Bearer <JETON-EXPURGE>
/coupe 500 ['_erreur']
/profond 0 ['_erreur']
0 0 12 7
EOF
verifier "T76 redirections, réponse expurgée, réponses abîmées" \
    cmp -s attendu-t76 sortie-t76
joindre sortie-t76
joindre journal-t76 5
rm -rf "$DEPOT/__pycache__"

titre "T50 : valeurs non finies"
for option in "--pause nan" "--pause inf" "--seuil-frequence nan"; do
    lancer italienne.pgn $option
    egal "T50 $option, code de retour" 2 "$RC"
    verifier "T50 $option, message" contient journal "doit être un nombre fini"
done
egal "T50 aucun dossier de travail créé" 0 \
    "$(find . -maxdepth 1 -type d -name 'analyse-italienne-*' | wc -l)"

titre "T54 : URL qui ne sont pas des parties"
for url in https://lichess.org/analysis/standard \
           https://lichess.org/study/abcdefgh/ijklmnop \
           https://example.com/abcdefgh; do
    lancer "$url" --sans-explorateur --profondeur 1
    egal "T54 $url, code de retour" 1 "$RC"
    verifier "T54 $url, refusée" contient journal "URL non reconnue"
    egal "T54 $url, aucun téléchargement" 0 "$(grep -c 'chargement du PGN' journal)"
done
SCRIPT="$SCRIPT" python3 - > sortie-t54 2>&1 <<'EOF'
import importlib.util
import os

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
for u in ("https://lichess.org/AbCd1234/black",
          "https://www.lichess.org/AbCd1234efGh#12",
          "https://lichess.org/embed/game/AbCd1234",
          "https://lichess.org/game/export/AbCd1234",
          "AbCd1234", "https://lichess.org/practice", "analysis"):
    print(cp.extraire_id(u))
EOF
printf 'AbCd1234\nAbCd1234\nAbCd1234\nAbCd1234\nAbCd1234\nNone\nNone\n' > attendu-t54
verifier "T54 identifiants extraits" cmp -s attendu-t54 sortie-t54
joindre sortie-t54
rm -rf "$DEPOT/__pycache__"

# --- Coup nul et explorateur ------------------------------------------------

titre "T56 : coup nul, explorateur simulé"
SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t56 2> journal-t56 <<'EOF'
import importlib.util
import io
import os
import pathlib
import tempfile

import chess.pgn

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
partie = chess.pgn.read_game(io.StringIO("1. e4 e5 2. -- Nc6 3. Nf3 *"))


class Faux:
    appels = 0

    def interroger(self, coups):
        Faux.appels += 1
        assert "0000" not in coups
        return 200, {"white": 600, "draws": 300, "black": 100,
                     "moves": [{"uci": c, "san": c, "white": 300,
                                "draws": 150, "black": 50}
                               for c in ("e2e4", "e7e5")]}


with tempfile.TemporaryDirectory() as d:
    r = cp.collecter_explorateur(
        partie, pathlib.Path(d), Faux(), 50, 10.0, 60, False)
print(Faux.appels, len(r["lignes"]), r["premiere_sortie"])
print([(n["demicoup"], n["san"], n["motif"]) for n in r["non_exploitables"]])
print(r["arret"][:28])
EOF
cat > attendu-t56 <<'EOF'
2 2 None
[(3, '--', 'coup nul, non interrogé')]
coup nul au demi-coup 3 : ce
EOF
verifier "T56 arrêt au coup nul, deux requêtes, pas de sortie" \
    cmp -s attendu-t56 sortie-t56
joindre sortie-t56
rm -rf "$DEPOT/__pycache__"

# --- Réglages ---------------------------------------------------------------

# Pilote de pseudo-terminal : lance le script avec les options données,
# répond aux questions dans l'ordre (réponses séparées par des barres
# verticales), puis affiche ce que le terminal a montré. Les questions de
# réglages ne sont posées que sur un terminal.
cat > t-pty.py <<'EOF'
import os
import pty
import select
import sys

script = os.environ["SCRIPT"]
pid, fd = pty.fork()
if pid == 0:
    os.execv(script, [script] + sys.argv[2:])
vu = b""


def lire():
    global vu
    while select.select([fd], [], [], 1)[0]:
        try:
            bloc = os.read(fd, 65536)
        except OSError:
            return
        if not bloc:
            return
        vu += bloc


for reponse in sys.argv[1].split("|"):
    lire()
    os.write(fd, reponse.encode() + b"\n")
# S'il manque une réponse, une fin de flux part après quinze secondes de
# silence : le script prend alors ses valeurs par défaut au lieu
# d'attendre sans fin.
silences = 0
while not os.waitpid(pid, os.WNOHANG)[0]:
    avant = len(vu)
    lire()
    silences = silences + 1 if len(vu) == avant else 0
    if silences >= 15:
        os.write(fd, b"\x04")
        silences = 0
sys.stdout.write(vu.decode("utf-8", "replace").replace("\r", ""))
EOF
# Options des lancements sur pseudo-terminal.
P="--sans-explorateur --profondeur 1 --garder-dossier --venv $VENV"

titre "T57 : premier lancement, réglages demandés puis enregistrés"
rm -rf analyse-italienne-*
SCRIPT="$SCRIPT" python3 t-pty.py "Zoe42, zoe|t|15|10|1300|b||||||" \
    italienne.pgn $P --reglages t-reglages.ini > sortie-pty 2>&1
verifier "T57 trois réponses demandées une seule fois" \
    contient sortie-pty "3 réponse(s) à donner une seule fois"
verifier "T57 question du niveau" \
    contient sortie-pty "Votre niveau, en points Elo approximatifs ?"
verifier "T57 question du pseudo" contient sortie-pty "Votre pseudo de joueur"
verifier "T57 question de la cadence" \
    contient sortie-pty "Votre cadence habituelle : [t]emps réel, [c]orrespondance"
verifier "T57 minutes demandées" contient sortie-pty "Minutes par joueur ?"
verifier "T57 incrément demandé" contient sortie-pty "Incrément en secondes ?"
verifier "T57 réglages enregistrés" contient sortie-pty "Réglages enregistrés :"
grep -v '^#' t-reglages.ini > extrait 2>/dev/null
printf '\n[joueur]\npseudos = Zoe42, zoe\ncadence = 15+10\n' > attendu
printf 'niveau = 1300\n' >> attendu
verifier "T57 contenu du fichier" cmp -s attendu extrait
cat analyse-italienne-*/partie.pgn > extrait 2>/dev/null
verifier "T57 balise vide complétée par le pseudo" \
    contient extrait '[White "Zoe42"]'
cat analyse-italienne-*/contexte.md > extrait 2>/dev/null
verifier "T57 cadence habituelle proposée et rédigée" \
    contient extrait "- Cadence : rapide, 15 minutes + 10 secondes par coup (défaut)"
grep -E 'glages|Votre|par |Erreur' sortie-pty > ligne 2>/dev/null
joindre ligne

titre "T58 : second lancement, priorité de --pseudos"
rm -rf analyse-italienne-*
SCRIPT="$SCRIPT" python3 t-pty.py "b||||||" italienne.pgn $P \
    --reglages t-reglages.ini > sortie-pty 2>&1
egal "T58 plus aucune question de réglages" 0 \
    "$(grep -c -E 'glages|Votre' sortie-pty)"
printf '[White "Alice"]\n[Black "Zoe42"]\n\n1. e4 e5 *\n' > t-noms.pgn
SCRIPT="$SCRIPT" python3 t-pty.py "||||" t-noms.pgn $P \
    --reglages t-reglages.ini > sortie-pty 2>&1
cat analyse-t-noms-*/contexte.md > extrait 2>/dev/null
verifier "T58 camp déduit du pseudo des réglages" \
    contient extrait "Camp du joueur : Noirs, déduit des en-têtes"
rm -rf analyse-t-noms-*
SCRIPT="$SCRIPT" python3 t-pty.py "||||" t-noms.pgn $P \
    --reglages t-reglages.ini --pseudos Alice > sortie-pty 2>&1
cat analyse-t-noms-*/contexte.md > extrait 2>/dev/null
verifier "T58 --pseudos l'emporte sur les réglages" \
    contient extrait "Camp du joueur : Blancs, déduit des en-têtes"
rm -rf analyse-t-noms-*

titre "T59 : hors terminal, puis pseudo refusé"
"$SCRIPT" italienne.pgn $O --venv "$VENV" --reglages t-abs/reglages.ini \
    > sortie 2> journal
egal "T59 hors terminal, code de retour" 0 $?
egal "T59 hors terminal, rien demandé" 0 "$(grep -c -i 'glages' journal)"
if [ -e t-abs ]; then
    egal "T59 hors terminal, aucun fichier créé" absent présent
else
    egal "T59 hors terminal, aucun fichier créé" absent absent
fi
rm -rf analyse-italienne-*
SCRIPT="$SCRIPT" python3 t-pty.py "|||n|Moi|Lui|||||" italienne.pgn $P \
    --reglages t-vide.ini > sortie-pty 2>&1
verifier "T59 sans pseudo, le nom du joueur est demandé" \
    contient sortie-pty "Votre nom de joueur ? (Entrée : ?)"
grep -v '^#' t-vide.ini > extrait 2>/dev/null
printf '\n[joueur]\npseudos =\ncadence = inconnue\nniveau = inconnu\n' \
    > attendu
verifier "T59 clefs vides enregistrées, donc plus redemandées" \
    cmp -s attendu extrait
cat analyse-italienne-*/partie.pgn > extrait 2>/dev/null
verifier "T59 balises complétées par les noms saisis" \
    contient extrait '[Black "Moi"]'
egal "T59 pas d'erreur inattendue" 0 "$(grep -c 'Erreur inattendue' sortie-pty)"
rm -rf analyse-italienne-*

titre "T60 : fichier mal formé, clefs ajoutées conservées"
printf 'pseudos = Alice\n' > t-mauvais.ini
"$SCRIPT" italienne.pgn $O --venv "$VENV" --reglages t-mauvais.ini \
    > sortie 2> journal
egal "T60 fichier mal formé, code de retour" 1 $?
verifier "T60 fichier mal formé, message" contient journal "Réglages illisibles :"
verifier "T60 fichier mal formé, remède indiqué" \
    contient journal "ou supprimez-le"
printf '[joueur]\npseudos = Alice\nniveau = 1500\n\n' > t-plus.ini
printf '[perso]\nnote = 100 %% à moi\n' >> t-plus.ini
SCRIPT="$SCRIPT" python3 t-pty.py "c|d|14|||||" t-noms.pgn $P \
    --reglages t-plus.ini > sortie-pty 2>&1
grep -v '^#' t-plus.ini > extrait 2>/dev/null
cat > attendu <<'EOF'

[joueur]
pseudos = Alice
cadence = 14 jours
niveau = 1500

[perso]
note = 100 % à moi
EOF
verifier "T60 clefs et sections ajoutées à la main conservées" \
    cmp -s attendu extrait
joindre extrait
rm -rf analyse-t-noms-*

titre "T62 : cadence vérifiée, réponses fausses refusées"
printf '[joueur]\npseudos = Alice\nniveau = inconnu\n' > t-cad.ini
printf 'cadence = Ploum ploum\n' >> t-cad.ini
SCRIPT="$SCRIPT" python3 t-pty.py "x|t|abc|-5|0|0|t|15|10|||||" t-noms.pgn \
    $P --reglages t-cad.ini > sortie-pty 2>&1
verifier "T62 cadence illisible des réglages redemandée" \
    contient sortie-pty "n'est pas lisible, elle est redemandée"
egal "T62 type refusé une fois" 1 \
    "$(grep -c 'attendue : t, c ou i' sortie-pty)"
egal "T62 nombre refusé deux fois" 2 \
    "$(grep -c 'un nombre entier, 0 ou plus' sortie-pty)"
egal "T62 cadence 0+0 refusée" 1 \
    "$(grep -c 'sans temps ni incrément' sortie-pty)"
verifier "T62 cadence enregistrée sous sa forme courte" \
    contient t-cad.ini "cadence = 15+10"
egal "T62 pas d'erreur inattendue" 0 "$(grep -c 'Erreur inattendue' sortie-pty)"
grep -E 'lisible|attendue|existe' sortie-pty > ligne 2>/dev/null
joindre ligne
rm -rf analyse-t-noms-*
SCRIPT="$SCRIPT" python3 t-pty.py "t|5|0||||" t-noms.pgn $P \
    --reglages t-cad.ini > sortie-pty 2>&1
cat analyse-t-noms-*/contexte.md > extrait 2>/dev/null
verifier "T62 cadence de la partie différente de l'habituelle" \
    contient extrait "- Cadence : blitz, 5 minutes sans incrément"
rm -rf analyse-t-noms-*
printf '[White "Alice"]\n[Black "Bob"]\n' > t-tc.pgn
printf '[TimeControl "600+5"]\n\n1. e4 e5 *\n' >> t-tc.pgn
SCRIPT="$SCRIPT" python3 t-pty.py "||||" t-tc.pgn $P \
    --reglages t-cad.ini > sortie-pty 2>&1
egal "T62 balise TimeControl : pas de question" 0 \
    "$(grep -c 'Cadence de la partie' sortie-pty)"
cat analyse-t-tc-*/contexte.md > extrait 2>/dev/null
verifier "T62 balise TimeControl traduite" \
    contient extrait "soit rapide, 10 minutes + 5 secondes par coup"
grep Cadence extrait > ligne 2>/dev/null
joindre ligne
rm -rf analyse-t-tc-*

titre "T63 : correspondance, trois systèmes vérifiés"
printf '[joueur]\npseudos = Alice\nniveau = inconnu\n' > t-corr.ini
SCRIPT="$SCRIPT" python3 t-pty.py \
    "c|x|c|0|0h|||c|5|36|36h|2||c|5|36h|20||||||" t-noms.pgn $P \
    --reglages t-corr.ini > sortie-pty 2>&1
egal "T63 système refusé une fois" 1 \
    "$(grep -c 'attendue : d, p ou c' sortie-pty)"
egal "T63 incrément sans unité refusé une fois" 1 \
    "$(grep -c 'suivi de h ou de j' sortie-pty)"
egal "T63 cadence incohérente refusée deux fois" 2 \
    "$(grep -c 'Cadence incohérente' sortie-pty)"
verifier "T63 capital, incrément et plafond enregistrés" \
    contient t-corr.ini "cadence = 5 jours + 36 heures, plafond 20 jours"
cat analyse-t-noms-*/contexte.md > extrait 2>/dev/null
verifier "T63 chess-mail.com : capital 5 jours + 36 heures, plafond 20" \
    contient extrait "capital de 5 jours + 36 heures par coup, plafonné à 20 jours"
egal "T63 pas d'erreur inattendue" 0 "$(grep -c 'Erreur inattendue' sortie-pty)"
grep -E 'attendue|incohérente' sortie-pty > ligne 2>/dev/null
joindre ligne
rm -rf analyse-t-noms-*
printf '[joueur]\npseudos = Alice\nniveau = inconnu\n' > t-corr.ini
printf 'cadence = 10 coups en 50 jours\n' >> t-corr.ini
SCRIPT="$SCRIPT" python3 t-pty.py "||||" t-noms.pgn $P \
    --reglages t-corr.ini > sortie-pty 2>&1
cat analyse-t-noms-*/contexte.md > extrait 2>/dev/null
verifier "T63 ICCF standard : 10 coups en 50 jours" \
    contient extrait "- Cadence : correspondance, 10 coups en 50 jours (défaut)"
rm -rf analyse-t-noms-*
printf '[joueur]\npseudos = Alice\nniveau = inconnu\n' > t-corr.ini
printf 'cadence = 50j+3j, plafond 50j, réserve 75j\n' >> t-corr.ini
SCRIPT="$SCRIPT" python3 t-pty.py "||||" t-noms.pgn $P \
    --reglages t-corr.ini > sortie-pty 2>&1
cat analyse-t-noms-*/contexte.md > extrait 2>/dev/null
verifier "T63 ICCF Triple Block : capital, incrément, plafond, réserve" \
    contient extrait "capital de 50 jours + 3 jours par coup, plafonné à 50 jours, réserve de 75 jours"
grep Cadence extrait > ligne 2>/dev/null
joindre ligne
rm -rf analyse-t-noms-*
# Fichier de réglages absent : le pseudo est demandé d'abord, puis, faute de
# pseudo, le camp.
SCRIPT="$SCRIPT" python3 t-pty.py "|c|p|10|40||b|||||" t-noms.pgn $P \
    --reglages t-vide2.ini > sortie-pty 2>&1
verifier "T63 coups par période saisis au clavier" \
    contient t-vide2.ini "cadence = 10 coups en 40 jours"
rm -rf analyse-t-noms-*

titre "T61 : plus de pseudo dans le script"
egal "T61 aide de --pseudos sans valeur en dur" 1 \
    "$(grep -c 'ceux de vos réglages' aide)"
egal "T61 constante du pseudo retirée" 0 "$(grep -c 'PSEUDOS_DEFAUT' "$SCRIPT")"

# --- Prompt d'analyse -------------------------------------------------------

printf '[White "Alice"]\n[Black "Bob"]\n[BlackElo "1500"]\n\n' > t-pr.pgn
printf '1. e4 e5 *\n' >> t-pr.pgn
printf '[joueur]\npseudos = Alice\ncadence = 14 jours\nniveau = 1300\n' \
    > t-pr.ini
# Options des tests du prompt, hors terminal, avec leurs propres réglages.
R="--sans-explorateur --sans-questions --venv $VENV --reglages t-pr.ini"

titre "T64 : prompt écrit à côté de l'archive"
"$SCRIPT" t-pr.pgn $R --profondeur 1 > sortie 2> journal
egal "T64 code de retour" 0 $?
egal "T64 une seule ligne sur la sortie standard" 1 "$(lignes sortie)"
ARCH=$(head -n 1 sortie)
PR="${ARCH%.zip}.prompt.txt"
verifier "T64 le prompt existe à côté de l'archive" test -f "$PR"
verifier "T64 le journal donne son chemin" \
    contient journal "Prompt d'analyse écrit :"
egal "T64 aucun repère du modèle ne reste" 0 "$(grep -c -E '^#!|\{\{' "$PR")"
egal "T64 le prompt n'est pas dans le zip" 0 \
    "$(unzip -l "$ARCH" 2>/dev/null | grep -c prompt)"
verifier "T64 version et archive nommées" \
    contient "$PR" "Prompt produit par IAnalyze v"
verifier "T64 nom de l'archive repris" contient "$PR" "$ARCH"
verifier "T64 pseudo des réglages" \
    contient "$PR" "- pseudo, sur Lichess et en général : Alice"
verifier "T64 camp déduit hors terminal" \
    contient "$PR" "- camp dans cette partie : Blancs"
verifier "T64 niveau déclaré" \
    contient "$PR" "- niveau : environ 1300 Elo, déclaré par le joueur"
verifier "T64 cadence habituelle rédigée" \
    contient "$PR" "celle de la partie : correspondance, 14 jours par coup"
unzip -p "$ARCH" '*/collecte.json' > extrait 2>/dev/null
verifier "T64 collecte.json nomme le prompt" contient extrait '"prompt_ecrit": "analyse-t-pr-'
head -n 12 "$PR" > ligne
joindre ligne
noter "  note   lignes du prompt : $(lignes "$PR")"

titre "T65 : le prompt ne garde que ce qui s'applique"
egal "T65 les chiffres du moteur font foi" 1 \
    "$(grep -c 'Les chiffres de la section 3 font foi' "$PR")"
egal "T65 Stockfish inutile à l'analyste" 1 \
    "$(grep -c 'Stockfish est inutile' "$PR")"
egal "T65 tous les fichiers de l'archive à utiliser" 1 \
    "$(grep -c 'Servez-vous de TOUS les fichiers fournis' "$PR")"
egal "T65 evaluations.json décrit" 1 \
    "$(grep -c '^- stockfish/evaluations.json :' "$PR")"
egal "T65 sans explorateur, ses fichiers ne sont pas annoncés" 0 \
    "$(grep -c '^- explorateur/NNN' "$PR")"
egal "T65 commentaires coupés à 75 colonnes, pas à 76" "2 0" \
    "$(grep -c 'à 75' "$PR") $(grep -c 'à 76' "$PR")"
# Consignes ajoutées après les essais sur quatre LLM : chacune répond à
# un défaut relevé sur un PGN réellement rendu.
for consigne in "9. LIGNES VIDES" \
    "N'écrivez jamais la variante à l'intérieur des accolades" \
    "vous êtes en cas B" \
    "N'annoncez un fichier que si vous l'avez réellement créé" \
    "ne rendez jamais un PGN sans commentaires"; do
    egal "T65 consigne : $consigne" 1 "$(grep -c -F "$consigne" "$PR")"
done
egal "T65 sans explorateur, dit dans le prompt" 1 \
    "$(grep -c "collecte de l'explorateur n'a pas" "$PR")"
egal "T65 sans explorateur, dit dans la tâche" 1 \
    "$(grep -c 'Aucune base n.a été interrogée' "$PR")"
egal "T65 sans explorateur, aucune base annoncée" 0 \
    "$(grep -c 'La base interrogée' "$PR")"
egal "T65 sans explorateur, pas de coups théoriques demandés" 0 \
    "$(grep -c 'trois coups théoriques' "$PR")"
egal "T65 sans explorateur, seule la section 3 fait foi" 1 \
    "$(grep -c 'Seuls les chiffres de la section 3 font foi' "$PR")"
egal "T65 sans explorateur, la section 2 ne fait pas foi" 0 \
    "$(grep -c 'Les chiffres des sections 2 et 3 font foi' "$PR")"
# Le récapitulatif, la balise Opening et la consigne finale renvoyaient
# encore à la section 2, que cette collecte n'a pas.
egal "T65 sans explorateur, aucun renvoi à la section 2" "0 0 0" \
    "$(grep -c 'sortie de théorie)' "$PR") $(grep -c 'sections 2 et 3' "$PR") $(grep -c 'position nommée' "$PR")"
verifier "T65 sans explorateur, la section 3 prime seule" \
    contient "$PR" "Les chiffres de la section 3 priment"
egal "T65 hors terminal, réponses non recueillies" 1 \
    "$(grep -c "n'a pas recueilli les réponses" "$PR")"
"$SCRIPT" t-pr.pgn $R --profondeur 1 --base maitres > sortie 2> journal
PR="$(head -n 1 sortie)"
PR="${PR%.zip}.prompt.txt"
egal "T65 base maîtres nommée en section 2" 1 \
    "$(grep -c 'Section 2, "Explorateur maîtres"' "$PR")"
# Les branches propres à chaque base ne s'écrivent qu'avec l'explorateur :
# le modèle est rendu ici sans collecte, base par base.
SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t65 2> journal-t65 <<'EOF'
import importlib.util
import os
import pathlib

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
modele = pathlib.Path(os.environ["SCRIPT"]).with_name(
    cp.PROMPT_MODELE).read_text(encoding="utf-8")
for base in ("BASE_LICHESS", "BASE_MAITRES"):
    conditions = dict.fromkeys(cp.PROMPT_CONDITIONS, False)
    conditions.update({"EXPLORATEUR": True, base: True})
    rendu = cp.rendre_modele(modele, conditions,
                             dict.fromkeys(cp.PROMPT_VALEURS, "x"), "essai")
    print(base, rendu.count("celle de tous les joueurs de Lichess"),
          rendu.count("celle des maîtres"),
          rendu.count("trois coups théoriques"),
          rendu.count("Aucune base n'a été interrogée"),
          rendu.count("Les chiffres des sections 2 et 3 priment"),
          rendu.count("position nommée de la section"))
EOF
printf 'BASE_LICHESS 1 0 1 0 1 1\nBASE_MAITRES 0 1 1 0 1 1\n' > attendu-t65
verifier "T65 avec explorateur, une seule branche de base" \
    cmp -s attendu-t65 sortie-t65
joindre sortie-t65
joindre journal-t65 5
rm -rf "$DEPOT/__pycache__"

titre "T66 : modèle fautif refusé avant la collecte"
rm -f analyse-t-pr-*
printf 'Bonjour {{PSEUDO}}\n' > t-modele.txt
"$SCRIPT" t-pr.pgn $R --profondeur 1 --prompt t-modele.txt \
    > sortie 2> journal
egal "T66 valeur inconnue, code de retour" 1 $?
verifier "T66 valeur inconnue, ligne et nom donnés" \
    contient journal "t-modele.txt, ligne 1 : valeur inconnue {{PSEUDO}}"
printf 'a\n#! si MOTEUR\nb\n#! fin\n' > t-modele.txt
"$SCRIPT" t-pr.pgn $R --profondeur 1 --prompt t-modele.txt \
    > sortie 2> journal
verifier "T66 condition inconnue" \
    contient journal "ligne 2 : condition inconnue MOTEUR"
printf 'a\n#! si STOCKFISH\nb\n' > t-modele.txt
"$SCRIPT" t-pr.pgn $R --profondeur 1 --prompt t-modele.txt \
    > sortie 2> journal
verifier "T66 si jamais fermé" contient journal "n'est jamais fermé par"
printf 'a\n#! tantque STOCKFISH\n' > t-modele.txt
"$SCRIPT" t-pr.pgn $R --profondeur 1 --prompt t-modele.txt \
    > sortie 2> journal
verifier "T66 directive inconnue" contient journal "directive inconnue"
"$SCRIPT" t-pr.pgn $R --profondeur 1 --prompt /nulle/part.txt \
    > sortie 2> journal
egal "T66 modèle absent, code de retour" 1 $?
verifier "T66 modèle absent, message" \
    contient journal "Modèle de prompt introuvable : /nulle/part.txt"
"$SCRIPT" t-pr.pgn --prompt x --sans-prompt > sortie 2> journal
egal "T66 options exclusives, code de retour" 2 $?
egal "T66 aucun dossier ni archive créés par ces refus" 0 \
    "$(find . -maxdepth 1 -name 'analyse-t-pr-*' | wc -l)"
printf 'Pour {{PSEUDOS}}.\n#! si non EXPLORATEUR\nsans base\n' > t-modele.txt
printf '#! si BASE_LICHESS\nlichess\n#! sinon\nmaitres\n#! fin\n' >> t-modele.txt
printf '#! sinon\navec base\n#! fin\n\n\n\nfin\n' >> t-modele.txt
"$SCRIPT" t-pr.pgn $R --profondeur 1 --prompt t-modele.txt \
    > sortie 2> journal
PR="$(head -n 1 sortie)"
PR="${PR%.zip}.prompt.txt"
printf 'Pour Alice.\nsans base\nlichess\n\nfin\n' > attendu
verifier "T66 emboîtement, négation et lignes vides resserrées" \
    cmp -s attendu "$PR"
joindre "$PR"
rm -f analyse-t-pr-*
"$SCRIPT" t-pr.pgn $R --profondeur 1 --sans-prompt > sortie 2> journal
egal "T66 --sans-prompt, code de retour" 0 $?
egal "T66 --sans-prompt, aucun prompt écrit" 0 \
    "$(find . -maxdepth 1 -name 'analyse-t-pr-*.prompt.txt' | wc -l)"

# Trois modèles que le script acceptait à tort : un repère mal écrit, qui
# partait tel quel dans le prompt, un modèle sans une ligne de texte, et
# un modèle de prompt seul dont la partie n'est citée que dans une note.
printf 'Camp : {{ CAMP }}\n' > t-modele-espace.txt
printf 'Camp : {{CAMP1}}\n' > t-modele-chiffre.txt
printf '#! note rien\n\n' > t-modele-vide.txt
printf '#! note {{PARTIE_PGN}}\nAnalysez.\n' > t-modele-note.txt
for cas in "t-modele-espace.txt|repère mal formé" \
           "t-modele-chiffre.txt|repère mal formé" \
           "t-modele-vide.txt|aucune ligne de texte"; do
    lancer t-pr.pgn $R --profondeur 1 --prompt "${cas%%|*}"
    egal "T66 ${cas%%|*}, code de retour" 1 "$RC"
    verifier "T66 ${cas%%|*}, message" contient journal "${cas##*|}"
done
lancer t-pr.pgn $R --profondeur 1 --prompt-seul --prompt t-modele-note.txt
egal "T66 partie citée dans une note, code de retour" 1 "$RC"
verifier "T66 partie citée dans une note, message" \
    contient journal "ne contient pas {{PARTIE_PGN}}"
# La partie placée sous une condition fausse : le prompt est écrit, mais
# le journal dit qu'il ne peut pas être collé seul.
printf '#! si BASE_MAITRES\n{{PARTIE_PGN}}\n#! fin\nAnalysez.\n' > t-modele-branche.txt
lancer t-pr.pgn $R --profondeur 1 --prompt-seul --prompt t-modele-branche.txt
egal "T66 partie sous une condition fausse, code de retour" 0 "$RC"
verifier "T66 partie sous une condition fausse, dit au journal" \
    contient journal "ne porte pas la partie"
egal "T66 partie sous une condition fausse, pas d'annonce contraire" 0 \
    "$(grep -c 'il porte la partie' journal)"
rm -f analyse-t-pr-*

titre "T67 : script copié sans son modèle"
mkdir t-seul
cp "$SCRIPT" t-seul/
rm -f analyse-t-pr-*
t-seul/ianalyze.py t-pr.pgn $R --profondeur 1 > sortie 2> journal
egal "T67 code de retour" 0 $?
verifier "T67 l'archive est produite" test -f "$(head -n 1 sortie)"
verifier "T67 avertissement du journal" \
    contient journal "modèle de prompt introuvable"
egal "T67 aucun prompt écrit" 0 \
    "$(find . -maxdepth 1 -name 'analyse-t-pr-*.prompt.txt' | wc -l)"

titre "T68 : niveau en points Elo, vérifié"
printf '[joueur]\npseudos = Alice\ncadence = 14 jours\nniveau = fort\n' \
    > t-niv.ini
rm -rf analyse-t-pr-*
SCRIPT="$SCRIPT" python3 t-pty.py "abc|50|9999|1450|||||" t-pr.pgn $P \
    --reglages t-niv.ini > sortie-pty 2>&1
verifier "T68 niveau illisible des réglages redemandé" \
    contient sortie-pty "n'est pas lisible, il est redemandé"
egal "T68 trois réponses refusées" 3 \
    "$(grep -c 'entre 100 et 3500' sortie-pty)"
verifier "T68 niveau enregistré" contient t-niv.ini "niveau = 1450"
cat analyse-t-pr-*.prompt.txt > extrait 2>/dev/null
verifier "T68 niveau déclaré dans le prompt" \
    contient extrait "- niveau : environ 1450 Elo, déclaré par le joueur"
verifier "T68 sur un terminal, réponses recueillies" \
    contient extrait "contient les réponses du joueur"
egal "T68 pas d'erreur inattendue" 0 "$(grep -c 'Erreur inattendue' sortie-pty)"
printf '[joueur]\npseudos = Bob\ncadence = 14 jours\nniveau = inconnu\n' \
    > t-niv.ini
rm -rf analyse-t-pr-*
"$SCRIPT" t-pr.pgn --sans-explorateur --sans-questions --profondeur 1 \
    --venv "$VENV" --reglages t-niv.ini > sortie 2> journal
cat analyse-t-pr-*.prompt.txt > extrait 2>/dev/null
verifier "T68 camp déduit de l'autre pseudo" \
    contient extrait "- camp dans cette partie : Noirs"
verifier "T68 sans niveau déclaré, Elo de la balise" \
    contient extrait "- niveau : 1500 Elo, d'après la balise BlackElo de la partie"
rm -rf analyse-t-pr-*

titre "T74 : prompt seul, court, à coller sans pièce jointe"

# Avec --prompt-seul, le prompt est tiré d'un modèle court : quelques
# consignes, la partie, puis les évaluations du moteur. Il se colle seul
# dans la conversation. Rien d'autre n'est écrit : ni archive, ni
# dossier de travail, et la sortie standard donne le chemin du prompt.
printf '[White "Alice"]\n[Black "Bob"]\n[Result "1-0"]\n\n' > t-seul.pgn
printf '1. e4 e5 2. Qh5 Nc6 3. Qxf7+ Kxf7 1-0\n' >> t-seul.pgn
S74="--sans-explorateur --sans-questions --venv $VENV --reglages t-pr.ini"
S74="$S74 --profondeur 8 --fils 2 --hachage 32"
"$SCRIPT" t-seul.pgn $S74 --prompt-seul > sortie 2> journal
egal "T74 code de retour" 0 $?
PR="$(head -n 1 sortie)"
verifier "T74 la sortie standard donne le prompt" test -f "$PR"
egal "T74 un seul fichier écrit, ni archive ni dossier" \
    "analyse-t-seul-.prompt.txt" \
    "$(ls -d analyse-t-seul-* | sed 's/[0-9]\{8\}-[0-9]\{6\}//')"
verifier "T74 le journal dit qu'aucune archive n'est écrite" \
    contient journal "aucune archive n'est écrite"
verifier "T74 le journal dit de le coller seul" \
    contient journal "à coller seul dans la conversation"
egal "T74 aucun repère du modèle ne reste" 0 "$(grep -c -E '^#!|\{\{' "$PR")"
verifier "T74 prompt court, moins de cent lignes" \
    test "$(lignes "$PR")" -lt 100
while IFS= read -r present; do
    verifier "T74 présent : $present" contient "$PR" "$present"
done <<'FIN'
Vous êtes Maître International d'échecs.
Le joueur avait les Blancs.
dans un seul bloc de code
hors des accolades
La partie :
[White "Alice"]
Évaluations de Stockfish, profondeur 8
FIN
while IFS= read -r absent; do
    egal "T74 absent : $absent" 0 "$(grep -c -F "$absent" "$PR")"
done <<'FIN'
IAnalyze
archive
synthese.md
Données brutes
CAS A
FIN
# Le tableau compte une ligne par demi-coup, et la dame donnée au coup 3
# y est une gaffe, suivie du meilleur coup et de sa suite.
egal "T74 tableau : une ligne par demi-coup" 6 \
    "$(grep -c -E '^[1-3]\.(\.\.)? [A-Za-z0-9+#x=-]+ +[+#-]' "$PR")"
egal "T74 tableau : gaffe, écart et meilleur coup" 1 \
    "$(grep -c -E '^3\. Qxf7\+ .* gaffe \([0-9a-z]+\) : mieux 3\. ' "$PR")"
# Notée 1-0, la partie finit avec une dame de moins pour les Blancs.
egal "T74 résultat contraire à l'évaluation, dit au LLM" 1 \
    "$(grep -c '^Attention : Résultat et évaluation finale' "$PR")"
# Le bilan demande trois erreurs. Un LLM à qui l'on en réclame trois en
# invente une quand le joueur en a commis moins : le prompt donne alors le
# nombre de coups faibles que porte son tableau. Les Blancs n'ont joué que
# trois coups, et le moteur ne juge pas toujours les mêmes faibles d'une
# machine à l'autre : le compte attendu se lit dans le tableau du prompt.
FAIBLES74="$(grep -c -E '^[0-9]+\. .* (imprécision|erreur|gaffe) \(' "$PR")"
if [ "$FAIBLES74" -lt 3 ]; then
    verifier "T74 bilan : le nombre de coups faibles du joueur est donné" \
        contient "$PR" "Coups faibles du joueur dans le tableau : $FAIBLES74."
    egal "T74 bilan : une seule des deux phrases" 0 \
        "$(grep -c 'les trois erreurs' "$PR")"
else
    verifier "T74 bilan : trois coups faibles, trois erreurs demandées" \
        contient "$PR" "les trois erreurs"
    egal "T74 bilan : une seule des deux phrases" 0 \
        "$(grep -c 'Coups faibles du joueur' "$PR")"
fi
# Avec --garder-dossier, le dossier de travail reste, sans archive :
# verifier-analyse.py peut le lire, avec les chiffres mêmes du prompt.
rm -f analyse-t-seul-*
"$SCRIPT" t-seul.pgn $S74 --prompt-seul --garder-dossier \
    > sortie 2> journal
PR="$(head -n 1 sortie)"
DOSSIER74="${PR%.prompt.txt}"
verifier "T74 --garder-dossier, les évaluations restent" \
    test -f "$DOSSIER74/stockfish/evaluations.json"
egal "T74 --garder-dossier, toujours aucune archive" 0 \
    "$(find . -maxdepth 1 -name 'analyse-t-seul-*.zip' | wc -l)"
cp "$DOSSIER74/partie.pgn" t-partie.pgn
rm -rf "$DOSSIER74"
verifier "T74 PGN de la collecte repris tel quel" \
    "$PYVENV" -c '
import sys
prompt = open(sys.argv[1], encoding="utf-8").read()
partie = open(sys.argv[2], encoding="utf-8").read().strip("\n")
sys.exit(0 if partie in prompt else 1)
' "$PR" t-partie.pgn
egal "T74 sans consignes, rien n'est précisé" 0 \
    "$(grep -c 'Ce que le joueur a précisé' "$PR")"
noter "  note   taille du prompt seul : $(wc -c < "$PR") octets, $(lignes "$PR") lignes"
head -n 6 "$PR" > ligne
joindre ligne
rm -f analyse-t-seul-*
# Ce que le prompt court reprend des réponses du joueur : celles qu'il
# n'a pas laissées par défaut, sans le camp, dit ailleurs.
SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t74 2> journal-t74 <<'EOF'
import importlib.util
import os

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
print(cp.consignes_joueur(
    "## Contexte\n"
    "- Camp du joueur : Blancs\n"
    "- Périmètre : la partie complète (défaut)\n"
    "- Objectif : la sortie de la dame\n"
    "- Contexte particulier : rien (défaut)\n"))
print("[%s]" % cp.consignes_joueur(None))
print("[%s]" % cp.consignes_joueur(
    "- Cadence : balise TimeControl `600+5`, soit rapide\n"
    "- Cadence : non précisée\n"))
EOF
printf '%s\n' "- Objectif : la sortie de la dame" "[]" "[]" > attendu-t74
verifier "T74 réponses du joueur reprises, défauts, camp et balise écartés" \
    cmp -s attendu-t74 sortie-t74
joindre journal-t74 5
rm -rf "$DEPOT/__pycache__"
# Le compte des coups faibles, sans moteur. Sa règle est celle du tableau :
# un coup n'y est marqué que s'il a une nature et un meilleur coup. Le
# modèle court change de phrase quand le joueur en compte moins de trois.
SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t74 2> journal-t74 <<'EOF'
import importlib.util
import os
import pathlib

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)


def coup(trait, nature, meilleurs=("x",)):
    return {"trait": trait, "nature": nature, "meilleurs": list(meilleurs)}


resultats = [coup("Blancs", None), coup("Noirs", "gaffe"),
             coup("Blancs", "erreur"), coup("Noirs", "imprécision"),
             coup("Blancs", "gaffe"), coup("Blancs", "erreur", ()),
             coup("Blancs", "imprécision")]
print(cp.coups_faibles_joueur(resultats, "Blancs"),
      cp.coups_faibles_joueur(resultats, "Noirs"),
      cp.coups_faibles_joueur(resultats, None),
      cp.coups_faibles_joueur([], "Blancs"))
modele = pathlib.Path(os.environ["SCRIPT"]).with_name(
    cp.PROMPT_SEUL_MODELE).read_text(encoding="utf-8")
# Quatre cas : aucun coup faible, moins de trois, trois ou plus, et un
# camp inconnu, où "le joueur" n'est d'aucun camp.
for cas, vraies in (("aucun", ("CAMP_CONNU", "PEU_DE_COUPS_FAIBLES",
                               "AUCUN_COUP_FAIBLE")),
                    ("peu", ("CAMP_CONNU", "PEU_DE_COUPS_FAIBLES")),
                    ("trois", ("CAMP_CONNU",)),
                    ("inconnu", ())):
    conditions = dict.fromkeys(cp.PROMPT_CONDITIONS, False)
    conditions.update(dict.fromkeys(vraies, True))
    valeurs = dict.fromkeys(cp.PROMPT_VALEURS, "x")
    valeurs["COUPS_FAIBLES_JOUEUR"] = "2"
    rendu = cp.rendre_modele(modele, conditions, valeurs, "essai")
    print(cas, rendu.count("ne marque aucun coup faible du joueur"),
          rendu.count("Coups faibles du joueur dans le tableau : 2."),
          rendu.count("sans en ajouter"), rendu.count("les trois erreurs"),
          rendu.count("pour chaque camp"),
          rendu.count("Le camp du joueur n'est pas connu"))
EOF
printf '3 2 None 0\naucun 1 0 0 0 0 0\npeu 0 1 1 0 0 0\n' > attendu-t74
printf 'trois 0 0 0 1 0 0\ninconnu 0 0 0 0 1 1\n' >> attendu-t74
verifier "T74 bilan : compte des coups faibles, phrase selon le compte" \
    cmp -s attendu-t74 sortie-t74
joindre sortie-t74
joindre journal-t74 5
rm -rf "$DEPOT/__pycache__"
# Un PGN terminé par une espace : le prompt porte bien la partie, et le
# journal ne doit pas annoncer le contraire.
printf '[White "Alice"]\n[Black "Bob"]\n\n1. e4 e5 * ' > t-espace.pgn
"$SCRIPT" t-espace.pgn $S74 --prompt-seul > sortie 2> journal
egal "T74 PGN fini par une espace, aucune fausse alerte" "0 1" \
    "$(grep -c 'ne porte pas la partie' journal) $(grep -c 'à coller seul dans la conversation' journal)"
rm -f analyse-t-espace-*
# Deux lancements dans la même seconde portaient le même nom : le second
# prompt écrasait le premier. Six lancements, six fichiers.
mkdir -p t-meme-seconde
for essai in 1 2 3 4 5 6; do
    "$SCRIPT" t-espace.pgn --sans-explorateur --sans-questions \
        --venv "$VENV" --reglages t-pr.ini --profondeur 1 --fils 1 \
        --hachage 16 --prompt-seul --sortie t-meme-seconde \
        > /dev/null 2>> journal || noter "  note   lancement $essai en échec"
done
egal "T74 lancements rapprochés, aucun prompt écrasé" 6 \
    "$(find t-meme-seconde -name '*.prompt.txt' | wc -l)"
rm -rf t-meme-seconde
"$SCRIPT" t-seul.pgn $S74 > sortie 2> journal
PR="$(head -n 1 sortie)"
PR="${PR%.zip}.prompt.txt"
egal "T74 sans l'option, le prompt complet" "0 1" \
    "$(grep -c '^La partie :' "$PR") $(grep -c 'PIÈCES JOINTES ATTENDUES' "$PR")"
# verifier-analyse.py --prompt-seul attend les balises de la partie
# d'origine, et non les sept du standard : t-seul.pgn n'en porte que trois,
# et sa copie fidèle ne doit pas être prise en faute. Les mêmes balises
# rendues dans un autre ordre, elles, le sont.
ARCH74="$(head -n 1 sortie)"
"$PYVENV" "$DEPOT/verifier-analyse.py" "$ARCH74" t-seul.pgn --prompt-seul \
    > bilan 2>&1
verifier "T74 vérificateur : trois balises recopiées, aucune faute" \
    contient bilan "OK        les balises obligatoires de la partie d'origine"
printf '[Black "Bob"]\n[White "Alice"]\n[Result "1-0"]\n\n' > t-seul-inverse.pgn
printf '1. e4 e5 2. Qh5 Nc6 3. Qxf7+ Kxf7 1-0\n' >> t-seul-inverse.pgn
"$PYVENV" "$DEPOT/verifier-analyse.py" "$ARCH74" t-seul-inverse.pgn \
    --prompt-seul > bilan 2>&1
verifier "T74 vérificateur : balises dans un autre ordre, relevé" \
    contient bilan "ECHEC     les balises obligatoires de la partie d'origine"
rm -rf "$DEPOT/__pycache__"
rm -f analyse-t-seul-*
"$SCRIPT" t-seul.pgn $S74 --prompt-seul --sans-prompt > sortie 2> journal
egal "T74 options exclusives, code de retour" 2 $?
verifier "T74 options exclusives, message" \
    contient journal "--prompt-seul et --sans-prompt s'excluent"
# Un modèle personnel qui ne place pas la partie est refusé avant la
# collecte : le prompt n'aurait rien à faire analyser.
printf 'Bonjour {{PSEUDOS}}.\n' > t-modele.txt
"$SCRIPT" t-seul.pgn $S74 --prompt t-modele.txt --prompt-seul \
    > sortie 2> journal
egal "T74 modèle sans la partie, code de retour" 1 $?
verifier "T74 modèle sans la partie, message" \
    contient journal "ne contient pas {{PARTIE_PGN}}"
mkdir -p t-seul-74 && cp "$SCRIPT" t-seul-74/
t-seul-74/ianalyze.py t-seul.pgn $S74 --prompt-seul \
    > sortie 2> journal
egal "T74 script copié sans son modèle, code de retour" 1 $?
verifier "T74 script copié sans son modèle, message" \
    contient journal "Modèle de prompt introuvable"
egal "T74 aucun dossier ni archive créés par ces refus" 0 \
    "$(find . -maxdepth 1 -name 'analyse-t-seul-*' | wc -l)"

titre "T03 : options refusées"

# Une option sans effet ou hors bornes est refusée, code 2, avant toute
# lecture de la partie. Chaque ligne donne les options, puis le message.
while IFS='|' read -r refusees message; do
    # Les options sont découpées en mots, d'où l'absence de guillemets.
    # shellcheck disable=SC2086
    "$SCRIPT" italienne.pgn $refusees --venv "$VENV" > sortie 2> journal
    egal "T03 $refusees, code de retour" 2 "$?"
    verifier "T03 $refusees, message" contient journal "$message"
done <<'FIN'
--base maitres --cadences rapid|--cadences n'a d'effet qu'avec --base lichess
--base lichess --cadences rapide|--cadences : valeur inconnue "rapide"
--base lichess --classements 1100|--classements : valeur inconnue "1100"
--coups-min -1|--coups-min doit valoir 0 ou plus
--pause 1|--pause ne doit pas descendre sous 2 secondes
--seuil-frequence 150|--seuil-frequence doit être compris entre 0 et 100
--base plebe|argument --base: invalid choice: 'plebe'
FIN

titre "T04 : fichier PGN introuvable"

lancer "$TRAVAIL/inexistant.pgn" $O
egal "T04 chemin absolu, code de retour" 1 "$RC"
verifier "T04 chemin absolu, message" \
    contient journal "Fichier PGN introuvable"
lancer inexistant.pgn $O
egal "T04 nom relatif, code de retour" 1 "$RC"
verifier "T04 nom relatif, pris pour un fichier et non pour un identifiant" \
    contient journal "Fichier PGN introuvable"

titre "T75 : PGN que python-chess lirait de travers, refusés"

# Chacun de ces fichiers est lu sans erreur par python-chess, qui saute ce
# qu'il ne reconnaît pas : notation française lue comme des coups de pion,
# partie tronquée à l'accolade jamais fermée. Le script doit les refuser
# avant la lecture, et nommer ce qui l'arrête.
printf '1. e4 e5 2. Cf3 Cc6 3. Fc4 Fc5 *\n' > t-francais.pgn
printf '1. e4 e5 2. \342\231\230f3 *\n' > t-figurines.pgn
printf '1. e4 e5 2. nf3 nc6 *\n' > t-minuscules.pgn
printf '1. e4 e5 2. Nf3 { bon coup Nc6 3. Bb5 a6 1-0\n' > t-accolade.pgn
printf '1. e4 e5 ( 1... c5 ( 1... d5\n' > t-parenthese.pgn
printf '1. e4 e5 2. Ke3 ) $2 *\n' > t-orpheline.pgn
printf '1. e4 e5 2. Nf3 *\n\nLes Blancs gagnent (voir b5) !\n' > t-queue.pgn
while read -r fichier cause; do
    lancer "$fichier" $O < /dev/null
    egal "T75 $fichier, code de retour" 1 "$RC"
    verifier "T75 $fichier, refusé comme PGN corrompu" \
        contient journal "PGN corrompu"
    verifier "T75 $fichier, cause nommée" contient journal "$cause"
    egal "T75 $fichier, pas d'erreur inattendue" 0 \
        "$(grep -c 'Erreur inattendue' journal)"
done <<'FIN'
t-francais.pgn "Cf3"
t-figurines.pgn notation anglaise
t-minuscules.pgn "nf3"
t-accolade.pgn jamais fermé
t-parenthese.pgn jamais fermée
t-orpheline.pgn sans variante ouverte
t-queue.pgn "Les"
FIN
joindre journal 3
egal "T75 aucun dossier ni archive créés par ces refus" 0 \
    "$(ls -d analyse-t-francais* analyse-t-accolade* analyse-t-queue* 2>/dev/null | wc -l)"
# Un fichier à plusieurs parties est refusé lui aussi, avec leur nombre.
printf '[Event "a"]\n\n1. e4 e5 1-0\n\n[Event "b"]\n\n1. d4 d5 0-1\n' > t-deux.pgn
printf '\n[Event "c"]\n\n1. c4 *\n' >> t-deux.pgn
lancer t-deux.pgn $O
egal "T75 plusieurs parties, code de retour" 1 "$RC"
verifier "T75 plusieurs parties, nombre annoncé" \
    contient journal "Le PGN contient 3 parties"
egal "T75 plusieurs parties, rien n'est écrit" 0 \
    "$(ls -d analyse-t-deux* 2>/dev/null | wc -l)"
# Ce qui doit continuer à passer : coups collés au numéro, signes
# d'appréciation, NAG, roque écrit avec des zéros, commentaire de fin de
# ligne.
printf '1.e4 e5 2.Nf3! Nc6?! 3.Bc4 $1 Bc5 { ok } 4. c3 ; fin\n' > t-formes.pgn
printf '4... Nf6 5. 0-0 0-0 *\n' >> t-formes.pgn
lancer t-formes.pgn $O
egal "T75 formes admises, code de retour" 0 "$RC"

titre "T77 : entrées qui finissaient en erreur inattendue"

# Entrée standard fermée par l'appelant, sans --sans-questions : ce n'est
# pas un terminal, aucune question n'est posée et la collecte se fait.
"$SCRIPT" italienne.pgn --sans-explorateur --profondeur 1 \
    --venv "$VENV" --reglages "$REGL" <&- > sortie 2> journal
egal "T77 entrée standard fermée, code de retour" 0 "$?"
verifier "T77 entrée standard fermée, questions sautées" \
    contient journal "terminal non interactif"
rm -rf analyse-italienne-*
# Un nom de fichier que le système refuse de regarder, ici trop long.
lancer "$(printf '%0300d' 0).pgn" $O
egal "T77 nom trop long, code de retour" 1 "$RC"
verifier "T77 nom trop long, fichier introuvable" \
    contient journal "Fichier PGN introuvable"
# Une URL aux crochets mal placés.
lancer 'https://[lichess.org]/abcdefgh' $O
egal "T77 URL mal formée, code de retour" 1 "$RC"
verifier "T77 URL mal formée, refusée" contient journal "URL non reconnue"
# Une partie qui part d'une balise FEN n'est pas une partie entière :
# elle est refusée, quelle que soit la position. La position initiale
# écrite en toutes lettres, elle, reste une partie entière.
printf '[SetUp "1"]\n[FEN "6k1/5ppp/8/8/8/8/5PPP/3Q2K1 b - - 0 30"]\n\n' > t-depuis-fen.pgn
printf '30... h6 31. Qd8+ Kh7 *\n' >> t-depuis-fen.pgn
lancer t-depuis-fen.pgn $O
egal "T77 partie depuis une FEN, code de retour" 1 "$RC"
verifier "T77 partie depuis une FEN, refusée" \
    contient journal "ne commence pas à la position initiale"
egal "T77 partie depuis une FEN, rien n'est écrit" 0 \
    "$(ls -d analyse-t-depuis-fen* 2>/dev/null | wc -l)"
printf '[SetUp "1"]\n' > t-fen-initiale.pgn
printf '[FEN "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"]\n\n' >> t-fen-initiale.pgn
printf '1. e4 e5 *\n' >> t-fen-initiale.pgn
lancer t-fen-initiale.pgn $O
egal "T77 FEN de la position initiale, acceptée" 0 "$RC"
# Chemins et sources mal reconnus : tilde non développé, adresse au
# schéma en majuscules, rubrique de Lichess ou répertoire de huit lettres
# pris pour une partie.
HOME="$TRAVAIL/maison" "$SCRIPT" italienne.pgn $O --venv "$VENV" \
    --reglages "$REGL" --sortie='~/analyses' > sortie 2> journal
egal "T77 tilde de --sortie, code de retour" 0 "$?"
verifier "T77 tilde de --sortie développé" \
    test -f "$TRAVAIL/maison/analyses/$(basename "$(head -n 1 sortie)")"
egal "T77 aucun répertoire nommé ~" 0 "$(ls -d ./~ 2>/dev/null | wc -l)"
mkdir -p abcdefgh
for source in abcdefgh 'HTTPS://lichess.org/Analysis' Features \
              https://lichess.org/insights; do
    lancer "$source" $O
    egal "T77 $source, code de retour" 1 "$RC"
    egal "T77 $source, aucun téléchargement" 0 \
        "$(grep -c 'chargement du PGN' journal)"
    cat journal >> journal-t77b
done
verifier "T77 répertoire nommé comme un identifiant" \
    contient journal-t77b "est un répertoire, pas un fichier PGN"
verifier "T77 schéma en majuscules reconnu comme une URL" \
    contient journal-t77b "URL non reconnue"
cat journal > journal-t77
egal "T77 aucune erreur inattendue" 0 \
    "$(cat journal-t77 journal | grep -c 'Erreur inattendue')"

titre "T06, T08 : dossier gardé, répertoire de sortie"

rm -rf analyse-italienne-*
lancer italienne.pgn $O --garder-dossier
egal "T06 code de retour" 0 "$RC"
verifier "T06 le dossier reste à côté de l'archive" test -d "${ARCH%.zip}"
rm -rf analyse-italienne-*
lancer italienne.pgn $O --sortie "$TRAVAIL/t-sortie/neuf"
egal "T08 code de retour" 0 "$RC"
verifier "T08 répertoire de sortie créé au besoin" \
    test -d "$TRAVAIL/t-sortie/neuf"
verifier "T08 archive écrite dans ce répertoire" test -f "$ARCH"
rm -rf analyse-italienne-*

titre "T81 : purge combinée, modèle vide, jeton mal écrit"
cp "$REGL" t-purge.ini
"$SCRIPT" --purge-reglages --installer-venv --venv "$VENV" \
    --reglages t-purge.ini > sortie 2> journal
egal "T81 purge avec une autre action, code de retour" 2 "$?"
verifier "T81 purge avec une autre action, message" \
    contient journal "--purge-reglages s'emploie seule"
verifier "T81 purge avec une autre action, fichier intact" test -f t-purge.ini
lancer italienne.pgn $O --prompt ""
egal "T81 --prompt vide, code de retour" 2 "$RC"
verifier "T81 --prompt vide, message" contient journal "--prompt : chemin vide"
# Le jeton est factice. Les collectes s'arrêtent à sa lecture, avant le
# catalogue et avant toute requête.
for contenu in 'LICHESS_TOKEN=lip_factice' '"lip_factice"' "'lip_factice'"; do
    printf '%s\n' "$contenu" > t-jeton-faux
    chmod 600 t-jeton-faux
    lancer italienne.pgn --sans-questions --profondeur 1 \
        --jeton-fichier t-jeton-faux --catalogue "$TRAVAIL/nulle-part"
    egal "T81 jeton écrit $contenu, code de retour" 1 "$RC"
    verifier "T81 jeton écrit $contenu, refusé" \
        contient journal "doit contenir le jeton seul"
    egal "T81 jeton écrit $contenu, non affiché" 0 \
        "$(grep -c 'lip_factice' journal)"
done

titre "T27 : fichier de jeton absent"

lancer italienne.pgn --sans-questions --profondeur 1 \
    --jeton-fichier /nulle/part
egal "T27 code de retour" 1 "$RC"
verifier "T27 message" contient journal "Jeton absent : /nulle/part"
egal "T27 aucun dossier de travail créé" 0 \
    "$(find . -maxdepth 1 -type d -name 'analyse-italienne-*' | wc -l)"

titre "T69 : purge des réglages"

printf '[joueur]\npseudos = Alice\n' > t-purge.ini
mkdir -p t-rep
"$SCRIPT" --purge-reglages --reglages t-purge.ini > sortie 2> journal
egal "T69 fichier présent, code de retour" 0 "$?"
verifier "T69 suppression annoncée" \
    contient journal "Réglages supprimés : t-purge.ini"
verifier "T69 le fichier n'existe plus" test ! -e t-purge.ini
egal "T69 sortie standard vide" 0 "$(wc -c < sortie)"
"$SCRIPT" --purge-reglages --reglages t-purge.ini > sortie 2> journal
egal "T69 fichier absent, code de retour" 0 "$?"
verifier "T69 fichier absent, annoncé" \
    contient journal "Aucun fichier de réglages à supprimer"
"$SCRIPT" --purge-reglages --reglages t-rep > sortie 2> journal
egal "T69 répertoire, code de retour" 1 "$?"
verifier "T69 répertoire refusé" contient journal "n'est pas un fichier"
verifier "T69 le répertoire est toujours là" test -d t-rep
# Une faute de frappe derrière --reglages ne doit pas détruire un autre
# fichier : seul un fichier portant la section [joueur], ou vide, part.
printf '[White "Alice"]\n\n1. e4 e5 *\n' > t-pas-reglages.pgn
"$SCRIPT" --purge-reglages --reglages t-pas-reglages.pgn > sortie 2> journal
egal "T69 autre fichier, code de retour" 1 "$?"
verifier "T69 autre fichier refusé" \
    contient journal "n'est pas un fichier de réglages"
verifier "T69 l'autre fichier est toujours là" test -f t-pas-reglages.pgn
printf 'pseudos = Alice\n[joueur\n[joueur]\n' > t-purge.ini
"$SCRIPT" --purge-reglages --reglages t-purge.ini > sortie 2> journal
egal "T69 réglages abîmés, supprimés quand même" "0 0" \
    "$? $(find . -maxdepth 1 -name t-purge.ini | wc -l)"
: > t-purge.ini
"$SCRIPT" --purge-reglages --reglages t-purge.ini > sortie 2> journal
egal "T69 fichier vide, supprimé" "0 0" \
    "$? $(find . -maxdepth 1 -name t-purge.ini | wc -l)"
joindre journal


titre "T71 : options retirées"

"$SCRIPT" italienne.pgn --sans-stockfish > sortie 2> journal
egal "T71 --sans-stockfish, code de retour" 2 "$?"
verifier "T71 --sans-stockfish, option inconnue" \
    contient journal "unrecognized arguments: --sans-stockfish"

"$SCRIPT" italienne.pgn --avec-stockfish > sortie 2> journal
egal "T71 code de retour" 2 "$?"
verifier "T71 option inconnue" \
    contient journal "unrecognized arguments: --avec-stockfish"
egal "T71 aide muette sur l'option" 0 \
    "$("$SCRIPT" --help 2>/dev/null | grep -c -- --avec-stockfish)"

# --consignes, retirée à son tour : le prompt porte les consignes, et les
# questions de démarrage le contexte.
echo "Annotez en français." > t-consignes.md
"$SCRIPT" italienne.pgn --consignes t-consignes.md > sortie 2> journal
egal "T71 --consignes, code de retour" 2 "$?"
verifier "T71 --consignes, option inconnue" \
    contient journal "unrecognized arguments: --consignes"
egal "T71 --consignes, aide muette" 0 \
    "$("$SCRIPT" --help 2>/dev/null | grep -c -- --consignes)"


# --- Moteur -----------------------------------------------------------------

# Liste des processus du moteur, sur une ligne. Elle est relevée avant et
# après les tests du moteur : seule une différence trahit un processus
# laissé par le script. Un moteur déjà lancé par un autre programme, une
# interface d'échecs par exemple, ne fausse ainsi plus le contrôle.
processus_moteur() {
    # Par le nom du processus, et non par sa ligne de commande : pgrep -f
    # retenait aussi tout shell dont la commande citait le chemin du
    # moteur, d'où de faux échecs.
    pgrep -x "$(basename "$STOCKFISH")" 2>/dev/null | sort | tr '\n' ' '
}

# La condition est toujours vraie depuis que le script s'arrête au départ
# sans moteur. Elle est gardée pour ne pas réindenter tout le bloc.
if [ -n "$STOCKFISH" ] && [ -x "$STOCKFISH" ]; then
    MOTEUR="--sans-explorateur --sans-questions --stockfish $STOCKFISH"
    MOTEURS_AVANT=$(processus_moteur)
    noter ""
    noter "  note   processus du moteur déjà présents : [${MOTEURS_AVANT}]"
    RAPIDE="--profondeur 8 --fils 2 --hachage 32"

    titre "T51 : mat manqué et mat concédé"
    printf '1. f3 e5 2. g4 Nc6 *\n' > t-mat.pgn
    lancer t-mat.pgn $MOTEUR $RAPIDE
    egal "T51 code de retour" 0 "$RC"
    extraire '*/synthese.md'
    grep -E '^\| [34] \|' extrait > lignes 2>/dev/null
    egal "T51 lignes 3 et 4 portent mat et gaffe" 2 \
        "$(grep -c '| mat | gaffe |' lignes)"
    # Un mat se compte après le coup de la ligne : 2. g4 laisse aux Noirs
    # un mat en un, "#-1", et le coup qui le donnerait, Qh4#, vaut "#-0".
    verifier "T51 Qh4# en premier choix, mat donné" \
        contient lignes "Qh4# (#-0)"
    egal "T51 après 2. g4, mat en un pour les Noirs" 1 \
        "$(grep -c -E '^\| 3 \|.*\| g4 \| #-1 \|' lignes)"
    verifier "T51 légende des mats" contient extrait \
        "le compte se lit après le coup de la ligne"
    verifier "T51 phrase d'explication" contient extrait "Écart \`mat\`"
    verifier "T51 écart négatif expliqué" contient extrait \
        "Négatif, il ne signale aucune faute"
    egal "T51 titre d'une partie sans balise Site" 1 \
        "$(grep -c "^# Dossier d'analyse : partie locale" extrait)"
    egal "T51 sans explorateur, son dossier n'est pas annoncé" 0 \
        "$(grep -c 'explorateur/NNN' extrait)"
    # Écart entre le premier choix et le coup joué, calculé à part : deux
    # mats de même sens ne donnent pas un écart d'un centipion.
    SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t51 2> journal-t51 <<'EOF'
import importlib.util
import os

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
for meilleur, joue in ((99999, 99998), (-99998, -99999), (99999, 300),
                       (50, 80), (120, -40), (300, -99999)):
    ecart = cp.ecart_au_meilleur(float(meilleur), float(joue))
    print(meilleur, joue, cp._ecart(ecart), cp.nature_coup(ecart))
EOF
    cat > attendu-t51 <<'EOF'
99999 99998 0 None
-99998 -99999 0 None
99999 300 mat gaffe
50 80 -30 None
120 -40 160 erreur
300 -99999 mat gaffe
EOF
    verifier "T51 écarts : deux mats, mat manqué, écart négatif" \
        cmp -s attendu-t51 sortie-t51
    joindre sortie-t51
    joindre journal-t51 5
    # Le moteur compte un mat avant le coup, celui-ci compris : le camp
    # qui mate en a un de moins à jouer une fois son coup joué, le camp
    # maté n'en retire aucun. Sans camp donné, le compte du moteur reste.
    SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t51 2> journal-t51 <<'EOF'
import importlib.util
import os

import chess
import chess.engine

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)


def mat(coups, camp):
    return chess.engine.PovScore(chess.engine.Mate(coups), camp)


B, N = chess.WHITE, chess.BLACK
print(cp.formater_score(mat(2, B), B), cp.formater_score(mat(1, B), B),
      cp.formater_score(mat(-2, B), B), cp.formater_score(mat(3, N), N),
      cp.formater_score(mat(1, N), N), cp.formater_score(mat(-1, N), N),
      cp.formater_score(mat(2, B)),
      cp.formater_score(chess.engine.PovScore(chess.engine.Cp(35), N), N))
EOF
    printf '%s\n' "#+1 #+0 #-2 #-2 #-0 #+1 #+2 -0.35" > attendu-t51
    verifier "T51 mats comptés après le coup, camp qui mate et camp maté" \
        cmp -s attendu-t51 sortie-t51
    joindre sortie-t51
    joindre journal-t51 5
    rm -rf "$DEPOT/__pycache__"
    joindre lignes
    joindre journal

    titre "T72 : résultat contraire à l'évaluation finale"
    # Les Blancs donnent leur dame et la partie est pourtant notée 1-0 :
    # la synthèse doit le dire. Notée 0-1, la même partie est cohérente.
    printf '[Result "1-0"]\n[Termination "Normal"]\n\n' > t-contre.pgn
    printf '1. e4 e5 2. Qh5 Nc6 3. Qxf7+ Kxf7 1-0\n' >> t-contre.pgn
    lancer t-contre.pgn $MOTEUR $RAPIDE
    egal "T72 code de retour" 0 "$RC"
    extraire '*/synthese.md'
    egal "T72 contradiction signalée" 1 \
        "$(grep -c 'Résultat et évaluation finale se contredisent' extrait)"
    verifier "T72 vainqueur déclaré et camp réellement mieux" \
        contient extrait "victoire des Blancs, alors que Stockfish donne"
    verifier "T72 dernier coup et balise Termination cités" \
        contient extrait "3... Kxf7, soit un net avantage aux Noirs"
    verifier "T72 balise Termination citée" \
        contient extrait 'La balise Termination vaut `Normal`.'
    PR="${ARCH%.zip}.prompt.txt"
    egal "T72 prompt : consigne de le dire au joueur" 1 \
        "$(grep -c 'le résultat contredit' "$PR")"
    sed 's/1-0/0-1/g' t-contre.pgn > t-coherent.pgn
    lancer t-coherent.pgn $MOTEUR $RAPIDE
    egal "T72 résultat cohérent, code de retour" 0 "$RC"
    : > extrait
    extraire '*/synthese.md'
    verifier "T72 résultat cohérent, synthèse produite" \
        contient extrait "## 3. Évaluations Stockfish"
    egal "T72 résultat cohérent, rien n'est signalé" 0 \
        "$(grep -c 'se contredisent' extrait)"

    # Le cas symétrique : les Noirs donnent leur dame, la partie est
    # notée 0-1.
    printf '[Result "0-1"]\n\n1. e4 e5 2. Nf3 Qh4 3. Nxh4 0-1\n' > t-contre-noirs.pgn
    lancer t-contre-noirs.pgn $MOTEUR $RAPIDE
    egal "T72 victoire des Noirs contredite, code de retour" 0 "$RC"
    : > extrait
    extraire '*/synthese.md'
    verifier "T72 victoire des Noirs contredite, signalée" contient extrait \
        "victoire des Noirs, alors que Stockfish donne"
    verifier "T72 victoire des Noirs contredite, avantage aux Blancs" \
        contient extrait "3. Nxh4, soit un net avantage aux Blancs"

    titre "T52 : coup nul"
    printf '1. e4 e5 2. -- Nc6 3. Nf3 *\n' > t-nul-coup.pgn
    lancer t-nul-coup.pgn $MOTEUR $RAPIDE
    egal "T52 code de retour" 0 "$RC"
    extraire '*/synthese.md'
    grep -E '^\| [34] \|' extrait > lignes 2>/dev/null
    verifier "T52 ligne du coup nul sans évaluation" \
        contient lignes "| 3 | 2 | Blancs | -- | - | - | - | - |"
    verifier "T52 mention en section 3 bis" \
        contient extrait "joué : coup nul, non évalué par le moteur"
    joindre lignes

    egal "T52 pas d'avis répété de python-chess" 0 \
        "$(grep -c 'Not transmitting' journal)"
    lancer t-nul-coup.pgn $MOTEUR $RAPIDE --prompt-seul
    PR="$ARCH"
    verifier "T52 prompt court : le coup nul est expliqué" \
        contient "$PR" 'Un coup noté "--" est un coup nul'
    lancer italienne.pgn $MOTEUR --profondeur 4 --prompt-seul
    PR="$ARCH"
    egal "T52 prompt court : rien sur le coup nul sans coup nul" 0 \
        "$(grep -c 'coup nul' "$PR")"
    verifier "T52 prompt court : chaque coup joué, sans limite" \
        contient "$PR" "après chaque coup joué."

    titre "T25 : moteur limité aux premiers coups"
    lancer italienne.pgn $MOTEUR --coups-stockfish 3 --profondeur 10 \
        --multipv 2 --longueur-pv 4 --fils 2 --hachage 128
    egal "T25 code de retour" 0 "$RC"
    extraire '*/synthese.md'
    verifier "T25 six demi-coups couverts sur neuf" contient extrait \
        "profondeur 10, multipv 2, 6 demi-coups couverts sur 9"
    egal "T25 six lignes au tableau" 6 \
        "$(grep -c -E '^\| [1-9] \| [1-5] \| (Blancs|Noirs) \| [A-Za-z]' extrait)"
    PR="${ARCH%.zip}.prompt.txt"
    verifier "T25 prompt : couverture partielle dite" contient "$PR" \
        "que les 6 premiers demi-coups sur 9"
    verifier "T25 prompt : deux coups par position, pas trois" \
        contient "$PR" "meilleurs coups du moteur, 2 par position"
    lancer italienne.pgn $MOTEUR --coups-stockfish 3 --profondeur 4 \
        --prompt-seul
    PR="$ARCH"
    verifier "T25 prompt court : couverture partielle dite" contient "$PR" \
        "après chacun des 6 premiers demi-coups sur 9"
    egal "T25 prompt court : plus de chaque coup joué" 0 \
        "$(grep -c 'après chaque coup joué' "$PR")"
    lancer italienne.pgn $MOTEUR --coups-stockfish 3 --profondeur 10 \
        --multipv 2 --longueur-pv 4 --fils 2 --hachage 128
    extraire '*/collecte.json'
    verifier "T25 fils dans collecte.json" contient extrait '"fils": 2'
    verifier "T25 hachage dans collecte.json" contient extrait '"hachage": 128'

    titre "T78 : moteur qui s'arrête hors d'une recherche"
    # Faux moteur : il annonce ses options, puis meurt au premier
    # réglage, comme Stockfish quand la mémoire de sa table de hachage
    # lui est refusée.
    cat > faux-moteur <<'FIN'
#!/bin/sh
while read -r ligne; do
    case "$ligne" in
        uci)
            echo "id name Faux"
            echo "option name Threads type spin default 1 min 1 max 8"
            echo "option name Hash type spin default 16 min 1 max 1024"
            echo "option name MultiPV type spin default 1 min 1 max 5"
            echo "uciok" ;;
        isready) echo "readyok" ;;
        setoption*) exit 1 ;;
        quit) exit 0 ;;
    esac
done
FIN
    chmod +x faux-moteur
    lancer italienne.pgn --sans-explorateur --sans-questions \
        --stockfish "$TRAVAIL/faux-moteur" --fils 2 --profondeur 4
    egal "T78 code de retour" 1 "$RC"
    verifier "T78 message du moteur, pas une erreur inattendue" \
        contient journal "Le moteur a échoué en cours d'analyse"
    egal "T78 pas d'erreur inattendue" 0 \
        "$(grep -c 'Erreur inattendue' journal)"
    joindre journal 6
    rm -rf analyse-italienne-*

    # Le moteur désigné par son nom nu, ou par un chemin à tilde : le
    # contrôle et le lancement le cherchent maintenant au même endroit.
    mkdir -p "$TRAVAIL/maison/bin"
    ln -sf "$STOCKFISH" "$TRAVAIL/maison/bin/moteur-essai"
    HOME="$TRAVAIL/maison" "$SCRIPT" italienne.pgn --sans-explorateur \
        --sans-questions --profondeur 1 --venv "$VENV" --reglages "$REGL" \
        --stockfish='~/bin/moteur-essai' > sortie 2> journal
    egal "T55 --stockfish avec un tilde" 0 "$?"
    PATH="$TRAVAIL/maison/bin:$PATH" "$SCRIPT" italienne.pgn \
        --sans-explorateur --sans-questions --profondeur 1 \
        --venv "$VENV" --reglages "$REGL" --stockfish moteur-essai \
        > sortie 2> journal
    egal "T55 --stockfish par son nom, cherché dans le PATH" 0 "$?"
    rm -rf analyse-italienne-*

    titre "T55 : options moteur hors bornes"
    lancer italienne.pgn $MOTEUR --profondeur 61
    egal "T55 --profondeur 61, code de retour" 2 "$RC"
    verifier "T55 --profondeur 61, message" \
        contient journal "--profondeur ne doit pas dépasser 60"
    for option in "--fils 100000" "--hachage 99999999999" "--multipv 9999"; do
            lancer italienne.pgn $MOTEUR $option
        egal "T55 $option, code de retour" 1 "$RC"
        verifier "T55 $option, refus avant la collecte" \
            contient journal "est hors des bornes du moteur"
        tail -n 1 journal > ligne
        joindre ligne
    done
    egal "T55 aucun dossier de travail créé" 0 \
        "$(find . -maxdepth 1 -type d -name 'analyse-italienne-*' | wc -l)"

    titre "T70 : test.pgn, la partie d'essai du dépôt"
    if [ -f "$DEPOT/test.pgn" ]; then
        cp "$DEPOT/test.pgn" test.pgn
        lancer test.pgn $MOTEUR $RAPIDE --pseudos "zoé blanche"
        egal "T70 code de retour" 0 "$RC"
        egal "T70 aucun avertissement" 0 "$(grep -c 'Attention' journal)"
        extraire '*/partie.pgn'
        verifier "T70 partie.pgn identique à test.pgn" cmp -s extrait test.pgn
        extraire '*/synthese.md'
        verifier "T70 trente-six demi-coups" contient extrait \
            "Nombre de demi-coups dans la ligne principale : 36."
        verifier "T70 balise accentuée" \
            contient extrait "| Black | Müller, Noël |"
        verifier "T70 balise TimeControl reprise" \
            contient extrait "| TimeControl | 600+5 |"
        verifier "T70 grand roque des Blancs" contient extrait \
            "Roque des Blancs : O-O-O au coup 14 (demi-coup 27)."
        verifier "T70 petit roque des Noirs" contient extrait \
            "Roque des Noirs : O-O au coup 7 (demi-coup 14)."
        egal "T70 mat concédé puis mat manqué" 2 \
            "$(grep -c -E '^\| [34] \| 2 \|.*\| mat \| gaffe \|' extrait)"
        egal "T70 prise en passant" 1 \
            "$(grep -c -E '^\| 9 \| 5 \| Blancs \| gxf6 \|' extrait)"
        egal "T70 promotion avec prise et échec" 1 \
            "$(grep -c -E '^\| 17 \| 9 \| Blancs \| gxf8=Q\+ \|' extrait)"
        egal "T70 coup nul non évalué" 1 \
            "$(grep -c -E '^\| 29 \| 15 \| Blancs \| -- \| - \| - \| - \| - \|' extrait)"
        egal "T70 trente-six lignes au tableau" 36 \
            "$(grep -c -E '^\| [0-9]+ \| [0-9]+ \| (Blancs|Noirs) \| ' extrait)"
        PR="${ARCH%.zip}.prompt.txt"
        verifier "T70 prompt : camp déduit malgré la casse" \
            contient "$PR" "- camp dans cette partie : Blancs"
        grep -E '^\| (3|4|9|17|29) \|' extrait | cut -c1-110 > lignes
        joindre lignes
    else
        sauter "T70 : test.pgn absent du dépôt"
    fi

    titre "T73 : verifier-analyse.py, contrôle du PGN rendu par un LLM"
    if [ -f "$DEPOT/test.pgn" ] && [ -f "$DEPOT/verifier-analyse.py" ]; then
        VERIF="$DEPOT/verifier-analyse.py"
        cp "$DEPOT/test.pgn" test.pgn
        lancer test.pgn $MOTEUR $RAPIDE
        # Deux PGN sont fabriqués à partir de l'archive, comme le ferait un
        # LLM : un conforme, construit avec python-chess, et un fautif, où
        # sont injectés les défauts relevés sur de vrais PGN de LLM.
        ARCHIVE="$ARCH" "$PYVENV" - > sortie-t73 2> journal-t73 <<'EOF'
import io
import json
import os
import textwrap
import zipfile

import chess
import chess.pgn

with zipfile.ZipFile(os.environ["ARCHIVE"]) as z:
    nom = [n for n in z.namelist() if n.endswith("partie.pgn")][0]
    racine = nom[:-len("partie.pgn")]
    source = chess.pgn.read_game(io.StringIO(z.read(nom).decode("utf-8")))
    evals = json.loads(z.read(racine + "stockfish/evaluations.json"))

# Les évaluations "inventées" doivent réellement manquer aux données du
# moteur. Un chiffre fixe ne le garantit pas : +7.77 a été un jour la
# vraie évaluation d'un coup, sur une machine où la partie d'essai se
# joue autour de +7, et le PGN fautif ne l'était plus sur ce point.
connues = {coup.get("score") for e in evals
           for coup in [e["joue"]] + e["meilleurs"]}


def invente(centiemes):
    """
    Première évaluation, à partir de la valeur donnée en centièmes de
    pion, que le moteur n'a rendue pour aucun coup de cette collecte.
    """
    while "+%d.%02d" % divmod(centiemes, 100) in connues:
        centiemes += 1
    return "+%d.%02d" % divmod(centiemes, 100)


INVENTE_PGN = invente(777)
INVENTE_CONVERSATION = invente(999)
# Le chiffre retenu pour le PGN est rendu au script : c'est lui que le
# bilan doit nommer.
open("t-invente-pgn", "w", encoding="utf-8").write(INVENTE_PGN + "\n")


def construire(fautif):
    jeu = chess.pgn.Game()
    for b in ("Event", "Site", "Date", "Round", "White", "Black", "Result"):
        jeu.headers[b] = source.headers[b]
    autres = {"Annotator": "Essai (test-app.sh)", "BlackElo": "1500",
              "PlyCount": str(len(evals)), "TimeControl": "600+5",
              "WhiteElo": "1450"}
    for b in sorted(autres):
        jeu.headers[b] = autres[b]
    jeu.comment = textwrap.fill("Partie d'essai, ouverture Barnes. " * 12, 75)
    noeud = jeu
    for e, coup in zip(evals, source.mainline_moves()):
        suivant = noeud.add_main_variation(coup)
        # Le demi-coup 4, mat manqué, est une gaffe pour tout moteur : le
        # PGN fautif l'oublie.
        if e["nature"] in ("erreur", "gaffe") and not (
                fautif and e["demicoup"] == 4):
            suivant.nags.add(chess.pgn.NAG_BLUNDER if e["nature"] == "gaffe"
                             else chess.pgn.NAG_MISTAKE)
            meilleur = e["meilleurs"][0]
            texte = ("Il fallait %s, que le moteur donne à %s contre %s "
                     "pour le coup joué." % (meilleur["san"],
                                             meilleur["score"],
                                             e["joue"]["score"]))
            if fautif and e["demicoup"] == 3:
                # Demi-coup 3, mat concédé : évaluation inventée, pour
                # cent, variante écrite dans le commentaire, variante
                # illégale, et NAG donnant les Blancs gagnants.
                texte += (" Chiffre inventé : %s, soit 50 %% de gain. (%s)"
                          " (2. Ke3 Nc6)"
                          % (INVENTE_PGN,
                             " ".join(meilleur["pv_san"].split()[:4])))
                suivant.nags.add(18)
            suivant.comment = textwrap.fill(texte, 75)
            # Variante tirée de la ligne du moteur, quatre demi-coups.
            var = noeud
            for uci in meilleur["pv_uci"][:4]:
                m = chess.Move.from_uci(uci)
                if m not in var.board().legal_moves:
                    break
                var = (var.add_variation(m) if var is noeud
                       else var.add_main_variation(m))
        noeud = suivant
    texte = jeu.accept(chess.pgn.StringExporter(columns=79)) + "\n"
    if fautif:
        # Défauts de qui écrit le PGN à la main : ligne vide après le
        # résumé, notation suffixe, marqueur de fin faux.
        texte = texte.replace("\n1. f3", "\n\n1. f3", 1)
        texte = texte.replace("2. g4 $4", "2. g4??", 1)
        fin = source.headers["Result"]
        texte = texte[:texte.rindex(fin)] + "1-0\n"
    return texte


open("t-conforme.pgn", "w", encoding="utf-8").write(construire(False))
# Trois défauts que le PGN conforme ne porte pas, un par fichier, pour
# que chacun soit relevé seul : ils ne changent ni les coups ni leur
# nombre, et passaient donc inaperçus.
conforme = construire(False)
lignes = conforme.rstrip("\n").split("\n")
lignes.insert(len(lignes) - 1, "")
open("t-vide-fin.pgn", "w", encoding="utf-8").write("\n".join(lignes) + "\n")
open("t-fermante.pgn", "w", encoding="utf-8").write(
    conforme.replace("Partie d'essai, ouverture",
                     "Partie d'essai } ouverture", 1))
blancs = '[White "%s"]\n' % source.headers["White"]
noirs = '[Black "%s"]\n' % source.headers["Black"]
open("t-balises.pgn", "w", encoding="utf-8").write(
    conforme.replace(blancs + noirs, noirs + blancs, 1))
open("t-fautif.pgn", "w", encoding="utf-8").write(construire(True))
# Ce que rend un LLM d'après le prompt court de --prompt-seul : les
# balises et les coups recopiés, un commentaire sur chaque erreur ou
# gaffe, sur une seule ligne, sans résumé, sans NAG, sans balise
# ajoutée.
court = chess.pgn.Game()
for b in ("Event", "Site", "Date", "Round", "White", "Black", "Result"):
    court.headers[b] = source.headers[b]
noeud = court
for e, coup in zip(evals, source.mainline_moves()):
    noeud = noeud.add_main_variation(coup)
    if e["nature"] in ("erreur", "gaffe"):
        noeud.comment = ("Ici tu devais jouer %s, bien meilleur d'après "
                         "le tableau : prends le temps de chercher ce coup "
                         "avant de pousser un pion." % e["meilleurs"][0]["san"])
open("t-court.pgn", "w", encoding="utf-8").write(
    court.accept(chess.pgn.StringExporter(columns=None)) + "\n")
open("t-conversation.txt", "w", encoding="utf-8").write(
    "Position 1 : %s\n"
    "Position 2 : 8/8/8/8/8/8/8/8 w - - 0 1\n"
    "Evaluation %s sortie de nulle part \u2014 avec un tiret cadratin.\n"
    % (evals[2]["fen"], INVENTE_CONVERSATION))
EOF
        "$PYVENV" "$VERIF" "$ARCH" t-conforme.pgn > bilan 2>&1
        egal "T73 PGN conforme, code de retour" 0 "$?"
        egal "T73 PGN conforme, aucun échec" 0 "$(grep -c '^  ECHEC' bilan)"
        verifier "T73 PGN conforme, variantes appuyées sur le moteur" \
            contient bilan "0 sont du cru du LLM"
        "$PYVENV" "$VERIF" "$ARCH" t-fautif.pgn --nom "essai fautif" \
            --synthese t-conversation.txt > bilan 2>&1
        egal "T73 PGN fautif, code de retour" 1 "$?"
        # Chaque ligne donne le défaut injecté, puis ce que le bilan en dit.
        while IFS='|' read -r defaut constat; do
            verifier "T73 défaut relevé : $defaut" \
                grep -q -E "^  ECHEC .*$constat" bilan
        done <<'FIN'
ligne vide dans le corps|ligne vide dans le corps de la partie
pour cent écrit %|aucun caractère % dans un commentaire
notation suffixe|pas de notation suffixe
marqueur de fin|marqueur de fin "1-0"
gaffe non commentée|toutes commentées \(1 oubliée
NAG contraire au moteur|aucun NAG de position contraire
variante illégale dans un commentaire|toutes légales \(1 illégale
tiret cadratin dans la conversation|aucun tiret cadratin dans la conversation \(1 relevé
FEN invalide|toutes les FEN sont des positions valides
FIN
        verifier "T73 variante écrite dans un commentaire" \
            contient bilan "écrite(s) à l'intérieur d'un commentaire"
        verifier "T73 coup illégal nommé" contient bilan "Ke3 est illégal"
        # Les deux évaluations inventées, celle du PGN et celle de la
        # conversation, donnent la même phrase au bilan : chacune est
        # cherchée dans sa section, l'une passait sinon pour l'autre.
        sed -n '/^=== 5\. /,/^=== 6\. /p' bilan > section5
        sed -n '/^=== 8\. /,/^=== Bilan/p' bilan > section8
        INVENTE=$(cat t-invente-pgn 2>/dev/null)
        verifier "T73 défaut relevé : évaluation inventée dans le PGN" \
            grep -q -E '^  ECHEC .*\(1 introuvable' section5
        verifier "T73 chiffre inventé nommé" \
            contient section5 ": ${INVENTE:-chiffre non rendu}"
        verifier "T73 défaut relevé : évaluation inventée dans la conversation" \
            grep -q -E '^  ECHEC .*\(1 introuvable' section8
        grep -E '^  (ECHEC|ATTENTION)' bilan | cut -c1-110 > lignes
        joindre lignes 20
        # Défauts qui ne changent pas les coups lus : chacun doit être
        # relevé à lui seul, sur un PGN par ailleurs conforme.
        while IFS='|' read -r fichier constat; do
            "$PYVENV" "$VERIF" "$ARCH" "$fichier" > bilan 2>&1
            egal "T73 $fichier, code de retour" 1 "$?"
            egal "T73 $fichier, un seul échec" 1 "$(grep -c '^  ECHEC' bilan)"
            verifier "T73 $fichier, défaut nommé" \
                grep -q -E "^  ECHEC .*$constat" bilan
        done <<'FIN'
t-vide-fin.pgn|ligne vide dans le corps de la partie
t-fermante.pgn|aucune accolade dans un commentaire
t-balises.pgn|les sept balises obligatoires, dans l'ordre
FIN
        # Un PGN conforme au prompt court n'a ni résumé ni lignes de 79
        # caractères : avec --prompt-seul il passe, sans l'option il
        # échoue sur ces deux points, qui viennent du prompt complet.
        "$PYVENV" "$VERIF" "$ARCH" t-court.pgn --prompt-seul > bilan 2>&1
        egal "T73 --prompt-seul, code de retour" 0 "$?"
        egal "T73 --prompt-seul, aucun échec" 0 "$(grep -c '^  ECHEC' bilan)"
        verifier "T73 --prompt-seul, dit en tête du bilan" \
            contient bilan "prompt  : court"
        "$PYVENV" "$VERIF" "$ARCH" t-court.pgn > bilan 2>&1
        egal "T73 le même sans l'option, code de retour" 1 "$?"
        egal "T73 le même sans l'option, deux échecs" 2 \
            "$(grep -c '^  ECHEC' bilan)"
        "$PYVENV" "$VERIF" "$ARCH" - --synthese t-conversation.txt \
            > bilan 2>&1
        egal "T73 aucun PGN rendu, code de retour" 1 "$?"
        verifier "T73 aucun PGN rendu, dit dans le bilan" \
            contient bilan "aucun PGN rendu"
        # Évaluations citées : le contrôle est appelé seul, sur un dossier
        # d'une seule évaluation, +0.35, dont l'arrondi se trompe en
        # flottant. Chaque ligne donne le texte cité et le nombre
        # d'échecs attendu.
        VERIF="$VERIF" "$PYVENV" - > sortie-t73c 2> journal-t73c <<'EOF'
import importlib.util
import os

spec = importlib.util.spec_from_file_location("va", os.environ["VERIF"])
va = importlib.util.module_from_spec(spec)
spec.loader.exec_module(va)
dossier = [{"joue": {"score": "+0.35"}, "meilleurs": [{"score": "-1.25"}]}]
for cite in ("+0.35 et -1.25", "+0.4 et +0.3", "-1.3 et -1.2", "+0,35",
             "+ 0.35", "\u22121.25", "+0.5", "+ 7.77", "\u22127.77",
             "+7.777", "7.77 minutes"):
    b = va.Bilan()
    va.controler_chiffres(b, [("essai", cite)], dossier, "essai")
    print(cite.encode("ascii", "backslashreplace").decode(), b.echecs)
EOF
        cat > attendu-t73c <<'EOF'
+0.35 et -1.25 0
+0.4 et +0.3 0
-1.3 et -1.2 0
+0,35 0
+ 0.35 0
\u22121.25 0
+0.5 1
+ 7.77 1
\u22127.77 1
+7.777 1
7.77 minutes 0
EOF
        verifier "T73 évaluations : arrondis admis, chiffres inventés relevés" \
            cmp -s attendu-t73c sortie-t73c
        joindre sortie-t73c 12
        joindre journal-t73c 5
        rm -rf "$DEPOT/__pycache__"
        "$PYVENV" "$VERIF" /nulle/part.zip t-conforme.pgn > bilan 2>&1
        egal "T73 archive illisible, code de retour" 2 "$?"
        # Un PGN venu de Windows, aux lignes de 79 caractères terminées
        # par CRLF, reste conforme.
        awk '{ printf "%s\r\n", $0 }' t-conforme.pgn > t-crlf.pgn
        "$PYVENV" "$VERIF" "$ARCH" t-crlf.pgn > bilan 2>&1
        egal "T73 fins de ligne CRLF, code de retour" 0 "$?"
        # Un PGN que python-chess ne sait pas lire donne un bilan, et une
        # archive abîmée le code 2 : jamais une trace Python.
        printf '1. e5 ) 1. e4 *\n' > t-illisible.pgn
        "$PYVENV" "$VERIF" "$ARCH" t-illisible.pgn > bilan 2>&1
        egal "T73 PGN illisible, code de retour" 1 "$?"
        verifier "T73 PGN illisible, dit dans le bilan" \
            contient bilan "aucune partie lisible"
        printf '1. e4 ( 1. e5 ) 1... e4 *\n' > t-variante-folle.pgn
        "$PYVENV" "$VERIF" "$ARCH" t-variante-folle.pgn > bilan2 2>&1
        egal "T73 variante illégale en tête, code de retour" 1 "$?"
        cat bilan2 >> bilan
        mkdir -p t-abimee/stockfish
        unzip -p "$ARCH" '*/partie.pgn' > t-abimee/partie.pgn
        unzip -p "$ARCH" '*/synthese.md' > t-abimee/synthese.md
        "$PYVENV" "$VERIF" t-abimee t-conforme.pgn >> bilan 2>&1
        egal "T73 archive incomplète, code de retour" 2 "$?"
        printf '{pas du JSON' > t-abimee/stockfish/evaluations.json
        "$PYVENV" "$VERIF" t-abimee t-conforme.pgn >> bilan 2>&1
        egal "T73 évaluations illisibles, code de retour" 2 "$?"
        printf '{"autre": "forme"}' > t-abimee/stockfish/evaluations.json
        "$PYVENV" "$VERIF" t-abimee t-conforme.pgn >> bilan 2>&1
        egal "T73 évaluations d'une autre forme, code de retour" 2 "$?"
        egal "T73 aucune trace Python dans ces cas" 0 \
            "$(grep -c 'Traceback' bilan)"
    else
        sauter "T73 : test.pgn ou verifier-analyse.py absent du dépôt"
    fi

    titre "T82 : vérificateur, mats, périmètre, mode court, dossier parent"
    if [ -f "$DEPOT/verifier-analyse.py" ]; then
        VERIF="$DEPOT/verifier-analyse.py"
        # Le mat de Légal : 5... Bxd1 concède un mat, que 7. Nd5# donne.
        printf '[White "Alice"]\n[Black "Bob"]\n[Result "1-0"]\n\n' > t-legal.pgn
        printf '1. e4 e5 2. Nf3 d6 3. Bc4 Bg4 4. Nc3 g6 5. Nxe5 Bxd1 ' \
            >> t-legal.pgn
        printf '6. Bxf7+ Ke7 7. Nd5# 1-0\n' >> t-legal.pgn
        mkdir -p t-parent
        lancer t-legal.pgn $MOTEUR $RAPIDE --garder-dossier --sortie t-parent
        egal "T82 code de retour" 0 "$RC"
        DOSSIER82="${ARCH%.zip}"
        egal "T82 tableau : le mat se compte après le coup" "1 1 1" \
            "$(grep -c -E '\| Bxf7\+ \| #\+1 \|' "$DOSSIER82/synthese.md") $(grep -c -E '\| Ke7 \| #\+1 \|' "$DOSSIER82/synthese.md") $(grep -c -E '\| Nd5# \| #\+0 \|' "$DOSSIER82/synthese.md")"
        # Trois PGN rendus : des mats cités, des commentaires limités aux
        # quatre premiers coups, un NAG contraire au moteur.
        PARTIE="$DOSSIER82/partie.pgn" "$PYVENV" - 2> journal-t82 <<'EOF'
import os

import chess.pgn

for nom in ("mats", "quatre", "nag"):
    with open(os.environ["PARTIE"], encoding="utf-8") as f:
        jeu = chess.pgn.read_game(f)
    for rang, noeud in enumerate(jeu.mainline(), 1):
        noeud.comment = "Coup %d." % rang
        if nom == "mats" and rang == 11:
            noeud.comment = "Le moteur donne #+1."
        if nom == "mats" and rang == 12:
            noeud.comment = "Toujours #1, puis un inventé : #+7."
        if nom == "quatre" and rang > 8:
            noeud.comment = ""
        if nom == "nag" and rang == 10:
            noeud.nags.add(15)
    with open("t-82-%s.pgn" % nom, "w", encoding="utf-8") as f:
        print(jeu, file=f)
EOF
        joindre journal-t82 5
        # Un mat des Blancs s'écrit "#+1" dans le dossier : cité tel quel
        # ou sans signe, il est reconnu, et un mat inventé est relevé.
        "$PYVENV" "$VERIF" "$ARCH" t-82-mats.pgn --prompt-seul > bilan 2>&1
        sed -n '/^=== 5\. /,/^=== 6\. /p' bilan > section5
        verifier "T82 mats cités : trois évaluations lues" \
            contient section5 "3 évaluation(s) citée(s)"
        verifier "T82 mats cités : le mat inventé est le seul relevé" \
            contient section5 "(1 introuvable(s))"
        verifier "T82 mats cités : mat inventé nommé" contient section5 "#+7"
        # Le périmètre convenu borne le contrôle : la gaffe du coup 5
        # n'est pas attendue d'un PGN limité aux quatre premiers coups.
        "$PYVENV" "$VERIF" "$ARCH" t-82-quatre.pgn --prompt-seul > bilan 2>&1
        # Le nombre d'erreurs relevées après le coup 4 varie avec le
        # moteur : seul compte l'échec du contrôle.
        egal "T82 sans périmètre, la gaffe du coup 5 est attendue" "1 0" \
            "$(grep -c 'ECHEC     les .* sont toutes commentées' bilan) $(grep -c '(0 oubliée(s))' bilan)"
        "$PYVENV" "$VERIF" "$ARCH" t-82-quatre.pgn --prompt-seul \
            --perimetre 4 > bilan 2>&1
        egal "T82 --perimetre 4, code de retour" 0 "$?"
        verifier "T82 --perimetre 4, dit dans le bilan" \
            contient bilan "périmètre convenu : les 4 premiers coups"
        verifier "T82 --perimetre 4, plus rien d'oublié" \
            contient bilan "(0 oubliée(s))"
        "$PYVENV" "$VERIF" "$ARCH" t-82-quatre.pgn --perimetre 0 \
            > bilan 2>&1
        egal "T82 --perimetre 0 refusé" 2 "$?"
        # Le périmètre donné au script se lit dans les consignes de la
        # synthèse : un nombre y vaut un nombre de coups.
        VERIF="$VERIF" "$PYVENV" - > sortie-t82 2> journal-t82 <<'EOF'
import importlib.util
import os

spec = importlib.util.spec_from_file_location("va", os.environ["VERIF"])
va = importlib.util.module_from_spec(spec)
spec.loader.exec_module(va)
for reponse in ("les 20 premiers coups", "12", "la partie complète (défaut)",
                "jusqu'au milieu de partie", "0"):
    print(va.perimetre_convenu("## Consignes\n- Périmètre : %s\n" % reponse))
print(va.perimetre_convenu("Aucune consigne."))
EOF
        printf '20\n12\nNone\nNone\nNone\nNone\n' > attendu-t82
        verifier "T82 périmètre lu dans les consignes de la synthèse" \
            cmp -s attendu-t82 sortie-t82
        joindre sortie-t82
        joindre journal-t82 5
        rm -rf "$DEPOT/__pycache__"
        # Mode court : ni NAG, ni tiret cadratin, ni nombre de FEN, que le
        # prompt court ne demande pas. Sans l'option, ils sont relevés.
        printf 'Synth\303\250se \342\200\224 sans position.\n' > t-82-conv.txt
        "$PYVENV" "$VERIF" "$ARCH" t-82-nag.pgn --prompt-seul \
            --synthese t-82-conv.txt > bilan 2>&1
        egal "T82 mode court, code de retour" 0 "$?"
        egal "T82 mode court, NAG, tiret cadratin et FEN non contrôlés" \
            "0 0 0" \
            "$(grep -c 'NAG de position' bilan) $(grep -c 'tiret cadratin' bilan) $(grep -c 'deux demandées' bilan)"
        "$PYVENV" "$VERIF" "$ARCH" t-82-nag.pgn \
            --synthese t-82-conv.txt > bilan 2>&1
        egal "T82 mode complet, les trois sont relevés" "1 1 1" \
            "$(grep -c 'ECHEC     aucun NAG de position' bilan) $(grep -c 'ECHEC     aucun tiret cadratin dans la conversation' bilan) $(grep -c 'ATTENTION 0 FEN' bilan)"
        # Dossier parent : la seule collecte complète est prise et nommée,
        # une collecte interrompue à côté ne s'y mêle pas, et deux
        # collectes complètes sont refusées plutôt que choisies.
        mkdir -p t-parent/analyse-aaa-interrompue
        cp "$DOSSIER82/partie.pgn" t-parent/analyse-aaa-interrompue/
        printf '1. d4 d5 *\n' > t-parent/analyse-aaa-interrompue/partie.pgn
        "$PYVENV" "$VERIF" t-parent t-82-mats.pgn --prompt-seul > bilan 2>&1
        verifier "T82 dossier parent, collecte complète nommée" \
            contient bilan "collecte: $(basename "$DOSSIER82")"
        verifier "T82 dossier parent, la bonne partie est lue" \
            contient bilan "OK        ligne principale identique"
        cp -R "$DOSSIER82" t-parent/analyse-zzz-seconde
        "$PYVENV" "$VERIF" t-parent t-82-mats.pgn --prompt-seul > bilan 2>&1
        egal "T82 deux collectes complètes, code de retour" 2 "$?"
        verifier "T82 deux collectes complètes, nommées" \
            contient bilan "contient 2 collectes complètes"
        joindre bilan
        rm -rf t-parent
    else
        sauter "T82 : verifier-analyse.py absent du dépôt"
    fi

    titre "M2 : analyse complète de l'italienne, moteur seul"
    lancer italienne.pgn $MOTEUR --profondeur 10 --fils 2 --hachage 64
    egal "M2 code de retour" 0 "$RC"
    extraire '*/synthese.md'
    egal "M2 neuf lignes dans le tableau Stockfish" 9 \
        "$(grep -c -E '^\| [1-9] \| [1-5] \| (Blancs|Noirs) \| [A-Za-z]' extrait)"
    grep -E '^Moteur' extrait | cut -c1-110 > ligne
    joindre ligne
    # Une seconde de délai : le moteur vient de recevoir "quit".
    sleep 1
    PR="${ARCH%.zip}.prompt.txt"
    egal "M2 prompt : les chiffres du moteur font foi" 1 \
        "$(grep -c 'Les chiffres de la section 3 font foi' "$PR")"
    egal "M2 prompt : Stockfish inutile à l'analyste" 1 \
        "$(grep -c 'Stockfish est inutile' "$PR")"
    egal "M2 prompt : la mention mat est expliquée" 1 \
        "$(grep -c 'porte .mat. quand le coup' "$PR")"
    egal "M2 aucun processus du moteur laissé par les tests" \
        "[$MOTEURS_AVANT]" "[$(processus_moteur)]"
fi

# ===========================================================================
# Tests avec le réseau et le jeton, seulement avec --reseau
# ===========================================================================

if [ "$RESEAU" = 1 ]; then

CAT="$TRAVAIL/catalogue"
# Options communes à toutes les collectes de cette partie : aucune
# question. Collecte de l'explorateur seule, sans moteur, pour EXPL.
BASE="--sans-questions"
EXPL="$BASE --profondeur 1"

# collecter options... : lance une collecte avec le catalogue temporaire
# et votre jeton. Sortie standard dans "sortie", journal dans "journal",
# code de retour dans RC, chemin de l'archive dans ARCH. La synthèse est
# extraite dans "synthese", sa section 2 dans "section2" et les lignes du
# tableau de l'explorateur dans "table".
collecter() {
    "$SCRIPT" "$@" --catalogue "$CAT" --jeton-fichier "$JETON" \
        --venv "$VENV" --reglages "$REGL" > sortie 2> journal
    RC=$?
    ARCH=$(head -n 1 sortie)
    : > synthese
    : > section2
    : > table
    if [ -n "$ARCH" ] && [ -f "$ARCH" ]; then
        unzip -p "$ARCH" '*/synthese.md' > synthese 2>/dev/null
        awk '/^## 2\./ {dedans = 1} /^## 3\./ {dedans = 0} dedans' \
            synthese > section2
        grep -E '^\| [0-9]+ \|' section2 > table 2>/dev/null
    fi
}

# Contrôles communs à toute collecte : elle aboutit, sans erreur
# inattendue, et l'explorateur n'a pas refusé le jeton.
sain() {
    egal "$1 code de retour" 0 "$RC"
    egal "$1 pas d'erreur inattendue" 0 "$(grep -c 'Erreur inattendue' journal)"
    if grep -q 'HTTP 401' journal; then
        NB_ECHEC=$((NB_ECHEC + 1))
        noter "  ECHEC  $1 : HTTP 401, l'explorateur refuse le jeton"
        printf '    ECHEC : %s, HTTP 401, jeton refusé\n' "$1" >&2
    fi
}


# Le fichier contient-il le jeton ? Le jeton sert de fichier de motifs à
# grep : il n'est ni lu par le shell ni affiché, seul un compte ressort.
compte_jeton() {
    grep -a -c -F -f "$JETON" "$1" 2>/dev/null
}

# --- Parties d'essai --------------------------------------------------------

# Une ligne italienne entièrement cataloguée, celle des tests hors réseau.
printf '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 *\n' > italienne.pgn
# La Polonaise suivie de g6, coup rare et hors catalogue. Elle est
# courte, pour borner le nombre de requêtes.
printf '1. b4 g6 2. Bb2 Nf6 3. e3 Bg7 4. Nf3 O-O *\n' > polonaise.pgn
# Une italienne où les deux camps roquent, pour T33.
printf '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6 6. O-O O-O *\n' \
    > roques.pgn
# Un coup nul au troisième demi-coup.
printf '1. e4 e5 2. -- Nc6 *\n' > nul.pgn

# --- Catalogue -----------------------------------------------------------

titre "T09, T10 : installation du catalogue"
"$SCRIPT" --installer-catalogue --catalogue "$CAT" --venv "$VENV" \
    > sortie 2> journal
egal "T09 code de retour" 0 $?
egal "T09 cinq fichiers téléchargés" 5 \
    "$(grep -c 'chargement du catalogue' journal)"
verifier "T09 message Catalogue installé" contient journal "Catalogue installé :"
grep 'Catalogue install' journal > ligne 2>/dev/null
joindre ligne
if [ ! -f "$CAT/catalogue.tsv" ]; then
    noter "  ECHEC  catalogue absent, les tests suivants n'ont pas de sens"
    printf 'Catalogue non installé, arrêt. Voir le journal ci-dessous.\n' >&2
    cat journal >&2
    exit 1
fi
head -n 1 "$CAT/catalogue.tsv" | tr '\t' ' ' > ligne
verifier "T10 première ligne : format 1" contient ligne "#format=1 date="
joindre ligne
egal "T10 aucun fichier temporaire résiduel" 0 \
    "$(find "$CAT" -name '.catalogue-*' | wc -l)"

titre "T11 : réinstallation identique"
tail -n +2 "$CAT/catalogue.tsv" > cat1.tsv
"$SCRIPT" --installer-catalogue --catalogue "$CAT" --venv "$VENV" \
    > sortie 2> journal
egal "T11 code de retour" 0 $?
tail -n +2 "$CAT/catalogue.tsv" > cat2.tsv
verifier "T11 contenu identique hors ligne datée" cmp -s cat1.tsv cat2.tsv

titre "T12, T13 : catalogue absent, catalogue tronqué"
"$SCRIPT" italienne.pgn $EXPL --catalogue "$TRAVAIL/vide" \
    --jeton-fichier "$JETON" --venv "$VENV" --reglages "$REGL" \
    > sortie 2> journal
egal "T12 code de retour" 1 $?
verifier "T12 catalogue absent signalé" \
    contient journal "Catalogue des ouvertures absent"
mkdir abime
head -n $(($(lignes "$CAT/catalogue.tsv") - 10)) "$CAT/catalogue.tsv" \
    > abime/catalogue.tsv
"$SCRIPT" italienne.pgn $EXPL --catalogue "$TRAVAIL/abime" \
    --jeton-fichier "$JETON" --venv "$VENV" --reglages "$REGL" \
    > sortie 2> journal
egal "T13 code de retour" 1 $?
verifier "T13 catalogue tronqué signalé" contient journal "Catalogue tronqué :"
grep 'Catalogue tronqu' journal > ligne 2>/dev/null
joindre ligne

# --- Jeton, sans requête -------------------------------------------------

titre "T28 : fichier de jeton lisible par d'autres"
# Un jeton factice : votre vrai jeton n'est pas recopié. Le catalogue
# absent arrête le script juste après la lecture du jeton, sans réseau.
printf 'lip_factice\n' > faux-jeton
chmod 644 faux-jeton
"$SCRIPT" italienne.pgn $EXPL --catalogue "$TRAVAIL/vide" \
    --jeton-fichier faux-jeton --venv "$VENV" --reglages "$REGL" \
    > sortie 2> journal
verifier "T28 avertissement sur le mode 644" \
    contient journal "est lisible par d'autres (mode 644)"

# --- Base maîtres --------------------------------------------------------

titre "T14 : italienne, base maîtres"
collecter italienne.pgn $EXPL --base maitres
sain "T14"
verifier "T14 journal : base maîtres" contient journal "Explorateur : base maîtres"
egal "T14 neuf lignes dans la table" 9 "$(lignes table)"
verifier "T14 ligne 1 : B00 King's Pawn Game" \
    contient table "| B00 King's Pawn Game |"
verifier "T14 ligne 5 : C50 Italian Game" contient table "| C50 Italian Game |"
verifier "T14 ligne 9 : Giuoco Pianissimo" \
    contient table "Giuoco Pianissimo |"
verifier "T14 arrêt en fin de partie" \
    contient section2 "Arrêt de l'interrogation : fin de la partie."
verifier "T14 aucune sortie de théorie" \
    contient section2 "Aucun coup interrogé ne passe sous le seuil de 10.0 % hors catalogue."
joindre table

titre "T15 : Polonaise, base maîtres"
collecter polonaise.pgn $EXPL --base maitres
sain "T15"
head -n 1 table > ligne
verifier "T15 ligne 1 : b4" contient ligne "| b4 |"
verifier "T15 ligne 1 : A00 Polish Opening" contient ligne "| A00 Polish Opening |"
joindre table
grep 'Arrêt de l' section2 > ligne 2>/dev/null
joindre ligne

# --- Base Lichess --------------------------------------------------------

titre "T16 : Polonaise, base Lichess"
collecter polonaise.pgn $EXPL --base lichess
sain "T16"
head -n 1 table > ligne
verifier "T16 ligne 1 : A00 Polish Opening" contient ligne "| A00 Polish Opening |"
verifier "T16 base Lichess annoncée" contient section2 "Base interrogée : **Lichess**"
verifier "T16 fenêtre de départ annoncée" contient section2 "Fenêtre de départ"
verifier "T16 première sortie : g6" contient section2 "**Noirs joue g6**"
verifier "T16 dernière position nommée : Polonaise" \
    contient section2 "dernière position nommée avant la sortie : A00 Polish Opening"
joindre table
grep -E 'Arrêt de l|Premier coup sous|fréquence du coup' section2 > ligne 2>/dev/null
joindre ligne

titre "T17 : arrêt à la première sortie"
collecter polonaise.pgn $EXPL --base lichess --coups-min 0
sain "T17"
egal "T17 deux lignes dans la table" 2 "$(lignes table)"
verifier "T17 arrêt sur la sortie de théorie" \
    contient section2 "sortie de théorie au demi-coup 2 : g6 joué à"
grep 'Arrêt de l' section2 > ligne 2>/dev/null
joindre ligne

titre "T18 : filtres de cadence et de classement"
collecter polonaise.pgn $EXPL --base lichess --coups-min 0 \
    --cadences ' Rapid,CLASSICAL,rapid' --classements 1000,0
sain "T18"
unzip -p "$ARCH" '*/collecte.json' > json 2>/dev/null
verifier "T18 cadences normalisées" contient json '"cadences": "rapid,classical"'
verifier "T18 classements normalisés" contient json '"classements": "0,1000"'
verifier "T18 filtres repris dans la synthèse" \
    contient section2 'Cadences : `rapid,classical`'
head -n 1 table > ligne
joindre ligne

# --- Seuils et modes -----------------------------------------------------

titre "T19 : seuil de parties inatteignable"
collecter italienne.pgn $EXPL --base lichess --seuil-parties 100000000000
sain "T19"
verifier "T19 échantillon insuffisant au demi-coup 1" \
    contient section2 "échantillon insuffisant au demi-coup 1"
verifier "T19 section 4 renseignée" \
    contient synthese "ne dit plus rien d'exploitable"

titre "T20 : seuil de fréquence à zéro"
collecter polonaise.pgn $EXPL --base lichess --coups-min 0 --seuil-frequence 0
sain "T20"
verifier "T20 aucune sortie sous 0.0 %" \
    contient section2 "Aucun coup interrogé ne passe sous le seuil de 0.0 %"
grep 'Arrêt de l' section2 > ligne 2>/dev/null
joindre ligne

titre "T21 : jusqu'à épuisement"
collecter polonaise.pgn $EXPL --base lichess --jusqu-a-epuisement
sain "T21"
verifier "T21 mode annoncé" contient section2 'Mode `--jusqu-a-epuisement`'
verifier "T21 première sortie toujours g6" contient section2 "**Noirs joue g6**"
noter "  note   lignes dans la table : $(lignes table)"
grep 'Arrêt de l' section2 > ligne 2>/dev/null
joindre ligne

titre "T22 : plafond de demi-coups"
collecter italienne.pgn $EXPL --jusqu-a-epuisement --max-demicoups 4
sain "T22"
egal "T22 quatre lignes dans la table" 4 "$(lignes table)"
verifier "T22 plafond atteint" \
    contient section2 "plafond de 4 demi-coups atteint (option --max-demicoups)"

titre "T23 : pause entre deux requêtes"
collecter italienne.pgn $EXPL --pause 3 --max-demicoups 3
sain "T23"
# Écart, en secondes, entre les horodatages des demi-coups 2 et 3 : la
# première requête part sans attendre, la pause sépare les suivantes.
ECART=$(grep -E 'Explorateur : demi-coup [23] ' journal \
    | sed 's/^\[\([0-9]*\):\([0-9]*\):\([0-9]*\)\].*/\1 \2 \3/' \
    | awk 'NR == 1 {a = $1 * 3600 + $2 * 60 + $3}
           NR == 2 {b = $1 * 3600 + $2 * 60 + $3}
           END {print b - a}')
noter "  note   écart mesuré entre les demi-coups 2 et 3 : ${ECART} s"
if [ "${ECART:-0}" -ge 3 ] 2>/dev/null; then
    egal "T23 au moins 3 secondes entre deux requêtes" oui oui
else
    egal "T23 au moins 3 secondes entre deux requêtes" oui non
fi
grep 'Explorateur : demi-coup' journal > ligne 2>/dev/null
joindre ligne

# --- Roque ---------------------------------------------------------------

titre "T33 : le roque retrouvé dans la base"
collecter roques.pgn $EXPL --base lichess
sain "T33"
grep -E '\| O-O \|' table > roques 2>/dev/null
egal "T33 deux roques dans la table" 2 "$(lignes roques)"
# Un roque non retrouvé ressortait au rang "-", à 0.0 %.
egal "T33 aucun roque au rang hors base" 0 \
    "$(grep -c -E '\| O-O \| - \|' roques)"
egal "T33 aucun roque à 0.0 %" 0 "$(grep -c -E '\| O-O \| [0-9-]+ \| 0\.0 %' roques)"
joindre roques
noter "  note   lignes dans la table : $(lignes table)"
grep 'Arrêt de l' section2 > ligne 2>/dev/null
joindre ligne

# --- Jeton dans l'archive ------------------------------------------------

titre "T29 : le jeton n'est pas dans l'archive"
unzip -p "$ARCH" > contenu 2>/dev/null
egal "T29 jeton absent de l'archive de T33" 0 "$(compte_jeton contenu)"
egal "T29 jeton absent du journal de T33" 0 "$(compte_jeton journal)"
unzip -p "$ARCH" '*/collecte.json' > json 2>/dev/null
verifier "T29 collecte.json note seulement sa présence" \
    contient json '"jeton_present": true'

# --- Source Lichess ------------------------------------------------------

titre "T24 : partie téléchargée depuis Lichess"
if [ -n "$ID_PARTIE" ]; then
    "$SCRIPT" "https://lichess.org/$ID_PARTIE" $EXPL --sans-explorateur \
        --venv "$VENV" --reglages "$REGL" > sortie 2> journal
    egal "T24 par URL, code de retour" 0 $?
    verifier "T24 par URL, export demandé" \
        contient journal "https://lichess.org/game/export/$ID_PARTIE"
    ARCH=$(head -n 1 sortie)
    case $ARCH in
        analyse-"$ID_PARTIE"-*.zip) NOM_OK=oui ;;
        *) NOM_OK=non ;;
    esac
    egal "T24 par URL, nom de l'archive" oui "$NOM_OK"
    "$SCRIPT" "$ID_PARTIE" $EXPL --sans-explorateur --venv "$VENV" \
        --reglages "$REGL" > sortie 2> journal
    egal "T24 par identifiant, code de retour" 0 $?
else
    sauter "T24 : aucune partie donnée. Pour le jouer : sh test-app.sh --reseau <identifiant ou adresse d'une partie de Lichess>"
fi

# --- Coup nul et collecte complète -----------------------------------------------------------

titre "N1 : coup nul, sur le vrai explorateur"
# Depuis la version 3.5.9, la collecte s'arrête au coup nul, sans rien
# demander pour ce demi-coup : auparavant, Lichess refusait par un HTTP
# 400 la liste de coups portant 0000.
collecter nul.pgn $EXPL --base lichess --jusqu-a-epuisement
sain "N1"
egal "N1 deux lignes dans la table" 2 "$(lignes table)"
verifier "N1 arrêt sur le coup nul" \
    contient section2 "Arrêt de l'interrogation : coup nul au demi-coup 3"
egal "N1 aucune requête refusée" 0 "$(grep -c 'HTTP 400' journal)"
verifier "N1 section 4 : coup nul, non interrogé" \
    contient synthese "coup nul, non interrogé"
grep 'Explorateur :' journal > ligne 2>/dev/null
joindre ligne
joindre table

if [ -n "$STOCKFISH" ] && [ -x "$STOCKFISH" ]; then
    titre "N2 : collecte complète, explorateur et moteur"
    collecter roques.pgn $BASE --stockfish "$STOCKFISH" --profondeur 12 \
        --fils 2 --hachage 64
    sain "N2"
    unzip -l "$ARCH" > liste 2>/dev/null
    verifier "N2 réponses de l'explorateur dans l'archive" \
        contient liste "/explorateur/001-e2e4.json"
    verifier "N2 évaluations du moteur dans l'archive" \
        contient liste "/stockfish/evaluations.json"
    awk '/^## 3\./ {dedans = 1} /^### 3 bis/ {dedans = 0} dedans' synthese \
        | grep -E '^\| [0-9]+ \|' > table3
    egal "N2 douze lignes dans le tableau du moteur" 12 "$(lignes table3)"
    unzip -p "$ARCH" > contenu 2>/dev/null
    egal "N2 jeton absent de l'archive" 0 "$(compte_jeton contenu)"
    grep -E 'Stockfish : termin' journal > ligne 2>/dev/null
    joindre ligne
    joindre table3 12
fi

fi

# --- Bilan ------------------------------------------------------------------

titre "Bilan"
noter "  réussis : $NB_OK"
noter "  échecs  : $NB_ECHEC"
noter "  sautés  : $NB_SAUTE"

# Le répertoire personnel et le répertoire temporaire sont masqués : le
# rapport ne contient alors ni votre nom d'utilisateur ni de chemin privé.
# LC_ALL=C : le rapport peut contenir des octets qui ne sont pas de l'UTF-8,
# le nom de fichier refusé par T44 par exemple. Sous une locale UTF-8, le
# sed de macOS s'arrête alors sur "illegal byte sequence" et tronque le
# rapport ; en locale C, il traite le fichier octet par octet.
# Dernier garde-fou, avec --reseau : le rapport n'est écrit que si le jeton
# n'y figure pas. Un fichier de jeton qui contiendrait une ligne vide ferait
# échouer ce contrôle à tort, grep prenant alors tout pour une
# correspondance : le rapport serait retenu, par prudence.
if [ "$RESEAU" = 1 ] &&
    [ "$(grep -a -c -F -f "$JETON" "$BRUT" 2>/dev/null)" != "0" ]; then
    printf '\nLe jeton apparaît dans le rapport : rapport NON écrit.\n' >&2
    printf 'Relancez avec GARDER=1 et signalez-le sans rien envoyer.\n' >&2
    exit 3
fi

LC_ALL=C sed -e "s#$TRAVAIL#<TMP>#g" -e "s#$HOME#~#g" \
    -e "s#${ID_PARTIE:-aucune-partie-donnee}#<PARTIE>#g" "$BRUT" > "$RAPPORT"

printf '\nRéussis : %d, échecs : %d, sautés : %d\n' \
    "$NB_OK" "$NB_ECHEC" "$NB_SAUTE" >&2
printf 'Rapport : %s\n' "$RAPPORT" >&2

[ "$NB_ECHEC" -eq 0 ]
