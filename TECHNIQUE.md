# IAnalyze : documentation technique

Ce document complète le [README](README.md), qui suffit à l'usage courant.

Il s'adresse à qui veut comprendre ce que fait le script, écrire son propre modèle de prompt, lire les fichiers produits depuis un autre programme, ou jouer les tests.

| Section | Contenu |
|---|---|
| 1 | les fichiers du dépôt qui servent au développement |
| 2 | les règles de cohérence des options |
| 3 | les critères d'arrêt de l'explorateur |
| 4 | l'écriture de l'archive, le détail de la synthèse, les codes de retour |
| 5 | les encodages et les caractères |
| 6 | le modèle de prompt : repères, valeurs, conditions |
| 7 | les tests |

## 1. Fichiers du dépôt

| Fichier | Rôle |
|---|---|
| `test.pgn` | une partie d'essai qui réunit les cas tordus d'un PGN |
| `test-app.sh` | la suite de tests, pour Linux et macOS (section 7) |
| `prompt-modele.txt`, `prompt-seul-modele.txt` | les deux modèles de prompt (section 6) |

Les autres fichiers sont présentés dans le README.

## 2. Règles de cohérence

Une option sans effet, ou une valeur hors bornes, est refusée plutôt qu'ignorée en silence :

- `--cadences` et `--classements` exigent `--base lichess`.
- `--pause` ne descend pas sous 2, `--seuil-frequence` reste entre 0 et 100, `--coups-min`, `--coups-stockfish` et `--longueur-pv` valent 0 ou plus, `--profondeur` va de 1 à 60, les autres valeurs numériques valent au moins 1.
- `--pause` et `--seuil-frequence` refusent nan et inf.
- `--fils`, `--hachage` et `--multipv` sont contrôlés auprès du moteur, qui annonce ses bornes : une valeur qu'il n'admet pas est refusée avant toute requête à l'explorateur et avant la création du dossier de travail.

## 3. Explorateur : critères d'arrêt

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

## 4. Archive, synthèse et codes de retour

Une archive présente sous son nom définitif est toujours complète et vérifiée : elle est écrite sous le nom provisoire `.<dossier>.partiel.zip`, puis renommée.

Il en va de même de chaque fichier du dossier de travail, écrit sous `.<nom>.partiel`. Après une interruption (Ctrl-C) ou un échec, ces fichiers provisoires sont retirés et le dossier de travail reste, sans archive.

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
| 1 | erreur signalée par un message, dont une valeur que le moteur n'admet pas, ou erreur inattendue |
| 2 | option inconnue, ou valeur refusée avant toute lecture de la partie |
| 130 | interruption (Ctrl-C) |

## 5. Encodages et caractères

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

## 6. Modèle de prompt

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

Un repère inconnu ou mal écrit, comme `{{ NIVEAU }}`, un "si" jamais fermé, une directive mal formée ou un modèle sans une ligne de texte arrêtent le script avant la collecte :

```text
Modèle de prompt prompt-modele.txt, ligne 12 : condition inconnue MOTEUR, conditions admises : STOCKFISH, EXPLORATEUR, ...
```

## 7. Tests

Tous les tests sont joués par un seul script, `test-app.sh`, sous Debian comme sous macOS.

Cette section dit comment le lancer et ce qu'il vérifie. Le détail de chaque test, commande par commande, est dans le script, qui fait foi.

### Lancer les tests

Depuis le dépôt, après l'installation décrite dans le README :

```bash
./test-app.sh
```

```bash
./test-app.sh --reseau
```

```bash
./test-app.sh --reseau <identifiant ou adresse d'une partie de Lichess>
```

| Commande | Ce qu'elle joue | Durée |
|---|---|---|
| `./test-app.sh` | les tests hors réseau, sans jeton | environ 3 minutes sur un Mac récent, 6 sur un Raspberry Pi |
| `./test-app.sh --reseau` | les mêmes, puis ceux qui demandent le réseau et votre jeton Lichess, sauf T24 | environ 3 minutes de plus |
| `./test-app.sh --reseau PARTIE` | de même, avec T24 : le téléchargement de la partie que vous désignez | quelques secondes de plus |

**La partie de T24 est à vous de la choisir.** Le dépôt ne désigne aucune partie réelle : T24 télécharge celle que vous donnez après `--reseau`, par son identifiant ou par son adresse. N'importe quelle partie de Lichess convient, la vôtre ou une autre. Sans elle, T24 est compté "sauté", et le script rappelle au départ la commande à lancer. L'identifiant donné n'est pas écrit dans le rapport.

Le script se termine par un bilan :

```text
Réussis : 556, échecs : 0, sautés : 0
Rapport : /chemin/du/depot/rapport-tests-Linux-20261120-002933.txt
```

Le rapport reprend l'environnement (système, Python, python-chess, Stockfish), le résultat de chaque contrôle et les extraits utiles au diagnostic. Vous pouvez le transmettre tel quel.

Le nombre de contrôles dépend de la version et du mode choisi. Sous macOS, un test est toujours sauté : il crée un fichier au nom non UTF-8, ce que son système de fichiers refuse.

### Ce que les tests ne touchent pas

- **Vos réglages et votre catalogue** : les tests désignent les leurs, dans un répertoire temporaire supprimé à la fin.
- **Le dépôt** : rien n'y est écrit, sauf le rapport.
- **Votre jeton** : il n'est ni affiché, ni copié, ni passé dans une ligne de commande. Le script vérifie au contraire qu'il n'apparaît ni dans les archives qu'il contrôle ni dans le rapport.

Avec `--reseau`, comptez environ 70 requêtes à l'explorateur de Lichess, espacées de 2 secondes, 10 fichiers du catalogue et, si vous donnez une partie, 2 exports de cette partie.

### Ce qu'il faut pour les jouer

- l'environnement virtuel, installé par `--installer-venv`
- Stockfish, obligatoire : chaque collecte l'emploie. Sans lui, le script s'arrête au départ
- avec `--reseau` seulement, votre jeton dans `~/.lichess_token`

Les tests qui ne portent pas sur le moteur le règlent au plus court, `--profondeur 1`.

### Variables facultatives

| Variable | Rôle | Défaut |
|---|---|---|
| `VENV` | environnement virtuel de python-chess | `~/.local/share/IAnalyze/venv` |
| `STOCKFISH` | moteur employé par les tests | celui du PATH, sinon `/opt/homebrew/bin`, `/usr/local/bin` ou `/usr/games` |
| `JETON` | fichier du jeton | `~/.lichess_token` |
| `GARDER` | `1` conserve le répertoire temporaire | supprimé |

```bash
GARDER=1 ./test-app.sh
```

### Tests hors réseau

| Famille | Tests | Ce qui est vérifié |
|---|---|---|
| Ligne de commande | T01 à T04, T50, T71 | compilation, aide, options refusées avec le code 2, fichier introuvable, valeurs `nan` et `inf`, options retirées |
| Plateforme | T31, T32 | commandes `apt` ou `brew` proposées selon le système, emplacements par défaut |
| Archive | T05, T06, T08, T48, T53, M1 | contenu du zip, dossier gardé, répertoire de sortie, noms à point ou accentués, interruption pendant l'archivage |
| Encodages | T34 à T47 | latin-1, cp1252, UTF-16, UTF-8 abîmé, octets NUL, fins de ligne, caractères de contrôle, locale C, noms de fichiers |
| Jeton | T27, T43 | fichier absent, marque d'ordre des octets, jeton non ASCII refusé, jeton jamais affiché |
| URL | T54 | adresses qui ne sont pas des parties, refusées sans rien envoyer |
| Explorateur simulé | T49, T56 | réponses inattendues, arrêt au coup nul |
| Réglages | T57 à T63, T68, T69 | premier lancement, priorité de `--pseudos`, fichier mal formé, cadence et niveau vérifiés, correspondance, purge |
| Prompt | T64 à T67, T74 | écrit à côté de l'archive, passages gardés ou retirés, modèle fautif refusé, script copié sans son modèle, prompt court de `--prompt-seul` |
| Moteur | T25, T26, T51, T52, T55, M2 | moteur introuvable, analyse limitée aux premiers coups, mat manqué, coup nul, options hors bornes, analyse complète |
| Partie d'essai | T70 | `test.pgn` : commentaires, variantes, prise en passant, promotion, roques, coup nul |
| Résultat contraire | T72 | partie notée gagnée dans une position perdue : la synthèse et le prompt le disent |
| Vérification | T73 | `verifier-analyse.py` : un PGN conforme passe, un PGN fautif voit chacun de ses défauts relevé, PGN absent, archive illisible |

### Tests avec `--reseau`

| Famille | Tests | Ce qui est vérifié |
|---|---|---|
| Catalogue | T09 à T13 | téléchargement, réinstallation identique, catalogue absent ou tronqué |
| Explorateur | T14 à T23, T33 | base maîtres, base Lichess, filtres, seuils, modes d'arrêt, pause entre deux requêtes, roque retrouvé dans la base |
| Jeton | T28, T29 | fichier lisible par d'autres signalé, jeton absent de l'archive et du journal |
| Source Lichess | T24 | partie téléchargée par URL et par identifiant, si vous en donnez une |
| Coup nul | N1 | arrêt sur le vrai explorateur, sans requête refusée |
| Collecte complète | N2 | explorateur et moteur ensemble |

Les chiffres de l'explorateur changent chaque mois : ces tests vérifient des formes et des ordres de grandeur, pas des totaux exacts.

### La partie d'essai

`test.pgn` réunit dans une seule partie légale ce qui a déjà fait trébucher un lecteur de PGN :

- balises accentuées
- commentaire d'avant le premier coup, commentaire de fin de ligne introduit par un point-virgule
- NAG, signes `??` et `?`, commentaires d'horloge `[%clk]`
- variantes emboîtées
- mat manqué, prise en passant, promotion avec prise et échec, les deux roques, un coup nul

La partie n'a aucun intérêt échiquéen. Elle sert aussi à un essai complet, à la main :

```bash
./ianalyze.py test.pgn --sans-questions
```

### Le seul test à jouer à la main

Réinstaller l'environnement virtuel touche à votre installation : `test-app.sh` ne le fait pas.

```bash
./ianalyze.py --installer-venv
```

Attendu, sur un environnement déjà présent : "Environnement virtuel déjà présent", puis "Installation de python-chess dans l'environnement virtuel." et "Environnement virtuel opérationnel".
