# IAnalyze : documentation technique

Le [README](README.md) suffit pour installer IAnalyze et analyser une partie. [EXEMPLES.md](EXEMPLES.md) donne toutes les commandes, toutes les options et ce qu'elles affichent.

Ce document va plus loin. Il s'adresse à qui veut comprendre ce que fait le script, l'appeler depuis un autre programme, lire les fichiers qu'il produit, ou écrire son propre modèle de prompt. Les tests ont leur document, [TESTS.md](TESTS.md).

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

## 1. Ce que fait le script, étape par étape

Une collecte suit toujours le même ordre. Les contrôles viennent d'abord : tant qu'ils ne sont pas tous passés, rien n'est écrit dans le répertoire de sortie et aucune requête ne part vers l'explorateur.

1. **Options.** Elles sont lues et contrôlées (section 3). Une option refusée arrête le script avec le code 2.
2. **Environnement virtuel.** Le Python du système n'a pas python-chess : le script se relance lui-même avec le Python de son environnement virtuel. Le journal l'annonce par "Environnement virtuel : relance via ...". C'est le fonctionnement normal, à chaque lancement.
3. **Réglages et modèle de prompt.** Le fichier de réglages est lu (section 6), le modèle de prompt est lu et contrôlé (section 12).
4. **Partie.** Le PGN est lu depuis le fichier, ou téléchargé depuis Lichess. Il est décodé (section 11), puis contrôlé (section 4).
5. **Jeton et catalogue.** Sauf avec `--sans-explorateur`, le jeton est lu (section 7) et le catalogue des ouvertures chargé (section 8).
6. **Moteur.** Le binaire de Stockfish est vérifié, puis lancé une première fois, seulement pour lui demander les bornes de ses options (section 9).
7. **Questions.** Dans un terminal, le script pose ses questions (section 5).
8. **Dossier de travail.** Il est créé dans le répertoire de sortie. Le script y écrit `partie.pgn` et, si vous avez répondu aux questions, `contexte.md`.
9. **Explorateur.** Une requête par demi-coup, jusqu'à un critère d'arrêt (section 8).
10. **Stockfish.** Une évaluation par demi-coup (section 9). C'est la phase la plus longue.
11. **Synthèse.** `collecte.json` et `synthese.md` sont écrits (section 10).
12. **Archive.** Le dossier est compressé, l'archive vérifiée, le dossier supprimé. Avec `--prompt-seul`, il n'y a pas d'archive.
13. **Prompt.** Il est écrit à côté de l'archive.
14. **Sortie standard.** Le chemin de l'archive, ou celui du prompt avec `--prompt-seul`, y est écrit seul.

Trois commandes ne collectent rien et s'arrêtent une fois leur travail fait : `--installer-venv`, `--installer-catalogue` et `--purge-reglages`.

Après l'étape 8, un échec laisse le dossier de travail en place, tel quel, pour diagnostic.

## 2. Fichiers du dépôt

| Fichier | Rôle |
|---|---|
| `ianalyze.py` | la collecte, en un seul fichier. Il ne demande que python-chess et Stockfish |
| `verifier-analyse.py` | le contrôle du PGN rendu par un LLM (section 13) |
| `prompt-modele.txt`, `prompt-seul-modele.txt` | les deux modèles de prompt (section 12) |
| `test-app.sh` | la suite de tests, pour Linux et macOS, décrite dans [TESTS.md](TESTS.md) |
| `test.pgn` | une partie d'essai qui réunit les cas tordus d'un PGN, décrite dans [TESTS.md](TESTS.md) |
| `parties-exemples/` | les fichiers cités dans [EXEMPLES.md](EXEMPLES.md) : parties, PGN refusés, PGN annotés |
| `README.md`, `EXEMPLES.md`, `TECHNIQUE.md`, `TESTS.md`, `CHANGELOG.md` | la documentation et l'historique des versions |
| `LICENSE` | la licence, CC0 |

Le HTTP passe par urllib et l'archive par zipfile, tous deux de la bibliothèque standard de Python.

## 3. Ligne de commande

### Règles de cohérence

Une option sans effet, ou une valeur hors bornes, est refusée plutôt qu'ignorée en silence :

- `--cadences` et `--classements` exigent `--base lichess`.
- `--pause` ne descend pas sous 2, `--seuil-frequence` reste entre 0 et 100, `--coups-min`, `--coups-stockfish` et `--longueur-pv` valent 0 ou plus, `--profondeur` va de 1 à 60, les autres valeurs numériques valent au moins 1.
- `--pause` et `--seuil-frequence` refusent nan et inf.
- `--fils`, `--hachage` et `--multipv` sont contrôlés auprès du moteur, qui annonce ses bornes : une valeur qu'il n'admet pas est refusée avant toute requête à l'explorateur et avant la création du dossier de travail.
- `--purge-reglages` s'emploie seule, sans partie ni autre action.
- `--sans-prompt` s'exclut avec `--prompt` et avec `--prompt-seul`.
- `--pseudos` et `--prompt` refusent une valeur vide.

### Codes de retour

| Code | Signification |
|---|---|
| 0 | succès |
| 1 | erreur signalée par un message, dont une valeur que le moteur n'admet pas, ou erreur inattendue |
| 2 | option inconnue, ou valeur refusée avant toute lecture de la partie |
| 130 | interruption (Ctrl-C) |

Ceux de `verifier-analyse.py` sont donnés en section 13.

### Sortie standard et journal

Le chemin de l'archive est écrit seul sur la sortie standard, le journal horodaté va sur la sortie d'erreur :

```bash
ARCHIVE=$(./ianalyze.py ma-partie.pgn 2>/dev/null)
```

Avec `--prompt-seul`, c'est le chemin du prompt qui est écrit sur la sortie standard.

Le journal, les questions et les messages d'erreur vont tous sur la sortie d'erreur. Chaque ligne du journal porte l'heure :

```text
[16:41:40] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[16:41:40] Lecture du PGN local : ma-partie.pgn
[16:41:41] Dossier de travail : analyse-ma-partie-20261119-164141
[16:41:41] Stockfish : évaluation de 49 demi-coups, profondeur 18, multipv 3, threads 8. C'est la phase la plus longue.
```

Un message d'erreur, lui, n'est pas horodaté : c'est la dernière ligne, et le code de retour vaut 1 ou 2.

### Appeler le script depuis un autre programme

```bash
ARCHIVE=$(./ianalyze.py ma-partie.pgn --sans-questions 2> collecte.log)
```

Le code de retour dit si la collecte a abouti, `collecte.log` garde le journal et `$ARCHIVE` reçoit le chemin de l'archive.

Rediriger la sortie d'erreur suffit à faire taire les questions (section 5) : `--sans-questions` le dit seulement en clair.

Sous macOS, cette commande met le prompt court dans le presse-papiers, prêt à être collé dans la conversation. La sortie d'erreur n'étant pas redirigée, les questions restent posées :

```bash
pbcopy < "$(./ianalyze.py ma-partie.pgn --prompt-seul)"
```

## 4. La partie, sa source et ses contrôles

SOURCE désigne la partie de trois façons : un fichier PGN, l'adresse d'une partie de Lichess, ou son identifiant.

**Une URL** doit viser lichess.org et porter l'identifiant en tête de chemin.

L'identifiant est la suite de 8 caractères qui suit `lichess.org/` dans l'adresse de la partie. Les formes `/<id>/black`, `/embed/game/<id>`, `/embed/<id>` et `/game/export/<id>` sont acceptées.

Un autre hôte, ou une autre page du site (étude, analyse, exercices), est refusé sans rien envoyer à Lichess.

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

Une partie de Lichess est téléchargée depuis `https://lichess.org/game/export/<identifiant>`, qui ne demande pas de jeton.

Le contrôle de la notation passe avant la lecture par python-chess, qui, lui, ne refuserait rien : il saute sans rien dire les caractères qu'il ne connaît pas. Sont admis hors des commentaires : les balises en début de ligne, les numéros de coup, les coups en notation anglaise, le coup nul `--`, les NAG, les signes d'appréciation, les parenthèses de variante et le résultat.

Un coup illégal arrête lui aussi le script. python-chess, à cet endroit, cesserait de lire sans lever d'erreur, et la partie serait analysée tronquée.

## 5. Questions de démarrage et terminal

### Ordre des questions

1. Au premier lancement, les réglages qui manquent : pseudo, cadence habituelle, niveau (section 6).
2. Votre camp, s'il ne se déduit pas de vos pseudos : "Avez-vous joué les Blancs ou les Noirs ? [b/n]". Les balises White et Black vides sont alors complétées : la vôtre par votre premier pseudo, ou par votre nom, demandé faute de pseudo, celle de l'adversaire par son nom, demandé lui aussi.
3. La cadence de la partie, si la balise TimeControl manque, est vide, ou vaut "?" ou "-".
4. Les quatre questions de contexte : périmètre, ce que vous cherchez à comprendre, contexte particulier, autres commentaires à inclure dans le PGN final.

Entrée retient la valeur proposée. Ctrl-D met fin aux questions : celles qui restent prennent leur valeur par défaut.

Les questions de réglages font exception : interrompues par Ctrl-D, elles n'enregistrent rien et reviendront au prochain lancement.

### Ce que deviennent les réponses

Les réponses vont dans `contexte.md`, repris en tête de la synthèse sous le titre "Consignes d'analyse".

Une réponse laissée à sa valeur proposée y porte la mention "(défaut)" : l'analyste distingue ainsi votre choix d'une valeur par défaut.

```text
Réponses du joueur aux questions de démarrage, recueillies par le script avant la collecte. "(défaut)" signale une réponse validée par Entrée.

- Camp du joueur : Blancs, déduit des en-têtes
- Cadence : balise TimeControl `600+5`, soit rapide, 10 minutes + 5 secondes par coup
- a. Périmètre : la partie complète (défaut)
- b. Ce que le joueur cherche à comprendre : la sortie de la dame
- c. Contexte particulier : rien (défaut)
- d. Autres commentaires à inclure dans le PGN final : rien (défaut)
```

Quand une balise White ou Black a été complétée, `partie.pgn` porte la partie avec ses nouvelles balises, et le PGN fourni est gardé sous `partie-origine.pgn`.

### Quand les questions ne sont pas posées

Les questions s'affichent dans le terminal et attendent une réponse au clavier.

Le script ne les pose donc que s'il est lancé à la main, dans un terminal. Il ne demande rien dans ces quatre cas :

- vous passez `--sans-questions`
- un autre programme le lance sans terminal : cron, un service
- son entrée ne vient pas du clavier : `./ianalyze.py ma-partie.pgn < /dev/null`
- son journal ne va pas à l'écran : `./ianalyze.py ma-partie.pgn 2> journal.log`

Le dernier cas surprend : les questions s'écrivent au même endroit que le journal, la sortie d'erreur. Si vous la redirigez, vous ne les verriez pas.

L'exemple de la section 3, avec `2>/dev/null`, ne pose donc aucune question. Sans cette redirection, `ARCHIVE=$(./ianalyze.py ma-partie.pgn)` les pose normalement.

Dans la suite, "sans terminal" désigne ces quatre cas.

### Sans questions, ce qui change

- Le journal le dit : "Questions de démarrage sautées", suivi de la raison, l'option ou le terminal non interactif.
- Les réglages qui manquent ne sont ni demandés ni écrits.
- `contexte.md` n'est pas écrit, et la synthèse n'a pas de section "Consignes d'analyse".
- Le camp se déduit de vos pseudos, sans question. Il faut pour cela qu'une seule des deux balises, White ou Black, porte l'un d'eux. Sinon le camp reste "inconnu".
- Le prompt dit au LLM que vos réponses n'ont pas été recueillies : c'est lui qui pose les quatre questions de contexte, en un seul message, avant d'analyser.

## 6. Réglages

Le fichier de réglages, `~/.config/IAnalyze/reglages.ini` ou celui de `--reglages`, est au format INI. Sa section `[joueur]` porte trois clefs que le script demande, `pseudos`, `cadence` et `niveau`, et une clef facultative, `annotateur`.

### Clefs et formes admises

**Les pseudos** sont vos noms de joueur, séparés par des virgules. Ils sont cherchés, sans tenir compte de la casse, dans les balises White et Black pour déduire votre camp. Le premier sert à compléter une balise vide.

**Le niveau** est un nombre de points Elo approximatifs, de 100 à 3500, ou "inconnu".

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

Le script tolère quelques variantes d'écriture : "j" ou "jour" pour "jours", "h" ou "heure" pour "heures", "reserve" sans accent. Une cadence vide, "?" ou "non précisée" vaut "inconnue".

Pour le temps réel, la catégorie est calculée comme le fait Lichess, sur une durée estimée : le temps initial plus quarante fois l'incrément.

| Durée estimée | Catégorie |
|---|---|
| moins de 30 secondes | ultrabullet |
| de 30 secondes à moins de 3 minutes | bullet |
| de 3 à moins de 8 minutes | blitz |
| de 8 à moins de 25 minutes | rapide |
| 25 minutes et plus | classique |

`15+10` donne 900 + 400 = 1300 secondes : rapide.

### Lecture

- Un fichier absent vaut des réglages vides.
- Une clef absente est demandée, une seule fois, dans un terminal.
- Une clef présente, même vide, n'est jamais redemandée.
- Une cadence ou un niveau illisible est redemandé, et le journal le dit.
- Un fichier mal formé arrête le script, avec le remède : le corriger ou le supprimer.
- Le signe "%" est un caractère comme un autre, il ne déclenche aucune substitution.
- Le fichier passe par le même décodage que le PGN (section 11) : son encodage n'a pas d'importance.
- `--pseudos` remplace les pseudos du fichier le temps d'un lancement. Au tout premier lancement, il est proposé comme réponse à la question du pseudo.

### Écriture

Le script n'écrit le fichier que lorsqu'il vient d'obtenir une réponse. Il le réécrit alors en entier :

1. un en-tête de commentaires
2. les clefs qu'il connaît, chacune sous un commentaire qui rappelle ses formes admises
3. les autres clefs que vous avez ajoutées à `[joueur]`
4. vos autres sections

Vos propres lignes de commentaire ne survivent donc pas à une réécriture. Le répertoire du fichier est créé au besoin.

Si l'écriture échoue, la collecte continue : le journal le signale, et la question sera reposée au prochain lancement.

Sans terminal, rien n'est demandé ni écrit.

### Plusieurs profils

`--reglages FICHIER` désigne un autre fichier. S'il n'existe pas, il est créé par les mêmes questions : c'est la façon de tenir un profil par joueur.

`--purge-reglages` supprime le fichier de réglages, celui de `--reglages` s'il est donné, puis quitte. Le répertoire reste en place. Un fichier absent n'est pas une erreur, un répertoire est refusé.

## 7. Jeton

Le jeton n'est transmis que dans l'en-tête Authorization, jamais dans l'URL. Il n'apparaît ni dans le journal, ni dans l'archive, où `collecte.json` note seulement sa présence.

Il n'est envoyé qu'à l'adresse de l'explorateur : si celui-ci répondait par une redirection, elle ne serait pas suivie, et l'interrogation s'arrêterait là.

Un fichier de jeton lisible par d'autres déclenche un avertissement. Le fichier ne porte que le jeton : une affectation, `LICHESS_TOKEN=...`, ou des guillemets sont refusés.

Le fichier peut porter une marque d'ordre des octets ou être en UTF-16, comme en produisent certains éditeurs Windows : le journal le signale et le jeton est lu normalement.

Le fichier n'est ouvert que si l'explorateur sert : avec `--sans-explorateur`, il n'est pas lu. Le téléchargement d'une partie de Lichess, lui, se fait sans jeton.

Contrôles à la lecture :

- un fichier absent ou vide arrête le script
- une espace, un signe égal ou un guillemet dans le jeton arrêtent le script : le fichier ne doit porter que le jeton
- un caractère hors de l'ASCII imprimable arrête le script, sans que le message reproduise le jeton

La réponse de l'explorateur est expurgée du jeton avant d'être gardée dans l'archive, au cas où un serveur renverrait l'en-tête qu'il a reçu. Il en va de même de la trace d'une erreur inattendue, avec `--debug`.

## 8. Explorateur

### Requêtes

Le script envoie une requête par demi-coup, à `https://explorer.lichess.org/lichess` ou à `https://explorer.lichess.org/masters` selon `--base`. La position y est désignée par la suite des coups joués depuis le début de la partie, et non par une FEN.

| Paramètre | Valeur | Rôle |
|---|---|---|
| `play` | les coups déjà joués, en notation UCI, séparés par des virgules | la position interrogée |
| `moves` | `256` | tous les coups connus de la position, et non les premiers seulement |
| `topGames` | `0` | aucune partie de référence, seules les statistiques servent |

La base `lichess` reçoit en plus les filtres :

| Paramètre | Valeur |
|---|---|
| `variant` | `standard` |
| `speeds` | la liste de `--cadences` |
| `ratings` | la liste de `--classements` |
| `since` | `2017-01` |
| `recentGames` | `0` |

Chaque requête porte l'en-tête d'agent `IAnalyze/4.0.0 (+https://github.com/deuza/IAnalyze)` et le jeton, dans l'en-tête Authorization.

Chaque réponse est gardée telle quelle dans `explorateur/NNN-<uci>.json` : NNN est le numéro du demi-coup, `<uci>` le coup joué. C'est la réponse sur la position d'avant ce coup.

### Pause, HTTP 429 et erreurs

Le script attend `--pause` secondes entre deux requêtes, 2 au minimum, et rien avant la première.

Sur un HTTP 429, le script attend 60 secondes et retente une seule fois. Au second refus, il cesse d'interroger : mieux vaut s'arrêter que se faire bannir.

Toute autre réponse inexploitable arrête l'interrogation à ce demi-coup : une erreur HTTP, un délai dépassé (`--delai`), une réponse qui n'est pas du JSON, une redirection. La collecte, elle, continue : la table de l'explorateur s'arrête là, et Stockfish évalue toute la partie.

Sans jeton, la base `lichess` répond 401. Le script demande un jeton pour les deux bases, et s'arrête avant toute requête si le fichier manque.

### Critères d'arrêt

Pour chaque demi-coup, la position AVANT le coup est interrogée, ce qui donne le rang et la fréquence du coup réellement joué.

L'interrogation s'arrête, dans cet ordre de test :

1. sur une erreur HTTP ou une position absente de la base.
2. sur un échantillon inférieur à `--seuil-parties`.
3. sur une sortie de théorie, hors de la fenêtre `--coups-min`.
4. au plafond `--max-demicoups`, ou à la fin de la partie.

Un coup nul, "--" dans le PGN, arrête aussi l'interrogation, avant toute requête pour ce demi-coup et quel que soit le mode : ce n'est pas un coup des échecs, la base ne peut pas suivre la partie au delà.

Il n'est pas compté comme une sortie de théorie, et la section 4 de la synthèse le signale.

### Sortie de théorie

Un coup est rare quand il est joué dans moins de `--seuil-frequence` pour cent des parties de la position.

Un coup rare est une sortie de théorie s'il mène à une position absente du catalogue des ouvertures. S'il reste dans une ligne que le catalogue connaît, ce n'en est pas une.

La première sortie est toujours notée. Elle n'arrête l'interrogation qu'après les `--coups-min` premiers coups, pour que la table couvre le début de la partie même après une sortie précoce.

### Catalogue des ouvertures

Le catalogue vient des cinq fichiers `a.tsv` à `e.tsv` du dépôt [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings).

`--installer-catalogue` les télécharge et rejoue chaque ligne avec python-chess. Un coup illisible ou illégal, ou une position nommée deux fois, arrête l'installation sans toucher au catalogue en place.

L'index est ensuite écrit dans `catalogue.tsv`, dans le répertoire de `--catalogue`. Il est écrit sous un nom provisoire, puis renommé : une collecte lancée pendant une mise à jour lit l'ancien index ou le nouveau, jamais un mélange.

```text
#format=1  date=2026-11-20T21:03:14+01:00  lignes=3865  nommees=3865  connues=7982  source=...
epd  eco  nom
```

La première ligne décrit l'index, la deuxième nomme les colonnes, et chaque ligne suivante porte une position : son EPD, son code ECO et son nom, séparés par des tabulations. Les positions sont triées, si bien que deux installations du même catalogue donnent deux fichiers identiques.

Une position est repérée par son EPD, la case de prise en passant n'y figurant que si la prise est jouable : c'est aussi la règle du serveur de l'explorateur.

Le catalogue dit "connu", jamais "bon" : "Barnes Opening: Fool's Mate" y figure.

Il compte aussi les positions intermédiaires des lignes nommées, que l'explorateur ne nomme pas lui-même.

Ces positions intermédiaires ont un nom vide dans l'index. Le 20 novembre 2026, le catalogue comptait 3865 lignes nommées, soit 7982 positions connues en les comptant.

Au chargement, le format et le nombre de positions annoncés sont vérifiés : un index absent, abîmé ou tronqué arrête le script, qui donne la commande à relancer.

## 9. Moteur

### Dialogue avec Stockfish

Le script pilote Stockfish par le protocole UCI, à travers python-chess. Il le lance deux fois :

1. avant la collecte, pour lire les bornes que le moteur annonce pour ses options, puis l'arrêter. Une valeur hors bornes est ainsi refusée tout de suite, et non après plusieurs minutes d'explorateur
2. pour l'analyse : il règle `Threads` et `Hash`, demande les chances de gain avec `UCI_ShowWDL` si le moteur connaît cette option, puis fait analyser chaque position jusqu'à la profondeur demandée

### Threads, Hash et MultiPV

| Option du script | Option UCI | Défaut du script | Défaut de Stockfish |
|---|---|---|---|
| `--fils` | `Threads` | le nombre de processeurs | 1 |
| `--hachage` | `Hash` | 256 | 16 |
| `--multipv` | `MultiPV` | 3 | 1 |

**Threads, les fils.** C'est le nombre de fils d'exécution que le moteur emploie pour explorer une position. Plus il en a, plus vite il atteint la profondeur demandée. La documentation de Stockfish conseille de lui en donner autant que la machine a de cœurs : c'est le défaut du script.

Une conséquence à connaître : avec plusieurs fils, deux analyses de la même position ne rendent pas exactement les mêmes chiffres. Mesuré avec Stockfish 16 à la profondeur 16 : trois analyses identiques avec un fil, trois analyses différentes de quelques centipions avec quatre fils, l'ordre des meilleurs coups pouvant changer quand ils se valent. Deux collectes de la même partie diffèrent donc un peu. Pour des chiffres reproductibles, lancez le script avec `--fils 1`.

**Hash, la table de hachage.** En explorant, un moteur retombe sans cesse sur les mêmes positions par des ordres de coups différents. La table de hachage, ou table de transposition, garde le résultat des recherches déjà faites pour ne pas les refaire. `--hachage` en fixe la taille, en mégaoctets. Trop petite, elle se remplit et le moteur recalcule. Trop grande pour la mémoire libre, le système refuse de l'allouer et le moteur s'arrête : le script le dit alors, et nomme `--hachage`.

**MultiPV, les meilleurs coups.** Par défaut, un moteur ne cherche que la meilleure suite, sa "variante principale". Avec MultiPV, il en rend plusieurs, classées. Le script en demande 3, pour que la synthèse montre ce que le moteur préférait au coup joué. La recherche en est ralentie : la documentation de Stockfish conseille de laisser 1 pour la meilleure performance.

Si le coup joué ne figure pas parmi ces meilleurs coups, le script lance une seconde recherche, restreinte à ce seul coup, pour lui donner une évaluation et mesurer l'écart.

**La profondeur.** `--profondeur` arrête la recherche quand le moteur a atteint cette profondeur. Le temps de calcul croît très vite avec elle. Le script la borne à 60.

Les bornes sont celles que le moteur annonce. Stockfish 17.1 et Stockfish 19 admettent de 1 à 1024 pour Threads, de 1 à 33554432 pour Hash et de 1 à 256 pour MultiPV.

Sources : [options UCI de Stockfish](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html) pour Threads, Hash, MultiPV et UCI_ShowWDL, et [Transposition Table](https://www.chessprogramming.org/Transposition_Table), sur le wiki Chess Programming, pour la table de hachage. Les deux pages sont en anglais.

### Ce que le script tire des évaluations

- **L'évaluation** est donnée du point de vue des Blancs, en pions : `+0.35`. Un mat s'écrit `#+2`, les Blancs matent en deux coups, ou `#-1`, les Noirs matent en un coup.
- **Un mat se compte après le coup**, comme toute évaluation du tableau. Le moteur, lui, compte avant le coup, celui-ci compris : le script retire donc un coup au camp qui mate quand c'est lui qui vient de jouer. `#+0` ou `#-0` : le coup de la ligne donne mat.
- **L'écart** est ce que le coup joué perd par rapport au premier choix du moteur, en centipions, du point de vue du joueur au trait.
- **La nature** suit l'écart : imprécision à partir de 50, erreur à partir de 100, gaffe à partir de 300.
- **Un écart négatif** n'est pas une faute. Le coup joué, évalué à part quand il n'est pas dans les premiers choix, sort alors un peu au-dessus du premier : les deux se valent.
- **Les mats** ne se chiffrent pas en centipions. Entre deux mats de même sens, mater en deux coups au lieu d'un par exemple, l'écart vaut 0. Un coup qui manque un mat ou en concède un porte l'écart "mat" et la nature "gaffe".
- **G/N/P** donne les chances de gain, de nulle et de perte des Blancs. Ce sont celles du modèle de Stockfish, établi sur des parties du moteur contre lui-même : une tendance, et non une probabilité entre joueurs humains.
- **Un coup nul**, `--`, n'est pas évalué : ce n'est pas un coup des échecs, le moteur ne peut pas le juger. Sa ligne garde les meilleurs coups de la position.

### `stockfish/evaluations.json`

Le fichier est une liste, un objet par demi-coup évalué :

| Clef | Contenu |
|---|---|
| `demicoup`, `numero`, `trait` | le rang du demi-coup, le numéro du coup, "Blancs" ou "Noirs" |
| `fen` | la position avant le coup |
| `joue` | le coup joué et son évaluation |
| `meilleurs` | les meilleurs coups du moteur, dans l'ordre, autant que `--multipv` |
| `ecart_cp` | l'écart en centipions. À partir de 10000, il ne mesure plus rien : l'un des deux coups est un mat |
| `nature` | "imprécision", "erreur", "gaffe", ou rien |

Pour un coup nul, `joue` porte `non_evalue`, et `ecart_cp` comme `nature` sont vides.

`joue` et chaque élément de `meilleurs` portent les mêmes clefs :

| Clef | Contenu |
|---|---|
| `san`, `uci` | le coup, en notation algébrique et en notation UCI |
| `score` | l'évaluation du point de vue des Blancs, comme dans la synthèse |
| `valeur_trait` | la même en centipions, du point de vue du joueur au trait. Un mat en n coups y vaut 100000 - n |
| `profondeur` | la profondeur atteinte |
| `pv_san`, `pv_uci` | la variante principale entière, que la synthèse coupe à `--longueur-pv` demi-coups |
| `wdl` | `gain`, `nulle` et `perte` des Blancs, en pour mille |

## 10. Fichiers produits

### Dossier de travail et archive

Le dossier de travail s'appelle `analyse-<étiquette>-<AAAAMMJJ-HHMMSS>`. L'étiquette est le nom du PGN sans son extension, assaini (section 11), ou l'identifiant Lichess. Un dossier ou une archive du même nom fait ajouter un suffixe, -2, -3 et ainsi de suite.

Une archive présente sous son nom définitif est toujours complète et vérifiée : elle est écrite sous le nom provisoire `.<dossier>.partiel.zip`, puis renommée.

Il en va de même de chaque fichier du dossier de travail, écrit sous `.<nom>.partiel`. Après une interruption (Ctrl-C) ou un échec, ces fichiers provisoires sont retirés et le dossier de travail reste, sans archive.

### `partie.pgn` et `partie-origine.pgn`

`partie.pgn` est le PGN fourni, converti en UTF-8 s'il ne l'était pas.

Si vos réponses ont complété une balise White ou Black, `partie.pgn` porte la partie réécrite par python-chess avec ses nouvelles balises, et `partie-origine.pgn` garde le texte fourni.

### `collecte.json`

Le fichier garde les paramètres exacts de la collecte : toutes les options de la ligne de commande, sous leur nom, les tirets devenant des soulignés, plus ces clefs :

| Clef | Contenu |
|---|---|
| `jeton_present` | vrai si un jeton a été lu. Le jeton lui-même n'y figure jamais |
| `catalogue_utilise` | la description du catalogue : date, nombre de lignes et de positions |
| `camp` | votre camp, son origine, déduit ou déclaré, et les balises complétées |
| `contexte_recueilli` | vrai si vous avez répondu aux questions |
| `pgn_encodage`, `pgn_remarques` | comment le PGN a été décodé |
| `prompt_ecrit` | le nom du prompt, ou rien avec `--sans-prompt` |

`pseudos` y porte les pseudos réellement employés, ceux de `--pseudos` ou ceux des réglages.

### `synthese.md`

Sections de `synthese.md` :

| Section | Contenu |
|---|---|
| Consignes d'analyse | `contexte.md`, vos réponses aux questions de démarrage. Absente quand elles ne sont pas posées |
| 1. En-têtes et coups | en-têtes, ligne principale, repères de phase (roques, dames, entrée en finale) |
| 2. Explorateur | filtres, seuils, table, première sortie |
| 3. Évaluations Stockfish | nature et G/N/P de chaque coup |
| 3 bis | variantes principales du moteur |
| 3 ter | erreurs et gaffes par camp, avec la FEN |
| 4. Positions non exploitables | là où la base ne dit plus rien, ou le demi-coup d'un coup nul |
| 5. Données brutes de l'archive | le contenu du zip, et l'encodage du PGN s'il a été converti. Le dossier `explorateur/` n'y figure que s'il existe |

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

## 11. Encodages et caractères

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

Les lettres accentuées sont conservées.

Console : un caractère que le terminal ne sait pas afficher devient "?" au lieu d'arrêter le script, sous LANG=C comme avec PYTHONIOENCODING=ascii.

Le chemin de l'archive est écrit en octets sur la sortie standard : ARCHIVE=$(...) reste exact dans tous les cas.

Questions de démarrage : une réponse saisie dans un autre encodage que celui du terminal est redécodée, cp1252 puis latin-1.

## 12. Modèle de prompt

Le prompt de chaque partie est tiré d'un modèle : `prompt-modele.txt`, ou `prompt-seul-modele.txt` avec `--prompt-seul`. Vous pouvez les modifier, ou désigner le vôtre avec `--prompt`.

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
| `COUPS_FAIBLES_JOUEUR` | nombre de vos coups que `TABLEAU_MOTEUR` marque imprécision, erreur ou gaffe, "inconnu" si votre camp ne l'est pas |

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
| `PEU_DE_COUPS_FAIBLES` | votre camp est connu et `COUPS_FAIBLES_JOUEUR` est inférieur à trois |
| `AUCUN_COUP_FAIBLE` | votre camp est connu et `COUPS_FAIBLES_JOUEUR` vaut zéro |

Les deux modèles, `prompt-modele.txt` et `prompt-seul-modele.txt`, partagent ces repères. `PARTIE_PGN`, `TABLEAU_MOTEUR`, `ALERTE_RESULTAT`, `CONSIGNES_JOUEUR`, `OUVERTURE`, `COUPS_FAIBLES_JOUEUR` et les conditions `RESULTAT_CONTREDIT`, `CONSIGNES_DONNEES`, `OUVERTURE_CONNUE`, `COUP_NUL`, `PEU_DE_COUPS_FAIBLES`, `AUCUN_COUP_FAIBLE` servent au prompt court.

Le prompt court finit par un bilan : les trois erreurs les plus coûteuses du joueur et le thème à travailler. Quand le tableau marque moins de trois coups faibles de votre côté, la phrase change : elle donne leur nombre et demande de s'en tenir à ceux-là.

```text
Après le bloc de code, donnez en quelques lignes les erreurs les plus
coûteuses du joueur et le thème qu'il doit travailler en priorité.
Coups faibles du joueur dans le tableau : 2.
Tenez-vous-en à ceux-là, sans en ajouter.
```

Sans aucun coup faible de votre côté, le prompt demande de ne vous prêter aucune erreur. Quand votre camp n'est pas connu, il demande de commenter les deux camps de la même façon et de donner le bilan pour chacun.

La raison vient des essais du 21 novembre 2026 (README, section 7) : le joueur n'avait commis que deux erreurs, et trois réponses sur cinq en ont présenté une troisième pour arriver au compte demandé.

Un repère inconnu ou mal écrit, comme `{{ NIVEAU }}`, un "si" jamais fermé, une directive mal formée ou un modèle sans une ligne de texte arrêtent le script avant la collecte :

```text
Modèle de prompt prompt-modele.txt, ligne 12 : condition inconnue MOTEUR, conditions admises : STOCKFISH, EXPLORATEUR, ...
```

Le contrôle du modèle a lieu avant la collecte, pour ne pas la faire pour rien.

Un fichier désigné par `--prompt` doit exister. Le modèle par défaut, lui, peut manquer quand le script a été copié seul : la collecte se fait alors sans prompt, et le journal le signale. Avec `--prompt-seul`, dont le prompt est le but, le script s'arrête.

Avec `--prompt-seul`, le modèle doit placer `{{PARTIE_PGN}}` dans une ligne de texte, et non dans une note : sans la partie, le prompt n'aurait rien à faire analyser. Si le repère est placé sous une condition qui ne s'applique pas à la partie, le prompt est écrit, mais le journal prévient qu'il ne peut pas être collé seul.

## 13. Le vérificateur en détail

Le README dit comment lancer le script et ce qu'il contrôle. Cette section donne ses règles exactes.

### Ce qu'il lit

Trois fichiers de l'archive : `partie.pgn`, `synthese.md` et `stockfish/evaluations.json`. Il les prend dans le zip, ou dans un dossier : le dossier de travail lui-même, ou celui qui le contient.

Les trois fichiers viennent toujours de la même collecte. Dans un dossier parent, seule une collecte complète est retenue, et le bilan la nomme : une collecte interrompue rangée à côté est ignorée. Si le dossier en contient plusieurs complètes, le script s'arrête et les nomme, plutôt que d'en choisir une.

Si l'un d'eux manque, ou si l'archive ne se lit pas, aucun contrôle n'a lieu et le code de retour vaut 2.

Comme `ianalyze.py`, il se relance dans l'environnement virtuel quand python-chess manque, mais seulement à son emplacement par défaut : il n'a pas d'option `--venv`.

### Repères du bilan

| Repère | Compte comme | Exemple |
|---|---|---|
| `ECHEC` | un échec, le code de retour vaut 1 | une erreur de Stockfish laissée sans commentaire |
| `ATTENTION` | un point à regarder, sans échec | une variante de plus de 5 demi-coups |
| `INFO` | une mesure | le nombre de coups commentés |
| `OK` | un contrôle passé | |

Code de retour : 0 sans `ECHEC`, 1 avec au moins un `ECHEC`, 2 si aucun contrôle n'a pu avoir lieu.

### Règles chiffrées

- **Lignes** : 79 caractères au plus.
- **Résumé** : un commentaire avant le premier coup. Son absence est un échec.
- **Signes interdits dans un commentaire** : accolade, signe pour cent, tiret cadratin. Un point-virgule vaut `ATTENTION`.
- **Balises** : les sept obligatoires en tête et dans l'ordre, leurs valeurs reprises de la partie d'origine. Les autres par ordre alphabétique, Annotator renseignée et PlyCount exact, sinon `ATTENTION`.
- **Coups commentés** : chaque erreur et chaque gaffe de Stockfish doit l'être. Le nombre total de coups commentés est donné pour information, le prompt en visant 15 à 25.
- **Périmètre** : le prompt limite les commentaires au périmètre convenu. Une erreur jouée au-delà n'est pas attendue. Le périmètre est le premier nombre de votre réponse à la question de démarrage, lue dans les consignes de `synthese.md` : "les 20 premiers coups" vaut 20 coups. Une réponse sans nombre, ou laissée par défaut, vaut la partie complète. `--perimetre N` le donne à la main, quand il a été convenu dans la conversation.
- **NAG de position** : `$14`, `$16`, `$18` et `$20` donnent les Blancs mieux, `$15`, `$17`, `$19` et `$21` les Noirs. Un tel NAG est contraire au moteur quand celui-ci donne l'autre camp mieux d'au moins un demi-pion, ou un mat.
- **NAG de qualité** : `$6` pour une imprécision, `$2` pour une erreur, `$4` pour une gaffe. Un autre avis que celui du moteur est donné pour information.
- **Variantes** : 5 demi-coups au plus, sinon `ATTENTION`. Une variante est dite appuyée sur le moteur quand ses deux premiers coups sont ceux d'une ligne que le moteur donne pour ce demi-coup.
- **Positions citées dans la conversation** : une FEN doit être valide et venir d'une position de la partie, reconnue à ses quatre premiers champs. Deux FEN sont demandées, sinon `ATTENTION`.

### Évaluations citées

Une évaluation se reconnaît à son signe : `+0.35`, `-1,20`, `+ 0.35`, le signe moins typographique, ou `#-3` pour un mat. Un nombre sans signe n'en est pas une, sauf pour un mat : `#2` est lu comme `#+2`, la forme du dossier.

Elle doit exister dans `evaluations.json`, pour le coup joué ou pour l'un des meilleurs coups, telle quelle ou arrondie à une décimale : `+0.35` peut être cité `+0.4` ou `+0.3`.

### Avec `--prompt-seul`

Le prompt court demande moins que le prompt complet. Les contrôles qu'il ne fonde pas sont sautés : longueur des lignes, résumé, NAG, signe pour cent, tiret cadratin, notation suffixe, balises Annotator et PlyCount, longueur des variantes. Avec `--synthese`, le tiret cadratin de la conversation et le nombre de FEN ne sont pas contrôlés non plus : une FEN citée doit seulement être valide et venir de la partie.

Les balises sont contrôlées autrement. Le prompt complet veut les sept balises obligatoires du standard PGN, dans leur ordre. Le prompt court demande seulement de recopier celles de la partie : parmi les sept, seules celles que porte la partie d'origine sont attendues, dans l'ordre où elle les écrit.
