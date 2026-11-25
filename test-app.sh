#!/bin/sh
# ===========================================================================
# test-app.sh: tests of ianalyze.py, on macOS and on Debian
#
# This script runs all the tests of the project, described one by one in
# TESTS.md, then writes a report that you can send back as it is.
#
#     sh test-app.sh             offline tests: encodings, archive,
#                                settings, time control, engine, check
#                                of the returned PGN. Neither token nor
#                                Lichess. About 3 minutes on a recent
#                                Mac, 6 on a Raspberry Pi.
#     sh test-app.sh --network   the same, then the tests that need the
#                                network and your token: catalog,
#                                explorer. About 3 more minutes.
#     sh test-app.sh --network GAME
#                                likewise, plus T24, which downloads a
#                                game from Lichess. GAME is the
#                                identifier or the address of any game
#                                of the site. The repository provides
#                                none: without it, T24 is skipped.
#
# Nothing is written in the repository, except the report, nor in your
# directories: everything happens in a temporary directory, deleted at
# the end. The tests name their own settings file and, with --network,
# their own catalog: yours are neither read nor modified.
#
# Your token, with --network: this script does not display it, does not
# copy it and does not pass it in any command line. It is ianalyze.py
# that reads it. The script itself only uses it as a pattern file for
# grep (option -f), to check that it appears neither in an archive nor
# in the report. If it were found in the report, the report would not be
# written.
#
# Load on Lichess, with --network: about 70 requests to the explorer,
# spaced 2 seconds apart by ianalyze.py, 10 catalog files from GitHub
# and, if you give a game, 2 exports of that game. PyPI is also asked
# once, for python-chess, to rebuild a virtual environment (T84).
#
# Optional variables:
#
#     VENV=/path/to/venv         virtual environment of python-chess
#     STOCKFISH=/path/to/binary  engine used by the engine tests
#     TOKEN=/path/to/file        token file (default: ~/.lichess_token)
#     KEEP=1                     keeps the temporary directory
#
# The script is written in POSIX shell: no arrays, no [[ ]], no "local".
# It has been checked with dash and bash, as well as with two checking
# tools: shellcheck and checkbashisms.
# ===========================================================================

# Three shellcheck notices are set aside for the whole file, on purpose:
# SC2086, the option variables ($O, $P, $MOTEUR, $EXPL) having to be
# split into several words; SC2012, ls only serving here to display the
# permissions of a file with a known name; SC2016, the backquotes looked
# for in the summary being markdown text and not a command.
# shellcheck disable=SC2086,SC2012,SC2016

set -u

# --- Arguments --------------------------------------------------------------

RESEAU=0
PARTIE=""
# True right after --network: the next argument, if it is not an option,
# is the game of T24.
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
        --network)
            RESEAU=1
            APRES_RESEAU=1
            ;;
        -h | --help)
            sed -n '2,/^# =====.*=$/p' "$0" | sed -n '2,$p' | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown argument: $argument" >&2
            echo "Usage: sh test-app.sh [--network [GAME]]" >&2
            exit 2
            ;;
    esac
done


# --- Locations --------------------------------------------------------------

DEPOT=$(pwd)
SCRIPT="$DEPOT/ianalyze.py"

if [ ! -f "$SCRIPT" ]; then
    echo "ianalyze.py not found in $DEPOT." >&2
    echo "Run this script from the repository directory." >&2
    exit 2
fi

SYSTEME=$(uname -s)

# Default virtual environment: the same place as in ianalyze.py, the
# local/ folder of the repository, on every platform.
if [ -z "${VENV:-}" ]; then
    VENV="$DEPOT/local/venv"
fi
PYVENV="$VENV/bin/python3"

if ! "$PYVENV" -c "import chess" >/dev/null 2>&1; then
    echo "python-chess not found in $VENV." >&2
    echo "Create the environment: ./ianalyze.py --install-venv" >&2
    echo "or give it: VENV=/path sh test-app.sh" >&2
    exit 2
fi

# Engine: the one you give, otherwise the one in the PATH, otherwise the
# usual locations of Homebrew and Debian.
if [ -z "${STOCKFISH:-}" ]; then
    STOCKFISH=$(command -v stockfish 2>/dev/null || true)
    for candidat in /opt/homebrew/bin/stockfish /usr/local/bin/stockfish \
                    /usr/games/stockfish; do
        if [ -z "$STOCKFISH" ] && [ -x "$candidat" ]; then
            STOCKFISH=$candidat
        fi
    done
fi

# Without an engine, no collection succeeds: the engine has been
# mandatory since version 4.0.0. It is better to stop here than to
# display hundreds of failures that say nothing about the script.
if [ -z "$STOCKFISH" ] || [ ! -x "$STOCKFISH" ]; then
    echo "Stockfish not found: the tests cannot run without it." >&2
    echo "Install it, or give it: STOCKFISH=/path sh test-app.sh" >&2
    exit 2
fi

JETON=${TOKEN:-$HOME/.lichess_token}
if [ "$RESEAU" = 1 ] && [ ! -f "$JETON" ]; then
    echo "Token file not found: $JETON" >&2
    echo "Give it: TOKEN=/path sh test-app.sh --network" >&2
    exit 2
fi
# Identifier of the game of T24, taken from what you gave by the very
# function of the script: an address and an identifier are accepted.
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
        echo "This is not a Lichess game: $PARTIE" >&2
        echo "Give its identifier, 8 characters, or its address:" >&2
        echo "    sh test-app.sh --network https://lichess.org/<identifier>" >&2
        exit 2
    fi
elif [ "$RESEAU" = 1 ]; then
    echo "No game given: T24, the download of a game, will be skipped." >&2
    echo "To play it, give any Lichess game:" >&2
    echo "    sh test-app.sh --network <identifier or address of the game>" >&2
fi

RAPPORT="$DEPOT/rapport-tests-$SYSTEME-$(date +%Y%m%d-%H%M%S).txt"
TRAVAIL=$(mktemp -d "${TMPDIR:-/tmp}/ianalyze-tests.XXXXXX") || exit 2
# Path cleaned up: on macOS, TMPDIR ends with a slash and the path built
# carries two of them, which prevented masking it in the report.
TRAVAIL=$(cd "$TRAVAIL" && pwd)

nettoyer() {
    if [ "${KEEP:-0}" = "1" ]; then
        echo "Temporary directory kept: $TRAVAIL" >&2
    else
        rm -rf "$TRAVAIL"
    fi
}
trap nettoyer EXIT
trap 'exit 130' INT TERM

cd "$TRAVAIL" || exit 2

# Options common to the tests that are about neither the explorer nor
# the engine. The variable is deliberately expanded without quotes.
O="--no-explorer --depth 1 --no-questions --stockfish $STOCKFISH"

# Settings file specific to the tests: yours is neither read nor
# modified. It carries a username, so that the tests that go through a
# terminal do not get the questions of the first run.
REGL="$TRAVAIL/reglages-tests.ini"
printf '[player]\nusernames = Moi\ntime_control = 14 days\nrating = 1300\n' \
    > "$REGL"

NB_OK=0
NB_ECHEC=0
NB_SAUTE=0
BRUT="$TRAVAIL/rapport.brut"
: > "$BRUT"

# --- Report tools -----------------------------------------------------------

# Writes a line in the report and, abridged, on the terminal.
noter() {
    printf '%s\n' "$*" >> "$BRUT"
}

titre() {
    noter ""
    noter "=== $* ==="
    printf '%s\n' "$*" >&2
}

# The POSIX shell has no local variables: a variable assigned in a
# function is that of the whole script. The functions that follow
# therefore prefix theirs, so that no test sees one of its own change
# value by calling them. T75 read the expected cause in a variable
# "attendu", which the function egal overwrote: it then looked for the
# digit 1 in the log, and found it or not depending on the time of day.

# verifier "label" command...: does the command succeed?
verifier() {
    verifier_libelle=$1
    shift
    if "$@" >/dev/null 2>&1; then
        NB_OK=$((NB_OK + 1))
        noter "  OK     $verifier_libelle"
    else
        NB_ECHEC=$((NB_ECHEC + 1))
        noter "  FAIL   $verifier_libelle"
        printf '    FAIL: %s\n' "$verifier_libelle" >&2
        # An expected text that is missing: the file searched is attached
        # to the report, so that the failure can be read without rerunning
        # the test.
        if [ "$1" = contient ] && [ -f "$2" ]; then
            joindre "$2" 8
        fi
    fi
}

# egal "label" expected obtained: comparison of two values. Spaces at
# the edges are ignored (wc adds some on macOS) and any run of spaces or
# tabs counts as a single space. Inner spaces count: "1 0" is not "10".
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
        noter "  FAIL   $1: expected [$2], got [$3]"
        printf '    FAIL: %s\n' "$1" >&2
    fi
}

sauter() {
    NB_SAUTE=$((NB_SAUTE + 1))
    noter "  SKIP   $*"
    printf '    skipped: %s\n' "$*" >&2
}

# Copies a file into the report, indented, limited to N lines (twenty by
# default), each line being cut at 200 characters.
joindre() {
    if [ -s "$1" ]; then
        head -n "${2:-20}" "$1" | LC_ALL=C cut -c1-200 | LC_ALL=C sed 's/^/      | /' >> "$BRUT"
    fi
}

# lancer options...: runs the script, stores standard output in
# "sortie", the log in "journal", and the exit code in RC. --venv is
# always passed: the script thus restarts in the virtual environment
# checked above, even if it is not the default one.
lancer() {
    "$SCRIPT" "$@" --venv "$VENV" --settings "$REGL" > sortie 2> journal
    RC=$?
    ARCH=$(head -n 1 sortie)
}

# Number of lines of a file, without the spaces that wc adds on macOS.
lignes() {
    wc -l < "$1" | tr -d ' '
}

# Does the file contain the string, taken literally?
contient() {
    grep -F -q -- "$2" "$1"
}

# Extracts a file from the current archive into the file "extrait".
extraire() {
    unzip -p "$ARCH" "$1" > extrait 2>/dev/null
}

# --- Report header ----------------------------------------------------------

titre "Environment"
noter "  date            : $(date '+%Y-%m-%d %H:%M:%S %z')"
noter "  system          : $(uname -srm)"
if command -v sw_vers >/dev/null 2>&1; then
    noter "  macOS           : $(sw_vers -productVersion 2>/dev/null)"
fi
if [ -r /etc/os-release ]; then
    noter "  distribution    : $(sed -n 's/^PRETTY_NAME=//p' /etc/os-release)"
fi
noter "  shell           : $(ls -l /bin/sh | sed 's/.* \/bin\/sh/\/bin\/sh/')"
noter "  system python3  : $(python3 --version 2>&1) ($(command -v python3))"
noter "  venv python     : $("$PYVENV" --version 2>&1)"
noter "  python-chess    : $("$PYVENV" -c 'import chess; print(chess.__version__)')"
noter "  venv            : $VENV"
noter "  stockfish       : $STOCKFISH"
noter "                    $(printf 'quit\n' | "$STOCKFISH" 2>/dev/null | head -n 1)"
noter "  locale          : LANG=${LANG:-} LC_ALL=${LC_ALL:-} LC_CTYPE=${LC_CTYPE:-}"
noter "  Python encodings: $("$PYVENV" -c 'import sys, locale; print(sys.stdout.encoding, sys.getfilesystemencoding(), locale.getpreferredencoding(False))')"
noter "  script version  : $(sed -n 's/^VERSION = //p' "$SCRIPT")"
if [ "$RESEAU" = 1 ]; then
    noter "  mode            : offline, then network and token (--network)"
    noter "  token file      : $JETON, permissions $(ls -l "$JETON" | cut -c1-10)"
    if [ -n "$ID_PARTIE" ]; then
        noter "  game of T24     : given, masked in this report"
    else
        noter "  game of T24     : none, T24 will be skipped"
    fi
else
    noter "  mode            : offline only"
fi
if command -v git >/dev/null 2>&1; then
    noter "  commit          : $(git -C "$DEPOT" log -1 --format='%h %s' 2>/dev/null)"
    noter "  script mode     : $(ls -l "$SCRIPT" | cut -c1-10)"
fi

printf '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 *\n' > italienne.pgn

# --- Platform ---------------------------------------------------------------

titre "T01, T02: compilation and help"
verifier "T01 py_compile" python3 -m py_compile "$SCRIPT"
rm -rf "$DEPOT/__pycache__"
"$SCRIPT" --help > aide 2> journal
egal "T02 --help, exit code" 0 $?
egal "T02 --min-moves quoted 4 times" 4 "$(grep -c -- --min-moves aide)"

titre "T31, T32: installation commands according to the platform"
if [ "$SYSTEME" = "Darwin" ]; then
    egal "T31 brew install quoted 4 times" 4 "$(grep -c 'brew install' aide)"
    egal "T32 apt install absent" 0 "$(grep -c 'apt install' aide)"
else
    egal "T31 brew install absent" 0 "$(grep -c 'brew install' aide)"
    egal "T32 apt install quoted 4 times" 4 "$(grep -c 'apt install' aide)"
fi
verifier "default of --venv in the application folder" \
    contient aide "/local/venv)"
verifier "default of --catalog in the application folder" \
    contient aide "/local)"
verifier "default of --settings in the application folder" \
    contient aide "/settings.ini)"

titre "T84: virtual environment left incomplete, recognized"
# A venv without pip, as an interrupted creation leaves it, a directory
# that only looks like a venv, without pyvenv.cfg, and the complete venv
# of the tests: only the first one may be rebuilt, and the second one,
# a wrong --venv, must never be emptied. The rebuild itself needs PyPI:
# it is played with --network.
rm -rf t84-sans-pip t84-pas-venv
"$PYVENV" -m venv --without-pip t84-sans-pip
mkdir -p t84-pas-venv/bin
ln -s "$(command -v python3)" t84-pas-venv/bin/python3
SCRIPT="$SCRIPT" VENV="$VENV" "$PYVENV" - > sortie-t84 2> journal-t84 <<'EOF'
import importlib.util
import os

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
print(cp.venv_incomplet("t84-sans-pip"), cp.venv_incomplet("t84-pas-venv"),
      cp.venv_incomplet(os.environ["VENV"]))
EOF
egal "T84 without pip, without pyvenv.cfg, complete" "True False False" \
    "$(cat sortie-t84)"
joindre journal-t84 5
rm -rf "$DEPOT/__pycache__"

titre "T85: --venv that is not a virtual environment, refused"
# A directory with an interpreter but no pyvenv.cfg, like /usr, and a
# directory of other files, like a home directory: --install-venv
# refuses both before anything runs, pip included, and changes nothing
# in them. A missing or empty directory and the venv of the tests are
# not refused. The refusal needs no network.
rm -rf t85-faux t85-autre t85-vide t85-absent
mkdir -p t85-faux/bin t85-autre t85-vide
ln -s "$(command -v python3)" t85-faux/bin/python3
echo temoin > t85-autre/temoin
for rep in t85-faux t85-autre; do
    "$SCRIPT" --install-venv --venv "$TRAVAIL/$rep" > sortie 2> journal
    egal "T85 $rep, exit code" 1 "$?"
    verifier "T85 $rep, refused" \
        contient journal "is not a virtual environment"
    egal "T85 $rep, nothing installed" 0 \
        "$(grep -c 'Installing python-chess' journal)"
done
egal "T85 nothing added to the two directories" "bin temoin" \
    "$(ls t85-faux) $(ls t85-autre)"
SCRIPT="$SCRIPT" VENV="$VENV" "$PYVENV" - > sortie-t85 2> journal-t85 <<'EOF'
import importlib.util
import os

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
print(cp.pas_un_venv("t85-faux"), cp.pas_un_venv("t85-autre"),
      cp.pas_un_venv("t85-vide"), cp.pas_un_venv("t85-absent"),
      cp.pas_un_venv(os.environ["VENV"]))
EOF
egal "T85 fake, other, empty, missing, complete" \
    "True True False False False" "$(cat sortie-t85)"
joindre journal-t85 5
rm -rf "$DEPOT/__pycache__"

titre "T05: minimal collection"
lancer italienne.pgn $O
egal "T05 exit code" 0 "$RC"
egal "T05 a single line on standard output" 1 "$(wc -l < sortie)"
verifier "T05 the archive exists" test -f "$ARCH"
unzip -l "$ARCH" > liste 2>/dev/null
verifier "T05 summary.md in the archive" contient liste "/summary.md"
verifier "T05 collection.json in the archive" contient liste "/collection.json"
egal "T05 no .partiel file in the archive" 0 "$(grep -c partiel liste)"

titre "T26: engine not found"
lancer italienne.pgn --no-explorer --no-questions --stockfish /nulle/part
egal "T26 exit code" 1 "$RC"
verifier "T26 message Stockfish not found" \
    contient journal "Stockfish not found: /nulle/part"
if [ "$SYSTEME" = "Darwin" ]; then
    verifier "T26 advice brew install stockfish" \
        contient journal "(brew install stockfish)"
fi
joindre journal

# --- Encodings --------------------------------------------------------------

titre "T34: PGN in latin-1, then in an unrecognized encoding"
# A latin-1 text reads as cp1252: the two only differ on bytes that no
# text uses.
printf '[White "Jos\351"]\n[Black "M\374ller"]\n\n' > t-latin1.pgn
printf '1. e4 e5 *\n' >> t-latin1.pgn
lancer t-latin1.pgn $O
egal "T34 exit code" 0 "$RC"
verifier "T34 encoding chosen: cp1252" \
    contient journal "encodage retenu : cp1252"
# The same in cp850: "é" is byte 0x82 there and "ü" byte 0x81, which
# cp1252 does not define. The script stops instead of removing the
# accented letters like control characters.
printf '[White "Jos\202"]\n[Black "M\201ller"]\n\n1. e4 e5 *\n' > t-cp850.pgn
lancer t-cp850.pgn $O
egal "T34 cp850, exit code" 1 "$RC"
verifier "T34 cp850, encoding not recognized" \
    contient journal "PGN encoding not recognized"
egal "T34 cp850, nothing is written" 0 \
    "$(ls -d analysis-t-cp850* 2>/dev/null | wc -l)"
lancer t-latin1.pgn $O
extraire '*/summary.md'
verifier "T34 White José" contient extrait "| White | José |"
verifier "T34 Black Müller" contient extrait "| Black | Müller |"
verifier "T34 encoding line in section 5" contient extrait "- Encodage : le PGN"
joindre journal

titre "T35: PGN in cp1252"
printf '[White "Jos\351"]\n[Event "Coupe d\222\351t\351 \226 5 \200"]\n' > t-cp1252.pgn
printf '\n1. e4 e5 *\n' >> t-cp1252.pgn
lancer t-cp1252.pgn $O
egal "T35 exit code" 0 "$RC"
verifier "T35 encoding chosen: cp1252" \
    contient journal "encodage retenu : cp1252"
extraire '*/summary.md'
verifier "T35 curly apostrophe, dash and euro" \
    contient extrait "| Event | Coupe d’été – 5 € |"
grep -F 'Event' extrait > ligne 2>/dev/null
joindre ligne

titre "T36: UTF-8 byte order mark"
printf '\357\273\277[White "Jos\303\251"]\n\n1. e4 e5 *\n' > t-bom.pgn
lancer t-bom.pgn $O
egal "T36 exit code" 0 "$RC"
verifier "T36 UTF-8 BOM removed" contient journal "(BOM) UTF-8 retirée"
extraire '*/game.pgn'
egal "T36 game.pgn starts with a bracket" "[" "$(head -c 1 extrait)"

titre "T37: UTF-16 with and without byte order mark"
if command -v iconv >/dev/null 2>&1; then
    printf '[White "Jos\303\251"]\n\n1. e4 e5 *\n' \
        | iconv -f UTF-8 -t UTF-16LE > t-utf16.pgn
    { printf '\377\376'; cat t-utf16.pgn; } > t-utf16-bom.pgn
    lancer t-utf16-bom.pgn $O
    egal "T37 with BOM, exit code" 0 "$RC"
    verifier "T37 with BOM, utf-16-le announced" \
        contient journal "(BOM) détectée, encodage retenu : utf-16-le"
    extraire '*/summary.md'
    verifier "T37 with BOM, White José" contient extrait "| White | José |"
    lancer t-utf16.pgn $O
    egal "T37 without BOM, exit code" 0 "$RC"
    verifier "T37 without BOM, utf-16-le recognized" \
        contient journal "un octet nul sur deux"
    extraire '*/summary.md'
    verifier "T37 without BOM, White José" contient extrait "| White | José |"
    joindre journal
else
    sauter "T37: iconv not found"
fi

titre "T38: damaged UTF-8"
printf '[White "Jos\303\251"]\n\n1. e4 {tr\377\376s bon} e5 *\n' > t-abime.pgn
lancer t-abime.pgn $O
egal "T38 exit code" 0 "$RC"
verifier "T38 two invalid bytes replaced" \
    contient journal "UTF-8 abîmé, 2 octet(s) invalide(s)"
extraire '*/summary.md'
verifier "T38 White José intact" contient extrait "| White | José |"
extraire '*/game.pgn'
egal "T38 comment kept" 1 "$(grep -c 's bon}' extrait)"

titre "T39: NUL bytes"
printf '[White "Jo\000s"]\n\n1. e4\000 e5 *\n' > t-nul.pgn
lancer t-nul.pgn $O
egal "T39 exit code" 0 "$RC"
verifier "T39 two NUL removed" contient journal "dont 2 NUL"
egal "T39 no NUL in the archive" 0 \
    "$(unzip -p "$ARCH" | od -c | grep -c '\\0')"
joindre journal

titre "T40: CRLF line ends"
printf '[White "A"]\r\n\r\n1. e4 e5 *\r\n' > t-crlf.pgn
lancer t-crlf.pgn $O
egal "T40 exit code" 0 "$RC"
egal "T40 no warning" 0 "$(grep -c Warning journal)"
egal "T40 no carriage return in game.pgn" 0 \
    "$(unzip -p "$ARCH" '*/game.pgn' | od -c | grep -c '\\r')"

titre "T41: C locale and ASCII output"
LANG=C "$SCRIPT" t-latin1.pgn $O --venv "$VENV" --settings "$REGL" \
    > sortie 2> journal
egal "T41 LANG=C, exit code" 0 $?
LC_ALL=C PYTHONUTF8=0 "$SCRIPT" --help > aide-c 2> journal
egal "T41 LC_ALL=C PYTHONUTF8=0 --help, exit code" 0 $?
grep 'startup questions' aide-c > ligne 2>/dev/null
noter "  note   help line under LC_ALL=C PYTHONUTF8=0:"
joindre ligne
PYTHONIOENCODING=ascii "$SCRIPT" --help > aide-ascii 2> journal
egal "T41 PYTHONIOENCODING=ascii --help, exit code" 0 $?
# The help is in English, without accents: those of the output come from
# the output directory, which the log names.
mkdir -p "$TRAVAIL/t41-été"
PYTHONIOENCODING=ascii "$SCRIPT" t-latin1.pgn $O --venv "$VENV" \
    --settings "$REGL" --output-dir "$TRAVAIL/t41-été" > sortie 2> journal
verifier "T41 accents replaced by ? in ASCII" \
    contient journal "t41-?t?"

titre "T42: control characters in the tags"
printf '[Event "Tour\tnoi"]\n[Site "\033[31mParis\007"]\n\n' > t-ctrl.pgn
printf '1. e4 e5 *\n' >> t-ctrl.pgn
lancer t-ctrl.pgn $O
egal "T42 exit code" 0 "$RC"
verifier "T42 two control characters removed" \
    contient journal "2 caractère(s) de contrôle retiré(s), dont 0 NUL"
extraire '*/summary.md'
verifier "T42 tab turned into a space" contient extrait "| Event | Tour noi |"
verifier "T42 ESC removed from Site" contient extrait "| Site | [31mParis |"
egal "T42 neither ESC nor BEL in the archive" 0 \
    "$(unzip -p "$ARCH" | tr -d -c '\033\007' | wc -c)"

titre "T43: dummy token file"
printf '\357\273\277lip_factice\r\n' > t-jeton
chmod 600 t-jeton
lancer italienne.pgn --depth 1 --no-questions \
    --token-file t-jeton --catalog /nulle/part
verifier "T43 BOM of the token removed" contient journal "(BOM) UTF-8 retirée"
verifier "T43 token accepted, stop on the catalog" \
    contient journal "Opening catalog missing"
egal "T43 the token is not displayed" 0 "$(grep -c lip_factice journal)"
printf 'lip_factic\351\n' > t-jeton
lancer italienne.pgn --depth 1 --no-questions \
    --token-file t-jeton --catalog /nulle/part
egal "T43 non-ASCII token, exit code" 1 "$RC"
verifier "T43 non-ASCII token refused" \
    contient journal "outside printable ASCII"
joindre journal

titre "T44: file names"
cp italienne.pgn 't-a:b?.pgn'
lancer 't-a:b?.pgn' $O
egal "T44 colon and question mark, exit code" 0 "$RC"
verifier "T44 folder sanitized as t-a_b_" \
    contient journal "Folder name sanitized: t-a_b_"
verifier "T44 the archive exists" test -f "$ARCH"
# Non-UTF-8 name: the macOS file system refuses it in principle.
NOM_LATIN=$(printf 't-\351t\351.pgn')
if cp italienne.pgn "$NOM_LATIN" 2> journal-cp; then
    lancer "$NOM_LATIN" $O
    egal "T44 non-UTF-8 name, exit code" 0 "$RC"
    verifier "T44 non-UTF-8 name, folder sanitized" \
        contient journal "Folder name sanitized"
    joindre journal
else
    sauter "T44 non-UTF-8 name: creation refused by the file system"
    joindre journal-cp
fi

titre "M1: accented name, output path with space and accent"
cp italienne.pgn "t-été à Paris.pgn"
lancer "t-été à Paris.pgn" $O --output-dir "$TRAVAIL/sorties d'été"
egal "M1 exit code" 0 "$RC"
verifier "M1 the displayed path does name the archive" test -f "$ARCH"
# The spaces of the PGN name become hyphens in that of the archive,
# those of the output directory are kept: it is yours.
case "$ARCH" in
    "$TRAVAIL/sorties d'été/analysis-t-été-à-Paris-"*.zip) vu=oui ;;
    *) vu=non ;;
esac
egal "M1 spaces of the name turned into hyphens" oui "$vu"
noter "  note   displayed path: $ARCH"
PYTHONIOENCODING=ascii "$SCRIPT" "t-été à Paris.pgn" $O \
    --output-dir "$TRAVAIL/sorties d'été" --venv "$VENV" --settings "$REGL" \
    > sortie 2> journal
ARCH=$(head -n 1 sortie)
verifier "M1 exact path even with an ASCII output" test -f "$ARCH"

titre "T45: answer typed in latin-1 on a pseudo-terminal"
rm -rf analysis-italienne-*
SCRIPT="$SCRIPT" VENV="$VENV" REGL="$REGL" python3 - > sortie-pty 2>&1 \
    <<'EOF'
import os
import pty
import time

script = os.environ["SCRIPT"]
pid, fd = pty.fork()
if pid == 0:
    os.execv(script, [script, "italienne.pgn", "--no-explorer",
                      "--depth", "1", "--keep-folder",
                      "--venv", os.environ["VENV"],
                      "--settings", os.environ["REGL"]])
for reponse in (b"w", b"Zo\xe9", b"", b"", b"", b"", b""):
    time.sleep(1)
    os.write(fd, reponse + b"\n")
time.sleep(3)
try:
    print(os.read(fd, 65536).decode("utf-8", "replace")[-300:])
except OSError as err:
    print("lecture du pseudo-terminal :", err)
os.waitpid(pid, 0)
EOF
cat analysis-italienne-*/game.pgn > extrait 2>/dev/null
verifier "T45 game.pgn carries [Black \"Zoé\"]" contient extrait '[Black "Zoé"]'
egal "T45 no unexpected error" 0 "$(grep -c 'Unexpected error' sortie-pty)"
joindre sortie-pty
rm -rf analysis-italienne-*

titre "T79: refused answers, too long or carrying PGN signs"
# The name of the opponent goes into a PGN tag: a quote or a bracket
# would close it too early. The first two answers are refused and the
# question asked again, the third one is kept.
rm -rf analysis-italienne-*
SCRIPT="$SCRIPT" VENV="$VENV" REGL="$REGL" python3 - > sortie-pty 2>&1 \
    <<'EOF'
import os
import pty
import time

script = os.environ["SCRIPT"]
pid, fd = pty.fork()
if pid == 0:
    os.execv(script, [script, "italienne.pgn", "--no-explorer",
                      "--depth", "1", "--keep-folder",
                      "--venv", os.environ["VENV"],
                      "--settings", os.environ["REGL"]])
recu = b""
for reponse in (b"w", b'Ev"il] [White "Pirate"] {x}', b"a" * 300, b"Bob",
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
print(texte.count("A name cannot contain"),
      texte.count("Answer too long: 255"),
      texte.count("Unexpected error"))
EOF
cat analysis-italienne-*/game.pgn > extrait 2>/dev/null
verifier "T79 name kept after two refusals" contient extrait '[Black "Bob"]'
egal "T79 a single White tag, no extra sign" "1 0" \
    "$(grep -c '^\[White ' extrait) $(grep -c 'Pirate' extrait)"
egal "T79 one refusal for a sign, one for the length, no error" "1 1 0" \
    "$(tail -n 1 sortie-pty)"
joindre sortie-pty
rm -rf analysis-italienne-*

titre "T80: long PGN name, in multibyte characters"
# A hundred ideograms, three hundred bytes: the label is bounded in
# bytes, otherwise the archive failed on a name too long after the
# analysis.
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
printf 'True 26\npartie-contre-machin\ngame a_b_\n' > attendu-t80
verifier "T80 label bounded in bytes, spaces as hyphens" \
    cmp -s attendu-t80 sortie-t80
joindre sortie-t80
joindre journal-t80 5
rm -rf "$DEPOT/__pycache__"

titre "T46, T47: sound PGN and version"
lancer italienne.pgn $O
egal "T46 no warning" 0 "$(grep -c Warning journal)"
extraire '*/collection.json'
verifier "T46 pgn_encoding utf-8" contient extrait '"pgn_encoding": "utf-8"'
verifier "T46 pgn_remarks empty" contient extrait '"pgn_remarks": []'
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
egal "T47 version in the X.Y.Z format, repeated in the user agent header" \
    "True True" "$(cat sortie-t47)"
joindre journal-t47 5
rm -rf "$DEPOT/__pycache__"

# --- Archive ----------------------------------------------------------------

titre "T48: dot in the PGN name"
cp italienne.pgn t-2026.11.18_A_vs_B.pgn
lancer t-2026.11.18_A_vs_B.pgn $O
egal "T48 exit code" 0 "$RC"
case $ARCH in
    analysis-t-2026.11.18_A_vs_B-*.zip) NOM_OK=oui ;;
    *) NOM_OK=non ;;
esac
egal "T48 full name of the archive" oui "$NOM_OK"
egal "T48 summary.md in the archive" 1 \
    "$(unzip -l "$ARCH" 2>/dev/null | grep -c summary.md)"
egal "T48 working folder deleted" 0 \
    "$(find . -maxdepth 1 -type d -name 'analysis-t-2026*' | wc -l)"

titre "T53: interruption during archiving, failing write"
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
d = pathlib.Path("analysis-essai-1")
d.mkdir()
for nom in ("game.pgn", "summary.md", "collection.json"):
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
    cp.ecrire_texte(d / "summary.md", 12345)
except TypeError:
    print((d / "summary.md").stat().st_size)
print(sorted(p.name for p in d.iterdir()))
print(cp.archiver(d, False))
print(sorted(p.name for p in pathlib.Path(".").iterdir()))
EOF
)
cat > attendu-r1 <<'EOF'
archivage interrompu
['analysis-essai-1']
5000
['collection.json', 'game.pgn', 'summary.md']
analysis-essai-1.zip
['analysis-essai-1.zip']
EOF
verifier "T53 six expected lines" cmp -s attendu-r1 sortie-r1
joindre sortie-r1
rm -rf "$DEPOT/__pycache__"

# --- Simulated explorer and options ----------------------------------------

titre "T49: unexpected answers of the explorer, simulated"
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
verifier "T49 two expected lines" cmp -s attendu-t49 sortie-t49
joindre sortie-t49
rm -rf "$DEPOT/__pycache__"

titre "T76: the token does not leave the explorer, simulated servers"
# Two local servers. The first one stands in for the explorer: it
# redirects to the second one, then sends back in its answer the
# Authorization header it received. The token, a dummy one, must
# neither follow the redirect nor get into the answer kept.
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
            # Error 500 whose announced body never arrives in full.
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
    print(code, statut, "redirection" in donnees.get("_error", ""))
print("tiers", len(recu))
statut, donnees = cp.Explorateur(
    JETON, 2.0, 5, base + "/echo", {}).interroger(["e2e4"])
print(statut, JETON in json.dumps(donnees), donnees.get("vu"))
# Answers that made the whole collection abort: HTTP error with a cut
# body, JSON nested too deep. Then the aberrant counts.
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
200 False Bearer <TOKEN-REDACTED>
/coupe 500 ['_error']
/profond 0 ['_error']
0 0 12 7
EOF
verifier "T76 redirects, redacted answer, damaged answers" \
    cmp -s attendu-t76 sortie-t76
joindre sortie-t76
joindre journal-t76 5
rm -rf "$DEPOT/__pycache__"

titre "T50: non-finite values"
for option in "--pause nan" "--pause inf" "--min-frequency nan"; do
    lancer italienne.pgn $option
    egal "T50 $option, exit code" 2 "$RC"
    verifier "T50 $option, message" contient journal "must be a finite number"
done
egal "T50 no working folder created" 0 \
    "$(find . -maxdepth 1 -type d -name 'analysis-italienne-*' | wc -l)"

titre "T54: URLs that are not games"
for url in https://lichess.org/analysis/standard \
           https://lichess.org/study/abcdefgh/ijklmnop \
           https://example.com/abcdefgh; do
    lancer "$url" --no-explorer --depth 1
    egal "T54 $url, exit code" 1 "$RC"
    verifier "T54 $url, refused" contient journal "URL not recognized"
    egal "T54 $url, no download" 0 "$(grep -c 'Downloading the PGN' journal)"
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
verifier "T54 identifiers extracted" cmp -s attendu-t54 sortie-t54
joindre sortie-t54
rm -rf "$DEPOT/__pycache__"

# --- Null move and explorer -------------------------------------------------

titre "T56: null move, simulated explorer"
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
print([(n["ply"], n["san"], n["motif"]) for n in r["non_exploitables"]])
print(r["arret"][:28])
EOF
cat > attendu-t56 <<'EOF'
2 2 None
[(3, '--', 'coup nul, non interrogé')]
coup nul au demi-coup 3 : ce
EOF
verifier "T56 stop at the null move, two requests, no exit" \
    cmp -s attendu-t56 sortie-t56
joindre sortie-t56
rm -rf "$DEPOT/__pycache__"

# --- Settings ---------------------------------------------------------------

# Pseudo-terminal driver: runs the script with the options given,
# answers the questions in order (answers separated by vertical bars),
# then displays what the terminal showed. The settings questions are
# only asked on a terminal.
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
# If an answer is missing, an end of stream is sent after fifteen
# seconds of silence: the script then takes its default values instead
# of waiting forever.
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
# Options of the runs on a pseudo-terminal.
P="--no-explorer --depth 1 --keep-folder --venv $VENV"

titre "T57: first run, settings asked then saved"
rm -rf analysis-italienne-*
SCRIPT="$SCRIPT" python3 t-pty.py "Zoe42, zoe|r|15|10|1300|w||||||" \
    italienne.pgn $P --settings t-reglages.ini > sortie-pty 2>&1
verifier "T57 three answers asked only once" \
    contient sortie-pty "3 answer(s) to give only once"
verifier "T57 rating question" \
    contient sortie-pty "Your rating, in approximate Elo points?"
verifier "T57 username question" contient sortie-pty "Your username"
verifier "T57 time control question" \
    contient sortie-pty "Your usual time control: [r]eal time, [c]orrespondence"
verifier "T57 minutes asked" contient sortie-pty "Minutes per player?"
verifier "T57 increment asked" contient sortie-pty "Increment in seconds?"
verifier "T57 settings saved" contient sortie-pty "Settings saved:"
grep -v '^#' t-reglages.ini > extrait 2>/dev/null
printf '\n[player]\nusernames = Zoe42, zoe\ntime_control = 15+10\n' > attendu
printf 'rating = 1300\n' >> attendu
verifier "T57 content of the file" cmp -s attendu extrait
cat analysis-italienne-*/game.pgn > extrait 2>/dev/null
verifier "T57 empty tag filled in with the username" \
    contient extrait '[White "Zoe42"]'
cat analysis-italienne-*/context.md > extrait 2>/dev/null
verifier "T57 usual time control suggested and written" \
    contient extrait "- Cadence : rapid, 15 minutes + 10 seconds per move (défaut)"
grep -E 'Settings|Your|per |rror' sortie-pty > ligne 2>/dev/null
joindre ligne

titre "T58: second run, priority of --usernames"
rm -rf analysis-italienne-*
SCRIPT="$SCRIPT" python3 t-pty.py "w||||||" italienne.pgn $P \
    --settings t-reglages.ini > sortie-pty 2>&1
egal "T58 no more settings question" 0 \
    "$(grep -c -E 'Settings|Your' sortie-pty)"
printf '[White "Alice"]\n[Black "Zoe42"]\n\n1. e4 e5 *\n' > t-noms.pgn
SCRIPT="$SCRIPT" python3 t-pty.py "||||" t-noms.pgn $P \
    --settings t-reglages.ini > sortie-pty 2>&1
cat analysis-t-noms-*/context.md > extrait 2>/dev/null
verifier "T58 side deduced from the username of the settings" \
    contient extrait "Camp du joueur : Noirs, déduit des en-têtes"
rm -rf analysis-t-noms-*
SCRIPT="$SCRIPT" python3 t-pty.py "||||" t-noms.pgn $P \
    --settings t-reglages.ini --usernames Alice > sortie-pty 2>&1
cat analysis-t-noms-*/context.md > extrait 2>/dev/null
verifier "T58 --usernames wins over the settings" \
    contient extrait "Camp du joueur : Blancs, déduit des en-têtes"
rm -rf analysis-t-noms-*

titre "T59: outside a terminal, then username refused"
"$SCRIPT" italienne.pgn $O --venv "$VENV" --settings t-abs/reglages.ini \
    > sortie 2> journal
egal "T59 outside a terminal, exit code" 0 $?
egal "T59 outside a terminal, nothing asked" 0 "$(grep -c -i 'settings' journal)"
if [ -e t-abs ]; then
    egal "T59 outside a terminal, no file created" absent présent
else
    egal "T59 outside a terminal, no file created" absent absent
fi
rm -rf analysis-italienne-*
SCRIPT="$SCRIPT" python3 t-pty.py "|||b|Moi|Lui|||||" italienne.pgn $P \
    --settings t-vide.ini > sortie-pty 2>&1
verifier "T59 without a username, the player name is asked" \
    contient sortie-pty "Your player name? (Enter: ?)"
grep -v '^#' t-vide.ini > extrait 2>/dev/null
printf '\n[player]\nusernames =\ntime_control = unknown\nrating = unknown\n' \
    > attendu
verifier "T59 empty keys saved, hence no longer asked" \
    cmp -s attendu extrait
cat analysis-italienne-*/game.pgn > extrait 2>/dev/null
verifier "T59 tags filled in with the names typed" \
    contient extrait '[Black "Moi"]'
egal "T59 no unexpected error" 0 "$(grep -c 'Unexpected error' sortie-pty)"
rm -rf analysis-italienne-*

titre "T60: badly formed file, added keys kept"
printf 'usernames = Alice\n' > t-mauvais.ini
"$SCRIPT" italienne.pgn $O --venv "$VENV" --settings t-mauvais.ini \
    > sortie 2> journal
egal "T60 badly formed file, exit code" 1 $?
verifier "T60 badly formed file, message" contient journal "Unreadable settings:"
verifier "T60 badly formed file, remedy given" \
    contient journal "or delete it"
printf '[player]\nusernames = Alice\nrating = 1500\n\n' > t-plus.ini
printf '[perso]\nnote = 100 %% à moi\n' >> t-plus.ini
SCRIPT="$SCRIPT" python3 t-pty.py "c|d|14|||||" t-noms.pgn $P \
    --settings t-plus.ini > sortie-pty 2>&1
grep -v '^#' t-plus.ini > extrait 2>/dev/null
cat > attendu <<'EOF'

[player]
usernames = Alice
time_control = 14 days
rating = 1500

[perso]
note = 100 % à moi
EOF
verifier "T60 keys and sections added by hand kept" \
    cmp -s attendu extrait
joindre extrait
rm -rf analysis-t-noms-*

titre "T62: time control checked, wrong answers refused"
printf '[player]\nusernames = Alice\nrating = unknown\n' > t-cad.ini
printf 'time_control = Ploum ploum\n' >> t-cad.ini
SCRIPT="$SCRIPT" python3 t-pty.py "x|r|abc|-5|0|0|r|15|10|||||" t-noms.pgn \
    $P --settings t-cad.ini > sortie-pty 2>&1
verifier "T62 unreadable time control of the settings asked again" \
    contient sortie-pty "the saved time control,"
egal "T62 type refused once" 1 \
    "$(grep -c 'answer: r, c or u' sortie-pty)"
egal "T62 number refused twice" 2 \
    "$(grep -c 'a whole number, 0 or more' sortie-pty)"
egal "T62 time control 0+0 refused" 1 \
    "$(grep -c 'neither time nor increment' sortie-pty)"
verifier "T62 time control saved in its short form" \
    contient t-cad.ini "time_control = 15+10"
egal "T62 no unexpected error" 0 "$(grep -c 'Unexpected error' sortie-pty)"
grep -E 'be read|answer|exist' sortie-pty > ligne 2>/dev/null
joindre ligne
rm -rf analysis-t-noms-*
SCRIPT="$SCRIPT" python3 t-pty.py "r|5|0||||" t-noms.pgn $P \
    --settings t-cad.ini > sortie-pty 2>&1
cat analysis-t-noms-*/context.md > extrait 2>/dev/null
verifier "T62 time control of the game different from the usual one" \
    contient extrait "- Cadence : blitz, 5 minutes without increment"
rm -rf analysis-t-noms-*
printf '[White "Alice"]\n[Black "Bob"]\n' > t-tc.pgn
printf '[TimeControl "600+5"]\n\n1. e4 e5 *\n' >> t-tc.pgn
SCRIPT="$SCRIPT" python3 t-pty.py "||||" t-tc.pgn $P \
    --settings t-cad.ini > sortie-pty 2>&1
egal "T62 TimeControl tag: no question" 0 \
    "$(grep -c 'Time control of the game' sortie-pty)"
cat analysis-t-tc-*/context.md > extrait 2>/dev/null
verifier "T62 TimeControl tag translated" \
    contient extrait "soit rapid, 10 minutes + 5 seconds per move"
grep Cadence extrait > ligne 2>/dev/null
joindre ligne
rm -rf analysis-t-tc-*

titre "T63: correspondence, three systems checked"
printf '[player]\nusernames = Alice\nrating = unknown\n' > t-corr.ini
SCRIPT="$SCRIPT" python3 t-pty.py \
    "c|x|c|0|0h|||c|5|36|36h|2||c|5|36h|20||||||" t-noms.pgn $P \
    --settings t-corr.ini > sortie-pty 2>&1
egal "T63 system refused once" 1 \
    "$(grep -c 'answer: d, p or c' sortie-pty)"
egal "T63 increment without a unit refused once" 1 \
    "$(grep -c 'followed by h or d' sortie-pty)"
egal "T63 inconsistent time control refused twice" 2 \
    "$(grep -c 'Inconsistent time control' sortie-pty)"
verifier "T63 clock, increment and maximum saved" \
    contient t-corr.ini "time_control = 5 days + 36 hours, maximum 20 days"
cat analysis-t-noms-*/context.md > extrait 2>/dev/null
verifier "T63 chess-mail.com: clock 5 days + 36 hours, maximum 20" \
    contient extrait "clock of 5 days + 36 hours per move, maximum of 20 days"
egal "T63 no unexpected error" 0 "$(grep -c 'Unexpected error' sortie-pty)"
grep -E 'answer|Inconsistent' sortie-pty > ligne 2>/dev/null
joindre ligne
rm -rf analysis-t-noms-*
printf '[player]\nusernames = Alice\nrating = unknown\n' > t-corr.ini
printf 'time_control = 10 moves in 50 days\n' >> t-corr.ini
SCRIPT="$SCRIPT" python3 t-pty.py "||||" t-noms.pgn $P \
    --settings t-corr.ini > sortie-pty 2>&1
cat analysis-t-noms-*/context.md > extrait 2>/dev/null
verifier "T63 standard ICCF: 10 moves in 50 days" \
    contient extrait "- Cadence : correspondence, 10 moves in 50 days (défaut)"
rm -rf analysis-t-noms-*
printf '[player]\nusernames = Alice\nrating = unknown\n' > t-corr.ini
printf 'time_control = 50d+3d, maximum 50d, bank 75d\n' >> t-corr.ini
SCRIPT="$SCRIPT" python3 t-pty.py "||||" t-noms.pgn $P \
    --settings t-corr.ini > sortie-pty 2>&1
cat analysis-t-noms-*/context.md > extrait 2>/dev/null
verifier "T63 ICCF Triple Block: clock, increment, maximum, bank" \
    contient extrait "clock of 50 days + 3 days per move, maximum of 50 days, bank of 75 days"
grep Cadence extrait > ligne 2>/dev/null
joindre ligne
rm -rf analysis-t-noms-*
# Settings file missing: the username is asked first, then, for lack
# of a username, the side.
SCRIPT="$SCRIPT" python3 t-pty.py "|c|p|10|40||w|||||" t-noms.pgn $P \
    --settings t-vide2.ini > sortie-pty 2>&1
verifier "T63 moves per period typed on the keyboard" \
    contient t-vide2.ini "time_control = 10 moves in 40 days"
rm -rf analysis-t-noms-*
# English plural, in the settings form and in the sentence: 0 and 2
# take an s, 1 does not. The forms checked above never reach 0 or 1.
SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t63 2> journal-t63 <<'EOF'
import importlib.util
import os

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
print(cp.noter_cadence({"type": "correspondance", "capital": 0,
                        "increment": 1, "plafond": 0, "reserve": 0}))
print(cp.noter_cadence({"type": "correspondance", "capital": 1,
                        "increment": 48, "plafond": 0, "reserve": 0}))
print(cp.decrire_cadence({"type": "reel", "initial": 0, "increment": 1}))
EOF
printf '%s\n' "0 days + 1 hour" "1 day + 2 days" \
    "bullet, 0 minutes + 1 second per move" > attendu-t63
verifier "T63 English plural: 0 days, 1 day, 2 days" \
    cmp -s attendu-t63 sortie-t63
joindre sortie-t63
joindre journal-t63 5
rm -rf "$DEPOT/__pycache__"

titre "T61: no more username in the script"
egal "T61 help of --usernames without a hard-coded value" 1 \
    "$(grep -c 'those of your settings' aide)"
egal "T61 username constant removed" 0 "$(grep -c 'PSEUDOS_DEFAUT' "$SCRIPT")"

# --- Analysis prompt --------------------------------------------------------

printf '[White "Alice"]\n[Black "Bob"]\n[BlackElo "1500"]\n\n' > t-pr.pgn
printf '1. e4 e5 *\n' >> t-pr.pgn
printf '[player]\nusernames = Alice\ntime_control = 14 days\nrating = 1300\n' \
    > t-pr.ini
# Options of the prompt tests, outside a terminal, with their own
# settings.
R="--no-explorer --no-questions --venv $VENV --settings t-pr.ini"

titre "T64: prompt written next to the archive"
"$SCRIPT" t-pr.pgn $R --depth 1 > sortie 2> journal
egal "T64 exit code" 0 $?
egal "T64 a single line on standard output" 1 "$(lignes sortie)"
ARCH=$(head -n 1 sortie)
PR="${ARCH%.zip}.prompt.txt"
verifier "T64 the prompt exists next to the archive" test -f "$PR"
verifier "T64 the log gives its path" \
    contient journal "Analysis prompt written:"
egal "T64 no marker of the template remains" 0 "$(grep -c -E '^#!|\{\{' "$PR")"
egal "T64 the prompt is not in the zip" 0 \
    "$(unzip -l "$ARCH" 2>/dev/null | grep -c prompt)"
verifier "T64 version and archive named" \
    contient "$PR" "Prompt produit par IAnalyze v"
verifier "T64 name of the archive repeated" contient "$PR" "$ARCH"
verifier "T64 username of the settings" \
    contient "$PR" "- pseudo, sur Lichess et en général : Alice"
verifier "T64 side deduced outside a terminal" \
    contient "$PR" "- camp dans cette partie : Blancs"
verifier "T64 declared rating" \
    contient "$PR" "- niveau : environ 1300 Elo, déclaré par le joueur"
verifier "T64 usual time control written" \
    contient "$PR" "celle de la partie : correspondence, 14 days per move"
unzip -p "$ARCH" '*/collection.json' > extrait 2>/dev/null
verifier "T64 collection.json names the prompt" contient extrait '"prompt_written": "analysis-t-pr-'
head -n 12 "$PR" > ligne
joindre ligne
noter "  note   lines of the prompt: $(lignes "$PR")"

titre "T65: the prompt keeps only what applies"
egal "T65 the engine figures are authoritative" 1 \
    "$(grep -c 'Les chiffres de la section 3 font foi' "$PR")"
egal "T65 Stockfish useless to the analyst" 1 \
    "$(grep -c 'Stockfish est inutile' "$PR")"
egal "T65 all the files of the archive to be used" 1 \
    "$(grep -c 'Servez-vous de TOUS les fichiers fournis' "$PR")"
egal "T65 evaluations.json described" 1 \
    "$(grep -c '^- stockfish/evaluations.json :' "$PR")"
egal "T65 without the explorer, its files are not announced" 0 \
    "$(grep -c '^- explorer/NNN' "$PR")"
egal "T65 comments cut at 75 columns, not at 76" "2 0" \
    "$(grep -c 'à 75' "$PR") $(grep -c 'à 76' "$PR")"
# Instructions added after the trials on four LLMs: each one answers a
# flaw found in a PGN actually returned.
for consigne in "9. LIGNES VIDES" \
    "N'écrivez jamais la variante à l'intérieur des accolades" \
    "vous êtes en cas B" \
    "N'annoncez un fichier que si vous l'avez réellement créé" \
    "ne rendez jamais un PGN sans commentaires"; do
    egal "T65 instruction: $consigne" 1 "$(grep -c -F "$consigne" "$PR")"
done
egal "T65 without the explorer, said in the prompt" 1 \
    "$(grep -c "collecte de l'explorateur n'a pas" "$PR")"
egal "T65 without the explorer, said in the task" 1 \
    "$(grep -c 'Aucune base n.a été interrogée' "$PR")"
egal "T65 without the explorer, no database announced" 0 \
    "$(grep -c 'La base interrogée' "$PR")"
egal "T65 without the explorer, no theoretical moves requested" 0 \
    "$(grep -c 'trois coups théoriques' "$PR")"
egal "T65 without the explorer, only section 3 is authoritative" 1 \
    "$(grep -c 'Seuls les chiffres de la section 3 font foi' "$PR")"
egal "T65 without the explorer, section 2 is not authoritative" 0 \
    "$(grep -c 'Les chiffres des sections 2 et 3 font foi' "$PR")"
# The recap, the Opening tag and the final instruction still referred
# to section 2, which this collection does not have.
egal "T65 without the explorer, no reference to section 2" "0 0 0" \
    "$(grep -c 'sortie de théorie)' "$PR") $(grep -c 'sections 2 et 3' "$PR") $(grep -c 'position nommée' "$PR")"
verifier "T65 without the explorer, section 3 alone prevails" \
    contient "$PR" "Les chiffres de la section 3 priment"
egal "T65 outside a terminal, answers not collected" 1 \
    "$(grep -c "n'a pas recueilli les réponses" "$PR")"
"$SCRIPT" t-pr.pgn $R --depth 1 --database masters > sortie 2> journal
PR="$(head -n 1 sortie)"
PR="${PR%.zip}.prompt.txt"
egal "T65 masters database named in section 2" 1 \
    "$(grep -c 'Section 2, "Explorateur maîtres"' "$PR")"
# The branches specific to each database are only written with the
# explorer: the template is rendered here without a collection,
# database by database.
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
verifier "T65 with the explorer, a single database branch" \
    cmp -s attendu-t65 sortie-t65
joindre sortie-t65
joindre journal-t65 5
rm -rf "$DEPOT/__pycache__"

titre "T66: faulty template refused before the collection"
rm -f analysis-t-pr-*
printf 'Bonjour {{PSEUDO}}\n' > t-modele.txt
"$SCRIPT" t-pr.pgn $R --depth 1 --prompt t-modele.txt \
    > sortie 2> journal
egal "T66 unknown value, exit code" 1 $?
verifier "T66 unknown value, line and name given" \
    contient journal "t-modele.txt, line 1: unknown value {{PSEUDO}}"
printf 'a\n#! si MOTEUR\nb\n#! fin\n' > t-modele.txt
"$SCRIPT" t-pr.pgn $R --depth 1 --prompt t-modele.txt \
    > sortie 2> journal
verifier "T66 unknown condition" \
    contient journal "line 2: unknown condition MOTEUR"
printf 'a\n#! si STOCKFISH\nb\n' > t-modele.txt
"$SCRIPT" t-pr.pgn $R --depth 1 --prompt t-modele.txt \
    > sortie 2> journal
verifier "T66 si never closed" contient journal "is never closed by"
printf 'a\n#! tantque STOCKFISH\n' > t-modele.txt
"$SCRIPT" t-pr.pgn $R --depth 1 --prompt t-modele.txt \
    > sortie 2> journal
verifier "T66 unknown directive" contient journal "unknown directive"
"$SCRIPT" t-pr.pgn $R --depth 1 --prompt /nulle/part.txt \
    > sortie 2> journal
egal "T66 missing template, exit code" 1 $?
verifier "T66 missing template, message" \
    contient journal "Prompt template not found: /nulle/part.txt"
"$SCRIPT" t-pr.pgn --prompt x --no-prompt > sortie 2> journal
egal "T66 exclusive options, exit code" 2 $?
egal "T66 no folder or archive created by these refusals" 0 \
    "$(find . -maxdepth 1 -name 'analysis-t-pr-*' | wc -l)"
printf 'Pour {{PSEUDOS}}.\n#! si non EXPLORATEUR\nsans base\n' > t-modele.txt
printf '#! si BASE_LICHESS\nlichess\n#! sinon\nmaitres\n#! fin\n' >> t-modele.txt
printf '#! sinon\navec base\n#! fin\n\n\n\nfin\n' >> t-modele.txt
"$SCRIPT" t-pr.pgn $R --depth 1 --prompt t-modele.txt \
    > sortie 2> journal
PR="$(head -n 1 sortie)"
PR="${PR%.zip}.prompt.txt"
printf 'Pour Alice.\nsans base\nlichess\n\nfin\n' > attendu
verifier "T66 nesting, negation and blank lines tightened" \
    cmp -s attendu "$PR"
joindre "$PR"
rm -f analysis-t-pr-*
"$SCRIPT" t-pr.pgn $R --depth 1 --no-prompt > sortie 2> journal
egal "T66 --no-prompt, exit code" 0 $?
egal "T66 --no-prompt, no prompt written" 0 \
    "$(find . -maxdepth 1 -name 'analysis-t-pr-*.prompt.txt' | wc -l)"

# Three templates that the script wrongly accepted: a badly written
# marker, which went as it is into the prompt, a template without a
# single line of text, and a prompt-only template whose game is only
# quoted in a note.
printf 'Camp : {{ CAMP }}\n' > t-modele-espace.txt
printf 'Camp : {{CAMP1}}\n' > t-modele-chiffre.txt
printf '#! note rien\n\n' > t-modele-vide.txt
printf '#! note {{PARTIE_PGN}}\nAnalysez.\n' > t-modele-note.txt
for cas in "t-modele-espace.txt|badly formed marker" \
           "t-modele-chiffre.txt|badly formed marker" \
           "t-modele-vide.txt|no line of text"; do
    lancer t-pr.pgn $R --depth 1 --prompt "${cas%%|*}"
    egal "T66 ${cas%%|*}, exit code" 1 "$RC"
    verifier "T66 ${cas%%|*}, message" contient journal "${cas##*|}"
done
lancer t-pr.pgn $R --depth 1 --prompt-only --prompt t-modele-note.txt
egal "T66 game quoted in a note, exit code" 1 "$RC"
verifier "T66 game quoted in a note, message" \
    contient journal "does not contain {{PARTIE_PGN}}"
# The game placed under a false condition: the prompt is written, but
# the log says that it cannot be pasted alone.
printf '#! si BASE_MAITRES\n{{PARTIE_PGN}}\n#! fin\nAnalysez.\n' > t-modele-branche.txt
lancer t-pr.pgn $R --depth 1 --prompt-only --prompt t-modele-branche.txt
egal "T66 game under a false condition, exit code" 0 "$RC"
verifier "T66 game under a false condition, said in the log" \
    contient journal "does not carry the game"
egal "T66 game under a false condition, no contrary announcement" 0 \
    "$(grep -c 'it carries the game' journal)"
rm -f analysis-t-pr-*

titre "T67: script copied without its template"
mkdir t-seul
cp "$SCRIPT" t-seul/
rm -f analysis-t-pr-*
t-seul/ianalyze.py t-pr.pgn $R --depth 1 > sortie 2> journal
egal "T67 exit code" 0 $?
verifier "T67 the archive is produced" test -f "$(head -n 1 sortie)"
verifier "T67 warning of the log" \
    contient journal "prompt template not found"
egal "T67 no prompt written" 0 \
    "$(find . -maxdepth 1 -name 'analysis-t-pr-*.prompt.txt' | wc -l)"

titre "T68: rating in Elo points, checked"
printf '[player]\nusernames = Alice\ntime_control = 14 days\nrating = strong\n' \
    > t-niv.ini
rm -rf analysis-t-pr-*
SCRIPT="$SCRIPT" python3 t-pty.py "abc|50|9999|1450|||||" t-pr.pgn $P \
    --settings t-niv.ini > sortie-pty 2>&1
verifier "T68 unreadable rating of the settings asked again" \
    contient sortie-pty "the saved rating,"
egal "T68 three answers refused" 3 \
    "$(grep -c 'between 100 and 3500' sortie-pty)"
verifier "T68 rating saved" contient t-niv.ini "rating = 1450"
cat analysis-t-pr-*.prompt.txt > extrait 2>/dev/null
verifier "T68 rating declared in the prompt" \
    contient extrait "- niveau : environ 1450 Elo, déclaré par le joueur"
verifier "T68 on a terminal, answers collected" \
    contient extrait "contient les réponses du joueur"
egal "T68 no unexpected error" 0 "$(grep -c 'Unexpected error' sortie-pty)"
printf '[player]\nusernames = Bob\ntime_control = 14 days\nrating = unknown\n' \
    > t-niv.ini
rm -rf analysis-t-pr-*
"$SCRIPT" t-pr.pgn --no-explorer --no-questions --depth 1 \
    --venv "$VENV" --settings t-niv.ini > sortie 2> journal
cat analysis-t-pr-*.prompt.txt > extrait 2>/dev/null
verifier "T68 side deduced from the other username" \
    contient extrait "- camp dans cette partie : Noirs"
verifier "T68 without a declared rating, Elo of the tag" \
    contient extrait "- niveau : 1500 Elo, d'après la balise BlackElo de la partie"
rm -rf analysis-t-pr-*

titre "T86: --no-settings, settings neither read nor written"
# A copy of the script looks for its settings file next to itself: the
# test gives it its own, so that yours, next to the script of the
# repository, is never touched, even if a check below fails. The copy
# has no template next to it: it gets the one of the repository.
mkdir t-86
cp "$SCRIPT" t-86/
printf '[player]\nusernames = Bob\ntime_control = 14 days\nrating = 1300\n' \
    > t-86/settings.ini
cp t-86/settings.ini t-86-avant.ini
rm -rf analysis-t-pr-*
t-86/ianalyze.py t-pr.pgn --no-explorer --no-questions --depth 1 \
    --venv "$VENV" --prompt "$DEPOT/prompt-modele.txt" > sortie 2> journal
cat analysis-t-pr-*.prompt.txt > extrait 2>/dev/null
verifier "T86 without the option, the copy reads its settings" \
    contient extrait "- niveau : environ 1300 Elo, déclaré par le joueur"
verifier "T86 without the option, usual time control of the settings" \
    contient extrait "celle de la partie : correspondence, 14 days per move"
rm -rf analysis-t-pr-*
t-86/ianalyze.py t-pr.pgn --no-explorer --no-questions --depth 1 \
    --venv "$VENV" --prompt "$DEPOT/prompt-modele.txt" --no-settings \
    > sortie 2> journal
egal "T86 exit code" 0 "$?"
verifier "T86 said in the log" \
    contient journal "Settings neither read nor written: option --no-settings."
cat analysis-t-pr-*.prompt.txt > extrait 2>/dev/null
verifier "T86 usernames of the settings ignored, side unknown" \
    contient extrait "- camp dans cette partie : inconnu"
verifier "T86 rating of the settings ignored" \
    contient extrait "- niveau : non précisé"
verifier "T86 usual time control of the settings ignored" \
    contient extrait "celle de la partie : unspecified"
unzip -p "$(head -n 1 sortie)" '*/collection.json' > ligne 2>/dev/null
verifier "T86 recorded in collection.json" contient ligne '"no_settings": true'
rm -rf analysis-t-pr-*
t-86/ianalyze.py t-pr.pgn --no-explorer --no-questions --depth 1 \
    --venv "$VENV" --prompt "$DEPOT/prompt-modele.txt" --no-settings \
    --usernames Bob > sortie 2> journal
cat analysis-t-pr-*.prompt.txt > extrait 2>/dev/null
verifier "T86 side deduced from --usernames" \
    contient extrait "- camp dans cette partie : Noirs"
verifier "T86 rating taken from the Elo tag of that side" \
    contient extrait "- niveau : 1500 Elo, d'après la balise BlackElo de la partie"
verifier "T86 settings file untouched" cmp -s t-86-avant.ini t-86/settings.ini
rm -rf analysis-t-pr-*
# On a terminal, without a settings file: its questions, which would
# create it, are not asked, and the side is asked instead.
rm -f t-86/settings.ini
rm -rf analysis-t-noms-*
SCRIPT=t-86/ianalyze.py python3 t-pty.py "b|||||" t-noms.pgn $P \
    --no-settings > sortie-pty 2>&1
egal "T86 on a terminal, no settings question" 0 \
    "$(grep -c -E 'Settings:|Your username|Your usual|Your rating' sortie-pty)"
verifier "T86 on a terminal, the side is asked" \
    contient sortie-pty "Did you play White or Black? [w/b]"
verifier "T86 on a terminal, no settings file created" \
    test ! -e t-86/settings.ini
cat analysis-t-noms-*/context.md > extrait 2>/dev/null
verifier "T86 on a terminal, side declared" \
    contient extrait "Camp du joueur : Noirs, déclaré"
egal "T86 no unexpected error" 0 "$(grep -c 'Unexpected error' sortie-pty)"
joindre sortie-pty
rm -rf analysis-t-noms-*
# Refused with --settings, whatever the path, and with --purge-settings,
# which would delete what the option leaves alone.
printf '[player]\nusernames = Bob\n' > t-86/settings.ini
t-86/ianalyze.py t-pr.pgn --no-settings --settings t-86/settings.ini \
    > sortie 2> journal
egal "T86 with --settings, exit code" 2 "$?"
verifier "T86 with --settings, refused" \
    contient journal "not allowed with argument"
t-86/ianalyze.py --purge-settings --no-settings > sortie 2> journal
egal "T86 with --purge-settings, exit code" 2 "$?"
verifier "T86 with --purge-settings, refused" \
    contient journal "--purge-settings and --no-settings are mutually exclusive"
verifier "T86 with --purge-settings, file kept" test -f t-86/settings.ini
joindre journal

titre "T87: collection.json in English, a key for every option"
# collection.json takes the keys of the options from CLEFS_COLLECTE: the
# dest of argparse stay French in the code. A new option without its
# key would stop the collection: this check names it first.
SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t87 2> journal-t87 <<'EOF'
import importlib.util
import os

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
dests = set(vars(cp.analyser_arguments(["x.pgn"])))
clefs = set(cp.CLEFS_COLLECTE)
valeurs = list(cp.CLEFS_COLLECTE.values())
print("missing:", sorted(dests - clefs))
print("extra:", sorted(clefs - dests))
print("repeated:", sorted({v for v in valeurs if valeurs.count(v) > 1}))
print("lowercase ascii:", all(v.isascii() and v == v.lower() for v in valeurs))
EOF
printf '%s\n' "missing: []" "extra: []" "repeated: []" \
    "lowercase ascii: True" > attendu-t87
verifier "T87 one key for each option, none left over or repeated" \
    cmp -s attendu-t87 sortie-t87
joindre sortie-t87
joindre journal-t87 5
rm -rf "$DEPOT/__pycache__"
# The keys actually written: those of the table, then those that the
# collection adds, and no other one.
rm -rf analysis-t-pr-*
"$SCRIPT" t-pr.pgn --no-explorer --no-questions --depth 1 \
    --venv "$VENV" --settings t-pr.ini --no-prompt > sortie 2> journal
unzip -p "$(head -n 1 sortie)" '*/collection.json' > t87.json 2>/dev/null
SCRIPT="$SCRIPT" "$PYVENV" - t87.json > sortie-t87 2> journal-t87 <<'EOF'
import importlib.util
import json
import os
import sys

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
with open(sys.argv[1], encoding="utf-8") as f:
    donnees = json.load(f)
ajoutees = {"token_present", "catalog_used", "side", "context_collected",
            "pgn_encoding", "pgn_remarks", "prompt_written"}
print(set(donnees) == set(cp.CLEFS_COLLECTE.values()) | ajoutees,
      donnees.get("depth"), donnees.get("output_dir"))
EOF
egal "T87 keys of collection.json, depth and output directory" "True 1 ." \
    "$(cat sortie-t87)"
joindre journal-t87 5
rm -rf "$DEPOT/__pycache__"
rm -rf analysis-t-pr-*

titre "T74: prompt only, short, to be pasted without an attachment"

# With --prompt-only, the prompt is drawn from a short template: a few
# instructions, the game, then the engine evaluations. It is pasted
# alone into the conversation. Nothing else is written: neither archive
# nor working folder, and standard output gives the path of the prompt.
printf '[White "Alice"]\n[Black "Bob"]\n[Result "1-0"]\n\n' > t-seul.pgn
printf '1. e4 e5 2. Qh5 Nc6 3. Qxf7+ Kxf7 1-0\n' >> t-seul.pgn
S74="--no-explorer --no-questions --venv $VENV --settings t-pr.ini"
S74="$S74 --depth 8 --threads 2 --hash 32"
"$SCRIPT" t-seul.pgn $S74 --prompt-only > sortie 2> journal
egal "T74 exit code" 0 $?
PR="$(head -n 1 sortie)"
verifier "T74 standard output gives the prompt" test -f "$PR"
egal "T74 a single file written, neither archive nor folder" \
    "analysis-t-seul-.prompt.txt" \
    "$(ls -d analysis-t-seul-* | sed 's/[0-9]\{8\}-[0-9]\{6\}//')"
verifier "T74 the log says that no archive is written" \
    contient journal "no archive is written"
verifier "T74 the log says to paste it alone" \
    contient journal "to be pasted alone into the conversation"
egal "T74 no marker of the template remains" 0 "$(grep -c -E '^#!|\{\{' "$PR")"
verifier "T74 short prompt, fewer than a hundred lines" \
    test "$(lignes "$PR")" -lt 100
while IFS= read -r present; do
    verifier "T74 present: $present" contient "$PR" "$present"
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
    egal "T74 absent: $absent" 0 "$(grep -c -F "$absent" "$PR")"
done <<'FIN'
IAnalyze
archive
summary.md
Données brutes
CAS A
FIN
# The table has one line per ply, and the queen given away on move 3
# is a blunder there, followed by the best move and its continuation.
egal "T74 table: one line per ply" 6 \
    "$(grep -c -E '^[1-3]\.(\.\.)? [A-Za-z0-9+#x=-]+ +[+#-]' "$PR")"
egal "T74 table: blunder, loss and best move" 1 \
    "$(grep -c -E '^3\. Qxf7\+ .* gaffe \([0-9a-z]+\) : mieux 3\. ' "$PR")"
# Scored 1-0, the game ends with White a queen down.
egal "T74 result contrary to the evaluation, told to the LLM" 1 \
    "$(grep -c '^Attention : Résultat et évaluation finale' "$PR")"
# The review asks for three errors. An LLM asked for three makes one up
# when the player made fewer: the prompt then gives the number of weak
# moves that its table carries. White played only three moves, and the
# engine does not always judge the same ones weak from one machine to
# another: the expected count is read in the table of the prompt.
FAIBLES74="$(grep -c -E '^[0-9]+\. .* (imprécision|erreur|gaffe) \(' "$PR")"
if [ "$FAIBLES74" -lt 3 ]; then
    verifier "T74 review: the number of weak moves of the player is given" \
        contient "$PR" "Coups faibles du joueur dans le tableau : $FAIBLES74."
    egal "T74 review: only one of the two sentences" 0 \
        "$(grep -c 'les trois erreurs' "$PR")"
else
    verifier "T74 review: three weak moves, three errors requested" \
        contient "$PR" "les trois erreurs"
    egal "T74 review: only one of the two sentences" 0 \
        "$(grep -c 'Coups faibles du joueur' "$PR")"
fi
# With --keep-folder, the working folder stays, without an archive:
# verifier-analyse.py can read it, with the very figures of the prompt.
rm -f analysis-t-seul-*
"$SCRIPT" t-seul.pgn $S74 --prompt-only --keep-folder \
    > sortie 2> journal
PR="$(head -n 1 sortie)"
DOSSIER74="${PR%.prompt.txt}"
verifier "T74 --keep-folder, the evaluations stay" \
    test -f "$DOSSIER74/stockfish/evaluations.json"
egal "T74 --keep-folder, still no archive" 0 \
    "$(find . -maxdepth 1 -name 'analysis-t-seul-*.zip' | wc -l)"
cp "$DOSSIER74/game.pgn" t-partie.pgn
rm -rf "$DOSSIER74"
verifier "T74 PGN of the collection repeated as it is" \
    "$PYVENV" -c '
import sys
prompt = open(sys.argv[1], encoding="utf-8").read()
partie = open(sys.argv[2], encoding="utf-8").read().strip("\n")
sys.exit(0 if partie in prompt else 1)
' "$PR" t-partie.pgn
egal "T74 without instructions, nothing is specified" 0 \
    "$(grep -c 'Ce que le joueur a précisé' "$PR")"
noter "  note   size of the prompt only: $(wc -c < "$PR") octets, $(lignes "$PR") lignes"
head -n 6 "$PR" > ligne
joindre ligne
rm -f analysis-t-seul-*
# What the short prompt takes from the player's answers: those that
# they did not leave at their default, without the side, stated
# elsewhere.
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
    "- Cadence : balise TimeControl `600+5`, soit rapid\n"
    "- Cadence : unspecified\n"))
EOF
printf '%s\n' "- Objectif : la sortie de la dame" "[]" "[]" > attendu-t74
verifier "T74 answers of the player repeated, defaults, side and tag set aside" \
    cmp -s attendu-t74 sortie-t74
joindre journal-t74 5
rm -rf "$DEPOT/__pycache__"
# The count of weak moves, without the engine. Its rule is that of the
# table: a move is only marked there if it has a category and a better
# move. The short template changes its sentence when the player has
# fewer than three.
SCRIPT="$SCRIPT" "$PYVENV" - > sortie-t74 2> journal-t74 <<'EOF'
import importlib.util
import os
import pathlib

spec = importlib.util.spec_from_file_location("cp", os.environ["SCRIPT"])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)


def coup(trait, nature, meilleurs=("x",)):
    return {"side_to_move": trait, "category": nature, "best": list(meilleurs)}


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
# Four cases: no weak move, fewer than three, three or more, and an
# unknown side, where "le joueur" belongs to no side.
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
verifier "T74 review: count of the weak moves, sentence according to the count" \
    cmp -s attendu-t74 sortie-t74
joindre sortie-t74
joindre journal-t74 5
rm -rf "$DEPOT/__pycache__"
# A PGN ending with a space: the prompt does carry the game, and the
# log must not announce the opposite.
printf '[White "Alice"]\n[Black "Bob"]\n\n1. e4 e5 * ' > t-espace.pgn
"$SCRIPT" t-espace.pgn $S74 --prompt-only > sortie 2> journal
egal "T74 PGN ending with a space, no false alert" "0 1" \
    "$(grep -c 'does not carry the game' journal) $(grep -c 'to be pasted alone into the conversation' journal)"
rm -f analysis-t-espace-*
# Two runs within the same second bore the same name: the second
# prompt overwrote the first one. Six runs, six files.
mkdir -p t-meme-seconde
for essai in 1 2 3 4 5 6; do
    "$SCRIPT" t-espace.pgn --no-explorer --no-questions \
        --venv "$VENV" --settings t-pr.ini --depth 1 --threads 1 \
        --hash 16 --prompt-only --output-dir t-meme-seconde \
        > /dev/null 2>> journal || noter "  note   lancement $essai en échec"
done
egal "T74 runs close together, no prompt overwritten" 6 \
    "$(find t-meme-seconde -name '*.prompt.txt' | wc -l)"
rm -rf t-meme-seconde
"$SCRIPT" t-seul.pgn $S74 > sortie 2> journal
PR="$(head -n 1 sortie)"
PR="${PR%.zip}.prompt.txt"
egal "T74 without the option, the full prompt" "0 1" \
    "$(grep -c '^La partie :' "$PR") $(grep -c 'PIÈCES JOINTES ATTENDUES' "$PR")"
# verifier-analyse.py --prompt-only expects the tags of the original
# game, and not the seven of the standard: t-seul.pgn carries only
# three, and its faithful copy must not be found at fault. The same
# tags returned in another order, for their part, are.
ARCH74="$(head -n 1 sortie)"
"$PYVENV" "$DEPOT/verifier-analyse.py" "$ARCH74" t-seul.pgn --prompt-only \
    > bilan 2>&1
verifier "T74 checker: three tags copied, no fault" \
    contient bilan "OK        les balises obligatoires de la partie d'origine"
printf '[Black "Bob"]\n[White "Alice"]\n[Result "1-0"]\n\n' > t-seul-inverse.pgn
printf '1. e4 e5 2. Qh5 Nc6 3. Qxf7+ Kxf7 1-0\n' >> t-seul-inverse.pgn
"$PYVENV" "$DEPOT/verifier-analyse.py" "$ARCH74" t-seul-inverse.pgn \
    --prompt-only > bilan 2>&1
verifier "T74 checker: tags in another order, reported" \
    contient bilan "ECHEC     les balises obligatoires de la partie d'origine"
rm -rf "$DEPOT/__pycache__"
rm -f analysis-t-seul-*
"$SCRIPT" t-seul.pgn $S74 --prompt-only --no-prompt > sortie 2> journal
egal "T74 exclusive options, exit code" 2 $?
verifier "T74 exclusive options, message" \
    contient journal "--prompt-only and --no-prompt are mutually exclusive"
# A personal template that does not place the game is refused before
# the collection: the prompt would have nothing to have analyzed.
printf 'Bonjour {{PSEUDOS}}.\n' > t-modele.txt
"$SCRIPT" t-seul.pgn $S74 --prompt t-modele.txt --prompt-only \
    > sortie 2> journal
egal "T74 template without the game, exit code" 1 $?
verifier "T74 template without the game, message" \
    contient journal "does not contain {{PARTIE_PGN}}"
mkdir -p t-seul-74 && cp "$SCRIPT" t-seul-74/
t-seul-74/ianalyze.py t-seul.pgn $S74 --prompt-only \
    > sortie 2> journal
egal "T74 script copied without its template, exit code" 1 $?
verifier "T74 script copied without its template, message" \
    contient journal "Prompt template not found"
egal "T74 no folder or archive created by these refusals" 0 \
    "$(find . -maxdepth 1 -name 'analysis-t-seul-*' | wc -l)"

titre "T03: refused options"

# An option without effect or out of bounds is refused, code 2, before
# any reading of the game. Each line gives the options, then the
# message.
while IFS='|' read -r refusees message; do
    # The options are split into words, hence the missing quotes.
    # shellcheck disable=SC2086
    "$SCRIPT" italienne.pgn $refusees --venv "$VENV" > sortie 2> journal
    egal "T03 $refusees, exit code" 2 "$?"
    verifier "T03 $refusees, message" contient journal "$message"
done <<'FIN'
--database masters --speeds rapid|--speeds only has an effect with --database lichess
--database lichess --speeds rapide|--speeds: unknown value "rapide"
--database lichess --ratings 1100|--ratings: unknown value "1100"
--min-moves -1|--min-moves must be 0 or more
--pause 1|--pause must not go below 2 seconds
--min-frequency 150|--min-frequency must be between 0 and 100
--database plebe|argument --database: invalid choice: 'plebe'
FIN

titre "T04: PGN file not found"

lancer "$TRAVAIL/inexistant.pgn" $O
egal "T04 absolute path, exit code" 1 "$RC"
verifier "T04 absolute path, message" \
    contient journal "PGN file not found"
lancer inexistant.pgn $O
egal "T04 relative name, exit code" 1 "$RC"
verifier "T04 relative name, taken for a file and not for an identifier" \
    contient journal "PGN file not found"

titre "T75: PGNs that python-chess would misread, refused"

# Each of these files is read without error by python-chess, which
# skips what it does not recognize: French notation read as pawn moves,
# game truncated at the brace never closed. The script must refuse them
# before the reading, and name what stops it.
printf '1. e4 e5 2. Cf3 Cc6 3. Fc4 Fc5 *\n' > t-francais.pgn
printf '1. e4 e5 2. \342\231\230f3 *\n' > t-figurines.pgn
printf '1. e4 e5 2. nf3 nc6 *\n' > t-minuscules.pgn
printf '1. e4 e5 2. Nf3 { bon coup Nc6 3. Bb5 a6 1-0\n' > t-accolade.pgn
printf '1. e4 e5 ( 1... c5 ( 1... d5\n' > t-parenthese.pgn
printf '1. e4 e5 2. Ke3 ) $2 *\n' > t-orpheline.pgn
printf '1. e4 e5 2. Nf3 *\n\nLes Blancs gagnent (voir b5) !\n' > t-queue.pgn
while read -r fichier cause; do
    lancer "$fichier" $O < /dev/null
    egal "T75 $fichier, exit code" 1 "$RC"
    verifier "T75 $fichier, refused as a corrupt PGN" \
        contient journal "Corrupt PGN"
    verifier "T75 $fichier, cause named" contient journal "$cause"
    egal "T75 $fichier, no unexpected error" 0 \
        "$(grep -c 'Unexpected error' journal)"
done <<'FIN'
t-francais.pgn "Cf3"
t-figurines.pgn English notation
t-minuscules.pgn "nf3"
t-accolade.pgn is never closed
t-parenthese.pgn and never closed
t-orpheline.pgn without an open variation
t-queue.pgn "Les"
FIN
joindre journal 3
egal "T75 no folder or archive created by these refusals" 0 \
    "$(ls -d analysis-t-francais* analysis-t-accolade* analysis-t-queue* 2>/dev/null | wc -l)"
# A file with several games is refused too, with their number.
printf '[Event "a"]\n\n1. e4 e5 1-0\n\n[Event "b"]\n\n1. d4 d5 0-1\n' > t-deux.pgn
printf '\n[Event "c"]\n\n1. c4 *\n' >> t-deux.pgn
lancer t-deux.pgn $O
egal "T75 several games, exit code" 1 "$RC"
verifier "T75 several games, number announced" \
    contient journal "The PGN contains 3 games"
egal "T75 several games, nothing is written" 0 \
    "$(ls -d analysis-t-deux* 2>/dev/null | wc -l)"
# A result repeated at the end of the file is not a second game: some
# sites write "0-1", a blank line, then "0-1" again. The file is
# accepted, and the log says what is ignored. Followed by a real game,
# the same file stays refused.
printf '[White "Alice"]\n[Black "Bob"]\n[Result "0-1"]\n1.e4 e5\n0-1\n\n0-1\n' \
    > t-repete.pgn
lancer t-repete.pgn $O
egal "T75 repeated result, exit code" 0 "$RC"
verifier "T75 repeated result, said in the log" \
    contient journal "Result repeated at the end of the file"
rm -f analysis-t-repete-*
printf '\n1. d4 d5 *\n' >> t-repete.pgn
lancer t-repete.pgn $O
egal "T75 repeated result then a real game, refused" 1 "$RC"
verifier "T75 repeated result then a real game, two games" \
    contient journal "The PGN contains 2 games"
# What must keep getting through: moves stuck to the number, annotation
# symbols, NAG, castling written with zeros, end-of-line comment.
printf '1.e4 e5 2.Nf3! Nc6?! 3.Bc4 $1 Bc5 { ok } 4. c3 ; fin\n' > t-formes.pgn
printf '4... Nf6 5. 0-0 0-0 *\n' >> t-formes.pgn
lancer t-formes.pgn $O
egal "T75 accepted forms, exit code" 0 "$RC"

titre "T77: inputs that ended in an unexpected error"

# Standard input closed by the caller, without --no-questions: it is
# not a terminal, no question is asked and the collection is done.
"$SCRIPT" italienne.pgn --no-explorer --depth 1 \
    --venv "$VENV" --settings "$REGL" <&- > sortie 2> journal
egal "T77 standard input closed, exit code" 0 "$?"
verifier "T77 standard input closed, questions skipped" \
    contient journal "non-interactive terminal"
rm -rf analysis-italienne-*
# A file name that the system refuses to look at, here too long.
lancer "$(printf '%0300d' 0).pgn" $O
egal "T77 name too long, exit code" 1 "$RC"
verifier "T77 name too long, file not found" \
    contient journal "PGN file not found"
# A URL with misplaced brackets.
lancer 'https://[lichess.org]/abcdefgh' $O
egal "T77 badly formed URL, exit code" 1 "$RC"
verifier "T77 badly formed URL, refused" contient journal "URL not recognized"
# A game that starts from a FEN tag is not a whole game: it is refused,
# whatever the position. The initial position written out in full, for
# its part, stays a whole game.
printf '[SetUp "1"]\n[FEN "6k1/5ppp/8/8/8/8/5PPP/3Q2K1 b - - 0 30"]\n\n' > t-depuis-fen.pgn
printf '30... h6 31. Qd8+ Kh7 *\n' >> t-depuis-fen.pgn
lancer t-depuis-fen.pgn $O
egal "T77 game from a FEN, exit code" 1 "$RC"
verifier "T77 game from a FEN, refused" \
    contient journal "does not start from the initial position"
egal "T77 game from a FEN, nothing is written" 0 \
    "$(ls -d analysis-t-depuis-fen* 2>/dev/null | wc -l)"
printf '[SetUp "1"]\n' > t-fen-initiale.pgn
printf '[FEN "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"]\n\n' >> t-fen-initiale.pgn
printf '1. e4 e5 *\n' >> t-fen-initiale.pgn
lancer t-fen-initiale.pgn $O
egal "T77 FEN of the initial position, accepted" 0 "$RC"
# Paths and sources badly recognized: tilde not expanded, address with
# an uppercase scheme, Lichess section or eight-letter directory taken
# for a game.
HOME="$TRAVAIL/maison" "$SCRIPT" italienne.pgn $O --venv "$VENV" \
    --settings "$REGL" --output-dir='~/analyses' > sortie 2> journal
egal "T77 tilde of --output-dir, exit code" 0 "$?"
verifier "T77 tilde of --output-dir expanded" \
    test -f "$TRAVAIL/maison/analyses/$(basename "$(head -n 1 sortie)")"
egal "T77 no directory named ~" 0 "$(ls -d ./~ 2>/dev/null | wc -l)"
mkdir -p abcdefgh
for source in abcdefgh 'HTTPS://lichess.org/Analysis' Features \
              https://lichess.org/insights; do
    lancer "$source" $O
    egal "T77 $source, exit code" 1 "$RC"
    egal "T77 $source, no download" 0 \
        "$(grep -c 'Downloading the PGN' journal)"
    cat journal >> journal-t77b
done
verifier "T77 directory named like an identifier" \
    contient journal-t77b "is a directory, not a PGN file"
verifier "T77 uppercase scheme recognized as a URL" \
    contient journal-t77b "URL not recognized"
cat journal > journal-t77
egal "T77 no unexpected error" 0 \
    "$(cat journal-t77 journal | grep -c 'Unexpected error')"

titre "T06, T08: folder kept, output directory"

rm -rf analysis-italienne-*
lancer italienne.pgn $O --keep-folder
egal "T06 exit code" 0 "$RC"
verifier "T06 the folder stays next to the archive" test -d "${ARCH%.zip}"
rm -rf analysis-italienne-*
lancer italienne.pgn $O --output-dir "$TRAVAIL/t-sortie/neuf"
egal "T08 exit code" 0 "$RC"
verifier "T08 output directory created if needed" \
    test -d "$TRAVAIL/t-sortie/neuf"
verifier "T08 archive written in this directory" test -f "$ARCH"
rm -rf analysis-italienne-*

titre "T81: combined purge, empty template, badly written token"
cp "$REGL" t-purge.ini
"$SCRIPT" --purge-settings --install-venv --venv "$VENV" \
    --settings t-purge.ini > sortie 2> journal
egal "T81 purge with another action, exit code" 2 "$?"
verifier "T81 purge with another action, message" \
    contient journal "--purge-settings is used alone"
verifier "T81 purge with another action, file intact" test -f t-purge.ini
lancer italienne.pgn $O --prompt ""
egal "T81 empty --prompt, exit code" 2 "$RC"
verifier "T81 empty --prompt, message" contient journal "--prompt: empty path"
# The token is a dummy one. The collections stop at its reading, before
# the catalog and before any request.
for contenu in 'LICHESS_TOKEN=lip_factice' '"lip_factice"' "'lip_factice'"; do
    printf '%s\n' "$contenu" > t-jeton-faux
    chmod 600 t-jeton-faux
    lancer italienne.pgn --no-questions --depth 1 \
        --token-file t-jeton-faux --catalog "$TRAVAIL/nulle-part"
    egal "T81 token written $contenu, exit code" 1 "$RC"
    verifier "T81 token written $contenu, refused" \
        contient journal "must contain the token alone"
    egal "T81 token written $contenu, not displayed" 0 \
        "$(grep -c 'lip_factice' journal)"
done

titre "T27: token file missing"

lancer italienne.pgn --no-questions --depth 1 \
    --token-file /nulle/part
egal "T27 exit code" 1 "$RC"
verifier "T27 message" contient journal "Token missing: /nulle/part"
egal "T27 no working folder created" 0 \
    "$(find . -maxdepth 1 -type d -name 'analysis-italienne-*' | wc -l)"

titre "T69: purge of the settings"

printf '[player]\nusernames = Alice\n' > t-purge.ini
mkdir -p t-rep
"$SCRIPT" --purge-settings --settings t-purge.ini > sortie 2> journal
egal "T69 file present, exit code" 0 "$?"
verifier "T69 deletion announced" \
    contient journal "Settings deleted: t-purge.ini"
verifier "T69 the file no longer exists" test ! -e t-purge.ini
egal "T69 standard output empty" 0 "$(wc -c < sortie)"
"$SCRIPT" --purge-settings --settings t-purge.ini > sortie 2> journal
egal "T69 file missing, exit code" 0 "$?"
verifier "T69 file missing, announced" \
    contient journal "No settings file to delete"
"$SCRIPT" --purge-settings --settings t-rep > sortie 2> journal
egal "T69 directory, exit code" 1 "$?"
verifier "T69 directory refused" contient journal "is not a file"
verifier "T69 the directory is still there" test -d t-rep
# A typo after --settings must not destroy another file: only a file
# carrying the [player] section, or an empty one, goes.
printf '[White "Alice"]\n\n1. e4 e5 *\n' > t-pas-reglages.pgn
"$SCRIPT" --purge-settings --settings t-pas-reglages.pgn > sortie 2> journal
egal "T69 other file, exit code" 1 "$?"
verifier "T69 other file refused" \
    contient journal "is not a settings file"
verifier "T69 the other file is still there" test -f t-pas-reglages.pgn
printf 'usernames = Alice\n[player\n[player]\n' > t-purge.ini
"$SCRIPT" --purge-settings --settings t-purge.ini > sortie 2> journal
egal "T69 damaged settings, deleted all the same" "0 0" \
    "$? $(find . -maxdepth 1 -name t-purge.ini | wc -l)"
: > t-purge.ini
"$SCRIPT" --purge-settings --settings t-purge.ini > sortie 2> journal
egal "T69 empty file, deleted" "0 0" \
    "$? $(find . -maxdepth 1 -name t-purge.ini | wc -l)"
joindre journal


titre "T71: removed options"

"$SCRIPT" italienne.pgn --sans-stockfish > sortie 2> journal
egal "T71 --sans-stockfish, exit code" 2 "$?"
verifier "T71 --sans-stockfish, unknown option" \
    contient journal "unrecognized arguments: --sans-stockfish"

"$SCRIPT" italienne.pgn --avec-stockfish > sortie 2> journal
egal "T71 exit code" 2 "$?"
verifier "T71 unknown option" \
    contient journal "unrecognized arguments: --avec-stockfish"
egal "T71 help silent about the option" 0 \
    "$("$SCRIPT" --help 2>/dev/null | grep -c -- --avec-stockfish)"

# --consignes, removed in its turn: the prompt carries the
# instructions, and the startup questions the context.
echo "Annotez en français." > t-consignes.md
"$SCRIPT" italienne.pgn --consignes t-consignes.md > sortie 2> journal
egal "T71 --consignes, exit code" 2 "$?"
verifier "T71 --consignes, unknown option" \
    contient journal "unrecognized arguments: --consignes"
egal "T71 --consignes, help silent" 0 \
    "$("$SCRIPT" --help 2>/dev/null | grep -c -- --consignes)"


# --- Engine -----------------------------------------------------------------

# List of the engine processes, on one line. It is taken before and
# after the engine tests: only a difference betrays a process left by
# the script. An engine already started by another program, a chess
# interface for example, thus no longer skews the check.
processus_moteur() {
    # By the name of the process, and not by its command line: pgrep -f
    # also caught any shell whose command quoted the path of the
    # engine, hence false failures.
    pgrep -x "$(basename "$STOCKFISH")" 2>/dev/null | sort | tr '\n' ' '
}

# The condition has always been true since the script stops at the
# start without an engine. It is kept so as not to reindent the whole
# block.
if [ -n "$STOCKFISH" ] && [ -x "$STOCKFISH" ]; then
    MOTEUR="--no-explorer --no-questions --stockfish $STOCKFISH"
    MOTEURS_AVANT=$(processus_moteur)
    noter ""
    noter "  note   engine processes already present: [${MOTEURS_AVANT}]"
    RAPIDE="--depth 8 --threads 2 --hash 32"

    titre "T51: missed mate and conceded mate"
    printf '1. f3 e5 2. g4 Nc6 *\n' > t-mat.pgn
    lancer t-mat.pgn $MOTEUR $RAPIDE
    egal "T51 exit code" 0 "$RC"
    extraire '*/summary.md'
    grep -E '^\| [34] \|' extrait > lignes 2>/dev/null
    egal "T51 lines 3 and 4 carry mat and gaffe" 2 \
        "$(grep -c '| mat | gaffe |' lignes)"
    # A mate is counted after the move of the line: 2. g4 leaves Black
    # a mate in one, "#-1", and the move that would give it, Qh4#, is "#-0".
    verifier "T51 Qh4# as first choice, mate given" \
        contient lignes "Qh4# (#-0)"
    egal "T51 after 2. g4, mate in one for Black" 1 \
        "$(grep -c -E '^\| 3 \|.*\| g4 \| #-1 \|' lignes)"
    verifier "T51 legend of the mates" contient extrait \
        "le compte se lit après le coup de la ligne"
    verifier "T51 sentence of explanation" contient extrait "Écart \`mat\`"
    verifier "T51 negative loss explained" contient extrait \
        "Négatif, il ne signale aucune faute"
    egal "T51 title of a game without a Site tag" 1 \
        "$(grep -c "^# Dossier d'analyse : partie locale" extrait)"
    egal "T51 without the explorer, its folder is not announced" 0 \
        "$(grep -c 'explorer/NNN' extrait)"
    # Loss between the first choice and the played move, computed apart:
    # two mates in the same direction do not give a loss of one centipawn.
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
    verifier "T51 losses: two mates, missed mate, negative loss" \
        cmp -s attendu-t51 sortie-t51
    joindre sortie-t51
    joindre journal-t51 5
    # The engine counts a mate before the move, that move included: the
    # mating side has one fewer to play once its move is played, the
    # mated side removes none. Without a side given, the engine count stays.
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
    verifier "T51 mates counted after the move, mating side and mated side" \
        cmp -s attendu-t51 sortie-t51
    joindre sortie-t51
    joindre journal-t51 5
    rm -rf "$DEPOT/__pycache__"
    joindre lignes
    joindre journal

    titre "T72: result contrary to the final evaluation"
    # White gives away their queen and the game is still scored 1-0: the
    # summary must say so. Scored 0-1, the same game is consistent.
    printf '[Result "1-0"]\n[Termination "Normal"]\n\n' > t-contre.pgn
    printf '1. e4 e5 2. Qh5 Nc6 3. Qxf7+ Kxf7 1-0\n' >> t-contre.pgn
    lancer t-contre.pgn $MOTEUR $RAPIDE
    egal "T72 exit code" 0 "$RC"
    extraire '*/summary.md'
    egal "T72 contradiction reported" 1 \
        "$(grep -c 'Résultat et évaluation finale se contredisent' extrait)"
    verifier "T72 declared winner and side really better" \
        contient extrait "victoire des Blancs, alors que Stockfish donne"
    verifier "T72 last move and Termination tag quoted" \
        contient extrait "3... Kxf7, soit un net avantage aux Noirs"
    verifier "T72 Termination tag quoted" \
        contient extrait 'La balise Termination vaut `Normal`.'
    PR="${ARCH%.zip}.prompt.txt"
    egal "T72 prompt: instruction to tell the player" 1 \
        "$(grep -c 'le résultat contredit' "$PR")"
    sed 's/1-0/0-1/g' t-contre.pgn > t-coherent.pgn
    lancer t-coherent.pgn $MOTEUR $RAPIDE
    egal "T72 consistent result, exit code" 0 "$RC"
    : > extrait
    extraire '*/summary.md'
    verifier "T72 consistent result, summary produced" \
        contient extrait "## 3. Évaluations Stockfish"
    egal "T72 consistent result, nothing is reported" 0 \
        "$(grep -c 'se contredisent' extrait)"

    # The symmetric case: Black gives away their queen, the game is
    # scored 0-1.
    printf '[Result "0-1"]\n\n1. e4 e5 2. Nf3 Qh4 3. Nxh4 0-1\n' > t-contre-noirs.pgn
    lancer t-contre-noirs.pgn $MOTEUR $RAPIDE
    egal "T72 win of Black contradicted, exit code" 0 "$RC"
    : > extrait
    extraire '*/summary.md'
    verifier "T72 win of Black contradicted, reported" contient extrait \
        "victoire des Noirs, alors que Stockfish donne"
    verifier "T72 win of Black contradicted, advantage to White" \
        contient extrait "3. Nxh4, soit un net avantage aux Blancs"

    titre "T52: null move"
    printf '1. e4 e5 2. -- Nc6 3. Nf3 *\n' > t-nul-coup.pgn
    lancer t-nul-coup.pgn $MOTEUR $RAPIDE
    egal "T52 exit code" 0 "$RC"
    extraire '*/summary.md'
    grep -E '^\| [34] \|' extrait > lignes 2>/dev/null
    verifier "T52 line of the null move without evaluation" \
        contient lignes "| 3 | 2 | Blancs | -- | - | - | - | - |"
    verifier "T52 mention in section 3 bis" \
        contient extrait "joué : coup nul, non évalué par le moteur"
    joindre lignes

    egal "T52 no repeated notice from python-chess" 0 \
        "$(grep -c 'Not transmitting' journal)"
    lancer t-nul-coup.pgn $MOTEUR $RAPIDE --prompt-only
    PR="$ARCH"
    verifier "T52 short prompt: the null move is explained" \
        contient "$PR" 'Un coup noté "--" est un coup nul'
    lancer italienne.pgn $MOTEUR --depth 4 --prompt-only
    PR="$ARCH"
    egal "T52 short prompt: nothing about the null move without a null move" 0 \
        "$(grep -c 'coup nul' "$PR")"
    verifier "T52 short prompt: each move played, without limit" \
        contient "$PR" "après chaque coup joué."

    titre "T25: engine limited to the first moves"
    lancer italienne.pgn $MOTEUR --stockfish-moves 3 --depth 10 \
        --multipv 2 --pv-length 4 --threads 2 --hash 128
    egal "T25 exit code" 0 "$RC"
    extraire '*/summary.md'
    verifier "T25 six plies covered out of nine" contient extrait \
        "profondeur 10, multipv 2, 6 demi-coups couverts sur 9"
    egal "T25 six lines in the table" 6 \
        "$(grep -c -E '^\| [1-9] \| [1-5] \| (Blancs|Noirs) \| [A-Za-z]' extrait)"
    PR="${ARCH%.zip}.prompt.txt"
    verifier "T25 prompt: partial coverage stated" contient "$PR" \
        "que les 6 premiers demi-coups sur 9"
    verifier "T25 prompt: two moves per position, not three" \
        contient "$PR" "meilleurs coups du moteur, 2 par position"
    lancer italienne.pgn $MOTEUR --stockfish-moves 3 --depth 4 \
        --prompt-only
    PR="$ARCH"
    verifier "T25 short prompt: partial coverage stated" contient "$PR" \
        "après chacun des 6 premiers demi-coups sur 9"
    egal "T25 short prompt: no more each move played" 0 \
        "$(grep -c 'après chaque coup joué' "$PR")"
    lancer italienne.pgn $MOTEUR --stockfish-moves 3 --depth 10 \
        --multipv 2 --pv-length 4 --threads 2 --hash 128
    extraire '*/collection.json'
    verifier "T25 threads in collection.json" contient extrait '"threads": 2'
    verifier "T25 hash in collection.json" contient extrait '"hash": 128'

    titre "T78: engine that stops outside a search"
    # Fake engine: it announces its options, then dies at the first
    # setting, like Stockfish when the memory of its hash table
    # is refused to it.
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
    lancer italienne.pgn --no-explorer --no-questions \
        --stockfish "$TRAVAIL/faux-moteur" --threads 2 --depth 4
    egal "T78 exit code" 1 "$RC"
    verifier "T78 message of the engine, not an unexpected error" \
        contient journal "The engine failed during the analysis"
    egal "T78 no unexpected error" 0 \
        "$(grep -c 'Unexpected error' journal)"
    joindre journal 6
    rm -rf analysis-italienne-*

    # The engine named by its bare name, or by a path with a tilde: the
    # check and the start now look for it at the same place.
    mkdir -p "$TRAVAIL/maison/bin"
    ln -sf "$STOCKFISH" "$TRAVAIL/maison/bin/moteur-essai"
    HOME="$TRAVAIL/maison" "$SCRIPT" italienne.pgn --no-explorer \
        --no-questions --depth 1 --venv "$VENV" --settings "$REGL" \
        --stockfish='~/bin/moteur-essai' > sortie 2> journal
    egal "T55 --stockfish with a tilde" 0 "$?"
    PATH="$TRAVAIL/maison/bin:$PATH" "$SCRIPT" italienne.pgn \
        --no-explorer --no-questions --depth 1 \
        --venv "$VENV" --settings "$REGL" --stockfish moteur-essai \
        > sortie 2> journal
    egal "T55 --stockfish by its name, looked up in the PATH" 0 "$?"
    rm -rf analysis-italienne-*

    titre "T55: engine options out of bounds"
    lancer italienne.pgn $MOTEUR --depth 61
    egal "T55 --depth 61, exit code" 2 "$RC"
    verifier "T55 --depth 61, message" \
        contient journal "--depth must not exceed 60"
    for option in "--threads 100000" "--hash 99999999999" "--multipv 9999"; do
            lancer italienne.pgn $MOTEUR $option
        egal "T55 $option, exit code" 1 "$RC"
        verifier "T55 $option, refused before the collection" \
            contient journal "is out of the bounds of the engine"
        tail -n 1 journal > ligne
        joindre ligne
    done
    egal "T55 no working folder created" 0 \
        "$(find . -maxdepth 1 -type d -name 'analysis-italienne-*' | wc -l)"

    titre "T70: test.pgn, the test game of the repository"
    if [ -f "$DEPOT/test.pgn" ]; then
        cp "$DEPOT/test.pgn" test.pgn
        lancer test.pgn $MOTEUR $RAPIDE --usernames "zoé blanche"
        egal "T70 exit code" 0 "$RC"
        egal "T70 no warning" 0 "$(grep -c 'Warning' journal)"
        extraire '*/game.pgn'
        verifier "T70 game.pgn identical to test.pgn" cmp -s extrait test.pgn
        extraire '*/summary.md'
        verifier "T70 thirty-six plies" contient extrait \
            "Nombre de demi-coups dans la ligne principale : 36."
        verifier "T70 accented tag" \
            contient extrait "| Black | Müller, Noël |"
        verifier "T70 TimeControl tag repeated" \
            contient extrait "| TimeControl | 600+5 |"
        verifier "T70 long castling by White" contient extrait \
            "Roque des Blancs : O-O-O au coup 14 (demi-coup 27)."
        verifier "T70 short castling by Black" contient extrait \
            "Roque des Noirs : O-O au coup 7 (demi-coup 14)."
        egal "T70 conceded mate then missed mate" 2 \
            "$(grep -c -E '^\| [34] \| 2 \|.*\| mat \| gaffe \|' extrait)"
        egal "T70 en passant capture" 1 \
            "$(grep -c -E '^\| 9 \| 5 \| Blancs \| gxf6 \|' extrait)"
        egal "T70 promotion with capture and check" 1 \
            "$(grep -c -E '^\| 17 \| 9 \| Blancs \| gxf8=Q\+ \|' extrait)"
        egal "T70 null move not evaluated" 1 \
            "$(grep -c -E '^\| 29 \| 15 \| Blancs \| -- \| - \| - \| - \| - \|' extrait)"
        egal "T70 thirty-six lines in the table" 36 \
            "$(grep -c -E '^\| [0-9]+ \| [0-9]+ \| (Blancs|Noirs) \| ' extrait)"
        PR="${ARCH%.zip}.prompt.txt"
        verifier "T70 prompt: side deduced despite the case" \
            contient "$PR" "- camp dans cette partie : Blancs"
        grep -E '^\| (3|4|9|17|29) \|' extrait | cut -c1-110 > lignes
        joindre lignes
    else
        sauter "T70: test.pgn missing from the repository"
    fi

    titre "T73: verifier-analyse.py, check of the PGN returned by an LLM"
    if [ -f "$DEPOT/test.pgn" ] && [ -f "$DEPOT/verifier-analyse.py" ]; then
        VERIF="$DEPOT/verifier-analyse.py"
        cp "$DEPOT/test.pgn" test.pgn
        lancer test.pgn $MOTEUR $RAPIDE
        # Two PGNs are built from the archive, as an LLM would do: a
        # compliant one, built with python-chess, and a faulty one, into
        # which the flaws found in real LLM PGNs are injected.
        ARCHIVE="$ARCH" "$PYVENV" - > sortie-t73 2> journal-t73 <<'EOF'
import io
import json
import os
import textwrap
import zipfile

import chess
import chess.pgn

with zipfile.ZipFile(os.environ["ARCHIVE"]) as z:
    nom = [n for n in z.namelist() if n.endswith("game.pgn")][0]
    racine = nom[:-len("game.pgn")]
    source = chess.pgn.read_game(io.StringIO(z.read(nom).decode("utf-8")))
    evals = json.loads(z.read(racine + "stockfish/evaluations.json"))

# The "invented" evaluations must really be missing from the engine
# data. A fixed figure does not guarantee it: +7.77 was once the real
# evaluation of a move, on a machine where the test game is played
# around +7, and the faulty PGN was no longer faulty on that point.
connues = {coup.get("score") for e in evals
           for coup in [e["played"]] + e["best"]}


def invente(centiemes):
    """
    First evaluation, from the value given in hundredths of a pawn, that
    the engine returned for no move of this collection.
    """
    while "+%d.%02d" % divmod(centiemes, 100) in connues:
        centiemes += 1
    return "+%d.%02d" % divmod(centiemes, 100)


INVENTE_PGN = invente(777)
INVENTE_CONVERSATION = invente(999)
# The figure chosen for the PGN is returned to the script: it is the
# one that the report must name.
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
        # Ply 4, a missed mate, is a blunder for any engine: the
        # faulty PGN forgets it.
        if e["category"] in ("erreur", "gaffe") and not (
                fautif and e["ply"] == 4):
            suivant.nags.add(chess.pgn.NAG_BLUNDER if e["category"] == "gaffe"
                             else chess.pgn.NAG_MISTAKE)
            meilleur = e["best"][0]
            texte = ("Il fallait %s, que le moteur donne à %s contre %s "
                     "pour le coup joué." % (meilleur["san"],
                                             meilleur["score"],
                                             e["played"]["score"]))
            if fautif and e["ply"] == 3:
                # Ply 3, a mate conceded: invented evaluation, percent,
                # variation written in the comment, illegal variation,
                # and NAG giving White as winning.
                texte += (" Chiffre inventé : %s, soit 50 %% de gain. (%s)"
                          " (2. Ke3 Nc6)"
                          % (INVENTE_PGN,
                             " ".join(meilleur["pv_san"].split()[:4])))
                suivant.nags.add(18)
            suivant.comment = textwrap.fill(texte, 75)
            # Variation taken from the engine line, four plies.
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
        # Flaws of someone who writes the PGN by hand: blank line after the
        # summary, suffix notation, wrong end marker.
        texte = texte.replace("\n1. f3", "\n\n1. f3", 1)
        texte = texte.replace("2. g4 $4", "2. g4??", 1)
        fin = source.headers["Result"]
        texte = texte[:texte.rindex(fin)] + "1-0\n"
    return texte


open("t-conforme.pgn", "w", encoding="utf-8").write(construire(False))
# Three flaws that the compliant PGN does not carry, one per file, so
# that each one is reported alone: they change neither the moves nor
# their number, and thus went unnoticed.
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
# What an LLM returns from the short prompt of --prompt-only: the
# tags and the moves copied, a comment on each mistake or
# blunder, on a single line, without a summary, without NAGs,
# without added tags.
court = chess.pgn.Game()
for b in ("Event", "Site", "Date", "Round", "White", "Black", "Result"):
    court.headers[b] = source.headers[b]
noeud = court
for e, coup in zip(evals, source.mainline_moves()):
    noeud = noeud.add_main_variation(coup)
    if e["category"] in ("erreur", "gaffe"):
        noeud.comment = ("Ici tu devais jouer %s, bien meilleur d'après "
                         "le tableau : prends le temps de chercher ce coup "
                         "avant de pousser un pion." % e["best"][0]["san"])
open("t-court.pgn", "w", encoding="utf-8").write(
    court.accept(chess.pgn.StringExporter(columns=None)) + "\n")
open("t-conversation.txt", "w", encoding="utf-8").write(
    "Position 1 : %s\n"
    "Position 2 : 8/8/8/8/8/8/8/8 w - - 0 1\n"
    "Evaluation %s sortie de nulle part \u2014 avec un tiret cadratin.\n"
    % (evals[2]["fen"], INVENTE_CONVERSATION))
EOF
        "$PYVENV" "$VERIF" "$ARCH" t-conforme.pgn > bilan 2>&1
        egal "T73 compliant PGN, exit code" 0 "$?"
        egal "T73 compliant PGN, no failure" 0 "$(grep -c '^  ECHEC' bilan)"
        verifier "T73 compliant PGN, variations backed by the engine" \
            contient bilan "0 sont du cru du LLM"
        "$PYVENV" "$VERIF" "$ARCH" t-fautif.pgn --name "essai fautif" \
            --summary t-conversation.txt > bilan 2>&1
        egal "T73 faulty PGN, exit code" 1 "$?"
        # Each line gives the injected flaw, then what the report says of it.
        while IFS='|' read -r defaut constat; do
            verifier "T73 flaw reported: $defaut" \
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
        verifier "T73 variation written in a comment" \
            contient bilan "écrite(s) à l'intérieur d'un commentaire"
        verifier "T73 illegal move named" contient bilan "Ke3 est illégal"
        # The two invented evaluations, the one of the PGN and the one of the
        # conversation, give the same sentence in the report: each one is
        # looked for in its section, otherwise one passed for the other.
        sed -n '/^=== 5\. /,/^=== 6\. /p' bilan > section5
        sed -n '/^=== 8\. /,/^=== Bilan/p' bilan > section8
        INVENTE=$(cat t-invente-pgn 2>/dev/null)
        verifier "T73 flaw reported: evaluation invented in the PGN" \
            grep -q -E '^  ECHEC .*\(1 introuvable' section5
        verifier "T73 invented figure named" \
            contient section5 ": ${INVENTE:-chiffre non rendu}"
        verifier "T73 flaw reported: evaluation invented in the conversation" \
            grep -q -E '^  ECHEC .*\(1 introuvable' section8
        grep -E '^  (ECHEC|ATTENTION)' bilan | cut -c1-110 > lignes
        joindre lignes 20
        # Flaws that do not change the moves read: each one must be
        # reported on its own, on a PGN otherwise compliant.
        while IFS='|' read -r fichier constat; do
            "$PYVENV" "$VERIF" "$ARCH" "$fichier" > bilan 2>&1
            egal "T73 $fichier, exit code" 1 "$?"
            egal "T73 $fichier, a single failure" 1 "$(grep -c '^  ECHEC' bilan)"
            verifier "T73 $fichier, flaw named" \
                grep -q -E "^  ECHEC .*$constat" bilan
        done <<'FIN'
t-vide-fin.pgn|ligne vide dans le corps de la partie
t-fermante.pgn|aucune accolade dans un commentaire
t-balises.pgn|les sept balises obligatoires, dans l'ordre
FIN
        # A PGN compliant with the short prompt has neither a summary nor
        # lines of 79 characters: with --prompt-only it passes, without the
        # option it fails on these two points, which come from the full prompt.
        "$PYVENV" "$VERIF" "$ARCH" t-court.pgn --prompt-only > bilan 2>&1
        egal "T73 --prompt-only, exit code" 0 "$?"
        egal "T73 --prompt-only, no failure" 0 "$(grep -c '^  ECHEC' bilan)"
        verifier "T73 --prompt-only, said at the top of the report" \
            contient bilan "prompt  : court"
        "$PYVENV" "$VERIF" "$ARCH" t-court.pgn > bilan 2>&1
        egal "T73 the same without the option, exit code" 1 "$?"
        egal "T73 the same without the option, two failures" 2 \
            "$(grep -c '^  ECHEC' bilan)"
        "$PYVENV" "$VERIF" "$ARCH" - --summary t-conversation.txt \
            > bilan 2>&1
        egal "T73 no PGN returned, exit code" 1 "$?"
        verifier "T73 no PGN returned, said in the report" \
            contient bilan "aucun PGN rendu"
        # Quoted evaluations: the check is called alone, on a folder
        # with a single evaluation, +0.35, whose rounding goes wrong in
        # floating point. Each line gives the quoted text and the
        # number of failures expected.
        VERIF="$VERIF" "$PYVENV" - > sortie-t73c 2> journal-t73c <<'EOF'
import importlib.util
import os

spec = importlib.util.spec_from_file_location("va", os.environ["VERIF"])
va = importlib.util.module_from_spec(spec)
spec.loader.exec_module(va)
dossier = [{"played": {"score": "+0.35"}, "best": [{"score": "-1.25"}]}]
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
        verifier "T73 evaluations: roundings accepted, invented figures reported" \
            cmp -s attendu-t73c sortie-t73c
        joindre sortie-t73c 12
        joindre journal-t73c 5
        rm -rf "$DEPOT/__pycache__"
        "$PYVENV" "$VERIF" /nulle/part.zip t-conforme.pgn > bilan 2>&1
        egal "T73 unreadable archive, exit code" 2 "$?"
        # A PGN coming from Windows, with lines of 79 characters ending
        # with CRLF, stays compliant.
        awk '{ printf "%s\r\n", $0 }' t-conforme.pgn > t-crlf.pgn
        "$PYVENV" "$VERIF" "$ARCH" t-crlf.pgn > bilan 2>&1
        egal "T73 CRLF line ends, exit code" 0 "$?"
        # A PGN that python-chess cannot read gives a report, and a
        # damaged archive the code 2: never a Python traceback.
        printf '1. e5 ) 1. e4 *\n' > t-illisible.pgn
        "$PYVENV" "$VERIF" "$ARCH" t-illisible.pgn > bilan 2>&1
        egal "T73 unreadable PGN, exit code" 1 "$?"
        verifier "T73 unreadable PGN, said in the report" \
            contient bilan "aucune partie lisible"
        printf '1. e4 ( 1. e5 ) 1... e4 *\n' > t-variante-folle.pgn
        "$PYVENV" "$VERIF" "$ARCH" t-variante-folle.pgn > bilan2 2>&1
        egal "T73 illegal variation at the start, exit code" 1 "$?"
        cat bilan2 >> bilan
        mkdir -p t-abimee/stockfish
        unzip -p "$ARCH" '*/game.pgn' > t-abimee/game.pgn
        unzip -p "$ARCH" '*/summary.md' > t-abimee/summary.md
        "$PYVENV" "$VERIF" t-abimee t-conforme.pgn >> bilan 2>&1
        egal "T73 incomplete archive, exit code" 2 "$?"
        printf '{pas du JSON' > t-abimee/stockfish/evaluations.json
        "$PYVENV" "$VERIF" t-abimee t-conforme.pgn >> bilan 2>&1
        egal "T73 unreadable evaluations, exit code" 2 "$?"
        printf '{"autre": "forme"}' > t-abimee/stockfish/evaluations.json
        "$PYVENV" "$VERIF" t-abimee t-conforme.pgn >> bilan 2>&1
        egal "T73 evaluations of another form, exit code" 2 "$?"
        egal "T73 no Python traceback in these cases" 0 \
            "$(grep -c 'Traceback' bilan)"
    else
        sauter "T73: test.pgn or verifier-analyse.py missing from the repository"
    fi

    titre "T82: checker, mates, scope, short mode, parent folder"
    if [ -f "$DEPOT/verifier-analyse.py" ]; then
        VERIF="$DEPOT/verifier-analyse.py"
        # Légal's mate: 5... Bxd1 concedes a mate, which 7. Nd5# gives.
        printf '[White "Alice"]\n[Black "Bob"]\n[Result "1-0"]\n\n' > t-legal.pgn
        printf '1. e4 e5 2. Nf3 d6 3. Bc4 Bg4 4. Nc3 g6 5. Nxe5 Bxd1 ' \
            >> t-legal.pgn
        printf '6. Bxf7+ Ke7 7. Nd5# 1-0\n' >> t-legal.pgn
        mkdir -p t-parent
        lancer t-legal.pgn $MOTEUR $RAPIDE --keep-folder --output-dir t-parent
        egal "T82 exit code" 0 "$RC"
        DOSSIER82="${ARCH%.zip}"
        egal "T82 table: the mate is counted after the move" "1 1 1" \
            "$(grep -c -E '\| Bxf7\+ \| #\+1 \|' "$DOSSIER82/summary.md") $(grep -c -E '\| Ke7 \| #\+1 \|' "$DOSSIER82/summary.md") $(grep -c -E '\| Nd5# \| #\+0 \|' "$DOSSIER82/summary.md")"
        # Three returned PGNs: quoted mates, comments limited to the
        # first four moves, a NAG contrary to the engine.
        PARTIE="$DOSSIER82/game.pgn" "$PYVENV" - 2> journal-t82 <<'EOF'
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
        # A mate by White is written "#+1" in the folder: quoted as it
        # is or without a sign, it is recognized, and an invented mate is
        # reported.
        "$PYVENV" "$VERIF" "$ARCH" t-82-mats.pgn --prompt-only > bilan 2>&1
        sed -n '/^=== 5\. /,/^=== 6\. /p' bilan > section5
        verifier "T82 quoted mates: three evaluations read" \
            contient section5 "3 évaluation(s) citée(s)"
        verifier "T82 quoted mates: the invented mate is the only one reported" \
            contient section5 "(1 introuvable(s))"
        verifier "T82 quoted mates: invented mate named" contient section5 "#+7"
        # The agreed scope bounds the check: the blunder of move 5
        # is not expected from a PGN limited to the first four moves.
        "$PYVENV" "$VERIF" "$ARCH" t-82-quatre.pgn --prompt-only > bilan 2>&1
        # The number of mistakes found after move 4 varies with the
        # engine: only the failure of the check counts.
        egal "T82 without a scope, the blunder of move 5 is expected" "1 0" \
            "$(grep -c 'ECHEC     les .* sont toutes commentées' bilan) $(grep -c '(0 oubliée(s))' bilan)"
        "$PYVENV" "$VERIF" "$ARCH" t-82-quatre.pgn --prompt-only \
            --scope 4 > bilan 2>&1
        egal "T82 --scope 4, exit code" 0 "$?"
        verifier "T82 --scope 4, said in the report" \
            contient bilan "périmètre convenu : les 4 premiers coups"
        verifier "T82 --scope 4, nothing forgotten any more" \
            contient bilan "(0 oubliée(s))"
        "$PYVENV" "$VERIF" "$ARCH" t-82-quatre.pgn --scope 0 \
            > bilan 2>&1
        egal "T82 --scope 0 refused" 2 "$?"
        # The scope given to the script is read in the instructions of
        # the summary: a number there means a number of moves.
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
        verifier "T82 scope read in the instructions of the summary" \
            cmp -s attendu-t82 sortie-t82
        joindre sortie-t82
        joindre journal-t82 5
        rm -rf "$DEPOT/__pycache__"
        # Short mode: neither NAG, nor em dash, nor number of FEN, which the
        # short prompt does not ask for. Without the option, they are reported.
        printf 'Synth\303\250se \342\200\224 sans position.\n' > t-82-conv.txt
        "$PYVENV" "$VERIF" "$ARCH" t-82-nag.pgn --prompt-only \
            --summary t-82-conv.txt > bilan 2>&1
        egal "T82 short mode, exit code" 0 "$?"
        egal "T82 short mode, NAG, em dash and FEN not checked" \
            "0 0 0" \
            "$(grep -c 'NAG de position' bilan) $(grep -c 'tiret cadratin' bilan) $(grep -c 'deux demandées' bilan)"
        "$PYVENV" "$VERIF" "$ARCH" t-82-nag.pgn \
            --summary t-82-conv.txt > bilan 2>&1
        egal "T82 full mode, the three are reported" "1 1 1" \
            "$(grep -c 'ECHEC     aucun NAG de position' bilan) $(grep -c 'ECHEC     aucun tiret cadratin dans la conversation' bilan) $(grep -c 'ATTENTION 0 FEN' bilan)"
        # Parent folder: the only complete collection is taken and named,
        # an interrupted collection beside it does not get mixed in, and two
        # complete collections are refused rather than chosen.
        mkdir -p t-parent/analysis-aaa-interrompue
        cp "$DOSSIER82/game.pgn" t-parent/analysis-aaa-interrompue/
        printf '1. d4 d5 *\n' > t-parent/analysis-aaa-interrompue/game.pgn
        "$PYVENV" "$VERIF" t-parent t-82-mats.pgn --prompt-only > bilan 2>&1
        verifier "T82 parent folder, complete collection named" \
            contient bilan "collecte: $(basename "$DOSSIER82")"
        verifier "T82 parent folder, the right game is read" \
            contient bilan "OK        ligne principale identique"
        cp -R "$DOSSIER82" t-parent/analysis-zzz-seconde
        "$PYVENV" "$VERIF" t-parent t-82-mats.pgn --prompt-only > bilan 2>&1
        egal "T82 two complete collections, exit code" 2 "$?"
        verifier "T82 two complete collections, named" \
            contient bilan "contient 2 collectes complètes"
        joindre bilan
        rm -rf t-parent
    else
        sauter "T82: verifier-analyse.py missing from the repository"
    fi

    titre "T83: example games of the repository"
    # EXEMPLES.md runs its commands on the files of parties-exemples:
    # each one must stay what the page says of it, accepted or refused
    # with its cause. The collections are done in the test directory.
    EX="$DEPOT/parties-exemples"
    if [ -d "$EX" ]; then
        for partie in ma-partie polonaise partie-lichess-org partie-commentee \
            partie-chess-com partie-chess-mail partie-ajedrezmail \
            partie-lucas-chess; do
            lancer "$EX/$partie.pgn" $MOTEUR --depth 1 --threads 1 \
                --hash 16
            egal "T83 $partie.pgn, collection done" "0 1" \
                "$RC $(find . -maxdepth 1 -name "analysis-$partie-*.zip" | wc -l)"
            # The log of the chess-mail.com export is kept: it must
            # say that the repeated result was ignored.
            [ "$partie" = partie-chess-mail ] && cp journal t-83-journal
        done
        while IFS='|' read -r partie cause; do
            lancer "$EX/$partie.pgn" $MOTEUR --depth 1
            egal "T83 $partie.pgn, exit code" 1 "$RC"
            verifier "T83 $partie.pgn, refused with its cause" \
                contient journal "$cause"
        done <<'FIN'
francais|is neither a move in English notation
deux-parties|The PGN contains 2 games
position|does not start from the initial position
accolade|brace
FIN
        # The annotated PGNs of the page go through the checker, on
        # the archive of ma-partie.pgn: the first one without a failure,
        # the second one with.
        lancer "$EX/ma-partie.pgn" $MOTEUR --depth 1 --threads 1 \
            --hash 16
        "$PYVENV" "$DEPOT/verifier-analyse.py" "$ARCH" "$EX/analyse-llm.pgn" \
            > bilan 2>&1
        verifier "T83 analyse-llm.pgn, report produced" \
            contient bilan "=== Bilan ==="
        "$PYVENV" "$DEPOT/verifier-analyse.py" "$ARCH" \
            "$EX/analyse-fautive.pgn" > bilan 2>&1
        egal "T83 analyse-fautive.pgn, failures" 1 "$?"
        verifier "T83 export of chess-mail.com, repeated result ignored" \
            contient t-83-journal "Result repeated at the end of the file"
        egal "T83 no real game: neither address nor identifier" 0 \
            "$(cat "$EX"/* | grep -c -i 'lichess.org/\|GameId')"
        rm -rf "$DEPOT/__pycache__"
    else
        sauter "T83: parties-exemples missing from the repository"
    fi

    titre "M2: full analysis of the Italian, engine only"
    lancer italienne.pgn $MOTEUR --depth 10 --threads 2 --hash 64
    egal "M2 exit code" 0 "$RC"
    extraire '*/summary.md'
    egal "M2 nine lines in the Stockfish table" 9 \
        "$(grep -c -E '^\| [1-9] \| [1-5] \| (Blancs|Noirs) \| [A-Za-z]' extrait)"
    grep -E '^Moteur' extrait | cut -c1-110 > ligne
    joindre ligne
    # One second of delay: the engine has just received "quit".
    sleep 1
    PR="${ARCH%.zip}.prompt.txt"
    egal "M2 prompt: the engine figures are authoritative" 1 \
        "$(grep -c 'Les chiffres de la section 3 font foi' "$PR")"
    egal "M2 prompt: Stockfish useless to the analyst" 1 \
        "$(grep -c 'Stockfish est inutile' "$PR")"
    egal "M2 prompt: the mention mat is explained" 1 \
        "$(grep -c 'porte .mat. quand le coup' "$PR")"
    egal "M2 no engine process left by the tests" \
        "[$MOTEURS_AVANT]" "[$(processus_moteur)]"
fi

# ===========================================================================
# Tests with the network and the token, only with --network
# ===========================================================================

if [ "$RESEAU" = 1 ]; then

CAT="$TRAVAIL/catalogue"
# Options common to all the collections of this part: no
# question. Collection of the explorer alone, without the engine, for
# EXPL.
BASE="--no-questions"
EXPL="$BASE --depth 1"

# collecter options...: runs a collection with the temporary catalog
# and your token. Standard output in "sortie", log in "journal", exit
# code in RC, path of the archive in ARCH. The summary is extracted
# into "synthese", its section 2 into "section2" and the lines of the
# explorer table into "table".
collecter() {
    "$SCRIPT" "$@" --catalog "$CAT" --token-file "$JETON" \
        --venv "$VENV" --settings "$REGL" > sortie 2> journal
    RC=$?
    ARCH=$(head -n 1 sortie)
    : > synthese
    : > section2
    : > table
    if [ -n "$ARCH" ] && [ -f "$ARCH" ]; then
        unzip -p "$ARCH" '*/summary.md' > synthese 2>/dev/null
        awk '/^## 2\./ {dedans = 1} /^## 3\./ {dedans = 0} dedans' \
            synthese > section2
        grep -E '^\| [0-9]+ \|' section2 > table 2>/dev/null
    fi
}

# Checks common to every collection: it succeeds, without an
# unexpected error, and the explorer did not refuse the token.
sain() {
    egal "$1 exit code" 0 "$RC"
    egal "$1 no unexpected error" 0 "$(grep -c 'Unexpected error' journal)"
    if grep -q 'HTTP 401' journal; then
        NB_ECHEC=$((NB_ECHEC + 1))
        noter "  FAIL   $1: HTTP 401, the explorer refuses the token"
        printf '    FAIL: %s, HTTP 401, token refused\n' "$1" >&2
    fi
}


# Does the file contain the token? The token serves as a pattern file
# for grep: it is neither read by the shell nor displayed, only a count
# comes out.
compte_jeton() {
    grep -a -c -F -f "$JETON" "$1" 2>/dev/null
}

# --- Test games -------------------------------------------------------------

# An Italian line fully cataloged, the one of the offline tests.
printf '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 *\n' > italienne.pgn
# The Polish followed by g6, a rare move outside the catalog. It is
# short, to bound the number of requests.
printf '1. b4 g6 2. Bb2 Nf6 3. e3 Bg7 4. Nf3 O-O *\n' > polonaise.pgn
# An Italian where both sides castle, for T33.
printf '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6 6. O-O O-O *\n' \
    > roques.pgn
# A null move on the third ply.
printf '1. e4 e5 2. -- Nc6 *\n' > nul.pgn

# --- Virtual environment -------------------------------------------------

titre "T84: virtual environment without pip, rebuilt"
# The venv without pip of the offline part: --install-venv rebuilds
# it, then installs python-chess from PyPI.
rm -rf "$TRAVAIL/t84-sans-pip"
"$PYVENV" -m venv --without-pip "$TRAVAIL/t84-sans-pip"
"$SCRIPT" --install-venv --venv "$TRAVAIL/t84-sans-pip" > sortie 2> journal
egal "T84 rebuild, exit code" 0 $?
verifier "T84 rebuild announced" contient journal "rebuilding it"
verifier "T84 python-chess installed after the rebuild" \
    "$TRAVAIL/t84-sans-pip/bin/python3" -c "import chess"
joindre journal 5

# --- Catalog -------------------------------------------------------------

titre "T09, T10: installation of the catalog"
"$SCRIPT" --install-catalog --catalog "$CAT" --venv "$VENV" \
    > sortie 2> journal
egal "T09 exit code" 0 $?
egal "T09 five files downloaded" 5 \
    "$(grep -c 'Downloading the catalog' journal)"
verifier "T09 message Catalog installed" contient journal "Catalog installed:"
grep 'Catalog installed' journal > ligne 2>/dev/null
joindre ligne
if [ ! -f "$CAT/catalog.tsv" ]; then
    noter "  FAIL   catalog missing, the following tests make no sense"
    printf 'Catalog not installed, stopping. See the log below.\n' >&2
    cat journal >&2
    exit 1
fi
head -n 1 "$CAT/catalog.tsv" | tr '\t' ' ' > ligne
verifier "T10 first line: format 2" contient ligne "#format=2 date="
joindre ligne
egal "T10 no leftover temporary file" 0 \
    "$(find "$CAT" -name '.catalog-*' | wc -l)"

titre "T11: identical reinstallation"
tail -n +2 "$CAT/catalog.tsv" > cat1.tsv
"$SCRIPT" --install-catalog --catalog "$CAT" --venv "$VENV" \
    > sortie 2> journal
egal "T11 exit code" 0 $?
tail -n +2 "$CAT/catalog.tsv" > cat2.tsv
verifier "T11 identical content except the dated line" cmp -s cat1.tsv cat2.tsv

titre "T12, T13: catalog missing, catalog truncated"
"$SCRIPT" italienne.pgn $EXPL --catalog "$TRAVAIL/vide" \
    --token-file "$JETON" --venv "$VENV" --settings "$REGL" \
    > sortie 2> journal
egal "T12 exit code" 1 $?
verifier "T12 missing catalog reported" \
    contient journal "Opening catalog missing"
mkdir abime
head -n $(($(lignes "$CAT/catalog.tsv") - 10)) "$CAT/catalog.tsv" \
    > abime/catalog.tsv
"$SCRIPT" italienne.pgn $EXPL --catalog "$TRAVAIL/abime" \
    --token-file "$JETON" --venv "$VENV" --settings "$REGL" \
    > sortie 2> journal
egal "T13 exit code" 1 $?
verifier "T13 truncated catalog reported" contient journal "Truncated catalog:"
grep 'Truncated catalog' journal > ligne 2>/dev/null
joindre ligne

# --- Token, without a request --------------------------------------------

titre "T28: token file readable by others"
# A dummy token: your real token is not copied. The missing catalog
# stops the script right after the token is read, without network.
printf 'lip_factice\n' > faux-jeton
chmod 644 faux-jeton
"$SCRIPT" italienne.pgn $EXPL --catalog "$TRAVAIL/vide" \
    --token-file faux-jeton --venv "$VENV" --settings "$REGL" \
    > sortie 2> journal
verifier "T28 warning about mode 644" \
    contient journal "is readable by others (mode 644)"

# --- Masters database ----------------------------------------------------

titre "T14: Italian, masters database"
collecter italienne.pgn $EXPL --database masters
sain "T14"
verifier "T14 log: masters database" contient journal "Explorer: database maîtres"
egal "T14 nine lines in the table" 9 "$(lignes table)"
verifier "T14 line 1: B00 King's Pawn Game" \
    contient table "| B00 King's Pawn Game |"
verifier "T14 line 5: C50 Italian Game" contient table "| C50 Italian Game |"
verifier "T14 line 9: Giuoco Pianissimo" \
    contient table "Giuoco Pianissimo |"
verifier "T14 stop at the end of the game" \
    contient section2 "Arrêt de l'interrogation : fin de la partie."
verifier "T14 no exit from theory" \
    contient section2 "Aucun coup interrogé ne passe sous le seuil de 10.0 % hors catalogue."
joindre table

titre "T15: Polish, masters database"
collecter polonaise.pgn $EXPL --database masters
sain "T15"
head -n 1 table > ligne
verifier "T15 line 1: b4" contient ligne "| b4 |"
verifier "T15 line 1: A00 Polish Opening" contient ligne "| A00 Polish Opening |"
joindre table
grep 'Arrêt de l' section2 > ligne 2>/dev/null
joindre ligne

# --- Lichess database ----------------------------------------------------

titre "T16: Polish, Lichess database"
collecter polonaise.pgn $EXPL --database lichess
sain "T16"
head -n 1 table > ligne
verifier "T16 line 1: A00 Polish Opening" contient ligne "| A00 Polish Opening |"
verifier "T16 Lichess database announced" contient section2 "Base interrogée : **Lichess**"
verifier "T16 starting window announced" contient section2 "Fenêtre de départ"
verifier "T16 first exit: g6" contient section2 "**Noirs joue g6**"
verifier "T16 last named position: Polish" \
    contient section2 "dernière position nommée avant la sortie : A00 Polish Opening"
joindre table
grep -E 'Arrêt de l|Premier coup sous|fréquence du coup' section2 > ligne 2>/dev/null
joindre ligne

titre "T17: stop at the first exit"
collecter polonaise.pgn $EXPL --database lichess --min-moves 0
sain "T17"
egal "T17 two lines in the table" 2 "$(lignes table)"
verifier "T17 stop on the exit from theory" \
    contient section2 "sortie de théorie au demi-coup 2 : g6 joué à"
grep 'Arrêt de l' section2 > ligne 2>/dev/null
joindre ligne

titre "T18: speed and rating filters"
collecter polonaise.pgn $EXPL --database lichess --min-moves 0 \
    --speeds ' Rapid,CLASSICAL,rapid' --ratings 1000,0
sain "T18"
unzip -p "$ARCH" '*/collection.json' > json 2>/dev/null
verifier "T18 speeds normalized" contient json '"speeds": "rapid,classical"'
verifier "T18 ratings normalized" contient json '"ratings": "0,1000"'
verifier "T18 filters repeated in the summary" \
    contient section2 'Cadences : `rapid,classical`'
head -n 1 table > ligne
joindre ligne

# --- Thresholds and modes ------------------------------------------------

titre "T19: unreachable game threshold"
collecter italienne.pgn $EXPL --database lichess --min-games 100000000000
sain "T19"
verifier "T19 sample too small at ply 1" \
    contient section2 "échantillon insuffisant au demi-coup 1"
verifier "T19 section 4 filled in" \
    contient synthese "ne dit plus rien d'exploitable"

titre "T20: frequency threshold at zero"
collecter polonaise.pgn $EXPL --database lichess --min-moves 0 --min-frequency 0
sain "T20"
verifier "T20 no exit below 0.0 %" \
    contient section2 "Aucun coup interrogé ne passe sous le seuil de 0.0 %"
grep 'Arrêt de l' section2 > ligne 2>/dev/null
joindre ligne

titre "T21: until exhaustion"
collecter polonaise.pgn $EXPL --database lichess --exhaustive
sain "T21"
verifier "T21 mode announced" contient section2 'Mode `--exhaustive`'
verifier "T21 first exit still g6" contient section2 "**Noirs joue g6**"
noter "  note   lines in the table: $(lignes table)"
grep 'Arrêt de l' section2 > ligne 2>/dev/null
joindre ligne

titre "T22: ply cap"
collecter italienne.pgn $EXPL --exhaustive --max-plies 4
sain "T22"
egal "T22 four lines in the table" 4 "$(lignes table)"
verifier "T22 cap reached" \
    contient section2 "plafond de 4 demi-coups atteint (option --max-plies)"

titre "T23: pause between two requests"
collecter italienne.pgn $EXPL --pause 3 --max-plies 3
sain "T23"
# Gap, in seconds, between the timestamps of plies 2 and 3: the first
# request goes without waiting, the pause separates the next ones.
ECART=$(grep -E 'Explorer: ply [23] ' journal \
    | sed 's/^\[\([0-9]*\):\([0-9]*\):\([0-9]*\)\].*/\1 \2 \3/' \
    | awk 'NR == 1 {a = $1 * 3600 + $2 * 60 + $3}
           NR == 2 {b = $1 * 3600 + $2 * 60 + $3}
           END {print b - a}')
noter "  note   gap measured between plies 2 and 3: ${ECART} s"
if [ "${ECART:-0}" -ge 3 ] 2>/dev/null; then
    egal "T23 at least 3 seconds between two requests" oui oui
else
    egal "T23 at least 3 seconds between two requests" oui non
fi
grep 'Explorer: ply' journal > ligne 2>/dev/null
joindre ligne

# --- Castling ------------------------------------------------------------

titre "T33: castling found in the database"
collecter roques.pgn $EXPL --database lichess
sain "T33"
grep -E '\| O-O \|' table > roques 2>/dev/null
egal "T33 two castling moves in the table" 2 "$(lignes roques)"
# A castling move not found came out at rank "-", at 0.0 %.
egal "T33 no castling at rank hors base" 0 \
    "$(grep -c -E '\| O-O \| - \|' roques)"
egal "T33 no castling at 0.0 %" 0 "$(grep -c -E '\| O-O \| [0-9-]+ \| 0\.0 %' roques)"
joindre roques
noter "  note   lines in the table: $(lignes table)"
grep 'Arrêt de l' section2 > ligne 2>/dev/null
joindre ligne

# --- Token in the archive ------------------------------------------------

titre "T29: the token is not in the archive"
unzip -p "$ARCH" > contenu 2>/dev/null
egal "T29 token absent from the archive of T33" 0 "$(compte_jeton contenu)"
egal "T29 token absent from the log of T33" 0 "$(compte_jeton journal)"
unzip -p "$ARCH" '*/collection.json' > json 2>/dev/null
verifier "T29 collection.json only records its presence" \
    contient json '"token_present": true'

# --- Lichess source ------------------------------------------------------

titre "T24: game downloaded from Lichess"
if [ -n "$ID_PARTIE" ]; then
    "$SCRIPT" "https://lichess.org/$ID_PARTIE" $EXPL --no-explorer \
        --venv "$VENV" --settings "$REGL" > sortie 2> journal
    egal "T24 by URL, exit code" 0 $?
    verifier "T24 by URL, export requested" \
        contient journal "https://lichess.org/game/export/$ID_PARTIE"
    ARCH=$(head -n 1 sortie)
    case $ARCH in
        analysis-"$ID_PARTIE"-*.zip) NOM_OK=oui ;;
        *) NOM_OK=non ;;
    esac
    egal "T24 by URL, name of the archive" oui "$NOM_OK"
    "$SCRIPT" "$ID_PARTIE" $EXPL --no-explorer --venv "$VENV" \
        --settings "$REGL" > sortie 2> journal
    egal "T24 by identifier, exit code" 0 $?
else
    sauter "T24: no game given. To play it: sh test-app.sh --network <identifier or address of a Lichess game>"
fi

# --- Null move and full collection -----------------------------------------------------------

titre "N1: null move, on the real explorer"
# Since version 3.5.9, the collection stops at the null move, without
# asking anything for that ply: before, Lichess refused with an HTTP
# 400 the move list carrying 0000.
collecter nul.pgn $EXPL --database lichess --exhaustive
sain "N1"
egal "N1 two lines in the table" 2 "$(lignes table)"
verifier "N1 stop on the null move" \
    contient section2 "Arrêt de l'interrogation : coup nul au demi-coup 3"
egal "N1 no request refused" 0 "$(grep -c 'HTTP 400' journal)"
verifier "N1 section 4: null move, not queried" \
    contient synthese "coup nul, non interrogé"
grep 'Explorer:' journal > ligne 2>/dev/null
joindre ligne
joindre table

if [ -n "$STOCKFISH" ] && [ -x "$STOCKFISH" ]; then
    titre "N2: full collection, explorer and engine"
    collecter roques.pgn $BASE --stockfish "$STOCKFISH" --depth 12 \
        --threads 2 --hash 64
    sain "N2"
    unzip -l "$ARCH" > liste 2>/dev/null
    verifier "N2 answers of the explorer in the archive" \
        contient liste "/explorer/001-e2e4.json"
    verifier "N2 evaluations of the engine in the archive" \
        contient liste "/stockfish/evaluations.json"
    awk '/^## 3\./ {dedans = 1} /^### 3 bis/ {dedans = 0} dedans' synthese \
        | grep -E '^\| [0-9]+ \|' > table3
    egal "N2 twelve lines in the engine table" 12 "$(lignes table3)"
    unzip -p "$ARCH" > contenu 2>/dev/null
    egal "N2 token absent from the archive" 0 "$(compte_jeton contenu)"
    grep -E 'Stockfish: done' journal > ligne 2>/dev/null
    joindre ligne
    joindre table3 12
fi

fi

# --- Report -----------------------------------------------------------------

titre "Results"
noter "  passed  : $NB_OK"
noter "  failed  : $NB_ECHEC"
noter "  skipped : $NB_SAUTE"

# The home directory and the temporary directory are masked: the
# report then contains neither your user name nor any private path.
# LC_ALL=C: the report may contain bytes that are not UTF-8, the file
# name refused by T44 for example. Under a UTF-8 locale, the macOS sed
# then stops on "illegal byte sequence" and truncates the report; in
# the C locale, it processes the file byte by byte.
# Last safeguard, with --network: the report is only written if the
# token does not appear in it. A token file that contained a blank line
# would make this check fail wrongly, grep then taking everything for a
# match: the report would be held back, out of caution.
if [ "$RESEAU" = 1 ] &&
    [ "$(grep -a -c -F -f "$JETON" "$BRUT" 2>/dev/null)" != "0" ]; then
    printf '\nThe token appears in the report: report NOT written.\n' >&2
    printf 'Run again with KEEP=1 and report it without sending anything.\n' >&2
    exit 3
fi

LC_ALL=C sed -e "s#$TRAVAIL#<TMP>#g" -e "s#$HOME#~#g" \
    -e "s#${ID_PARTIE:-aucune-partie-donnee}#<PARTIE>#g" "$BRUT" > "$RAPPORT"

printf '\nPassed: %d, failed: %d, skipped: %d\n' \
    "$NB_OK" "$NB_ECHEC" "$NB_SAUTE" >&2
printf 'Report: %s\n' "$RAPPORT" >&2

[ "$NB_ECHEC" -eq 0 ]
