# IAnalyze : documentation technique

English version: [TECHNICAL.md](TECHNICAL.md)

Le [README](../README.fr.md) suffit pour installer IAnalyze et analyser une partie. [EXAMPLES.fr.md](../EXAMPLES.fr.md) donne toutes les commandes, toutes les options et ce qu'elles affichent.

Ce document va plus loin. Il s'adresse à qui veut comprendre ce que fait le script, l'appeler depuis un autre programme, lire les fichiers qu'il produit, écrire son propre modèle de prompt, ou reprendre le projet : la section 15 en est le guide. Les tests ont leur document, [TESTS.fr.md](TESTS.fr.md), et les essais des LLM aussi, [TRIALS.fr.md](TRIALS.fr.md).

Le script, ses messages et ses fichiers sont en anglais : les noms de fichiers, les clefs, les valeurs et les sorties de cette page sont donc les mêmes que dans sa version anglaise.

## Sommaire

- [1. Ce que fait le script, étape par étape](#1-ce-que-fait-le-script-étape-par-étape)
- [2. Fichiers du dépôt](#2-fichiers-du-dépôt)
- [3. Ligne de commande](#3-ligne-de-commande)
- [4. La partie, sa source et ses contrôles](#4-la-partie-sa-source-et-ses-contrôles)
- [5. Questions de démarrage et terminal](#5-questions-de-démarrage-et-terminal)
- [6. Réglages](#6-réglages)
- [7. Jeton](#7-jeton)
- [8. Explorateur](#8-explorateur)
- [9. Moteur](#9-moteur)
- [10. Fichiers produits](#10-fichiers-produits)
- [11. Encodages et caractères](#11-encodages-et-caractères)
- [12. Modèle de prompt](#12-modèle-de-prompt)
- [13. Le vérificateur en détail](#13-le-vérificateur-en-détail)
- [14. Sources et liens](#14-sources-et-liens)
- [15. Reprendre le projet](#15-reprendre-le-projet)

## 1. Ce que fait le script, étape par étape

Une collecte suit toujours le même ordre. Les contrôles viennent d'abord : tant qu'ils ne sont pas tous passés, rien n'est écrit dans le répertoire de sortie et aucune requête ne part vers l'explorateur.

1. **Options.** Elles sont lues et contrôlées (section 3). Une option refusée arrête le script avec le code 2.
2. **Environnement virtuel.** Le Python du système n'a pas python-chess : le script se relance lui-même avec le Python de son environnement virtuel. Le journal l'annonce par "Virtual environment: restarting with ...". C'est le fonctionnement normal, à chaque lancement.
3. **Réglages et modèle de prompt.** Le fichier de réglages est lu (section 6), le modèle de prompt est lu et contrôlé (section 12).
4. **Partie.** Le PGN est lu depuis le fichier, ou téléchargé depuis Lichess. Il est décodé (section 11), puis contrôlé (section 4).
5. **Jeton et catalogue.** Sauf avec `--no-explorer`, le jeton est lu (section 7) et le catalogue des ouvertures chargé (section 8).
6. **Moteur.** Le binaire de Stockfish est vérifié, puis lancé une première fois, seulement pour lui demander les bornes de ses options (section 9).
7. **Questions.** Dans un terminal, le script pose ses questions (section 5).
8. **Dossier de travail.** Il est créé dans le répertoire de sortie. Le script y écrit `game.pgn` et, si vous avez répondu aux questions, `context.md`.
9. **Explorateur.** Une requête par demi-coup, jusqu'à un critère d'arrêt (section 8).
10. **Stockfish.** Une évaluation par demi-coup (section 9). C'est la phase la plus longue.
11. **Synthèse.** `collection.json` et `summary.md` sont écrits (section 10).
12. **Archive.** Le dossier est compressé, l'archive vérifiée, le dossier supprimé. Avec `--prompt-only`, il n'y a pas d'archive.
13. **Prompt.** Il est écrit à côté de l'archive.
14. **Sortie standard.** Le chemin de l'archive, ou celui du prompt avec `--prompt-only`, y est écrit seul.

Trois commandes ne collectent rien et s'arrêtent une fois leur travail fait : `--install-venv`, `--install-catalog` et `--purge-settings`.

`--install-venv` contrôle le code de retour de `python -m venv`. Une création interrompue avant ce retour, par Ctrl-C ou une coupure, laisse un environnement sans pip, que le lancement suivant retrouve à moitié fait. Le script le reconnaît : `pyvenv.cfg` et l'interpréteur sont là, mais `python -m pip --version` échoue. Il le reconstruit alors par `python -m venv --clear`, puis installe python-chess. Sans `pyvenv.cfg`, un répertoire n'est jamais pris pour un environnement à reconstruire, et `--clear` ne peut rien y effacer.

Un `--venv` qui n'est pas un environnement virtuel est refusé avant tout le reste : un chemin qui existe sans être un répertoire, un fichier ordinaire par exemple, sur lequel `python -m venv` échouait avec un message qui évoquait un paquet manquant ; un répertoire existant, non vide et sans `pyvenv.cfg`, comme `/usr` ou un répertoire personnel. pip aurait tourné sur le Python trouvé là, souvent celui du système, et `python -m venv` aurait mêlé ses fichiers à ceux qui y étaient. Un répertoire absent ou vide reçoit l'environnement. Une création interrompue dans les tout premiers instants, avant l'écriture de `pyvenv.cfg`, laisse un répertoire que ce refus écarte aussi : il suffit alors de le supprimer.

Après l'étape 8, un échec laisse le dossier de travail en place, tel quel, pour diagnostic.

## 2. Fichiers du dépôt

| Fichier | Rôle |
|---|---|
| `ianalyze.py` | la collecte, en un seul fichier. Il ne demande que python-chess et Stockfish |
| `verify-analysis.py` | le contrôle du PGN rendu par un LLM (section 13) |
| `prompt-template.txt`, `prompt-only-template.txt` | les deux modèles de prompt (section 12) |
| `tests/test-app.sh` | la suite de tests, pour Linux et macOS, décrite dans [TESTS.fr.md](TESTS.fr.md) |
| `tests/test.pgn` | une partie d'essai qui réunit les cas tordus d'un PGN, décrite dans [TESTS.fr.md](TESTS.fr.md) |
| `tests/refused/`, `tests/llm/` | les PGN que le script refuse et les PGN annotés écrits pour [EXAMPLES.fr.md](../EXAMPLES.fr.md), que les tests lisent aussi |
| `example-games/` | les parties citées dans [EXAMPLES.fr.md](../EXAMPLES.fr.md), prêtes à être analysées |
| `README.md`, `EXAMPLES.md`, et dans `docs/` : `TECHNICAL.md`, `TESTS.md`, `TRIALS.md` | la documentation, chaque document avec sa version française, sous le même nom terminé par `.fr.md` |
| `CHANGELOG.md` | l'historique des versions, en anglais seulement |
| `LICENSE` | la licence, CC0 |

Le HTTP passe par urllib et l'archive par zipfile, tous deux de la bibliothèque standard de Python.

### Où le script range ce qu'il crée

Les mêmes sur les deux plateformes, sauf pour le moteur.

Tout ce que le script crée pour lui-même reste dans le dossier de l'application : supprimer ce dossier ne laisse rien derrière, hors votre jeton.\
Le dossier `local/` ne garde que ce que le script sait refaire seul, l'environnement virtuel et le catalogue : le vider remet l'application à neuf sans toucher à vos réglages. `local/` et les fichiers de réglages sont ignorés par git.

| | Emplacement |
|---|---|
| `--venv` | `local/venv`, dans le dossier de l'application |
| `--catalog` | `local/`, dans le dossier de l'application |
| réglages | `settings.ini`, à la racine du dossier de l'application, comme tout autre fichier de réglages nommé par `--settings` |
| jeton | `~/.lichess_token` |
| `--stockfish`, Debian | le binaire trouvé dans le PATH, sinon `/usr/games/stockfish` |
| `--stockfish`, macOS | le binaire trouvé dans le PATH, sinon `/opt/homebrew/bin/stockfish` |

Jusqu'à la version 4.0.2, l'environnement virtuel et le catalogue étaient rangés dans `~/.local/share/IAnalyze`, les réglages dans `~/.config/IAnalyze`.\
Le script ne les y lit plus : relancez `--install-venv` et `--install-catalog`, puis supprimez ces deux répertoires. Vos réglages vous seront redemandés au premier lancement dans un terminal.

## 3. Ligne de commande

### Règles de cohérence

Une option sans effet, ou une valeur hors bornes, est refusée plutôt qu'ignorée en silence :

- `--speeds` et `--ratings` exigent `--database lichess`.
- `--pause` ne descend pas sous 2, `--min-frequency` reste entre 0 et 100, `--min-moves`, `--stockfish-moves` et `--pv-length` valent 0 ou plus, `--depth` va de 1 à 60, les autres valeurs numériques valent au moins 1. `--timeout` est contrôlé avec `--install-catalog` aussi, qui télécharge également.
- `--pause` et `--min-frequency` refusent nan et inf.
- `--threads`, `--hash` et `--multipv` sont contrôlés auprès du moteur, qui annonce ses bornes : une valeur qu'il n'admet pas est refusée avant toute requête à l'explorateur et avant la création du dossier de travail.
- `--settings` prend un nom de fichier qui finit par `.ini`, sans dossier et qui ne commence pas par un point (section 6) : un chemin est refusé, `/dev/null` compris.
- `--settings` et `--no-settings` s'excluent, de même que `--purge-settings` et `--no-settings`.
- `--purge-settings` s'emploie seule, sans partie ni autre action.
- `--no-prompt` s'exclut avec `--prompt` et avec `--prompt-only`.
- `--usernames` et `--prompt` refusent une valeur vide.

### Codes de retour

| Code | Signification |
|---|---|
| 0 | succès |
| 1 | erreur signalée par un message, dont une valeur que le moteur n'admet pas, ou erreur inattendue |
| 2 | option inconnue, options qui s'excluent, ou valeur refusée avant toute lecture de la partie |
| 130 | interruption (Ctrl-C) |

Ceux de `verify-analysis.py` sont donnés en section 13.

### Sortie standard et journal

Le chemin de l'archive est écrit seul sur la sortie standard, le journal horodaté va sur la sortie d'erreur :

```bash
ARCHIVE=$(./ianalyze.py my-game.pgn 2>/dev/null)
```

Avec `--prompt-only`, c'est le chemin du prompt qui est écrit sur la sortie standard.

Le journal, les questions et les messages d'erreur vont tous sur la sortie d'erreur. Chaque ligne du journal porte l'heure :

```text
[14:20:16] Virtual environment: restarting with /home/user/IAnalyze/local/venv/bin/python3
[14:20:16] Reading the local PGN: my-game.pgn
[14:20:17] Working folder: analysis-my-game-20261125-142017
[14:20:33] Stockfish: evaluation of 9 plies, depth 18, multipv 3, threads 4. This is the longest phase.
```

Un message d'erreur, lui, n'est pas horodaté : c'est la dernière ligne, et le code de retour vaut 1 ou 2.

### Appeler le script depuis un autre programme

```bash
ARCHIVE=$(./ianalyze.py my-game.pgn --no-questions 2> collection.log)
```

Le code de retour dit si la collecte a abouti, `collection.log` garde le journal et `$ARCHIVE` reçoit le chemin de l'archive.

Rediriger la sortie d'erreur suffit à faire taire les questions (section 5) : `--no-questions` le dit seulement en clair.

Sous macOS, cette commande met le prompt court dans le presse-papiers, prêt à être collé dans la conversation. La sortie d'erreur n'étant pas redirigée, les questions restent posées :

```bash
pbcopy < "$(./ianalyze.py my-game.pgn --prompt-only)"
```

## 4. La partie, sa source et ses contrôles

SOURCE désigne la partie de trois façons : un fichier PGN, l'adresse d'une partie de Lichess, ou son identifiant.

**Une URL** doit viser lichess.org et porter l'identifiant en tête de chemin.

L'identifiant est la suite de 8 caractères qui suit `lichess.org/` dans l'adresse de la partie. Les formes `/<id>/black`, `/embed/game/<id>`, `/embed/<id>` et `/game/export/<id>` sont acceptées.

Un autre hôte, ou une autre page du site (étude, analyse, exercices), est refusé sans rien envoyer à Lichess. Certaines rubriques du site ont un nom de huit lettres, la forme d'un identifiant : `analysis`, `training`, `timeline` ou `bookmark` par exemple. Elles sont refusées elles aussi, d'après une liste que les routes du site ont complétée en novembre 2026.

**Un identifiant** fait exactement 8 ou 12 caractères alphanumériques.

Une source qui ressemble à un chemin (point, barre oblique ou tilde) et qui n'existe pas est signalée comme fichier introuvable. Un répertoire est refusé, même si son nom a la forme d'un identifiant.

**Un PGN** doit contenir une seule partie, en échecs standard. Un fichier qui en réunit plusieurs est refusé : isolez celle à analyser dans un fichier à part.

**Un résultat répété** en fin de fichier n'est pas une seconde partie. Certains sites écrivent le résultat, une ligne vide, puis le résultat encore : python-chess y lit une partie de plus, sans une balise ni un coup. Le script l'ignore et l'écrit au journal. Le fichier gardé dans l'archive reste celui que vous avez fourni.

Un PGN corrompu est refusé plutôt qu'analysé tronqué. Une partie qui ne part pas de la position initiale, c'est-à-dire qui porte une balise FEN, est refusée elle aussi : IAnalyze analyse une partie entière, du premier coup au dernier. Pour étudier une position, chargez-la dans un échiquier d'analyse.

Les coups doivent être écrits en notation anglaise : K, Q, R, B, N. Une partie notée en français (R, D, T, F, C) ou en figurines est refusée, avec le premier mot qui n'a pas été compris. Sans ce refus, "Cf3" serait lu "f3", un coup de pion, et l'analyse porterait sur une autre partie que la vôtre.

Sont refusés de la même façon :

- un commentaire dont l'accolade n'est jamais fermée
- une variante dont la parenthèse n'est jamais fermée, ou une parenthèse fermante en trop
- du texte libre hors des accolades, après la partie par exemple
- une ligne qui commence par un crochet sans être une balise bien formée, seule sur sa ligne, avant les coups de sa partie : python-chess la sauterait, avec ce qu'elle porte, ou jouerait les coups que ses crochets contiennent
- un coup nul joué en échec, après un mat par exemple : les positions qui suivent sont illégales, et Stockfish y mourait sans dire pourquoi

Une partie de Lichess est téléchargée depuis `https://lichess.org/game/export/<identifier>`, qui ne demande pas de jeton.

Le contrôle de la notation passe avant la lecture par python-chess, qui, lui, ne refuserait rien : il saute sans rien dire les caractères qu'il ne connaît pas. Sont admis hors des commentaires : les balises, seules sur leur ligne et avant les coups de leur partie, les numéros de coup, les coups en notation anglaise, le coup nul `--`, les NAG, les signes d'appréciation, les parenthèses de variante et le résultat.

Un coup illégal arrête lui aussi le script. python-chess, à cet endroit, cesserait de lire sans lever d'erreur, et la partie serait analysée tronquée. Le refus nomme le coup, une seule fois : python-chess ne l'écrit plus de lui-même avant.

## 5. Questions de démarrage et terminal

### Ordre des questions

1. Au premier lancement, les réglages qui manquent : pseudo, cadence habituelle, niveau (section 6). Avec `--settings`, un nom dont le fichier n'existe pas encore est d'abord confirmé.
2. Votre camp, s'il ne se déduit pas de vos pseudos : "Did you play White or Black? [w/b]". Les balises White et Black vides sont alors complétées : la vôtre par votre premier pseudo, ou par votre nom, demandé faute de pseudo, celle de l'adversaire par son nom, demandé lui aussi.
3. La cadence de la partie, si la balise TimeControl manque, est vide, ou vaut "?" ou "-".
4. Les quatre questions de contexte : périmètre, ce que vous cherchez à comprendre, contexte particulier, autres commentaires à inclure dans le PGN final.

Entrée retient la valeur proposée. Ctrl-D met fin aux questions : celles qui restent prennent leur valeur par défaut.

Les questions de réglages font exception : interrompues par Ctrl-D, elles n'enregistrent rien et reviendront au prochain lancement.

### Limites d'une réponse

Une réponse fait 255 caractères au plus.\
Un nom de joueur ou un pseudo ne peut contenir ni guillemet, ni barre oblique inversée, ni crochet, ni accolade : il part dans une balise du PGN, que ces signes rendraient illisible.

Une réponse refusée est redemandée.

### Ce que deviennent les réponses

Les réponses vont dans `context.md`, repris en tête de la synthèse sous le titre "Analysis instructions".

Une réponse laissée à sa valeur proposée y porte la mention "(default)" : l'analyste distingue ainsi votre choix d'une valeur par défaut.

```text
The player's answers to the startup questions, asked by the script before the collection. "(default)" marks an answer confirmed with Enter.

- Player's side: White, deduced from the headers
- Time control: TimeControl tag `600+5`, that is rapid, 10 minutes + 5 seconds per move
- a. Scope: the whole game (default)
- b. What the player wants to understand: the early queen sortie
- c. Particular context: nothing (default)
- d. Other comments to include in the final PGN: nothing (default)
```

Quand une balise White ou Black a été complétée, `game.pgn` porte la partie avec ses nouvelles balises, et le PGN fourni est gardé sous `game-original.pgn`.

### Quand les questions ne sont pas posées

Les questions s'affichent dans le terminal et attendent une réponse au clavier.

Le script ne les pose donc que s'il est lancé à la main, dans un terminal. Il ne demande rien dans ces quatre cas :

- vous passez `--no-questions`
- un autre programme le lance sans terminal : cron, un service
- son entrée ne vient pas du clavier : `./ianalyze.py my-game.pgn < /dev/null`
- son journal ne va pas à l'écran : `./ianalyze.py my-game.pgn 2> log.txt`

Le dernier cas surprend : les questions s'écrivent au même endroit que le journal, la sortie d'erreur. Si vous la redirigez, vous ne les verriez pas.

L'exemple de la section 3, avec `2>/dev/null`, ne pose donc aucune question. Sans cette redirection, `ARCHIVE=$(./ianalyze.py my-game.pgn)` les pose normalement.

Dans la suite, "sans terminal" désigne ces quatre cas.

### Sans questions, ce qui change

- Le journal le dit : "Startup questions skipped", suivi de la raison, l'option ou le terminal non interactif.
- Les réglages qui manquent ne sont ni demandés ni écrits.
- `context.md` n'est pas écrit, et la synthèse n'a pas de section "Analysis instructions".
- Le camp se déduit de vos pseudos, sans question. Il faut pour cela qu'une seule des deux balises, White ou Black, porte l'un d'eux. Sinon le camp reste "unknown".
- Le prompt dit au LLM que vos réponses n'ont pas été recueillies : c'est lui qui pose les quatre questions de contexte, en un seul message, avant d'analyser.

## 6. Réglages

Le fichier de réglages, `settings.ini` ou celui que nomme `--settings`, est rangé à la racine du dossier de l'application, au format INI. Sa section `[player]` porte trois clefs que le script demande, `usernames`, `time_control` et `rating`, et une clef facultative, `annotator`.

### Clefs et formes admises

**Les pseudos**, `usernames`, sont vos noms de joueur, séparés par des virgules. Ils sont cherchés, sans tenir compte de la casse, dans les balises White et Black pour déduire votre camp, comme nom entier ou comme suite de ses mots : "Müller" est trouvé dans "Müller, Noël", mais "Max" ne l'est pas dans "Maxime", ni "deuza" dans "DeuZa42". Donnez chacun de vos pseudos. Le premier sert à compléter une balise vide.

**Le niveau**, `rating`, est un nombre de points Elo approximatifs, de 100 à 3500, ou "unknown".

**L'annotateur**, `annotator`, est une clef facultative, que le script ne demande pas. Elle fixe la balise Annotator du PGN annoté :

```text
annotator = Claude (Anthropic)
```

Sans elle, le prompt demande à l'analyste d'y mettre son propre nom de modèle.

**La cadence**, `time_control`, s'écrit de l'une de ces façons :

| Vous écrivez | Système | Où on le trouve |
|---|---|---|
| `15+10` | temps réel : minutes par joueur, puis incrément en secondes | Lichess |
| `14 days` | correspondance à délai fixe : jours par coup, rien n'est reporté d'un coup au suivant | Lichess, chess.com |
| `10 moves in 50 days` | correspondance par période : le temps économisé est reporté | ICCF, cadence standard |
| `5 days + 36 hours, maximum 20 days` | correspondance à capital de temps : jours au départ, puis incrément par coup en heures ou en jours, plafond facultatif | chess-mail.com |
| `50 days + 3 days, maximum 50 days, bank 75 days` | le même, avec une réserve à côté du capital | ICCF, Triple Block |
| `unknown` | | |

Les deux systèmes de l'ICCF suivent ses règles en vigueur depuis le 1er janvier 2026, section 2.4.

Le délai fixe par coup, lui, n'existe pas à l'ICCF.

Le script tolère quelques variantes d'écriture : "d" ou "day" pour "days", "h" ou "hour" pour "hours", "move" pour "moves". Une cadence vide, "?" ou "unspecified" vaut "unknown".

Pour le temps réel, la catégorie est calculée comme le fait Lichess, sur une durée estimée : le temps initial plus quarante fois l'incrément. Le script l'écrit en anglais.

| Durée estimée | Catégorie |
|---|---|
| moins de 30 secondes | ultrabullet |
| de 30 secondes à moins de 3 minutes | bullet |
| de 3 à moins de 8 minutes | blitz |
| de 8 à moins de 25 minutes | rapid |
| 25 minutes et plus | classical |

`15+10` donne 900 + 400 = 1300 secondes : rapid.

### Lecture

- Un fichier absent vaut des réglages vides.
- Une clef absente est demandée, une seule fois, dans un terminal.
- Une clef présente, même vide, n'est jamais redemandée.
- Une cadence ou un niveau illisible est redemandé, et le journal le dit.
- Un fichier mal formé arrête le script, avec le remède : le corriger ou le supprimer.
- Le signe "%" est un caractère comme un autre, il ne déclenche aucune substitution.
- Le fichier passe par le même décodage que le PGN (section 11) : son encodage n'a pas d'importance.
- `--usernames` remplace les pseudos du fichier le temps d'un lancement. Au tout premier lancement, il est proposé comme réponse à la question du pseudo.
- Un `settings.ini` à l'ancien format, recopié à la main depuis le `reglages.ini` de la version 4 ou écrit par une version de développement de la 5.0.0, porte une section `[joueur]`, qui n'est plus lue : ses questions sont reposées, et la section reste dans le fichier après `[player]`, comme une section à vous.

### Écriture

Le script n'écrit le fichier que lorsqu'il vient d'obtenir une réponse. Il le réécrit alors en entier :

1. un en-tête de commentaires
2. les clefs qu'il connaît, chacune sous un commentaire qui rappelle ses formes admises
3. les autres clefs que vous avez ajoutées à `[player]`
4. vos autres sections

Vos propres lignes de commentaire ne survivent donc pas à une réécriture.

Le fichier n'est écrit que sur un fichier de réglages : un chemin qui n'existe pas encore, ou un fichier ordinaire vide ou portant la section `[player]`, ou la section `[joueur]` de l'ancien format. La section est cherchée dans le texte décodé comme le fait la lecture : un fichier de réglages en UTF-16 est reconnu, pour l'écriture comme pour `--purge-settings`. Tout le reste, un périphérique, une FIFO, un répertoire ou le fichier d'un autre programme, est laissé intact.

Si l'écriture échoue, ou si le fichier ne doit pas être remplacé, la collecte continue : le journal le signale, et la question sera reposée au prochain lancement.

Sans terminal, rien n'est demandé ni écrit.

### Plusieurs profils

`--settings NAME` désigne un autre fichier : un nom de fichier qui finit par `.ini` et ne commence pas par un point, qui le cacherait, rangé à la racine du dossier de l'application, à côté de `settings.ini`. Un chemin est refusé, même à l'intérieur du dossier : les réglages ne quittent jamais le dossier, et le supprimer ne laisse rien derrière. Si le fichier n'existe pas, il est créé par les mêmes questions : c'est la façon de tenir un profil par joueur.

Dans un terminal, un nom dont le fichier n'existe pas encore est d'abord confirmé : "Settings: player2.ini does not exist yet in ... Create it? [y/n]". `n`, ou Ctrl-D, arrête le script avant toute écriture et toute collecte : une faute de frappe ne crée pas de nouveau fichier. Le fichier par défaut, `settings.ini`, est créé sans cette question.

`--no-settings` laisse les réglages de côté le temps d'un lancement : aucun fichier n'est lu ni écrit, et les questions de réglages ne sont pas posées. Le camp est demandé, ou déduit de `--usernames`, et le niveau vient de la balise Elo de votre camp.

`--purge-settings` supprime le fichier de réglages, celui de `--settings` s'il est donné, puis quitte. Seul un fichier qui porte la section `[player]`, ou un fichier vide, est supprimé : une faute de frappe ne doit pas détruire un autre fichier. Un fichier absent n'est pas une erreur, un répertoire est refusé.

## 7. Jeton

Le jeton n'est transmis que dans l'en-tête Authorization, jamais dans l'URL. Il n'apparaît ni dans le journal, ni dans l'archive, où `collection.json` note seulement sa présence.

Il n'est envoyé qu'à l'adresse de l'explorateur : si celui-ci répondait par une redirection, elle ne serait pas suivie, et l'interrogation s'arrêterait là.

Un fichier de jeton lisible par d'autres déclenche un avertissement. Le fichier ne porte que le jeton : une affectation, `LICHESS_TOKEN=...`, ou des guillemets sont refusés.

Le fichier peut porter une marque d'ordre des octets ou être en UTF-16, comme en produisent certains éditeurs Windows : le journal le signale et le jeton est lu normalement.

Le fichier n'est ouvert que si l'explorateur sert : avec `--no-explorer`, il n'est pas lu. Le téléchargement d'une partie de Lichess, lui, se fait sans jeton.

Contrôles à la lecture :

- un fichier absent ou vide arrête le script
- une espace, un signe égal ou un guillemet dans le jeton arrêtent le script : le fichier ne doit porter que le jeton
- un caractère hors de l'ASCII imprimable arrête le script, sans que le message reproduise le jeton

La réponse de l'explorateur est expurgée du jeton avant d'être gardée dans l'archive, au cas où un serveur renverrait l'en-tête qu'il a reçu. Il en va de même de la trace d'une erreur inattendue, avec `--debug`.

## 8. Explorateur

### Requêtes

Le script envoie une requête par demi-coup, à `https://explorer.lichess.org/lichess` ou à `https://explorer.lichess.org/masters` selon `--database`. La position y est désignée par la suite des coups joués depuis le début de la partie, et non par une FEN.

| Paramètre | Valeur | Rôle |
|---|---|---|
| `play` | les coups déjà joués, en notation UCI, séparés par des virgules | la position interrogée |
| `moves` | `256` | tous les coups connus de la position, et non les premiers seulement |
| `topGames` | `0` | aucune partie de référence, seules les statistiques servent |

La base `lichess` reçoit en plus les filtres :

| Paramètre | Valeur |
|---|---|
| `variant` | `standard` |
| `speeds` | la liste de `--speeds` |
| `ratings` | la liste de `--ratings` |
| `since` | `2017-01` |
| `recentGames` | `0` |

Chaque requête porte l'en-tête d'agent `IAnalyze/<version> (+https://github.com/deuza/IAnalyze)` et le jeton, dans l'en-tête Authorization.

Chaque réponse est gardée telle quelle dans `explorer/NNN-<uci>.json` : NNN est le numéro du demi-coup, `<uci>` le coup joué. C'est la réponse sur la position d'avant ce coup.

### Pause, HTTP 429 et erreurs

Le script attend `--pause` secondes entre deux requêtes, 2 au minimum, et rien avant la première.

Sur un HTTP 429, le script attend 60 secondes et retente une seule fois. Au second refus, il cesse d'interroger : mieux vaut s'arrêter que se faire bannir.

Toute autre réponse inexploitable arrête l'interrogation à ce demi-coup : une erreur HTTP, un délai dépassé (`--timeout`), une réponse qui n'est pas du JSON, une redirection, une réponse sans liste de coups. La collecte, elle, continue : la table de l'explorateur s'arrête là, et Stockfish évalue toute la partie. Une réponse sans liste de coups passait pour une sortie de théorie, son coup joué à 0.0 %.

Sans jeton, la base `lichess` répond 401. Le script demande un jeton pour les deux bases, et s'arrête avant toute requête si le fichier manque.

Un jeton refusé, HTTP 401 à n'importe quel demi-coup, arrête toute l'exécution, avec le code de retour 1, avant le moteur : aucune autre réponse ne peut venir, et Stockfish tournait des minutes pour une collecte privée de sa section 2. Le message conseille de remplacer le jeton ou de relancer avec `--no-explorer`. La réponse reste dans `explorer/`, et le dossier de travail est gardé.

### Critères d'arrêt

Pour chaque demi-coup, la position AVANT le coup est interrogée, ce qui donne le rang et la fréquence du coup réellement joué.

L'interrogation s'arrête, dans cet ordre de test :

1. sur une erreur HTTP, une réponse inexploitable ou une position absente de la base.
2. sur un échantillon inférieur à `--min-games`.
3. sur une sortie de théorie, hors de la fenêtre `--min-moves`.
4. au plafond `--max-plies`, ou à la fin de la partie.

Un coup nul, "--" dans le PGN, arrête aussi l'interrogation, avant toute requête pour ce demi-coup et quel que soit le mode : ce n'est pas un coup des échecs, la base ne peut pas suivre la partie au-delà.

Il n'est pas compté comme une sortie de théorie, et la section 4 de la synthèse le signale.

### Sortie de théorie

Un coup est rare quand il est joué dans moins de `--min-frequency` pour cent des parties de la position.

Un coup rare est une sortie de théorie s'il mène à une position absente du catalogue des ouvertures. S'il reste dans une ligne que le catalogue connaît, ce n'en est pas une.

La première sortie est toujours notée. Elle n'arrête l'interrogation qu'après les `--min-moves` premiers coups, pour que la table couvre le début de la partie même après une sortie précoce.

### Catalogue des ouvertures

Le catalogue vient des cinq fichiers `a.tsv` à `e.tsv` du dépôt [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings).

`--install-catalog` les télécharge et rejoue chaque ligne avec python-chess. Un coup illisible ou illégal, ou une position nommée deux fois, arrête l'installation sans toucher au catalogue en place.

L'index est ensuite écrit dans `catalog.tsv`, dans le répertoire de `--catalog`. Il est écrit sous un nom provisoire, puis renommé : une collecte lancée pendant une mise à jour lit l'ancien index ou le nouveau, jamais un mélange.

```text
#format=2  date=2026-11-25T14:20:09+00:00  lines=3865  named=3865  known=7982  source=...
epd  eco  name
```

La première ligne décrit l'index, la deuxième nomme les colonnes, et chaque ligne suivante porte une position : son EPD, son code ECO et son nom, séparés par des tabulations. Les positions sont triées, si bien que deux installations du même catalogue donnent deux fichiers identiques.

Une position est repérée par son EPD, la case de prise en passant n'y figurant que si la prise est jouable : c'est aussi la règle du serveur de l'explorateur.

Le catalogue dit "connu", jamais "bon" : "Barnes Opening: Fool's Mate" y figure.

Il compte aussi les positions intermédiaires des lignes nommées, que l'explorateur ne nomme pas lui-même.

Ces positions intermédiaires ont un nom vide dans l'index. Le 25 novembre 2026, le catalogue comptait 3865 lignes nommées, soit 7982 positions connues en les comptant.

Au chargement, le format et le nombre de positions annoncés sont vérifiés : un index absent, abîmé ou tronqué arrête le script, qui donne la commande à relancer.

Un index du catalogue écrit avant la version 5.0.0, `catalogue.tsv`, n'est pas lu : relancez `--install-catalog`.

## 9. Moteur

### Dialogue avec Stockfish

Par défaut, le moteur est le binaire `stockfish` trouvé dans le PATH, sous Debian comme sous macOS. À défaut, c'est celui du paquet : `/usr/games/stockfish` sous Debian, que le PATH de root ne contient pas, et `/opt/homebrew/bin/stockfish` sous macOS. `--stockfish` en nomme un autre.

Le script pilote Stockfish par le protocole UCI, à travers python-chess. Il le lance deux fois :

1. avant la collecte, pour lire les bornes que le moteur annonce pour ses options, puis l'arrêter. Une valeur hors bornes est ainsi refusée tout de suite, et non après plusieurs minutes d'explorateur
2. pour l'analyse : il règle `Threads` et `Hash`, demande les chances de gain avec `UCI_ShowWDL` si le moteur connaît cette option, puis fait analyser chaque position jusqu'à la profondeur demandée

### Threads, Hash et MultiPV

| Option du script | Option UCI | Défaut du script | Défaut de Stockfish |
|---|---|---|---|
| `--threads` | `Threads` | le nombre de processeurs | 1 |
| `--hash` | `Hash` | 256 | 16 |
| `--multipv` | `MultiPV` | 3 | 1 |

**Threads, les fils.** C'est le nombre de fils d'exécution que le moteur emploie pour explorer une position. Plus il en a, plus vite il atteint la profondeur demandée. La documentation de Stockfish conseille de lui en donner autant que la machine a de cœurs : c'est le défaut du script.

Une conséquence à connaître : avec plusieurs fils, deux analyses de la même position ne rendent pas exactement les mêmes chiffres. Mesuré avec Stockfish 16 à la profondeur 16 : trois analyses identiques avec un fil, trois analyses différentes de quelques centipions avec quatre fils, l'ordre des meilleurs coups pouvant changer quand ils se valent. Deux collectes de la même partie diffèrent donc un peu. Pour des chiffres reproductibles, lancez le script avec `--threads 1`.

**Hash, la table de hachage.** En explorant, un moteur retombe sans cesse sur les mêmes positions par des ordres de coups différents. La table de hachage, ou table de transposition, garde le résultat des recherches déjà faites pour ne pas les refaire. `--hash` en fixe la taille, en mégaoctets. Trop petite, elle se remplit et le moteur recalcule. Trop grande pour la mémoire libre, le système refuse de l'allouer et le moteur s'arrête : le script le dit alors, et nomme `--hash`.

**MultiPV, les meilleurs coups.** Par défaut, un moteur ne cherche que la meilleure suite, sa "variante principale". Avec MultiPV, il en rend plusieurs, classées. Le script en demande 3, pour que la synthèse montre ce que le moteur préférait au coup joué. La recherche en est ralentie : la documentation de Stockfish conseille de laisser 1 pour la meilleure performance.

Si le coup joué ne figure pas parmi ces meilleurs coups, le script lance une seconde recherche, restreinte à ce seul coup, pour lui donner une évaluation et mesurer l'écart.

**La profondeur.** `--depth` arrête la recherche quand le moteur a atteint cette profondeur. Le temps de calcul croît très vite avec elle. Le script la borne à 60.

Les bornes sont celles que le moteur annonce. Stockfish 17.1 et Stockfish 19 admettent de 1 à 1024 pour Threads, de 1 à 33554432 pour Hash et de 1 à 256 pour MultiPV.

Sources : [options UCI de Stockfish](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html) pour Threads, Hash, MultiPV et UCI_ShowWDL, et [Transposition Table](https://www.chessprogramming.org/Transposition_Table), sur le wiki Chess Programming, pour la table de hachage. Les deux pages sont en anglais.

### Ce que le script tire des évaluations

- **L'évaluation** est donnée du point de vue des Blancs, en pions : `+0.35`. Un mat s'écrit `#+2`, les Blancs matent en deux coups, ou `#-1`, les Noirs matent en un coup.
- **Un mat se compte après le coup**, comme toute évaluation du tableau. Le moteur, lui, compte avant le coup, celui-ci compris : le script retire donc un coup au camp qui mate quand c'est lui qui vient de jouer. `#+0` ou `#-0` : le coup de la ligne donne mat.
- **L'écart** est ce que le coup joué perd par rapport au premier choix du moteur, en centipions, du point de vue du joueur au trait.
- **La nature** suit l'écart : `inaccuracy`, l'imprécision, à partir de 50, `mistake`, l'erreur, à partir de 100, `blunder`, la gaffe, à partir de 300.
- **Un écart négatif** n'est pas une faute. Le coup joué, évalué à part quand il n'est pas dans les premiers choix, sort alors un peu au-dessus du premier : les deux se valent. Au-delà de 10000, la recherche du coup joué a trouvé un mat que celle des meilleurs coups n'a pas vu : l'écart porte "mate", au lieu de quelque -99000 centipions.
- **Les mats** ne se chiffrent pas en centipions. Entre deux mats de même sens, mater en deux coups au lieu d'un par exemple, l'écart vaut 0. Un coup qui manque un mat ou en concède un porte l'écart "mate" et la nature "blunder".
- **W/D/L** donne les chances de gain, de nulle et de perte des Blancs. Ce sont celles du modèle de Stockfish, établi sur des parties du moteur contre lui-même : une tendance, et non une probabilité entre joueurs humains. Le moteur les donne pour mille ; le script les écrit en pourcentages entiers dont la somme vaut 100, par les plus forts restes : chaque part est arrondie par défaut, puis les points manquants vont aux plus forts restes. Arrondies une à une, 15, 970 et 15 pour mille donnaient 2/97/2. Les parts sont calculées pour les Blancs, puis échangées pour les Noirs, dont la vue reste le miroir de celle des Blancs.
- **Les variantes** s'écrivent en notation numérotée, celle du PGN : une variante qui commence par un coup noir se lit `8... Bg4`, avec une espace après les points. python-chess écrivait `8...Bg4`.
- **Un coup nul**, `--`, n'est pas évalué : ce n'est pas un coup des échecs, le moteur ne peut pas le juger. Sa ligne garde les meilleurs coups de la position.

### `stockfish/evaluations.json`

Le fichier est une liste, un objet par demi-coup évalué :

| Clef | Contenu |
|---|---|
| `ply`, `move_number`, `side_to_move` | le rang du demi-coup, le numéro du coup, "White" ou "Black" |
| `fen` | la position avant le coup |
| `played` | le coup joué et son évaluation |
| `best` | les meilleurs coups du moteur, dans l'ordre, autant que `--multipv` |
| `cp_loss` | l'écart en centipions. À partir de 10000, il ne mesure plus rien : l'un des deux coups est un mat |
| `category` | "inaccuracy", "mistake", "blunder", ou null |

Pour un coup nul, `played` porte `not_evaluated`, et `cp_loss` comme `category` valent null.

`played` et chaque élément de `best` portent les mêmes clefs :

| Clef | Contenu |
|---|---|
| `san`, `uci` | le coup, en notation algébrique et en notation UCI |
| `score` | l'évaluation du point de vue des Blancs, comme dans la synthèse |
| `value_for_side` | la même en centipions, du point de vue du joueur au trait. Un mat en n coups y vaut 100000 - n |
| `depth` | la profondeur atteinte |
| `pv_san`, `pv_uci` | la variante principale entière, que la synthèse coupe à `--pv-length` demi-coups |
| `wdl` | `win`, `draw` et `loss` des Blancs, en pour mille |

## 10. Fichiers produits

### Contenu de l'archive, en un coup d'œil

| Fichier | Contenu |
|---|---|
| `summary.md` | la synthèse, que l'analyste lit en premier |
| `game.pgn` | le PGN, en-têtes complétés s'il y a lieu |
| `game-original.pgn` | le PGN fourni, si des en-têtes manquaient |
| `context.md` | les réponses aux questions de démarrage |
| `explorer/NNN-<uci>.json` | une réponse brute par demi-coup interrogé |
| `stockfish/evaluations.json` | les évaluations complètes du moteur, variantes entières |
| `collection.json` | les paramètres exacts de la collecte, sans le jeton. `pgn_encoding` et `pgn_remarks` disent comment le PGN a été décodé, `prompt_written` nomme le prompt |

Le prompt, `analysis-<label>-<YYYYMMDD-HHMMSS>.prompt.txt`, est écrit à côté de l'archive, et non dedans.

### Dossier de travail et archive

Le dossier de travail s'appelle `analysis-<label>-<YYYYMMDD-HHMMSS>`. L'étiquette `<label>` est le nom du PGN sans son extension, assaini (section 11), ou l'identifiant Lichess : une étiquette assainie est annoncée dans le journal par "Folder name sanitized: ...". Un dossier ou une archive du même nom fait ajouter un suffixe, -2, -3 et ainsi de suite.

Une archive présente sous son nom définitif est toujours complète et vérifiée : elle est écrite sous le nom provisoire `.<folder>.partial.zip`, puis renommée.

Il en va de même de chaque fichier du dossier de travail, écrit sous `.<name>.partial`. Après une interruption (Ctrl-C) ou un échec, ces fichiers provisoires sont retirés et le dossier de travail reste, sans archive.

### `game.pgn` et `game-original.pgn`

`game.pgn` est le PGN fourni, converti en UTF-8 s'il ne l'était pas.

Si vos réponses ont complété une balise White ou Black, `game.pgn` porte la partie réécrite par python-chess avec ses nouvelles balises, et `game-original.pgn` garde le texte fourni.

### `collection.json`

Le fichier garde les paramètres exacts de la collecte : toutes les options de la ligne de commande, sous leur nom, les tirets devenant des soulignés, plus ces clefs :

| Clef | Contenu |
|---|---|
| `token_present` | vrai si un jeton a été lu. Le jeton lui-même n'y figure jamais |
| `catalog_used` | la description du catalogue : date, nombre de lignes et de positions |
| `side` | votre camp, son origine, déduit ou déclaré, et les balises complétées |
| `context_collected` | vrai si vous avez répondu aux questions |
| `pgn_encoding`, `pgn_remarks` | comment le PGN a été décodé |
| `prompt_written` | le nom du prompt, ou null avec `--no-prompt` |

`usernames` y porte les pseudos réellement employés, ceux de `--usernames` ou ceux des réglages.

Un chemin sous votre dossier personnel y est écrit avec `~`, comme la source et le moteur dans `summary.md` : le nom de ce dossier, votre identifiant le plus souvent, ne part pas vers le LLM avec l'archive.

### `summary.md`

Sections de `summary.md`, sous leur titre anglais :

| Section | Contenu |
|---|---|
| Analysis instructions | `context.md`, vos réponses aux questions de démarrage. Absente quand elles ne sont pas posées |
| 1. Headers and moves of the game | en-têtes, ligne principale, repères de phase (roques, dames, entrée en finale) |
| 2. Explorer of the ... database, exit from theory | filtres, seuils, table, première sortie |
| 3. Stockfish evaluations | nature et W/D/L de chaque coup |
| 3a. Principal variations of the engine | les variantes principales du moteur |
| 3b. Mistakes and blunders by side | erreurs et gaffes par camp, avec la FEN |
| 4. Positions with an unusable sample | là où la base ne dit plus rien, ou le demi-coup d'un coup nul |
| 5. Raw data of the archive | le contenu du zip, et l'encodage du PGN s'il a été converti. Le dossier `explorer/` n'y figure que s'il existe |

**Table de l'explorateur**, une ligne par demi-coup, sous les colonnes `#`, `Move`, `Side`, `Pos. games`, `Played`, `Rank`, `Freq.`, `White score`, `Top move`, `Top freq.`, `Top White score` et `Opening` :

- demi-coup, numéro du coup, trait
- parties de la position
- coup joué, son rang, sa fréquence, le score des Blancs sur ce coup
- coup majoritaire, sa fréquence et son score
- Opening : nom ECO de la position atteinte, "(intermediate)" pour une position de passage d'une ligne nommée, "-" hors catalogue

**Table Stockfish**, une ligne par demi-coup, sous les colonnes `#`, `Move`, `Side`, `Played`, `Eval`, `W/D/L`, `CP loss`, `Category`, `1st`, `2nd` et `3rd` :

- demi-coup, numéro du coup, trait, coup joué
- évaluation, du point de vue des Blancs
- W/D/L : chances de gain, de nulle et de perte des Blancs selon le modèle de Stockfish, à lire comme une tendance plutôt que comme une probabilité entre joueurs humains
- écart au premier choix du moteur, du point de vue du joueur au trait
- nature : inaccuracy à partir de 50 cp d'écart, mistake à partir de 100, blunder à partir de 300
- les trois meilleurs coups

Trois cas particuliers :

- l'écart porte "mate" quand le coup joué manque un mat, en concède un, ou en trouve un que la recherche des meilleurs coups n'a pas vu : il ne se chiffre pas en centipions
- sous le tableau, une ligne "Result and final evaluation contradict each other" apparaît quand le camp déclaré vainqueur est nettement moins bien après le dernier coup, d'au moins 300 cp : la partie ne s'est pas décidée sur l'échiquier, et l'analyste doit le dire au lieu de raconter une victoire méritée
- un coup nul, "--" dans le PGN, n'est pas évalué : sa ligne garde les trois meilleurs coups de la position, ses autres colonnes portent "-"

## 11. Encodages et caractères

Aucune entrée mal encodée ne doit arrêter le script sur une trace Python : au pire, une ligne "Warning" du journal et une dégradation propre.

PGN, modèle de prompt et fichier de jeton, essais dans cet ordre :

1. marque d'ordre des octets (BOM) UTF-8, UTF-16 ou UTF-32
2. UTF-32 sans marque, reconnu à ses trois octets nuls sur quatre
3. UTF-16 sans marque, reconnu à son octet nul sur deux
4. UTF-8
5. UTF-8 abîmé : au moins un caractère accentué correctement codé et au plus quatre octets invalides pour chacun d'eux, ces octets deviennent U+FFFD
6. cp1252, puis latin-1, qui accepte n'importe quel octet

Hors UTF-8 sans défaut, le journal nomme l'encodage retenu :

```text
Warning, PGN: the content is not UTF-8, encoding used: cp1252.
```

Les fins de ligne CRLF et CR sont ramenées à LF. Les caractères de contrôle, NUL compris, sont retirés et comptés dans le journal, la tabulation et le saut de ligne sont conservés.

Le fichier `game.pgn` est donc toujours de l'UTF-8 propre : si le fichier fourni a dû être converti, la section 5 de la synthèse le dit, et `collection.json` garde le détail.

Un texte latin-1 se décode aussi sans erreur en cp1252, les deux ne différant que sur les octets 0x80 à 0x9F : c'est cp1252 qui est annoncé.

Un PGN qui n'est ni en UTF-8, ni en UTF-16, ni en cp1252 est refusé, avec le conseil de le convertir. Le script le reconnaît à l'un des cinq octets que cp1252 ne définit pas.

Un PGN en UTF-16 ou en UTF-32 dont les octets ne forment pas tous des caractères est refusé aussi : dans ces encodages, un caractère tient sur deux ou quatre octets, et un seul octet perdu, par un transfert coupé par exemple, décale tout le texte qui suit. Le refus nomme l'encodage. Il reprochait auparavant à un U+FFFD de ne pas être un coup, ou à une accolade de n'être jamais fermée, la cause restant dans la ligne "Warning" de l'encodage. En UTF-8, un octet invalide n'abîme qu'un caractère : l'UTF-8 abîmé de l'étape 5 reste accepté.

Limite : un fichier en cp850 ou en MacRoman qui ne contient aucun de ces cinq octets passe pour du cp1252. Ses lettres accentuées sortent fausses dans les noms et les commentaires, et rien ne permet de le voir. Les coups, écrits en ASCII, restent justes.

Balises du PGN (White, Black, Event, Site et les autres) : tabulations et caractères de contrôle en sont retirés avant l'écriture des en-têtes de la synthèse et avant tout affichage.

Autres lectures :

- le fichier de jeton suit la même détection que le PGN, et un jeton hors de l'ASCII imprimable est refusé avant toute requête
- le catalogue et les réponses de l'explorateur sont lus en UTF-8, marque d'ordre des octets tolérée
- la sortie du moteur est décodée en UTF-8 par python-chess, qui écarte une ligne illisible sans s'arrêter

Rien ne dépend de la locale.

Écritures : tous les fichiers de l'archive sont en UTF-8, fins de ligne LF.

Dans l'étiquette de l'archive, les caractères de contrôle, les caractères `/ \ : * ? " < > |` et les octets non décodables du nom du PGN deviennent "\_", et les espaces des tirets : `game against machine.pgn` donne `analysis-game-against-machine-...`. L'étiquette est bornée à 80 octets.

Les lettres accentuées sont conservées.

Console : un caractère que le terminal ne sait pas afficher devient "?" au lieu d'arrêter le script, sous LANG=C comme avec PYTHONIOENCODING=ascii.

Le chemin de l'archive est écrit en octets sur la sortie standard : ARCHIVE=$(...) reste exact dans tous les cas.

Questions de démarrage : une réponse saisie dans un autre encodage que celui du terminal est redécodée, cp1252 puis latin-1.

## 12. Modèle de prompt

Le prompt de chaque partie est tiré d'un modèle : `prompt-template.txt`, ou `prompt-only-template.txt` avec `--prompt-only`. Vous pouvez les modifier, ou désigner le vôtre avec `--prompt`.

Le prompt décrit toujours la synthèse que cette version du script vient d'écrire : les deux ne peuvent pas diverger.

Deux sortes de repères sont interprétés :

| Repère | Effet |
|---|---|
| `{{NAME}}` | une valeur, remplacée |
| `#! if CONDITION` | garde ce qui suit si la condition est vraie |
| `#! if not CONDITION` | garde ce qui suit si elle est fausse |
| `#! else` | bascule |
| `#! end` | ferme le dernier "if" ouvert |
| `#! note ...` | commentaire du modèle, jamais recopié |

Une directive occupe une ligne entière, et les "if" peuvent s'emboîter. Les lignes vides laissées par un passage retiré sont resserrées.

Dans les modèles du dépôt, les lignes de texte sont coupées à 71 colonnes, telles que le prompt les montre. Une phrase qu'une condition coupe se poursuit par des lignes entières dans chaque branche, même si leur début se répète : le prompt garde une coupure régulière quelles que soient les conditions, ce que vérifie le test T92.

Valeurs :

| Valeur | Contenu |
|---|---|
| `VERSION` | version du script |
| `REPOSITORY` | adresse du dépôt d'IAnalyze |
| `ARCHIVE` | nom du fichier de l'archive |
| `USERNAMES` | vos pseudos, séparés par des virgules |
| `SIDE` | White, Black ou unknown |
| `RATING` | votre niveau, rédigé : "about 1300 Elo, declared by the player", sinon l'Elo de votre balise, sinon "unspecified: judge from the game, and stay accessible" |
| `TIME_CONTROL` | votre cadence habituelle, rédigée |
| `ANNOTATOR` | valeur de la balise Annotator |
| `DATABASE` | base interrogée : "Lichess (all players)" ou "masters" |
| `INACCURACY_THRESHOLD`, `MISTAKE_THRESHOLD`, `BLUNDER_THRESHOLD` | seuils de nature du coup, en centipions : 50, 100 et 300 |
| `DEPTH`, `MULTIPV` | valeurs de `--depth` et de `--multipv` |
| `GAME_PGN` | le PGN de la partie, tel que l'archive le contient |
| `ENGINE_TABLE` | les évaluations de Stockfish, une ligne par demi-coup. Derrière un coup faible : sa nature, son écart, le meilleur coup, sa suite sur `--pv-length` demi-coups et son évaluation |
| `RESULT_ALERT` | la phrase qui signale un résultat contraire à l'évaluation finale, vide sinon |
| `PLAYER_INSTRUCTIONS` | celles de vos réponses aux questions de démarrage que vous n'avez pas laissées par défaut |
| `OPENING` | l'ouverture et la sortie de théorie en une phrase, d'après l'explorateur |
| `PLIES` | nombre de demi-coups de la partie |
| `PLIES_EVALUATED` | nombre de demi-coups que le moteur a évalués, plus petit avec `--stockfish-moves` |
| `PLAYER_WEAK_MOVES` | nombre de vos coups que `ENGINE_TABLE` marque inaccuracy, mistake ou blunder, "unknown" si votre camp ne l'est pas |
| `FENCE` | clôture du bloc de code qui contient `GAME_PGN` : une suite d'accents graves plus longue que toute suite de la partie, trois au moins |

Conditions :

| Condition | Vraie quand |
|---|---|
| `STOCKFISH` | toujours, depuis la version 4.0.0. Gardée pour les modèles personnels qui l'emploient |
| `EXPLORER` | la section 2 a été collectée |
| `LICHESS_DATABASE` | base de tous les joueurs |
| `MASTERS_DATABASE` | base des maîtres |
| `ANSWERS` | le script a recueilli vos réponses aux questions de démarrage |
| `SIDE_KNOWN` | votre camp est connu |
| `USERNAME_KNOWN` | au moins un pseudo est connu |
| `RATING_DECLARED` | votre niveau figure dans les réglages |
| `RESULT_CONTRADICTED` | le résultat de la partie contredit l'évaluation finale |
| `INSTRUCTIONS_GIVEN` | `PLAYER_INSTRUCTIONS` n'est pas vide |
| `OPENING_KNOWN` | `OPENING` n'est pas vide |
| `PARTIAL_COVERAGE` | `--stockfish-moves` a limité le moteur aux premiers coups |
| `NULL_MOVE` | la partie contient un coup nul, noté `--` |
| `FEW_WEAK_MOVES` | votre camp est connu et `PLAYER_WEAK_MOVES` est inférieur à trois |
| `NO_WEAK_MOVE` | votre camp est connu et `PLAYER_WEAK_MOVES` vaut zéro |

`STOCKFISH`, `MASTERS_DATABASE` et `RATING_DECLARED` ne servent à aucun des deux modèles du dépôt : elles sont gardées pour les modèles personnels.

Les deux modèles, `prompt-template.txt` et `prompt-only-template.txt`, partagent ces repères. `GAME_PGN`, `ENGINE_TABLE`, `RESULT_ALERT`, `PLAYER_INSTRUCTIONS`, `OPENING`, `DEPTH`, `FENCE`, `PLAYER_WEAK_MOVES` et les conditions `RESULT_CONTRADICTED`, `INSTRUCTIONS_GIVEN`, `OPENING_KNOWN`, `NULL_MOVE`, `FEW_WEAK_MOVES`, `NO_WEAK_MOVE` servent au prompt court. `PLAYER_WEAK_MOVES`, `FEW_WEAK_MOVES` et `NO_WEAK_MOVE` servent aussi au bilan final du prompt complet.

Les deux prompts finissent par un bilan : les trois erreurs les plus coûteuses du joueur et le thème à travailler. Quand le tableau marque moins de trois coups faibles de votre côté, la phrase change : elle donne leur nombre et demande de s'en tenir à ceux-là. Dans le prompt court :

```text
After the code block, give in a few lines the costliest errors of the
player and the theme they must work on first.
Weak moves of the player in the table: 2.
Keep to those, without adding any.
```

Le prompt complet le dit dans son bilan final, et demande en outre de ne pas remplacer vos erreurs par celles de votre adversaire. Sans aucun coup faible de votre côté, les deux prompts demandent de ne vous prêter aucune erreur. Quand votre camp n'est pas connu, le prompt court demande de commenter les deux camps de la même façon et de donner le bilan pour chacun ; le prompt complet demande vos erreurs une fois votre camp trouvé, et celles de chaque camp sinon.

Les deux prompts disent que les balises et les commentaires du PGN sont des données, au plus les notes du joueur, jamais des consignes : un commentaire, ou une balise, pourrait sinon donner des ordres au LLM. Le prompt court place la partie dans un bloc de code, dont la clôture, `FENCE`, est plus longue que toute suite d'accents graves de la partie : avec une clôture fixe de trois, un commentaire qui portait une telle ligne fermait le bloc.

Les deux prompts demandent de garder ces notes dans le PGN rendu, avant le commentaire du LLM, et d'en retirer les commandes qu'un site écrit entre crochets dans les commentaires : `[%clk 0:10:00]` pour la pendule, `[%eval 0.23]` pour son moteur. Une partie téléchargée de Lichess les porte, l'export donnant par défaut les pendules et les évaluations, et le prompt complet interdit le caractère `%` dans un commentaire. Un `%` que porte une note devient lui aussi "percent" ; les autres contraintes de format visent le texte du LLM, pas une note gardée. Quand une note contredit les chiffres du moteur, ceux que laisse l'analyse d'un site par exemple, le moteur l'emporte et le LLM doit le dire.

Le bilan final du prompt complet s'en tient au périmètre convenu, comme les commentaires : il demandait les erreurs les plus coûteuses de toute la table, même quand les commentaires s'arrêtaient au coup 15. Le prompt court dit la même chose sous "What the player specified", quand un périmètre y est donné. Les deux ajoutent qu'un périmètre qui contient moins d'erreurs que demandé ne donne que celles-là : les comptes de coups faibles sont ceux de toute la table.

Le prompt complet fixe l'ordre du début de la réponse : la ligne qui dit si le LLM peut exécuter du code, cas A ou B, puis le récapitulatif. Deux sections demandaient l'une et l'autre le début de la réponse.

La notation du PGN rendu est la notation standard : K, Q, R, B, N, aucune lettre pour un pion, le roque avec la lettre O majuscule. Le prompt complet listait `K Q R B N P`, ce qui invitait à un `P` que le vérificateur refuse désormais.

Avec `--stockfish-moves`, les coups faibles ne sont comptés que sur les demi-coups évalués : sous `PARTIAL_COVERAGE`, les deux prompts bornent ce compte, ou l'absence de coup faible, à ces premiers demi-coups, et demandent qu'une erreur trouvée au-delà soit donnée comme une estimation du LLM, sans chiffre. Sans cette borne, un joueur sans coup faible dans la fenêtre évaluée était dit sans erreur sur toute la partie.

La raison vient des essais du 21 novembre 2026 ([TRIALS.fr.md](TRIALS.fr.md#le-21-novembre-2026-avec---prompt-seul-aujourdhui---prompt-only)) : le joueur n'avait commis que deux erreurs, et trois réponses sur cinq en ont présenté une troisième pour arriver au compte demandé. Un essai du prompt complet, le 25 novembre 2026, a montré l'autre dérobade : prié de donner "les trois erreurs les plus coûteuses" sans qu'on lui dise de qui, le LLM a donné celles de l'adversaire, et laissé de côté l'un des deux coups faibles du joueur.

Un repère inconnu ou mal écrit, comme `{{ RATING }}`, un "if" jamais fermé, une directive mal formée ou un modèle sans une ligne de texte arrêtent le script avant la collecte :

```text
Prompt template prompt-template.txt, line 12: unknown condition ENGINE, accepted conditions: STOCKFISH, EXPLORER, ...
```

Le contrôle du modèle a lieu avant la collecte, pour ne pas la faire pour rien.

Un fichier désigné par `--prompt` doit exister. Le modèle par défaut, lui, peut manquer quand le script a été copié seul : la collecte se fait alors sans prompt, et le journal le signale. Avec `--prompt-only`, dont le prompt est le but, le script s'arrête.

Avec `--prompt-only`, le modèle doit placer `{{GAME_PGN}}` dans une ligne de texte, et non dans une note : sans la partie, le prompt n'aurait rien à faire analyser. Si le repère est placé sous une condition qui ne s'applique pas à la partie, le prompt est écrit, mais le journal prévient qu'il ne peut pas être collé seul.

Un modèle écrit avant la version 5.0.0, avec les directives `si`, `sinon` et `fin` et les valeurs françaises, est refusé de la même façon, à son premier repère de l'ancien langage, `{{DEPOT}}` par exemple : ses directives, ses conditions et ses valeurs sont à renommer.

## 13. Le vérificateur en détail

Le README dit comment lancer le script. Cette section donne ce qu'il contrôle et ses règles exactes.

### Ce qui est contrôlé, en un coup d'œil

| Contrôle | Défauts relevés |
|---|---|
| Lecture | fichier hors UTF-8, coup illégal dans la partie ou dans une variante, ligne vide dans le corps de la partie, seconde partie dans le fichier |
| Ligne principale | différente de la partie d'origine |
| Format | ligne de plus de 79 caractères, accolade ouvrante ou fermante dans un commentaire, mot hors des accolades, coup écrit avec un `P`, roque écrit avec des zéros, `%`, tiret cadratin, notation suffixe, balises absentes ou dans le désordre, marqueur de fin |
| Coups commentés | erreur ou gaffe de Stockfish laissée sans commentaire dans le périmètre convenu, NAG de position contraire à l'évaluation du moteur ; pour information, les NAG de qualité d'un autre avis que le moteur. Les notes que la partie d'origine portait déjà, que les deux prompts demandent de garder, sont d'abord mises de côté : seul le texte du LLM est jugé |
| Évaluations | chiffre ou mat cité qui n'existe nulle part dans les données du moteur ; un `#7` sans signe, qui peut être un rang, n'est qu'un avertissement |
| Variantes | variante écrite à l'intérieur d'un commentaire, donc non jouable, variante illégale ou trop longue |
| Conversation | FEN invalide ou étrangère à la partie, tiret cadratin |

### Trois défauts vus dans de vrais PGN

- **La ligne vide dans le corps de la partie.** python-chess y voit la fin de la partie et n'en lit pas la suite. Le script la relève où qu'elle soit, même si elle ne cache qu'une variante ou le marqueur de fin, puis poursuit ses contrôles sur le fichier une fois la ligne retirée. Dans un commentaire, python-chess lit jusqu'à l'accolade fermante : le bilan le dit, et compte la ligne comme une faute tout de même, le prompt l'interdisant et un autre lecteur s'y arrêtant.
- **Les mots hors des accolades.** python-chess les saute sans rien dire : un texte libre écrit entre deux coups est perdu, et un coup écrit `Pg2xf3`, ou un roque écrit `0-0`, est lu quand même, ce qui cache la faute. Le script nomme chacun de ces mots, ligne par ligne.
- **La variante écrite entre accolades.** Ce n'est que du texte, SCID ne la rejoue pas. Le script la rejoue lui-même pour dire si elle est légale et si elle vient d'une ligne du moteur.

### Ce qu'il lit

Trois fichiers de l'archive : `game.pgn`, `summary.md` et `stockfish/evaluations.json`. Il les prend dans le zip, ou dans un dossier : le dossier de travail lui-même, ou celui qui le contient.

Les trois fichiers viennent toujours de la même collecte. Dans un dossier parent, seule une collecte complète est retenue, et le bilan la nomme : une collecte interrompue rangée à côté est ignorée. Si le dossier en contient plusieurs complètes, le script s'arrête et les nomme, plutôt que d'en choisir une.

Si l'un d'eux manque, ou si l'archive ne se lit pas, aucun contrôle n'a lieu et le code de retour vaut 2. Une archive écrite avant la version 5.0.0, avec ses noms français, est dans ce cas.

Comme `ianalyze.py`, il se relance dans l'environnement virtuel quand python-chess manque, mais seulement à son emplacement par défaut : il n'a pas d'option `--venv`.

Du PGN rendu, python-chess ne lit que la première partie : une seconde dans le fichier est signalée comme un échec, rien d'elle n'étant contrôlé. Un résultat répété seul à la fin n'est pas une partie, comme pour `ianalyze.py`. Les lignes vides du corps sont retirées pour les contrôles qui suivent, mais seulement dans le corps de la première partie : la ligne vide qui ouvre les balises d'une autre partie reste, alors que son retrait fondait les deux parties en une.

### Repères du bilan

| Repère | Compte comme | Exemple |
|---|---|---|
| `FAIL` | un échec, le code de retour vaut 1 | une erreur de Stockfish laissée sans commentaire |
| `WARNING` | un point à regarder, sans échec | une variante de plus de 5 demi-coups |
| `INFO` | une mesure | le nombre de coups commentés |
| `OK` | un contrôle passé | |

Le bilan se termine par ses totaux, sous `=== Totals ===` : le nombre d'échecs, `failures`, et d'avertissements, `warnings`.

Code de retour : 0 sans `FAIL`, 1 avec au moins un `FAIL`, 2 si aucun contrôle n'a pu avoir lieu.

### Règles chiffrées

- **Lignes** : 79 caractères au plus.
- **Résumé** : un commentaire avant le premier coup. Son absence est un échec.
- **Signes interdits dans un commentaire** : accolade, signe pour cent, tiret cadratin. Un point-virgule vaut `WARNING`.
- **Hors des commentaires** : seulement des coups en notation standard, des numéros de coup, des NAG, les parenthèses des variantes et le résultat. Tout autre mot est un échec, nommé avec sa ligne : un texte libre, que python-chess saute sans rien dire, un coup écrit `Pg2xf3`, qu'il lit `g2xf3`, un coup écrit avec un tiret entre ses cases. La règle est plus stricte que celle d'`ianalyze.py`, qui lit les PGN de tous les sites. Le roque écrit avec des zéros, `0-0`, que python-chess lit `O-O`, est un échec à part, hors `--prompt-only`. Les mots d'un commentaire coupé trop tôt par une accolade fermante restent comptés dans ce seul défaut.
- **Ligne vide** : dans le corps de la partie, c'est un échec. Dans un commentaire, python-chess poursuit sa lecture jusqu'à l'accolade fermante : le bilan le dit, le prompt interdisant la ligne tout de même.
- **Balises** : les sept obligatoires en tête et dans l'ordre, leurs valeurs reprises de la partie d'origine. Les autres par ordre alphabétique, Annotator renseignée et PlyCount exact, sinon `WARNING`.
- **Notes de la partie d'origine** : les deux prompts demandent de les garder avant le commentaire du LLM. Le script les retire d'abord de chaque commentaire, avant le coup 1 et après chaque coup de la ligne principale, quels que soient les sauts de ligne, après un trait d'union compris, les commandes d'un site retirées et un `%` écrit "percent" ou non. Ce qui reste est le texte du LLM, le seul jugé : un chiffre cité dans une note n'est pas une évaluation inventée, et un coup qui ne porte que sa note d'origine n'est pas commenté. Le bilan compte les notes gardées.
- **Coups commentés** : chaque erreur et chaque gaffe de Stockfish doit l'être. L'une d'elles commentée sans NAG compte comme `WARNING`, hors `--prompt-only`. Le nombre total de coups commentés est donné pour information, le prompt en visant 15 à 25.
- **Périmètre** : le prompt limite les commentaires au périmètre convenu. Une erreur jouée au-delà n'est pas attendue. Le périmètre est le premier nombre de votre réponse à la question de démarrage, lue dans les consignes de `summary.md` : "the first 20 moves" vaut 20 coups, mais "moves 15 to 30" vaut les 15 premiers coups : donnez `--scope` quand il ne convient pas. Une réponse sans nombre, ou laissée par défaut, vaut la partie complète. `--scope N` le donne à la main, quand il a été convenu dans la conversation.
- **NAG de position** : `$14`, `$16`, `$18` et `$20` donnent les Blancs mieux, `$15`, `$17`, `$19` et `$21` les Noirs. Un tel NAG est contraire au moteur quand celui-ci donne l'autre camp mieux d'au moins un demi-pion, ou un mat. `$10`, position égale, n'est pas comparé : posé sur une position gagnée, il passe.
- **NAG de qualité** : `$6` pour une imprécision, `$2` pour une erreur, `$4` pour une gaffe. Un autre avis que celui du moteur est donné pour information, avec le coup et sa perte : un autre de ces trois NAG, `$1` ou `$3` sur une erreur ou une gaffe, ou `$6`, `$2` ou `$4` sur un coup que le moteur ne classe pas, sa perte restant sous 50 cp.
- **Variantes** : 5 demi-coups au plus, sinon `WARNING`. Une variante est dite appuyée sur le moteur quand ses deux premiers coups sont ceux d'une ligne que le moteur donne pour ce demi-coup.
- **Positions citées dans la conversation** : une FEN doit être valide et venir d'une position de la partie, reconnue à ses quatre premiers champs une fois écrite comme l'écrit python-chess : la case en passant, que la norme écrit après toute poussée de deux cases, ne compte que si la prise peut être jouée. Deux FEN sont demandées, sinon `WARNING`.

### Évaluations citées

Une évaluation se reconnaît à son signe : `+0.35`, `-1,20`, `+ 0.35`, le signe moins typographique, ou `#-3` pour un mat. Un nombre sans signe n'en est pas une, sauf pour un mat : `#2` est lu comme `#+2`, la forme du dossier.

Elle doit exister dans `evaluations.json`, pour le coup joué ou pour l'un des meilleurs coups, telle quelle ou arrondie à une décimale : `+0.35` peut être cité `+0.4` ou `+0.3`. Une troisième décimale nulle n'ajoute rien : `+0.350` se lit `+0.35` ; toute autre troisième décimale est une précision que le moteur n'a pas donnée. Un `#7` sans signe qui ne s'y trouve pas n'est qu'un `WARNING` : ce peut être un rang, "mistake #7", aussi bien qu'un mat.

Un écart que le LLM a calculé entre deux évaluations, `+1.77`, n'existe nulle part dans les données : il est signalé comme inventé, au même titre qu'un chiffre forgé.

Le bilan cite le PGN et le texte rendus par le LLM : leurs caractères de contrôle y sont montrés en `?`, jamais joués par le terminal. Un caractère que la sortie ne sait pas représenter devient `?` lui aussi, et le bilan va jusqu'au bout.

### Avec `--prompt-only`

Le prompt court demande moins que le prompt complet. Les contrôles qu'il ne demande pas sont sautés : longueur des lignes, résumé, NAG, signe pour cent, point-virgule, tiret cadratin, notation suffixe, roque écrit avec des zéros, ordre alphabétique des autres balises, balises Annotator et PlyCount, longueur des variantes. Le prompt court demande de recopier les coups tels quels : une partie exportée avec `0-0` reste fidèle avec eux. Les mots hors des accolades, eux, sont contrôlés : le prompt court demande les commentaires entre accolades. Avec `--summary`, le tiret cadratin de la conversation et le nombre de FEN ne sont pas contrôlés non plus : une FEN citée doit seulement être valide et venir de la partie.

Les balises sont contrôlées autrement. Le prompt complet veut les sept balises obligatoires du standard PGN, dans leur ordre. Le prompt court demande seulement de recopier celles de la partie : parmi les sept, seules celles que porte la partie d'origine sont attendues, dans l'ordre où elle les écrit.

Les mots hors des accolades sont eux aussi contrôlés autrement. Le prompt court demande de recopier les coups sans en changer un seul : un mot que la partie d'origine écrit elle-même hors de la notation standard, `e2-e4` ou `bxa8Q`, que lit `ianalyze.py`, est accepté tel quel.

### Ce qu'il ne juge pas

Il ne juge pas la qualité du commentaire. Une explication fausse mais bien formée passe : un LLM peut placer une dame sur la mauvaise case dans une phrase sans qu'aucun contrôle ne le voie.\
Cette lecture reste la vôtre, et [TRIALS.fr.md](TRIALS.fr.md) montre combien elle est nécessaire.

Deux limites s'ajoutent à celles que donne chaque règle plus haut, les évaluations arrondies, les écarts calculés, les NAG de position comparés et le périmètre lu :

- Un nombre écrit sans signe, "7.77", n'est pas pris pour une évaluation : le script le confondrait avec une durée ou un classement. Un chiffre inventé écrit ainsi passe donc
- Le script repère un chiffre qui n'existe nulle part, pas un vrai chiffre attribué au mauvais coup

## 14. Sources et liens

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

## 15. Reprendre le projet

Cette section s'adresse à qui reprend le code : comment il est organisé, comment le modifier sans le casser, et comment une version est publiée.

### Organisation d'`ianalyze.py`

Le script tient en un seul fichier, déroulé tout entier par `main()`, dans cet ordre :

1. Les options, lues par `analyser_arguments()`, qui construit la ligne de commande avec argparse, par groupes, puis contrôle leur cohérence.
2. Les actions qui s'arrêtent là : `--install-venv`, par `installer_venv()`, et `--purge-settings`.
3. La relance dans l'environnement virtuel, quand python-chess ne s'importe pas : `relancer_dans_venv()` relance le script avec le Python de l'environnement, et un marqueur dans l'environnement empêche une boucle. `--install-catalog`, par `installer_catalogue()`, vient après : il a besoin de python-chess.
4. Les réglages : `lire_reglages()`, ou `reglages_vides()` avec `--no-settings`.
5. Le modèle de prompt, contrôlé avant toute collecte : `chemin_modele()`, puis `verifier_modele()`.
6. La partie : `lire_fichier_texte()` et `decoder_octets()` pour un fichier local, `extraire_id()` et `telecharger_pgn()` pour Lichess, puis `charger_partie()`, qui passe d'abord par le contrôle lexical de `controler_lexique()`.
7. Le jeton et le catalogue, sans `--no-explorer` : `lire_jeton()`, `lire_catalogue()`.
8. Le moteur, contrôlé avant les questions : `verifier_moteur()`, `verifier_options_moteur()`.
9. Les questions de démarrage : `completer_reglages()`, `completer_entetes()`, `recueillir_contexte()`. Chaque réponse passe par `demander()`.
10. Le dossier de travail, puis l'explorateur, `collecter_explorateur()` avec la classe `Explorateur`, et le moteur, `collecter_stockfish()`.
11. Les fichiers : `collection.json`, `summary.md` par `ecrire_synthese()`, l'archive par `archiver()`, puis le prompt, tiré par `rendre_modele()`.

Le chemin qu'`annoncer_archive()` écrit seul sur la sortie standard est celui de l'archive, ou du prompt avec `--prompt-only`.\
Chaque fichier texte est écrit par `ecrire_texte()`, sous un nom provisoire, `.<name>.partial`, puis renommé : aucun fichier n'est jamais laissé à moitié écrit (section 10).

### Les tables à connaître

| Nom | Rôle |
|---|---|
| `VERSION` | la version du script, seul endroit à changer : le User-Agent `UA` en dérive |
| `CLEFS_COLLECTE` | pour chaque option, sa clef dans `collection.json` : les dest d'argparse restent en français dans le code, l'archive est en anglais |
| `PROMPT_CONDITIONS`, `PROMPT_VALEURS` | les conditions et les valeurs qu'un modèle peut employer (section 12), calculées dans `main()` |
| `REGLAGES_CLEFS` | les clefs de `settings.ini`, avec leurs commentaires |
| `SEUIL_IMPRECISION`, `SEUIL_ERREUR`, `SEUIL_GAFFE` | les écarts, en centipions, à partir desquels un coup est une imprécision, une erreur ou une gaffe : 50, 100 et 300 |
| `EXEMPLES` | les exemples de la fin de `--help` |

### Ajouter une option

1. La déclarer dans son groupe d'`analyser_arguments()`, avec son contrôle après la lecture de la ligne de commande s'il lui en faut un.
2. Lui donner sa clef dans `CLEFS_COLLECTE` : le nom de l'option sans ses deux tirets de tête, ses traits d'union devenant des soulignés, `no_questions` pour `--no-questions`. T87 échoue tant qu'une option n'a pas de clef, ou qu'une clef n'a pas d'option.
3. Si elle a une valeur par défaut dans les réglages, comme `--usernames` : `REGLAGES_CLEFS` et `completer_reglages()`.
4. Si le prompt s'en sert : une condition ou une valeur, ajoutée à `PROMPT_CONDITIONS` ou à `PROMPT_VALEURS` et calculée dans `main()`.
5. Un test dans `tests/test-app.sh`, et la documentation dans les deux langues : [EXAMPLES.fr.md](../EXAMPLES.fr.md) avec sa sortie réelle, le README si l'usage courant change, ce document, et la ligne du test dans [TESTS.fr.md](TESTS.fr.md). Le CHANGELOG sous Unreleased.

### Le vérificateur

`verify-analysis.py` lit l'archive avec `lire_archive()`, puis fait ses contrôles dans l'ordre de son bilan :

| Section du bilan | Fonction |
|---|---|
| 1. Reading the PGN | `controler_lecture()` |
| 2. Main line | `controler_partie()`, puis `retirer_notes()`, qui met de côté les notes de la partie d'origine |
| 3. Format | `controler_format()` |
| 4. Commented moves | `controler_couverture()` |
| 5. Evaluations quoted in the PGN | `controler_chiffres()` |
| 6. Variations | `controler_variantes()` |
| 7. Conversation: positions quoted, language | `controler_synthese()`, avec `--summary` |
| 8. Evaluations quoted in the conversation | `controler_chiffres()` à nouveau |

Les sections 4 et 6 n'ont lieu que sur une ligne principale identique à la partie d'origine. `afficher()` écrit le bilan et ses totaux.\
Le mode court, `--prompt-only`, saute ce que le prompt court ne demande pas (section 13).

### La suite de tests

`tests/test-app.sh` est un script shell POSIX : il tourne sous dash, bash et posh. Ses outils :

| Outil | Rôle |
|---|---|
| `titre` | ouvre un test : "Tnn: " suivi de ce qu'il vérifie |
| `lancer` | lance le script avec le fichier de réglages des tests : la sortie standard dans `sortie`, le journal dans `journal`, le code de retour dans `RC`, l'archive dans `ARCH` |
| `piloter` | le lance sur un pseudo-terminal, les réponses données en un seul argument, séparées par des barres verticales |
| `verifier`, `egal` | un contrôle : une commande qui doit réussir, ou une valeur attendue |
| `sauter` | un contrôle qui ne peut pas avoir lieu ici |
| `joindre` | joint au rapport un extrait d'un fichier |

On compte des contrôles, pas des tests. Un test est un `titre`, un lancement, puis ses contrôles, chacun étiqueté du numéro de son test ; [TESTS.fr.md](TESTS.fr.md) lui donne sa ligne.

Deux pièges ont été rencontrés en vrai :

- Une seule suite à la fois sur une machine : M2 compte les processus du moteur de toute la machine, et voit ceux d'une autre suite.
- Le pilote du pseudo-terminal répond après une seconde de silence : sur une machine lente, un Raspberry Pi, la réponse peut précéder la question. Une question finit sans saut de ligne : un contrôle en compte les occurrences, jamais les lignes.

### Conventions

- Les noms de fonctions, de variables et de constantes sont en français ; les commentaires, les docstrings, les messages et la documentation en anglais.
- Pas de tiret cadratin, pas de guillemets chevrons, pas d'émoji dans les scripts.
- Le README, `EXAMPLES.md` et chaque document de `docs/` ont une version française, `.fr.md`, sur le même plan, tenue à jour dans le même changement. Le CHANGELOG est en anglais seulement.
- Chaque changement de comportement s'accompagne d'un test et de sa documentation, dans les deux langues.
- Aucun code n'est supprimé pour "optimiser" : une suppression nécessaire est dite dans le commit.

### Contrôles avant un commit

Sur les scripts : `python3 -m py_compile`, `flake8`, `ruff check`, `mypy`, `bandit`, `codespell` et `vulture`. Sur la suite : `shellcheck`, `checkbashisms`, et `sh -n`, `dash -n`, `bash -n`, `posh -n`. Puis la suite elle-même, hors réseau sous `sh` et sous `posh`, et avec `--network`. La date et l'heure des derniers passages réussis, hors réseau et avec `--network`, vont dans [TESTS.fr.md](TESTS.fr.md#1-lancer-les-tests), section 1.

Certaines remarques sont connues et acceptées :

- `ruff`, en version 0.16 sans fichier de configuration : UP031, le formatage par `%` étant le style de la maison, trois DTZ005, `datetime.now()` sans fuseau horaire, pour une heure locale voulue, et un S110, le `try`/`except`/`pass` que relève aussi `bandit`
- `bandit` : onze remarques, sur le lancement de processus, par `subprocess` et `os.execv`, sur `urllib` et sur ce `try`/`except`/`pass`
- `flake8` : une ligne de 81 caractères, la signature d'`ecrire_synthese()`
- `vulture` : `redirect_request`, une méthode d'urllib redéfinie
- `codespell` : les identifiants français
- `mdl` : MD013, les documents écrivant une phrase par ligne

### Branches et versions

- Le travail se fait sur la branche `dev` ; `main` ne reçoit que les versions publiées.
- `dev` porte aussi `CLAUDE.md`, les notes de travail de l'assistant qui sert à développer le projet, que `main` ne publie pas : chaque fusion le retire par `git rm -f CLAUDE.md`. C'est pourquoi `main` n'est pas un ancêtre de `dev`, et pourquoi chaque fusion bute sur un conflit modification/suppression de ce fichier, réglé par la même commande.
- Les versions suivent la [gestion sémantique de version](https://semver.org/lang/fr/), le CHANGELOG [Tenez un Changelog](https://keepachangelog.com/fr/1.1.0/) : entre deux fusions, tout s'accumule sous Unreleased.

Une version se publie dans cet ordre :

1. Sur `dev`, un commit "Version X.Y.Z" : `VERSION`, le titre de la version dans le CHANGELOG et ses références de liens.
2. La suite avec `--network` relancée sur chaque machine d'essai, et le tableau des machines de [TESTS.fr.md](TESTS.fr.md#1-lancer-les-tests), section 1, mis à jour dans les deux langues.
3. Sur `main`, la fusion de `dev`, intitulée "IAnalyze X.Y.Z".
4. Une étiquette annotée et signée, `vX.Y.Z`, faite avec `git tag -s`.
5. Une release GitHub du même nom.
