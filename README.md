[![License: CC0](https://img.shields.io/badge/license-CC0_1.0-lightgrey.svg?style=plastic)](https://creativecommons.org/publicdomain/zero/1.0/)
![Hack The Planet](https://img.shields.io/badge/hack-the--planet-black?style=plastic&logo=Debian&logoColor=white)
![Built With Love](https://img.shields.io/badge/built%20with-%E2%9D%A4%20by%20DeuZa-red?style=plastic)

![GitHub release](https://img.shields.io/github/v/release/deuza/IAnalyze?label=release&style=plastic)
[![GitHub last commit](https://img.shields.io/github/last-commit/deuza/IAnalyze?style=plastic)](https://github.com/deuza/IAnalyze/commits/main)
![GitHub commit activity](https://img.shields.io/github/commit-activity/t/deuza/IAnalyze?style=plastic)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/deuza/IAnalyze?style=plastic)

# IAnalyze - Le dossier d'une partie d'échecs pour un analyste LLM

IAnalyze prépare l'analyse d'une partie d'échecs par un LLM. 

Son script, `collecte-partie.py`, rassemble le PGN, les statistiques de l'explorateur Lichess, le catalogue des ouvertures et les évaluations de Stockfish, puis écrit deux fichiers : une archive zip et le prompt qui va avec.

*Le script ne produit aucune analyse : il donne à l'analyste des chiffres sûrs, et le prompt lui impose de s'y tenir.*

```bash
./collecte-partie.py ma-partie.pgn
```

```text
analyse-ma-partie-20261119-164140.zip
analyse-ma-partie-20261119-164140.prompt.txt
```

Vous collez le contenu du fichier prompt.txt dans une conversation neuve avec le LLM de votre choix, vous joignez le fichier zip et vous recevez un PGN annoté et une synthèse.

| Fichier | Rôle |
|---|---|
| `collecte-partie.py` | le script, en un seul fichier |
| `prompt-modele.txt` | le modèle dont est tiré le prompt de chaque partie (section 9) |
| `test.pgn` | une partie d'essai qui réunit les cas tordus d'un PGN |
| `test-app.sh` | la suite de tests, pour Linux et macOS |
| [`TESTS.md`](TESTS.md) | le plan de tests, commande par commande |
| [`CHANGELOG.md`](CHANGELOG.md) | l'historique des versions |

Plateformes : Debian et macOS (Homebrew). Python 3 et python-chess, que le script installe lui-même dans un environnement virtuel dédié.

---

## 1. Présentation

Le script rassemble et met en forme :

- **le PGN** de la partie, lu depuis un fichier local ou téléchargé depuis Lichess
- **les statistiques de l'explorateur Lichess**, position par position, pour situer la sortie de théorie
- **l'évaluation Stockfish** de chaque coup, calculée sur votre machine

La chaîne complète tient en trois temps :

1. `./collecte-partie.py ma-partie.pgn`

   Le script collecte, calcule, et écrit deux fichiers : `analyse-<partie>-<date>.zip` et `analyse-<partie>-<date>.prompt.txt`.

2. Dans une conversation neuve avec un LLM, vous collez le contenu du prompt et vous joignez l'archive.

   Si le LLM n'ouvre pas les zip, décompressez l'archive et envoyez-lui tous ses fichiers (voir section 9).

3. Le LLM rend un PGN annoté et une synthèse.

   Il explique, il ne calcule pas : les évaluations viennent de Stockfish, la théorie vient de l'explorateur et du catalogue.

Le prompt est tiré du modèle `prompt-modele.txt`, rangé à côté du script.

Il décrit toujours la synthèse que cette version du script vient d'écrire : les deux ne peuvent pas diverger.

## 2. Prérequis et installation

### Debian

L'installation se fait **en root**, depuis `/root`, une fois pour toute la machine :

```bash
apt install git python3-venv stockfish
```

```bash
git clone https://github.com/deuza/IAnalyze.git
```

```bash
cd IAnalyze
```

```bash
./collecte-partie.py --installer-venv
```

```bash
./collecte-partie.py --installer-catalogue
```

Le joueur n'a pas besoin des droits root pour s'en servir.

Copiez le dépôt dans son répertoire personnel et donnez-lui en la propriété, `joueur` étant ici son nom de compte :

```bash
cp -r /root/IAnalyze /home/joueur/IAnalyze
```

```bash
chown -R joueur:joueur /home/joueur/IAnalyze
```

Le joueur lance ensuite le script depuis `/home/joueur/IAnalyze`, sous son propre compte.

Son jeton et ses réglages vont dans son répertoire personnel, pas dans celui de root.

### macOS

Rien ne demande les droits root, tout va dans votre répertoire personnel.

Avec Homebrew, dont le Python fournit déjà le module venv :

```bash
brew install git python stockfish
```

```bash
git clone https://github.com/deuza/IAnalyze.git
```

```bash
cd IAnalyze
```

```bash
./collecte-partie.py --installer-venv
```

```bash
./collecte-partie.py --installer-catalogue
```

### Ce que font ces deux commandes

**`--installer-venv`** crée un environnement virtuel dédié et y installe python-chess, que Debian n'empaquette pas.

Le script s'y relance ensuite tout seul : vous continuez à l'appeler avec le Python du système.

**`--installer-catalogue`** télécharge le catalogue des ouvertures nommées de Lichess, gardé en local.

Relancez-la de temps en temps pour le mettre à jour.

**Stockfish est obligatoire** : son évaluation fait partie de toute collecte.

### Emplacements par défaut

| | Debian | macOS |
|---|---|---|
| `--venv` | `/opt/venv/lichess` | `~/.local/share/IAnalyze/venv` |
| `--catalogue` | `/usr/local/share/IAnalyze` | `~/.local/share/IAnalyze` |
| `--stockfish` | `/usr/games/stockfish` | le binaire trouvé dans le PATH, sinon `/opt/homebrew/bin/stockfish` |
| jeton | `~/.lichess_token` | `~/.lichess_token` |
| réglages | `~/.config/IAnalyze/reglages.ini` | `~/.config/IAnalyze/reglages.ini` |

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
./collecte-partie.py SOURCE [options]
```

SOURCE accepte trois formes :

```bash
./collecte-partie.py ma-partie.pgn                 # PGN local
./collecte-partie.py https://lichess.org/xvoiNy2C  # URL Lichess
./collecte-partie.py xvoiNy2C                      # identifiant
```

**Une URL** doit viser lichess.org et porter l'identifiant en tête de chemin.

Les formes `/xvoiNy2C/black`, `/embed/game/<id>`, `/embed/<id>` et `/game/export/<id>` sont acceptées.

Un autre hôte, ou une autre page du site (étude, analyse, exercices), est refusé sans rien envoyer à Lichess.

**Un identifiant** fait exactement 8 ou 12 caractères alphanumériques.

Une source qui ressemble à un chemin (point, barre oblique ou tilde) et qui n'existe pas est signalée comme fichier introuvable.

**Un PGN** n'est traité que pour sa première partie, en échecs standard uniquement.

Un PGN corrompu est refusé plutôt qu'analysé tronqué. Une partie qui ne part pas de la position initiale est traitée sans explorateur.

Le chemin de l'archive est écrit seul sur la sortie standard, le journal horodaté va sur la sortie d'erreur :

```bash
ARCHIVE=$(./collecte-partie.py ma-partie.pgn 2>/dev/null)
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

### Quand les questions ne sont pas posées

Les questions s'affichent dans le terminal et attendent une réponse au clavier.

Le script ne les pose donc que s'il est lancé à la main, dans un terminal. Il ne demande rien, et retient les valeurs par défaut, dans ces quatre cas :

- vous passez `--sans-questions`
- un autre programme le lance : cron, un script, un service
- son entrée ne vient pas du clavier : `./collecte-partie.py ma-partie.pgn < /dev/null`
- son journal ne va pas à l'écran : `./collecte-partie.py ma-partie.pgn 2> journal.log`

Le dernier cas surprend : les questions s'écrivent au même endroit que le journal, la sortie d'erreur. Si vous la redirigez, vous ne les verriez pas.

L'exemple plus haut, avec `2>/dev/null`, ne pose donc aucune question. Sans cette redirection, `ARCHIVE=$(./collecte-partie.py ma-partie.pgn)` les pose normalement.

Dans la suite, "sans terminal" désigne ces quatre cas.

## 4. Options

### Général

#### `-h, --help`

Affiche l'aide complète et les exemples.

```bash
./collecte-partie.py --help
```

#### `--delai S`

*Défaut : `30`*

Délai réseau maximal par requête, en secondes : export PGN,  explorateur, téléchargement du catalogue.

```bash
./collecte-partie.py ma-partie.pgn --delai 60
```

#### `--debug`

Laisse remonter la trace complète d'une erreur inattendue, expurgée du jeton.    
Sans cette option, seul un message d'une ligne s'affiche.

```bash
./collecte-partie.py ma-partie.pgn --debug
```

### Environnement virtuel

#### `--installer-venv`

Crée l'environnement virtuel s'il manque, y installe ou met à jour python-chess, puis quitte. Peut être relancé sans risque.

```bash
./collecte-partie.py --installer-venv
```

#### `--venv CHEMIN`

*Défaut : selon la plateforme, voir la section 2*

Emplacement de l'environnement virtuel, à l'installation comme à l'usage.

```bash
./collecte-partie.py --installer-venv --venv /opt/venv/echecs
./collecte-partie.py ma-partie.pgn --venv /opt/venv/echecs
```

### Questions de démarrage

#### `--sans-questions`

Ne pose aucune question, ni camp ni contexte. Les valeurs par défaut sont retenues.

```bash
./collecte-partie.py ma-partie.pgn --sans-questions
```

#### `--pseudos LISTE`

*Défaut : ceux de vos réglages*

Vos noms de joueur, séparés par des virgules, cherchés sans tenir compte de la casse dans White et Black pour déduire votre camp.    
Le premier sert à compléter une balise vide. L'option remplace, le temps d'un lancement, les pseudos du fichier de réglages.

```bash
./collecte-partie.py ma-partie.pgn --pseudos MonPseudo,AutrePseudo
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
./collecte-partie.py ma-partie.pgn --reglages ~/echecs.ini
```

#### `--purge-reglages`

Supprime le fichier de réglages, puis quitte. Aucune partie n'est attendue.

Vos réponses seront redemandées à la prochaine collecte lancée dans un terminal.

Avec `--reglages`, c'est le fichier désigné qui est supprimé. Son répertoire reste en place.

Un fichier absent n'est pas une erreur, un répertoire est refusé.

```bash
./collecte-partie.py --purge-reglages
```

### Catalogue des ouvertures

#### `--installer-catalogue`

Télécharge les cinq fichiers du catalogue (`a.tsv` à `e.tsv`), rejoue chaque ligne pour la valider, écrit l'index puis quitte. 

Le remplacement est atomique : un échec laisse l'ancien index en place. Relancer l'option fait la mise à jour.

```bash
./collecte-partie.py --installer-catalogue
```

#### `--catalogue REP`

*Défaut : selon la plateforme, voir la section 2*

Répertoire du catalogue local, à l'installation comme à l'usage.

```bash
./collecte-partie.py --installer-catalogue --catalogue /srv/cat
./collecte-partie.py ma-partie.pgn --catalogue /srv/cat
```

### Sortie

#### `--sortie REP`

*Défaut : `.`*

Répertoire où écrire l'archive, créé au besoin.

```bash
./collecte-partie.py ma-partie.pgn --sortie ~/analyses
```

#### `--consignes FICHIER`

Insère tel quel un fichier texte ou Markdown en tête de la synthèse, sous le titre "Consignes d'analyse".

Il remplace alors les questions de contexte.

```bash
./collecte-partie.py ma-partie.pgn --consignes ~/annotation.md
```

#### `--garder-dossier`

Conserve le dossier de travail à côté de l'archive. Sans cette option, il est supprimé une fois l'archive vérifiée.

```bash
./collecte-partie.py ma-partie.pgn --garder-dossier
```

#### `--prompt FICHIER`

*Défaut : `prompt-modele.txt` à côté du script*

Modèle du prompt d'analyse, écrit à côté de l'archive sous le nom `<archive>.prompt.txt` (voir section 9). 

Le modèle est contrôlé avant la collecte : un repère inconnu arrête le script en donnant le numéro de la ligne. Un fichier désigné par l'option doit exister.

Si le modèle par défaut manque, parce que le script a été copié seul, la collecte se fait sans prompt et le journal le signale.

```bash
./collecte-partie.py ma-partie.pgn --prompt ~/mon-modele.txt
```

#### `--sans-prompt`

N'écrit pas le prompt d'analyse. S'exclut avec `--prompt`.

```bash
./collecte-partie.py ma-partie.pgn --sans-prompt
```

### Explorateur

#### `--base {lichess,maitres}`

*Défaut : `lichess`*

Base interrogée :

- `lichess` : les parties classées de tous les joueurs du site, la base de https://lichess.org/opening
- `maitres` : les parties de maîtres

```bash
./collecte-partie.py ma-partie.pgn --base maitres
```

#### `--cadences LISTE`

*Défaut : `bullet,blitz,rapid,classical,correspondence`*

Base `lichess` seulement. Cadences retenues, séparées par des virgules, parmi : ultraBullet, bullet, blitz, rapid, classical, correspondence.

La casse est tolérée, les doublons sont retirés.

```bash
./collecte-partie.py ma-partie.pgn --cadences rapid,classical,correspondence
```

#### `--classements LISTE`

*Défaut : `1000,1200,1400,1600,1800,2000,2200,2500`*

Base `lichess` seulement. Tranches de classement retenues parmi 0, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2500.

Chaque tranche court de sa valeur à la suivante : 0 couvre 0 à 999 (affichée "400" sur le site), 2500 tout ce qui dépasse.

Une partie est rangée selon la moyenne des classements de ses deux joueurs.

```bash
./collecte-partie.py ma-partie.pgn --classements 0,1000
```

Les filtres par défaut, plus la date de début fixée à janvier 2017, reprennent ceux de https://lichess.org/opening : vous y retrouvez les mêmes pourcentages.

#### `--jeton-fichier FICHIER`

*Défaut : `~/.lichess_token`*

Fichier contenant le jeton personnel, et rien d'autre.

```bash
./collecte-partie.py ma-partie.pgn --jeton-fichier ~/.jeton-test
```

#### `--seuil-parties N`

*Défaut : `50`*

Arrêt quand la position compte moins de N parties dans la base.

```bash
./collecte-partie.py ma-partie.pgn --seuil-parties 200
```

#### `--seuil-frequence P`

*Défaut : `10.0`*

Un coup joué dans moins de P % des parties de la position est rare.

Un coup rare qui mène hors du catalogue des ouvertures est une sortie de théorie. S'il reste dans une ligne nommée, ce n'en est pas une.

0 désactive le critère.

```bash
./collecte-partie.py ma-partie.pgn --seuil-frequence 5
./collecte-partie.py ma-partie.pgn --seuil-frequence 0
```

#### `--coups-min N`

*Défaut : `6`*

Aucun arrêt sur la fréquence avant la fin du coup N, soit 2N demi-coups.

La table couvre ainsi le début de partie même après une sortie précoce.

Le seuil de parties reste actif, et la première sortie est notée même dans la fenêtre. 0 arrête dès la première sortie.

```bash
./collecte-partie.py ma-partie.pgn --coups-min 10
./collecte-partie.py ma-partie.pgn --coups-min 0
```

#### `--jusqu-a-epuisement`

Ignore les deux seuils pour l'arrêt : l'interrogation descend tant que la base connaît la position. La première sortie reste notée.

```bash
./collecte-partie.py ma-partie.pgn --jusqu-a-epuisement
```

#### `--max-demicoups N`

*Défaut : `60`*

Plafond de demi-coups interrogés, garde-fou toujours actif.

```bash
./collecte-partie.py ma-partie.pgn --max-demicoups 30
```

#### `--pause S`

*Défaut : `2.0`*

Pause entre deux requêtes, minimum 2 secondes. Sur un HTTP 429, le script attend 60 secondes et retente une seule fois.

```bash
./collecte-partie.py ma-partie.pgn --pause 3
```

#### `--sans-explorateur`

Saute la collecte explorateur : ni réseau vers l'explorateur, ni jeton, ni catalogue requis.

```bash
./collecte-partie.py ma-partie.pgn --sans-explorateur
```

### Moteur

L'évaluation Stockfish fait partie de toute collecte. Le binaire est vérifié avant toute écriture.

#### `--coups-stockfish N`

*Défaut : `0`*

Limite le moteur aux N premiers coups entiers, soit 2N demi-coups. 0 analyse toute la partie.

```bash
./collecte-partie.py ma-partie.pgn --coups-stockfish 15
```

#### `--profondeur D`

*Défaut : `18`*

Profondeur de recherche par position.

```bash
./collecte-partie.py ma-partie.pgn --profondeur 22
```

#### `--multipv K`

*Défaut : `3`*

Nombre de meilleurs coups demandés par position. Si le coup joué n'y figure pas, une seconde analyse fournit son évaluation et son écart.

```bash
./collecte-partie.py ma-partie.pgn --multipv 5
```

#### `--fils N`

*Défaut : nombre de processeurs*

Threads Stockfish.

```bash
./collecte-partie.py ma-partie.pgn --fils 2
```

#### `--hachage MO`

*Défaut : `256`*

Table de hachage du moteur, en mégaoctets.

```bash
./collecte-partie.py ma-partie.pgn --hachage 512
```

#### `--stockfish CHEMIN`

*Défaut : selon la plateforme, voir la section 2*

Binaire du moteur.

```bash
./collecte-partie.py ma-partie.pgn --stockfish /usr/local/bin/stockfish
```

#### `--longueur-pv N`

*Défaut : `5`*

Demi-coups de variante principale reproduits dans la synthèse, 0 pour la variante entière.   
Les variantes complètes restent dans `stockfish/evaluations.json`.

```bash
./collecte-partie.py ma-partie.pgn --longueur-pv 0
```

## 5. Règles de cohérence

Une option sans effet est refusée plutôt qu'ignorée en silence :

- `--cadences` et `--classements` exigent `--base lichess`.
- `--pause` ne descend pas sous 2, `--seuil-frequence` reste entre 0 et 100, `--coups-min` et `--coups-stockfish` valent 0 ou plus, les autres valeurs numériques au moins 1.
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
| Consignes d'analyse | `contexte.md`, ou le fichier de `--consignes` |
| 1. En-têtes et coups | en-têtes, ligne principale, repères de phase (roques, dames, entrée en finale) |
| 2. Explorateur | filtres, seuils, table, première sortie |
| 3. Évaluations Stockfish | nature et G/N/P de chaque coup |
| 3 bis | variantes principales du moteur |
| 3 ter | erreurs et gaffes par camp, avec la FEN |
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

Deux cas particuliers :

- l'écart porte "mat" quand le coup joué manque un mat ou en concède un : il ne se chiffre pas en centipions
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

PGN et fichier de consignes, essais dans cet ordre :

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

Limite : un texte latin-1 se décode aussi sans erreur en cp1252, les deux ne différant que sur les octets 0x80 à 0x9F. C'est donc cp1252 qui est annoncé, sauf si le fichier contient l'un des cinq octets que cp1252 ne définit pas.

Balises du PGN (White, Black, Event, Site et les autres) : tabulations et caractères de contrôle en sont retirés avant l'écriture des en-têtes de la synthèse et avant tout affichage.

Autres lectures :

- le fichier de jeton suit la même détection que le PGN, et un jeton hors de l'ASCII imprimable est refusé avant toute requête
- le catalogue et les réponses de l'explorateur sont lus en UTF-8, marque d'ordre des octets tolérée
- la sortie du moteur est décodée en UTF-8 par python-chess, qui écarte une ligne illisible sans s'arrêter

Rien ne dépend de la locale.

Écritures : tous les fichiers de l'archive sont en UTF-8, fins de ligne LF.    
Dans l'étiquette de l'archive, les caractères de contrôle, les caractères `/ \ : * ? " < > |` et les octets non décodables du nom du PGN deviennent "\_". L'étiquette est bornée à 80 caractères.   
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

Conditions :

| Condition | Vraie quand |
|---|---|
| `STOCKFISH` | toujours, depuis la version 4.0.0. Gardée pour les modèles personnels qui l'emploient |
| `EXPLORATEUR` | la section 2 a été collectée |
| `BASE_LICHESS` | base de tous les joueurs |
| `BASE_MAITRES` | base des maîtres |
| `REPONSES` | le script a recueilli vos réponses aux questions de démarrage |
| `CONSIGNES_LIBRES` | un fichier a été passé par `--consignes` |
| `CAMP_CONNU` | votre camp est connu |
| `PSEUDO_CONNU` | au moins un pseudo est connu |
| `NIVEAU_DECLARE` | votre niveau figure dans les réglages |

Sans terminal, le camp se déduit de vos pseudos sans poser de question.

Un repère inconnu, un "si" jamais fermé ou une directive mal formée arrêtent le script avant la collecte :

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

## 10. Jeton

Le jeton n'est transmis que dans l'en-tête Authorization, jamais dans l'URL. Il n'apparaît ni dans le journal, ni dans l'archive, où `collecte.json` note seulement sa présence.    

Un fichier de jeton lisible par d'autres déclenche un avertissement.

Le fichier peut porter une marque d'ordre des octets ou être en UTF-16, comme en produisent certains éditeurs Windows : le journal le signale et le jeton est lu normalement.

## 11. Sources et liens

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
