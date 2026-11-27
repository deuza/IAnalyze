# CLAUDE.md

## Projet

IAnalyze collecte les données d'une partie d'échecs (PGN, stats de
l'explorateur Lichess, catalogue d'ouvertures, évaluations Stockfish)
et produit un zip avec summary.md, plus le prompt d'analyse de la
partie, écrit à côté. Les deux alimentent une conversation avec un LLM,
où l'analyse est faite. Le script ne produit lui-même aucune analyse.

Fichiers : ianalyze.py, prompt-template.txt (modèle du prompt),
prompt-only-template.txt (modèle du prompt court de --prompt-only),
verify-analysis.py (contrôle du PGN rendu par le LLM),
tests/ (test-app.sh, la suite de tests, qui trouve le dépôt d'après
son propre chemin et écrit son rapport dans tests/ ; test.pgn, sa
partie d'essai ; refused/ et llm/, les PGN refusés et les PGN annotés
qu'EXAMPLES cite et que T83 contrôle), example-games/ (les parties
analysables des exemples d'EXAMPLES.md),
README.md (installation et usage courant, pour le joueur),
README.fr.md (sa version française), EXAMPLES.md (commandes,
options et sorties, sur le plan d'une page de manuel),
EXAMPLES.fr.md (sa version française), docs/ (pour qui reprend le
projet : TECHNICAL.md, le fonctionnement, et en section 15 le guide
du développeur ; TESTS.md, le lancement des tests et le tableau de
tous les tests ; TRIALS.md, les essais des LLM ; chacun avec sa
version française en .fr.md), CHANGELOG.md.

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
- Machines d'essai de la suite, pour la 5.0.0 : Debian 13 sur PC et
  sur Raspberry Pi 4 (aarch64), macOS 27.3 sur M1, et le conteneur
  Ubuntu de Claude. docs/TESTS.md en tient le tableau, sans nom de
  machine ni chemin personnel.
- Python : modules hors apt installés dans un venv dédié, jamais dans
  l'environnement système. Signale tout nouveau module requis.

## Git, versions, changelog

- On travaille sur la branche dev. Ni push ni merge sans demande.
- Ne commite ni ne pousse rien. Chaque lot est livré en patch (git diff,
  appliqué par "git apply --index"), avec un brouillon du message de
  commit : en français, sans ligne Co-Authored-By. Un sujet par commit
  par défaut ; l'utilisateur préfère un lot unique quand les sujets
  sont nombreux et liés, pour ne pas noyer l'historique : le CHANGELOG
  en garde le détail, et le message les regroupe par thème.
  L'utilisateur applique, commite à son nom et pousse. Avant le lot
  suivant, vérifie qu'origin/dev contient exactement le patch, puis
  recale-toi dessus.
- L'utilisateur dépose le patch et le message dans /root/dev/, le
  dossier parent de son dépôt, /root/dev/IAnalyze : les commandes
  livrées se lancent dans le dépôt, sur `../<lot>.patch` et
  `../<lot>.msg`.
- CLAUDE.md est le fichier de Claude : il le tient à jour lui-même, à
  chaque lot qui change ce qu'il décrit, sans attendre qu'on le lui
  demande.
- CHANGELOG.md : <https://keepachangelog.com/en/1.1.0/> (section
  Unreleased pendant le travail).
- Versions : <https://semver.org/>. La version figure dans le script et
  dans le User-Agent : les deux changent ensemble.
- main porte la 5.0.0, publiée sur GitHub le 27 novembre 2026 ; les
  étiquettes v4.0.0, v4.0.1, v4.0.2 et v5.0.0 sont sur le dépôt. main
  ne porte pas CLAUDE.md : à chaque fusion, le fichier est retiré par
  "git rm -f CLAUDE.md" avant le commit. main n'est pas un ancêtre de
  dev : son dernier commit est la fusion de la 5.0.0, qui retire
  CLAUDE.md. La fusion de dev dans main bute donc sur un conflit
  modification/suppression de CLAUDE.md, réglé par ce même git rm.
- Une publication suit toujours le même rite : sur dev, un commit
  "Version X.Y.Z" (VERSION, titre de la version dans le CHANGELOG et
  ses références de liens) ; la suite --network relancée sur chaque
  machine d'essai, et le tableau des machines de docs/TESTS.md mis à
  jour, dans les deux langues ; sur main, la fusion de dev, intitulée
  "IAnalyze X.Y.Z", puis "Fusion de la branche dev." et un résumé ;
  une étiquette vX.Y.Z annotée et signée (git tag -s) ; une release
  GitHub du même nom. Claude en rédige les messages et les notes.
- Un seul bump par fusion dans main, jamais par fournée de travail sur
  dev : entre deux fusions, tout s'accumule sous Unreleased. Annonce le
  niveau choisi et sa raison avant de l'appliquer.

## Traduction en anglais (faite, publiée en 5.0.0)

- Tout passe en anglais, sans alias : sorties (journal, erreurs,
  questions, aide), options, réglages, archive (noms et contenu),
  modèles de prompt, vérificateur, commentaires, docstrings,
  documentation et noms des fichiers du dépôt.
- Documentation bilingue : README, EXAMPLES, et dans docs/ TECHNICAL,
  TESTS et TRIALS ont chacun leur version française, `<nom>.fr.md`,
  au vouvoiement, sur le même plan, tenue à jour avec la version
  anglaise dans le même lot.
  Commandes et sorties y sont les mêmes, en anglais. Le CHANGELOG
  reste en anglais seul.
- Restent en français : les noms de fonctions, de variables et de
  constantes, et les dest d'argparse (--output-dir remplit toujours
  options.sortie). Les algorithmes ne changent pas : seuls les
  littéraux changent (chaînes, motifs des regex, mots des réponses),
  sauf pluriel(), qui passe à la règle anglaise (!= 1), et les rangs
  des variantes, confiés au 4b à ordinal() (1st, 2nd, 3rd, 11th, 21st)
  à la place d'une liste suivie d'un suffixe unique.
- Rupture de compatibilité, donc version majeure : 5.0.0, appliquée
  une seule fois, à la fusion dans main du 27 novembre 2026.
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
- Lot 5 : renommage des fichiers du dépôt et documentation, en huit
  sous-lots : 5a, renommages des fichiers du dépôt et leurs
  références ; 5b, exemples (noms et contenu) et textes de LLM
  simulés des tests ; 5c, README.md et README.fr.md ; 5d,
  TECHNICAL.md ; 5e, EXAMPLES.md et EXAMPLES.fr.md, sorties
  réelles ; 5f, TESTS.md et TESTS.fr.md ; 5g, TECHNICAL.fr.md ;
  5h, historique du CHANGELOG, traduit, les noms d'options, de
  fichiers, de clefs et les messages de chaque version gardés tels
  qu'ils étaient. Le contenu des exemples passe en anglais, sauf
  french-notation.pgn, dont la notation est le sujet.
- Dérogation : la documentation (README, EXAMPLES, TECHNICAL, TESTS)
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
- Renommages du lot 5a, faits : verifier-analyse.py ->
  verify-analysis.py, prompt-modele.txt -> prompt-template.txt,
  prompt-seul-modele.txt -> prompt-only-template.txt,
  parties-exemples/ -> example-games/, EXEMPLES.md -> EXAMPLES.md,
  TECHNIQUE.md -> TECHNICAL.md ; `rapport-tests-<système>-<date>.txt`
  -> `test-report-<system>-<date>.txt` ; dans le .gitignore,
  analyse-* -> analysis-*. Les fichiers de example-games/ sont
  renommés au 5b, d'après la table validée.
- Renommages du lot 5b, faits : dans example-games/, accolade,
  analyse-courte, analyse-fautive, analyse-llm, conversation.txt,
  deux-parties, francais, ma-partie, partie-ajedrezmail,
  partie-chess-com, partie-chess-mail, partie-commentee,
  partie-lichess-org, partie-lucas-chess, polonaise ->
  unclosed-brace, llm-short, llm-faulty, llm-annotated,
  llm-conversation.txt, two-games, french-notation, my-game,
  game-ajedrezmail, game-chess-com, game-chess-mail, commented-game,
  game-lichess-org, game-lucas-chess, polish-opening (position
  inchangé) ; pseudos MonPseudo, Adversaire -> MyUsername, Opponent.
  Contenus traduits, sauf french-notation.pgn ; test.pgn garde ses
  noms accentués et un échantillon d'accents.
- Renommage hors lot, fait : fichiers provisoires `.<nom>.partiel`,
  `.<dossier>.partiel.zip` -> `.<nom>.partial`,
  `.<dossier>.partial.zip`.
- Points d'attention : au terminal, "b" voulait dire Blancs, il veut
  dire Black ([w/b]) depuis le lot 3b, signalé dans le CHANGELOG ;
  verify-analysis.py ne lira plus les archives 4.x ; le prompt traduit
  ne se valide qu'avec un vrai LLM, par l'utilisateur : fait le
  27 novembre 2026, sur les prompts publiés (docs/TRIALS.md).
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
  et d'une mise à jour de la documentation, dans ses deux langues :
  EXAMPLES.md pour une option ou un message, avec sa sortie réelle,
  README.md si l'usage courant change, docs/TECHNICAL.md pour le
  fonctionnement, docs/TESTS.md pour les tests. docs/TESTS.md porte
  une ligne par test : un test ajouté y reçoit sa ligne, un test
  modifié y voit la sienne mise à jour.
- Le README s'adresse au joueur : installation, usage, choix du LLM,
  vérification du PGN rendu. Le fonctionnement va dans
  docs/TECHNICAL.md, dont la section 15, le guide du développeur,
  suit tout changement de l'organisation du code, des tables, des
  outils de la suite, des remarques connues des contrôles ou du rite
  de publication.

## Vérifications avant livraison

Lance ce qui est disponible : python3 -m py_compile, flake8, ruff check,
mypy, bandit, codespell, vulture. Dis lesquels manquent et ne prétends
jamais avoir vérifié ce que tu n'as pas lancé. Idem pour ce qui n'a pas
pu être testé (par exemple un vrai jeton Lichess).

La suite se lance à chaque lot, sur un clone où le patch est appliqué :
hors réseau, puis avec --network, l'une après l'autre. Avec --network,
TOKEN désigne le fichier factice et le proxy injecte le vrai jeton
(voir Sécurité) ; T24 prend une partie publique de Lichess, dont
l'identifiant ne s'écrit nulle part dans le dépôt. Une fois les deux
passages réussis, le tableau "Last runs" de docs/TESTS.md, section 1,
et celui de docs/TESTS.fr.md en reçoivent, dans le même lot, la date et
l'heure de fin en UTC, l'heure du fichier du rapport, et les comptes.
Aucune durée, ni là ni ailleurs : elle dépend de la machine et du
réseau.

Pièges de la suite, vus en vrai :

- Une seule suite à la fois par machine : M2 compte les moteurs de
  toute la machine, et voit ceux d'une autre suite.
- Le pilote du pseudo-terminal répond après une seconde de silence :
  sur une machine lente, un Raspberry Pi, la réponse peut précéder la
  question. Une question finit sans saut de ligne : un contrôle en
  compte les occurrences, jamais les lignes.
- Le conteneur de Claude est une Ubuntu, pas une Debian : un résultat
  qui en dépend se dit tel quel.

## Sécurité

Le jeton Lichess est dans ~/.lichess_token (mode 600). Ne le lis pas
pour l'afficher, ne le journalise pas, ne le copie dans aucun fichier
du dépôt ni dans aucun test. Les tests utilisent un faux jeton ou un
faux explorateur, sauf ceux de test-app.sh --network, qui emploient le
vrai jeton sans l'afficher ni le copier. L'utilisateur les lance, ou
Claude avec le jeton que le proxy de son environnement injecte dans
les requêtes à explorer.lichess.org : TOKEN désigne alors un fichier
factice, et le vrai jeton n'entre jamais dans le bac à sable.

## Style

- Commentaires et docstrings abondants, en anglais.
- Pas de tiret cadratin, pas de guillemets chevrons, pas d'émoji dans
  les scripts.
- Saut de ligne Markdown : une barre oblique inverse en fin de ligne,
  jamais d'espaces, que git signale comme parasites. Elle ne marche
  pas sous Obsidian, l'utilisateur le sait. La documentation ne parle
  pas de cette convention.
- Documents en anglais, sauf leurs versions françaises (.fr.md), au
  vouvoiement. Nos échanges restent en français, au tutoiement.

## Essais des LLM

- Une série : une partie, collectée une fois par route, le zip puis
  --prompt-only avec --keep-folder. L'utilisateur envoie les réponses,
  nommées d'après le LLM, et les dossiers de travail. Une réponse
  ajoutée plus tard reprend le prompt déjà écrit, sans nouvelle
  collecte : les évaluations changent d'une collecte à l'autre.
- Chaque PGN passe au vérificateur contre le dossier de sa route, avec
  --summary pour le texte qui l'entoure. Une réponse dont la copie a
  perdu ses sauts de ligne est revérifiée une fois remise en forme, et
  la doc le dit.
- Les récits se contrôlent sur l'échiquier, un agent par réponse, puis
  chaque erreur citée dans la doc est revérifiée avec python-chess. Ne
  comptent que les faits : prises, échecs, attaques, défenses,
  matériel, cases, pendules, chiffres de la base ; jamais les
  opinions, ni les mots comme "ouverte" pour "demi-ouverte".
- docs/TRIALS.md, dans les deux langues : une section par série, son
  tableau, ce qu'elle montre ; le conseil du README, section 4, s'en
  tient à ce qu'elles montrent ; la partie dans example-games, avec
  sa ligne dans EXAMPLES.

## Façon de travailler

- Réponses courtes, une étape à la fois.
- Je distingue fait vérifié, probable, hypothèse. Pas de lien non
  vérifié.
- Si j'écris DEBUG ON, on discute du problème sans rien modifier
  jusqu'à DEBUG OFF.
