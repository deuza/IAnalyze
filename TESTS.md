# IAnalyze : tests

Tous les tests sont joués par un seul script, `test-app.sh`, sous Debian comme sous macOS. Retour au [README](README.md).

Cette page dit comment le lancer et ce qu'il vérifie. Le détail de chaque test, commande par commande, est dans le script, qui fait foi.

## Lancer les tests

Depuis le dépôt, après l'installation décrite dans le README :

```bash
./test-app.sh
```

```bash
./test-app.sh --reseau
```

| Commande | Ce qu'elle joue | Durée |
|---|---|---|
| `./test-app.sh` | les tests hors réseau, sans jeton | une à deux minutes, davantage sur une petite machine |
| `./test-app.sh --reseau` | les mêmes, puis ceux qui demandent le réseau et votre jeton Lichess | quatre à six minutes de plus |

Le script se termine par un bilan :

```text
Réussis : 270, échecs : 0, sautés : 0
Rapport : /chemin/du/depot/rapport-tests-Linux-20261120-002933.txt
```

Le rapport reprend l'environnement (système, Python, python-chess, Stockfish), le résultat de chaque contrôle et les extraits utiles au diagnostic. Vous pouvez le transmettre tel quel.

## Ce que les tests ne touchent pas

- **Vos réglages et votre catalogue** : les tests désignent les leurs, dans un répertoire temporaire supprimé à la fin.
- **Le dépôt** : rien n'y est écrit, sauf le rapport.
- **Votre jeton** : il n'est ni affiché, ni copié, ni passé dans une ligne de commande. Le script vérifie au contraire qu'il n'apparaît dans aucune archive ni dans le rapport.

Avec `--reseau`, comptez environ 70 requêtes à l'explorateur de Lichess, espacées de 2 secondes, 2 exports de partie et 10 fichiers du catalogue.

## Ce qu'il faut pour les jouer

- l'environnement virtuel, installé par `--installer-venv`
- Stockfish, obligatoire : chaque collecte l'emploie
- avec `--reseau` seulement, votre jeton dans `~/.lichess_token`

Les tests qui ne portent pas sur le moteur le règlent au plus court, `--profondeur 1`.

## Variables facultatives

| Variable | Rôle | Défaut |
|---|---|---|
| `VENV` | environnement virtuel de python-chess | `~/.local/share/IAnalyze/venv` |
| `STOCKFISH` | moteur employé par les tests du moteur | celui du script |
| `JETON` | fichier du jeton | `~/.lichess_token` |
| `PARTIE` | identifiant Lichess téléchargé par T24 | `xvoiNy2C` |
| `GARDER` | `1` conserve le répertoire temporaire | supprimé |

```bash
GARDER=1 ./test-app.sh
```

## Tests hors réseau

| Famille | Tests | Ce qui est vérifié |
|---|---|---|
| Ligne de commande | T01 à T04, T50, T71 | compilation, aide, options refusées avec le code 2, fichier introuvable, valeurs `nan` et `inf`, options retirées |
| Plateforme | T31, T32 | commandes `apt` ou `brew` proposées selon le système, emplacements par défaut |
| Archive | T05 à T08, T48, T53, M1 | contenu du zip, dossier gardé, consignes, répertoire de sortie, noms à point ou accentués, interruption pendant l'archivage |
| Encodages | T34 à T47 | latin-1, cp1252, UTF-16, UTF-8 abîmé, octets NUL, fins de ligne, caractères de contrôle, locale C, noms de fichiers |
| Jeton | T27, T43 | fichier absent, marque d'ordre des octets, jeton non ASCII refusé, jeton jamais affiché |
| URL | T54 | adresses qui ne sont pas des parties, refusées sans rien envoyer |
| Explorateur simulé | T49, T56 | réponses inattendues, arrêt au coup nul |
| Réglages | T57 à T63, T68, T69 | premier lancement, priorité de `--pseudos`, fichier mal formé, cadence et niveau vérifiés, correspondance, purge |
| Prompt | T64 à T67 | écrit à côté de l'archive, passages gardés ou retirés, modèle fautif refusé, script copié sans son modèle |
| Moteur | T25, T26, T51, T52, T55, M2 | moteur introuvable, analyse limitée aux premiers coups, mat manqué, coup nul, options hors bornes, analyse complète |
| Partie d'essai | T70 | `test.pgn` : commentaires, variantes, prise en passant, promotion, roques, coup nul |

## Tests avec `--reseau`

| Famille | Tests | Ce qui est vérifié |
|---|---|---|
| Catalogue | T09 à T13 | téléchargement, réinstallation identique, catalogue absent ou tronqué |
| Explorateur | T14 à T23, T33 | base maîtres, base Lichess, filtres, seuils, modes d'arrêt, pause entre deux requêtes, roque retrouvé dans la base |
| Jeton | T28, T29 | fichier lisible par d'autres signalé, jeton absent de l'archive et du journal |
| Source Lichess | T24 | partie téléchargée par URL et par identifiant |
| Coup nul | N1 | arrêt sur le vrai explorateur, sans requête refusée |
| Collecte complète | N2 | explorateur et moteur ensemble |

Les chiffres de l'explorateur changent chaque mois : ces tests vérifient des formes et des ordres de grandeur, pas des totaux exacts.

## La partie d'essai

`test.pgn` réunit dans une seule partie légale ce qui a déjà fait trébucher un lecteur de PGN :

- balises accentuées
- commentaire d'avant le premier coup, commentaire de fin de ligne introduit par un point-virgule
- NAG, signes `??` et `?`, commentaires d'horloge `[%clk]`
- variantes emboîtées
- mat manqué, prise en passant, promotion avec prise et échec, les deux roques, un coup nul

La partie n'a aucun intérêt échiquéen. Elle sert aussi à un essai complet, à la main :

```bash
./collecte-partie.py test.pgn --sans-questions
```

## Le seul test à jouer à la main

Réinstaller l'environnement virtuel touche à votre installation : `test-app.sh` ne le fait pas.

```bash
./collecte-partie.py --installer-venv
```

Attendu, sur un environnement déjà présent : "Environnement virtuel déjà présent", puis "Installation de python-chess dans l'environnement virtuel." et "Environnement virtuel opérationnel".

## Où les tests ont été joués

Version 4.0.0, le 19 novembre 2026, après une installation neuve sur chaque machine :

| | Debian 13 Trixie, Raspberry Pi | macOS 27.3, Apple Silicon |
|---|---|---|
| Python | 3.13.5 | 3.15.2 |
| python-chess | 1.11.2 | 1.11.2 |
| Stockfish | 17.1 | 19 |
| `./test-app.sh` | 235 réussis | 234 réussis, 1 sauté |
| `./test-app.sh --reseau` | 318 réussis | 317 réussis, 1 sauté |

Le test sauté sous macOS crée un fichier au nom non UTF-8, ce que son système de fichiers refuse.
