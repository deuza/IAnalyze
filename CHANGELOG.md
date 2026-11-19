# Changelog

Toutes les modifications notables de collecte-partie.py sont consignées
dans ce fichier.

Le format suit [Tenez un Changelog](https://keepachangelog.com/fr/1.1.0/)
et le projet applique le [versionnage sémantique](https://semver.org/).

## [Unreleased]

### Changed

- Le modèle du prompt s'appelle `prompt-modele.txt` et non plus
  `INSTRUCTIONS.txt` : le fichier n'est plus un texte à coller tel quel
  mais ce dont le script tire le prompt de chaque partie. Un modèle
  personnel passé par `--prompt` n'est pas concerné.
- En-tête du prompt : "Prompt produit par IAnalyze vX.Y.Z", suivi de
  l'adresse du dépôt, que porte la nouvelle valeur `{{DEPOT}}` du
  modèle.
- Le prompt ne suppose plus que l'analyste dispose d'un bac à sable. Il
  admet le seul fichier `synthese.md`, joint ou collé, quand l'archive
  ne peut pas être ouverte, et distingue deux cas : l'analyste qui
  exécute du code construit et vérifie le PGN avec python-chess, celui
  qui n'en exécute pas l'écrit lui-même, l'annonce, et n'invente ni
  résultat d'exécution ni évaluation chiffrée.

## [3.6.0] - 2026-11-19

### Added

- Prompt d'analyse écrit à côté de l'archive, sous le nom
  `<archive>.prompt.txt`, à coller dans la conversation avec l'archive
  en pièce jointe. Il est tiré d'un modèle, `INSTRUCTIONS.txt`, rangé à
  côté du script et modifiable sans toucher au code : le script y
  remplit les valeurs (pseudo, camp, niveau, cadence, nom de l'archive)
  et ne garde que les passages qui s'appliquent (base interrogée,
  moteur présent ou non, réponses recueillies ou non). Le prompt décrit
  ainsi toujours la synthèse que cette version vient d'écrire.
- Repères du modèle : `{{NOM}}` pour une valeur, et les directives
  `#! si`, `#! si non`, `#! sinon`, `#! fin` et `#! note`. Le modèle est
  contrôlé avant la collecte ; un repère inconnu arrête le script en
  donnant le numéro de la ligne.
- Options `--prompt FICHIER`, pour un autre modèle, et `--sans-prompt`.
- Réglage `niveau`, en points Elo, demandé une seule fois comme le
  pseudo et la cadence ; réglage facultatif `annotateur`.
- Hors terminal, le camp du joueur se déduit de ses pseudos pour le
  prompt, sans poser de question.
- `collecte.json` : clef `prompt_ecrit`.
- README.nfo : la chaîne complète en présentation, et la section 9,
  prompt d'analyse.
- TESTS.nfo : section V, tests T64 à T68.
- Fichier de réglages de l'utilisateur,
  `~/.config/collecte-partie/reglages.ini`, au format INI : il garde vos
  pseudos et votre cadence habituelle. Les clefs absentes sont demandées
  une seule fois, au premier lancement sur un terminal ; hors terminal,
  rien n'est demandé ni écrit.
- Option `--reglages FICHIER`, pour désigner un autre fichier.
- Sans pseudo connu, le script demande votre nom de joueur quand votre
  balise est vide, comme il le fait pour l'adversaire.
- Cadence saisie par des questions vérifiées, et non plus en texte
  libre : temps réel, correspondance ou inconnue, puis les minutes par
  joueur et l'incrément en secondes. La correspondance connaît trois
  systèmes : un délai fixe en jours par coup (Lichess, chess.com) ; un
  nombre de coups par période, comme "10 coups en 50 jours" (cadence
  standard de l'ICCF) ; ou un capital de temps, jours au départ,
  incrément par coup en heures ou en jours, plafond et réserve
  facultatifs (chess-mail.com, Triple Block de l'ICCF). Les deux
  derniers suivent les ICCF Rules en vigueur depuis le 1er janvier
  2026. Seuls des nombres entiers sont acceptés. Le script rédige
  lui-même la phrase
  transmise à l'analyste, avec la catégorie de Lichess (ultrabullet,
  bullet, blitz, rapide, classique), calculée comme le fait Lichess sur
  le temps initial plus quarante fois l'incrément.
- Une balise `TimeControl` de la forme `600+5` ou `300` est citée, puis
  traduite : "soit rapide, 10 minutes + 5 secondes par coup".
- TESTS.nfo : section U, tests T57 à T63.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.6.0`.
- `INSTRUCTIONS.txt` devient le modèle du prompt : son en-tête ne porte
  plus de pseudo, de niveau ni de cadence en dur, et il décrit les
  sorties apparues depuis la version 3.5.0, que l'analyste rencontrait
  sans explication : la mention `mat` de la colonne Écart, la ligne
  d'un coup nul, la ligne "Encodage" de la section 5, et la cadence
  rédigée par le script.
- README.nfo : le titre porte le nom du dépôt, IAnalyze ; les sections
  Jeton et Sources deviennent 10 et 11.
- `--pseudos` n'a plus de valeur par défaut dans le code : sans
  l'option, les pseudos viennent du fichier de réglages. Donnée, elle
  l'emporte toujours.
- La cadence proposée par la question de cadence de la partie est celle
  de vos réglages, "non précisée" à défaut. Dans le fichier de
  réglages, elle s'écrit `15+10`, `14 jours`, `10 coups en 50 jours`,
  `5 jours + 36 heures, plafond 20 jours, réserve 50 jours` ou
  `inconnue` ; une valeur d'une autre forme est redemandée.
- `collecte.json` enregistre les pseudos réellement utilisés.
- TESTS.nfo : T45 fournit son propre fichier de réglages, pour que les
  questions du premier lancement ne décalent pas ses réponses.
- TESTS.nfo : T33 rejoue le roque sur une partie générique, produite
  par le test ; l'état des vérifications par plateforme est mis à jour,
  et le refus du nom non UTF-8 sous macOS (T44) n'est plus une
  hypothèse.

### Removed

- Le pseudo et la cadence personnels de l'auteur, jusqu'ici valeurs par
  défaut du script, ainsi que la constante `PSEUDOS_DEFAUT`. Les
  exemples de l'aide et de la documentation emploient des pseudos
  neutres.

## [3.5.9] - 2026-11-19

### Added

- TESTS.nfo : test T56, le coup nul et l'explorateur, sur un
  explorateur simulé.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.5.9`.
- README.nfo, section 6 : le coup nul parmi les critères d'arrêt.

### Fixed

- Explorateur : un coup nul, `--` dans le PGN, ressortait dans la table
  à 0.0 %, au rang "-", et était désigné comme la première sortie de
  théorie. Dans la fenêtre de `--coups-min`, la collecte continuait et
  envoyait à Lichess une liste de coups contenant `0000`, refusée par un
  HTTP 400 ("illegal move 0000: illegal uci") : l'arrêt était alors
  attribué à une erreur HTTP. L'interrogation s'arrête désormais au
  coup nul, sans requête pour ce demi-coup, avec le motif "coup nul au
  demi-coup N" ; la section 4 de la synthèse le liste, et il ne compte
  plus comme une sortie de théorie. Le défaut existait déjà en 3.4.1 :
  la version 3.5.4 n'avait traité que le côté Stockfish.

## [3.5.8] - 2026-11-18

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.5.8`.
- Les guillemets chevrons du script sont remplacés par des guillemets
  droits : deux commentaires, et l'aide de `--consignes`, qui affiche
  désormais `sous le titre "Consignes d'analyse"`.

## [3.5.7] - 2026-11-18

### Added

- TESTS.nfo : test T55, les options moteur hors bornes.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.5.7`.
- `collecte-partie.py` est enregistré exécutable (mode 755) dans le
  dépôt.
- Le moteur est lancé une première fois, brièvement, pendant les
  vérifications préalables, puis une seconde fois pour l'analyse.
- README.nfo, section 5 : le contrôle des options moteur.

### Removed

- Constante `RE_ID_PARTIE`, inutilisée depuis que `RE_ID_SOURCE` l'a
  remplacée.

### Fixed

- Une valeur de `--fils`, `--hachage` ou `--multipv` hors des bornes du
  moteur, ou un moteur ne connaissant pas l'une de ces options, n'était
  refusée qu'à la configuration du moteur, après toute la phase
  explorateur, par le message "Le moteur a échoué en cours d'analyse".
  Ces options sont désormais contrôlées auprès du moteur pendant les
  vérifications préalables, avant toute requête et avant la création du
  dossier de travail.

## [3.5.6] - 2026-11-18

### Added

- TESTS.nfo : test T54, les URL qui ne sont pas des parties.
- Message d'arrêt propre aux URL refusées, qui rappelle la forme
  attendue.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.5.6`.
- README.nfo, section 3 : les formes d'URL acceptées.

### Fixed

- Une URL qui n'est pas celle d'une partie était quand même demandée à
  Lichess : `https://lichess.org/analysis/...` donnait l'identifiant
  "analysis", l'URL d'une étude celui de l'étude, et
  `https://example.com/abcdefgh` était acceptée quel que soit l'hôte.
  Il en résultait une requête inutile et un "Export PGN : HTTP 404".
  Une URL doit désormais viser `lichess.org` et porter l'identifiant en
  tête de chemin, ou derrière `/embed/game/`, `/embed/` ou
  `/game/export/`. Les rubriques `analysis`, `training`, `practice` et
  `streamer` ne passent plus pour des identifiants.

## [3.5.5] - 2026-11-18

### Added

- TESTS.nfo : test T53, interruption pendant l'archivage et écriture
  qui échoue en cours de route, sur un archivage simulé.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.5.5`.
- README.nfo, section 7 : ce qui reste sur le disque après un échec.

### Fixed

- Une interruption (Ctrl-C) ou un échec pendant la création du zip
  laissait une archive tronquée sous son nom définitif, que rien ne
  distinguait d'une archive valide. Le zip est désormais écrit sous un
  nom provisoire, `.<dossier>.partiel.zip`, vérifié, puis renommé ; en
  cas d'arrêt il est retiré, et le dossier de travail est conservé.
- Une écriture interrompue laissait un fichier tronqué, `synthese.md`
  ou `collecte.json` par exemple, dans le dossier de travail conservé.
  Chaque fichier de l'archive est désormais écrit dans un fichier
  voisin `.<nom>.partiel`, renommé une fois complet.

## [3.5.4] - 2026-11-18

### Added

- TESTS.nfo : test T52, le coup nul dans le tableau Stockfish.
- Synthèse, section 3 : une phrase explique la ligne d'un coup nul,
  quand la partie en contient un.
- `stockfish/evaluations.json` : clef `non_evalue` sur le coup joué
  quand c'est un coup nul.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.5.4`.
- README.nfo, section 7 : la ligne d'un coup nul.

### Fixed

- Stockfish : un coup nul, `--` dans le PGN, recevait une évaluation, un
  écart et parfois une nature ("+0.00", 55 cp, "imprécision") que le
  moteur n'avait jamais donnés, le protocole UCI ne sachant pas
  restreindre une recherche à ce coup. Sa ligne est gardée avec les
  meilleurs coups de la position, mais ses colonnes Éval, G/N/P, Écart
  et Nature portent désormais `-`. La suite de la partie est analysée
  comme avant.

## [3.5.3] - 2026-11-18

### Added

- TESTS.nfo : test T51, l'écart d'un mat manqué.
- Synthèse, section 3 : une phrase explique la mention `mat` de la
  colonne Écart cp.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.5.3`.
- README.nfo, section 7 : la mention `mat` de la colonne Écart.

### Fixed

- Tableau Stockfish : quand le coup joué manquait un mat, ou en
  concédait un, la colonne Écart cp affichait un nombre voisin de
  100000, 99729 par exemple. Ce nombre vient de la valeur
  bornée par laquelle le script remplace un mat pour classer les coups,
  non du moteur. La cellule porte désormais `mat`, comme le palmarès
  écrivait déjà "écart lié à un mat". `stockfish/evaluations.json`
  garde la valeur brute dans `ecart_cp`.

## [3.5.2] - 2026-11-18

### Added

- TESTS.nfo : tests T49, réponses inattendues de l'explorateur, sur un
  explorateur simulé, et T50, valeurs non finies.
- README.nfo, section 5 : `--pause` et `--seuil-frequence` refusent
  `nan` et `inf`.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.5.2`.

### Fixed

- Explorateur : une réponse JSON dont la clef `moves` n'est pas une
  liste, ou dont un compteur vaut l'infini (`1e999`), arrêtait le script
  sur une `TypeError` ou une `OverflowError`. Ces valeurs sont
  désormais ignorées, comme les autres écarts de schéma.
- `--pause nan` et `--pause inf` étaient acceptés puis arrêtaient la
  collecte sur une erreur inattendue à la première pause, dossier de
  travail déjà créé ; `--seuil-frequence nan` était accepté et
  neutralisait le critère de fréquence en silence. Ces valeurs sont
  refusées à la lecture des options, code 2.

## [3.5.1] - 2026-11-18

### Added

- TESTS.nfo : test T48, un point dans le nom du PGN.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.5.1`.

### Fixed

- Un PGN dont le nom contient un point, comme les exports de Lichess
  (`lichess_pgn_2026.11.18_A_vs_B.pgn`), faisait échouer l'archivage
  avec "Archive illisible, dossier conservé" et le code 1 : le script
  cherchait `analyse-lichess_pgn_2026.11.zip` alors que l'archive,
  valide, était écrite sous le nom complet du dossier. Le chemin de
  l'archive n'était pas affiché et le dossier de travail restait en
  place. Le contrôle des archives homonymes souffrait du même défaut.

## [3.5.0] - 2026-11-18

### Added

- Sortie console : la sortie standard et la sortie d'erreur sont
  reconfigurées avec `errors="replace"`. Un caractère que le terminal ne
  sait pas afficher devient `?` au lieu de provoquer une
  `UnicodeEncodeError`, par exemple avec `PYTHONIOENCODING=ascii`, ou
  sous `LC_ALL=C` avec `PYTHONUTF8=0`.
- Les caractères de contrôle sont retirés des lignes du journal et des
  messages d'arrêt avant affichage.
- Lecture du PGN et des consignes quel que soit leur encodage : marque
  d'ordre des octets (BOM) UTF-8, UTF-16 ou UTF-32, UTF-16 sans marque,
  UTF-8, puis repli sur cp1252 et sur latin-1. Une ligne "Attention" du
  journal nomme l'encodage retenu. Un fichier UTF-8 abîmé par quelques
  octets invalides reste lu en UTF-8, ces octets devenant U+FFFD.
- Les caractères de contrôle du PGN, NUL compris, sont retirés et
  comptés dans le journal ; les fins de ligne CRLF et CR sont ramenées à
  LF.
- collecte.json : clefs `pgn_encodage` et `pgn_remarques`. Si le PGN a
  dû être converti, la section 5 de la synthèse le signale.
- Fichier de jeton : même détection d'encodage que pour le PGN, marque
  d'ordre des octets et UTF-16 compris. Un jeton hors de l'ASCII
  imprimable est refusé avant toute requête, par un message qui ne le
  reproduit pas.
- Catalogue et réponses de l'explorateur : lecture en `utf-8-sig`, avec
  un traitement des erreurs explicite, sans dépendance à la locale.
- Écritures : tous les fichiers de l'archive passent par une seule
  fonction, en UTF-8, fins de ligne LF, sans dépendance à la locale.
- Nom du dossier de travail et chemins du zip : les caractères de
  contrôle, `/ \\ : * ? " < > |` et les octets non décodables du nom du
  PGN deviennent `_`, l'étiquette est bornée à 80 caractères. Espaces et
  lettres accentuées sont conservés.
- Le chemin de l'archive est écrit en octets sur la sortie standard, tel
  que le système de fichiers le connaît.
- Valeurs issues du PGN (noms des joueurs, Event, Site et toute autre
  balise) : tabulations et caractères de contrôle sont retirés avant
  l'écriture des en-têtes dans `synthese.md` et avant tout affichage.
- Questions de démarrage : une réponse saisie dans un autre encodage que
  celui du terminal est redécodée (cp1252, puis latin-1) et nettoyée de
  ses caractères de contrôle.
- Constante `VERSION`, d'où est tiré l'en-tête d'agent HTTP.
- TESTS.nfo : section L, tests T34 à T47, dont les fixtures sont
  produites par les tests eux-mêmes.
- README.nfo : section 8, encodages et caractères.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.5.0`.
- `partie.pgn` est toujours écrit en UTF-8, fins de ligne LF, sans
  marque d'ordre des octets ni caractère de contrôle : ce n'est plus,
  octet pour octet, le fichier fourni quand celui-ci s'en écartait.
- README.nfo : les sections Jeton et Sources deviennent 9 et 10.

### Fixed

- Un PGN en latin-1 ou en cp1252 était lu comme de l'UTF-8 : chaque
  lettre accentuée devenait U+FFFD dans `synthese.md` et dans
  `partie.pgn`, sans aucun avertissement.
- Un PGN en UTF-16 était refusé avec le message trompeur "PGN sans aucun
  coup dans la ligne principale".

- Un fichier de jeton enregistré avec une marque d'ordre des octets
  faisait échouer la première requête avec le diagnostic "réponse non
  JSON : 'latin-1' codec can't encode character '\ufeff'", et l'archive
  était produite sans explorateur.

- Un PGN au nom non décodable, en latin-1 sur un système UTF-8 par
  exemple, arrêtait la collecte sur une `UnicodeEncodeError` à
  l'écriture de `collecte.json`, dossier de travail laissé en place.

- NUL, ESC et autres caractères de contrôle des balises du PGN étaient
  recopiés tels quels dans `synthese.md`, et une balise `Variant`
  piégée envoyait ses séquences d'échappement au terminal.
- Une réponse aux questions de démarrage saisie en latin-1 arrêtait le
  script sur une `UnicodeEncodeError`, dossier de travail laissé en
  place.

## [3.4.1] - 2026-11-17

### Added

- TESTS.nfo : test T33, le roque dans l'explorateur.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.4.1`.
- TESTS.nfo : T12, T13 et T26 précisent que le fichier de jeton doit
  exister.

### Fixed

- Explorateur : un roque joué n'était pas retrouvé dans la réponse de la
  base, qui le note "roi prend tour" (`e1h1`, `e1a1`, `e8h8`, `e8a8`)
  alors que le script comparait avec `e1g1`, `e1c1`, `e8g8` et `e8c8`.
  Le roque ressortait à 0 partie, au rang "hors base", et déclenchait
  une fausse sortie de théorie, donc un arrêt prématuré de
  l'interrogation. Les deux notations sont désormais admises.

## [3.4.0] - 2026-11-17

### Added

- Prise en charge de macOS : les emplacements par défaut dépendent
  désormais de la plateforme.
  - `--venv` : `~/.local/share/collecte-partie/venv`.
  - `--catalogue` : `~/.local/share/collecte-partie`.
  - `--stockfish` : le binaire trouvé dans le PATH, avec repli sur
    `/opt/homebrew/bin/stockfish`.
- Sous macOS, les messages d'erreur et l'aide proposent `brew install`
  au lieu de `apt install`.
- README.nfo : paquets macOS et table des emplacements par plateforme.
- TESTS.nfo : variables `CAT` et `VENV` par plateforme, tests T31 et T32.
- CHANGELOG.md.

### Changed

- En-tête d'agent HTTP : `collecte-partie/3.4`.
- TESTS.nfo : commandes rendues portables (`head -n -10`, `shred`) et
  attendus de T03, T04, T14, T15 et T26 réalignés sur les défauts et les
  messages de la version 3.3.0.

Sous Debian, les défauts, les messages et la sortie de `--help` sont
inchangés.

## [3.3.0] - 2026-10-09

Historique reconstitué à partir des conversations des 8 et 9 octobre
2026. La numérotation des étapes intermédiaires n'a pas été conservée :
leurs changements sont regroupés ici, sous la version que porte l'en-tête
d'agent du script.

### Added

- `--base {lichess,maitres}` : interrogation de la base de l'ensemble des
  joueurs Lichess, celle de https://lichess.org/opening, en plus de la
  base maîtres.
- `--cadences` et `--classements` : filtres de la base Lichess, avec les
  défauts de https://lichess.org/opening et les parties depuis janvier
  2017.
- Catalogue local des ouvertures nommées de Lichess (domaine public,
  CC0) : `--installer-catalogue`, `--catalogue`, et colonne Ouverture
  dans la synthèse.
- `--coups-min` (défaut 6) : aucun arrêt sur la fréquence dans la fenêtre
  de départ, la première sortie de théorie restant notée.
- Questions de démarrage sur un terminal interactif : camp, adversaire,
  cadence et les quatre questions du projet d'analyse. Les réponses vont
  dans `contexte.md` et en tête de la synthèse.
- `--pseudos` pour déduire le camp des balises White et Black, et
  `--sans-questions`.
- `partie-origine.pgn` : le PGN fourni, conservé quand le script complète
  des en-têtes.
- Section 3 : colonnes Nature (imprécision, erreur, gaffe à 50, 100 et
  300 cp) et G/N/P, et section 3 ter, erreurs et gaffes par camp avec le
  meilleur coup, sa ligne et la FEN.
- Section 1 : repères de phase (roques, disparition des dames, entrée en
  finale).
- Journal : annonce de la phase Stockfish et temps restant estimé.
- `--sans-stockfish`.
- README.nfo et TESTS.nfo.

### Changed

- La base Lichess devient la base par défaut, à la place de la base
  maîtres.
- L'évaluation Stockfish est calculée par défaut. `--avec-stockfish`
  reste acceptée, sans effet.
- `--longueur-pv` passe de 6 à 5.
- Un coup rare qui reste dans une ligne du catalogue n'est plus une
  sortie de théorie.
- Un identifiant Lichess fait exactement 8 ou 12 caractères : un fichier
  inexistant est signalé introuvable au lieu d'être envoyé à Lichess.

### Fixed

- Explorateur : la requête ne demandait que les dix premiers coups
  (`moves=10`), un coup plus rare ressortait à 0 partie et au rang "hors
  base". Elle demande désormais `moves=256`.

## Versions antérieures au 8 octobre 2026

Non documentées. Le script collectait déjà le PGN, local ou téléchargé
depuis Lichess, les statistiques de la base maîtres de l'explorateur et,
sur demande avec `--avec-stockfish`, les évaluations du moteur, le tout
dans une archive zip avec `synthese.md`.
