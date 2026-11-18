# Changelog

Toutes les modifications notables de collecte-partie.py sont consignées
dans ce fichier.

Le format suit [Tenez un Changelog](https://keepachangelog.com/fr/1.1.0/)
et le projet applique le [versionnage sémantique](https://semver.org/).

## [Unreleased]

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
