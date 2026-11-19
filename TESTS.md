# IAnalyze : plan de tests

Plan de tests de `collecte-partie.py`. Retour au [README](README.md).

Lancez les tests depuis le répertoire du script, dans l'ordre. Le
script `test-app.sh`, à côté, joue la plupart d'entre eux d'un seul coup
et écrit un rapport : `sh test-app.sh` hors réseau, `sh test-app.sh
--reseau` avec votre jeton. Les chiffres attendus datent du
8 octobre 2026 : les totaux de la base Lichess croissent chaque mois, les
pourcentages bougent peu. "Probable" signale un résultat non mesuré.

Plan mis à jour le 19 novembre 2026, pour la version 3.6.0. État des
vérifications :

- T01, T02, T05, T26, T31, T32 et T34 à T55 : joués le 18 novembre
  2026 sur la version 3.5.8, sous macOS 27.3 (Python 3.15.2,
  Stockfish 19) et sous Debian 13 Trixie (Python 3.13.5, Stockfish
  17.1), python-chess 1.11.2 des deux côtés ;
- T09 à T24, T29 et T33 : joués le même jour, sur les mêmes machines,
  avec un jeton. T28 l'a été avec un jeton factice ;
- T56 à T68 : joués le 19 novembre 2026 sur la version 3.6.0, sur
  les mêmes machines, T56 sur un explorateur simulé ;
- T03, T04, T06 à T08, T69 et T70 : joués sous Linux seulement
  (Ubuntu 24.04, Python 3.13, Stockfish 16) ;
- T25, T27 et T30 : non rejoués depuis la version 3.4.1.

Les chiffres des tests avec jeton datent du 8 octobre, sauf ceux de
T33, relevés le 18 novembre.

Les emplacements par défaut dépendent de la plateforme. Posez d'abord
ces deux variables, que les tests reprennent :

```bash
# Debian
CAT=/usr/local/share/collecte-partie ; VENV=/opt/venv/lichess
# macOS
CAT=~/.local/share/collecte-partie ; VENV=$CAT/venv
```

Sur un terminal, le script pose ses questions de démarrage : validez par
Entrée, ou ajoutez `--sans-questions`. Stockfish tourne par défaut : pour
raccourcir un test qui ne porte pas sur le moteur, ajoutez
`--sans-stockfish`.
Au tout premier lancement sur un terminal, il demande aussi votre
pseudo et votre cadence habituelle, une fois pour toutes (section U).

Préparation, une ligne italienne entièrement cataloguée :

```bash
printf '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 *\n' \
    > italienne.pgn
```

Et une Polonaise, 1.b4 g6, qui sort tôt de la théorie :

```bash
printf '1. b4 g6 2. Bb2 Nf6 3. e3 Bg7 4. Nf3 O-O *\n' \
    > polonaise.pgn
```

Le dépôt fournit aussi `test.pgn`, une partie d'essai qui réunit les cas
tordus : voir T70.

Pour lire une synthèse :

```bash
unzip -p "$ARCH" '*/synthese.md' | less
```

## A. Sans réseau ni jeton

### T01

```bash
python3 -m py_compile collecte-partie.py ; echo $?
```

Attendu : aucune sortie, puis 0.

### T02

```bash
./collecte-partie.py --help | grep -c -- --coups-min
```

Attendu : 4 (usage, option, deux exemples).

### T03

Options refusées, code 2 à chaque fois :

```bash
for o in "--base maitres --cadences rapid" \
         "--base lichess --cadences rapide" \
         "--base lichess --classements 1100" "--coups-min -1" \
         "--pause 1" "--seuil-frequence 150" \
         "--sans-stockfish --profondeur 20" "--base plebe"; do
    ./collecte-partie.py italienne.pgn $o 2>&1 | tail -1; echo "  $?"
done
```

```text
Attendu, dans l'ordre, après "collecte-partie.py: error:" :
  --cadences n'a d'effet qu'avec --base lichess
  --cadences : valeur inconnue "rapide", valeurs admises : ...
  --classements : valeur inconnue "1100", valeurs admises : ...
  --coups-min doit valoir 0 ou plus
  --pause ne doit pas descendre sous 2 secondes
  --seuil-frequence doit être compris entre 0 et 100
  --profondeur n'a pas d'effet avec --sans-stockfish
  argument --base: invalid choice: 'plebe' (...)
Le "$?" affiche 0 à cause du tube : vérifiez le code avec
./collecte-partie.py italienne.pgn --pause 1 ; echo $?   -> 2
```

### T04

```bash
./collecte-partie.py /tmp/inexistant.pgn ; echo $?
./collecte-partie.py inexistant.pgn ; echo $?
```

Attendu : "Fichier PGN introuvable : /tmp/inexistant.pgn", puis 1,
et de même pour `inexistant.pgn`, sans aucune requête vers Lichess.
Seule une source de 8 ou 12 caractères alphanumériques exactement
passe pour un identifiant Lichess.

### T05

```bash
ARCH=$(./collecte-partie.py italienne.pgn --sans-explorateur \
    --sans-stockfish --jeton-fichier /nulle/part \
    --catalogue /nulle/part 2>/dev/null)
echo "$ARCH" ; unzip -l "$ARCH"
```

Attendu : une seule ligne, le chemin de l'archive ; l'archive
contient `synthese.md`, `partie.pgn` et `collecte.json`, sans répertoire
explorateur/. Section 2 : "Collecte de l'explorateur non effectuée :
désactivée par `--sans-explorateur`."

### T06

```bash
./collecte-partie.py italienne.pgn --sans-explorateur \
    --sans-stockfish --sans-questions --garder-dossier
ls -d analyse-italienne-*/
```

Attendu : le dossier existe à côté de l'archive. Sans l'option
(T05), il n'existe pas.

### T07

```bash
echo "Annotez en français." > /tmp/consignes.md
./collecte-partie.py italienne.pgn --sans-explorateur \
    --sans-stockfish --sans-questions --consignes /tmp/consignes.md
```

Attendu : `synthese.md` commence par la section "## Consignes
d'analyse" contenant la phrase.

### T08

```bash
./collecte-partie.py italienne.pgn --sans-explorateur \
    --sans-stockfish --sans-questions --sortie /tmp/analyses
```

Attendu : archive créée dans /tmp/analyses, répertoire créé au besoin.

## B. Catalogue (réseau vers GitHub, sans jeton)

### T09

```bash
./collecte-partie.py --installer-catalogue
```

Attendu : cinq lignes "Téléchargement du catalogue : ...a.tsv" à
"...e.tsv", puis "Catalogue installé : 3865 lignes, 3865 positions
nommées, 7982 positions connues, dans $CAT/catalogue.tsv", chemin
développé.

### T10

```bash
ls -l $CAT/
head -1 $CAT/catalogue.tsv
```

Attendu : `catalogue.tsv` seul sous Debian, à côté du répertoire venv
sous macOS, -rw-r--r--, environ 690 Ko. Première
ligne : #format=1, date=..., lignes=3865, nommees=3865,
connues=7982, source=..., séparés par des tabulations.

### T11

```bash
cp $CAT/catalogue.tsv /tmp/cat1.tsv
./collecte-partie.py --installer-catalogue
diff <(tail -n +2 /tmp/cat1.tsv) \
     <(tail -n +2 $CAT/catalogue.tsv) \
     && echo identique
ls -a $CAT/
```

Attendu : "identique" (seule la ligne datée change), aucun fichier
.catalogue-\*.tmp résiduel.

### T12

```bash
./collecte-partie.py italienne.pgn --catalogue /tmp/vide ; echo $?
```

Attendu : "Catalogue des ouvertures absent :
/tmp/vide/catalogue.tsv introuvable.", suivi de la commande
d'installation avec `--catalogue` /tmp/vide, puis 1. Aucun nouveau
dossier analyse-\* créé.
Le fichier de jeton doit exister : il est lu avant le catalogue,
sans accès réseau. Il en va de même pour T13 et T26.

### T13

```bash
mkdir /tmp/abime
head -n $(( $(wc -l < $CAT/catalogue.tsv) - 10 )) \
    $CAT/catalogue.tsv > /tmp/abime/catalogue.tsv
./collecte-partie.py italienne.pgn --catalogue /tmp/abime
```

Attendu : "Catalogue tronqué : 7982 positions annoncées, 7972 lues
dans /tmp/abime/catalogue.tsv.", suivi de la commande de
réinstallation. La forme head -n -10 n'existe pas sous macOS,
d'où le calcul du nombre de lignes.

## C. Base maîtres (jeton)

### T14

```bash
./collecte-partie.py italienne.pgn --base maitres
```

```text
Attendu : journal "Catalogue des ouvertures : 7982 positions
connues, du ..." puis "Explorateur : base maîtres, ...". Neuf
lignes dans la table, colonne Ouverture dans l'ordre :
  B00 King's Pawn Game
  C20 King's Pawn Game
  C40 King's Knight Opening
  C44 King's Knight Opening: Normal Variation
  C50 Italian Game
  C50 Italian Game: Giuoco Piano
  C53 Italian Game: Classical Variation
  C54 Italian Game: Classical Variation
  C54 Italian Game: Classical Variation, Giuoco Pianissimo
Arrêt : "fin de la partie". Première sortie : "Aucun coup
interrogé ne passe sous le seuil de 10.0 % hors catalogue."
(toutes les positions sont cataloguées, aucune sortie possible).
```

### T15

```bash
./collecte-partie.py polonaise.pgn --base maitres
```

Attendu, ligne 1 : 2879587 parties, b4, rang 9, 0.1 %, Ouverture
"A00 Polish Opening". Probable : arrêt sur échantillon insuffisant
dans les premiers demi-coups, la base maîtres connaissant peu
1.b4 g6.

## D. Base Lichess (jeton)

### T16

```bash
./collecte-partie.py polonaise.pgn --base lichess
```

```text
Attendu :
  ligne 1 : environ 7 270 millions de parties, b4, rang 11, 0.4 %,
            score B. environ 53.5 %, majoritaire e4 à 58.6 %,
            Ouverture "A00 Polish Opening" ;
  ligne 2 : g6 vers 5 %, Ouverture "-", comme les suivantes ;
  section 2 : ligne "Base interrogée : **Lichess** ..." avec les
            filtres par défaut, et ligne "Fenêtre de départ" ;
  première sortie : "**Noirs joue g6** au coup **1** (demi-coup 2)"
            et "dernière position nommée avant la sortie : A00
            Polish Opening".
Arrêt : sur échantillon insuffisant, sinon "fin de la partie", la
Polonaise d'essai ne comptant que 8 demi-coups.
Contrôle croisé : la fréquence de g6 doit correspondre aux 5 %
affichés sur https://lichess.org/opening/Polish_Opening/b4
```

### T17

```bash
./collecte-partie.py polonaise.pgn --base lichess --coups-min 0
```

Attendu : deux lignes, arrêt "sortie de théorie au demi-coup 2 :
g6 joué à 5.x %, seuil 10.0 %, hors catalogue".

### T18

```bash
./collecte-partie.py polonaise.pgn --base lichess --coups-min 0 \
    --cadences ' Rapid,CLASSICAL,rapid' --classements 1000,0
```

Attendu : `collecte.json` porte "cadences": "rapid,classical" et
"classements": "0,1000" ; la synthèse affiche les mêmes valeurs ;
le total de la ligne 1 est nettement inférieur à celui de T16.

## E. Seuils et modes (jeton)

### T19

```bash
./collecte-partie.py italienne.pgn --base lichess \
    --seuil-parties 100000000000
```

Attendu : arrêt "échantillon insuffisant au demi-coup 1 : ...
parties pour un seuil de 100000000000" ; section 4 liste ce
demi-coup, suivi de "Au delà de ce point, la base Lichess (tous
joueurs) ne dit plus rien d'exploitable".

### T20

```bash
./collecte-partie.py polonaise.pgn --base lichess --coups-min 0 \
    --seuil-frequence 0
```

Attendu : "Aucun coup interrogé ne passe sous le seuil de 0.0 %
hors catalogue." ; arrêt sur échantillon ou position inconnue.

### T21

```bash
./collecte-partie.py polonaise.pgn --base lichess --jusqu-a-epuisement
```

Attendu : texte "Mode ``--jusqu-a-epuisement``" ; arrêt "position
inconnue de la base au demi-coup N" ou "fin de la partie" ;
première sortie toujours g6, demi-coup 2.

### T22

```bash
./collecte-partie.py italienne.pgn --jusqu-a-epuisement \
    --max-demicoups 4
```

Attendu : quatre lignes, arrêt "plafond de 4 demi-coups atteint
(option `--max-demicoups`)".

### T23

```bash
./collecte-partie.py italienne.pgn --pause 3 2>&1 | grep demi-coup
```

Attendu : au moins 3 secondes entre deux horodatages successifs.

## F. Source Lichess

### T24

```bash
./collecte-partie.py https://lichess.org/<ID> --sans-explorateur
./collecte-partie.py <ID> --sans-explorateur
(<ID> : une de vos parties Lichess, huit caractères.)
```

Attendu : journal "Téléchargement du PGN :
https:`//lichess.org/game/export/<ID>`", archive
`analyse-<ID>-<horodatage>.zip`.

## G. Stockfish

### T25

```bash
./collecte-partie.py italienne.pgn --sans-explorateur \
    --avec-stockfish --coups-stockfish 3 --profondeur 10 \
    --multipv 2 --longueur-pv 4 --fils 2 --hachage 128
```

Attendu : "Moteur : `&lt;binaire par défaut>`, profondeur 10, multipv
2, 6 demi-coups couverts sur 9." ; six lignes, colonne 3e à "-" ;
variantes de la section 3 bis tronquées à 4 demi-coups ;
stockfish/evaluations.json présent ; fils et hachage visibles dans
`collecte.json`.

### T26

```bash
./collecte-partie.py italienne.pgn --avec-stockfish \
    --stockfish /nulle/part ; echo $?
```

Attendu : "Stockfish introuvable : /nulle/part. Installez-le (apt
install stockfish, dans /usr/games), indiquez son chemin avec
`--stockfish`, ou laissez l'évaluation à l'analyste avec
`--sans-stockfish`.", puis 1. Sous macOS, la parenthèse devient
"(brew install stockfish)".

## H. Jeton

### T27

```bash
./collecte-partie.py italienne.pgn --jeton-fichier /nulle/part
```

Attendu : "Jeton absent : /nulle/part introuvable.", code 1.

### T28

```bash
cp ~/.lichess_token ~/jeton-test ; chmod 644 ~/jeton-test
./collecte-partie.py italienne.pgn --jeton-fichier ~/jeton-test \
    --max-demicoups 1
shred -u ~/jeton-test       # sous macOS : rm ~/jeton-test
```

Attendu : "Attention : &lt;chemin complet de `~/jeton-test`> est lisible
par d'autres (mode 644)." dans le journal, collecte normale ensuite.

### T29

```bash
ARCH=$(./collecte-partie.py italienne.pgn 2>/dev/null)
unzip -p "$ARCH" | grep -c -F -f ~/.lichess_token
```

Attendu : 0. Le jeton est lu depuis le fichier par grep, il ne
passe pas dans la ligne de commande.

## I. Environnement virtuel

### T30

```bash
./collecte-partie.py --installer-venv
```

Attendu : "Environnement virtuel déjà présent : $VENV", puis
"Installation de python-chess dans l'environnement virtuel." et
"Environnement virtuel opérationnel : $VENV/bin/python3", chemins
développés.

## J. Plateforme

### T31

```bash
./collecte-partie.py --help | grep -c "brew install"
```

Attendu : 0 sous Debian, 3 sous macOS.

### T32

```bash
./collecte-partie.py --help | grep -c "apt install"
```

Attendu : 3 sous Debian, 0 sous macOS.

## K. Roque (jeton)

### T33

```bash
printf '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6 ' \
    > roques.pgn
printf '6. O-O O-O *\n' >> roques.pgn
./collecte-partie.py roques.pgn --sans-stockfish --sans-questions
```

Attendu : douze lignes dans la table. Lignes 11 et 12, O-O au rang
1 puis au rang 2, fréquences proches de 27 % et de 19 % (27.1 % et
18.9 % le 18 novembre 2026, sur 4060402 et 2417197 parties).
Arrêt : "fin de la partie". Avant la version 3.4.1, un roque
ressortait à 0.0 %, au rang "-", et passait pour une sortie de
théorie : la base le note "roi prend tour", e1h1, là où le script
comparait avec e1g1.

## L. Encodages (sans réseau ni jeton)

Les fixtures sont produites par printf, aucun fichier binaire n'est
versionné. Posez d'abord :

```bash
O="--sans-explorateur --sans-stockfish --sans-questions"
```

### T34

```bash
printf '[White "Jos\351"]\n[Black "M\374ller"]\n[Site "\201"]\n\n' \
    > t-latin1.pgn
printf '1. e4 e5 *\n' >> t-latin1.pgn
ARCH=$(./collecte-partie.py t-latin1.pgn $O) ; echo $?
unzip -p "$ARCH" '*/synthese.md' | grep -E 'White|Black|Encodage'
```

```text
Attendu, dans le journal :
  Attention, PGN : le contenu n'est pas en UTF-8, encodage retenu :
  latin-1.
  Attention, PGN : 1 caractère(s) de contrôle retiré(s), dont 0 NUL.
puis 0. Synthèse : "| White | José |", "| Black | Müller |", et en
section 5 la ligne "- Encodage : le PGN fourni a été converti en
UTF-8 ...". L'octet 201, que cp1252 ne définit pas, force le repli
jusqu'à latin-1.
```

### T35

```bash
printf '[White "Jos\351"]\n[Event "Coupe d\222\351t\351 \226 5 \200"]\n' \
    > t-cp1252.pgn
printf '\n1. e4 e5 *\n' >> t-cp1252.pgn
ARCH=$(./collecte-partie.py t-cp1252.pgn $O)
unzip -p "$ARCH" '*/synthese.md' | grep -E 'White|Event'
```

Attendu : "Attention, PGN : le contenu n'est pas en UTF-8, encodage
retenu : cp1252." ; "| Event | Coupe d’été – 5 € |" avec
l'apostrophe courbe, le tiret demi-cadratin et l'euro, et
"| White | José |".

### T36

```bash
printf '\357\273\277[White "Jos\303\251"]\n\n1. e4 e5 *\n' \
    > t-bom.pgn
ARCH=$(./collecte-partie.py t-bom.pgn $O)
unzip -p "$ARCH" '*/partie.pgn' | od -c | head -n 1
```

Attendu : "Attention, PGN : marque d'ordre des octets (BOM) UTF-8
retirée." ; la sortie de od commence par "[   W   h   i   t   e",
sans 357 273 277.

### T37

```bash
printf '[White "Jos\303\251"]\n\n1. e4 e5 *\n' \
    | iconv -f UTF-8 -t UTF-16LE > t-utf16.pgn
{ printf '\377\376' ; cat t-utf16.pgn ; } > t-utf16-bom.pgn
for f in t-utf16-bom.pgn t-utf16.pgn; do
    ARCH=$(./collecte-partie.py $f $O)
    unzip -p "$ARCH" '*/synthese.md' | grep White
done
```

Attendu, pour le premier : "Attention, PGN : marque d'ordre des
octets (BOM) détectée, encodage retenu : utf-16-le." ; pour le
second : "Attention, PGN : un octet nul sur deux et pas de marque
d'ordre des octets, encodage retenu : utf-16-le." ; dans les deux
cas "| White | José |". Avant la version 3.5.0 : "PGN sans aucun
coup dans la ligne principale."

### T38

```bash
printf '[White "Jos\303\251"]\n\n1. e4 {tr\377\376s bon} e5 *\n' \
    > t-abime.pgn
ARCH=$(./collecte-partie.py t-abime.pgn $O) ; echo $?
unzip -p "$ARCH" '*/synthese.md' | grep White
unzip -p "$ARCH" '*/partie.pgn' | grep -c 's bon}'
```

Attendu : "Attention, PGN : UTF-8 abîmé, 2 octet(s) invalide(s)
remplacé(s) par U+FFFD, encodage retenu : utf-8.", puis 0 ;
"| White | José |" intact ; 1 : le commentaire est gardé, ses deux
octets invalides remplacés.

### T39

```bash
printf '[White "Jo\000s"]\n\n1. e4\000 e5 *\n' > t-nul.pgn
ARCH=$(./collecte-partie.py t-nul.pgn $O) ; echo $?
unzip -p "$ARCH" | od -c | grep -c '\\0'
```

Attendu : "Attention, PGN : 2 caractère(s) de contrôle retiré(s),
dont 2 NUL.", puis 0, puis 0 : aucun NUL dans l'archive.

### T40

```bash
printf '[White "A"]\r\n\r\n1. e4 e5 *\r\n' > t-crlf.pgn
ARCH=$(./collecte-partie.py t-crlf.pgn $O 2> t-crlf.log)
grep -c Attention t-crlf.log
unzip -p "$ARCH" '*/partie.pgn' | od -c | grep -c '\\r'
```

Attendu : 0 et 0. Les fins de ligne CRLF sont ramenées à LF sans
avertissement.

### T41

```bash
LANG=C ./collecte-partie.py t-latin1.pgn $O ; echo $?
LC_ALL=C PYTHONUTF8=0 ./collecte-partie.py --help \
    | grep 'questions de d'
PYTHONIOENCODING=ascii ./collecte-partie.py --help > /dev/null
echo $?
```

Attendu : 0 pour le premier lancement, le chemin de l'archive étant
affiché ; "questions de d?marrage:" pour le deuxième ; 0 pour le
troisième. Sous LANG=C seul, Python passe de lui-même en UTF-8 et
les accents s'affichent ; dans les deux autres cas ils deviennent
"?". Avant la version 3.5.0, ces deux derniers lancements donnaient
"Erreur inattendue (UnicodeEncodeError)" et le code 1.

### T42

```bash
printf '[Event "Tour\tnoi"]\n[Site "\033[31mParis\007"]\n\n' \
    > t-ctrl.pgn
printf '1. e4 e5 *\n' >> t-ctrl.pgn
ARCH=$(./collecte-partie.py t-ctrl.pgn $O)
unzip -p "$ARCH" '*/synthese.md' | grep -E 'Event|Site'
unzip -p "$ARCH" | tr -d -c '\033\007' | wc -c
```

Attendu : "Attention, PGN : 2 caractère(s) de contrôle retiré(s),
dont 0 NUL." ; "| Event | Tour noi |", la tabulation devenue une
espace, et "| Site | [31mParis |" ; puis 0 : ni ESC ni BEL dans
l'archive.

### T43

```bash
printf '\357\273\277lip_factice\r\n' > t-jeton ; chmod 600 t-jeton
./collecte-partie.py italienne.pgn --sans-stockfish \
    --sans-questions --jeton-fichier t-jeton --catalogue /nulle/part
printf 'lip_factic\351\n' > t-jeton
./collecte-partie.py italienne.pgn --sans-stockfish \
    --sans-questions --jeton-fichier t-jeton --catalogue /nulle/part
echo $?
```

Attendu, premier lancement : "Attention, jeton (.../t-jeton) :
marque d'ordre des octets (BOM) UTF-8 retirée.", puis "Catalogue des
ouvertures absent", preuve que le jeton est accepté, sans réseau.
Second lancement : "Le jeton lu dans .../t-jeton contient des
caractères hors de l'ASCII imprimable : recopiez-le depuis Lichess,
sans rien d'autre dans le fichier.", puis 1. Le jeton n'est
reproduit dans aucun des deux messages.

### T44

```bash
cp italienne.pgn 't-a:b?.pgn'
./collecte-partie.py 't-a:b?.pgn' $O
cp italienne.pgn "$(printf 't-\351t\351.pgn')"      # Linux seulement
./collecte-partie.py "$(printf 't-\351t\351.pgn')" $O ; echo $?
```

Attendu : "Nom du dossier assaini : t-a_b\_", archive
`analyse-t-a_b_-<horodatage>.zip` ; puis "Nom du dossier assaini :
t-\_t\_", archive `analyse-t-_t_-<horodatage>.zip`, et 0. Avant la
version 3.5.0, le second lancement donnait "Erreur inattendue
(UnicodeEncodeError)". Sous macOS, le système de fichiers refuse
de créer ce second fichier, au nom non UTF-8 : cp répond "Illegal
byte sequence" (vérifié sous macOS 27.3), le cas ne peut donc pas
s'y produire.

### T45

Réponse saisie en latin-1 aux questions de démarrage. Le test
passe par un pseudo-terminal, les questions n'étant posées que sur
un terminal. Il fournit son propre fichier de réglages, afin que
les questions du premier lancement ne décalent pas ses réponses :

```bash
printf '[joueur]\npseudos = Moi\ncadence = 14 jours\n' > t-r45.ini
printf 'niveau = 1300\n' >> t-r45.ini
python3 - <<'EOF'
import os, pty, time
pid, fd = pty.fork()
if pid == 0:
    os.execv("./collecte-partie.py",
             ["./collecte-partie.py", "italienne.pgn",
              "--sans-explorateur", "--sans-stockfish",
              "--garder-dossier", "--reglages", "t-r45.ini"])
for reponse in (b"b", b"Zo\xe9", b"", b"", b"", b"", b""):
    time.sleep(1)
    os.write(fd, reponse + b"\n")
time.sleep(3)
print(os.read(fd, 65536).decode("utf-8", "replace")[-160:])
os.waitpid(pid, 0)
EOF
grep Black analyse-italienne-*/partie.pgn
```

Attendu : la sortie se termine par le chemin de l'archive, et
`partie.pgn` porte [Black "Zoé"]. Avant la version 3.5.0 : "Erreur
inattendue (UnicodeEncodeError)".

### T46

```bash
ARCH=$(./collecte-partie.py italienne.pgn $O 2> t-utf8.log)
grep -c Attention t-utf8.log
unzip -p "$ARCH" '*/collecte.json' | grep pgn_
```

Attendu : 0, puis "pgn_encodage": "utf-8" et "pgn_remarques": [].
Un PGN sain ne déclenche aucun avertissement.

### T47

```bash
grep -n '^VERSION' collecte-partie.py
```

Attendu : VERSION = "3.6.0". L'en-tête d'agent HTTP en est tiré.

## M. Nom du PGN

### T48

```bash
cp italienne.pgn t-2026.11.18_A_vs_B.pgn
ARCH=$(./collecte-partie.py t-2026.11.18_A_vs_B.pgn $O) ; echo $?
echo "$ARCH" ; unzip -l "$ARCH" | grep -c synthese.md
ls -d analyse-t-2026*
```

Attendu : 0, puis `analyse-t-2026.11.18_A_vs_B-<horodatage>.zip`,
puis 1 ; ls ne montre que cette archive et son prompt, le dossier
de travail étant supprimé. Avant la version 3.5.1 : "Archive illisible,
dossier conservé : [Errno 2] No such file or directory:
'`analyse-t-2026.11.zip`'", code 1, rien sur la sortie standard.

## N. Explorateur simulé et valeurs non finies (sans réseau ni jeton)

### T49

Réponses inattendues de l'explorateur, sans réseau : le script est
chargé comme module par l'interpréteur de l'environnement virtuel,
et l'explorateur est remplacé par un faux.

```bash
$VENV/bin/python3 - <<'EOF'
import importlib.util, io, json, pathlib, tempfile
import chess.pgn
spec = importlib.util.spec_from_file_location("cp",
                                              "collecte-partie.py")
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
```

Attendu : "2 20 None" puis "2 10 None", chacun précédé de deux
lignes de journal "Explorateur : demi-coup", sans trace Python.
"moves" n'étant pas une liste, le coup joué est hors base ; le
compteur infini vaut zéro. Avant la version 3.5.2 : TypeError
("'int' object is not iterable"), puis OverflowError.

### T50

```bash
for o in "--pause nan" "--pause inf" "--seuil-frequence nan"; do
    ./collecte-partie.py italienne.pgn $o 2>&1 | tail -1
done
./collecte-partie.py italienne.pgn --pause nan ; echo $?
ls -d analyse-italienne-* 2>/dev/null | wc -l
```

```text
Attendu, après "collecte-partie.py: error:" :
  --pause doit être un nombre fini
  --pause doit être un nombre fini
  --seuil-frequence doit être un nombre fini
puis le code 2, puis 0 (lancez ce test après le nettoyage : aucun
dossier de travail n'est créé). Avant la version 3.5.2, --pause nan
donnait "Erreur inattendue (ValueError) : Invalid value NaN" à la
première pause, et --seuil-frequence nan était accepté.
```

## O. Stockfish : mat manqué

### T51

```bash
printf '1. f3 e5 2. g4 Nc6 *\n' > t-mat.pgn
ARCH=$(./collecte-partie.py t-mat.pgn --sans-explorateur \
    --sans-questions --profondeur 8 --fils 2 --hachage 32)
unzip -p "$ARCH" '*/synthese.md' | grep -E '^\| [34] \||cart .mat'
unzip -p "$ARCH" '*/evaluations.json' | grep -c '"ecart_cp": 99'
```

```text
Attendu : la phrase "Écart `mat` : l'un des deux scores comparés
est un mat ...", puis les lignes 3 et 4 du tableau. Les Blancs
concèdent un mat par g4, les Noirs le manquent par Nc6 :
  | 3 | 2 | Blancs | g4 | #-1 | 0/0/100 | mat | gaffe | ...
  | 4 | 2 | Noirs | Nc6 | <éval> | 0/0/100 | mat | gaffe |
  Qh4# (#-1) | ...
puis 2 : evaluations.json garde les deux valeurs brutes.
L'évaluation de Nc6 varie avec la version du moteur. Avant la
version 3.5.3, la colonne Écart cp affichait deux nombres voisins
de 99700.
```

## P. Stockfish : coup nul

### T52

```bash
printf '1. e4 e5 2. -- Nc6 3. Nf3 *\n' > t-nul-coup.pgn
ARCH=$(./collecte-partie.py t-nul-coup.pgn --sans-explorateur \
    --sans-questions --profondeur 8 --fils 2 --hachage 32)
echo $?
unzip -p "$ARCH" '*/synthese.md' \
    | grep -E '^\| [34] \||Coup nul|coup nul'
```

```text
Attendu : 0, puis la phrase "Coup nul `--` : le trait passe sans
qu'une pièce ne bouge ...", puis les lignes 3 et 4 du tableau :
  | 3 | 2 | Blancs | -- | - | - | - | - | <trois coups> |
  | 4 | 2 | Noirs | Nc6 | <éval> | <G/N/P> | <écart> | ... |
et, en section 3 bis, "    - joué : coup nul, non évalué par le
moteur". Le coup suivant, Nc6, est évalué normalement. Avant la
version 3.5.4, la ligne 3 portait une évaluation "+0.00", un écart
et la nature "imprécision", tous inventés.
```

## Q. Interruption (sans réseau ni jeton)

### T53

Interruption simulée pendant l'archivage, puis écriture qui échoue
en cours de route. Le script est chargé comme module, comme pour
T49. Lancez le test dans un répertoire vide :

```bash
mkdir t-r1 && cd t-r1
$VENV/bin/python3 - <<'EOF'
import importlib.util, pathlib, zipfile
spec = importlib.util.spec_from_file_location(
    "cp", "../collecte-partie.py")
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
cd .. && rm -rf t-r1
```

```text
Attendu, hors lignes de journal :
  archivage interrompu
  ['analyse-essai-1']
  5000
  ['collecte.json', 'partie.pgn', 'synthese.md']
  analyse-essai-1.zip
  ['analyse-essai-1.zip']
Après l'interruption, il ne reste que le dossier de travail : ni
archive, ni fichier .partiel. L'écriture qui échoue laisse
synthese.md intact, 5000 octets. L'archivage relancé aboutit
ensuite normalement. Avant la version 3.5.5, la deuxième ligne
était ['analyse-essai-1', 'analyse-essai-1.zip'], un zip tronqué
sous le nom d'une archive, et la troisième 0.
```

## R. Url de la partie (sans réseau ni jeton)

### T54

```bash
for u in https://lichess.org/analysis/standard \
         https://lichess.org/study/abcdefgh/ijklmnop \
         https://example.com/abcdefgh ; do
    ./collecte-partie.py $u --sans-explorateur --sans-stockfish \
        2>&1 | grep -c -E 'URL non reconnue|chargement du PGN'
done
./collecte-partie.py https://example.com/abcdefgh ; echo $?
python3 - <<'EOF'
import importlib.util
spec = importlib.util.spec_from_file_location("cp",
                                              "collecte-partie.py")
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
for u in ("https://lichess.org/xvoiNy2C/black",
          "https://www.lichess.org/xvoiNy2CabcD#12",
          "https://lichess.org/embed/game/xvoiNy2C",
          "https://lichess.org/game/export/xvoiNy2C",
          "xvoiNy2C", "https://lichess.org/practice", "analysis"):
    print(cp.extraire_id(u))
EOF
```

Attendu : 1, 1, 1, une seule ligne à chaque fois, celle du refus,
sans ligne "Téléchargement du PGN" ; puis "URL non reconnue comme
une partie Lichess : https://example.com/abcdefgh", la forme
attendue, et le code 1 ; puis cinq fois "xvoiNy2C" et deux fois
"None". Avant la version 3.5.6, les trois URL étaient demandées à
Lichess et les deux dernières lignes valaient "practice" et
"analysis".

## S. Options moteur hors bornes (sans réseau ni jeton)

### T55

```bash
for o in "--fils 100000" "--hachage 99999999999" "--multipv 9999"
do
    ./collecte-partie.py italienne.pgn --sans-explorateur \
        --sans-questions $o 2>&1 | tail -1
done
./collecte-partie.py italienne.pgn --sans-explorateur \
    --sans-questions --fils 100000 2>/dev/null ; echo $?
ls -d analyse-italienne-* 2>/dev/null | wc -l
```

```text
Attendu, avec Stockfish 16 :
  --fils : 100000 est hors des bornes du moteur <binaire>, qui
  admet de 1 à 1024 pour Threads.
  --hachage : 99999999999 est hors des bornes du moteur <binaire>,
  qui admet de 1 à 33554432 pour Hash.
  --multipv : 9999 est hors des bornes du moteur <binaire>, qui
  admet de 1 à 500 pour MultiPV.
puis le code 1, puis 0 (lancez ce test après le nettoyage : aucun
dossier de travail n'est créé). Les bornes sont celles qu'annonce
le moteur, elles varient d'une version à l'autre. Avant la version
3.5.7, le refus n'arrivait qu'après la phase explorateur, par "Le
moteur a échoué en cours d'analyse : expected value for option
'Threads' to be at most 1024, got: 100000", dossier de travail
déjà créé.
```

## T. Explorateur : coup nul (sans réseau ni jeton)

### T56

Coup nul dans la partie, explorateur simulé, comme pour T49 :

```bash
$VENV/bin/python3 - <<'EOF'
import importlib.util, io, pathlib, tempfile
import chess.pgn
spec = importlib.util.spec_from_file_location("cp",
                                              "collecte-partie.py")
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
partie = chess.pgn.read_game(
    io.StringIO("1. e4 e5 2. -- Nc6 3. Nf3 *"))
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
print(r["arret"])
print([(n["demicoup"], n["san"], n["motif"])
       for n in r["non_exploitables"]])
EOF
```

```text
Attendu, hors lignes de journal :
  2 2 None
  coup nul au demi-coup 3 : ce n'est pas un coup des échecs,
  l'explorateur ne peut pas suivre la partie au delà
  [(3, '--', 'coup nul, non interrogé')]
Deux requêtes pour deux lignes : rien n'est demandé pour le coup
nul ni au delà, et il n'est pas une sortie de théorie. Avant la
version 3.5.9 : trois lignes, le coup nul à 0.0 % désigné comme
première sortie de théorie, puis, sur le vrai explorateur, "HTTP
400 au demi-coup 4" (illegal move 0000).
```

## U. Réglages (sans réseau ni jeton)

Les questions de réglages ne sont posées que sur un terminal. Ces tests
passent donc par un pseudo-terminal, piloté par un petit script que le
premier d'entre eux crée : il lance `collecte-partie.py` avec les options
données, répond aux questions dans l'ordre, les réponses étant
séparées par des barres verticales, puis affiche ce que le terminal a
montré. S'il manque une réponse, il envoie une fin de flux après
quinze secondes de silence, plutôt que d'attendre sans fin : les
questions restantes prennent alors leur valeur par défaut.
Tous désignent leur fichier par `--reglages` : le vôtre n'est ni lu ni
modifié.

### T57

```bash
cat > t-pty.py <<'EOF'
import os, pty, select, sys
pid, fd = pty.fork()
if pid == 0:
    os.execv("./collecte-partie.py",
             ["./collecte-partie.py"] + sys.argv[2:])
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
P="--sans-explorateur --sans-stockfish --garder-dossier"
python3 t-pty.py "Zoe42, zoe|t|15|10|1300|b||||||" italienne.pgn \
    $P --reglages t-reglages.ini | grep -E 'glages|Votre|par '
grep -v '^#' t-reglages.ini
grep White analyse-italienne-*/partie.pgn
grep Cadence analyse-italienne-*/contexte.md
```

```text
Attendu, premier lancement : "Réglages : 3 réponse(s) à donner une
seule fois, gardée(s) dans t-reglages.ini.", la question "Votre
pseudo de joueur, ou plusieurs séparés par des virgules ? (Entrée
: aucun)", puis "Votre cadence habituelle : [t]emps réel,
[c]orrespondance ou [i]nconnue ? (Entrée : non précisée)",
"Minutes par joueur ?" et "Incrément en secondes ?", puis "Votre
niveau, en points Elo approximatifs ? (Entrée : inconnu)", enfin
"Réglages enregistrés : t-reglages.ini". Le fichier contient :
  [joueur]
  pseudos = Zoe42, zoe
  cadence = 15+10
  niveau = 1300
puis [White "Zoe42"], la balise vide ayant reçu le premier pseudo,
et "- Cadence : rapide, 15 minutes + 10 secondes par coup
(défaut)" : la question de cadence de la partie, validée par
Entrée, a retenu la cadence habituelle.
```

### T58

```bash
rm -rf analyse-italienne-*
python3 t-pty.py "b||||||" italienne.pgn $P \
    --reglages t-reglages.ini | grep -c -E 'glages|Votre'
printf '[White "Alice"]\n[Black "Zoe42"]\n\n1. e4 e5 *\n' \
    > t-noms.pgn
python3 t-pty.py "||||" t-noms.pgn $P --reglages t-reglages.ini \
    > /dev/null
grep Camp analyse-t-noms-*/contexte.md ; rm -rf analyse-t-noms-*
python3 t-pty.py "||||" t-noms.pgn $P --reglages t-reglages.ini \
    --pseudos Alice > /dev/null
grep Camp analyse-t-noms-*/contexte.md
```

Attendu : 0, les réglages n'étant demandés qu'une fois ; puis
"- Camp du joueur : Noirs, déduit des en-têtes", le pseudo venant
des réglages ; puis "- Camp du joueur : Blancs, déduit des
en-têtes", `--pseudos` l'emportant sur les réglages.

### T59

```bash
./collecte-partie.py italienne.pgn $O --reglages t-abs/reglages.ini
ls t-abs
python3 t-pty.py "|||n|Moi|Lui|||||" italienne.pgn $P \
    --reglages t-vide.ini | grep 'Votre nom'
grep -v '^#' t-vide.ini
```

Attendu : hors terminal ($O porte `--sans-questions`), la collecte
aboutit sans rien demander, et ls ne trouve pas t-abs : aucun
fichier n'est créé. Puis, les trois questions de réglages étant
validées par Entrée, "Votre nom de joueur ? (Entrée : ?) Moi" :
sans pseudo, le nom est demandé comme celui de l'adversaire. Le
fichier garde "pseudos =", "cadence = inconnue" et "niveau =
inconnu", et ne redemandera rien.

### T60

```bash
printf 'pseudos = Alice\n' > t-mauvais.ini
./collecte-partie.py italienne.pgn $O --reglages t-mauvais.ini
echo $?
printf '[joueur]\npseudos = Alice\nniveau = 1500\n\n' > t-plus.ini
printf '[perso]\nnote = 100 %% à moi\n' >> t-plus.ini
python3 t-pty.py "c|d|14|||||" t-noms.pgn $P \
    --reglages t-plus.ini \
    > /dev/null
grep -v '^#' t-plus.ini
```

```text
Attendu : "Réglages illisibles : File contains no section headers.
...", puis "Corrigez t-mauvais.ini, ou supprimez-le : il sera
recréé au prochain lancement sur un terminal.", et 1, sans dossier
de travail. Puis, pour t-plus.ini, seule la cadence étant
demandée :
  [joueur]
  pseudos = Alice
  cadence = 14 jours
  niveau = 1500

  [perso]
  note = 100 % à moi
Les clefs et les sections ajoutées à la main sont conservées.
```

### T62

Cadence : seules des réponses vérifiées sont acceptées.

```bash
printf '[joueur]\npseudos = Alice\nniveau = inconnu\n' > t-cad.ini
printf 'cadence = Ploum ploum\n' >> t-cad.ini
python3 t-pty.py "x|t|abc|-5|0|0|t|15|10|||||" t-noms.pgn $P \
    --reglages t-cad.ini | grep -E 'lisible|attendue|existe'
grep cadence t-cad.ini
rm -rf analyse-t-noms-*
python3 t-pty.py "t|5|0||||" t-noms.pgn $P --reglages t-cad.ini \
    > /dev/null
grep Cadence analyse-t-noms-*/contexte.md ; rm -rf analyse-t-noms-*
printf '[White "Alice"]\n[Black "Bob"]\n' > t-tc.pgn
printf '[TimeControl "600+5"]\n\n1. e4 e5 *\n' >> t-tc.pgn
python3 t-pty.py "||||" t-tc.pgn $P --reglages t-cad.ini \
    | grep -c 'Cadence de la partie'
grep Cadence analyse-t-tc-*/contexte.md
```

Attendu : "Réglages : la cadence enregistrée, "Ploum ploum", n'est
pas lisible, elle est redemandée.", puis, les réponses fausses
étant refusées une à une, "Réponse attendue : t, c ou i." une
fois, "Réponse attendue : un nombre entier, 0 ou plus." deux
fois, et "Une cadence sans temps ni incrément n'existe pas." une
fois ; le fichier porte ensuite "cadence = 15+10". Puis
"- Cadence : blitz, 5 minutes sans incrément", la cadence de la
partie pouvant différer de l'habituelle. Enfin 0 et "- Cadence :
balise TimeControl `600+5`, soit rapide, 10 minutes + 5 secondes
par coup" : la balise dispense de la question, et elle est
traduite. Catégories de Lichess, d'après le temps initial plus
quarante fois l'incrément : ultrabullet sous 30 secondes, bullet
sous 3 minutes, blitz sous 8, rapide sous 25, classique au delà.

### T63

Correspondance : trois systèmes, tous vérifiés.

```bash
printf '[joueur]\npseudos = Alice\nniveau = inconnu\n' > t-corr.ini
python3 t-pty.py "c|x|c|0|0h|||c|5|36|36h|2||c|5|36h|20||||||" \
    t-noms.pgn $P --reglages t-corr.ini \
    | grep -E 'attendue|incohérente'
grep cadence t-corr.ini
grep Cadence analyse-t-noms-*/contexte.md ; rm -rf analyse-t-noms-*
for c in '10 coups en 50 jours' \
         '50j+3j, plafond 50j, réserve 75j'; do
    printf '[joueur]\npseudos = Alice\nniveau = inconnu\n' \
        > t-corr.ini
    printf 'cadence = %s\n' "$c" >> t-corr.ini
    python3 t-pty.py "||||" t-noms.pgn $P --reglages t-corr.ini \
        > /dev/null
    grep Cadence analyse-t-noms-*/contexte.md
    rm -rf analyse-t-noms-*
done
```

Attendu, dans l'ordre : "Réponse attendue : d, p ou c." pour un
système inconnu ; "Cadence incohérente : il faut un capital ou un
incrément, et un plafond au moins égal au capital de départ." pour
0 jour et 0 heure ; "Réponse attendue : un nombre entier suivi de
h ou de j." pour un incrément sans unité ; puis la même "Cadence
incohérente" pour un plafond de 2 jours sous un capital de 5. Le
fichier porte ensuite "cadence = 5 jours + 36 heures, plafond 20
jours", et `contexte.md` "- Cadence : correspondance, capital de 5
jours + 36 heures par coup, plafonné à 20 jours (défaut)" : c'est
le système de chess-mail.com. Les deux autres formes, écrites à la
main dans le fichier, donnent "- Cadence : correspondance, 10
coups en 50 jours (défaut)", cadence standard de l'ICCF, puis
"- Cadence : correspondance, capital de 50 jours + 3 jours par
coup, plafonné à 50 jours, réserve de 75 jours (défaut)", son
Triple Block.

### T61

```bash
./collecte-partie.py --help | grep -c 'ceux de vos réglages'
grep -c 'PSEUDOS_DEFAUT' collecte-partie.py
./collecte-partie.py italienne.pgn --pseudos ' , ' 2>&1 | tail -1
```

Attendu : 1, l'aide de `--pseudos` n'annonçant plus aucun pseudo par
défaut ; 0, la constante qui le portait ayant disparu ; puis
"`collecte-partie.py`: error: `--pseudos` : liste vide".

## V. Prompt d'analyse (sans réseau ni jeton)

Préparation, une partie aux deux noms connus et des réglages complets :

```bash
printf '[White "Alice"]\n[Black "Bob"]\n[BlackElo "1500"]\n\n' \
    > t-pr.pgn
printf '1. e4 e5 *\n' >> t-pr.pgn
printf '[joueur]\npseudos = Alice\ncadence = 14 jours\n' > t-pr.ini
printf 'niveau = 1300\n' >> t-pr.ini
R="--sans-explorateur --sans-questions --reglages t-pr.ini"
```

### T64

```bash
ARCH=$(./collecte-partie.py t-pr.pgn $R --sans-stockfish \
    2> t-pr.log)
echo "$ARCH" | wc -l ; PR="${ARCH%.zip}.prompt.txt" ; ls "$PR"
grep -c 'Prompt d.analyse écrit' t-pr.log
grep -c -E '^#!|\{\{' "$PR" ; unzip -l "$ARCH" | grep -c prompt
sed -n 1,13p "$PR"
```

```text
Attendu : 1, la sortie standard ne portant que le chemin de
l'archive ; le fichier analyse-t-pr-<horodatage>.prompt.txt, à
côté de l'archive ; 1 ; puis 0 et 0 : aucun repère du modèle ne
reste dans le prompt, et le prompt n'est pas dans le zip. Ses
premières lignes :
  Prompt produit par IAnalyze v3.6.0, https://github.com/deuza/IAnalyze
  pour l'archive analyse-t-pr-<horodatage>.zip

  Joueur à qui vous vous adressez :
  - pseudo, sur Lichess et en général : Alice
  - camp dans cette partie : Blancs
  - niveau : environ 1300 Elo, déclaré par le joueur
  - cadence habituelle, si ni les en-têtes ni les consignes ne donnent
    celle de la partie : correspondance, 14 jours par coup
  Balise Annotator du PGN que vous produirez :
  votre nom de modèle, suivi de son éditeur entre parenthèses
Le camp est déduit du pseudo, hors terminal et sans question.
```

### T65

Le prompt ne garde que les passages qui s'appliquent.

```bash
for motif in 'Stockfish. : absente de ce dossier' \
             'La section 3 est absente' 'Stockfish est inutile' \
             'collecte de l.explorateur n.a pas' \
             'celle de tous les joueurs de Lichess'; do
    grep -c "$motif" "$PR"
done
ARCH=$(./collecte-partie.py t-pr.pgn $R --profondeur 6 --fils 1 \
    --hachage 16 --base maitres 2>/dev/null)
PR="${ARCH%.zip}.prompt.txt"
for motif in 'Stockfish est inutile' 'Les chiffres de la section 3' \
             'porte "mat"' 'La section 3 est absente' \
             'celle des maîtres'; do
    grep -c "$motif" "$PR"
done
```

Attendu, sans moteur : 1, 1, 0, 1, 1. Puis, avec le moteur et la
base maîtres : 1, 1, 1, 0, 1. Le premier prompt demande à
l'analyste d'évaluer lui-même, le second lui dit que les chiffres
font foi et lui explique la mention "mat".

### T66

```bash
printf 'Bonjour {{PSEUDO}}\n' > t-modele.txt
./collecte-partie.py t-pr.pgn $R --sans-stockfish \
    --prompt t-modele.txt ; echo $?
printf 'a\n#! si MOTEUR\nb\n#! fin\n' > t-modele.txt
./collecte-partie.py t-pr.pgn $R --sans-stockfish \
    --prompt t-modele.txt 2>&1 | cut -c1-60
printf 'a\n#! si STOCKFISH\nb\n' > t-modele.txt
./collecte-partie.py t-pr.pgn $R --sans-stockfish \
    --prompt t-modele.txt
./collecte-partie.py t-pr.pgn $R --prompt /nulle/part.txt
./collecte-partie.py t-pr.pgn --prompt x --sans-prompt 2>&1 | tail -1
rm -f analyse-t-pr-*
./collecte-partie.py t-pr.pgn $R --sans-stockfish --sans-prompt
ls analyse-t-pr-* | grep -c prompt
```

Attendu, dans l'ordre : "Modèle de prompt `t-modele.txt`, ligne 1 :
valeur inconnue `{{PSEUDO}}`, valeurs admises : VERSION, DEPOT,
ARCHIVE, ...", puis 1 ; "Modèle de prompt `t-modele.txt`, ligne 2 :
condition inconnue MOTEUR" ; "Modèle de prompt `t-modele.txt`, ligne
2 : ce "si" n'est jamais fermé par "fin"" ; "Modèle de prompt
introuvable : /nulle/part.txt" ; "`collecte-partie.py`: error:
`--prompt` et `--sans-prompt` s'excluent" ; enfin le chemin de
l'archive et 0. Les quatre refus ont lieu avant la collecte :
aucun dossier ni archive n'est créé.

### T67

```bash
mkdir t-seul && cp collecte-partie.py t-seul/
rm -f analyse-t-pr-*
t-seul/collecte-partie.py t-pr.pgn $R --sans-stockfish 2> t-pr.log
echo $? ; grep -c 'modèle de prompt introuvable' t-pr.log
ls analyse-t-pr-* | grep -c prompt
```

Attendu : le chemin de l'archive, 0, 1, puis 0. Copié sans son
modèle, le script collecte quand même, sans prompt, et le journal
le signale : "Attention : modèle de prompt introuvable
(.../t-seul/prompt-modele.txt), aucun prompt ne sera écrit. Voir
`--prompt` et `--sans-prompt`."

### T68

Niveau en points Elo, vérifié comme la cadence. Le test passe par
le pilote de pseudo-terminal de T57.

```bash
printf '[joueur]\npseudos = Alice\ncadence = 14 jours\n' > t-niv.ini
printf 'niveau = fort\n' >> t-niv.ini
rm -rf analyse-t-pr-*
python3 t-pty.py "abc|50|9999|1450|||||" t-pr.pgn $P \
    --reglages t-niv.ini | grep -c -E 'lisible|entre 100 et 3500'
grep '^niveau' t-niv.ini
grep -h -E 'niveau :|contient les réponses' analyse-t-pr-*.prompt.txt
printf '[joueur]\npseudos = Bob\ncadence = 14 jours\n' > t-niv.ini
printf 'niveau = inconnu\n' >> t-niv.ini
rm -rf analyse-t-pr-*
./collecte-partie.py t-pr.pgn --sans-explorateur --sans-questions \
    --sans-stockfish --reglages t-niv.ini > /dev/null 2>&1
grep -h -E 'camp dans|niveau :' analyse-t-pr-*.prompt.txt
```

Attendu : 4, soit "Réglages : le niveau enregistré, "fort", n'est
pas lisible, il est redemandé." puis trois fois "Réponse attendue
: un nombre entier entre 100 et 3500, ou Entrée." ; "niveau =
1450" ; "- niveau : environ 1450 Elo, déclaré par le joueur" et
"La section "Consignes d'analyse" contient les réponses du joueur
: ne", le script ayant recueilli les réponses. Enfin, sans niveau
déclaré : "- camp dans cette partie : Noirs" et "- niveau : 1500
Elo, d'après la balise BlackElo de la partie".

### T69

Purge des réglages.

```bash
printf '[joueur]\npseudos = Alice\n' > t-purge.ini ; mkdir t-rep
./collecte-partie.py --purge-reglages --reglages t-purge.ini
echo $? ; ls t-purge.ini
./collecte-partie.py --purge-reglages --reglages t-purge.ini ; echo $?
./collecte-partie.py --purge-reglages --reglages t-rep ; echo $?
ls -d t-rep
```

Attendu : "Réglages supprimés : `t-purge.ini`. Ils seront redemandés
à la prochaine collecte lancée sur un terminal.", 0, et ls ne
trouve plus le fichier ; "Aucun fichier de réglages à supprimer :
`t-purge.ini`", 0 ; "`--purge-reglages` : t-rep n'est pas un fichier,
rien n'est supprimé.", 1, et le répertoire est toujours là. Aucune
partie n'est demandée et la sortie standard reste vide.

## W. Partie d'essai

`test.pgn`, fourni avec le dépôt, réunit dans une seule partie légale ce
qui a déjà fait trébucher un lecteur de PGN : balises accentuées,
commentaire d'avant le premier coup, commentaire de fin de ligne
introduit par un point-virgule, NAG ($6, $5) et signes ?? et ?,
commentaires d'horloge [%clk], variantes emboîtées, mat manqué, prise
en passant, promotion avec prise et échec, les deux roques et un coup
nul. La partie n'a aucun intérêt échiquéen.

### T70

```bash
ARCH=$(./collecte-partie.py test.pgn --sans-explorateur \
    --sans-questions --profondeur 8 --pseudos "zoé blanche" \
    2> t-essai.log)
grep -c Attention t-essai.log
unzip -p "$ARCH" '*/partie.pgn' | cmp - test.pgn ; echo $?
unzip -p "$ARCH" '*/synthese.md' > t-essai.md
grep -E 'demi-coups dans|^- Roque|Black \|' t-essai.md
grep -E '^\| (3|4|9|17|29) \|' t-essai.md | cut -c1-60
grep -c -E '^\| [0-9]+ \| [0-9]+ \| (Blancs|Noirs) ' t-essai.md
grep 'camp dans' "${ARCH%.zip}.prompt.txt"
```

```text
Attendu : 0 ; 0, partie.pgn étant la copie exacte de test.pgn,
commentaires et variantes compris ; "| Black | Müller, Noël |",
"Nombre de demi-coups dans la ligne principale : 36.", "Roque des
Blancs : O-O-O au coup 14 (demi-coup 27)." et "Roque des Noirs :
O-O au coup 7 (demi-coup 14)." ; puis cinq lignes du tableau :
  | 3 | 2 | Blancs | g4 | #-1 | 0/0/100 | mat | gaffe | ...
  | 4 | 2 | Noirs | Nc6 | ... | mat | gaffe | Qh4# (#-1) | ...
  | 9 | 5 | Blancs | gxf6 | ...            la prise en passant
  | 17 | 9 | Blancs | gxf8=Q+ | ...        la promotion
  | 29 | 15 | Blancs | -- | - | - | - | - | ...   le coup nul
puis 36, et "- camp dans cette partie : Blancs", le pseudo étant
reconnu malgré la casse. Les évaluations chiffrées varient d'une
version de Stockfish à l'autre : seules la nature "mat", "gaffe"
des lignes 3 et 4 et les colonnes vides de la ligne 29 sont
attendues telles quelles. Le journal répète "Not
transmitting history with null moves to UCI engine", message de
python-chess sans conséquence.
```

## Nettoyage

```bash
rm -rf /tmp/analyses /tmp/abime /tmp/cat1.tsv /tmp/consignes.md \
    analyse-* t-*
```

