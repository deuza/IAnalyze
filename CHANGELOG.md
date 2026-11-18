# Changelog

Toutes les modifications notables de collecte-partie.py sont consignées
dans ce fichier.

Le format suit [Tenez un Changelog](https://keepachangelog.com/fr/1.1.0/)
et le projet applique le [versionnage sémantique](https://semver.org/).

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
