# IAnalyze : commandes, options et sorties

Cette page est l'aide-mémoire d'IAnalyze, bâtie comme une page de manuel : chaque commande, chaque option, et ce que le terminal affiche.

Le [README](README.md) explique l'installation et l'usage courant. [TECHNIQUE.md](TECHNIQUE.md) explique le fonctionnement.

## Sommaire

- [NOM](#nom)
- [SYNOPSIS](#synopsis)
- [DESCRIPTION](#description)
- <details><summary><a href="#exemples">EXEMPLES</a></summary>

  - [première collecte](#première-collecte)
  - [collecte sans rien saisir](#collecte-sans-rien-saisir)
  - [partie de Lichess](#partie-de-lichess)
  - [avec l'explorateur](#avec-lexplorateur)
  - [pour un LLM qui n'ouvre pas les zip](#pour-un-llm-qui-nouvre-pas-les-zip)
  - [vérifier la réponse du LLM](#vérifier-la-réponse-du-llm)

  </details>
- <details><summary><a href="#options">OPTIONS</a></summary>

  - [général](#général)
  - [environnement virtuel](#environnement-virtuel)
  - [questions de démarrage](#questions-de-démarrage)
  - [catalogue des ouvertures](#catalogue-des-ouvertures)
  - [sortie](#sortie)
  - [explorateur](#explorateur)
  - [moteur](#moteur)
  - [vérificateur](#vérificateur)

  </details>
- [MESSAGES D'ERREUR](#messages-derreur)
- [CODES DE RETOUR](#codes-de-retour)
- [FICHIERS](#fichiers)
- [VOIR AUSSI](#voir-aussi)

## NOM

**ianalyze.py** : prépare l'analyse d'une partie d'échecs par un LLM.

**verifier-analyse.py** : contrôle le PGN annoté que le LLM a rendu.

## SYNOPSIS

```text
./ianalyze.py SOURCE [options]
./ianalyze.py --installer-venv [--venv CHEMIN]
./ianalyze.py --installer-catalogue [--catalogue REP]
./ianalyze.py --purge-reglages [--reglages FICHIER]
./ianalyze.py --help

./verifier-analyse.py ARCHIVE PGN [--synthese FICHIER] [--nom NOM] [--prompt-seul] [--perimetre N]
```

SOURCE est un fichier PGN, l'adresse d'une partie de Lichess ou son identifiant de 8 caractères.

## DESCRIPTION

`ianalyze.py` rassemble le PGN d'une partie, les statistiques de l'explorateur Lichess et les évaluations de Stockfish.   
Il écrit une archive zip et le prompt qui va avec, à donner à un LLM. Il n'analyse rien lui-même.

`verifier-analyse.py` compare ensuite le PGN annoté rendu par le LLM à cette archive.

### Lire cette page

- Chaque exemple donne la commande, puis ce que le terminal affiche.
- Les lignes qui commencent par une heure forment le journal : elles vont sur la sortie d'erreur.
- La dernière ligne, le chemin du fichier produit, est la seule à aller sur la sortie standard.
- Une ligne `...` remplace des lignes retirées pour abréger.
- `~` désigne votre répertoire personnel.

### D'où viennent les sorties

Ce sont de vraies sorties de la version 4.0.0, relevées le 21 novembre 2026 sous Linux, avec Python 3.13 et Stockfish 16.   
Celles de l'explorateur viennent de collectes du 20 novembre 2026 : ses statistiques changent chaque mois, les vôtres différeront.

Les évaluations du moteur varient elles aussi un peu, d'une machine à l'autre et d'un lancement à l'autre.   
Pour être rejoués sans jeton Lichess et sans rien saisir, la plupart des exemples ajoutent `--sans-explorateur` et `--sans-questions`.

### Les parties des exemples

Tous les fichiers cités dans cette page sont dans le répertoire `parties-exemples` du dépôt.

Pour rejouer un exemple tel quel, placez-vous dans ce répertoire et appelez le script un niveau plus haut : `../ianalyze.py` à la place de `./ianalyze.py`.

```bash
cd parties-exemples
```

```bash
../ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions
```

| Fichier | Ce que c'est |
|---|---|
| `ma-partie.pgn` | une partie italienne de neuf demi-coups, celle de presque tous les exemples |
| `polonaise.pgn` | une ouverture qui sort tôt de la théorie, pour les options de l'explorateur |
| `partie-commentee.pgn` | une vraie partie de 25 coups, anonymisée, exportée de Lichess avec ses commentaires, ses variantes et ses horloges |
| `francais.pgn`, `deux-parties.pgn`, `position.pgn`, `accolade.pgn` | quatre fichiers que le script refuse, pour les messages d'erreur |
| `analyse-llm.pgn`, `analyse-fautive.pgn`, `analyse-courte.pgn` | trois PGN annotés écrits pour l'exemple, à la place de ceux qu'un LLM rendrait |
| `conversation.txt` | le texte d'une conversation, pour l'option `--synthese` du vérificateur |

Vos propres parties se rangent où vous voulez : le script prend le chemin du PGN que vous lui donnez, et écrit l'archive dans le répertoire courant, ou dans celui de `--sortie`.

`ma-partie.pgn` est une partie italienne de neuf demi-coups :

```text
[Event "Partie amicale"]
[Site "?"]
[Date "2026.11.19"]
[Round "-"]
[White "MonPseudo"]
[Black "Adversaire"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 *
```

`polonaise.pgn` sort tôt de la théorie, ce qui met les seuils de l'explorateur à l'épreuve :

```text
1. b4 g6 2. Bb2 Nf6 3. e3 Bg7 4. Nf3 O-O *
```

## EXEMPLES

Ces exemples supposent IAnalyze installé (README, section 2). Les deux commandes d'installation sont décrites plus bas, à [`--installer-venv`](#--installer-venv) et à [`--installer-catalogue`](#--installer-catalogue).

### Première collecte

Au tout premier lancement dans un terminal, le script demande vos réglages, puis pose les questions propres à la partie. 

Entrée retient la valeur proposée entre parenthèses.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur
```

```text
[01:08:35] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:08:35] Lecture du PGN local : ma-partie.pgn
[01:08:35] Réglages : 3 réponse(s) à donner une seule fois, gardée(s) dans ~/.config/IAnalyze/reglages.ini.
Votre pseudo de joueur, ou plusieurs séparés par des virgules ? (Entrée : aucun) MonPseudo
Votre cadence habituelle : [t]emps réel, [c]orrespondance ou [i]nconnue ? (Entrée : non précisée) t
  Minutes par joueur ? 15
  Incrément en secondes ? 10
Votre niveau, en points Elo approximatifs ? (Entrée : inconnu) 1300
[01:08:36] Réglages enregistrés : ~/.config/IAnalyze/reglages.ini
[01:08:36] Questions de démarrage, Entrée retient la valeur proposée.
Cadence de la partie : [t]emps réel, [c]orrespondance ou [i]nconnue ? (Entrée : rapide, 15 minutes + 10 secondes par coup)
Périmètre : les N premiers coups, ou la partie complète ? (Entrée : la partie complète)
Ce que vous cherchez à comprendre dans cette partie ? (Entrée : laissé ouvert) la sortie de l'ouverture
Contexte particulier : zeitnot, fatigue, ouverture inconnue, adversaire particulier ? (Entrée : rien)
Autres commentaires à inclure dans le PGN final ? (Entrée : rien)
[01:08:38] Dossier de travail : analyse-ma-partie-20261121-010838
[01:08:38] Stockfish : évaluation de 9 demi-coups, profondeur 18, multipv 3, threads 4. C'est la phase la plus longue.
[01:08:38] Stockfish : demi-coup 1/9 (e4)
[01:08:39] Stockfish : demi-coup 2/9 (e5)
[01:08:41] Stockfish : demi-coup 3/9 (Nf3)
[01:08:42] Stockfish : demi-coup 4/9 (Nc6), reste moins d'une minute
[01:08:43] Stockfish : demi-coup 5/9 (Bc4), reste moins d'une minute
[01:08:44] Stockfish : demi-coup 6/9 (Bc5), reste moins d'une minute
[01:08:45] Stockfish : demi-coup 7/9 (c3), reste moins d'une minute
[01:08:45] Stockfish : demi-coup 8/9 (Nf6), reste moins d'une minute
[01:08:46] Stockfish : demi-coup 9/9 (d3), reste moins d'une minute
[01:08:47] Stockfish : terminé en 0 min 08 s.
[01:08:47] Synthèse écrite : analyse-ma-partie-20261121-010838/synthese.md
[01:08:47] Création de l'archive : analyse-ma-partie-20261121-010838.zip
[01:08:47] Dossier de travail supprimé.
[01:08:47] Prompt d'analyse écrit : analyse-ma-partie-20261121-010838.prompt.txt, à coller dans la conversation, l'archive en pièce jointe.
analyse-ma-partie-20261121-010838.zip
```

Les réglages ne seront plus demandés.   
La dernière ligne est le chemin de l'archive, celle d'avant nomme le prompt : collez son contenu dans une conversation neuve avec le LLM, et joignez l'archive.

### Collecte sans rien saisir

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions
```

```text
[01:08:11] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:08:11] Lecture du PGN local : ma-partie.pgn
[01:08:11] Questions de démarrage sautées : option --sans-questions.
[01:08:11] Dossier de travail : analyse-ma-partie-20261121-010811
[01:08:11] Stockfish : évaluation de 9 demi-coups, profondeur 18, multipv 3, threads 4. C'est la phase la plus longue.
[01:08:11] Stockfish : demi-coup 1/9 (e4)
[01:08:12] Stockfish : demi-coup 2/9 (e5)
[01:08:13] Stockfish : demi-coup 3/9 (Nf3)
[01:08:15] Stockfish : demi-coup 4/9 (Nc6), reste moins d'une minute
[01:08:16] Stockfish : demi-coup 5/9 (Bc4), reste moins d'une minute
[01:08:17] Stockfish : demi-coup 6/9 (Bc5), reste moins d'une minute
[01:08:18] Stockfish : demi-coup 7/9 (c3), reste moins d'une minute
[01:08:18] Stockfish : demi-coup 8/9 (Nf6), reste moins d'une minute
[01:08:19] Stockfish : demi-coup 9/9 (d3), reste moins d'une minute
[01:08:20] Stockfish : terminé en 0 min 08 s.
[01:08:20] Synthèse écrite : analyse-ma-partie-20261121-010811/synthese.md
[01:08:20] Création de l'archive : analyse-ma-partie-20261121-010811.zip
[01:08:20] Dossier de travail supprimé.
[01:08:20] Prompt d'analyse écrit : analyse-ma-partie-20261121-010811.prompt.txt, à coller dans la conversation, l'archive en pièce jointe.
analyse-ma-partie-20261121-010811.zip
```

### Partie de Lichess

Par son adresse, ou par son identifiant, la suite de 8 caractères qui suit `lichess.org/` :

```bash
./ianalyze.py https://lichess.org/<identifiant>
```

```bash
./ianalyze.py <identifiant>
```

Le PGN est téléchargé, puis la collecte se déroule comme pour un fichier.   
L'archive porte l'identifiant de la partie : `analyse-<identifiant>-<date>.zip`.

### Avec l'explorateur

Sans `--sans-explorateur`, le script interroge aussi l'explorateur de Lichess.   
Il lui faut le jeton et le catalogue des ouvertures (README, section 2).

```bash
./ianalyze.py ma-partie.pgn --sans-questions --base maitres
```

La section 2 de `synthese.md` reçoit alors la table de l'explorateur, une ligne par demi-coup interrogé. 

Pour cette partie et la base des maîtres, le 20 novembre 2026 :

| # | Coup | Trait | Parties pos. | Joué | Rang | Fréq. | Score B. | Majoritaire | Fréq. majo | Score B. majo | Ouverture |
|---:|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|
| 1 | 1 | Blancs | 2997412 | e4 | 1 | 45.6 % | 53.8 % | e4 | 45.6 % | 53.8 % | B00 King's Pawn Game |
| 2 | 1 | Noirs | 1368125 | e5 | 2 | 24.3 % | 54.4 % | c5 | 45.9 % | 52.8 % | C20 King's Pawn Game |
| 3 | 2 | Blancs | 332635 | Nf3 | 1 | 92.3 % | 54.6 % | Nf3 | 92.3 % | 54.6 % | C40 King's Knight Opening |
| 4 | 2 | Noirs | 307183 | Nc6 | 1 | 85.8 % | 54.1 % | Nc6 | 85.8 % | 54.1 % | C44 King's Knight Opening: Normal Variation |
| 5 | 3 | Blancs | 264440 | Bc4 | 2 | 19.2 % | 53.0 % | Bb5 | 65.3 % | 54.9 % | C50 Italian Game |
| 6 | 3 | Noirs | 51257 | Bc5 | 1 | 52.5 % | 52.5 % | Bc5 | 52.5 % | 52.5 % | C50 Italian Game: Giuoco Piano |
| 7 | 4 | Blancs | 26979 | c3 | 1 | 55.6 % | 52.8 % | c3 | 55.6 % | 52.8 % | C53 Italian Game: Classical Variation |
| 8 | 4 | Noirs | 14997 | Nf6 | 1 | 96.2 % | 52.5 % | Nf6 | 96.2 % | 52.5 % | C54 Italian Game: Classical Variation |
| 9 | 5 | Blancs | 14427 | d3 | 1 | 74.2 % | 53.3 % | d3 | 74.2 % | 53.3 % | C54 Italian Game: Classical Variation, Giuoco Pianissimo |

```text
Arrêt de l'interrogation : fin de la partie.
```

### Pour un LLM qui n'ouvre pas les zip

`--prompt-seul` écrit un prompt court, à coller seul dans la conversation. Aucune archive n'est écrite.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --prompt-seul
```

```text
[01:09:21] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:09:21] Lecture du PGN local : ma-partie.pgn
[01:09:21] Questions de démarrage sautées : option --sans-questions.
[01:09:21] Dossier de travail : analyse-ma-partie-20261121-010921
[01:09:21] Stockfish : évaluation de 9 demi-coups, profondeur 18, multipv 3, threads 4. C'est la phase la plus longue.
...
[01:09:30] Synthèse écrite : analyse-ma-partie-20261121-010921/synthese.md
[01:09:30] Prompt d'analyse écrit : analyse-ma-partie-20261121-010921.prompt.txt, à coller seul dans la conversation : il porte la partie et les évaluations, aucune pièce jointe n'est nécessaire.
[01:09:30] Dossier de travail supprimé, aucune archive n'est écrite avec --prompt-seul.
analyse-ma-partie-20261121-010921.prompt.txt
```

Le prompt porte les consignes, la partie, puis les évaluations du moteur :

```text
Vous êtes Maître International d'échecs.

Analysez la partie ci-dessous coup par coup, pour un joueur qui cherche
à progresser. Le style est instructif et détaillé, en français, et vous
tutoyez le joueur.
Le joueur avait les Blancs.
Son niveau : environ 1300 Elo, déclaré par le joueur.
...
Évaluations de Stockfish, profondeur 18, du point de vue des Blancs,
après chaque coup joué.
Derrière un coup faible viennent sa nature, ce qu'il perd en centipions
par rapport au meilleur coup, puis ce meilleur coup, sa suite et son
évaluation. "mat" à la place du nombre : le coup manque un mat ou en
concède un.
Un mat s'écrit "#+2", les Blancs matent en deux coups, ou "#-1", les
Noirs matent en un coup. Le compte se lit après le coup de la ligne :
"#+0" ou "#-0", ce coup donne mat.

1. e4           +0.35
1... e5         +0.34
2. Nf3          +0.32
2... Nc6        +0.28
3. Bc4          +0.23
3... Bc5        +0.25
4. c3           +0.24
4... Nf6        +0.20
5. d3           +0.16
```

### Vérifier la réponse du LLM

`analyse-llm.pgn` tient ici la place du PGN annoté qu'un LLM aurait rendu : il a été écrit pour l'exemple.   
Le vérificateur le compare à l'archive :

```bash
./verifier-analyse.py analyse-ma-partie-20261121-010838.zip analyse-llm.pgn
```

```text
Contrôle d'une analyse rendue par un LLM
  archive : analyse-ma-partie-20261121-010838.zip
  PGN     : analyse-llm.pgn

=== 1. Lecture du PGN ===
  OK        fichier en UTF-8
  OK        aucun coup illégal, variantes comprises (0 erreur(s) de lecture)

=== 2. Ligne principale ===
  OK        ligne principale identique à la partie d'origine (9 demi-coups)

=== 3. Format ===
  OK        aucune ligne de plus de 79 caractères
  OK        aucune accolade dans un commentaire
  OK        aucun caractère % dans un commentaire
  OK        aucun tiret cadratin
  OK        aucun point-virgule dans un commentaire
  OK        pas de notation suffixe, les NAG seuls
  OK        les sept balises obligatoires, dans l'ordre
  OK        les autres balises par ordre alphabétique
  OK        valeurs des sept balises reprises de la partie d'origine
  OK        balise Annotator renseignée : "Exemple"
  OK        balise PlyCount : "9", attendu "9"
  OK        marqueur de fin "*" identique à la balise Result "*"

=== 4. Coups commentés ===
  OK        résumé de la partie avant le coup 1 (3 ligne(s), 6 à 10 demandées)
  INFO      3 coup(s) commenté(s) sur 9, 15 à 25 visés sur une partie complète
  INFO      0 coup(s) porteur(s) d'un NAG
  OK        les 0 erreur(s) et gaffe(s) de Stockfish sont toutes commentées (0 oubliée(s))
  OK        aucun NAG de position contraire à l'évaluation du moteur
  INFO      NAG de qualité : 0 conforme(s) à la nature donnée par le moteur, 0 d'un autre avis

=== 5. Évaluations citées dans le PGN ===
  INFO      2 évaluation(s) citée(s)
  OK        toutes se retrouvent dans les données du moteur (0 introuvable(s))

=== 6. Variantes ===
  INFO      1 variante(s) jouable(s) sur la ligne principale
  OK        aucune variante de plus de 5 demi-coups
  INFO      0 variante(s) partent d'une ligne du moteur, 1 sont du cru du LLM
            - 3. Bb5

=== Bilan ===
  échecs     : 0
  attentions : 0
```

Un PGN fautif, lui, voit chacun de ses défauts nommé.   
Celui-ci porte une ligne vide entre deux coups, un signe pour cent, un chiffre inventé et une variante écrite dans un commentaire :

```bash
./verifier-analyse.py analyse-ma-partie-20261121-010838.zip analyse-fautive.pgn --nom "Modèle essayé"
```

```text
Contrôle d'une analyse rendue par un LLM
  modèle  : Modèle essayé
  archive : analyse-ma-partie-20261121-010838.zip
  PGN     : analyse-fautive.pgn
...
=== 1. Lecture du PGN ===
...
  ECHEC     ligne vide dans le corps de la partie : python-chess y arrête sa lecture et ne voit que 2 demi-coup(s) sur 9
            - ligne 13
...
=== 2. Ligne principale ===
...
=== 3. Format ===
...
  ECHEC     aucun caractère % dans un commentaire
            - 1. e4
...
=== 4. Coups commentés ===
...
=== 5. Évaluations citées dans le PGN ===
...
  ECHEC     toutes se retrouvent dans les données du moteur (1 introuvable(s))
            - 1. e4 : +1.50
...
=== 6. Variantes ===
...
  ECHEC     aucune variante jouable : les 1 variantes sont écrites à l'intérieur des commentaires, où elles ne sont que du texte
...
=== Bilan ===
  échecs     : 4
  attentions : 0
```

## OPTIONS

### Général

#### `-h, --help`

Affiche l'aide complète et les exemples.

```bash
./ianalyze.py --help
```

```text
usage: ianalyze.py [-h] [--installer-venv] [--venv CHEMIN] [--sans-questions]
                   [--pseudos LISTE] [--reglages FICHIER] [--purge-reglages]
                   [--installer-catalogue] [--catalogue REP] [--sortie REP]
                   [--garder-dossier] [--prompt FICHIER] [--sans-prompt]
                   [--prompt-seul] [--base {lichess,maitres}]
                   [--cadences LISTE] [--classements LISTE]
                   [--jeton-fichier FICHIER] [--seuil-parties N]
                   [--seuil-frequence P] [--jusqu-a-epuisement]
                   [--coups-min N] [--max-demicoups N] [--pause S]
                   [--sans-explorateur] [--coups-stockfish N] [--profondeur D]
                   [--multipv K] [--fils N] [--hachage MO]
                   [--stockfish CHEMIN] [--longueur-pv N] [--delai S]
                   [--debug]
                   [source]

Collecte le matériel d'analyse d'une partie d'échecs : PGN, statistiques
de l'explorateur Lichess (base de tous les joueurs, ou base maîtres avec
--base maitres) pour déterminer la sortie de théorie, et évaluations
Stockfish de la partie. Ne produit aucune analyse.

positional arguments:
  source                fichier PGN local, URL Lichess, ou identifiant de
                        partie à huit ou douze caractères

options:
  -h, --help            show this help message and exit
  --delai S             délai réseau maximal, en secondes (défaut : 30)
  --debug               laisse remonter la trace complète des erreurs
                        inattendues
...
```

#### `--delai S`

*Défaut : `30`*

Délai réseau maximal par requête, en secondes : export PGN,  explorateur, téléchargement du catalogue.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --delai 60
```

Rien ne change à l'écran hors réseau : le délai ne joue que sur les requêtes vers Lichess.   
Le journal est le même qu'à la section [Collecte sans rien saisir](#collecte-sans-rien-saisir).

#### `--debug`

Laisse remonter la trace complète d'une erreur inattendue, expurgée du jeton.   
Sans cette option, seul un message d'une ligne s'affiche.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --debug
```

Sans erreur inattendue, rien ne change. Le journal est le même qu'à la section [Collecte sans rien saisir](#collecte-sans-rien-saisir).

### Environnement virtuel

#### `--installer-venv`

Crée l'environnement virtuel s'il manque, y installe ou met à jour python-chess, puis quitte.   
Il peut être relancé sans risque.

La première fois :

```bash
./ianalyze.py --installer-venv
```

```text
[01:06:52] Création de l'environnement virtuel : ~/.local/share/IAnalyze/venv
[01:06:54] Installation de python-chess dans l'environnement virtuel.
[01:06:58] Environnement virtuel opérationnel : ~/.local/share/IAnalyze/venv/bin/python3
```

Les fois suivantes :

```bash
./ianalyze.py --installer-venv
```

```text
[01:07:02] Environnement virtuel déjà présent : ~/.local/share/IAnalyze/venv
[01:07:02] Installation de python-chess dans l'environnement virtuel.
[01:07:03] Environnement virtuel opérationnel : ~/.local/share/IAnalyze/venv/bin/python3
```

#### `--venv CHEMIN`

*Défaut : `~/.local/share/IAnalyze/venv`*

Emplacement de l'environnement virtuel, à l'installation comme à l'usage.

```bash
./ianalyze.py --installer-venv --venv ~/venv/echecs
```

```text
[01:11:35] Création de l'environnement virtuel : ~/venv/echecs
[01:11:37] Installation de python-chess dans l'environnement virtuel.
[01:11:39] Environnement virtuel opérationnel : ~/venv/echecs/bin/python3
```

La même option sert ensuite à chaque collecte, et le journal nomme l'environnement employé :

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --venv ~/venv/echecs
```

```text
[01:11:39] Environnement virtuel : relance via ~/venv/echecs/bin/python3
[01:11:39] Lecture du PGN local : ma-partie.pgn
...
```

### Questions de démarrage

#### `--sans-questions`

Ne pose aucune question, ni camp ni contexte.   
Rien n'est retenu à votre place : le prompt dit alors au LLM que vos réponses n'ont pas été recueillies, et c'est lui qui vous pose les questions avant d'analyser.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions
```

```text
...
[01:08:11] Lecture du PGN local : ma-partie.pgn
[01:08:11] Questions de démarrage sautées : option --sans-questions.
...
```

#### `--pseudos LISTE`

*Défaut : ceux de vos réglages*

Vos noms de joueur, séparés par des virgules, cherchés sans tenir compte de la casse dans White et Black pour déduire votre camp.   
Le premier sert à compléter une balise vide. L'option remplace, le temps d'un lancement, les pseudos du fichier de réglages.

`ma-partie.pgn` oppose MonPseudo, avec les Blancs, à Adversaire.   
Avec le pseudo de celui-ci, le camp retenu pour le prompt change :

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --pseudos Adversaire
```

```bash
grep "camp dans cette partie" analyse-ma-partie-*.prompt.txt
```

```text
- camp dans cette partie : Noirs
```

#### `--reglages FICHIER`

*Défaut : `~/.config/IAnalyze/reglages.ini`*

Fichier de réglages à employer à la place du vôtre : pseudos, cadence habituelle et niveau (README, section 2).

Si le fichier n'existe pas encore, le script pose ses trois questions dans le terminal, puis le crée.   
C'est la façon de tenir plusieurs profils sur un même compte, un par joueur par exemple.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --reglages ~/.config/IAnalyze/joueur2.ini
```

```text
[01:12:11] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:12:11] Lecture du PGN local : ma-partie.pgn
[01:12:11] Réglages : 3 réponse(s) à donner une seule fois, gardée(s) dans ~/.config/IAnalyze/joueur2.ini.
Votre pseudo de joueur, ou plusieurs séparés par des virgules ? (Entrée : aucun) Joueur2
Votre cadence habituelle : [t]emps réel, [c]orrespondance ou [i]nconnue ? (Entrée : non précisée) i
Votre niveau, en points Elo approximatifs ? (Entrée : inconnu) 1800
[01:12:12] Réglages enregistrés : ~/.config/IAnalyze/joueur2.ini
[01:12:12] Questions de démarrage, Entrée retient la valeur proposée.
Avez-vous joué les Blancs ou les Noirs ? [b/n] n
Cadence de la partie : [t]emps réel, [c]orrespondance ou [i]nconnue ? (Entrée : non précisée)
Périmètre : les N premiers coups, ou la partie complète ? (Entrée : la partie complète)
Ce que vous cherchez à comprendre dans cette partie ? (Entrée : laissé ouvert)
Contexte particulier : zeitnot, fatigue, ouverture inconnue, adversaire particulier ? (Entrée : rien)
Autres commentaires à inclure dans le PGN final ? (Entrée : rien)
[01:12:14] Dossier de travail : analyse-ma-partie-20261121-011214
...
[01:12:23] Synthèse écrite : analyse-ma-partie-20261121-011214/synthese.md
[01:12:23] Création de l'archive : analyse-ma-partie-20261121-011214.zip
[01:12:23] Dossier de travail supprimé.
[01:12:23] Prompt d'analyse écrit : analyse-ma-partie-20261121-011214.prompt.txt, à coller dans la conversation, l'archive en pièce jointe.
analyse-ma-partie-20261121-011214.zip
```

Ici le pseudo du second joueur ne figure pas dans la partie : le script demande donc son camp.   
Les lancements suivants avec ce fichier ne redemandent pas les réglages.

- Une clef absente du fichier est demandée une seule fois, puis enregistrée.
- Une clef présente, même vide, n'est jamais redemandée.
- Une cadence ou un niveau illisible est redemandé.
- Les clefs et les sections que vous ajoutez sont conservées.

Un fichier mal formé arrête le script avec un message.

#### `--purge-reglages`

Supprime le fichier de réglages, puis quitte. Aucune partie n'est attendue.   
Vos réponses seront redemandées à la prochaine collecte lancée dans un terminal.

Avec `--reglages`, c'est le fichier désigné qui est supprimé. Son répertoire reste en place.

Un fichier absent n'est pas une erreur, un répertoire est refusé.   
Un fichier qui n'est pas un fichier de réglages est refusé lui aussi : seul un fichier portant la section `[joueur]`, ou un fichier vide, est supprimé.

```bash
./ianalyze.py --purge-reglages
```

```text
[01:11:14] Réglages supprimés : ~/.config/IAnalyze/reglages.ini. Ils seront redemandés à la prochaine collecte lancée sur un terminal.
```

Relancée aussitôt :

```bash
./ianalyze.py --purge-reglages
```

```text
[01:11:14] Aucun fichier de réglages à supprimer : ~/.config/IAnalyze/reglages.ini
```

### Catalogue des ouvertures

#### `--installer-catalogue`

Télécharge le catalogue des ouvertures de Lichess, le contrôle, puis quitte.   
Relancer l'option le met à jour. Un échec laisse l'ancien catalogue en place.

```bash
./ianalyze.py --installer-catalogue
```

```text
[01:07:03] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:07:03] Téléchargement du catalogue : https://raw.githubusercontent.com/lichess-org/chess-openings/master/a.tsv
[01:07:04] Téléchargement du catalogue : https://raw.githubusercontent.com/lichess-org/chess-openings/master/b.tsv
[01:07:04] Téléchargement du catalogue : https://raw.githubusercontent.com/lichess-org/chess-openings/master/c.tsv
[01:07:05] Téléchargement du catalogue : https://raw.githubusercontent.com/lichess-org/chess-openings/master/d.tsv
[01:07:05] Téléchargement du catalogue : https://raw.githubusercontent.com/lichess-org/chess-openings/master/e.tsv
[01:07:06] Catalogue installé : 3865 lignes, 3865 positions nommées, 7982 positions connues, dans ~/.local/share/IAnalyze/catalogue.tsv
```

#### `--catalogue REP`

*Défaut : `~/.local/share/IAnalyze`*

Répertoire du catalogue local, à l'installation comme à l'usage.

```bash
./ianalyze.py --installer-catalogue --catalogue ~/echecs/catalogue
```

```text
[01:11:48] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:11:48] Téléchargement du catalogue : https://raw.githubusercontent.com/lichess-org/chess-openings/master/a.tsv
...
[01:11:51] Catalogue installé : 3865 lignes, 3865 positions nommées, 7982 positions connues, dans ~/echecs/catalogue/catalogue.tsv
```

La même option sert ensuite à chaque collecte :

```bash
./ianalyze.py ma-partie.pgn --catalogue ~/echecs/catalogue
```

### Sortie

Sans aucune de ces options, le script écrit deux fichiers dans le répertoire courant : l'archive et le prompt complet.

| Vous ajoutez | Le script écrit | Vous en faites |
|---|---|---|
| rien | l'archive `.zip` et le prompt complet `.prompt.txt` | vous collez le prompt dans la conversation et vous joignez l'archive |
| `--prompt-seul` | le prompt court, sans archive | vous collez le prompt, sans rien joindre |
| `--sans-prompt` | l'archive, sans prompt | vous rédigez vous-même votre demande au LLM |
| `--prompt FICHIER` | l'archive et un prompt tiré de votre propre modèle | vous collez le prompt et vous joignez l'archive |

#### `--sortie REP`

*Défaut : `.`, le répertoire courant*

Répertoire où le script écrit ses fichiers. Il est créé au besoin.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --sortie ~/analyses
```

```text
[01:09:00] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:09:01] Lecture du PGN local : ma-partie.pgn
...
[01:09:01] Dossier de travail : ~/analyses/analyse-ma-partie-20261121-010901
...
[01:09:10] Synthèse écrite : ~/analyses/analyse-ma-partie-20261121-010901/synthese.md
[01:09:10] Création de l'archive : ~/analyses/analyse-ma-partie-20261121-010901.zip
[01:09:10] Dossier de travail supprimé.
[01:09:10] Prompt d'analyse écrit : ~/analyses/analyse-ma-partie-20261121-010901.prompt.txt, à coller dans la conversation, l'archive en pièce jointe.
~/analyses/analyse-ma-partie-20261121-010901.zip
```

```bash
ls ~/analyses
```

```text
analyse-ma-partie-20261121-010901.prompt.txt
analyse-ma-partie-20261121-010901.zip
```

#### `--garder-dossier`

Pendant la collecte, le script range ses fichiers dans un dossier de travail, `analyse-<partie>-<date>`.   
Il le compresse ensuite en zip, puis le supprime.

Avec cette option, le dossier reste à côté de l'archive.   
Il sert quand le LLM n'ouvre pas les zip : vous lui envoyez alors les fichiers du dossier.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --garder-dossier
```

```text
[01:09:10] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:09:10] Lecture du PGN local : ma-partie.pgn
...
[01:09:10] Dossier de travail : analyse-ma-partie-20261121-010910
...
[01:09:20] Synthèse écrite : analyse-ma-partie-20261121-010910/synthese.md
[01:09:20] Création de l'archive : analyse-ma-partie-20261121-010910.zip
[01:09:20] Dossier conservé sur demande : analyse-ma-partie-20261121-010910
[01:09:20] Prompt d'analyse écrit : analyse-ma-partie-20261121-010910.prompt.txt, à coller dans la conversation, l'archive en pièce jointe.
analyse-ma-partie-20261121-010910.zip
```

Le dossier porte les fichiers de l'archive :

```bash
ls -R analyse-ma-partie-*/ | grep -v "^$"
```

```text
analyse-ma-partie-20261121-010910/:
collecte.json
partie.pgn
stockfish
synthese.md
analyse-ma-partie-20261121-010910/stockfish:
evaluations.json
```

#### `--prompt-seul`

Écrit un prompt court, à coller seul dans la conversation, sans pièce jointe : quelques consignes, la partie, puis les évaluations de Stockfish.

C'est la route à prendre avec un compte gratuit, ou avec un LLM qui n'ouvre pas les zip ou n'exécute pas de code (README, section 7).   
Le PGN annoté lui est demandé dans un bloc de code.

Aucune archive n'est écrite : le prompt est le seul fichier produit, et c'est son chemin qui est écrit sur la sortie standard.   
Pour l'archive et ses données, lancez une collecte sans cette option.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --prompt-seul
```

```text
[01:09:21] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:09:21] Lecture du PGN local : ma-partie.pgn
...
[01:09:21] Dossier de travail : analyse-ma-partie-20261121-010921
...
[01:09:30] Synthèse écrite : analyse-ma-partie-20261121-010921/synthese.md
[01:09:30] Prompt d'analyse écrit : analyse-ma-partie-20261121-010921.prompt.txt, à coller seul dans la conversation : il porte la partie et les évaluations, aucune pièce jointe n'est nécessaire.
[01:09:30] Dossier de travail supprimé, aucune archive n'est écrite avec --prompt-seul.
analyse-ma-partie-20261121-010921.prompt.txt
```

Ajoutez `--garder-dossier` si vous comptez faire contrôler la réponse du LLM par `verifier-analyse.py` : le dossier de travail reste alors à côté du prompt.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --prompt-seul --garder-dossier
```

```text
[01:09:30] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:09:31] Lecture du PGN local : ma-partie.pgn
...
[01:09:31] Dossier de travail : analyse-ma-partie-20261121-010931
...
[01:09:39] Synthèse écrite : analyse-ma-partie-20261121-010931/synthese.md
[01:09:39] Prompt d'analyse écrit : analyse-ma-partie-20261121-010931.prompt.txt, à coller seul dans la conversation : il porte la partie et les évaluations, aucune pièce jointe n'est nécessaire.
[01:09:39] Dossier conservé sur demande : analyse-ma-partie-20261121-010931
analyse-ma-partie-20261121-010931.prompt.txt
```

S'exclut avec `--sans-prompt`.

#### `--sans-prompt`

N'écrit que l'archive, sans prompt. S'exclut avec `--prompt` et avec `--prompt-seul`.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --sans-prompt
```

```text
[01:09:39] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:09:39] Lecture du PGN local : ma-partie.pgn
...
[01:09:39] Dossier de travail : analyse-ma-partie-20261121-010939
...
[01:09:48] Synthèse écrite : analyse-ma-partie-20261121-010939/synthese.md
[01:09:48] Création de l'archive : analyse-ma-partie-20261121-010939.zip
[01:09:48] Dossier de travail supprimé.
analyse-ma-partie-20261121-010939.zip
```

#### `--prompt FICHIER`

*Défaut : `prompt-modele.txt`, rangé à côté du script*

À n'employer que si vous avez écrit votre propre modèle de prompt.

Le prompt d'une partie n'est pas un texte fixe. Le script le fabrique à partir d'un modèle :   
Un fichier texte dont il remplit les blancs, votre pseudo, votre camp ou le nom de l'archive, et dont il ne garde que les passages utiles à cette partie.

Cette option lui fait prendre votre modèle à la place de celui du dépôt.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --prompt ~/mon-modele.txt
```

```text
[01:09:48] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:09:48] Lecture du PGN local : ma-partie.pgn
...
[01:09:49] Dossier de travail : analyse-ma-partie-20261121-010949
...
[01:09:57] Synthèse écrite : analyse-ma-partie-20261121-010949/synthese.md
[01:09:57] Création de l'archive : analyse-ma-partie-20261121-010949.zip
[01:09:57] Dossier de travail supprimé.
[01:09:57] Prompt d'analyse écrit : analyse-ma-partie-20261121-010949.prompt.txt, à coller dans la conversation, l'archive en pièce jointe.
analyse-ma-partie-20261121-010949.zip
```

Le fichier doit exister.   
Pour écrire un modèle, partez d'une copie de `prompt-modele.txt` : ce qu'il peut contenir est décrit dans [TECHNIQUE.md](TECHNIQUE.md), section 12.

Avec `--prompt-seul`, le modèle par défaut est `prompt-seul-modele.txt`, et c'est de lui qu'il faut partir.

### Explorateur

Ces options demandent le jeton et le catalogue.   
Les extraits viennent de la section 2 de `synthese.md`, relevés le 20 novembre 2026.

#### `--base {lichess,maitres}`

*Défaut : `lichess`*

Base interrogée :

- `lichess` : les parties classées de tous les joueurs du site, la base de <https://lichess.org/opening>
- `maitres` : les parties de maîtres

```bash
./ianalyze.py polonaise.pgn --sans-questions --base lichess
```

| # | Coup | Trait | Parties pos. | Joué | Rang | Fréq. | Score B. | Majoritaire | Fréq. majo | Score B. majo | Ouverture |
|---:|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|
| 1 | 1 | Blancs | 7676304687 | b4 | 11 | 0.4 % | 53.4 % | e4 | 58.5 % | 51.3 % | A00 Polish Opening |
| 2 | 1 | Noirs | 33336712 | g6 | 5 | 4.9 % | 55.0 % | e5 | 34.5 % | 54.7 % | - |
| 3 | 2 | Blancs | 1638628 | Bb2 | 1 | 92.5 % | 55.9 % | Bb2 | 92.5 % | 55.9 % | - |
| 4 | 2 | Noirs | 1514424 | Nf6 | 1 | 67.6 % | 49.5 % | Nf6 | 67.6 % | 49.5 % | A00 Polish Opening: King's Indian Variation |
| 5 | 3 | Blancs | 2055319 | e3 | 1 | 24.5 % | 49.2 % | e3 | 24.5 % | 49.2 % | - |
| 6 | 3 | Noirs | 510542 | Bg7 | 1 | 96.6 % | 49.1 % | Bg7 | 96.6 % | 49.1 % | - |
| 7 | 4 | Blancs | 493481 | Nf3 | 1 | 39.5 % | 49.9 % | Nf3 | 39.5 % | 49.9 % | - |
| 8 | 4 | Noirs | 334723 | O-O | 1 | 69.6 % | 49.7 % | O-O | 69.6 % | 49.7 % | - |

```text
Arrêt de l'interrogation : fin de la partie.
Premier coup sous le seuil de 10.0 % hors catalogue : **Noirs joue g6** au coup **1** (demi-coup 2).
- fréquence du coup joué : 4.9 % (1640131 parties sur 33336712)
```

La même partie dans la base des maîtres, où elle est bien plus rare :

```bash
./ianalyze.py polonaise.pgn --sans-questions --base maitres
```

| # | Coup | Trait | Parties pos. | Joué | Rang | Fréq. | Score B. | Majoritaire | Fréq. majo | Score B. majo | Ouverture |
|---:|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|
| 1 | 1 | Blancs | 2997412 | b4 | 9 | 0.1 % | 46.7 % | e4 | 45.6 % | 53.8 % | A00 Polish Opening |
| 2 | 1 | Noirs | 2269 | g6 | 10 | 0.5 % | 45.8 % | e5 | 53.2 % | 45.1 % | - |

```text
Arrêt de l'interrogation : échantillon insuffisant au demi-coup 3 : 12 parties pour un seuil de 50.
```

#### `--cadences LISTE`

*Défaut : `bullet,blitz,rapid,classical,correspondence`*

Base `lichess` seulement. 

Cadences retenues, séparées par des virgules, parmi : 
- UltraBullet
- Bullet 
- Blitz 
- Rapid
- Classical
- Correspondence

La casse est tolérée, les doublons sont retirés.

#### `--classements LISTE`

*Défaut : `1000,1200,1400,1600,1800,2000,2200,2500`*

Base `lichess` seulement.   
Tranches de classement retenues parmi 0, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2500.

Chaque tranche court de sa valeur à la suivante : 0 couvre 0 à 999 (affichée "400" sur le site), 2500 tout ce qui dépasse.   
Une partie est rangée selon la moyenne des classements de ses deux joueurs.

Les filtres par défaut, plus la date de début fixée à janvier 2017, reprennent ceux de <https://lichess.org/opening> : vous y retrouvez les mêmes pourcentages.  
Les deux filtres ensemble, sur les parties lentes des joueurs classés sous 1200 :

```bash
./ianalyze.py polonaise.pgn --sans-questions --coups-min 0 --cadences rapid,classical --classements 0,1000
```

| # | Coup | Trait | Parties pos. | Joué | Rang | Fréq. | Score B. | Majoritaire | Fréq. majo | Score B. majo | Ouverture |
|---:|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|
| 1 | 1 | Blancs | 222375359 | b4 | 14 | 0.2 % | 46.9 % | e4 | 68.6 % | 52.6 % | A00 Polish Opening |

#### `--jeton-fichier FICHIER`

*Défaut : `~/.lichess_token`*

Fichier contenant le jeton personnel, et rien d'autre.   
Si le fichier manque, le script s'arrête avant toute requête :

```bash
./ianalyze.py ma-partie.pgn --sans-questions --jeton-fichier ~/.jeton-test
```

```text
[01:11:54] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:11:54] Lecture du PGN local : ma-partie.pgn
Jeton absent : ~/.jeton-test introuvable.
```

#### `--seuil-parties N`

*Défaut : `50`*

Arrêt quand la position compte moins de N parties dans la base.   
Avec le seuil par défaut, 50, la Polonaise s'arrête au troisième demi-coup dans la base des maîtres :

```bash
./ianalyze.py polonaise.pgn --sans-questions --base maitres
```

```text
Arrêt de l'interrogation : échantillon insuffisant au demi-coup 3 : 12 parties pour un seuil de 50.
```

Pour un seuil plus exigeant :

```bash
./ianalyze.py ma-partie.pgn --sans-questions --seuil-parties 200
```

#### `--seuil-frequence P`

*Défaut : `10.0`*

Un coup joué dans moins de P % des parties de la position est rare.   
Un coup rare qui mène hors du catalogue des ouvertures est une sortie de théorie. S'il reste dans une ligne nommée, ce n'en est pas une.

0 désactive le critère.

```bash
./ianalyze.py polonaise.pgn --sans-questions --coups-min 0
```

```text
Arrêt de l'interrogation : sortie de théorie au demi-coup 2 : g6 joué à 4.9 %, seuil 10.0 %, hors catalogue.
```

Avec 0, plus aucun coup n'est une sortie de théorie :

```bash
./ianalyze.py polonaise.pgn --sans-questions --coups-min 0 --seuil-frequence 0
```

```text
Arrêt de l'interrogation : fin de la partie.
```

#### `--coups-min N`

*Défaut : `6`*

Aucun arrêt sur la fréquence avant la fin du coup N, soit 2N demi-coups.   
La table couvre ainsi le début de partie même après une sortie précoce.

Le seuil de parties reste actif, et la première sortie est notée même dans la fenêtre. 0 arrête dès la première sortie.

Avec la valeur par défaut, la table de la Polonaise va jusqu'au bout de la partie, bien que 1... g6 soit une sortie de théorie : voir `--base`, plus haut.   
Avec 0, elle s'arrête sur ce coup :

```bash
./ianalyze.py polonaise.pgn --sans-questions --coups-min 0
```

```text
Arrêt de l'interrogation : sortie de théorie au demi-coup 2 : g6 joué à 4.9 %, seuil 10.0 %, hors catalogue.
```

#### `--jusqu-a-epuisement`

Ignore les deux seuils pour l'arrêt : l'interrogation descend tant que la base connaît la position.   
La première sortie reste notée.

```bash
./ianalyze.py polonaise.pgn --sans-questions --jusqu-a-epuisement
```

```text
Arrêt de l'interrogation : fin de la partie.
```

#### `--max-demicoups N`

*Défaut : `60`*

Plafond de demi-coups interrogés, garde-fou toujours actif.

```bash
./ianalyze.py ma-partie.pgn --sans-questions --jusqu-a-epuisement --max-demicoups 4
```

```text
Arrêt de l'interrogation : plafond de 4 demi-coups atteint (option --max-demicoups).
```

#### `--pause S`

*Défaut : `2.0`*

Pause entre deux requêtes à l'explorateur, 2 secondes au minimum.   
Avec une pause de 3 secondes, visible à l'heure de chaque ligne :

```bash
./ianalyze.py ma-partie.pgn --sans-questions --pause 3 --max-demicoups 3
```

```text
[21:05:20] Explorateur : demi-coup 1 (e4)
[21:05:20] Explorateur : demi-coup 2 (e5)
[21:05:23] Explorateur : demi-coup 3 (Nf3)
```

#### `--sans-explorateur`

Saute la collecte explorateur : ni réseau vers l'explorateur, ni jeton, ni catalogue requis.   
Le journal passe alors de la lecture de la partie au moteur, sans ligne "Explorateur" :

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions
```

```text
[01:08:11] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:08:11] Lecture du PGN local : ma-partie.pgn
[01:08:11] Questions de démarrage sautées : option --sans-questions.
[01:08:11] Dossier de travail : analyse-ma-partie-20261121-010811
[01:08:11] Stockfish : évaluation de 9 demi-coups, profondeur 18, multipv 3, threads 4. C'est la phase la plus longue.
[01:08:11] Stockfish : demi-coup 1/9 (e4)
...
```

### Moteur

L'évaluation Stockfish fait partie de toute collecte : le binaire est vérifié avant toute écriture.

#### `--coups-stockfish N`

*Défaut : `0`*

Limite le moteur aux N premiers coups entiers, soit 2N demi-coups. 0 analyse toute la partie.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --coups-stockfish 3
```

```text
...
[01:09:58] Stockfish : évaluation de 6 demi-coups, profondeur 18, multipv 3, threads 4. C'est la phase la plus longue.
...
```

#### `--profondeur D`

*Défaut : `18`*

Profondeur de recherche par position, de 1 à 60.   
Le temps de calcul croît très vite avec elle : au delà de 60, une seule position occuperait le moteur des heures !

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --profondeur 12
```

```text
...
[01:10:05] Stockfish : évaluation de 9 demi-coups, profondeur 12, multipv 3, threads 4. C'est la phase la plus longue.
...
```

#### `--multipv K`

*Défaut : `3`*

Nombre de meilleurs coups que le moteur donne pour chaque position.   
Avec 3, la synthèse montre, en face de chaque coup de la partie, les trois coups que Stockfish préférait.

Si le coup joué n'en fait pas partie, le script le fait évaluer à part, pour mesurer ce qu'il perd.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --multipv 5
```

```text
...
[01:10:06] Stockfish : évaluation de 9 demi-coups, profondeur 18, multipv 5, threads 4. C'est la phase la plus longue.
...
```

#### `--fils N`

*Défaut : le nombre de processeurs de la machine*

Nombre de processeurs que Stockfish emploie en même temps. Baissez-le pour garder la machine disponible pendant le calcul.

#### `--hachage MO`

*Défaut : `256`*

Mémoire que Stockfish réserve à ses calculs, en mégaoctets. La valeur par défaut convient à l'usage courant.

Les deux ensemble.   
Le journal nomme le nombre de fils, "threads", pas la taille de la table :

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --fils 2 --hachage 128
```

```text
...
[01:10:24] Stockfish : évaluation de 9 demi-coups, profondeur 18, multipv 3, threads 2. C'est la phase la plus longue.
...
```

Ces trois réglages, MultiPV, Threads et Hash pour Stockfish, sont expliqués dans [TECHNIQUE.md](TECHNIQUE.md), section 9.

#### `--stockfish CHEMIN`

*Défaut : `/usr/games/stockfish` sous Debian, le binaire trouvé dans le PATH sous macOS*

Binaire du moteur.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --stockfish /usr/games/stockfish
```

Le journal est le même qu'à la section [Collecte sans rien saisir](#collecte-sans-rien-saisir).

Un chemin qui ne mène à rien arrête le script avant la collecte :

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --stockfish /nulle/part
```

```text
[01:11:53] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:11:53] Lecture du PGN local : ma-partie.pgn
Stockfish introuvable : /nulle/part. Installez-le (apt install stockfish, dans /usr/games), ou indiquez son chemin avec --stockfish. L'évaluation du moteur fait partie de toute collecte.
```

#### `--longueur-pv N`

*Défaut : `5`*

Demi-coups de variante principale reproduits dans la synthèse, 0 pour la variante entière.

Les variantes complètes restent dans `stockfish/evaluations.json`.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --longueur-pv 2 --garder-dossier
```

Dans `synthese.md`, les variantes sont alors coupées à deux demi-coups :

```text
### 3 bis. Variantes principales du moteur

Variantes tronquées à 2 demi-coups ; les variantes complètes sont dans `stockfish/evaluations.json`.

- Demi-coup 1, Blancs jouent e4 (position avant le coup)
    - 1er (+0.39) : 1. d4 Nf6
    - 2e, joué (+0.37) : 1. e4 c5
    - 3e (+0.29) : 1. Nf3 d5
...
```

### Vérificateur

Les options qui suivent sont celles de `verifier-analyse.py`.

#### `ARCHIVE PGN`

L'archive écrite par `ianalyze.py`, zip ou dossier décompressé, puis le PGN annoté rendu par le LLM.   
Un tiret à la place du PGN signale que le LLM n'en a rendu aucun.

Le dossier peut aussi être celui qui contient la collecte, s'il n'en contient qu'une complète : le bilan la nomme.   
Voir [Vérifier la réponse du LLM](#vérifier-la-réponse-du-llm) pour un bilan complet.

#### `--nom NOM`

Nom du modèle essayé, repris en tête du bilan.

```bash
./verifier-analyse.py analyse-ma-partie-20261121-010838.zip analyse-fautive.pgn --nom "Modèle essayé"
```

```text
Contrôle d'une analyse rendue par un LLM
  modèle  : Modèle essayé
  archive : analyse-ma-partie-20261121-010838.zip
  PGN     : analyse-fautive.pgn
...
```

#### `--synthese FICHIER`

La conversation du LLM, copiée dans un fichier texte.   
Les positions et les évaluations qu'elle cite sont alors contrôlées aussi, dans deux sections de plus.

```bash
./verifier-analyse.py analyse-ma-partie-20261121-010838.zip analyse-llm.pgn --synthese conversation.txt
```

```text
Contrôle d'une analyse rendue par un LLM
  archive : analyse-ma-partie-20261121-010838.zip
  PGN     : analyse-llm.pgn
...
=== 7. Conversation : positions citées, langue ===
  OK        aucun tiret cadratin dans la conversation (0 relevé(s))
  OK        2 FEN citée(s), deux demandées
  OK        toutes les FEN sont des positions valides
  OK        toutes viennent d'une position de la partie

=== 8. Évaluations citées dans la conversation ===
  INFO      2 évaluation(s) citée(s)
  OK        toutes se retrouvent dans les données du moteur (0 introuvable(s))

=== Bilan ===
  échecs     : 0
  attentions : 0
```

Sans PGN rendu, seule la conversation est contrôlée :

```bash
./verifier-analyse.py analyse-ma-partie-20261121-010838.zip - --synthese conversation.txt
```

```text
Contrôle d'une analyse rendue par un LLM
  archive : analyse-ma-partie-20261121-010838.zip
  PGN     : -

=== 1. Lecture du PGN ===
  ECHEC     aucun PGN rendu : les contrôles 2 à 6 sont sans objet

=== 7. Conversation : positions citées, langue ===
  OK        aucun tiret cadratin dans la conversation (0 relevé(s))
  OK        2 FEN citée(s), deux demandées
  OK        toutes les FEN sont des positions valides
  OK        toutes viennent d'une position de la partie

=== 8. Évaluations citées dans la conversation ===
  INFO      2 évaluation(s) citée(s)
  OK        toutes se retrouvent dans les données du moteur (0 introuvable(s))

=== Bilan ===
  échecs     : 1
  attentions : 0
```

#### `--prompt-seul`, pour le vérificateur

Le PGN répond au prompt court de `ianalyze.py --prompt-seul`.   
Ce prompt demande moins que le prompt complet : les contrôles qu'il ne fonde pas sont sautés.

L'archive est ici le dossier gardé par `--prompt-seul --garder-dossier`.

```bash
./verifier-analyse.py analyse-ma-partie-20261121-010931 analyse-courte.pgn --prompt-seul
```

```text
Contrôle d'une analyse rendue par un LLM
  archive : analyse-ma-partie-20261121-010931
  PGN     : analyse-courte.pgn
  prompt  : court (--prompt-seul), contrôles réduits à ce qu'il demande

=== 1. Lecture du PGN ===
  OK        fichier en UTF-8
  OK        aucun coup illégal, variantes comprises (0 erreur(s) de lecture)

=== 2. Ligne principale ===
  OK        ligne principale identique à la partie d'origine (9 demi-coups)

=== 3. Format ===
  OK        aucune accolade dans un commentaire
  OK        les balises obligatoires de la partie d'origine, dans le même ordre
  OK        valeurs des sept balises reprises de la partie d'origine
  OK        marqueur de fin "*" identique à la balise Result "*"

=== 4. Coups commentés ===
  INFO      3 coup(s) commenté(s) sur 9
  INFO      0 coup(s) porteur(s) d'un NAG
  OK        les 0 erreur(s) et gaffe(s) de Stockfish sont toutes commentées (0 oubliée(s))

=== 5. Évaluations citées dans le PGN ===
  INFO      0 évaluation(s) citée(s)
  OK        toutes se retrouvent dans les données du moteur (0 introuvable(s))

=== 6. Variantes ===
  INFO      0 variante(s) jouable(s) sur la ligne principale

=== Bilan ===
  échecs     : 0
  attentions : 0
```

#### `--perimetre N`

Le périmètre convenu avec le LLM, en coups.   
Les erreurs et gaffes jouées après le coup N ne sont pas attendues dans le PGN : le prompt limite les commentaires au périmètre.

Sans cette option, le périmètre est celui de votre réponse à la question de démarrage, lu dans l'archive.   
Elle sert quand il a été fixé dans la conversation.

```bash
./verifier-analyse.py analyse-ma-partie-20261121-010838.zip analyse-llm.pgn --perimetre 3
```

```text
...
=== 4. Coups commentés ===
  OK        résumé de la partie avant le coup 1 (3 ligne(s), 6 à 10 demandées)
  INFO      3 coup(s) commenté(s) sur 9, 15 à 25 visés sur une partie complète
  INFO      0 coup(s) porteur(s) d'un NAG
  INFO      périmètre convenu : les 3 premiers coups, les erreurs et gaffes jouées au-delà ne sont pas attendues
  OK        les 0 erreur(s) et gaffe(s) de Stockfish sont toutes commentées (0 oubliée(s))
...
```

## MESSAGES D'ERREUR

Un message d'erreur n'est pas horodaté : c'est la dernière ligne, et le code de retour vaut 1 ou 2.

### Fichier introuvable

```bash
./ianalyze.py partie-absente.pgn
```

```text
[01:11:51] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
Fichier PGN introuvable : partie-absente.pgn
```

### Partie notée en français

Les coups doivent être notés en anglais : K, Q, R, B, N.

```bash
./ianalyze.py francais.pgn --sans-explorateur --sans-questions
```

```text
[01:11:52] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:11:52] Lecture du PGN local : francais.pgn
PGN corrompu : "Cf3", ligne 1, n'est ni un coup en notation anglaise (K, Q, R, B, N) ni un autre élément de PGN. Une partie notée en français ou en figurines doit être convertie, un texte libre placé entre accolades.
```

### Résultat répété en fin de fichier

Ce n'est pas une erreur : l'export de chess-mail.com écrit le résultat deux fois, et le second est ignoré. Le journal le signale, la collecte se poursuit.

```bash
./ianalyze.py partie-chess-mail.pgn --sans-explorateur --sans-questions
```

```text
[17:04:02] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[17:04:03] Lecture du PGN local : partie-chess-mail.pgn
[17:04:03] Résultat répété en fin de fichier, après la partie : ignoré.
[17:04:03] Questions de démarrage sautées : option --sans-questions.
...
analyse-partie-chess-mail-20261121-170403.zip
```

### Plusieurs parties dans le fichier

```bash
./ianalyze.py deux-parties.pgn --sans-explorateur --sans-questions
```

```text
[01:11:52] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:11:52] Lecture du PGN local : deux-parties.pgn
Le PGN contient 2 parties : isolez celle à analyser dans un fichier à part.
```

### Partie qui part d'une position

```bash
./ianalyze.py position.pgn --sans-explorateur --sans-questions
```

```text
[01:11:52] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:11:52] Lecture du PGN local : position.pgn
La partie ne commence pas à la position initiale, elle part d'une balise FEN. IAnalyze analyse une partie entière, du premier coup au dernier : pour étudier une position, chargez-la dans un échiquier d'analyse.
```

### Commentaire jamais fermé

```bash
./ianalyze.py accolade.pgn --sans-explorateur --sans-questions
```

```text
[01:11:52] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:11:53] Lecture du PGN local : accolade.pgn
PGN corrompu : le commentaire ouvert par une accolade à la ligne 1 n'est jamais fermé.
```

### Option inconnue

Ici une option retirée depuis la version 4.0.0 : Le code de retour vaut 2.

```bash
./ianalyze.py ma-partie.pgn --sans-stockfish
```

```text
usage: ianalyze.py [-h] [--installer-venv] [--venv CHEMIN] [--sans-questions]
...
ianalyze.py: error: unrecognized arguments: --sans-stockfish
```

### Valeur refusée

Le code de retour vaut 2.

```bash
./ianalyze.py ma-partie.pgn --pause 1
```

```text
usage: ianalyze.py [-h] [--installer-venv] [--venv CHEMIN] [--sans-questions]
...
ianalyze.py: error: --pause ne doit pas descendre sous 2 secondes
```

### Valeur hors des bornes du moteur

Les bornes sont celles que le moteur annonce : elles changent d'une version de Stockfish à l'autre.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --multipv 9999
```

```text
[01:11:53] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:11:53] Lecture du PGN local : ma-partie.pgn
--multipv : 9999 est hors des bornes du moteur /usr/games/stockfish, qui admet de 1 à 500 pour MultiPV.
```

### Moteur introuvable

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --stockfish /nulle/part
```

```text
[01:11:53] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:11:53] Lecture du PGN local : ma-partie.pgn
Stockfish introuvable : /nulle/part. Installez-le (apt install stockfish, dans /usr/games), ou indiquez son chemin avec --stockfish. L'évaluation du moteur fait partie de toute collecte.
```

### Jeton absent

Sans `--sans-explorateur`  le script a besoin du jeton Lichess (README, section 2).

```bash
./ianalyze.py ma-partie.pgn --sans-questions
```

```text
[01:11:54] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:11:54] Lecture du PGN local : ma-partie.pgn
Jeton absent : ~/.lichess_token introuvable.
```

### Catalogue absent

Le jeton est en place, mais le catalogue des ouvertures n'a pas été installé.

```bash
./ianalyze.py ma-partie.pgn --sans-questions
```

```text
[01:11:54] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
[01:11:54] Lecture du PGN local : ma-partie.pgn
Catalogue des ouvertures absent : ~/.local/share/IAnalyze/catalogue.tsv introuvable.

Installez-le en une commande :
    ~/IAnalyze/ianalyze.py --installer-catalogue
```

### Modèle de prompt fautif

Le modèle désigné par `--prompt` porte ici une valeur mal écrite.

```bash
./ianalyze.py ma-partie.pgn --sans-explorateur --sans-questions --prompt ~/modele-fautif.txt
```

```text
[01:11:55] Environnement virtuel : relance via ~/.local/share/IAnalyze/venv/bin/python3
Modèle de prompt ~/modele-fautif.txt, ligne 21 : valeur inconnue {{VERSON}}, valeurs admises : VERSION, DEPOT, ARCHIVE, PSEUDOS, CAMP, NIVEAU, CADENCE, ANNOTATEUR, BASE, SEUIL_IMPRECISION, SEUIL_ERREUR, SEUIL_GAFFE, PROFONDEUR, MULTIPV, PARTIE_PGN, TABLEAU_MOTEUR, ALERTE_RESULTAT, CONSIGNES_JOUEUR, OUVERTURE, DEMI_COUPS, DEMI_COUPS_EVALUES, COUPS_FAIBLES_JOUEUR
```

### Fichier qui n'est pas un fichier de réglages

`--purge-reglages` ne supprime pas le fichier qu'une faute de frappe lui désignerait :   
Le code de retour vaut 1.

```bash
./ianalyze.py --purge-reglages --reglages ma-partie.pgn
```

```text
--purge-reglages : ma-partie.pgn n'est pas un fichier de réglages, il ne porte pas la section [joueur]. Rien n'est supprimé.
```

### Dossier à plusieurs collectes, pour le vérificateur

Le répertoire courant contient ici deux dossiers de collecte complets :   
Le code de retour vaut 2.

```bash
./verifier-analyse.py . analyse-llm.pgn
```

```text
Lecture impossible : . contient 2 collectes complètes : analyse-ma-partie-20261121-010931, analyse-ma-partie-20261121-011502. Donnez le dossier de celle que le LLM a reçue.
```

### Archive introuvable, pour le vérificateur

Le code de retour vaut 2.

```bash
./verifier-analyse.py archive-absente.zip analyse-llm.pgn
```

```text
Lecture impossible : [Errno 2] No such file or directory: 'archive-absente.zip'
```

## CODES DE RETOUR

`ianalyze.py` :

| Code | Signification |
|---|---|
| 0 | succès |
| 1 | erreur signalée par un message, dont une valeur que le moteur n'admet pas, ou erreur inattendue |
| 2 | option inconnue, ou valeur refusée avant toute lecture de la partie |
| 130 | interruption (Ctrl-C) |

`verifier-analyse.py` :

| Code | Signification |
|---|---|
| 0 | aucun `ECHEC` dans le bilan |
| 1 | au moins un `ECHEC` |
| 2 | un fichier ne peut pas être lu, ou l'archive n'est pas celle d'IAnalyze : aucun contrôle n'a eu lieu |

## FICHIERS

Ce que le script lit :

| Fichier | Rôle |
|---|---|
| `~/.local/share/IAnalyze/venv` | l'environnement virtuel, où vit python-chess |
| `~/.local/share/IAnalyze/catalogue.tsv` | le catalogue des ouvertures |
| `~/.config/IAnalyze/reglages.ini` | vos réglages : pseudos, cadence habituelle, niveau |
| `~/.lichess_token` | votre jeton Lichess, en mode 600 |
| `prompt-modele.txt`, `prompt-seul-modele.txt` | les modèles de prompt, à côté du script |
| `/usr/games/stockfish` | le moteur sous Debian. Sous macOS, celui du PATH |

Ce qu'il écrit, dans le répertoire courant ou dans celui de `--sortie` :

| Fichier | Rôle |
|---|---|
| `analyse-<partie>-<date>.zip` | l'archive, à joindre à la conversation |
| `analyse-<partie>-<date>.prompt.txt` | le prompt, à coller dans la conversation |
| `analyse-<partie>-<date>/` | le dossier de travail, gardé seulement avec `--garder-dossier` ou après un échec |

Le contenu de l'archive est décrit dans le README, section 5.

Le fichier de réglages, tel que le script l'écrit après la première collecte :

```ini
# Réglages de ianalyze.py.
# Vous pouvez modifier ce fichier à la main. Une clef supprimée
# sera redemandée au prochain lancement sur un terminal.

[joueur]
# Vos noms de joueur, séparés par des virgules. Ils sont cherchés,
# sans tenir compte de la casse, dans les balises White et Black
# pour déduire votre camp. L'option --pseudos les remplace le temps
# d'un lancement.
pseudos = MonPseudo
# Votre cadence habituelle, proposée quand la balise TimeControl
# d'une partie ne la donne pas. Formes admises :
#   15+10                 temps réel, minutes puis incrément en
#                         secondes
#   14 jours              correspondance, délai fixe par coup
#   10 coups en 50 jours  correspondance, coups par période
#   5 jours + 36 heures   correspondance, capital de départ puis
#                         incrément par coup, en heures ou en
#                         jours ; ajoutez au besoin ", plafond 20
#                         jours" et ", réserve 50 jours"
#   inconnue
cadence = 15+10
# Votre niveau, en points Elo approximatifs, ou inconnu. Il est
# transmis à l'analyste, qui y adapte ses explications. Sans lui,
# c'est l'Elo de votre balise dans la partie qui sert.
niveau = 1300
```

## VOIR AUSSI

- [README.md](README.md) : l'installation, l'usage courant, le choix du LLM
- [TECHNIQUE.md](TECHNIQUE.md) : le fonctionnement du script, le format des fichiers
- [TESTS.md](TESTS.md) : la suite de tests, test par test
- [CHANGELOG.md](CHANGELOG.md) : l'historique des versions
- `./ianalyze.py --help` : le résumé des options, dans le terminal
