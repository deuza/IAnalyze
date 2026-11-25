# CLAUDE.md

## Projet

IAnalyze collecte les données d'une partie d'échecs (PGN, stats de
l'explorateur Lichess, catalogue d'ouvertures, évaluations Stockfish)
et produit un zip avec synthese.md, plus le prompt d'analyse de la
partie, écrit à côté. Les deux alimentent une conversation avec un LLM,
où l'analyse est faite. Le script ne produit lui-même aucune analyse.

Fichiers : ianalyze.py, prompt-modele.txt (modèle du prompt),
prompt-seul-modele.txt (modèle du prompt court de --prompt-seul),
verifier-analyse.py (contrôle du PGN rendu par le LLM),
test.pgn (partie d'essai), test-app.sh (suite de tests),
parties-exemples/ (fichiers des exemples d'EXEMPLES.md),
README.md (installation et usage courant), EXEMPLES.md (commandes,
options et sorties, sur le plan d'une page de manuel), TECHNIQUE.md
(fonctionnement), TESTS.md (lancement des tests et tableau de tous les
tests), CHANGELOG.md.

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
- Ne commite ni ne pousse rien. Chaque lot est livré en patch (git diff,
  appliqué par "git apply --index"), avec un brouillon du message de
  commit : en français, un sujet par commit, sans ligne Co-Authored-By.
  L'utilisateur applique, commite à son nom et pousse. Avant le lot
  suivant, vérifie qu'origin/dev contient exactement le patch, puis
  recale-toi dessus.
- CHANGELOG.md : <https://keepachangelog.com/en/1.1.0/> (section
  Unreleased pendant le travail).
- Versions : <https://semver.org/>. La version figure dans le script et
  dans le User-Agent : les deux changent ensemble.
- La 4.0.0 a été fusionnée dans main, étiquetée et publiée sur GitHub
  le 21 novembre 2026. main ne porte pas CLAUDE.md : à chaque fusion,
  le fichier est retiré par "git rm -f CLAUDE.md" avant le commit.
- Un seul bump par fusion dans main, jamais par fournée de travail sur
  dev : entre deux fusions, tout s'accumule sous Unreleased. Annonce le
  niveau choisi et sa raison avant de l'appliquer.

## Traduction en anglais (en cours, vers la 5.0.0)

- Tout passe en anglais, sans alias : sorties (journal, erreurs,
  questions, aide), options, réglages, archive (noms et contenu),
  modèles de prompt, vérificateur, commentaires, docstrings,
  documentation et noms des fichiers du dépôt. README.fr.md est la
  version française du README, tenue à jour avec lui.
- Restent en français : les noms de fonctions, de variables et de
  constantes, et les dest d'argparse (--output remplit toujours
  options.sortie). Les algorithmes ne changent pas : seuls les
  littéraux changent (chaînes, motifs des regex, mots des réponses),
  sauf pluriel(), qui passe à la règle anglaise (!= 1).
- Rupture de compatibilité, donc version majeure : 5.0.0, appliquée
  une seule fois, à la fusion dans main.
- Pas de migration : l'ancien reglages.ini et l'ancien catalogue.tsv
  sont ignorés, sans message.
- Traduction faite directement, sans DeepL.
- Six lots, un patch chacun. Lot 0 : CLAUDE.md.
- Lot 1 : commentaires et docstrings, sans changer le code : l'AST, une
  fois les docstrings retirées, est identique avant et après.
- Lot 2 : messages (journal, erreurs, questions, aide) et vérifications
  des tests.
- Lot 3 : interface, soit options, réponses au terminal, réglages,
  catalogue, variables d'environnement, options de test-app.sh.
- Lot 4 : archive et LLM, soit noms et contenu des fichiers (JSON,
  synthèse, contexte), modèles de prompt, vérificateur.
- Lot 5 : renommage des fichiers du dépôt et documentation.
- Dérogation : la documentation (README, EXEMPLES, TECHNIQUE, TESTS)
  est traduite et remise à jour au lot 5, une fois l'interface figée.
  Le CHANGELOG suit chaque lot, en anglais, sous Unreleased. CLAUDE.md
  suit chaque renommage dans le lot qui le fait.
- Renommages du lot 3 : reglages.ini -> settings.ini, catalogue.tsv ->
  catalog.tsv, variable JETON de test-app.sh -> TOKEN, option --reseau
  de test-app.sh -> --network. Les noms des autres options sont fixés
  au lot 3.
- Renommages du lot 5 : verifier-analyse.py -> verify-analysis.py,
  prompt-modele.txt -> prompt-template.txt, prompt-seul-modele.txt ->
  prompt-only-template.txt, parties-exemples/ -> example-games/
  (fichiers compris), EXEMPLES.md -> EXAMPLES.md, TECHNIQUE.md ->
  TECHNICAL.md.
- Points d'attention : au terminal, "b" voulait dire Blancs, il voudra
  dire Black ([w/b]), à signaler dans le CHANGELOG ; verify-analysis.py
  ne lira plus les archives 4.x ; le prompt traduit ne se valide
  qu'avec un vrai LLM, par l'utilisateur.
- Glossaire, à compléter au fil des lots : partie = game ; coup = move ;
  demi-coup = ply ; trait = side to move ; Blancs, Noirs = White,
  Black ; camp = side ; cadence = time control ; correspondance =
  correspondence ; classique, rapide = classical, rapid ; imprécision,
  erreur, gaffe = inaccuracy, mistake, blunder ; centipion = centipawn ;
  écart au meilleur coup = centipawn loss ; variante = variation
  (variante principale = principal variation, PV) ; profondeur =
  depth ; explorateur = explorer ; base maîtres = masters database ;
  catalogue = catalog ; niveau, classement = rating ; pseudo =
  username ; jeton = token ; réglages = settings ; synthèse = summary ;
  journal = log ; modèle = template ; périmètre = scope ; gain, nulle,
  perte = win, draw, loss (W/D/L). Capital, plafond et réserve des
  cadences par correspondance : termes à reprendre du texte anglais
  des ICCF Rules (section 2.4), vérifiés au lot 2.

## Règles de modification

- Aucun correctif à l'aveugle : reproduis ou démontre le défaut, ou
  demande les logs, la conf et la version.
- Ne supprime aucun code pour "optimiser". Toute suppression
  nécessaire est listée à la fin de la livraison.
- Modification d'un fichier existant : changement ciblé, pas de
  réécriture complète non demandée.
- Chaque ajout de comportement s'accompagne d'un test dans test-app.sh
  et d'une mise à jour de la documentation : EXEMPLES.md pour une
  option ou un message, avec sa sortie réelle, README.md si l'usage
  courant change, TECHNIQUE.md pour le fonctionnement, TESTS.md pour
  les tests. TESTS.md porte une ligne par test : un test ajouté y
  reçoit sa ligne, un test modifié y voit la sienne mise à jour.

## Vérifications avant livraison

Lance ce qui est disponible : python3 -m py_compile, flake8, ruff check,
mypy, bandit, codespell, vulture. Dis lesquels manquent et ne prétends
jamais avoir vérifié ce que tu n'as pas lancé. Idem pour ce qui n'a pas
pu être testé (par exemple un vrai jeton Lichess).

## Sécurité

Le jeton Lichess est dans ~/.lichess_token (mode 600). Ne le lis pas
pour l'afficher, ne le journalise pas, ne le copie dans aucun fichier
du dépôt ni dans aucun test. Les tests utilisent un faux jeton ou un
faux explorateur, sauf ceux de test-app.sh --reseau, qui emploient le
vrai jeton sans l'afficher ni le copier, et que seul l'utilisateur
lance.

## Style

- Commentaires et docstrings abondants, en anglais.
- Pas de tiret cadratin, pas de guillemets chevrons, pas d'émoji dans
  les scripts.
- Documents en anglais, sauf README.fr.md, en français et au
  vouvoiement. Nos échanges restent en français, au tutoiement.

## Façon de travailler

- Réponses courtes, une étape à la fois.
- Je distingue fait vérifié, probable, hypothèse. Pas de lien non
  vérifié.
- Si j'écris DEBUG ON, on discute du problème sans rien modifier
  jusqu'à DEBUG OFF.
