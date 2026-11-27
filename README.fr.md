[![License: CC0](https://img.shields.io/badge/license-CC0_1.0-lightgrey.svg?style=plastic)](https://creativecommons.org/publicdomain/zero/1.0/)
![Hack The Planet](https://img.shields.io/badge/hack-the--planet-black?style=plastic&logo=Debian&logoColor=white)
![Built With Love](https://img.shields.io/badge/built%20with-%E2%9D%A4%20by%20DeuZa-red?style=plastic)

![GitHub release](https://img.shields.io/github/v/release/deuza/IAnalyze?label=release&style=plastic)
[![GitHub last commit](https://img.shields.io/github/last-commit/deuza/IAnalyze?style=plastic)](https://github.com/deuza/IAnalyze/commits/main)
![GitHub commit activity](https://img.shields.io/github/commit-activity/t/deuza/IAnalyze?style=plastic)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/deuza/IAnalyze?style=plastic)

# IAnalyze

English version: [README.md](README.md)

IAnalyze prépare l'analyse d'une de vos parties d'échecs par un LLM *(désigné comme l'analyste dans la suite de ce document)*, Claude avant tout.

Vous lui donnez une partie, il en rassemble les chiffres : l'évaluation Stockfish de chaque coup, calculée sur votre machine, avec derrière chaque coup faible le meilleur coup et sa suite, les statistiques de l'explorateur Lichess et le nom de l'ouverture.\
Il les écrit dans une archive zip, avec le prompt qui va avec.

```bash
./ianalyze.py my-game.pgn
```

```text
analysis-my-game-20261125-142017.zip
analysis-my-game-20261125-142017.prompt.txt
```

Vous collez le contenu du fichier prompt.txt dans une conversation neuve avec Claude, vous joignez le fichier zip, et vous recevez votre partie, annotée coup par coup, et une synthèse de vos erreurs.\
Le LLM explique, il ne calcule pas : les évaluations viennent de Stockfish, la théorie vient de l'explorateur et du catalogue.

*Le script ne produit aucune analyse : il donne à l'analyste des chiffres sûrs, et le prompt lui impose de s'y tenir.*

L'idée vient du programme [Lucas Chess](https://lucaschess.pythonanywhere.com/), dont le prompt d'analyse tient en quelques lignes suivies de la partie.

**IAnalyze est fait pour Claude :**\
Avec un compte gratuit, ou pour un autre LLM, l'option `--prompt-only` écrit un prompt court qui porte la partie et les évaluations de Stockfish, à coller seul, sans pièce jointe : voir la section 4.

Un outil supplémentaire, `verify-analysis.py`, contrôle le PGN que le LLM vous a rendu : voir la section 5.

Le script, ses messages, l'archive et le prompt sont en anglais depuis la version 5.0.0, et l'analyse est demandée en anglais.

## Sommaire

- [1. Installation](#1-installation)
   - [Jeton Lichess](#jeton-lichess)
   - [Ce que fait l'installation](#ce-que-fait-linstallation)
- [2. Analyser une partie](#2-analyser-une-partie)
   - [La partie](#la-partie)
   - [Les questions du script](#les-questions-du-script)
   - [Vos réglages](#vos-réglages)
   - [Ce que vous obtenez](#ce-que-vous-obtenez)
   - [L'envoyer à l'analyste](#lenvoyer-à-lanalyste)
- [3. Options courantes](#3-options-courantes)
- [4. Choisir un LLM](#4-choisir-un-llm)
   - [Avec le zip et le prompt](#avec-le-zip-et-le-prompt)
   - [Avec `--prompt-only`](#avec---prompt-only)
   - [Fiez-vous aux chiffres, vérifiez les récits](#fiez-vous-aux-chiffres-vérifiez-les-récits)
- [5. Vérifier le PGN rendu](#5-vérifier-le-pgn-rendu)
   - [Lire le rapport](#lire-le-rapport)
   - [Ce qu'il ne juge pas](#ce-quil-ne-juge-pas)
- [6. Pour aller plus loin](#6-pour-aller-plus-loin)
- [Licences](#licences)

---

## 1. Installation

Debian ou macOS, avec Python 3.10 ou plus récent.

Sous Debian, les paquets s'installent en root :

```bash
apt install git python3-venv stockfish
```

Sous macOS, avec Homebrew, dont le Python fournit déjà le module venv :

```bash
brew install git python stockfish
```

Puis, sous votre propre compte :

```bash
git clone https://github.com/deuza/IAnalyze.git
cd IAnalyze
./ianalyze.py --install-venv
./ianalyze.py --install-catalog
```

Chaque joueur de la machine refait ces quatre commandes sous son propre compte : rien n'est partagé, rien n'est à copier.\
Reste le jeton Lichess, ci-dessous.

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

Sans jeton, lancez le script avec `--no-explorer`.\
Si Lichess refuse le jeton, faux, expiré ou révoqué, le script s'arrête à la première requête, avant le moteur : créez-en un nouveau, ou relancez avec `--no-explorer`.

### Ce que fait l'installation

**`--install-venv`** crée un environnement virtuel dédié et y installe python-chess, la bibliothèque qui lit les parties, que Debian n'empaquette pas.\
Le script s'y relance ensuite tout seul : vous continuez à l'appeler avec le Python du système.

**`--install-catalog`** télécharge le catalogue des ouvertures nommées de Lichess, gardé en local.\
Relancez-la de temps en temps pour le mettre à jour.

**Stockfish est obligatoire** : son évaluation fait partie de toute collecte.

Tout ce que le script crée pour lui-même reste dans le dossier de l'application : supprimer ce dossier ne laisse rien derrière, hors votre jeton.\
Le dossier `local/` ne garde que ce que le script sait refaire seul, l'environnement virtuel et le catalogue : le vider remet l'application à neuf sans toucher à vos réglages.

Les emplacements exacts, et ceux des versions d'avant la 5.0.0, sont dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md#2-fichiers-du-dépôt), section 2.\
Les machines sur lesquelles toute la suite de tests est passée, dont un Raspberry Pi 4 et un Apple M1, sont données dans [docs/TESTS.fr.md](docs/TESTS.fr.md#1-lancer-les-tests).

## 2. Analyser une partie

### La partie

```bash
./ianalyze.py SOURCE [options]
```

SOURCE accepte trois formes :

```bash
./ianalyze.py my-game.pgn                        # local PGN
./ianalyze.py https://lichess.org/<identifier>   # Lichess URL
./ianalyze.py <identifier>                       # identifier
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

Le message d'erreur nomme ce qui est refusé. Les formes d'adresse acceptées et le détail de ces contrôles sont dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md#4-la-partie-sa-source-et-ses-contrôles), section 4.

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

Pour lancer une collecte sans répondre à rien, ajoutez `--no-questions`.\
Le prompt dit alors au LLM que vos réponses n'ont pas été recueillies, et c'est lui qui vous les demande avant d'analyser.

Les limites d'une réponse, et ce qui change quand le script n'est pas lancé à la main dans un terminal, sont dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md#5-questions-de-démarrage-et-terminal), section 5.

### Vos réglages

Votre pseudo, votre cadence habituelle et votre niveau sont gardés dans `settings.ini`, à la racine du dossier de l'application.

Le script les demande une seule fois, au premier lancement dans un terminal.

```ini
[player]
usernames = MyUsername, OtherUsername
time_control = 15+10
rating = 1300
```

Vous pouvez modifier ce fichier à la main, ou le supprimer avec `--purge-settings` : vos réponses seront alors redemandées.

**Les pseudos** sont cherchés dans les balises White et Black de la partie, sans tenir compte de la casse, pour déduire votre camp : chacun comme le nom entier ou comme une suite de ses mots, jamais comme un morceau de mot.\
`Max` est trouvé dans `Max Power`, pas dans `Maxime` ni dans `Max_Power` : écrivez chacun de vos pseudos en entier.

**Le niveau** est un nombre de points Elo approximatifs, de 100 à 3500, ou "unknown".

Il est transmis à l'analyste, qui y adapte ses explications. Sans lui, c'est l'Elo de votre balise dans la partie qui sert.

**La cadence** s'écrit `15+10` pour le temps réel, minutes par joueur puis incrément en secondes, et `14 days` pour la correspondance à délai fixe.

**Un autre joueur** de la même machine garde ses réglages dans un fichier à lui, nommé par `--settings` : `--settings player2.ini`. L'option prend un nom de fichier en `.ini`, qui ne commence pas par un point, rangé dans le dossier de l'application à côté de `settings.ini`, jamais un chemin. Dans un terminal, un nom dont le fichier n'existe pas encore n'est créé qu'après confirmation : une faute de frappe ne lance pas un nouveau fichier.

**Pour un seul lancement** qui laisse vos réglages de côté, la partie d'un ami par exemple, `--no-settings` ne lit ni n'écrit aucun fichier de réglages.

Les autres formes de correspondance, la clef facultative `annotator` et la façon dont le script réécrit ce fichier sont décrites dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md#6-réglages), section 6.

### Ce que vous obtenez

Archive : `analysis-<label>-<YYYYMMDD-HHMMSS>.zip`, l'étiquette `<label>` étant le nom du PGN sans extension, ou l'identifiant Lichess.\
Un dossier ou une archive homonyme fait ajouter un suffixe -2, -3...

À côté de l'archive, et non dedans :

```text
analysis-<label>-<YYYYMMDD-HHMMSS>.prompt.txt
```

C'est le prompt d'analyse de cette partie, à coller dans la conversation.\
Son chemin est donné par le journal ; la sortie standard ne porte que celui de l'archive.

Avec `--prompt-only`, il n'y a pas d'archive : la sortie standard porte le chemin du prompt.

En cas d'échec, le dossier de travail est conservé tel quel pour diagnostic.

L'archive contient la synthèse que l'analyste lit en premier, `summary.md`, la partie, vos réponses, et les données brutes du moteur et de l'explorateur.\
Le contenu de chacun de ses fichiers est détaillé dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md#10-fichiers-produits), section 10.

### L'envoyer à l'analyste

Le prompt se colle comme un message, dans une conversation neuve, l'archive en pièce jointe.\
Il vaut pour une partie : c'est le coller à chaque conversation qui garantit qu'il correspond à l'archive.

Le prompt suit ce que la collecte a réellement fait. Sans explorateur, il ne demande ni fréquence ni coup majoritaire.\
Avec `--stockfish-moves`, il dit jusqu'où le moteur a évalué. Avec `--multipv 1`, il n'annonce pas trois coups par position.

Tous les LLM n'ouvrent pas un zip, et tous n'exécutent pas de code.

Le prompt prévoit les deux cas :

- **Le LLM n'accepte pas l'archive** : décompressez-la et envoyez-lui **tous** ses fichiers, joints ou collés.

  `--keep-folder` laisse le dossier décompressé à côté de l'archive.

  Le prompt demande à l'analyste de se servir de tous les fichiers, pas de la seule synthèse : les `.json` portent les variantes entières du moteur et tous les coups connus de l'explorateur, que `summary.md` résume.

  S'il n'en reçoit qu'une partie, il doit dire lesquels manquent et vous demander de les envoyer.

- **Le LLM exécute du code** : il construit le PGN avec python-chess et en prouve la légalité.
- **Le LLM n'exécute pas de code** : il écrit le PGN lui-même, le dit, et vous laisse ouvrir le fichier pour confirmer.

Le prompt est tiré du modèle `prompt-template.txt`, rangé à côté du script, que vous pouvez modifier librement, sans toucher au script.\
À chaque collecte, le script en tire le prompt de la partie : il remplit les valeurs et ne garde que les passages qui s'appliquent.\
Pour écrire votre propre modèle, la liste des repères, des valeurs et des conditions est dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md#12-modèle-de-prompt), section 12.

## 3. Options courantes

Quelques options suffisent à la plupart des usages :

| Option | Effet |
|---|---|
| `--no-explorer` | pas de statistiques d'ouverture : ni jeton ni catalogue ne sont demandés |
| `--no-questions` | aucune question : le LLM vous les posera lui-même |
| `--prompt-only` | un prompt court à coller seul, sans archive, pour un compte gratuit ou un LLM qui n'ouvre pas les zip (section 4) |
| `--keep-folder` | garde le dossier décompressé à côté de l'archive |
| `--output-dir DIR` | écrit les fichiers dans le répertoire DIR |
| `--database masters` | interroge la base des maîtres au lieu de celle de tous les joueurs de Lichess |
| `--depth D` | profondeur de calcul de Stockfish, 18 par défaut : plus elle est grande, plus le calcul est long |
| `--stockfish-moves N` | limite le moteur aux N premiers coups |
| `--usernames LIST` | vos pseudos, pour cette seule collecte |
| `--settings NAME` | un autre fichier de réglages, par son nom, dans le dossier de l'application : un profil par joueur |
| `--no-settings` | ne lit ni n'écrit aucun fichier de réglages, pour ce seul lancement |

```bash
./ianalyze.py my-game.pgn --no-explorer --output-dir ~/analyses
```

Toutes les options sont dans [EXAMPLES.fr.md](EXAMPLES.fr.md), chacune avec sa commande et ce que le terminal affiche.\
`./ianalyze.py --help` en donne le résumé.

## 4. Choisir un LLM

**Optez pour Claude** : c'est le conseil de ce dépôt, et il vient des essais décrits dans [docs/TRIALS.fr.md](docs/TRIALS.fr.md). Les autres LLM n'ont été essayés que sur leur offre gratuite.

Avec le zip, Claude est le seul qui ait rendu un PGN utilisable tel quel.\
Avec le prompt court, avec un abonnement comme avec un compte gratuit, c'est lui qui a rendu les PGN les plus propres, et ses explications sont celles qui ont le mieux tenu à la vérification sur l'échiquier.

IAnalyze a été mis au point avec lui par l'auteur, qui l'utilise pour analyser ses parties.\
Deux routes mènent à une analyse, et il est le premier choix sur les deux :

| Route | Ce que vous envoyez | Ce qu'il faut au LLM | Ce que vous recevez |
|---|---|---|---|
| Le zip et le prompt | l'archive en pièce jointe, le prompt collé | ouvrir un zip, exécuter du code, rendre un fichier | un fichier PGN construit avec python-chess, appuyé sur toutes les données |
| `--prompt-only` | un seul texte collé, sans pièce jointe | une simple conversation | le PGN annoté dans un bloc de code |

**Avec un compte gratuit, prenez `--prompt-only` et Claude. Choisissez le modèle `Sonnet 5.5` avec l'effort `Max`.**\
C'est la combinaison qui a donné le meilleur résultat sans rien payer.\
Le zip passe aussi sur une offre gratuite, si vous pouvez attendre que le quota revienne : voyez [la série du 27 novembre 2026](docs/TRIALS.fr.md#le-27-novembre-2026-les-deux-routes-avec-les-prompts-publiés).

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

Pour contrôler le PGN rendu avec `verify-analysis.py --prompt-only` (section 5), ajoutez `--keep-folder` à la collecte : le vérificateur a besoin des évaluations qui ont servi au prompt.

### Fiez-vous aux chiffres, vérifiez les récits

C'est ce que tous les essais ont en commun.

**Les chiffres tiennent.** Aucun LLM n'a inventé une évaluation, avec le zip comme avec le prompt court.\
Ce qui vient du tableau du moteur est recopié fidèlement : les écarts, les meilleurs coups, leurs suites.

**Les récits sont fragiles.**\
Ce que le LLM déduit seul de la position peut être faux : un sacrifice qui n'en est pas un, un échec qui n'en est pas un, une pièce en prise que personne ne signale, un mat en un qui est un mat en deux, une pièce de moins prise pour l'égalité matérielle.

Quand un commentaire vous surprend, posez les pièces et regardez.\
Le script `verify-analysis.py` contrôle la forme du PGN et les chiffres cités, il ne juge pas ce qui est raconté.

## 5. Vérifier le PGN rendu

`verify-analysis.py` est un outil supplémentaire, indépendant de la collecte : il contrôle ce que le LLM vous a rendu.

Un LLM peut rendre un PGN qui a l'air juste et ne l'est pas : un coup illégal dans une variante, un chiffre arrangé, une gaffe passée sous silence.\
`verify-analysis.py` compare le PGN rendu à l'archive que le LLM a reçue, et sort le même rapport pour chaque LLM essayé.

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip llm-annotated.pgn
```

Copiez la conversation dans un fichier texte pour faire contrôler aussi les positions et les évaluations qu'elle cite :

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip llm-annotated.pgn --summary llm-conversation.txt --name "Model name"
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

Le prompt court demande moins que le prompt complet : avec cette option, les contrôles qu'il ne demande pas sont sautés.

Si vous avez convenu avec le LLM d'un périmètre, les 20 premiers coups par exemple, le script le lit dans votre réponse à la question de démarrage et n'attend aucun commentaire au-delà.\
Quand le périmètre a été fixé dans la conversation, donnez-le :

```bash
./verify-analysis.py analysis-my-game-20261125-142017.zip llm-annotated.pgn --scope 20
```

Le script accepte le zip ou son dossier décompressé, et se relance tout seul dans l'environnement virtuel d'IAnalyze, à son emplacement par défaut.\
Un dossier qui contient plusieurs collectes est refusé : donnez celui de la collecte que le LLM a reçue.

Il n'a pas d'option `--venv`. Si votre environnement est ailleurs, lancez-le avec le Python de cet environnement : `~/venv/chess/bin/python3 verify-analysis.py ...`

Ce que contrôle le script, et les règles de chaque contrôle, sont dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md#13-le-vérificateur-en-détail), section 13.

### Lire le rapport

| Repère | Sens |
|---|---|
| `OK` | conforme |
| `FAIL` | contraire à une consigne impérative du prompt |
| `WARNING` | à regarder de près, sans être forcément fautif |
| `INFO` | mesure donnée pour comparer les LLM entre eux |

Code de retour : 0 sans `FAIL`, 1 avec au moins un `FAIL`, 2 si un fichier ne peut pas être lu ou si l'archive n'est pas celle d'IAnalyze.\
Avec le code 2, aucun contrôle n'a eu lieu.

### Ce qu'il ne juge pas

Il ne juge pas la qualité du commentaire. Une explication fausse mais bien formée passe : un LLM peut placer une dame sur la mauvaise case dans une phrase sans qu'aucun contrôle ne le voie.\
Cette lecture reste la vôtre.

Les limites de ses contrôles sont dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md#13-le-vérificateur-en-détail), section 13.

## 6. Pour aller plus loin

- [EXAMPLES.fr.md](EXAMPLES.fr.md) : l'aide-mémoire, toutes les commandes, toutes les options, et ce que le terminal affiche
- [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md) : le fonctionnement du script, son emploi depuis un autre programme, le détail des fichiers produits, et le guide pour reprendre le projet
- [docs/TESTS.fr.md](docs/TESTS.fr.md) : la suite de tests, test par test
- [docs/TRIALS.fr.md](docs/TRIALS.fr.md) : les essais des LLM, sur lesquels s'appuie le conseil de la section 4
- [CHANGELOG.md](CHANGELOG.md) : l'historique des versions, en anglais

Chaque document a aussi sa version anglaise, sous le même nom sans `.fr` ; le CHANGELOG n'existe qu'en anglais.\
Les sources que le script interroge et sur lesquelles il s'appuie sont données dans [docs/TECHNICAL.fr.md](docs/TECHNICAL.fr.md#14-sources-et-liens), section 14.

---

## Licences

- Catalogue des ouvertures de Lichess (chess-openings) : CC0. Il est téléchargé à l'installation, pas distribué avec ce dépôt.
- python-chess, installé dans l'environnement virtuel : GPL-3.0-or-later.
- Stockfish, installé par votre système : GPL-3.0.
- Tout le contenu de ce dépôt est en licence [CC0](LICENSE) : faites-en ce que vous voulez :)

[![CC0](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/cc-zero.svg)](https://creativecommons.org/publicdomain/zero/1.0/)

<p align="center">With ❤️ by <a href="https://github.com/deuza">DeuZa</a></p>
