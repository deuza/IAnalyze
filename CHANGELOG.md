# Changelog

Toutes les modifications notables d'IAnalyze sont consignées
dans ce fichier.

Le format suit [Tenez un Changelog](https://keepachangelog.com/fr/1.1.0/)
et le projet applique le [versionnage sémantique](https://semver.org/).

## [Unreleased]

### Added - 2026-11-21

Icône de la licence CC-0

### Changed

- The comments and docstrings of `ianalyze.py`, `verifier-analyse.py`
  and `test-app.sh`, and the comments of `.gitignore`, are in English.
  The code is unchanged: the Python syntax trees, docstrings set aside,
  and the shell code, comments set aside, are identical to those of
  version 4.0.2.
- The messages that `ianalyze.py` writes on standard error are in
  English: progress log, warnings, errors, and the command line help
  with its option descriptions, group titles, placeholders and
  examples. A warning now starts with "Warning" instead of
  "Attention". The options keep their names for now, and the messages
  quote them as they are.

## [4.0.2] - 2026-11-21

### Added

- `parties-exemples/partie-lichess-org.pgn` : une vraie partie
  anonymisée, telle que Lichess l'exporte sans l'analyse du site. C'est
  celle des essais du 21 novembre 2026, que le README décrit en
  section 7.

### Changed

- README : Lichess est présenté comme la source de référence du
  script, avec ses deux exemples, l'export simple et l'export commenté.

## [4.0.1] - 2026-11-21

### Added

- `parties-exemples/` : quatre vraies parties anonymisées, telles que
  les exportent Chess.com, chess-mail.com, ajedrezmail.org et Lucas
  Chess. Avec celle de Lichess, elles montrent les exports essayés, que
  le README énumère.

### Fixed

- Un PGN dont le résultat est écrit deux fois en fin de fichier, comme
  ceux de chess-mail.com, était refusé pour "2 parties" : python-chess
  lit dans le second résultat une partie sans balise ni coup. Elle est
  maintenant ignorée, et le journal le dit. Un fichier qui réunit
  vraiment plusieurs parties reste refusé.

## [4.0.0] - 2026-11-21

Première version publiée depuis la 3.5.8. Elle réunit le travail des
versions 3.5.9 à 3.8.0, restées sur la branche de développement et
jamais publiées.

### Added

- Prompt d'analyse écrit à côté de l'archive, sous le nom
  `<archive>.prompt.txt`, à coller dans la conversation avec l'archive
  en pièce jointe. Il est tiré d'un modèle, `prompt-modele.txt`, rangé
  à côté du script et modifiable sans toucher au code : le script y
  remplit les valeurs (pseudo, camp, niveau, cadence, nom de l'archive)
  et ne garde que les passages qui s'appliquent (base interrogée,
  explorateur ou non, réponses recueillies ou non). Le prompt décrit
  ainsi toujours la synthèse que cette version vient d'écrire.
- Repères du modèle : `{{NOM}}` pour une valeur, et les directives
  `#! si`, `#! si non`, `#! sinon`, `#! fin` et `#! note`. Le modèle est
  contrôlé avant la collecte : un repère inconnu ou mal écrit, une
  condition jamais fermée ou un modèle sans une ligne de texte arrêtent
  le script, avec le numéro de la ligne. `TECHNIQUE.md`, section 12,
  donne la liste des valeurs et des conditions.
- Options `--prompt FICHIER`, pour un autre modèle, et `--sans-prompt`.
- Option `--prompt-seul` : un prompt court, à coller seul dans la
  conversation, sans pièce jointe. Il tient en quelques consignes, la
  partie et les évaluations de Stockfish, une ligne par demi-coup, le
  meilleur coup et sa suite derrière chaque coup faible. C'est la
  route à prendre avec un compte gratuit, ou avec un LLM qui n'ouvre
  pas les zip ou n'exécute pas de code, sur le modèle du prompt
  d'analyse de Lucas Chess, avec les chiffres du moteur en plus. Il
  est tiré d'un modèle à part,
  `prompt-seul-modele.txt`. Aucune archive n'est alors écrite : le
  prompt est le seul fichier produit, sauf avec `--garder-dossier`, qui
  laisse le dossier de travail à `verifier-analyse.py`. Son bilan
  demande les trois erreurs les plus coûteuses du joueur : quand le
  tableau du moteur marque moins de trois coups faibles de son côté,
  le prompt en donne le nombre et demande de s'en tenir à ceux-là :
  un LLM à qui l'on en réclame trois en invente une. Valeur
  `COUPS_FAIBLES_JOUEUR` et conditions `PEU_DE_COUPS_FAIBLES` et
  `AUCUN_COUP_FAIBLE` pour les modèles personnels. Sans aucun coup
  faible, le prompt demande de ne prêter aucune erreur au joueur.
  Quand son camp n'est pas connu, il demande de commenter les deux
  camps de la même façon et de donner le bilan pour chacun.
- `verifier-analyse.py`, qui contrôle le PGN annoté rendu par un LLM en
  le comparant à l'archive qu'il a reçue : lecture, ligne principale,
  format, erreurs et gaffes commentées, évaluations citées, variantes,
  positions citées dans la conversation. Il nomme les pièges relevés
  sur de vrais PGN de LLM, dont la ligne vide dans le corps de la partie
  et la variante écrite à l'intérieur d'un commentaire, qu'il rejoue
  lui-même. Il ne juge pas la qualité du commentaire. Son option
  `--prompt-seul` contrôle un PGN rendu d'après le prompt court, qui ne
  demande ni résumé, ni lignes de 79 caractères, ni NAG, ni tiret
  cadratin, ni FEN. Son option `--perimetre N` borne le contrôle des
  erreurs et gaffes commentées au périmètre convenu avec le LLM. Sans
  elle, le périmètre est lu dans la réponse du joueur à la question de
  démarrage. Un mat cité, `#+2` ou `#2`, est contrôlé comme les autres
  évaluations. Dans un dossier qui contient plusieurs collectes, seule
  une collecte complète est retenue, et nommée : s'il y en a plusieurs,
  le script s'arrête plutôt que d'en choisir une.
- Fichier de réglages, `~/.config/IAnalyze/reglages.ini`, au format
  INI : il garde vos pseudos, votre cadence habituelle et votre niveau
  en points Elo, plus un réglage facultatif `annotateur`. Les clefs
  absentes sont demandées une seule fois, au premier lancement sur un
  terminal. Hors terminal, rien n'est demandé ni écrit.
- Options `--reglages FICHIER`, pour désigner un autre fichier, et
  `--purge-reglages`, qui le supprime puis quitte. Seul un fichier qui
  porte la section `[joueur]`, ou un fichier vide, est supprimé : une
  faute de frappe derrière `--reglages` ne détruit pas un autre
  fichier.
- Cadence saisie par des questions vérifiées, et non plus en texte
  libre : temps réel, correspondance ou inconnue, puis les minutes par
  joueur et l'incrément en secondes. La correspondance connaît trois
  systèmes : un délai fixe en jours par coup (Lichess, chess.com), un
  nombre de coups par période, comme "10 coups en 50 jours" (cadence
  standard de l'ICCF), ou un capital de temps avec incrément, plafond
  et réserve facultatifs (chess-mail.com, Triple Block de l'ICCF). Les
  deux derniers suivent les ICCF Rules en vigueur depuis le 1er
  janvier 2026. Le script rédige lui-même la phrase transmise à
  l'analyste, avec la catégorie de Lichess, calculée comme le fait
  Lichess sur le temps initial plus quarante fois l'incrément.
- Une balise `TimeControl` de la forme `600+5` ou `300` est citée, puis
  traduite : "soit rapide, 10 minutes + 5 secondes par coup".
- Sans pseudo connu, le script demande votre nom de joueur quand votre
  balise est vide, comme il le fait pour l'adversaire. Hors terminal,
  le camp du joueur se déduit de ses pseudos, sans question.
- Synthèse : sous le tableau de Stockfish, une ligne "Résultat et
  évaluation finale se contredisent" quand le camp déclaré vainqueur
  est moins bien d'au moins 300 cp après le dernier coup. La partie ne
  s'est alors pas décidée sur l'échiquier, et le prompt demande à
  l'analyste de le dire.
- `collecte.json` : clef `prompt_ecrit`, et les pseudos réellement
  utilisés.
- `parties-exemples/`, les fichiers cités dans `EXEMPLES.md` : les
  parties des exemples, les PGN que le script refuse, trois PGN annotés
  pour le vérificateur, et une vraie partie anonymisée, exportée de
  Lichess avec ses commentaires, pour un premier essai.
- `test.pgn`, partie d'essai qui réunit les cas tordus d'un PGN :
  balises accentuées, commentaires de toutes sortes, NAG, variantes
  emboîtées, mat manqué, prise en passant, promotion, les deux roques
  et un coup nul.
- `test-app.sh`, qui joue la suite de tests d'un seul coup et écrit un
  rapport, sous Linux comme sous macOS : `sh test-app.sh` hors réseau,
  `sh test-app.sh --reseau PARTIE` avec un jeton et une partie de
  Lichess de votre choix. Le dépôt ne cite aucune partie réelle : sans
  partie, le test de téléchargement est sauté.
- `.gitignore` : rapports de `test-app.sh`, archives, dossiers de
  travail et prompts produits dans le dépôt.

### Changed

- Le script s'appelle `ianalyze.py`, du nom du projet, au lieu de
  `collecte-partie.py`. La commande devient
  `./ianalyze.py ma-partie.pgn`.
- Stockfish est obligatoire : son évaluation fait partie de toute
  collecte. Une synthèse sans chiffres du moteur laissait l'analyste
  estimer seul, ce qui n'est pas le but du projet.
- Emplacements par défaut, les mêmes sous Debian et sous macOS, tous
  dans le répertoire personnel : environnement virtuel dans
  `~/.local/share/IAnalyze/venv`, catalogue dans
  `~/.local/share/IAnalyze`, réglages dans `~/.config/IAnalyze`. Sous
  Debian, seuls les paquets demandent encore les droits root. Les
  anciens emplacements étaient `/opt/venv/lichess`,
  `/usr/local/share/collecte-partie` et
  `~/.local/share/collecte-partie`.
- En-tête d'agent HTTP : `IAnalyze/4.0.0`, suivi de l'adresse du dépôt.
- `--pseudos` n'a plus de valeur par défaut dans le code : sans
  l'option, les pseudos viennent du fichier de réglages. Donnée, elle
  l'emporte toujours.
- Un PGN qui contient plusieurs parties est refusé, avec leur nombre.
  Jusqu'ici la première était analysée après un simple avertissement.
- Un PGN qui ne part pas de la position initiale, donc qui porte une
  balise FEN, est refusé. IAnalyze analyse une partie entière, du
  premier coup au dernier.
- Un PGN dont l'encodage n'est ni UTF-8, ni UTF-16, ni cp1252 est
  refusé, avec le conseil de le convertir. Il était lu en latin-1, et
  ses lettres accentuées retirées comme des caractères de contrôle.
- `--profondeur` est bornée à 60. Une valeur démesurée, par faute de
  frappe, occupait le moteur sans jamais rendre la main.
- Questions de démarrage : une réponse fait 255 caractères au plus, et
  un nom de joueur ne peut plus contenir de guillemet, de barre oblique
  inversée, de crochet ni d'accolade. Un tel nom donnait un
  `partie.pgn` non conforme. La question est reposée.
- Nom de l'archive : les espaces du nom du PGN y deviennent des tirets,
  `partie contre machin.pgn` donne `analyse-partie-contre-machin-...`.
- Le modèle du prompt, `prompt-modele.txt`, remplace
  `INSTRUCTIONS.txt`, qui était un texte à coller tel quel. Le prompt
  demande à l'analyste de se servir de tous les fichiers de l'archive,
  et les décrit un par un. Il ne suppose plus que l'analyste exécute du
  code : celui qui n'en exécute pas écrit le PGN lui-même, l'annonce,
  et n'invente ni résultat d'exécution ni évaluation chiffrée.
- Prompt : consignes ajoutées après des essais sur quatre LLM, chacune
  répondant à un défaut relevé sur un PGN réellement rendu. Aucune
  ligne vide dans le corps de la partie, variantes écrites hors des
  accolades, ne jamais annoncer un fichier qui n'a pas été créé, ne
  jamais rendre un PGN sans commentaires au motif qu'un fichier manque.
  La coupe des commentaires passe de 76 à 75 colonnes, pour que les
  lignes exportées tiennent en 79 caractères.
- Documentation en Markdown, en quatre fichiers. `README.md` remplace
  `README.nfo` et s'en tient à l'installation et à l'usage courant.
  `EXEMPLES.md` est l'aide-mémoire, bâti comme une page de manuel :
  toutes les commandes, toutes les options, et ce que le terminal
  affiche. `TECHNIQUE.md` explique le fonctionnement du script, son
  emploi depuis un autre programme, le détail des fichiers produits,
  les encodages et le modèle de prompt. `TESTS.md` remplace
  `TESTS.nfo` : comment lancer les tests, puis un tableau qui donne,
  test par test, ce qui est vérifié. Le README conseille Claude, avec le zip et le prompt
  comme avec `--prompt-seul`, compte gratuit compris, et rend compte de
  deux séries d'essais sur quatre LLM : le 20 novembre 2026 avec le
  zip, le 21 avec le prompt court. Il en tire une règle de lecture :
  les chiffres tiennent, les récits sont à vérifier sur l'échiquier.

### Removed

- Options `--avec-stockfish` et `--sans-stockfish` : le moteur est
  toujours appelé. La clef `avec_stockfish` de `collecte.json`
  disparaît aussi.
- Option `--consignes`, qui insérait un fichier de votre main en tête
  de la synthèse. Elle datait d'avant le prompt, quand la synthèse était
  le seul fichier remis au LLM. Le prompt porte désormais les consignes
  d'analyse, et vos réponses aux questions de démarrage le contexte de
  la partie.
- Le pseudo et la cadence personnels de l'auteur, jusqu'ici valeurs par
  défaut du script. Les exemples de l'aide et de la documentation
  emploient des pseudos neutres.
- `INSTRUCTIONS.txt`, `README.nfo` et `TESTS.nfo`, remplacés par les
  fichiers cités plus haut.

### Fixed

- Mats : le nombre de coups était celui d'avant le coup. Dans un
  tableau qui donne l'évaluation après chaque coup, le camp qui mate
  affichait un coup de trop : `#+2` après un échec qui ne laissait
  qu'un coup, `#+1` sur le coup du mat lui-même. Le compte se lit
  maintenant après le coup, `#+0` ou `#-0` désignant le coup qui donne
  mat. Les centipions, les écarts et la nature des coups ne changent
  pas.
- Une partie notée en français, en figurines ou en minuscules était
  analysée de travers sans aucun message : python-chess écarte la lettre
  qu'il ne connaît pas, et "Cf3" devenait "f3", un coup de pion. Le
  corps de la partie est maintenant contrôlé avant la lecture, et le
  premier mot qui n'est pas un élément de PGN arrête le script.
- Un commentaire dont l'accolade n'est jamais fermée tronquait la
  partie en silence. Il est refusé, comme une parenthèse de variante
  jamais fermée ou fermée en trop.
- Explorateur : un coup nul, `--` dans le PGN, ressortait dans la table
  à 0.0 % et était désigné comme la première sortie de théorie, ou
  provoquait un HTTP 400 de Lichess. L'interrogation s'arrête désormais
  au coup nul, sans requête pour ce demi-coup, et la section 4 de la
  synthèse le liste.
- Explorateur : une erreur HTTP dont le corps arrive coupé, ou une
  réponse imbriquée à l'excès, faisait avorter toute la collecte. Seule
  l'interrogation s'arrête maintenant, et Stockfish fait son travail.
  Un compte de parties négatif ou démesuré est tenu pour absent.
- Plusieurs entrées finissaient en "Erreur inattendue" au lieu du
  message prévu : du texte libre après la partie, l'entrée standard
  fermée par l'appelant, un nom de fichier trop long, une URL aux
  crochets mal placés, un moteur qui s'arrête hors d'une recherche.
- Source : une adresse au schéma en majuscules, `HTTPS://`, était prise
  pour un fichier. Une rubrique de Lichess de huit lettres, `Analysis`
  ou `features`, et un répertoire local de huit lettres étaient pris
  pour des identifiants de partie, et une requête partait.
- Chemins : `--sortie='~/analyses'` créait un répertoire nommé `~`, et
  `--stockfish` ne développait pas le tilde. Un moteur désigné par son
  nom nu était contrôlé dans le répertoire courant, puis lancé depuis
  le PATH.
- Un PGN au nom long, écrit en caractères de plusieurs octets, faisait
  échouer l'écriture de l'archive après toute l'analyse.
- Synthèse : entre deux mats de même sens, la colonne "Écart cp"
  affichait 1, lu comme un centipion. Elle affiche 0, et la légende dit
  ce que vaut un écart négatif. Le titre d'une partie sans balise Site
  est "partie locale" et non "?".
- Un fichier de jeton écrit `LICHESS_TOKEN=...` ou entre guillemets
  passait la lecture, et Lichess répondait 401 : il est refusé avec un
  message clair.
- Sur une partie qui contient un coup nul, le journal répétait à
  chaque position suivante un avis de python-chess. Sans conséquence
  sur les évaluations, il est écarté.

### Security

- Le jeton Lichess ne suit plus une redirection HTTP. Si l'explorateur
  répondait 301, 302, 303, 307 ou 308, l'en-tête Authorization partait
  avec la requête vers la nouvelle adresse, quel qu'en soit l'hôte. La
  redirection est maintenant refusée et l'interrogation s'arrête.
- Le jeton est retiré de la réponse de l'explorateur avant qu'elle soit
  gardée dans l'archive, au cas où un serveur renverrait l'en-tête reçu.

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

Historique reconstitué à partir des conversations des 8 et 9 octobre 2026.
La numérotation des étapes intermédiaires n'a pas été conservée :
leurs changements sont regroupés ici, sous la version que porte l'en-tête
d'agent du script.

### Added

- `--base {lichess,maitres}` : interrogation de la base de l'ensemble des
  joueurs Lichess, celle de <https://lichess.org/opening>, en plus de la
  base maîtres.
- `--cadences` et `--classements` : filtres de la base Lichess, avec les
  défauts de <https://lichess.org/opening> et les parties depuis
  janvier 2017.
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
