# IAnalyze, les essais des LLM

English version: [TRIALS.md](TRIALS.md)

Le conseil du README, section [Choisir un LLM](../README.fr.md#4-choisir-un-llm), s'appuie sur ces essais. Chacun a envoyé la même partie à plusieurs LLM, avec le zip et le prompt complet, ou avec le prompt court de `--prompt-only`.

## Sommaire

- [Comment les essais ont été menés](#comment-les-essais-ont-été-menés)
- [Le 20 novembre 2026, avec le zip et le prompt](#le-20-novembre-2026-avec-le-zip-et-le-prompt)
- [Le 21 novembre 2026, avec `--prompt-seul`, aujourd'hui `--prompt-only`](#le-21-novembre-2026-avec---prompt-seul-aujourdhui---prompt-only)
- [Le 25 novembre 2026, avec le zip et le prompt anglais](#le-25-novembre-2026-avec-le-zip-et-le-prompt-anglais)
- [Le 26 novembre 2026, les deux routes, avec les prompts anglais](#le-26-novembre-2026-les-deux-routes-avec-les-prompts-anglais)
- [Le 27 novembre 2026, les deux routes, avec les prompts publiés](#le-27-novembre-2026-les-deux-routes-avec-les-prompts-publiés)

---

## Comment les essais ont été menés

Quatre séries et un essai isolé, un seul essai par LLM, par offre et par route, une partie à chaque fois.

Les deux premières séries d'essais ont été menées avec la version 4.0, dont les prompts étaient en français. Les prompts anglais de la version 5.0.0 sont passés par un essai isolé, puis par une troisième série, les 25 et 26 novembre 2026, et par une quatrième avec les prompts publiés, le 27 novembre 2026, qui vont dans le même sens.

**Ce n'est pas un banc d'essai.**\
Un essai ne dit rien de la régularité d'un modèle. Mais les séries vont dans le même sens, et le conseil du README ne s'appuie sur rien d'autre que ce qui a été vu.

**Les autres LLM n'ont été essayés que sur leur offre gratuite.**\
ChatGPT, Gemini et Copilot n'ont jamais été essayés sur une offre payante. Leurs modèles payants pourraient bien être plus précis, comme Claude l'a été sur son abonnement les 21 et 27 novembre 2026, mais ces essais ne permettent pas de le dire.

**Comment chaque réponse est jugée.**\
Chaque PGN rendu passe par `verify-analysis.py`, contre le dossier de travail de sa collecte. Ses récits sont ensuite contrôlés sur l'échiquier, un à un, avec python-chess : seuls comptent les faits, prises, échecs, attaques, défenses, matériel, cases, pendules, chiffres de la base, jamais les opinions. Les erreurs citées dans les tableaux ont été revérifiées ainsi. **Les listes ne sont pas exhaustives.**

**Ce que toutes les réponses partagent.**\
Les quatorze réponses au prompt court, sur trois séries, ne citent aucune évaluation que le tableau ne contienne pas. Treize ont rendu la partie entière, tous les coups commentés ; le 27 novembre 2026, Gemini a changé un coup et commenté 39 demi-coups sur 49.

## Le 20 novembre 2026, avec le zip et le prompt

Une partie de 49 demi-coups, le même zip et le même prompt pour tous, celui de la version 4.0.0, avant les consignes et l'option `--prompt-seul`, aujourd'hui `--prompt-only`, que ces essais ont fait ajouter.

| LLM, tel qu'il se nomme lui-même | Offre | PGN rendu | Bilan de `verify-analysis.py` |
|---|---|---|---|
| Claude Opus 5.5 (Anthropic) | abonnement | oui, construit avec python-chess | aucun échec : 24 erreurs et gaffes commentées sur 24, 27 variantes jouables |
| GPT-6 (OpenAI) | gratuite | oui, écrit à la main, python-chess n'ayant pas pu être installé | 3 échecs : une ligne vide arrête la lecture, les 25 variantes sont dans les commentaires, un NAG contredit le moteur |
| M365 Copilot (Microsoft) | gratuite | oui, la partie sans aucun commentaire | 3 échecs : il dit n'avoir trouvé que trois fichiers dans l'archive, et ne commente rien |
| Gemini (Google), version non relevée | gratuite | non | il annonce un fichier qui n'existe pas, puis perd le fil de la conversation |

Ce que cette série montre :

- **Les données tiennent partout.** Aucun des quatre n'a inventé une évaluation, et tous donnent les trois mêmes erreurs principales, avec les bons écarts.
- **C'est la fabrication du PGN qui les sépare.** Seul le LLM qui a construit son fichier avec python-chess a rendu un PGN utilisable tel quel.
- **Le fond peut être bon sous une forme fautive.** Les 25 variantes écrites à la main par GPT-6 étaient toutes légales et tirées des lignes du moteur.
- **La partie était notée gagnée dans une position perdue.** Deux LLM sur quatre ont raconté une victoire méritée, d'où la ligne ajoutée à la synthèse (voir [TECHNICAL.fr.md](TECHNICAL.fr.md), section 10).

L'offre gratuite de Claude annonce elle aussi la création de fichiers et l'exécution de code, sur d'autres modèles que celui de cet essai, d'après [sa page de tarifs](https://claude.com/pricing), lue le 20 novembre 2026 et de nouveau le 25 novembre 2026.

Elle a été essayée avec le fichier zip le 27 novembre 2026, plus bas.

## Le 21 novembre 2026, avec `--prompt-seul`, aujourd'hui `--prompt-only`

Une partie de 39 demi-coups, gagnée par le joueur, et le même prompt court collé seul dans cinq conversations. C'est `example-games/game-lichess-org.pgn`.\
Le tableau du moteur y marque dix coups faibles, dont deux du joueur.

Les cinq réponses ont en commun l'essentiel :

- La ligne principale est recopiée sans un coup changé
- Les 39 demi-coups sont commentés, toutes les erreurs et gaffes du tableau comprises
- 126 évaluations sont citées dans les PGN, toutes tirées du tableau

Ce qui les sépare :

| LLM | Offre | Forme du PGN | Sur l'échiquier |
|---|---|---|---|
| Claude Sonnet 5.5 (Anthropic) | abonnement | conforme : bloc de code, balises intactes, 10 suites jouables sur 10 | aucune erreur trouvée |
| Claude Sonnet 5.5 (Anthropic), effort Max | gratuite | conforme, de même | une erreur : une case de fuite annoncée au roi alors qu'elle est battue |
| ChatGPT (OpenAI), version non relevée | gratuite | les suites sont écrites dans les commentaires, aucune n'est jouable. Dix suffixes `?!` ou `??` ajoutés aux coups, cinq balises HTML dans les commentaires | un sacrifice qui n'en est pas un, le mauvais cavalier nommé sur une prise, un mat en un annoncé pour un mat en deux |
| Gemini (Google), version non relevée | gratuite | 7 suites jouables sur 10. Il parle du joueur à la troisième personne, puis écrit deux fois "erreur de ma part" à sa place | le même faux sacrifice, la couleur des fous inversée sur trois coups, une colonne annoncée ouverte qui ne l'est pas |
| Copilot (Microsoft), version non relevée | gratuite | pas de bloc de code : la balise Site est rendue sous la forme d'un lien HTML. 10 suites jouables sur 10 | le même faux sacrifice, et un cavalier laissé en prise que rien ne signale |

Les erreurs de la dernière colonne ont été vérifiées une à une sur la position, avec python-chess. **La liste n'est pas exhaustive.**

Ce que cette série montre :

- **Le prompt court fait le travail.** Sans pièce jointe et sans exécution de code, les cinq réponses sont lisibles et leurs chiffres sont justes. C'est mieux que ce que la chaîne complète avait donné la veille chez les trois autres LLM.
- **Claude est devant sur les deux offres.** Ses deux PGN sont conformes, et ses explications sont celles qui résistent le mieux à la vérification : aucune erreur trouvée d'un côté, une seule de l'autre. Le compte gratuit fait presque jeu égal avec l'abonnement, en deux fois plus long : 1968 mots de commentaires contre 943.
- **Le même piège a pris trois LLM sur quatre.** Un fou prend un pion en h7 avec échec, défendu par sa dame : le roi ne peut pas le reprendre. ChatGPT, Gemini et Copilot parlent de sacrifice. Claude écrit, dans l'essai du compte gratuit, "ici il n'y a aucun sacrifice, le pion tombe gratuitement". Les essais ont été menés en français.
- **Demander trois erreurs en fait inventer une.** Le joueur n'en avait commis que deux. ChatGPT, Gemini et Copilot en ont présenté une troisième, Claude a répondu les deux fois qu'il n'y en avait que deux. Les deux prompts donnent désormais le nombre réel de coups faibles du joueur (voir [TECHNICAL.fr.md](TECHNICAL.fr.md), section 12).
- **Le vérificateur n'aurait presque rien vu.** En mode `--prompt-only`, il contrôle les balises, la ligne principale et les chiffres cités. Les suites écrites dans le texte, les balises HTML et les récits faux passent : c'est à vous de les relire.

## Le 25 novembre 2026, avec le zip et le prompt anglais

Un essai isolé, le premier des prompts anglais de la version 5.0.0, avant leur publication.\
Une partie par correspondance de 39 demi-coups, gagnée par le joueur, envoyée avec son zip à GPT-6 (OpenAI), sur l'offre gratuite.

- Il a annoncé le cas B, python-chess n'ayant pas pu être installé, et a écrit son PGN à la main. Les chiffres de sa réponse sont tous justes.
- `verify-analysis.py` finit sur 2 échecs : une variante placée après le coup qu'elle devait remplacer, `( 19... Kg8 20. Qh7# )` après 19.Qh5+, y est illégale, et python-chess arrête la lecture de la ligne principale au demi-coup 37 sur 39. Sans cette variante, le PGN passe sans un échec.
- Ses trois erreurs les plus coûteuses étaient celles de l'adversaire, et `$7`, coup forcé, était posé sur l'échec au lieu de la réponse.
- Il a mis `$6` sur sept coups que le moteur ne classe pas.

Ces quatre points ont amené les derniers changements de la version 5.0.0 : les prompts disent où commence une variante, où va `$7` et de qui donner les erreurs, et le vérificateur range ces NAG parmi les autres avis.

Les prompts ont encore changé le 27 novembre 2026, après ces essais : les notes du joueur sont gardées, les commandes d'un site retirées, la partie du prompt court tient dans un bloc de code, et le bilan s'en tient au périmètre convenu.\
Ces dernières consignes sont passées par la série du 27 novembre 2026, plus bas.

## Le 26 novembre 2026, les deux routes, avec les prompts anglais

Une partie par correspondance de 54 demi-coups, perdue par le joueur, mat au 27e coup, et les prompts anglais de la version 5.0.0, avant leur publication.\
Les limites d'usage des offres gratuites ne permettaient pas les deux routes : ChatGPT, Gemini et Copilot n'ont reçu que le prompt court, et Claude, sur l'abonnement, les deux.

La partie a été collectée une fois par route, à deux heures d'intervalle. Les évaluations de Stockfish varient d'une exécution à l'autre : le tableau du prompt court marque 12 erreurs et gaffes, dont 7 du joueur, et l'archive 11.

| LLM | Offre, route | Bilan de `verify-analysis.py` | Sur l'échiquier |
|---|---|---|---|
| Claude Sonnet 5.5 (Anthropic), effort Max | abonnement, zip | aucun échec, aucun avertissement : les 11 erreurs et gaffes commentées, 17 variantes jouables, les 59 évaluations citées toutes retrouvées | aucune erreur trouvée |
| Claude Sonnet 5.5 (Anthropic), effort Max | abonnement, `--prompt-only` | aucun échec : bloc de code, balises intactes, les 54 demi-coups commentés, 19 variantes jouables, les 91 évaluations citées toutes retrouvées | aucune erreur trouvée |
| Gemini (Google), version non relevée | gratuite, `--prompt-only` | aucun échec : bloc de code, balises intactes, les 54 demi-coups commentés, 18 variantes jouables, les 56 évaluations citées toutes retrouvées | la couleur des fous confondue deux fois, un fianchetto préparé sans plus aucun fou, l'aile dame dite développée avec le fou de c1 encore chez lui |
| ChatGPT (OpenAI), version non relevée | gratuite, `--prompt-only` | 1 échec : les 19 variantes sont écrites dans les commentaires, aucune n'est jouable. Douze suffixes `?` ou `??` ajoutés aux coups | une pièce de moins annoncée comme égalité matérielle, un échec qui n'en est pas un, une reprise dite forcée alors que l'autre tour pouvait prendre |
| Copilot (Microsoft), version non relevée | gratuite, `--prompt-only` | 1 échec : la balise Site rendue sous la forme d'un lien HTML. Pas de bloc de code, 18 variantes jouables | une pièce de moins annoncée deux fois comme égalité matérielle, trois coups dits forcés alors que d'autres étaient légaux |

Les erreurs de la dernière colonne ont été vérifiées une à une sur la position, avec python-chess. **La liste n'est pas exhaustive.**

Ce que cette série montre :

- **Les prompts anglais font le travail.** Trois des cinq réponses citent des évaluations, 206 en tout, toutes retrouvées dans les données du moteur ; ChatGPT et Copilot n'en citent aucune. Chaque réponse commente toutes les erreurs et gaffes de son tableau.
- **Les erreurs du joueur, et les siennes seulement.** Les cinq bilans donnent trois erreurs du joueur, aucune de l'adversaire. Avec le zip, Claude a même écarté les deux plus coûteuses selon les chiffres, 21.Qb1 et 22.Kh2, jouées dans une position déjà perdue, et a dit pourquoi.
- **Le point de départ d'une variante est compris.** Les 91 variantes des cinq réponses, celles de ChatGPT comprises, sont légales et tirées des lignes du moteur, et aucune ne recopie les coups joués.
- **Les offres gratuites gardent leurs défauts du 21 novembre.** ChatGPT écrit toujours les variantes dans les commentaires et ajoute des suffixes aux coups, Copilot ne rend toujours pas de bloc de code et change la balise Site en lien. Gemini passe le vérificateur, pas la vérification sur l'échiquier.
- **Claude se vérifie lui-même.** Avec le prompt court, il dit avoir rejoué ses variantes avec python-chess et contrôlé ses explications avec Stockfish, ce que le prompt ne demande pas. Il y commente chaque coup, en 2178 mots ; avec le zip, 18 coups, comme le demande le prompt complet, en 1062 mots.
- **Le vérificateur ne juge pas les récits.** Gemini le passe sans un échec, avec quatre erreurs sur l'échiquier.

## Le 27 novembre 2026, les deux routes, avec les prompts publiés

La partie est [`example-games/player-notes.pgn`](../example-games/player-notes.pgn), 49 demi-coups, notée 1-0 dans une position perdue pour le joueur : `commented-game.pgn` sans l'analyse de Lichess, ses pendules gardées, et trois notes du joueur ajoutées.\
Elles éprouvent les dernières consignes : l'une cite un pourcentage, "I was 80% sure", une autre fait de 9.Nb5 le meilleur coup de la partie, une gaffe pour le moteur, et la dernière est en français, "Ici je pensais gagner une pièce".

La partie a été collectée une fois par route : le tableau du zip marque 22 erreurs et gaffes, celui du prompt court 23.\
Le zip est allé à Claude sur les deux offres, le prompt court aux cinq.

| LLM | Offre, route | Bilan de `verify-analysis.py` | Notes et pendules | Sur l'échiquier |
|---|---|---|---|---|
| Claude Sonnet 5.5 (Anthropic), effort Max | abonnement, zip | aucun échec, aucun avertissement : les 22 erreurs et gaffes commentées, 23 variantes jouables, les 62 évaluations citées toutes retrouvées | les trois notes gardées, le pourcentage écrit "80 percent", les pendules retirées ; à 9.Nb5, "Stockfish disagrees" | une erreur, dans le bilan final : 9.axb4 présenté comme "a free bishop", alors que le cavalier a6 le défend |
| Claude Sonnet 5.5 (Anthropic), effort High | gratuite, zip | aucun échec, aucun avertissement : les 22 erreurs et gaffes commentées, 23 variantes jouables, les 33 évaluations citées toutes retrouvées. Le quota s'est épuisé avant le bilan final | les trois notes gardées, le pourcentage écrit "80 percent", les pendules retirées ; la note de 9.Nb5 réfutée sur l'échiquier, la note en français citée, puis traduite | 9.axb4 "a clean piece", alors qu'il gagne un fou contre un pion ; après 11.Ne4, "a piece down for the rest of the game", alors que le matériel redevient égal après 23...Bxb8 |
| Claude Sonnet 5.5 (Anthropic), effort Max | abonnement, `--prompt-only` | aucun échec : les 49 demi-coups commentés, 31 variantes jouables, les 113 évaluations citées toutes retrouvées | les trois notes gardées telles quelles, les pendules retirées ; "Stockfish disagrees with your note" à 9.Nb5 et 11.Ne4 | aucune erreur trouvée |
| Claude Sonnet 5.5 (Anthropic), effort Max | gratuite, `--prompt-only` | aucun échec : les 49 demi-coups commentés, 31 variantes jouables, les 54 évaluations citées toutes retrouvées | les trois notes gardées telles quelles, les pendules retirées ; à 9.Nb5, "the table has a different view" | 3.g4 "before a single piece is developed", alors que Nf3 est sorti ; 4.Nfd2 "leaves your h-pawn loose", alors que Rh1 le défend ; le fou de 8...Bb4 "free", deux fois |
| ChatGPT (OpenAI), version non relevée | gratuite, `--prompt-only` | aucun échec : les 49 demi-coups commentés, 28 variantes jouables | aucune des trois notes gardée telle quelle : deux paraphrasées, celle de 9.Nb5 supprimée ; les pendules retirées | 12...e3 "a passed pawn", alors que le pion e2 se tient devant lui ; 13.O-O "connecting your rooks", avec Bc1 et Qd1 entre elles ; 16...gxf4 "opening the f-file", alors qu'il ouvre la colonne g ; 23.Nxb8 "a rook won", alors qu'il gagne la qualité ; un matériel égal présenté comme un avantage noir |
| Gemini (Google), version non relevée | gratuite, `--prompt-only` | 1 échec : 22...Qd7 changé en 22...Qe7. 39 demi-coups commentés, les 20 variantes écrites dans les commentaires | aucune des trois notes gardée, les pendules retirées | 8...Bb4 "a pin", alors qu'aucune pièce n'est clouée ; 24...Nxg2 "recaptures", après un coup qui n'avait rien pris ; un matériel égal à la fin présenté comme un gros avantage noir |
| Copilot (Microsoft), version non relevée | gratuite, `--prompt-only` | 5 échecs : la copie de sa réponse tient tout le PGN sur une ligne, balises comprises. Remis sur des lignes séparées : aucun échec, les 49 demi-coups commentés, 15 variantes jouables | les trois notes gardées, avec leurs pendules | 4.Nfd2 "attacks the bishop", que rien n'attaque ; 12...e3 "a passed pawn" ; 21.Nxa7 attaquant les tours, que rien n'attaque |

Les erreurs de la dernière colonne ont été vérifiées une à une sur la position, avec python-chess. **La liste n'est pas exhaustive.**

Ce que cette série montre :

- **Les notes du joueur passent chez Claude et Copilot.** Claude les garde dans ses quatre réponses, avant son propre commentaire, et contredit la note de 9.Nb5, trois fois au nom du moteur, une fois sur l'échiquier. Avec le zip, il écrit le pourcentage en toutes lettres et traduit la note en français après l'avoir citée. Copilot les garde aussi, ChatGPT en paraphrase deux et supprime la troisième, Gemini n'en garde aucune. Le vérificateur les compte, "0 kept out of 3" pour ChatGPT, sans en faire un échec.
- **Les pendules sont retirées, sauf par Copilot**, qui garde les trois qui accompagnaient les notes.
- **Un coup changé, pour la première fois dans ces essais.** Gemini rend 22...Qe7 au lieu de 22...Qd7. La partie reste légale jusqu'au bout : seul le vérificateur le voit.
- **Le zip passe sur une offre gratuite.** Claude a rendu un PGN complet, avec son résumé, ses 22 erreurs et gaffes commentées et ses 23 variantes. Le quota de jetons s'est épuisé avant le bilan final : il revient plein au bout de six heures environ, d'après l'auteur, si bien qu'un joueur qui n'est pas pressé peut avoir toute l'analyse sans payer.
- **Claude reste devant.** Ses quatre réponses tiennent leurs chiffres, et avec le zip sur l'abonnement, ses pendules, ses chiffres de la base, son matériel et ses FEN sont tous justes. Avec le prompt court sur l'abonnement, aucune erreur n'est trouvée sur l'échiquier. Les trois autres disent à un moment le fou de 8...Bb4 gratuit, alors que le cavalier a6 le défend : le prendre coûte un pion.
- **ChatGPT a changé de forme, pas de récits.** Pour la première fois, ses variantes se tiennent hors des commentaires, toutes jouables, et le vérificateur ne trouve aucun échec. Ses récits gardent leurs erreurs, dont deux partagées : le pion e3 dit passé, avec Copilot, et un matériel égal présenté comme un avantage noir, avec Gemini.
- **Le vérificateur ne juge pas les récits.** ChatGPT le passe sans un échec, avec cinq erreurs sur l'échiquier dans le tableau.
