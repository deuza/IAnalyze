# CLAUDE.md

## Projet
IA-chess-brief collecte les données d'une partie d'échecs (PGN,
stats de l'explorateur Lichess, catalogue d'ouvertures, évaluations
Stockfish) et produit un zip avec synthese.md. Ce zip alimente le
projet claude.ai "Analyses de parties d'échecs", où l'analyse est faite.
Le script ne produit lui-même aucune analyse.

Fichiers : IA-chess-brief, catalogue.tsv, README.nfo, TESTS.nfo,
CHANGELOG.md.

## Plateformes
- Serveurs : Debian Trixie, en root, pas de sudo. Stockfish dans
  /usr/games/stockfish, venv par défaut /opt/venv/lichess.
- Poste : macOS M1 (Homebrew), venv et catalogue dans
  ~/.local/share/collecte-partie.
- Le comportement doit rester identique sur les deux. Toute option de
  la ligne de commande existante doit continuer à fonctionner.
- Python : modules hors apt installés dans un venv dédié, jamais dans
  l'environnement système. Signale tout nouveau module requis.

## Git, versions, changelog
- On travaille sur la branche dev. Ni push ni merge sans demande.
- Commits atomiques, un par sujet, message en français.
- CHANGELOG.md : https://keepachangelog.com/en/1.1.0/ (section
  Unreleased pendant le travail).
- Versions : https://semver.org/. Annonce le niveau de bump choisi et
  sa raison avant de l'appliquer. La version figure dans le script et
  dans le User-Agent : les deux changent ensemble.

## Règles de modification
- Aucun correctif à l'aveugle : reproduis ou démontre le défaut, ou
  demande les logs, la conf et la version.
- Ne supprime aucun code pour "optimiser". Toute suppression
  nécessaire est listée à la fin de la livraison.
- Modification d'un fichier existant : changement ciblé, pas de
  réécriture complète non demandée.
- Chaque ajout de comportement s'accompagne d'un test dans TESTS.nfo
  et d'une mise à jour de README.nfo.

## Vérifications avant livraison
Lance ce qui est disponible : python3 -m py_compile, flake8, ruff check,
mypy, bandit, codespell, vulture. Dis lesquels manquent et ne prétends
jamais avoir vérifié ce que tu n'as pas lancé. Idem pour ce qui n'a pas
pu être testé (par exemple un vrai jeton Lichess).

## Sécurité
Le jeton Lichess est dans ~/.lichess_token (mode 600). Ne le lis pas
pour l'afficher, ne le journalise pas, ne le copie dans aucun fichier
du dépôt ni dans aucun test. Les tests utilisent un faux jeton ou un
faux explorateur.

## Style
- Commentaires abondants en français, au vouvoiement.
- Pas de tiret cadratin, pas de guillemets chevrons, pas d'émoji dans
  les scripts.
- Le vouvoiement s'applique aux documents (README, CHANGELOG), le
  tutoiement à nos échanges.

## Façon de travailler
- Réponses courtes, une étape à la fois.
- Je distingue fait vérifié, probable, hypothèse. Pas de lien non
  vérifié.
- Si j'écris DEBUG ON, on discute du problème sans rien modifier
  jusqu'à DEBUG OFF.
