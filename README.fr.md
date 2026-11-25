[![License: CC0](https://img.shields.io/badge/license-CC0_1.0-lightgrey.svg?style=plastic)](https://creativecommons.org/publicdomain/zero/1.0/)
![Hack The Planet](https://img.shields.io/badge/hack-the--planet-black?style=plastic&logo=Debian&logoColor=white)
![Built With Love](https://img.shields.io/badge/built%20with-%E2%9D%A4%20by%20DeuZa-red?style=plastic)

![GitHub release](https://img.shields.io/github/v/release/deuza/IAnalyze?label=release&style=plastic)
[![GitHub last commit](https://img.shields.io/github/last-commit/deuza/IAnalyze?style=plastic)](https://github.com/deuza/IAnalyze/commits/main)
![GitHub commit activity](https://img.shields.io/github/commit-activity/t/deuza/IAnalyze?style=plastic)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/deuza/IAnalyze?style=plastic)

# IAnalyze

English version: [README.md](README.md)

IAnalyze prépare l'analyse d'une partie d'échecs par un LLM *(désigné comme l'analyste dans la suite de ce document)*.

Il y ajoute les évaluations de Stockfish : une ligne par demi-coup, et derrière chaque coup faible le meilleur coup et sa suite.\
Son script, `ianalyze.py`, rassemble le PGN, les statistiques de l'explorateur Lichess, le catalogue des ouvertures et les évaluations de Stockfish, puis écrit deux fichiers : une archive zip et le prompt qui va avec.

L'idée vient du programme [Lucas Chess](https://lucaschess.pythonanywhere.com/), dont le prompt d'analyse tient en quelques lignes suivies de la partie.

*Le script ne produit aucune analyse : il donne à l'analyste des chiffres sûrs, et le prompt lui impose de s'y tenir.*

```bash
./ianalyze.py my-game.pgn
```

```text
analysis-my-game-20261125-142017.zip
analysis-my-game-20261125-142017.prompt.txt
```

Vous collez le contenu du fichier prompt.txt dans une conversation neuve avec Claude, vous joignez le fichier zip, et vous recevez un PGN annoté et une synthèse.

**IAnalyze est fait pour Claude :**\
Avec un compte gratuit, ou pour un autre LLM, l'option `--prompt-only` écrit un prompt court qui porte la partie et les évaluations de Stockfish, à coller seul, sans pièce jointe : voir la section 7.

Un outil supplémentaire, `verify-analysis.py`, contrôle le PGN que le LLM vous a rendu : voir la section 8.

Plateformes : Debian et macOS (Homebrew).\
Python 3.10 ou plus récent, et python-chess, que le script installe lui-même dans un environnement virtuel dédié.

Le script, ses messages, l'archive et le prompt sont en anglais depuis la version 5.0.0, et l'analyse est demandée en anglais. La documentation tient en quatre fichiers, chacun en anglais et en français :

- [README.md](README.md), pour installer IAnalyze et analyser une partie, dont ce fichier est la traduction
- [EXAMPLES.fr.md](EXAMPLES.fr.md), l'aide-mémoire : toutes les commandes, toutes les options, et ce que le terminal affiche, version française d'[EXAMPLES.md](EXAMPLES.md)
- [TECHNICAL.fr.md](TECHNICAL.fr.md), pour le fonctionnement du script, son emploi depuis un autre programme, et le détail des fichiers produits, version française de [TECHNICAL.md](TECHNICAL.md)
- [TESTS.fr.md](TESTS.fr.md), pour lancer les tests et savoir ce que chacun vérifie, version française de [TESTS.md](TESTS.md)

## Sommaire

- [1. Présentation](#1-présentation)
- [2. Prérequis et installation](#2-prérequis-et-installation)
- [3. Utilisation](#3-utilisation)
- [4. Options courantes](#4-options-courantes)
- [5. Résultat](#5-résultat)
- [6. Prompt d'analyse](#6-prompt-danalyse)
- [7. Choisir un LLM](#7-choisir-un-llm)
- [8. Vérifier le PGN rendu](#8-vérifier-le-pgn-rendu)
- [9. Sources et liens](#9-sources-et-liens)
- [Licences](#licences)

---

## 1. Présentation

Le script rassemble et met en forme :

- **le PGN** de la partie, lu depuis un fichier local ou téléchargé depuis Lichess
- **les statistiques de l'explorateur Lichess**, position par position, pour situer la sortie de théorie
- **l'évaluation Stockfish** de chaque coup, calculée sur votre machine

La chaîne complète tient en trois temps :

1. `./ianalyze.py my-game.pgn`

   Le script collecte, calcule, et écrit deux fichiers : `analysis-<partie>-<date>.zip` et `analysis-<partie>-<date>.prompt.txt`.

2. Dans une conversation neuve avec un LLM, vous collez le contenu du prompt et vous joignez l'archive.

   Si le LLM n'ouvre pas les zip, décompressez l'archive et envoyez-lui tous ses fichiers (voir la section 6).

3. Le LLM rend un PGN annoté et une synthèse.

   Il explique, il ne calcule pas : les évaluations viennent de Stockfish, la théorie vient de l'explorateur et du catalogue.

Le prompt est tiré du modèle `prompt-template.txt`, rangé à côté du script.\
Il décrit toujours la synthèse que cette version du script vient d'écrire : les deux ne peuvent pas diverger.

Les fichiers du dépôt :

| Fichier | Rôle |
|---|---|
| `ianalyze.py` | le script, en un seul fichier |
| `prompt-template.txt` | le modèle dont est tiré le prompt de chaque partie (section 6) |
| `prompt-only-template.txt` | le modèle du prompt court de `--prompt-only` (section 7) |
| `verify-analysis.py` | l'outil supplémentaire qui contrôle le PGN rendu par le LLM (section 8) |
| [`EXAMPLES.md`](EXAMPLES.md) | l'aide-mémoire : commandes, options et sorties, en anglais |
| [`TECHNICAL.md`](TECHNICAL.md) | la documentation technique, en anglais |
| [`TESTS.md`](TESTS.md) | les tests : comment les lancer, ce que chacun vérifie, en anglais |
| [`CHANGELOG.md`](CHANGELOG.md) | l'historique des versions |
| [`README.md`](README.md) | ce README, en anglais |
| [`EXAMPLES.fr.md`](EXAMPLES.fr.md) | l'aide-mémoire, en français |
| [`TECHNICAL.fr.md`](TECHNICAL.fr.md) | la documentation technique, en français |
| [`TESTS.fr.md`](TESTS.fr.md) | les tests, en français |
| [`LICENSE`](LICENSE) | la licence du code (voir Licences) |
| `test-app.sh`, `test.pgn` | la suite de tests et sa partie d'essai, décrites dans [TESTS.fr.md](TESTS.fr.md) |
| `example-games/` | les parties et les fichiers des exemples d'[EXAMPLES.fr.md](EXAMPLES.fr.md), dont une vraie partie anonymisée pour un premier essai |

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
./ianalyze.py --install-venv
```

```bash
./ianalyze.py --install-catalog
```

Chaque joueur de la machine refait les étapes 2 et 3 sous son propre compte : rien n'est partagé, rien n'est à copier.

### Ce que font ces deux commandes

**`--install-venv`** crée un environnement virtuel dédié et y installe python-chess, que Debian n'empaquette pas.\
Le script s'y relance ensuite tout seul : vous continuez à l'appeler avec le Python du système.

**`--install-catalog`** télécharge le catalogue des ouvertures nommées de Lichess, gardé en local.\
Relancez-la de temps en temps pour le mettre à jour.

**Stockfish est obligatoire** : son évaluation fait partie de toute collecte.

### Emplacements par défaut

Les mêmes sur les deux plateformes, sauf pour le moteur.

Tout ce que le script crée pour lui-même reste dans le dossier de l'application : supprimer ce dossier ne laisse rien derrière, hors votre jeton.

Le dossier `local/` ne garde que ce que le script sait refaire seul, l'environnement virtuel et le catalogue : le vider remet l'application à neuf sans toucher à vos réglages.

| | Emplacement |
|---|---|
| `--venv` | `local/venv`, dans le dossier de l'application |
| `--catalog` | `local/`, dans le dossier de l'application |
| réglages | `settings.ini`, à la racine du dossier de l'application, comme tout autre fichier de réglages nommé par `--settings` |
| jeton | `~/.lichess_token` |
| `--stockfish`, Debian | `/usr/games/stockfish` |
| `--stockfish`, macOS | le binaire trouvé dans le PATH, sinon `/opt/homebrew/bin/stockfish` |

Jusqu'à la version 4.0.2, l'environnement virtuel et le catalogue étaient rangés dans `~/.local/share/IAnalyze`, les réglages dans `~/.config/IAnalyze`.

Le script ne les y lit plus : relancez `--install-venv` et `--install-catalog`, puis supprimez ces deux répertoires. Vos réglages vous seront redemandés au premier lancement dans un terminal.

### Jeton Lichess

L'explorateur de Lichess demande un jeton d'accès personnel.

Une fois connecté à Lichess, créez-le sur <https://lichess.org/account/oauth/token>, sans cocher aucun droit.\
Le script le lit dans `~/.lichess_token`, un fichier qui ne contient que le jeton et que vous seul pouvez lire.

Créez le fichier vide, fermez-en l'accès, puis collez-y le jeton :

```bash
touch ~/.lichess_token
```

```bash
chmod 600 ~/.lichess_token
```

```bash
vi ~/.lichess_token
```

*Utilisez `nano` si vous ne connaissez pas `vi`, ou l'éditeur de votre choix.*

Dans cet ordre, le jeton n'est à aucun moment dans un fichier lisible par d'autres.\
Le script ne l'affiche jamais, ne l'écrit dans aucun des fichiers qu'il produit, et ne le reçoit pas en ligne de commande.\
Il vous prévient si le fichier est lisible par d'autres que vous.

Sans jeton, lancez le script avec `--no-explorer`.

### Réglages personnels

Votre pseudo, votre cadence habituelle et votre niveau sont gardés dans `settings.ini`, à la racine du dossier de l'application.

Le script les demande une seule fois, au premier lancement dans un terminal.

```ini
[player]
usernames = MyUsername, OtherUsername
time_control = 15+10
rating = 1300
```

Vous pouvez modifier ce fichier à la main, ou le supprimer avec `--purge-settings` : vos réponses seront alors redemandées.

**Le niveau** est un nombre de points Elo approximatifs, de 100 à 3500, ou "unknown".

Il est transmis à l'analyste, qui y adapte ses explications. Sans lui, c'est l'Elo de votre balise dans la partie qui sert.

**La cadence** s'écrit `15+10` pour le temps réel, minutes par joueur puis incrément en secondes, et `14 days` pour la correspondance à délai fixe.

**Un autre joueur** de la même machine garde ses réglages dans un fichier à lui, nommé par `--settings` : `--settings joueur2.ini`. L'option prend un nom de fichier en `.ini`, rangé dans le dossier de l'application à côté de `settings.ini`, jamais un chemin. Dans un terminal, un nom dont le fichier n'existe pas encore n'est créé qu'après confirmation : une faute de frappe ne lance pas un nouveau fichier.

**Pour un seul lancement** qui laisse vos réglages de côté, la partie d'un ami par exemple, `--no-settings` ne lit ni n'écrit aucun fichier de réglages.

Les autres formes de correspondance, la clef facultative `annotator` et la façon dont le script réécrit ce fichier sont décrites dans [TECHNICAL.fr.md](TECHNICAL.fr.md), section 6.

## 3. Utilisation

```bash
./ianalyze.py SOURCE [options]
```

SOURCE accepte trois formes :

```bash
./ianalyze.py my-game.pgn                        # PGN local
./ianalyze.py https://lichess.org/<identifiant>  # URL Lichess
./ianalyze.py <identifiant>                      # identifiant
```

L'identifiant est la suite de 8 caractères qui suit `lichess.org/` dans l'adresse de la partie, ou de 12 dans l'adresse de la partie vue d'un camp.

**Le PGN doit contenir une seule partie, entière, en échecs standard, notée en anglais** : K, Q, R, B, N.

**Lichess est la source de référence d'IAnalyze** : le script y télécharge une partie par son adresse ou son identifiant, et c'est son explorateur qui fournit les statistiques d'ouverture.

Les exports de ces sites et logiciels ont été essayés, et passent tels quels :

| Source | Particularité de son export |
|---|---|
| Lichess | aucune. Avec l'analyse du site, ses commentaires, ses variantes et ses horloges sont lus eux aussi |
| Chess.com | aucune |
| chess-mail.com | notation longue (`Ng1f3`), résultat écrit deux fois en fin de fichier : le second est ignoré, et le journal le dit |
| ajedrezmail.org | un coup par ligne |
| Lucas Chess | durées et horloges en commentaires |

Une partie de chacun est dans le répertoire `example-games`, anonymisée. Lichess en a deux : `game-lichess-org.pgn`, l'export simple, et `commented-game.pgn`, l'export avec l'analyse du site.

Le script refuse plutôt que d'analyser de travers :

- un fichier qui réunit plusieurs parties : isolez celle à analyser dans un fichier à part
- une partie qui ne part pas de la position initiale, c'est-à-dire qui porte une balise FEN : pour étudier une position, chargez-la dans un échiquier d'analyse
- une partie notée en français (R, D, T, F, C) ou en figurines : sans ce refus, "Cf3" serait lu "f3", un coup de pion, et l'analyse porterait sur une autre partie que la vôtre
- un PGN abîmé : accolade ou parenthèse jamais fermée, texte libre hors des accolades

Le message d'erreur nomme ce qui est refusé. Les formes d'adresse acceptées et le détail de ces contrôles sont dans [TECHNICAL.fr.md](TECHNICAL.fr.md), section 4.

### Les questions du script

Avant la collecte, le script vous pose quelques questions, en anglais.\
*Entrée retient la valeur proposée.*

- **Au tout premier lancement seulement** : votre pseudo, votre cadence habituelle et votre niveau, rangés dans le fichier de réglages.
- **Votre camp**, s'il ne se déduit pas des balises White ou Black grâce à vos pseudos.

  Les balises vides sont alors complétées, et le PGN fourni est conservé sous `game-original.pgn`.

- **La cadence de la partie**, si la balise TimeControl ne la donne pas : temps réel, correspondance ou inconnue.

  Entrée retient votre cadence habituelle. Seuls des nombres entiers sont acceptés, une autre réponse fait reposer la question.

- **Quatre questions de contexte** : périmètre, objectif, contexte particulier, commentaires à inclure dans le PGN final.

Le script rédige lui-même la cadence transmise à l'analyste, toujours de la même façon :

```text
rapid, 15 minutes + 10 seconds per move
correspondence, 14 days per move
correspondence, clock of 5 days + 36 hours per move, maximum of 20 days
```

Une réponse fait 255 caractères au plus.\
Un nom de joueur ou un pseudo ne peut contenir ni guillemet, ni barre oblique inversée, ni crochet, ni accolade : il part dans une balise du PGN, que ces signes rendraient illisible.

Une réponse refusée est redemandée.

Pour lancer une collecte sans répondre à rien, ajoutez `--no-questions`.\
Le prompt dit alors au LLM que vos réponses n'ont pas été recueillies, et c'est lui qui vous les demande avant d'analyser.

Le script ne pose pas non plus ses questions quand il n'est pas lancé à la main dans un terminal, depuis un autre programme par exemple : voir [TECHNICAL.fr.md](TECHNICAL.fr.md), section 5.

## 4. Options courantes

Quelques options suffisent à la plupart des usages :

| Option | Effet |
|---|---|
| `--no-explorer` | pas de statistiques d'ouverture : ni jeton ni catalogue ne sont demandés |
| `--no-questions` | aucune question : le LLM vous les posera lui-même |
| `--prompt-only` | un prompt court à coller seul, sans archive, pour un compte gratuit ou un LLM qui n'ouvre pas les zip (section 7) |
| `--keep-folder` | garde le dossier décompressé à côté de l'archive |
| `--output-dir REP` | écrit les fichiers dans le répertoire REP |
| `--database masters` | interroge la base des maîtres au lieu de celle de tous les joueurs de Lichess |
| `--depth D` | profondeur de calcul de Stockfish, 18 par défaut : plus elle est grande, plus le calcul est long |
| `--stockfish-moves N` | limite le moteur aux N premiers coups |
| `--usernames LISTE` | vos pseudos, pour cette seule collecte |
| `--settings NOM` | un autre fichier de réglages, par son nom, dans le dossier de l'application : un profil par joueur |
| `--no-settings` | ne lit ni n'écrit aucun fichier de réglages, pour ce seul lancement |

```bash
./ianalyze.py my-game.pgn --no-explorer --output-dir ~/analyses
```

Toutes les options sont dans [EXAMPLES.fr.md](EXAMPLES.fr.md), chacune avec sa commande et ce que le terminal affiche.\
`./ianalyze.py --help` en donne le résumé.

## 5. Résultat

Archive : `analysis-<étiquette>-<AAAAMMJJ-HHMMSS>.zip`, l'étiquette étant le nom du PGN sans extension, ou l'identifiant Lichess.\
Un dossier ou une archive homonyme fait ajouter un suffixe -2, -3...

En cas d'échec, le dossier de travail est conservé tel quel pour diagnostic.

L'étiquette est assainie (voir [TECHNICAL.fr.md](TECHNICAL.fr.md), section 11) : le journal l'annonce alors par "Folder name sanitized: ..."

Contenu :

| Fichier | Contenu |
|---|---|
| `summary.md` | la synthèse, que l'analyste lit en premier |
| `game.pgn` | le PGN, en-têtes complétés s'il y a lieu |
| `game-original.pgn` | le PGN fourni, si des en-têtes manquaient |
| `context.md` | les réponses aux questions de démarrage |
| `explorer/NNN-<uci>.json` | une réponse brute par demi-coup interrogé |
| `stockfish/evaluations.json` | les évaluations complètes du moteur, variantes entières |
| `collection.json` | les paramètres exacts de la collecte, sans le jeton. `pgn_encoding` et `pgn_remarks` disent comment le PGN a été décodé, `prompt_written` nomme le prompt |

À côté de l'archive, et non dedans :

```text
analysis-<étiquette>-<AAAAMMJJ-HHMMSS>.prompt.txt
```

C'est le prompt d'analyse de cette partie, à coller dans la conversation.\
Son chemin est donné par le journal ; la sortie standard ne porte que celui de l'archive.

Avec `--prompt-only`, il n'y a pas d'archive : la sortie standard porte le chemin du prompt.

Le contenu de chacun de ces fichiers est détaillé dans [TECHNICAL.fr.md](TECHNICAL.fr.md), section 10.

## 6. Prompt d'analyse

Les données ne suffisent pas : il faut dire à l'analyste ce qu'il doit en faire.\
Ce texte vit dans le modèle `prompt-template.txt`, que vous pouvez modifier librement, sans toucher au script.

À chaque collecte, le script en tire le prompt de la partie : il remplit les valeurs et ne garde que les passages qui s'appliquent.

Pour écrire votre propre modèle, la liste des repères, des valeurs et des conditions est dans [TECHNICAL.fr.md](TECHNICAL.fr.md), section 12.

Le prompt suit ce que la collecte a réellement fait. Sans explorateur, il ne demande ni fréquence ni coup majoritaire.\
Avec `--stockfish-moves`, il dit jusqu'où le moteur a évalué. Avec `--multipv 1`, il n'annonce pas trois coups par position.

Le prompt se colle comme un message, dans une conversation neuve, l'archive en pièce jointe.\
Il vaut pour une partie : c'est le coller à chaque conversation qui garantit qu'il correspond à l'archive.

Tous les LLM n'ouvrent pas un zip, et tous n'exécutent pas de code.

Le prompt prévoit les deux cas :

- **Le LLM n'accepte pas l'archive** : décompressez-la et envoyez-lui **tous** ses fichiers, joints ou collés.

  `--keep-folder` laisse le dossier décompressé à côté de l'archive.

  Le prompt demande à l'analyste de se servir de tous les fichiers, pas de la seule synthèse : les `.json` portent les variantes entières du moteur et tous les coups connus de l'explorateur, que `summary.md` résume.

  S'il n'en reçoit qu'une partie, il doit dire lesquels manquent et vous demander de les envoyer.

- **Le LLM exécute du code** : il construit le PGN avec python-chess et en prouve la légalité.
- **Le LLM n'exécute pas de code** : il écrit le PGN lui-même, le dit, et vous laisse ouvrir le fichier pour confirmer.

## 7. Choisir un LLM

**Optez pour Claude** : c'est le conseil de ce dépôt, et il vient des essais décrits plus bas.

Avec le zip, Claude est le seul qui ait rendu un PGN utilisable tel quel.\
Avec le prompt court, avec un abonnement comme avec un compte gratuit, c'est lui qui a rendu les PGN les plus propres, et ses explications sont celles qui ont le mieux tenu à la vérification sur l'échiquier.

IAnalyze a été mis au point avec lui par l'auteur, qui l'utilise pour analyser ses parties.\
Deux routes mènent à une analyse, et il est le premier choix sur les deux :

| Route | Ce que vous envoyez | Ce qu'il faut au LLM | Ce que vous recevez |
|---|---|---|---|
| Le zip et le prompt | l'archive en pièce jointe, le prompt collé | ouvrir un zip, exécuter du code, rendre un fichier | un fichier PGN construit avec python-chess, appuyé sur toutes les données |
| `--prompt-only` | un seul texte collé, sans pièce jointe | une simple conversation | le PGN annoté dans un bloc de code |

**Avec un compte gratuit, prenez `--prompt-only` et Claude. Choisissez le modèle `Sonnet 5.5` avec l'effort `Max`.**\
C'est la combinaison qui a donné le meilleur résultat sans rien payer.

Ces essais ont été menés avec la version 4.0, dont les prompts étaient en français. Les prompts anglais de la version 5.0.0 ne les ont pas encore repassés.

### Avec le zip et le prompt

C'est la chaîne complète : vous joignez le zip, vous collez le prompt, le LLM rend un fichier PGN.\
Il dispose alors de toutes les données : la synthèse, les trois meilleurs coups du moteur à chaque position, les statistiques de l'explorateur.

Cette chaîne demande un LLM qui sait :

- Ouvrir une archive zip
- Exécuter du code et y installer python-chess, pour construire le PGN et en prouver la légalité
- Rendre un fichier à télécharger

Dans les essais, seul Claude l'a menée au bout correctement.

Deux conseils si vous l'essayez avec un autre LLM :

- Certains refusent un fichier `.pgn` en pièce jointe : renommez-le en `.txt`, ou passez à `--prompt-only`.
- Si le LLM annonce un fichier que vous ne trouvez pas, demandez-lui le PGN dans un bloc de code.

### Avec `--prompt-only`

Pour un compte gratuit, ou pour un LLM qui n'ouvre pas les zip, refuse certaines pièces jointes ou n'exécute pas de code, le script écrit un prompt court :

```bash
./ianalyze.py my-game.pgn --prompt-only
```

Vous collez ce seul texte dans la conversation, sans rien joindre.\
Le LLM rend le PGN annoté dans un bloc de code, que vous enregistrez vous-même dans un fichier `.pgn`.

Ce qu'il faut savoir de ce mode :

- Le prompt pèse environ 4 Ko pour `game-lichess-org.pgn`, 39 demi-coups, et 11 Ko pour `commented-game.pgn`, 49 demi-coups : chaque coup faible y ajoute son meilleur coup et sa suite
- Il ne porte ni la synthèse ni les fichiers `.json` : le LLM n'a que la partie, le tableau du moteur et, avec l'explorateur, une phrase sur l'ouverture
- Aucune archive n'est écrite, le prompt est le seul fichier produit
- Les cinq réponses essayées ont rendu la partie entière, tous les coups commentés, sans une évaluation inventée

Pour contrôler le PGN rendu avec `verify-analysis.py --prompt-only` (section 8), ajoutez `--keep-folder` à la collecte : le vérificateur a besoin des évaluations qui ont servi au prompt.

### Fiez-vous aux chiffres, vérifiez les récits

C'est ce que les deux séries d'essais ont en commun.

**Les chiffres tiennent.** Aucun LLM n'a inventé une évaluation, avec le zip comme avec le prompt court.\
Ce qui vient du tableau du moteur est recopié fidèlement : les écarts, les meilleurs coups, leurs suites.

**Les récits sont fragiles.**\
Ce que le LLM déduit seul de la position peut être faux : un sacrifice qui n'en est pas un, une pièce en prise que personne ne signale, un mat en un qui est un mat en deux.

Quand un commentaire vous surprend, posez les pièces et regardez.\
Le script `verify-analysis.py` contrôle la forme du PGN et les chiffres cités, il ne juge pas ce qui est raconté.

### Essais menés

Deux séries, un seul essai par LLM et par offre, une partie par série.

**Ce n'est pas un banc d'essai.**\
Un essai ne dit rien de la régularité d'un modèle. Mais les deux séries vont dans le même sens, et le conseil de cette section ne s'appuie sur rien d'autre que ce qui a été vu.

#### Le 20 novembre 2026, avec le zip et le prompt

Une partie de 49 demi-coups, le même zip et le même prompt pour tous, celui de la version 4.0.0, avant les consignes et l'option `--prompt-seul`, aujourd'hui `--prompt-only`, que ces essais ont fait ajouter.

| LLM, tel qu'il se nomme lui-même | Offre | PGN rendu | Bilan de `verify-analysis.py` |
|---|---|---|---|
| Claude Opus 5.5 (Anthropic) | abonnement | oui, construit avec python-chess | aucun échec : 24 erreurs et gaffes commentées sur 24, 27 variantes jouables |
| GPT-6 (OpenAI) | gratuite | oui, écrit à la main, python-chess n'ayant pas pu être installé | 3 échecs : une ligne vide arrête la lecture, les 25 variantes sont dans les commentaires, un NAG contredit le moteur |
| M365 Copilot (Microsoft) | gratuite | oui, la partie sans aucun commentaire | 3 échecs : il dit n'avoir trouvé que trois fichiers dans l'archive, et ne commente rien |
| Gemini (Google), version non relevée | gratuite | non | il annonce un fichier qui n'existe pas, puis perd le fil de la conversation |

Ce que cette série montre :

- **Les données tiennent partout.** Aucun des quatre n'a inventé une évaluation, et tous donnent les trois mêmes erreurs principales, avec les bons écarts.
- **C'est la fabrication du PGN qui les sépare.** Seul le LLM qui a construit son fichier avec python-chess a rendu un PGN utilisable tel quel.
- **Le fond peut être bon sous une forme fautive.** Les 25 variantes écrites à la main par GPT-6 étaient toutes légales et tirées des lignes du moteur.
- **La partie était notée gagnée dans une position perdue.** Deux LLM sur quatre ont raconté une victoire méritée, d'où la ligne ajoutée à la synthèse (voir [TECHNICAL.fr.md](TECHNICAL.fr.md), section 10).

L'offre gratuite de Claude annonce elle aussi la création de fichiers et l'exécution de code, sur d'autres modèles que celui de cet essai, d'après [sa page de tarifs](https://claude.com/pricing), lue le 20 novembre 2026 et de nouveau le 25 novembre 2026.

Elle n'a pas été essayée avec le fichier zip.

#### Le 21 novembre 2026, avec `--prompt-seul`, aujourd'hui `--prompt-only`

Une partie de 39 demi-coups, gagnée par le joueur, et le même prompt court collé seul dans cinq conversations. C'est `example-games/game-lichess-org.pgn`.\
Le tableau du moteur y marque dix coups faibles, dont deux du joueur.

Les cinq réponses ont en commun l'essentiel :

- La ligne principale est recopiée sans un coup changé
- Les 39 demi-coups sont commentés, toutes les erreurs et gaffes du tableau comprises
- 126 évaluations sont citées dans les PGN, toutes tirées du tableau

Ce qui les sépare :

| LLM | Offre | Forme du PGN | Sur l'échiquier |
|---|---|---|---|
| Claude Sonnet 5.5 (Anthropic) | abonnement | conforme : bloc de code, balises intactes, 10 suites jouables sur 10 | aucune erreur trouvée |
| Claude Sonnet 5.5 (Anthropic), effort Max | gratuite | conforme, de même | une erreur : une case de fuite annoncée au roi alors qu'elle est battue |
| ChatGPT (OpenAI), version non relevée | gratuite | les suites sont écrites dans les commentaires, aucune n'est jouable. Dix suffixes `?!` ou `??` ajoutés aux coups, cinq balises HTML dans les commentaires | un sacrifice qui n'en est pas un, le mauvais cavalier nommé sur une prise, un mat en un annoncé pour un mat en deux |
| Gemini (Google), version non relevée | gratuite | 7 suites jouables sur 10. Il parle du joueur à la troisième personne, puis écrit deux fois "erreur de ma part" à sa place | le même faux sacrifice, la couleur des fous inversée sur trois coups, une colonne annoncée ouverte qui ne l'est pas |
| Copilot (Microsoft), version non relevée | gratuite | pas de bloc de code : la balise Site est rendue sous la forme d'un lien HTML. 10 suites jouables sur 10 | le même faux sacrifice, et un cavalier laissé en prise que rien ne signale |

Les erreurs de la dernière colonne ont été vérifiées une à une sur la position, avec python-chess. **La liste n'est pas exhaustive.**

Ce que cette série montre :

- **Le prompt court fait le travail.** Sans pièce jointe et sans exécution de code, les cinq réponses sont lisibles et leurs chiffres sont justes. C'est mieux que ce que la chaîne complète avait donné la veille chez les trois autres LLM.
- **Claude est devant sur les deux offres.** Ses deux PGN sont conformes, et ses explications sont celles qui résistent le mieux à la vérification : aucune erreur trouvée d'un côté, une seule de l'autre. Le compte gratuit fait presque jeu égal avec l'abonnement, en deux fois plus long : 1968 mots de commentaires contre 943.
- **Le même piège a pris trois LLM sur quatre.** Un fou prend un pion en h7 avec échec, défendu par sa dame : le roi ne peut pas le reprendre. ChatGPT, Gemini et Copilot parlent de sacrifice. Claude écrit, dans l'essai du compte gratuit, "ici il n'y a aucun sacrifice, le pion tombe gratuitement".
- **Demander trois erreurs en fait inventer une.** Le joueur n'en avait commis que deux. ChatGPT, Gemini et Copilot en ont présenté une troisième, Claude a répondu les deux fois qu'il n'y en avait que deux. Les deux prompts donnent désormais le nombre réel de coups faibles du joueur (voir [TECHNICAL.fr.md](TECHNICAL.fr.md), section 12).
- **Le vérificateur n'aurait presque rien vu.** En mode `--prompt-only`, il contrôle les balises, la ligne principale et les chiffres cités. Les suites écrites dans le texte, les balises HTML et les récits faux passent : c'est à vous de les relire.

## 8. Vérifier le PGN rendu

`verify-analysis.py` est un outil supplémentaire, indépendant de la collecte : il contrôle ce que le LLM vous a rendu.

Un LLM peut rendre un PGN qui a l'air juste et ne l'est pas : un coup illégal dans une variante, un chiffre arrangé, une gaffe passée sous silence.\
`verify-analysis.py` compare le PGN rendu à l'archive que le LLM a reçue, et sort le même rapport pour chaque LLM essayé.

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip llm-annotated.pgn
```

Copiez la conversation dans un fichier texte pour faire contrôler aussi les positions et les évaluations qu'elle cite :

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip llm-annotated.pgn --summary llm-conversation.txt --name "Nom du modèle"
```

Si le LLM n'a rendu aucun PGN, mettez un tiret à la place du fichier :

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip - --summary llm-conversation.txt
```

Pour un PGN obtenu avec le prompt court de `--prompt-only`, ajoutez la même option, et donnez le dossier de travail gardé par `--keep-folder` :

```bash
./ianalyze.py my-game.pgn --prompt-only --keep-folder
```

```bash
./verify-analysis.py analysis-my-game-20261125-142017 llm-annotated.pgn --prompt-only
```

Le prompt court demande moins que le prompt complet. Avec cette option, les contrôles qu'il ne demande pas sont sautés : lignes de 79 caractères, résumé avant le premier coup, NAG, `%`, tiret cadratin, notation suffixe, balises Annotator et PlyCount, longueur des variantes, nombre de FEN. Restent la lecture, la ligne principale, les accolades, les balises recopiées, le marqueur de fin, les erreurs et gaffes commentées, les évaluations citées et les variantes.

Si vous avez convenu avec le LLM d'un périmètre, les 20 premiers coups par exemple, le script le lit dans votre réponse à la question de démarrage et n'attend aucun commentaire au-delà.\
Quand le périmètre a été fixé dans la conversation, donnez-le :

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip llm-annotated.pgn --scope 20
```

Le script accepte le zip ou son dossier décompressé, et se relance tout seul dans l'environnement virtuel d'IAnalyze, à son emplacement par défaut.\
Un dossier qui contient plusieurs collectes est refusé : donnez celui de la collecte que le LLM a reçue.

Il n'a pas d'option `--venv`. Si votre environnement est ailleurs, lancez-le avec le Python de cet environnement : `~/venv/echecs/bin/python3 verify-analysis.py ...`

### Ce qui est contrôlé

| Contrôle | Défauts relevés |
|---|---|
| Lecture | fichier hors UTF-8, coup illégal dans la partie ou dans une variante, ligne vide dans le corps de la partie |
| Ligne principale | différente de la partie d'origine |
| Format | ligne de plus de 79 caractères, accolade ouvrante ou fermante dans un commentaire, `%`, tiret cadratin, notation suffixe, balises absentes ou dans le désordre, marqueur de fin |
| Coups commentés | erreur ou gaffe de Stockfish laissée sans commentaire dans le périmètre convenu, NAG de position contraire à l'évaluation du moteur ; pour information, les NAG de qualité d'un autre avis que le moteur |
| Évaluations | chiffre ou mat cité qui n'existe nulle part dans les données du moteur |
| Variantes | variante écrite à l'intérieur d'un commentaire, donc non jouable, variante illégale ou trop longue |
| Conversation | FEN invalide ou étrangère à la partie, tiret cadratin |

Deux de ces défauts viennent de vrais PGN de LLM et méritent une explication :

- **La ligne vide dans le corps de la partie.** python-chess y voit la fin de la partie et n'en lit pas la suite. Le script la relève où qu'elle soit, même si elle ne cache qu'une variante ou le marqueur de fin, puis poursuit ses contrôles sur le fichier une fois la ligne retirée.
- **La variante écrite entre accolades.** Ce n'est que du texte, SCID ne la rejoue pas. Le script la rejoue lui-même pour dire si elle est légale et si elle vient d'une ligne du moteur.

### Lire le rapport

| Repère | Sens |
|---|---|
| `OK` | conforme |
| `FAIL` | contraire à une consigne impérative du prompt |
| `WARNING` | à regarder de près, sans être forcément fautif |
| `INFO` | mesure donnée pour comparer les LLM entre eux |

Code de retour : 0 sans `FAIL`, 1 avec au moins un `FAIL`, 2 si un fichier ne peut pas être lu ou si l'archive n'est pas celle d'IAnalyze.\
Avec le code 2, aucun contrôle n'a eu lieu.

### Ce que le script ne fait pas

Il ne juge pas la qualité du commentaire. Une explication fausse mais bien formée passe : un LLM peut placer une dame sur la mauvaise case dans une phrase sans qu'aucun contrôle ne le voie.\
Cette lecture reste la vôtre.

Trois limites à connaître :

- Une évaluation arrondie à une décimale est acceptée : "+0.35" cité "+0.4" ou "+0.3" ne compte pas comme inventé
- Un nombre écrit sans signe, "7.77", n'est pas pris pour une évaluation : le script le confondrait avec une durée ou un classement. Un chiffre inventé écrit ainsi passe donc
- Le script repère un chiffre qui n'existe nulle part, pas un vrai chiffre attribué au mauvais coup

## 9. Sources et liens

Ce que le script interroge :

- Jeton d'accès personnel : <https://lichess.org/account/oauth/token>, une fois connecté à Lichess
- Explorateur, base de tous les joueurs : `https://explorer.lichess.org/lichess`
- Explorateur, base des maîtres : `https://explorer.lichess.org/masters`
- Catalogue des ouvertures : [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings), fichiers `a.tsv` à `e.tsv`. Ce sont ceux que charge aussi le serveur de l'explorateur.

Ce sur quoi il s'appuie :

- [python-chess](https://python-chess.readthedocs.io/en/latest/), la bibliothèque qui lit le PGN et pilote le moteur
- [Stockfish](https://stockfishchess.org/), le moteur, et [ses options UCI](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html), dont Threads, Hash et MultiPV (en anglais)
- [Spécification PGN](https://www.saremba.de/chessgml/standards/pgn/pgn-complete.htm), Steven J. Edwards, 1994

D'où viennent les cadences :

- Catégories du temps réel : [Speed.scala](https://raw.githubusercontent.com/lichess-org/scalachess/master/core/src/main/scala/Speed.scala), dans [scalachess](https://github.com/lichess-org/scalachess), la bibliothèque de règles de Lichess
- Correspondance, ICCF : [ICCF Rules, en vigueur depuis le 1er janvier 2026](https://webfiles.iccf.com/rules/2026/2026%20ICCF%20Rules%2C%20260311.pdf), section 2.4 (PDF, en anglais)
- Correspondance, capital de temps : [règlement de chess-mail.com](https://www.chess-mail.com/index.php?page=reg)

Conventions du dépôt :

- [Tenez un Changelog](https://keepachangelog.com/fr/1.1.0/) pour `CHANGELOG.md`
- [Gestion sémantique de version](https://semver.org/lang/fr/) pour les numéros de version

---

## Licences

- Catalogue des ouvertures de Lichess (chess-openings) : CC0. Il est téléchargé à l'installation, pas distribué avec ce dépôt.
- python-chess, installé dans l'environnement virtuel : GPL-3.0-or-later.
- Stockfish, installé par votre système : GPL-3.0.
- Tout le contenu de ce dépôt est en licence [CC0](LICENSE) : faites-en ce que vous voulez :)

[![CC0](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/cc-zero.svg)](https://creativecommons.org/publicdomain/zero/1.0/)

<p align="center">With ❤️ by <a href="https://github.com/deuza">DeuZa</a></p>
