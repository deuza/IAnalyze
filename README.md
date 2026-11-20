[![License: CC0](https://img.shields.io/badge/license-CC0_1.0-lightgrey.svg?style=plastic)](https://creativecommons.org/publicdomain/zero/1.0/)
![Hack The Planet](https://img.shields.io/badge/hack-the--planet-black?style=plastic&logo=Debian&logoColor=white)
![Built With Love](https://img.shields.io/badge/built%20with-%E2%9D%A4%20by%20DeuZa-red?style=plastic)

![GitHub release](https://img.shields.io/github/v/release/deuza/IAnalyze?label=release&style=plastic)
[![GitHub last commit](https://img.shields.io/github/last-commit/deuza/IAnalyze?style=plastic)](https://github.com/deuza/IAnalyze/commits/main)
![GitHub commit activity](https://img.shields.io/github/commit-activity/t/deuza/IAnalyze?style=plastic)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/deuza/IAnalyze?style=plastic)

# IAnalyze - Le dossier d'une partie d'échecs pour un analyste LLM

IAnalyze prépare l'analyse d'une partie d'échecs par un LLM.

Son script, `ianalyze.py`, rassemble le PGN, les statistiques de l'explorateur Lichess, le catalogue des ouvertures et les évaluations de Stockfish, puis écrit deux fichiers : une archive zip et le prompt qui va avec.

*Le script ne produit aucune analyse : il donne à l'analyste des chiffres sûrs, et le prompt lui impose de s'y tenir.*

```bash
./ianalyze.py ma-partie.pgn
```

```text
analyse-ma-partie-20261119-164140.zip
analyse-ma-partie-20261119-164140.prompt.txt
```

Vous collez le contenu du fichier prompt.txt dans une conversation neuve avec Claude, vous joignez le fichier zip et vous recevez un PGN annoté et une synthèse.

**IAnalyze est fait pour Claude.** Pour un autre LLM, l'option `--prompt-seul` écrit un prompt court qui porte la partie et les évaluations de Stockfish, à coller seul, sans pièce jointe : voir la section 10.

| Fichier | Rôle |
|---|---|
| `ianalyze.py` | le script, en un seul fichier |
| `prompt-modele.txt` | le modèle dont est tiré le prompt de chaque partie (section 9) |
| `prompt-seul-modele.txt` | le modèle du prompt court de `--prompt-seul` (section 9) |
| `verifier-analyse.py` | le contrôle du PGN rendu par le LLM (section 10) |
| `test.pgn` | une partie d'essai qui réunit les cas tordus d'un PGN |
| `test-app.sh` | la suite de tests, pour Linux et macOS |
| [`TESTS.md`](TESTS.md) | comment lancer les tests et ce qu'ils vérifient |
| [`CHANGELOG.md`](CHANGELOG.md) | l'historique des versions |

Plateformes : Debian et macOS (Homebrew). Python 3 et python-chess, que le script installe lui-même dans un environnement virtuel dédié.

---

## 1. Présentation

Le script rassemble et met en forme :

- **le PGN** de la partie, lu depuis un fichier local ou téléchargé depuis Lichess
- **les statistiques de l'explorateur Lichess**, position par position, pour situer la sortie de théorie
- **l'évaluation Stockfish** de chaque coup, calculée sur votre machine

La chaîne complète tient en trois temps :

1. `./ianalyze.py ma-partie.pgn`

   Le script collecte, calcule, et écrit deux fichiers : `analyse-<partie>-<date>.zip` et `analyse-<partie>-<date>.prompt.txt`.

2. Dans une conversation neuve avec un LLM, vous collez le contenu du prompt et vous joignez l'archive.

   Si le LLM n'ouvre pas les zip, décompressez l'archive et envoyez-lui tous ses fichiers (voir section 9).

3. Le LLM rend un PGN annoté et une synthèse.

   Il explique, il ne calcule pas : les évaluations viennent de Stockfish, la théorie vient de l'explorateur et du catalogue.

Le prompt est tiré du modèle `prompt-modele.txt`, rangé à côté du script.

Il décrit toujours la synthèse que cette version du script vient d'écrire : les deux ne peuvent pas diverger.

## 2. Prérequis et installation

Tout s'installe dans votre répertoire personnel, sous Debian comme sous macOS.

Seule l'installation des paquets de Debian demande les droits root.

**1. Les paquets**

Sous Debian, en root :

```bash
apt install git python3-venv stockfish
```

Sous macOS, avec Homebrew, dont le Python fournit déjà le module venv :

```bash
brew install git python stockfish
```

**2. Le dépôt**, sous le compte du joueur :

```bash
git clone https://github.com/deuza/IAnalyze.git
```

```bash
cd IAnalyze
```

**3. L'environnement virtuel et le catalogue**, sous le même compte :

```bash
./ianalyze.py --installer-venv
```

```bash
./ianalyze.py --installer-catalogue
```

Chaque joueur de la machine refait les étapes 2 et 3 sous son propre compte : rien n'est partagé, rien n'est à copier.

### Ce que font ces deux commandes

**`--installer-venv`** crée un environnement virtuel dédié et y installe python-chess, que Debian n'empaquette pas.

Le script s'y relance ensuite tout seul : vous continuez à l'appeler avec le Python du système.

**`--installer-catalogue`** télécharge le catalogue des ouvertures nommées de Lichess, gardé en local.

Relancez-la de temps en temps pour le mettre à jour.

**Stockfish est obligatoire** : son évaluation fait partie de toute collecte.

### Emplacements par défaut

Les mêmes sur les deux plateformes, sauf pour le moteur :

| | Emplacement |
|---|---|
| `--venv` | `~/.local/share/IAnalyze/venv` |
| `--catalogue` | `~/.local/share/IAnalyze` |
| réglages | `~/.config/IAnalyze/reglages.ini` |
| jeton | `~/.lichess_token` |
| `--stockfish`, Debian | `/usr/games/stockfish` |
| `--stockfish`, macOS | le binaire trouvé dans le PATH, sinon `/opt/homebrew/bin/stockfish` |

### Jeton Lichess

L'explorateur de Lichess demande un jeton d'accès personnel.

Une fois connecté à Lichess, créez-le sur https://lichess.org/account/oauth/token, sans cocher aucun droit.

Le script le lit dans `~/.lichess_token`, un fichier en mode 600 qui ne contient que le jeton :

```bash
umask 077 ; vi ~/.lichess_token
```

Sans jeton, lancez le script avec `--sans-explorateur`.

### Réglages personnels

Votre pseudo, votre cadence habituelle et votre niveau sont gardés dans `~/.config/IAnalyze/reglages.ini`.

Le script les demande une seule fois, au premier lancement dans un terminal.

Vous pouvez ensuite modifier le fichier à la main, ou le supprimer avec `--purge-reglages` :

```ini
[joueur]
pseudos = MonPseudo, AutrePseudo
cadence = 15+10
niveau = 1300
```

**Le niveau** est un nombre de points Elo approximatifs, de 100 à 3500, ou "inconnu".

Il est transmis à l'analyste, qui y adapte ses explications. Sans lui, c'est l'Elo de votre balise dans la partie qui sert.

**L'annotateur** est une clef facultative, que le script ne demande pas. Elle fixe la balise Annotator du PGN annoté :

```text
annotateur = Claude (Anthropic)
```

Sans elle, le prompt demande à l'analyste d'y mettre son propre nom de modèle.

**La cadence** s'écrit de l'une de ces façons :

| Vous écrivez | Système | Où on le trouve |
|---|---|---|
| `15+10` | temps réel : minutes par joueur, puis incrément en secondes | Lichess |
| `14 jours` | correspondance à délai fixe : jours par coup, rien n'est reporté d'un coup au suivant | Lichess, chess.com |
| `10 coups en 50 jours` | correspondance par période : le temps économisé est reporté | ICCF, cadence standard |
| `5 jours + 36 heures, plafond 20 jours` | correspondance à capital de temps : jours au départ, puis incrément par coup en heures ou en jours, plafond facultatif | chess-mail.com |
| `50 jours + 3 jours, plafond 50 jours, réserve 75 jours` | le même, avec une réserve à côté du capital | ICCF, Triple Block |
| `inconnue` | | |

Les deux systèmes de l'ICCF suivent ses règles en vigueur depuis le 1er janvier 2026, section 2.4.

Le délai fixe par coup, lui, n'existe pas à l'ICCF.

## 3. Utilisation

```bash
./ianalyze.py SOURCE [options]
```

SOURCE accepte trois formes :

```bash
./ianalyze.py ma-partie.pgn                 # PGN local
./ianalyze.py https://lichess.org/<identifiant>  # URL Lichess
./ianalyze.py <identifiant>                      # identifiant
```

**Une URL** doit viser lichess.org et porter l'identifiant en tête de chemin.

L'identifiant est la suite de 8 caractères qui suit `lichess.org/` dans l'adresse de la partie. Les formes `/<id>/black`, `/embed/game/<id>`, `/embed/<id>` et `/game/export/<id>` sont acceptées.

Un autre hôte, ou une autre page du site (étude, analyse, exercices), est refusé sans rien envoyer à Lichess.

**Un identifiant** fait exactement 8 ou 12 caractères alphanumériques.

Une source qui ressemble à un chemin (point, barre oblique ou tilde) et qui n'existe pas est signalée comme fichier introuvable. Un répertoire est refusé, même si son nom a la forme d'un identifiant.

**Un PGN** doit contenir une seule partie, en échecs standard. Un fichier qui en réunit plusieurs est refusé : isolez celle à analyser dans un fichier à part.

Un PGN corrompu est refusé plutôt qu'analysé tronqué. Une partie qui ne part pas de la position initiale, c'est-à-dire qui porte une balise FEN, est refusée elle aussi : IAnalyze analyse une partie entière, du premier coup au dernier. Pour étudier une position, chargez-la dans un échiquier d'analyse.

Les coups doivent être écrits en notation anglaise : K, Q, R, B, N. Une partie notée en français (R, D, T, F, C) ou en figurines est refusée, avec le premier mot qui n'a pas été compris. Sans ce refus, "Cf3" serait lu "f3", un coup de pion, et l'analyse porterait sur une autre partie que la vôtre.

Sont refusés de la même façon :

- un commentaire dont l'accolade n'est jamais fermée
- une variante dont la parenthèse n'est jamais fermée, ou une parenthèse fermante en trop
- du texte libre hors des accolades, après la partie par exemple

Le chemin de l'archive est écrit seul sur la sortie standard, le journal horodaté va sur la sortie d'erreur :

```bash
ARCHIVE=$(./ianalyze.py ma-partie.pgn 2>/dev/null)
```

### Questions de démarrage

Avant la collecte, le script vous pose quelques questions. Entrée retient la valeur proposée.

- **Au tout premier lancement seulement** : votre pseudo, votre cadence habituelle et votre niveau, rangés dans le fichier de réglages.
- **Votre camp**, s'il ne se déduit pas des balises White ou Black grâce à vos pseudos.

  Les balises vides sont alors complétées, et le PGN fourni est conservé sous `partie-origine.pgn`.

- **La cadence de la partie**, si la balise TimeControl ne la donne pas : temps réel, correspondance ou inconnue.

  Entrée retient votre cadence habituelle. Seuls des nombres entiers sont acceptés, une autre réponse fait reposer la question.

- **Quatre questions de contexte** : périmètre, objectif, contexte particulier, commentaires à inclure dans le PGN final.

Le script rédige lui-même la cadence transmise à l'analyste, toujours de la même façon :

```text
rapide, 15 minutes + 10 secondes par coup
correspondance, 14 jours par coup
correspondance, capital de 5 jours + 36 heures par coup, plafonné à 20 jours
```

Les réponses vont dans `contexte.md`, repris en tête de la synthèse sous le titre "Consignes d'analyse".

Une réponse fait 255 caractères au plus. Un nom de joueur ou un pseudo ne peut contenir ni guillemet, ni barre oblique inversée, ni crochet, ni accolade : il part dans une balise du PGN, que ces signes rendraient illisible. Une réponse refusée est redemandée.

### Quand les questions ne sont pas posées

Les questions s'affichent dans le terminal et attendent une réponse au clavier.

Le script ne les pose donc que s'il est lancé à la main, dans un terminal. Il ne demande rien, et retient les valeurs par défaut, dans ces quatre cas :

- vous passez `--sans-questions`
- un autre programme le lance : cron, un script, un service
- son entrée ne vient pas du clavier : `./ianalyze.py ma-partie.pgn < /dev/null`
- son journal ne va pas à l'écran : `./ianalyze.py ma-partie.pgn 2> journal.log`

Le dernier cas surprend : les questions s'écrivent au même endroit que le journal, la sortie d'erreur. Si vous la redirigez, vous ne les verriez pas.

L'exemple plus haut, avec `2>/dev/null`, ne pose donc aucune question. Sans cette redirection, `ARCHIVE=$(./ianalyze.py ma-partie.pgn)` les pose normalement.

Dans la suite, "sans terminal" désigne ces quatre cas.

## 4. Options

### Général

#### `-h, --help`

Affiche l'aide complète et les exemples.

```bash
./ianalyze.py --help
```

#### `--delai S`

*Défaut : `30`*

Délai réseau maximal par requête, en secondes : export PGN,  explorateur, téléchargement du catalogue.

```bash
./ianalyze.py ma-partie.pgn --delai 60
```

#### `--debug`

Laisse remonter la trace complète d'une erreur inattendue, expurgée du jeton.

Sans cette option, seul un message d'une ligne s'affiche.

```bash
./ianalyze.py ma-partie.pgn --debug
```

### Environnement virtuel

#### `--installer-venv`

Crée l'environnement virtuel s'il manque, y installe ou met à jour python-chess, puis quitte. Peut être relancé sans risque.

```bash
./ianalyze.py --installer-venv
```

#### `--venv CHEMIN`

*Défaut : `~/.local/share/IAnalyze/venv`*

Emplacement de l'environnement virtuel, à l'installation comme à l'usage.

```bash
./ianalyze.py --installer-venv --venv /opt/venv/echecs
./ianalyze.py ma-partie.pgn --venv /opt/venv/echecs
```

### Questions de démarrage

#### `--sans-questions`

Ne pose aucune question, ni camp ni contexte. Les valeurs par défaut sont retenues.

```bash
./ianalyze.py ma-partie.pgn --sans-questions
```

#### `--pseudos LISTE`

*Défaut : ceux de vos réglages*

Vos noms de joueur, séparés par des virgules, cherchés sans tenir compte de la casse dans White et Black pour déduire votre camp.

Le premier sert à compléter une balise vide. L'option remplace, le temps d'un lancement, les pseudos du fichier de réglages.

```bash
./ianalyze.py ma-partie.pgn --pseudos MonPseudo,AutrePseudo
```

#### `--reglages FICHIER`

*Défaut : `~/.config/IAnalyze/reglages.ini`*

Fichier de réglages, au format INI, section `[joueur]` : pseudos, cadence et niveau.

- Une clef absente est demandée une seule fois, dans un terminal, puis enregistrée.
- Une clef présente, même vide, n'est jamais redemandée.
- Une cadence ou un niveau illisible est redemandé.
- Les clefs et les sections que vous ajoutez sont conservées.
- Sans terminal, rien n'est demandé ni écrit.

Un fichier mal formé arrête le script avec un message.

```bash
./ianalyze.py ma-partie.pgn --reglages ~/echecs.ini
```

#### `--purge-reglages`

Supprime le fichier de réglages, puis quitte. Aucune partie n'est attendue.

Vos réponses seront redemandées à la prochaine collecte lancée dans un terminal.

Avec `--reglages`, c'est le fichier désigné qui est supprimé. Son répertoire reste en place.

Un fichier absent n'est pas une erreur, un répertoire est refusé.

```bash
./ianalyze.py --purge-reglages
```

### Catalogue des ouvertures

#### `--installer-catalogue`

Télécharge les cinq fichiers du catalogue (`a.tsv` à `e.tsv`), rejoue chaque ligne pour la valider, écrit l'index puis quitte.

Le remplacement est atomique : un échec laisse l'ancien index en place. Relancer l'option fait la mise à jour.

```bash
./ianalyze.py --installer-catalogue
```

#### `--catalogue REP`

*Défaut : `~/.local/share/IAnalyze`*

Répertoire du catalogue local, à l'installation comme à l'usage.

```bash
./ianalyze.py --installer-catalogue --catalogue /srv/cat
./ianalyze.py ma-partie.pgn --catalogue /srv/cat
```

### Sortie

#### `--sortie REP`

*Défaut : `.`*

Répertoire où écrire l'archive, créé au besoin.

```bash
./ianalyze.py ma-partie.pgn --sortie ~/analyses
```

#### `--garder-dossier`

Conserve le dossier de travail à côté de l'archive. Sans cette option, il est supprimé une fois l'archive vérifiée.

```bash
./ianalyze.py ma-partie.pgn --garder-dossier
```

#### `--prompt FICHIER`

*Défaut : `prompt-modele.txt` à côté du script*

Modèle du prompt d'analyse, écrit à côté de l'archive sous le nom `<archive>.prompt.txt` (voir section 9).

Le modèle est contrôlé avant la collecte : un repère inconnu arrête le script en donnant le numéro de la ligne. Un fichier désigné par l'option doit exister.

Si le modèle par défaut manque, parce que le script a été copié seul, la collecte se fait sans prompt et le journal le signale.

```bash
./ianalyze.py ma-partie.pgn --prompt ~/mon-modele.txt
```

#### `--sans-prompt`

N'écrit pas le prompt d'analyse. S'exclut avec `--prompt` et avec `--prompt-seul`.

```bash
./ianalyze.py ma-partie.pgn --sans-prompt
```

#### `--prompt-seul`

Écrit un prompt court, à coller seul dans la conversation, sans pièce jointe : quelques consignes, la partie, puis les évaluations de Stockfish.

C'est le repli pour un LLM qui n'ouvre pas les zip ou n'exécute pas de code (voir section 10). Le PGN annoté lui est demandé dans un bloc de code.

Ce prompt est tiré de `prompt-seul-modele.txt`, et non de `prompt-modele.txt`. L'archive est écrite quand même : `verifier-analyse.py` en a besoin.

S'exclut avec `--sans-prompt`. Avec `--prompt`, le modèle désigné doit placer `{{PARTIE_PGN}}`, sans quoi le script s'arrête avant la collecte.

```bash
./ianalyze.py ma-partie.pgn --prompt-seul
```

### Explorateur

#### `--base {lichess,maitres}`

*Défaut : `lichess`*

Base interrogée :

- `lichess` : les parties classées de tous les joueurs du site, la base de https://lichess.org/opening
- `maitres` : les parties de maîtres

```bash
./ianalyze.py ma-partie.pgn --base maitres
```

#### `--cadences LISTE`

*Défaut : `bullet,blitz,rapid,classical,correspondence`*

Base `lichess` seulement. Cadences retenues, séparées par des virgules, parmi : ultraBullet, bullet, blitz, rapid, classical, correspondence.

La casse est tolérée, les doublons sont retirés.

```bash
./ianalyze.py ma-partie.pgn --cadences rapid,classical,correspondence
```

#### `--classements LISTE`

*Défaut : `1000,1200,1400,1600,1800,2000,2200,2500`*

Base `lichess` seulement. Tranches de classement retenues parmi 0, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2500.

Chaque tranche court de sa valeur à la suivante : 0 couvre 0 à 999 (affichée "400" sur le site), 2500 tout ce qui dépasse.

Une partie est rangée selon la moyenne des classements de ses deux joueurs.

```bash
./ianalyze.py ma-partie.pgn --classements 0,1000
```

Les filtres par défaut, plus la date de début fixée à janvier 2017, reprennent ceux de https://lichess.org/opening : vous y retrouvez les mêmes pourcentages.

#### `--jeton-fichier FICHIER`

*Défaut : `~/.lichess_token`*

Fichier contenant le jeton personnel, et rien d'autre.

```bash
./ianalyze.py ma-partie.pgn --jeton-fichier ~/.jeton-test
```

#### `--seuil-parties N`

*Défaut : `50`*

Arrêt quand la position compte moins de N parties dans la base.

```bash
./ianalyze.py ma-partie.pgn --seuil-parties 200
```

#### `--seuil-frequence P`

*Défaut : `10.0`*

Un coup joué dans moins de P % des parties de la position est rare.

Un coup rare qui mène hors du catalogue des ouvertures est une sortie de théorie. S'il reste dans une ligne nommée, ce n'en est pas une.

0 désactive le critère.

```bash
./ianalyze.py ma-partie.pgn --seuil-frequence 5
./ianalyze.py ma-partie.pgn --seuil-frequence 0
```

#### `--coups-min N`

*Défaut : `6`*

Aucun arrêt sur la fréquence avant la fin du coup N, soit 2N demi-coups.

La table couvre ainsi le début de partie même après une sortie précoce.

Le seuil de parties reste actif, et la première sortie est notée même dans la fenêtre. 0 arrête dès la première sortie.

```bash
./ianalyze.py ma-partie.pgn --coups-min 10
./ianalyze.py ma-partie.pgn --coups-min 0
```

#### `--jusqu-a-epuisement`

Ignore les deux seuils pour l'arrêt : l'interrogation descend tant que la base connaît la position. La première sortie reste notée.

```bash
./ianalyze.py ma-partie.pgn --jusqu-a-epuisement
```

#### `--max-demicoups N`

*Défaut : `60`*

Plafond de demi-coups interrogés, garde-fou toujours actif.

```bash
./ianalyze.py ma-partie.pgn --max-demicoups 30
```

#### `--pause S`

*Défaut : `2.0`*

Pause entre deux requêtes, minimum 2 secondes. Sur un HTTP 429, le script attend 60 secondes et retente une seule fois.

```bash
./ianalyze.py ma-partie.pgn --pause 3
```

#### `--sans-explorateur`

Saute la collecte explorateur : ni réseau vers l'explorateur, ni jeton, ni catalogue requis.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur
```

### Moteur

L'évaluation Stockfish fait partie de toute collecte. Le binaire est vérifié avant toute écriture.

#### `--coups-stockfish N`

*Défaut : `0`*

Limite le moteur aux N premiers coups entiers, soit 2N demi-coups. 0 analyse toute la partie.

```bash
./ianalyze.py ma-partie.pgn --coups-stockfish 15
```

#### `--profondeur D`

*Défaut : `18`*

Profondeur de recherche par position, de 1 à 60. Le temps de calcul croît très vite avec elle : au delà de 60, une seule position occuperait le moteur des heures.

```bash
./ianalyze.py ma-partie.pgn --profondeur 22
```

#### `--multipv K`

*Défaut : `3`*

Nombre de meilleurs coups demandés par position. Si le coup joué n'y figure pas, une seconde analyse fournit son évaluation et son écart.

```bash
./ianalyze.py ma-partie.pgn --multipv 5
```

#### `--fils N`

*Défaut : nombre de processeurs*

Threads Stockfish.

```bash
./ianalyze.py ma-partie.pgn --fils 2
```

#### `--hachage MO`

*Défaut : `256`*

Table de hachage du moteur, en mégaoctets.

```bash
./ianalyze.py ma-partie.pgn --hachage 512
```

#### `--stockfish CHEMIN`

*Défaut : selon la plateforme, voir la section 2*

Binaire du moteur.

```bash
./ianalyze.py ma-partie.pgn --stockfish /usr/local/bin/stockfish
```

#### `--longueur-pv N`

*Défaut : `5`*

Demi-coups de variante principale reproduits dans la synthèse, 0 pour la variante entière.

Les variantes complètes restent dans `stockfish/evaluations.json`.

```bash
./ianalyze.py ma-partie.pgn --longueur-pv 0
```

## 5. Règles de cohérence

Une option sans effet est refusée plutôt qu'ignorée en silence :

- `--cadences` et `--classements` exigent `--base lichess`.
- `--pause` ne descend pas sous 2, `--seuil-frequence` reste entre 0 et 100, `--coups-min`, `--coups-stockfish` et `--longueur-pv` valent 0 ou plus, `--profondeur` va de 1 à 60, les autres valeurs numériques valent au moins 1.
- `--pause` et `--seuil-frequence` refusent nan et inf.
- `--fils`, `--hachage` et `--multipv` sont contrôlés auprès du moteur, qui annonce ses bornes : une valeur qu'il n'admet pas est refusée avant toute requête et avant la création du dossier de travail.

## 6. Explorateur : critères d'arrêt

Pour chaque demi-coup, la position AVANT le coup est interrogée, ce qui donne le rang et la fréquence du coup réellement joué.

L'interrogation s'arrête, dans cet ordre de test :

1. sur une erreur HTTP ou une position absente de la base.
2. sur un échantillon inférieur à `--seuil-parties`.
3. sur une sortie de théorie, hors de la fenêtre `--coups-min`.
4. au plafond `--max-demicoups`, ou à la fin de la partie.

Un coup nul, "--" dans le PGN, arrête aussi l'interrogation, avant toute requête pour ce demi-coup et quel que soit le mode : ce n'est pas un coup des échecs, la base ne peut pas suivre la partie au delà.

Il n'est pas compté comme une sortie de théorie, et la section 4 de la synthèse le signale.

Le catalogue dit "connu", jamais "bon" : "Barnes Opening: Fool's Mate" y figure.

Il compte aussi les positions intermédiaires des lignes nommées, que l'explorateur ne nomme pas lui-même.

## 7. Résultat

Archive : `analyse-<étiquette>-<AAAAMMJJ-HHMMSS>.zip`, l'étiquette étant le nom du PGN sans extension ou l'identifiant Lichess. Un dossier ou une archive homonyme fait ajouter un suffixe -2, -3...

En cas d'échec, le dossier de travail est conservé tel quel pour diagnostic.

L'étiquette est assainie (voir section 8) : le journal l'annonce alors par "Nom du dossier assaini : ..."

Une archive présente sous son nom définitif est toujours complète et vérifiée : elle est écrite sous le nom provisoire `.<dossier>.partiel.zip`, puis renommée.

Il en va de même de chaque fichier du dossier de travail, écrit sous `.<nom>.partiel`. Après une interruption (Ctrl-C) ou un échec, ces fichiers provisoires sont retirés et le dossier de travail reste, sans archive.

Contenu :

| Fichier | Contenu |
|---|---|
| `synthese.md` | la synthèse, que l'analyste lit en premier |
| `partie.pgn` | le PGN, en-têtes complétés s'il y a lieu |
| `partie-origine.pgn` | le PGN fourni, si des en-têtes manquaient |
| `contexte.md` | les réponses aux questions de démarrage |
| `explorateur/NNN-<uci>.json` | une réponse brute par demi-coup interrogé |
| `stockfish/evaluations.json` | les évaluations complètes du moteur, variantes entières |
| `collecte.json` | paramètres exacts de la collecte, sans le jeton. `pgn_encodage` et `pgn_remarques` disent comment le PGN a été décodé, `prompt_ecrit` nomme le prompt |

À côté de l'archive, et non dedans :

```text
analyse-<étiquette>-<AAAAMMJJ-HHMMSS>.prompt.txt
le prompt d'analyse de cette partie, à coller dans la conversation.
Son chemin est donné par le journal, la sortie standard ne porte que celui de l'archive.
```

Sections de `synthese.md` :

| Section | Contenu |
|---|---|
| Consignes d'analyse | `contexte.md`, vos réponses aux questions de démarrage. Absente quand elles ne sont pas posées |
| 1. En-têtes et coups | en-têtes, ligne principale, repères de phase (roques, dames, entrée en finale) |
| 2. Explorateur | filtres, seuils, table, première sortie |
| 3. Évaluations Stockfish | nature et G/N/P de chaque coup |
| 3 bis | variantes principales du moteur |
| 3 ter | erreurs et gaffes par camp, avec la FEN |
| 5 | fichiers de l'archive. Le dossier `explorateur/` n'y figure que s'il existe |
| 4. Positions non exploitables | là où la base ne dit plus rien, ou le demi-coup d'un coup nul |
| 5. Données brutes de l'archive | le contenu du zip, et l'encodage du PGN s'il a été converti |

**Table de l'explorateur**, une ligne par demi-coup :

- demi-coup, numéro du coup, trait
- parties de la position
- coup joué, son rang, sa fréquence, le score des Blancs sur ce coup
- coup majoritaire, sa fréquence et son score
- Ouverture : nom ECO de la position atteinte, "(intermédiaire)" pour une position de passage d'une ligne nommée, "-" hors catalogue

**Table Stockfish**, une ligne par demi-coup :

- demi-coup, numéro du coup, trait, coup joué
- évaluation, du point de vue des Blancs
- G/N/P : chances de gain, de nulle et de perte des Blancs selon le modèle de Stockfish, à lire comme une tendance plutôt que comme une probabilité entre joueurs humains
- écart au premier choix du moteur, du point de vue du joueur au trait
- nature : imprécision à partir de 50 cp d'écart, erreur à partir de 100, gaffe à partir de 300
- les trois meilleurs coups

Trois cas particuliers :

- l'écart porte "mat" quand le coup joué manque un mat ou en concède un : il ne se chiffre pas en centipions
- sous le tableau, une ligne "Résultat et évaluation finale se contredisent" apparaît quand le camp déclaré vainqueur est nettement moins bien après le dernier coup, d'au moins 300 cp : la partie ne s'est pas décidée sur l'échiquier, et l'analyste doit le dire au lieu de raconter une victoire méritée
- un coup nul, "--" dans le PGN, n'est pas évalué : sa ligne garde les trois meilleurs coups de la position, ses autres colonnes portent "-"

Codes de retour :

| Code | Signification |
|---|---|
| 0 | succès |
| 1 | erreur signalée par un message, ou erreur inattendue |
| 2 | option invalide |
| 130 | interruption (Ctrl-C) |

## 8. Encodages et caractères

Aucune entrée mal encodée ne doit arrêter le script sur une trace Python : au pire, une ligne "Attention" du journal et une dégradation propre.

PGN, modèle de prompt et fichier de jeton, essais dans cet ordre :

1. marque d'ordre des octets (BOM) UTF-8, UTF-16 ou UTF-32
2. UTF-16 sans marque, reconnu à son octet nul sur deux
3. UTF-8
4. UTF-8 abîmé : au moins un caractère accentué correctement codé et au plus quatre octets invalides pour chacun d'eux, ces octets deviennent U+FFFD
5. cp1252, puis latin-1, qui accepte n'importe quel octet

Hors UTF-8 sans défaut, le journal nomme l'encodage retenu :

```text
Attention, PGN : le contenu n'est pas en UTF-8, encodage retenu : cp1252.
```

Les fins de ligne CRLF et CR sont ramenées à LF. Les caractères de contrôle, NUL compris, sont retirés et comptés dans le journal, la tabulation et le saut de ligne sont conservés.

Le fichier `partie.pgn` est donc toujours de l'UTF-8 propre : si le fichier fourni a dû être converti, la section 5 de la synthèse le dit, et `collecte.json` garde le détail.

Un texte latin-1 se décode aussi sans erreur en cp1252, les deux ne différant que sur les octets 0x80 à 0x9F : c'est cp1252 qui est annoncé.

Un PGN qui n'est ni en UTF-8, ni en UTF-16, ni en cp1252 est refusé, avec le conseil de le convertir. Le script le reconnaît à l'un des cinq octets que cp1252 ne définit pas.

Limite : un fichier en cp850 ou en MacRoman qui ne contient aucun de ces cinq octets passe pour du cp1252. Ses lettres accentuées sortent fausses dans les noms et les commentaires, et rien ne permet de le voir. Les coups, écrits en ASCII, restent justes.

Balises du PGN (White, Black, Event, Site et les autres) : tabulations et caractères de contrôle en sont retirés avant l'écriture des en-têtes de la synthèse et avant tout affichage.

Autres lectures :

- le fichier de jeton suit la même détection que le PGN, et un jeton hors de l'ASCII imprimable est refusé avant toute requête
- le catalogue et les réponses de l'explorateur sont lus en UTF-8, marque d'ordre des octets tolérée
- la sortie du moteur est décodée en UTF-8 par python-chess, qui écarte une ligne illisible sans s'arrêter

Rien ne dépend de la locale.

Écritures : tous les fichiers de l'archive sont en UTF-8, fins de ligne LF.

Dans l'étiquette de l'archive, les caractères de contrôle, les caractères `/ \ : * ? " < > |` et les octets non décodables du nom du PGN deviennent "\_", et les espaces des tirets : `partie contre machin.pgn` donne `analyse-partie-contre-machin-...`. L'étiquette est bornée à 80 octets.

Espaces et lettres accentuées sont conservés.

Console : un caractère que le terminal ne sait pas afficher devient "?" au lieu d'arrêter le script, sous LANG=C comme avec PYTHONIOENCODING=ascii.

Le chemin de l'archive est écrit en octets sur la sortie standard : ARCHIVE=$(...) reste exact dans tous les cas.

Questions de démarrage : une réponse saisie dans un autre encodage que celui du terminal est redécodée, cp1252 puis latin-1.

## 9. Prompt d'analyse

Les données ne suffisent pas : il faut dire à l'analyste ce qu'il doit en faire. Ce texte vit dans le modèle `prompt-modele.txt`, que vous pouvez modifier librement, sans toucher au script.

À chaque collecte, le script en tire le prompt de la partie : il remplit les valeurs et ne garde que les passages qui s'appliquent.

Deux sortes de repères sont interprétés :

| Repère | Effet |
|---|---|
| `{{NOM}}` | une valeur, remplacée |
| `#! si CONDITION` | garde ce qui suit si la condition est vraie |
| `#! si non CONDITION` | garde ce qui suit si elle est fausse |
| `#! sinon` | bascule |
| `#! fin` | ferme le dernier "si" ouvert |
| `#! note ...` | commentaire du modèle, jamais recopié |

Une directive occupe une ligne entière, et les "si" peuvent s'emboîter. Les lignes vides laissées par un passage retiré sont resserrées.

Valeurs :

| Valeur | Contenu |
|---|---|
| `VERSION` | version du script |
| `DEPOT` | adresse du dépôt d'IAnalyze |
| `ARCHIVE` | nom du fichier de l'archive |
| `PSEUDOS` | vos pseudos, séparés par des virgules |
| `CAMP` | Blancs, Noirs ou inconnu |
| `NIVEAU` | votre niveau, rédigé : "environ 1300 Elo, déclaré par le joueur", sinon l'Elo de votre balise, sinon "non précisé" |
| `CADENCE` | votre cadence habituelle, rédigée |
| `ANNOTATEUR` | valeur de la balise Annotator |
| `BASE` | base interrogée : "Lichess (tous joueurs)" ou "maîtres" |
| `SEUIL_IMPRECISION`, `SEUIL_ERREUR`, `SEUIL_GAFFE` | seuils de nature du coup, en centipions : 50, 100 et 300 |
| `PROFONDEUR`, `MULTIPV` | valeurs de `--profondeur` et de `--multipv` |
| `PARTIE_PGN` | le PGN de la partie, tel que l'archive le contient |
| `TABLEAU_MOTEUR` | les évaluations de Stockfish, une ligne par demi-coup. Derrière un coup faible : sa nature, son écart, le meilleur coup, sa suite sur `--longueur-pv` demi-coups et son évaluation |
| `ALERTE_RESULTAT` | la phrase qui signale un résultat contraire à l'évaluation finale, vide sinon |
| `CONSIGNES_JOUEUR` | celles de vos réponses aux questions de démarrage que vous n'avez pas laissées par défaut |
| `OUVERTURE` | l'ouverture et la sortie de théorie en une phrase, d'après l'explorateur |
| `DEMI_COUPS` | nombre de demi-coups de la partie |
| `DEMI_COUPS_EVALUES` | nombre de demi-coups que le moteur a évalués, plus petit avec `--coups-stockfish` |

Conditions :

| Condition | Vraie quand |
|---|---|
| `STOCKFISH` | toujours, depuis la version 4.0.0. Gardée pour les modèles personnels qui l'emploient |
| `EXPLORATEUR` | la section 2 a été collectée |
| `BASE_LICHESS` | base de tous les joueurs |
| `BASE_MAITRES` | base des maîtres |
| `REPONSES` | le script a recueilli vos réponses aux questions de démarrage |
| `CAMP_CONNU` | votre camp est connu |
| `PSEUDO_CONNU` | au moins un pseudo est connu |
| `NIVEAU_DECLARE` | votre niveau figure dans les réglages |
| `RESULTAT_CONTREDIT` | le résultat de la partie contredit l'évaluation finale |
| `CONSIGNES_DONNEES` | `CONSIGNES_JOUEUR` n'est pas vide |
| `OUVERTURE_CONNUE` | `OUVERTURE` n'est pas vide |
| `COUVERTURE_PARTIELLE` | `--coups-stockfish` a limité le moteur aux premiers coups |
| `COUP_NUL` | la partie contient un coup nul, noté `--` |

Les deux modèles, `prompt-modele.txt` et `prompt-seul-modele.txt`, partagent ces repères. `PARTIE_PGN`, `TABLEAU_MOTEUR`, `ALERTE_RESULTAT`, `CONSIGNES_JOUEUR`, `OUVERTURE` et les conditions `RESULTAT_CONTREDIT`, `CONSIGNES_DONNEES`, `OUVERTURE_CONNUE`, `COUP_NUL` servent au prompt court.

Le prompt suit ce que la collecte a réellement fait. Sans explorateur, il ne demande ni fréquence ni coup majoritaire. Avec `--coups-stockfish`, il dit jusqu'où le moteur a évalué. Avec `--multipv 1`, il n'annonce pas trois coups par position.

Sans terminal, le camp se déduit de vos pseudos sans poser de question.

Un repère inconnu ou mal écrit, comme `{{ NIVEAU }}`, un "si" jamais fermé, une directive mal formée ou un modèle sans une ligne de texte arrêtent le script avant la collecte :

```text
Modèle de prompt prompt-modele.txt, ligne 12 : condition inconnue MOTEUR, conditions admises : STOCKFISH, EXPLORATEUR, ...
```

Le prompt se colle comme un message, dans une conversation neuve, l'archive en pièce jointe. Il vaut pour une partie : c'est le coller à chaque conversation qui garantit qu'il correspond à l'archive.

Tous les LLM n'ouvrent pas un zip, et tous n'exécutent pas de code.

Le prompt prévoit les deux cas :

- **Le LLM n'accepte pas l'archive** : décompressez-la et envoyez-lui **tous** ses fichiers, joints ou collés.

  `--garder-dossier` laisse le dossier décompressé à côté de l'archive.

  Le prompt demande à l'analyste de se servir de tous les fichiers, pas de la seule synthèse : les `.json` portent les variantes entières du moteur et tous les coups connus de l'explorateur, que `synthese.md` résume.

  S'il n'en reçoit qu'une partie, il doit dire lesquels manquent et vous proposer de les envoyer.

- **Le LLM exécute du code** : il construit le PGN avec python-chess et en prouve la légalité.
- **Le LLM n'exécute pas de code** : il écrit le PGN lui-même, le dit, et vous laisse ouvrir le fichier pour confirmer.

## 10. Choisir un LLM et vérifier son travail

### Avec Claude : le zip et le prompt

**IAnalyze est fait pour Claude.** C'est avec lui que la chaîne a été mise au point, et le seul avec lequel elle a rendu un PGN utilisable tel quel dans les essais ci-dessous.

Vous joignez le zip, vous collez le prompt, il rend un fichier PGN.

Cette chaîne complète demande en effet un LLM qui sait :

- ouvrir une archive zip
- exécuter du code et y installer python-chess, pour construire le PGN et en prouver la légalité
- rendre un fichier à télécharger

### Avec un autre LLM : `--prompt-seul`

Pour un LLM qui n'ouvre pas les zip, refuse certaines pièces jointes ou n'exécute pas de code, le script écrit un prompt court :

```bash
./ianalyze.py ma-partie.pgn --prompt-seul
```

Vous collez ce seul texte dans la conversation, sans rien joindre. Le LLM rend le PGN annoté dans un bloc de code, que vous enregistrez vous-même dans un fichier `.pgn`.

L'idée vient de Lucas Chess, dont le prompt d'analyse tient en quelques lignes suivies de la partie. Celui-ci y ajoute les évaluations de Stockfish : une ligne par demi-coup, et derrière chaque coup faible le meilleur coup et sa suite.

Ce qu'il faut savoir de ce mode :

- le prompt pèse environ 5 Ko pour une partie de 25 coups
- il ne porte ni la synthèse ni les fichiers `.json` : le LLM n'a que la partie, le tableau du moteur et, avec l'explorateur, une phrase sur l'ouverture
- l'archive est écrite quand même, gardez-la : `verifier-analyse.py` en a besoin
- **c'est un repli, et il n'a pas encore été essayé** : les essais ci-dessous lui sont antérieurs

La qualité de l'analyse dépend alors du LLM que vous choisissez. Passez toujours son PGN à `verifier-analyse.py --prompt-seul`, décrit plus bas.

Deux conseils tirés des essais :

- certains LLM refusent un fichier `.pgn` en pièce jointe : renommez-le en `.txt`, ou passez à `--prompt-seul`
- si le LLM annonce un fichier que vous ne trouvez pas, demandez-lui le PGN dans un bloc de code

### Essais menés

Un seul essai par LLM, le 20 novembre 2026, sur la même partie de 49 demi-coups, avec le même zip et le même prompt, celui de la version 4.0.0 avant les consignes et l'option `--prompt-seul` que ces essais ont fait ajouter.

**Ce n'est pas un classement.** Un essai ne dit rien de la régularité d'un modèle, et les offres ne sont pas comparables : un abonnement d'un côté, trois offres gratuites de l'autre.

| LLM, tel qu'il se nomme lui-même | Offre | PGN rendu | Bilan de `verifier-analyse.py` |
|---|---|---|---|
| Claude Opus 5.5 (Anthropic) | abonnement | oui, construit avec python-chess | aucun échec : 24 erreurs et gaffes commentées sur 24, 27 variantes jouables |
| GPT-6 (OpenAI) | gratuite | oui, écrit à la main, python-chess n'ayant pas pu être installé | 3 échecs : une ligne vide arrête la lecture, les 25 variantes sont dans les commentaires, un NAG contredit le moteur |
| M365 Copilot (Microsoft) | gratuite | oui, la partie sans aucun commentaire | 3 échecs : il dit n'avoir trouvé que trois fichiers dans l'archive, et ne commente rien |
| Gemini (Google), version non relevée | gratuite | non | il annonce un fichier qui n'existe pas, puis perd le fil de la conversation |

Ce que ces essais montrent :

- **Les données tiennent partout.** Aucun des quatre n'a inventé une évaluation, et tous donnent les trois mêmes erreurs principales, avec les bons écarts.
- **C'est la fabrication du PGN qui les sépare.** Seul le LLM qui a construit son fichier avec python-chess a rendu un PGN utilisable tel quel.
- **Le fond peut être bon sous une forme fautive.** Les 25 variantes écrites à la main par GPT-6 étaient toutes légales et tirées des lignes du moteur.
- **La partie était notée gagnée dans une position perdue.** Deux LLM sur quatre ont raconté une victoire méritée, d'où la ligne ajoutée à la synthèse (section 7).

L'offre gratuite de Claude annonce elle aussi la création de fichiers et l'exécution de code, sur d'autres modèles que celui de l'essai, d'après [sa page de tarifs](https://claude.com/pricing) lue le 20 novembre 2026. Elle n'a pas été essayée.

### Vérifier le PGN rendu

Un LLM peut rendre un PGN qui a l'air juste et ne l'est pas : un coup illégal dans une variante, un chiffre arrangé, une gaffe passée sous silence.

`verifier-analyse.py` compare le PGN rendu à l'archive que le LLM a reçue, et sort le même bilan pour chaque LLM essayé.

```bash
./verifier-analyse.py analyse-ma-partie-20261119-164140.zip analyse-llm.pgn
```

Copiez la conversation dans un fichier texte pour faire contrôler aussi les positions et les évaluations qu'elle cite :

```bash
./verifier-analyse.py analyse-ma-partie-20261119-164140.zip analyse-llm.pgn --synthese conversation.txt --nom "Nom du modèle"
```

Si le LLM n'a rendu aucun PGN, mettez un tiret à la place du fichier :

```bash
./verifier-analyse.py analyse-ma-partie-20261119-164140.zip - --synthese conversation.txt
```

Pour un PGN obtenu avec le prompt court de `--prompt-seul`, ajoutez la même option :

```bash
./verifier-analyse.py analyse-ma-partie-20261119-164140.zip analyse-llm.pgn --prompt-seul
```

Le prompt court demande moins que le prompt complet. Avec cette option, les contrôles qu'il ne fonde pas sont sautés : lignes de 79 caractères, résumé avant le premier coup, NAG, `%`, tiret cadratin, notation suffixe, balises Annotator et PlyCount. Restent la lecture, la ligne principale, les accolades, les balises recopiées, le marqueur de fin, les erreurs et gaffes commentées, les évaluations citées et les variantes.

Le script accepte le zip ou son dossier décompressé, et se relance tout seul dans l'environnement virtuel d'IAnalyze, à son emplacement par défaut.

### Ce qui est contrôlé

| Contrôle | Défauts relevés |
|---|---|
| Lecture | fichier hors UTF-8, coup illégal dans la partie ou dans une variante, ligne vide dans le corps de la partie |
| Ligne principale | différente de la partie d'origine |
| Format | ligne de plus de 79 caractères, accolade ouvrante ou fermante dans un commentaire, `%`, tiret cadratin, notation suffixe, balises absentes ou dans le désordre, marqueur de fin |
| Coups commentés | erreur ou gaffe de Stockfish laissée sans commentaire, NAG de position contraire à l'évaluation du moteur |
| Évaluations | chiffre cité qui n'existe nulle part dans les données du moteur |
| Variantes | variante écrite à l'intérieur d'un commentaire, donc non jouable, variante illégale ou trop longue |
| Conversation | FEN invalide ou étrangère à la partie, tiret cadratin |

Deux de ces défauts viennent de vrais PGN de LLM et méritent une explication :

- **La ligne vide dans le corps de la partie.** python-chess y voit la fin de la partie et n'en lit pas la suite. Le script la relève où qu'elle soit, même si elle ne cache qu'une variante ou le marqueur de fin, puis poursuit ses contrôles sur le fichier une fois la ligne retirée.
- **La variante écrite entre accolades.** Ce n'est que du texte, SCID ne la rejoue pas. Le script la rejoue lui-même pour dire si elle est légale et si elle vient d'une ligne du moteur.

### Lire le bilan

| Repère | Sens |
|---|---|
| `OK` | conforme |
| `ECHEC` | contraire à une consigne impérative du prompt |
| `ATTENTION` | à regarder de près, sans être forcément fautif |
| `INFO` | mesure donnée pour comparer les LLM entre eux |

Code de retour : 0 sans `ECHEC`, 1 avec au moins un `ECHEC`, 2 si un fichier ne peut pas être lu ou si l'archive n'est pas celle d'IAnalyze. Avec le code 2, aucun contrôle n'a eu lieu.

### Ce que le script ne fait pas

Il ne juge pas la qualité du commentaire. Une explication fausse mais bien formée passe : un LLM peut placer une dame sur la mauvaise case dans une phrase sans qu'aucun contrôle ne le voie. Cette lecture reste la vôtre.

Trois limites à connaître :

- une évaluation arrondie à une décimale est acceptée : "+0.35" cité "+0.4" ou "+0.3" ne compte pas comme inventé
- un nombre écrit sans signe, "7.77", n'est pas pris pour une évaluation : le script le confondrait avec une durée ou un classement. Un chiffre inventé écrit ainsi passe donc
- le script repère un chiffre qui n'existe nulle part, pas un vrai chiffre attribué au mauvais coup

## 11. Jeton

Le jeton n'est transmis que dans l'en-tête Authorization, jamais dans l'URL. Il n'apparaît ni dans le journal, ni dans l'archive, où `collecte.json` note seulement sa présence.

Il n'est envoyé qu'à l'adresse de l'explorateur : si celui-ci répondait par une redirection, elle ne serait pas suivie, et l'interrogation s'arrêterait là.

Un fichier de jeton lisible par d'autres déclenche un avertissement. Le fichier ne porte que le jeton : une affectation, `LICHESS_TOKEN=...`, ou des guillemets sont refusés.

Le fichier peut porter une marque d'ordre des octets ou être en UTF-16, comme en produisent certains éditeurs Windows : le journal le signale et le jeton est lu normalement.

## 12. Sources et liens

Ce que le script interroge :

- Jeton d'accès personnel : https://lichess.org/account/oauth/token, une fois connecté à Lichess

- Explorateur, base de tous les joueurs : `https://explorer.lichess.org/lichess`
- Explorateur, base des maîtres : `https://explorer.lichess.org/masters`
- Catalogue des ouvertures : [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings), fichiers `a.tsv` à `e.tsv`. Ce sont ceux que charge aussi le serveur de l'explorateur.

Ce sur quoi il s'appuie :

- [python-chess](https://python-chess.readthedocs.io/en/latest/), la bibliothèque qui lit le PGN et pilote le moteur
- [Stockfish](https://stockfishchess.org/), le moteur
- [Spécification PGN](https://www.saremba.de/chessgml/standards/pgn/pgn-complete.htm), Steven J. Edwards, 1994

D'où viennent les cadences :

- Catégories du temps réel : [Speed.scala](https://raw.githubusercontent.com/lichess-org/scalachess/master/core/src/main/scala/Speed.scala), dans [scalachess](https://github.com/lichess-org/scalachess), la bibliothèque de règles de Lichess
- Correspondance, ICCF : [ICCF Rules, en vigueur depuis le 1er janvier 2026](https://webfiles.iccf.com/rules/2026/2026%20ICCF%20Rules%2C%20260311.pdf), section 2.4 (PDF, en anglais)
- Correspondance, capital de temps : [règlement de chess-mail.com](https://www.chess-mail.com/index.php?page=reg)

Conventions du dépôt :

- [Tenez un Changelog](https://keepachangelog.com/fr/1.1.0/) pour `CHANGELOG.md`
- [Gestion sémantique de version](https://semver.org/lang/fr/) pour les numéros de version
- [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/deed.fr) pour la licence

---

## Licences

- Catalogue des ouvertures de Lichess (chess-openings) : CC0. Il est téléchargé à l'installation, pas distribué avec ce dépôt.
- python-chess, installé dans l'environnement virtuel : GPL-3.0-or-later.
- Stockfish, installé par votre système : GPL-3.0.
- Tout le contenu de ce dépôt est en CC0 : faites-en ce que vous voulez :)

<p align="center">With ❤️ by <a href="https://github.com/deuza">DeuZa</a></p>
