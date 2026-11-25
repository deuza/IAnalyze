# IAnalyze, les tests

Tous les tests sont joués par un seul script, `test-app.sh`, sous Debian comme sous macOS.

Ce document dit comment le lancer, puis ce que vérifie chaque test. Le détail, commande par commande, est dans le script, qui fait foi.

Le [README](README.md) explique l'installation et l'usage courant, [EXAMPLES.md](EXAMPLES.md) les commandes et leurs sorties, [TECHNICAL.md](TECHNICAL.md) le fonctionnement.

## Sommaire

- [1. Lancer les tests](#1-lancer-les-tests)
- [2. Ce que les tests ne touchent pas](#2-ce-que-les-tests-ne-touchent-pas)
- [3. Ce qu'il faut pour les jouer](#3-ce-quil-faut-pour-les-jouer)
- [4. Variables facultatives](#4-variables-facultatives)
- [5. Tests hors réseau](#5-tests-hors-réseau)
- [6. Tests avec `--reseau`](#6-tests-avec---reseau)
- [7. La partie d'essai](#7-la-partie-dessai)
- [8. Le seul test à jouer à la main](#8-le-seul-test-à-jouer-à-la-main)

---

## 1. Lancer les tests

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
Rapport : /chemin/du/depot/test-report-Linux-20261120-002933.txt
```

Le rapport reprend l'environnement (système, Python, python-chess, Stockfish), le résultat de chaque contrôle et les extraits utiles au diagnostic. Vous pouvez le transmettre tel quel.

Le nombre de contrôles dépend de la version et du mode choisi. Sous macOS, un contrôle de T44 est toujours sauté : il crée un fichier au nom non UTF-8, ce que son système de fichiers refuse.

## 2. Ce que les tests ne touchent pas

- **Vos réglages et votre catalogue** : les tests désignent les leurs, dans un répertoire temporaire supprimé à la fin.
- **Le dépôt** : rien n'y est écrit, sauf le rapport.
- **Votre jeton** : il n'est ni affiché, ni copié, ni passé dans une ligne de commande. Le script vérifie au contraire qu'il n'apparaît ni dans les archives qu'il contrôle ni dans le rapport.

Avec `--reseau`, comptez environ 70 requêtes à l'explorateur de Lichess, espacées de 2 secondes, 10 fichiers du catalogue et, si vous donnez une partie, 2 exports de cette partie.

## 3. Ce qu'il faut pour les jouer

- l'environnement virtuel, installé par `--installer-venv`
- Stockfish, obligatoire : chaque collecte l'emploie. Sans lui, le script s'arrête au départ
- avec `--reseau` seulement, votre jeton dans `~/.lichess_token`

Les tests qui ne portent pas sur le moteur le règlent au plus court, `--profondeur 1`.

## 4. Variables facultatives

| Variable | Rôle | Défaut |
|---|---|---|
| `VENV` | environnement virtuel de python-chess | `local/venv` du dépôt |
| `STOCKFISH` | moteur employé par les tests | celui du PATH, sinon `/opt/homebrew/bin`, `/usr/local/bin` ou `/usr/games` |
| `JETON` | fichier du jeton | `~/.lichess_token` |
| `GARDER` | `1` conserve le répertoire temporaire | supprimé |

```bash
GARDER=1 ./test-app.sh
```

## 5. Tests hors réseau

Les numéros suivent l'ordre de création des tests, pas celui de leur passage. Un numéro absent est celui d'un test retiré. M1 et M2 sont deux collectes complètes, moteur seul.

| Test | Sujet | Ce qui est vérifié |
|---|---|---|
| T01 | Compilation | `ianalyze.py` passe `py_compile` |
| T02 | Aide | `--help` rend 0, cite les options attendues et place les défauts de `--venv` et `--catalogue` dans le dossier `local/` de l'application, et celui de `--reglages` à sa racine |
| T03 | Options refusées | une option inconnue ou une valeur refusée arrêtent le script avec le code 2 |
| T04 | PGN introuvable | le fichier absent est nommé, et un nom relatif est pris pour un fichier, non pour un identifiant |
| T05 | Collecte minimale | l'archive existe et porte `synthese.md` et `collecte.json`, sans fichier provisoire |
| T06 | Dossier gardé | `--garder-dossier` laisse le dossier de travail à côté de l'archive |
| T08 | Répertoire de sortie | `--sortie` reçoit l'archive, et le répertoire est créé au besoin |
| T25 | Moteur limité | `--coups-stockfish` borne l'analyse aux premiers coups, la synthèse et les deux prompts le disent |
| T26 | Moteur introuvable | un binaire absent arrête le script avec un message et la commande d'installation |
| T27 | Jeton absent | le fichier de jeton manquant est signalé avant toute requête |
| T31 | Plateforme, `brew` | la commande `brew install` est proposée sous macOS, jamais sous Linux |
| T32 | Plateforme, `apt` | la commande `apt install` est proposée sous Linux, jamais sous macOS |
| T34 | Latin-1 | un PGN en latin-1 est lu, un encodage non reconnu est refusé sans rien écrire |
| T35 | cp1252 | un PGN en cp1252 est lu, apostrophe courbe, tiret et euro compris |
| T36 | Marque UTF-8 | la marque d'ordre des octets en tête de PGN est retirée |
| T37 | UTF-16 | un PGN en UTF-16 est lu, avec ou sans marque d'ordre |
| T38 | UTF-8 abîmé | les octets invalides sont remplacés, le reste du PGN est conservé |
| T39 | Octets NUL | ils sont retirés, aucun ne reste dans l'archive |
| T40 | Fins de ligne CRLF | un PGN venu de Windows est lu comme les autres |
| T41 | Locale C | le script tourne sous une locale ASCII, les accents de sa sortie y deviennent des `?` |
| T42 | Caractères de contrôle | ceux d'une balise sont retirés, une tabulation devient une espace |
| T43 | Jeton factice | marque d'ordre retirée, jeton non ASCII refusé, jeton jamais affiché |
| T44 | Noms de fichiers | un nom à deux-points ou point d'interrogation, ou non UTF-8, donne un dossier assaini |
| T45 | Saisie en latin-1 | une réponse tapée en latin-1 dans un terminal est décodée sans erreur |
| T46 | PGN sain | un PGN en UTF-8 ne produit ni avertissement ni remarque |
| T47 | Version | la version a la forme X.Y.Z et figure dans l'en-tête d'agent |
| T48 | Point dans le nom | un PGN dont le nom porte un point donne une archive bien nommée |
| T49 | Explorateur simulé | des réponses inattendues sont signalées sans erreur inattendue |
| T50 | Valeurs non finies | `nan` et `inf` sont refusés pour les options numériques, sans dossier créé |
| T51 | Mats | mat manqué et mat concédé notés `mat` et gaffe, mat compté après le coup, légende de la synthèse |
| T52 | Coup nul | le coup `--` garde sa ligne au tableau, sans évaluation inventée, et le prompt court l'explique |
| T53 | Interruption | une interruption pendant l'archivage, ou une écriture qui échoue, garde le dossier de travail et ne laisse pas d'archive tronquée |
| T54 | Fausses adresses | une URL qui n'est pas une partie est refusée sans rien envoyer, les identifiants sont extraits des vraies |
| T55 | Options du moteur | une valeur hors des bornes est refusée avec ses bornes, `--stockfish` admet un tilde ou un nom cherché dans le PATH |
| T56 | Coup nul, explorateur | l'interrogation s'arrête au coup nul, sur un explorateur simulé |
| T57 | Premier lancement | les réglages sont demandés puis enregistrés, répertoire compris |
| T58 | Second lancement | les réglages sont relus, et `--pseudos` les emporte |
| T59 | Hors terminal | rien n'est demandé ni écrit. Sur un terminal sans pseudo, le nom du joueur est demandé |
| T60 | Réglages mal formés | le fichier illisible est signalé, les clefs ajoutées à la main sont conservées |
| T61 | Pseudo | aucun pseudo n'est écrit en dur dans le script ni dans son aide |
| T62 | Cadence | les réponses sont vérifiées, les fausses refusées |
| T63 | Correspondance | les trois systèmes de cadence par correspondance sont reconnus |
| T64 | Prompt écrit | le prompt est écrit à côté de l'archive, avec ses valeurs remplies |
| T65 | Prompt adapté | le prompt ne garde que les passages qui s'appliquent : explorateur, base, réponses, section 2 |
| T66 | Modèle fautif | repère inconnu, condition jamais fermée ou modèle absent arrêtent le script avant la collecte |
| T67 | Script sans modèle | le script copié seul fait sa collecte sans prompt, et le dit |
| T68 | Niveau | le niveau en points Elo est vérifié et repris dans le prompt |
| T69 | Purge des réglages | fichier supprimé, fichier absent admis, répertoire et fichier étranger refusés |
| T70 | Partie d'essai | `test.pgn` est lu en entier : commentaires, variantes, prise en passant, promotion, roques, coup nul |
| T71 | Options retirées | `--sans-stockfish`, `--avec-stockfish` et `--consignes` sont inconnues |
| T72 | Résultat contraire | une partie notée gagnée dans une position perdue est signalée dans la synthèse et le prompt |
| T73 | Vérificateur | un PGN conforme passe, un PGN fautif voit chaque défaut relevé, PGN absent, archive illisible |
| T74 | Prompt seul | prompt court écrit sans archive, tableau du moteur, bilan selon le nombre de coups faibles, camp inconnu, prompt jamais écrasé |
| T75 | PGN lus de travers | les PGN que python-chess lirait de travers, ou à plusieurs parties, sont refusés avec leur cause, sans rien écrire. Un résultat répété en fin de fichier est ignoré, sauf s'il est suivi d'une vraie partie |
| T76 | Jeton et serveurs | sur des serveurs simulés, une redirection n'est pas suivie et le jeton est expurgé des réponses citées |
| T77 | Entrées inattendues | entrée standard fermée, nom trop long, URL mal formée, partie qui part d'une FEN, tilde de `--sortie` : un message, plus une erreur inattendue |
| T78 | Moteur qui s'arrête | un moteur mort hors d'une recherche donne un message et le code 1 |
| T79 | Réponses refusées | une réponse trop longue ou porteuse de signes du PGN est refusée et redemandée |
| T80 | Nom long | un nom de PGN long, en caractères de plusieurs octets, donne une étiquette bornée et valide |
| T81 | Cas combinés | la purge s'emploie seule, un modèle vide est refusé, un jeton mal écrit est refusé sans être affiché |
| T82 | Vérificateur, suite | mats cités, périmètre convenu, contrôles sautés du mode court, dossier parent à une ou plusieurs collectes |
| T83 | Parties d'exemples | les fichiers de `example-games` restent ce qu'`EXAMPLES.md` en dit : huit parties acceptées, dont les exports de quatre sites et d'un logiciel, quatre refusées avec leur cause, deux PGN annotés contrôlés, aucune adresse ni identifiant de partie réelle |
| T84 | Environnement virtuel incomplet | un environnement sans pip est reconnu, un répertoire sans `pyvenv.cfg` ne l'est jamais ; avec `--reseau`, `--installer-venv` reconstruit le premier et y installe python-chess |
| T85 | `--venv` qui n'est pas un environnement virtuel | un répertoire non vide sans `pyvenv.cfg`, avec ou sans interpréteur, est refusé par `--installer-venv` avant tout pip, et rien n'y est ajouté ; un répertoire absent ou vide ne l'est pas |
| M1 | Collecte, noms | nom de PGN accentué, chemin de sortie avec espace et accent |
| M2 | Collecte complète | l'italienne analysée en entier, moteur seul, sans processus du moteur laissé derrière |

## 6. Tests avec `--reseau`

Ces tests emploient votre jeton et le vrai explorateur. N1 et N2 sont deux collectes complètes.

| Test | Sujet | Ce qui est vérifié |
|---|---|---|
| T09 | Catalogue installé | les cinq fichiers sont téléchargés, le message d'installation est écrit |
| T10 | Catalogue, format | l'index porte son en-tête, aucun fichier temporaire ne reste |
| T11 | Réinstallation | une seconde installation donne un catalogue identique |
| T12 | Catalogue absent | il est signalé, avec la commande d'installation |
| T13 | Catalogue tronqué | il est signalé plutôt que lu à moitié |
| T14 | Italienne, maîtres | la table de l'explorateur et la sortie de théorie sur la base des maîtres |
| T15 | Polonaise, maîtres | une ouverture rare sur la base des maîtres |
| T16 | Polonaise, Lichess | la même sur la base de tous les joueurs : fenêtre de départ, première sortie, dernière position nommée |
| T17 | Première sortie | l'interrogation s'arrête à la première sortie de théorie quand on le demande |
| T18 | Filtres | les filtres de cadence et de classement sont transmis et écrits dans la synthèse |
| T19 | Seuil de parties | un seuil inatteignable donne un échantillon insuffisant dès le premier demi-coup, noté en section 4 |
| T20 | Seuil de fréquence | un seuil à zéro ne déclare aucune sortie |
| T21 | Épuisement | `--jusqu-a-epuisement` est annoncé, et la première sortie de théorie reste la même |
| T22 | Plafond | `--max-demicoups` borne l'interrogation |
| T23 | Pause | le délai entre deux requêtes est respecté |
| T24 | Partie téléchargée | la partie que vous désignez est téléchargée par son adresse et par son identifiant |
| T28 | Droits du jeton | un fichier de jeton lisible par d'autres est signalé |
| T29 | Jeton et archive | le jeton n'apparaît ni dans l'archive ni dans le journal |
| T33 | Roque | les deux roques figurent dans la table, aucun n'est donné hors base ni à 0.0 % |
| N1 | Coup nul | l'interrogation s'arrête au coup nul sur le vrai explorateur, sans requête refusée |
| N2 | Collecte complète | explorateur et moteur ensemble |

Les chiffres de l'explorateur changent chaque mois : ces tests vérifient des formes et des ordres de grandeur, pas des totaux exacts.

## 7. La partie d'essai

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

## 8. Le seul test à jouer à la main

Réinstaller l'environnement virtuel touche à votre installation : `test-app.sh` ne le fait pas.

```bash
./ianalyze.py --installer-venv
```

Attendu, sur un environnement déjà présent : "Environnement virtuel déjà présent", puis "Installation de python-chess dans l'environnement virtuel." et "Environnement virtuel opérationnel".
