# CLAUDE.md

## Projet
IAnalyze collecte les données d'une partie d'échecs (PGN, stats de
l'explorateur Lichess, catalogue d'ouvertures, évaluations Stockfish)
et produit un zip avec synthese.md, plus le prompt d'analyse de la
partie, écrit à côté. Les deux alimentent une conversation avec un LLM,
où l'analyse est faite. Le script ne produit lui-même aucune analyse.

Fichiers : collecte-partie.py, prompt-modele.txt (modèle du prompt),
prompt-seul-modele.txt (modèle du prompt court de --prompt-seul),
verifier-analyse.py (contrôle du PGN rendu par le LLM),
test.pgn (partie d'essai), test-app.sh (suite de tests),
README.md, TESTS.md, CHANGELOG.md.

## Plateformes
- Serveurs : Debian Trixie, en root, pas de sudo. Stockfish dans
  /usr/games/stockfish.
- Poste : macOS M1 (Homebrew).
- Sur les deux : venv dans ~/.local/share/IAnalyze/venv, catalogue dans
  ~/.local/share/IAnalyze, réglages dans ~/.config/IAnalyze.
- Le comportement doit rester identique sur les deux.
- Python : modules hors apt installés dans un venv dédié, jamais dans
  l'environnement système. Signale tout nouveau module requis.

## Git, versions, changelog
- On travaille sur la branche dev. Ni push ni merge sans demande.
- Commits atomiques, un par sujet, message en français.
- CHANGELOG.md : https://keepachangelog.com/en/1.1.0/ (section
  Unreleased pendant le travail).
- Versions : https://semver.org/. La version figure dans le script et
  dans le User-Agent : les deux changent ensemble.
- La 4.0.0 est la version qui sera fusionnée dans main, étiquetée et
  publiée sur GitHub. D'ici là, aucun bump : tout s'accumule sous
  Unreleased sur dev.
- Ensuite, un seul bump par fusion dans main, jamais par fournée de
  travail sur dev. Annonce le niveau choisi et sa raison avant de
  l'appliquer.

## Règles de modification
- Aucun correctif à l'aveugle : reproduis ou démontre le défaut, ou
  demande les logs, la conf et la version.
- Ne supprime aucun code pour "optimiser". Toute suppression
  nécessaire est listée à la fin de la livraison.
- Modification d'un fichier existant : changement ciblé, pas de
  réécriture complète non demandée.
- Chaque ajout de comportement s'accompagne d'un test dans test-app.sh
  et d'une mise à jour de README.md. TESTS.md ne décrit que les
  familles de tests : il ne change que si une famille apparaît.

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
