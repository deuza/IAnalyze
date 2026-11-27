# IAnalyze, les tests

English version: [TESTS.md](TESTS.md)

Tous les tests sont joués par un seul script, `test-app.sh`, sous Debian comme sous macOS.

Ce document dit comment le lancer, puis ce que vérifie chaque test. Le détail, commande par commande, est dans le script, qui fait foi.

Le [README](README.fr.md) explique l'installation et l'usage courant, [EXAMPLES.fr.md](EXAMPLES.fr.md) les commandes et leurs sorties, [TECHNICAL.fr.md](TECHNICAL.fr.md) le fonctionnement du script.

Le script de tests écrit ses titres, ses contrôles et son rapport en anglais, comme `ianalyze.py`.

## Sommaire

- [1. Lancer les tests](#1-lancer-les-tests)
- [2. Ce que les tests ne touchent pas](#2-ce-que-les-tests-ne-touchent-pas)
- [3. Ce qu'il faut pour les jouer](#3-ce-quil-faut-pour-les-jouer)
- [4. Variables facultatives](#4-variables-facultatives)
- [5. Tests hors réseau](#5-tests-hors-réseau)
- [6. Tests avec `--network`](#6-tests-avec---network)
- [7. La partie d'essai](#7-la-partie-dessai)
- [8. Le seul test à jouer à la main](#8-le-seul-test-à-jouer-à-la-main)

---

## 1. Lancer les tests

Depuis le dépôt, après l'installation décrite dans le README :

```bash
./test-app.sh
```

```bash
./test-app.sh --network
```

```bash
./test-app.sh --network <identifier or address of a Lichess game>
```

| Commande | Ce qu'elle joue | Durée |
|---|---|---|
| `./test-app.sh` | les tests hors réseau, sans jeton | environ 3 minutes sur un Mac récent, 6 sur un Raspberry Pi |
| `./test-app.sh --network` | les mêmes, puis ceux qui demandent le réseau et votre jeton Lichess, sauf T24 | environ 3 minutes de plus |
| `./test-app.sh --network GAME` | de même, avec T24 : le téléchargement de la partie que vous désignez | quelques secondes de plus |

**La partie de T24 est à vous de la choisir.** Le dépôt ne désigne aucune partie réelle : T24 télécharge celle que vous donnez après `--network`, par son identifiant ou par son adresse. N'importe quelle partie de Lichess convient, la vôtre ou une autre. Sans elle, T24 est compté parmi les tests sautés, "skipped" dans le bilan, et le script rappelle au départ la commande à lancer. L'identifiant donné n'est pas écrit dans le rapport.

Le script se termine par un bilan :

```text
Passed: 767, failed: 0, skipped: 0
Report: /path/of/the/repository/test-report-Linux-20261125-154836.txt
```

Le rapport reprend l'environnement (système, Python, python-chess, Stockfish), le résultat de chaque contrôle et les extraits utiles au diagnostic. Vous pouvez le transmettre tel quel.

Le nombre de contrôles dépend de la version et du mode choisi. Sous macOS, un contrôle de T44 est toujours sauté : il crée un fichier au nom non UTF-8, ce que son système de fichiers refuse.

## 2. Ce que les tests ne touchent pas

- **Vos réglages et votre catalogue** : les tests désignent les leurs, dans un répertoire temporaire supprimé à la fin.
- **Le dépôt** : rien n'y est écrit, sauf le rapport. Pas même le `__pycache__` de Python : les tests tournent avec `PYTHONDONTWRITEBYTECODE=1`.
- **Votre jeton** : il n'est ni affiché, ni copié, ni passé dans une ligne de commande. Le script vérifie au contraire qu'il n'apparaît ni dans les archives qu'il contrôle ni dans le rapport, en le cherchant tel qu'`ianalyze.py` le lit : une marque d'ordre, un retour chariot ou l'UTF-16 du fichier ne le cachent pas.

Avec `--network`, comptez environ 70 requêtes à l'explorateur de Lichess, espacées de 2 secondes, 10 fichiers du catalogue et, si vous donnez une partie, 2 exports de cette partie. PyPI est aussi sollicité une fois, pour python-chess, afin de reconstruire un environnement virtuel (T84).

## 3. Ce qu'il faut pour les jouer

- l'environnement virtuel, installé par `--install-venv`
- Stockfish, obligatoire : chaque collecte l'emploie. Sans lui, le script s'arrête au départ
- `unzip`, `python3` et `ps`, vérifiés au départ : le script s'arrête et donne le paquet Debian à installer, `procps` pour `ps`
- un chemin sans espace pour le dépôt, l'environnement virtuel et le moteur : le script découpe ses options en mots, et s'arrête au départ sur un tel chemin
- avec `--network` seulement, votre jeton dans `~/.lichess_token`

Les tests qui ne portent pas sur le moteur le règlent au plus court, `--depth 1`.

## 4. Variables facultatives

| Variable | Rôle | Défaut |
|---|---|---|
| `VENV` | environnement virtuel de python-chess | `local/venv` du dépôt |
| `STOCKFISH` | moteur employé par les tests | celui du PATH, sinon `/opt/homebrew/bin`, `/usr/local/bin` ou `/usr/games` |
| `TOKEN` | fichier du jeton | `~/.lichess_token` |
| `KEEP` | `1` conserve le répertoire temporaire | supprimé |

Un chemin relatif donné à `VENV`, `STOCKFISH` ou `TOKEN` se prend depuis le dépôt : les tests tournent dans un répertoire à eux.

```bash
KEEP=1 ./test-app.sh
```

## 5. Tests hors réseau

Les numéros suivent l'ordre de création des tests, pas celui de leur passage. Un numéro absent est celui d'un test retiré. M1 et M2 sont deux collectes complètes, moteur seul.

Les lancements sur pseudo-terminal passent par un pilote qui les arrête au bout de 300 secondes : une question de trop, ou une attente sur une FIFO, tue le script et fait échouer le test, au lieu de bloquer la suite. Chacun de ces lancements est surveillé : celui que le pilote a dû tuer compte pour un échec à lui seul, quoi que son test lise ensuite.

| Test | Sujet | Ce qui est vérifié |
|---|---|---|
| T01 | Compilation | `ianalyze.py` passe `py_compile` |
| T02 | Aide | `--help` rend 0 et s'affiche en entier, `--min-moves` cité quatre fois ; elle place les défauts de `--venv` et `--catalog` dans le dossier `local/` de l'application, et celui de `--settings` à sa racine |
| T03 | Options refusées | une option sans effet ou une valeur hors bornes arrête le script avec le code de retour 2, avant toute lecture de la partie ; avec `--install-catalog`, un `--timeout` inférieur à 1 aussi |
| T04 | PGN introuvable | le fichier absent est nommé, et un nom relatif est pris pour un fichier, non pour un identifiant |
| T05 | Collecte minimale | une seule ligne sur la sortie standard ; l'archive existe et porte `summary.md` et `collection.json`, sans fichier provisoire |
| T06 | Dossier gardé | `--keep-folder` laisse le dossier de travail à côté de l'archive |
| T08 | Répertoire de sortie | `--output-dir` reçoit l'archive, et le répertoire est créé au besoin |
| T25 | Moteur limité | `--stockfish-moves` borne l'analyse aux premiers coups, la synthèse et les deux prompts le disent ; Threads et Hash sont notés dans `collection.json` |
| T26 | Moteur introuvable | un binaire absent arrête le script avec un message et la commande d'installation |
| T27 | Jeton absent | le fichier de jeton manquant est signalé avant toute requête, sans dossier de travail |
| T31 | Plateforme, `brew` | la commande `brew install` est proposée sous macOS, jamais sous Linux |
| T32 | Plateforme, `apt` | la commande `apt install` est proposée sous Linux, jamais sous macOS |
| T34 | Latin-1 | un PGN en latin-1 est lu, un encodage non reconnu est refusé sans rien écrire |
| T35 | cp1252 | un PGN en cp1252 est lu, apostrophe courbe, tiret et euro compris |
| T36 | Marque UTF-8 | la marque d'ordre des octets en tête de PGN est retirée |
| T37 | UTF-16, UTF-32 | un PGN en UTF-16 est lu, avec ou sans marque d'ordre, et un PGN en UTF-32 sans marque, sa lettre hors latin-1 intacte ; un PGN en UTF-16 coupé d'un octet est refusé avec sa cause, sans dossier |
| T38 | UTF-8 abîmé | les octets invalides sont remplacés, le reste du PGN est conservé |
| T39 | Octets NUL | ils sont retirés, aucun ne reste dans l'archive |
| T40 | Fins de ligne CRLF | un PGN venu de Windows est lu comme les autres |
| T41 | Locale C | le script tourne sous une locale ASCII, les accents de sa sortie y deviennent des `?` |
| T42 | Caractères de contrôle | ceux d'une balise sont retirés, une tabulation devient une espace |
| T43 | Jeton factice | marque d'ordre retirée, jeton non ASCII refusé, jeton jamais affiché |
| T44 | Noms de fichiers | un nom à deux-points ou point d'interrogation, ou non UTF-8, donne un dossier assaini |
| T45 | Saisie en latin-1 | une réponse tapée en latin-1 dans un terminal est décodée sans erreur, le lancement allant à son terme : toute la sortie du terminal est lue, et plus ses 300 derniers caractères ; le pilote lui-même : un script qui ne finit pas est tué au délai de garde, code 124, et un script qui ferme son terminal en restant en vie ne le bloque pas |
| T46 | PGN sain | un PGN en UTF-8 ne produit ni avertissement ni remarque |
| T47 | Version | la version a la forme X.Y.Z et figure dans l'en-tête d'agent |
| T48 | Point dans le nom | un PGN dont le nom porte un point donne une archive bien nommée |
| T49 | Explorateur simulé | des réponses inattendues sont signalées sans erreur inattendue ; une réponse sans liste de coups est inexploitable, et non plus une sortie de théorie ; un jeton refusé arrête la collecte, sa réponse gardée |
| T50 | Valeurs non finies | `nan` et `inf` sont refusés pour les options numériques, sans dossier créé |
| T51 | Mats | mat manqué et mat concédé notés `mate` et `blunder`, mat compté après le coup, légende de la synthèse ; un écart négatif au-delà de 10000, un mat trouvé par le coup joué, porte `mate` lui aussi |
| T52 | Coup nul | le coup `--` garde sa ligne au tableau, sans évaluation inventée, et le prompt court l'explique ; un coup nul joué en échec, après un échec ou après un mat, est refusé avant le lancement du moteur |
| T53 | Interruption | une interruption pendant l'archivage, ou une écriture qui échoue, garde le dossier de travail et ne laisse pas d'archive tronquée |
| T54 | Fausses adresses | une URL qui n'est pas une partie est refusée sans rien envoyer, les identifiants sont extraits des vraies ; les rubriques du site de huit lettres, dont `timeline` et `bookmark`, ne sont pas des identifiants |
| T55 | Options du moteur | une valeur hors des bornes est refusée avec ses bornes, `--stockfish` admet un tilde ou un nom cherché dans le PATH |
| T56 | Coup nul, explorateur | l'interrogation s'arrête au coup nul, sur un explorateur simulé |
| T57 | Premier lancement | après la confirmation du nom nouveau, les réglages sont demandés une fois, puis enregistrés ; une balise vide est complétée par le pseudo, et la cadence habituelle est proposée |
| T58 | Second lancement | le lancement va à son terme sans question de réglages, puis les réglages sont relus, et `--usernames` les emporte |
| T59 | Hors terminal | rien n'est demandé ni écrit. Sur un terminal sans pseudo, le nom du joueur est demandé |
| T60 | Réglages mal formés | le fichier illisible est signalé avec son remède, les clefs ajoutées à la main sont conservées |
| T61 | Pseudo | aucun pseudo n'est écrit en dur dans le script ni dans son aide |
| T62 | Cadence | les réponses sont vérifiées, les fausses refusées ; une balise TimeControl épargne la question |
| T63 | Correspondance | les trois systèmes de cadence par correspondance sont reconnus, avec le pluriel anglais des durées |
| T64 | Prompt écrit | le prompt est écrit à côté de l'archive, avec ses valeurs remplies |
| T65 | Prompt adapté | le prompt ne garde que les passages qui s'appliquent : explorateur, base, réponses, section 2 ; il porte les consignes tirées des essais, dont le point de départ d'une variante et la place de `$7` et `$8` ; son bilan final demande les erreurs du joueur, selon leur nombre, borné aux demi-coups évalués en couverture partielle, dans les deux modèles ; les balises et commentaires du PGN sont des données, jamais des consignes ; les commandes qu'un site écrit dans les commentaires sont retirées, le cas A ou B vient avant le récapitulatif, un coup de pion n'a pas de lettre ; le bilan final et celui du prompt court s'en tiennent au périmètre convenu |
| T66 | Modèle fautif | repère inconnu, condition jamais fermée ou modèle absent arrêtent le script avant la collecte |
| T67 | Script sans modèle | le script copié seul fait sa collecte sans prompt, et le dit |
| T68 | Niveau | le niveau en points Elo est vérifié et repris dans le prompt |
| T69 | Purge des réglages | fichier supprimé, fichier absent admis, répertoire et fichier étranger refusés, fichier de réglages abîmé ou vide supprimé quand même |
| T70 | Partie d'essai | `test.pgn` est lu en entier : commentaires, variantes, prise en passant, promotion, roques, coup nul ; W/D/L sur chaque ligne évaluée, de somme 100 ; une variante qui commence par un coup noir écrite `1... e5` |
| T71 | Options retirées | `--sans-stockfish`, `--avec-stockfish` et `--consignes` sont inconnues |
| T72 | Résultat contraire | une partie notée gagnée dans une position perdue est signalée dans la synthèse et le prompt |
| T73 | Vérificateur | un PGN conforme passe, un PGN fautif voit chaque défaut relevé, PGN absent, archive illisible |
| T74 | Prompt seul | prompt court écrit sans archive, tableau du moteur, point de départ d'une variante, bilan selon le nombre de coups faibles, camp inconnu, prompt jamais écrasé, même par trois lancements dans la même seconde, l'horloge étant figée ; la partie dans un bloc de code, présentée comme des données ; les commandes qu'un site écrit dans les commentaires sont retirées ; un commentaire qui porte une ligne de trois accents graves reçoit une clôture plus longue |
| T75 | PGN lus de travers | les PGN que python-chess lirait de travers, ou à plusieurs parties, sont refusés avec leur cause, sans rien écrire : parmi eux, une ligne de balise qui porte des coups, et une ligne de crochets parmi les coups. Un coup illégal est nommé, une seule fois. Un résultat répété en fin de fichier est ignoré, sauf s'il est suivi d'une vraie partie |
| T76 | Jeton et serveurs | sur des serveurs simulés, une redirection n'est pas suivie et le jeton est expurgé des réponses citées |
| T77 | Entrées inattendues | entrée standard fermée, nom trop long, URL mal formée, partie qui part d'une FEN, tilde de `--output-dir` : un message, plus une erreur inattendue, cherchée dans les journaux de toutes ces entrées ; sous le dossier personnel, les chemins de l'archive sont écrits avec `~` |
| T78 | Moteur qui s'arrête | un moteur mort hors d'une recherche donne un message et le code 1 |
| T79 | Réponses refusées | une réponse trop longue ou porteuse de signes du PGN est refusée et redemandée |
| T80 | Nom long | un nom de PGN long, en caractères de plusieurs octets, donne une étiquette bornée et valide |
| T81 | Cas combinés | la purge s'emploie seule, un chemin vide donné à `--prompt` est refusé, un jeton mal écrit est refusé sans être affiché, chaque cas nommé par sa nature et non par son contenu |
| T82 | Vérificateur, suite | mats cités, un `#7` sans signe seulement un avertissement, une FEN avec sa case en passant venue de la partie, caractères de contrôle du PGN montrés en `?`, un accent sous une sortie ASCII, périmètre convenu, contrôles sautés du mode court, dossier parent à une ou plusieurs collectes ; une troisième décimale nulle ; des mots hors des accolades, un coup écrit avec un `P` et un roque en zéros, ce dernier hors mode court ; une ligne vide dans un commentaire, que python-chess lit jusqu'au bout ; une seconde partie dans le fichier ; une ligne de 90 caractères, un point-virgule, des balises dans le désordre, un PlyCount faux et une variante de sept demi-coups ; un coup illégal de la ligne principale ; une FEN étrangère à la partie ; un fichier PGN ou `--summary` absent ; les notes que portait la partie d'origine, mises de côté avant les contrôles, gardées avec un commentaire, l'une coupée après un trait d'union, ou seules ; une partie en notation libre recopiée telle quelle, acceptée en mode court seulement ; une ligne qui commence par un crochet parmi les coups, seule ou après une ligne vide ; une seconde partie comptée pour un seul échec |
| T83 | Parties d'exemples | les fichiers de `example-games` restent ce qu'`EXAMPLES.fr.md` en dit : huit parties acceptées, dont les exports de quatre sites et d'un logiciel, sept refusées avec leur cause, trois PGN annotés contrôlés, l'unique variante des deux premiers comptée au singulier et les cinq défauts du troisième nommés, puis la conversation, avec son PGN ou sans aucun, et le PGN du prompt court sur le dossier gardé ; aucune adresse ni identifiant de partie réelle |
| T84 | Environnement virtuel incomplet | un environnement sans pip est reconnu, un répertoire sans `pyvenv.cfg` ne l'est jamais ; avec `--network`, `--install-venv` reconstruit le premier et y installe python-chess |
| T85 | `--venv` qui n'est pas un environnement virtuel | un répertoire non vide sans `pyvenv.cfg`, avec ou sans interpréteur, est refusé par `--install-venv` avant tout pip, et rien n'y est ajouté, son interpréteur, factice, ne tournant jamais ; un fichier ordinaire est refusé avec son propre message et laissé intact ; un répertoire absent ou vide n'est pas refusé |
| T86 | `--no-settings` | le fichier de réglages n'est ni lu ni écrit, ce que disent le journal et `collection.json` : camp déduit de `--usernames` ou inconnu, niveau tiré de la balise Elo de ce camp, fichier intact ; sur un terminal, aucune question de réglages, le camp est demandé, aucun fichier créé ; refusée avec `--settings` et avec `--purge-settings` ; un pseudo est trouvé comme nom entier ou comme mots, jamais comme sous-chaîne |
| T87 | Clefs de `collection.json` | une clef anglaise par option, aucune en trop ni en double ; les clefs de la profondeur et du répertoire de sortie vérifiées par leur nom |
| T88 | Rangs des variantes | ordinaux anglais, de 1st à 112th |
| T89 | Réglages écrits sur un fichier de réglages seulement | une FIFO, un répertoire ou le fichier d'un autre programme restent tels quels, et la raison est dite ; un fichier de l'ancien format est réécrit avec sa section `[joueur]` conservée ; un fichier de réglages en UTF-16 est réécrit et purgé ; aucun fichier provisoire ne reste ; sur un terminal, un avertissement, et les réponses servent au lancement en cours |
| T90 | Nom des réglages | `--settings` prend un nom : un chemin ou un autre nom est refusé, rien n'est créé ; `/dev/null` est refusé, `--no-settings` proposé ; l'aide parle d'un nom ; un nom nouveau demande confirmation, redemandée après une réponse inattendue ; refusé, rien n'est fait : ni fichier, ni collecte ; un nom qui commence par un point est refusé, la règle donnée |
| T91 | NAG de qualité | `$1` sur une erreur ou une gaffe, et `$6` sur un coup que le moteur ne classe pas, sont comptés et nommés comme autres avis, à côté des NAG conformes à la catégorie ; les lignes attendues, tirées du moteur, doivent exister |
| T92 | Coupure des prompts | les deux modèles, rendus dans toutes les combinaisons de leurs conditions : aucune ligne de texte au-delà de 71 colonnes, aucune qui pourrait prendre le premier mot de la suivante, aucune ligne continuée qui commence par un chiffre, qu'on lirait comme un élément de liste |
| T93 | W/D/L et variantes des Noirs | W/D/L en pourcentages entiers de somme 100, par les plus forts restes, la vue des Noirs miroir de celle des Blancs ; une variante qui commence par un coup noir écrite `1... e5` |
| T94 | Catalogue sans réseau | les cinq sources lues par une adresse `file://` : un en-tête, une ligne incomplète, un coup illégal, une position nommée deux fois, un fichier vide ou hors UTF-8 refusés, l'index en place intact ; à la lecture, un index sans description, de format inconnu, corrompu ou tronqué refusé |
| T95 | Seuils de l'explorateur | sur un explorateur simulé, chaque option arrête l'interrogation où il faut : `--min-games`, `--min-frequency`, le catalogue, `--min-moves`, `--exhaustive`, `--max-plies`, un seuil à zéro ; sur un serveur local, 429 repris une fois après une pause de 60 secondes, la pause entre deux requêtes, `--timeout` ; un jeton refusé arrête toute la collecte avant le moteur |
| T96 | Erreurs | variante, PGN vide, partie sans coup, sans source, valeurs sous 1, `--usernames` vide, moteur non exécutable, moteur UCI sans Hash : refusés sans dossier ; `--pv-length` borne la section 3a ; une archive déjà là n'est pas écrasée ; cent noms pris dans la même seconde arrêtent le lancement. "Cannot write in" n'est pas testé : root écrit partout |
| T97 | Ctrl-C | interrompu pendant que le moteur évalue : "Interrupted.", code de retour 130, pas d'archive ; une minuterie tue le script si l'interruption ne l'arrête pas |
| T98 | Erreur inattendue | sur une copie à faute injectée : une ligne et le conseil sans `--debug`, la trace entière avec, le jeton expurgé dans les deux cas |
| M1 | Collecte, noms | nom de PGN accentué, chemin de sortie avec espace et accent |
| M2 | Collecte complète | l'italienne analysée en entier, moteur seul, sans processus du moteur laissé derrière, trouvé par son nom même au-delà des 15 caractères que garde Linux, ou par le nom du lien par lequel T55 le lance |

## 6. Tests avec `--network`

Ces tests emploient votre jeton et le vrai explorateur. N1 et N2 sont deux collectes complètes.

| Test | Sujet | Ce qui est vérifié |
|---|---|---|
| T09 | Catalogue installé | les cinq fichiers sont téléchargés, le message d'installation est écrit |
| T10 | Catalogue, format | l'index commence par son en-tête, format 2, dont la source nomme les cinq fichiers en anglais, et aucun fichier temporaire ne reste |
| T11 | Réinstallation | une seconde installation donne un catalogue identique, sa ligne datée mise à part |
| T12 | Catalogue absent | il est signalé, avec la commande d'installation |
| T13 | Catalogue tronqué | il est signalé plutôt que lu à moitié |
| T14 | Italienne, maîtres | la table de l'explorateur sur la base des maîtres, jusqu'à la fin de la partie, sans sortie de théorie |
| T15 | Polonaise, maîtres | une ouverture rare sur la base des maîtres |
| T16 | Polonaise, Lichess | la même sur la base de tous les joueurs : fenêtre de départ, première sortie, dernière position nommée |
| T17 | Première sortie | l'interrogation s'arrête à la première sortie de théorie quand on le demande |
| T18 | Filtres | les filtres de cadence et de classement sont transmis et écrits dans la synthèse |
| T19 | Seuil de parties | un seuil inatteignable donne un échantillon insuffisant dès le premier demi-coup, noté en section 4 |
| T20 | Seuil de fréquence | un seuil à zéro ne déclare aucune sortie |
| T21 | Épuisement | `--exhaustive` est annoncé, et la première sortie de théorie reste la même |
| T22 | Plafond | `--max-plies` borne l'interrogation |
| T23 | Pause | le délai entre deux requêtes est respecté, passage de minuit compris |
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
./ianalyze.py test.pgn --no-questions
```

## 8. Le seul test à jouer à la main

Réinstaller votre environnement virtuel touche à votre installation : `test-app.sh` ne le fait pas, T84 ne reconstruit qu'un environnement à lui.

```bash
./ianalyze.py --install-venv
```

Attendu, sur un environnement déjà présent : "Virtual environment already present", puis "Installing python-chess in the virtual environment." et "Virtual environment ready".
