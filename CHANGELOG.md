# Changelog

Toutes les modifications notables de collecte-partie.py sont consignées
dans ce fichier.

Le format suit [Tenez un Changelog](https://keepachangelog.com/fr/1.1.0/)
et le projet applique le [versionnage sémantique](https://semver.org/).

## [Unreleased]

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
