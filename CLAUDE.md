# CLAUDE.md

## Projet

IAnalyze collecte les données d'une partie d'échecs (PGN, stats de
l'explorateur Lichess, catalogue d'ouvertures, évaluations Stockfish)
et produit un zip avec summary.md, plus le prompt d'analyse de la
partie, écrit à côté. Les deux alimentent une conversation avec un LLM,
où l'analyse est faite. Le script ne produit lui-même aucune analyse.

Fichiers : ianalyze.py, prompt-modele.txt (modèle du prompt),
prompt-seul-modele.txt (modèle du prompt court de --prompt-only),
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
- Sur les deux : tout ce que le script crée pour lui-même vit dans le
  dossier de l'application. Dans local/, ce qu'il sait refaire seul :
  venv (local/venv) et catalogue. À la racine, les réglages :
  settings.ini, et tout autre profil : --settings ne prend qu'un nom en
  .ini, jamais un chemin. Les deux sont ignorés par git. Supprimer le
  dossier ne laisse rien, hors le jeton (~/.lichess_token) ; vider
  local/ garde les réglages.
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
  constantes, et les dest d'argparse (--output-dir remplit toujours
  options.sortie). Les algorithmes ne changent pas : seuls les
  littéraux changent (chaînes, motifs des regex, mots des réponses),
  sauf pluriel(), qui passe à la règle anglaise (!= 1), et les rangs
  des variantes, confiés au 4b à ordinal() (1st, 2nd, 3rd, 11th, 21st)
  à la place d'une liste suivie d'un suffixe unique.
- Rupture de compatibilité, donc version majeure : 5.0.0, appliquée
  une seule fois, à la fusion dans main.
- Pas de migration : l'ancien reglages.ini et l'ancien catalogue.tsv
  sont ignorés, sans message. Un settings.ini à l'ancien format garde
  sa section [joueur], recopiée comme section inconnue après [player].
- Traduction faite directement, sans DeepL.
- Huit lots, dont le 4 en quatre sous-lots ; un patch par lot ou
  sous-lot. Lot 0 : CLAUDE.md.
- Lot 1 : commentaires et docstrings, sans changer le code : l'AST, une
  fois les docstrings retirées, est identique avant et après.
- Lot 2 : messages d'ianalyze.py sur la sortie d'erreur (journal,
  avertissements, erreurs, aide) et vérifications des tests. Seules les
  chaînes changent, avec les mêmes marqueurs %. Une chaîne qui part
  aussi dans l'archive attend le lot 4.
- Lot 2b : messages de test-app.sh (titres, libellés des vérifications,
  rapport, erreurs).
- Lot 3a : noms et valeurs des options d'ianalyze.py, de
  verifier-analyse.py et de test-app.sh, variables d'environnement.
- Lot 3b : questions et réponses au terminal, réglages, catalogue. Les
  questions vont avec leurs réponses : elles portent les touches à
  taper. Les quatre questions de QUESTIONS_CONTEXTE, dont les réponses
  partent dans context.md, attendent le lot 4. La phrase de cadence
  (decrire_cadence) passe au 3b : défaut affiché au terminal, elle
  partage pluriel() et duree_increment() avec settings.ini ; dans
  context.md et le prompt, ses libellés restent français jusqu'au
  lot 4.
- Lot 4 : archive et LLM, en quatre sous-lots, chacun avec la suite au
  vert ; le vérificateur suit chaque changement de l'archive dans le
  sous-lot qui le fait. 4a : noms de l'archive et clefs JSON. 4b :
  context.md et summary.md, questions de démarrage comprises, et les
  valeurs écrites dans leurs phrases (camps, natures des coups, origine
  du camp, remarques d'encodage, erreurs et motifs d'arrêt de
  l'explorateur). 4c : modèles de prompt, langage compris
  (directives, conditions, valeurs). 4d : rapport et messages du
  vérificateur, hors ses options, renommées au lot 3a.
- Choix du lot 4 : l'analyse est demandée en anglais ; les clefs de
  collection.json passent par une table dest -> clef (CLEFS_COLLECTE),
  avec un test qui exige une clef par option ; le langage des modèles
  passe en anglais, sans alias.
- Lot 5 : renommage des fichiers du dépôt et documentation.
- Dérogation : la documentation (README, EXEMPLES, TECHNIQUE, TESTS)
  est traduite et remise à jour au lot 5, une fois l'interface figée.
  Le CHANGELOG suit chaque lot, en anglais, sous Unreleased. CLAUDE.md
  suit chaque renommage dans le lot qui le fait.
- Renommages du lot 3a : toutes les options d'ianalyze.py et de
  verifier-analyse.py, dest inchangés ; --base maitres -> --database
  masters ; variables JETON et GARDER de test-app.sh -> TOKEN et KEEP ;
  option --reseau de test-app.sh -> --network ; variable
  IANALYZE_DEJA_RELANCE -> IANALYZE_RELAUNCHED.
- Renommages du lot 3b, faits : catalogue.tsv -> catalog.tsv, format 2,
  colonnes epd eco name, clefs lines, named, known ; dans
  settings.ini, [joueur] -> [player], pseudos, cadence, niveau,
  annotateur -> usernames, time_control, rating, annotator.
- Renommages du lot 4a, faits : `analyse-<partie>-<date>` ->
  `analysis-<game>-<date>` ; partie.pgn, partie-origine.pgn,
  synthese.md, contexte.md, collecte.json, explorateur/ -> game.pgn,
  game-original.pgn, summary.md, context.md, collection.json,
  explorer/ ; clefs d'evaluations.json demicoup, numero, trait, joue,
  meilleurs, ecart_cp, nature, valeur_trait, profondeur, non_evalue,
  gain, nulle, perte -> ply, move_number, side_to_move, played, best,
  cp_loss, category, value_for_side, depth, not_evaluated, win, draw,
  loss ; dans collection.json, les options sous leur nom anglais, puis
  token_present, catalog_used, side (side, origin, modified_tags),
  context_collected, pgn_encoding, pgn_remarks, prompt_written ;
  _erreur -> _error ; `<JETON-EXPURGE>` -> `<TOKEN-REDACTED>`.
- Renommages du lot 4b, faits : valeurs Blancs, Noirs, imprécision,
  erreur, gaffe, mat, maîtres -> White, Black, inaccuracy, mistake,
  blunder, mate, masters ; libellés de context.md (a. Scope, Player's
  side...) et (défaut) -> (default) ; titres de summary.md, dont
  3 bis et 3 ter -> 3a et 3b, et colonnes, dont G/N/P -> W/D/L.
- Renommages du lot 4c, faits : directives si, si non, sinon, fin ->
  if, if not, else, end ; conditions et valeurs des modèles en anglais
  (EXPLORER, SIDE_KNOWN, {{GAME_PGN}}, {{USERNAMES}}... ; STOCKFISH,
  VERSION, ARCHIVE, MULTIPV inchangés) ; sections du prompt en
  anglais, dont RÉSUMÉ DE LA PARTIE -> OVERVIEW OF THE GAME ; le
  tutoiement devient "you", sur un ton amical.
- Renommages du lot 4d, faits : dans le rapport du vérificateur,
  repères ECHEC, ATTENTION -> FAIL, WARNING (OK, INFO inchangés) ;
  === Bilan === -> === Totals ===, échecs, attentions -> failures,
  warnings ; titres des sections (1. Reading the PGN... 8. Evaluations
  quoted in the conversation) ; métavariables FICHIER, NOM -> FILE,
  NAME, --name recevant metavar="NAME", seul changement hors
  littéraux.
- Renommages du lot 5 : verifier-analyse.py -> verify-analysis.py,
  prompt-modele.txt -> prompt-template.txt, prompt-seul-modele.txt ->
  prompt-only-template.txt, parties-exemples/ -> example-games/
  (fichiers compris), EXEMPLES.md -> EXAMPLES.md, TECHNIQUE.md ->
  TECHNICAL.md.
- Points d'attention : au terminal, "b" voulait dire Blancs, il veut
  dire Black ([w/b]) depuis le lot 3b, signalé dans le CHANGELOG ;
  verify-analysis.py ne lira plus les archives 4.x ; le prompt traduit
  ne se valide qu'avec un vrai LLM, par l'utilisateur.
- Glossaire, à compléter au fil des lots : partie = game ; coup = move ;
  demi-coup = ply ; trait = side to move ; Blancs, Noirs = White,
  Black ; camp = side ; cadence = time control ; correspondance =
  correspondence ; classique, rapide = classical, rapid ; imprécision,
  erreur, gaffe = inaccuracy, mistake, blunder ; erreur au sens large =
  error ; centipion = centipawn ; écart au meilleur coup = centipawn
  loss ; variante = variation (variante principale = principal
  variation, PV) ; profondeur = depth ; explorateur = explorer ; base
  maîtres = masters database ; sortie de théorie = exit from theory ;
  catalogue = catalog ; niveau, classement = rating ; pseudo =
  username ; jeton = token ; réglages = settings ; questions de
  démarrage = startup questions ; collecte = collection ; dossier de
  travail = working folder ; synthèse = summary ; consignes =
  instructions ; journal = log ; bilan = report ; palmarès = ranking ;
  modèle = template ; périmètre = scope ; dossier de sortie = output
  directory ; délai = timeout ; fils = threads ; jusqu'à épuisement =
  exhaustive ; gain, nulle, perte = win, draw, loss (W/D/L) ;
  avertissement "Attention" = "Warning" ; aide = help ; code de retour
  = exit code ; inconnu = unknown ; cadence non précisée =
  unspecified ; délai fixe = fixed delay ; repères de phase = phase
  markers ; fenêtre de départ = starting window ; échantillon =
  sample ; coup majoritaire = most played move (colonne Top move) ;
  motif d'arrêt = stop reason ; résumé d'avant le coup 1 = overview ;
  contrôle = check ; rendu par le LLM = returned by the LLM ; du cru
  du LLM = the LLM's own ; dans le rapport des tests,
  réussi, échec, sauté = passed, failed, skipped, et les marqueurs
  ECHEC, SAUTE = FAIL, SKIP ; dans celui du vérificateur, ECHEC,
  ATTENTION = FAIL, WARNING, et son bilan = totals, toute sa sortie
  étant déjà le rapport.
- Correspondance à capital : capital, incrément, plafond, réserve =
  clock, increment, maximum, bank, termes des ICCF Rules 2026 (§2.4 et
  annexe 3), vérifiés au lot 1.

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
faux explorateur, sauf ceux de test-app.sh --network, qui emploient le
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
