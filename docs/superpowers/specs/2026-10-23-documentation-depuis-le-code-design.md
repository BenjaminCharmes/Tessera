# La documentation par lot se lit dans le code livré

Conception du ticket-535. Décision : ADR-057, qui amende ADR-035.

## Problème

`_brief` (`services/documentation.py`) donne à `doc-technique` et
`doc-fonctionnelle` le **texte des tickets** et la documentation actuelle,
jamais le code. Un ticket dit l'intention ; il ne dit ni le numéro d'une
migration, ni un seuil, ni le libellé d'un onglet. L'agent les devine, et
`appliquer_editions` ne sait vérifier qu'une chose : que l'`ancien` existe.
Rien ne vérifie le `nouveau`.

Les deux prompts le consacrent : « Pas les diffs » (technique) et « N'invente
rien qui ne soit pas dans les tickets » (les deux lisent des tickets, qui ne
contiennent pas les faits demandés).

## Options

1. **Un outil `Read` en lecture seule.** Écartée. Les deux rôles tournent sans
   outils (`allow_tools=False`, `ROLES_TEXTE`), et leur en donner change le
   profil de coût, de durée et de sécurité de l'étape. Surtout, un modèle qui
   explore ne prouve rien : on ne sait pas ce qu'il a lu pour affirmer un fait.
2. **Les fichiers que le lot touche, sans diff.** Écartée. L'agent voit l'état
   final, pas ce qui est nouveau : il ne sait pas quoi documenter.
3. **Le diff livré de chaque ticket, puis le contenu des fichiers qu'il
   touche, et une preuve exigée pour chaque édition.** Retenue. Le diff dit
   ce qui a changé et porte les noms, numéros et seuils. Le fichier entier
   corrige ce qu'un diff cache (un diff qui ajoute un quatrième onglet ne dit
   pas qu'il y en a quatre). La preuve rend le contrôle mécanique.

## Ce que l'agent reçoit

Dans l'ordre, chaque bloc avec sa propre borne :

1. **Les tickets** (inchangé) : l'intention.
2. **Le diff livré de chaque ticket**, via `ticket_diff.diff_du_ticket`, qui
   le retrouve par la branche ou, après merge et squash, par le message de
   commit. Filtré : `_ARTEFACTS` exclu comme aujourd'hui, **`README.md` et
   `docs/` exclus aussi** (le commit de documentation d'un run précédent est
   dans ce diff ; l'agent le relirait comme du code). Lockfiles réduits à une
   ligne (`_resumer_lockfiles`). Borne : 12 000 caractères par ticket,
   60 000 pour le lot.
3. **Le contenu des fichiers modifiés ou ajoutés par ces diffs** (jamais les
   supprimés), au plus 8 000 caractères chacun, 40 000 au total, par nombre de
   lignes changées décroissant. Un fichier qui ne tient pas reste représenté
   par ses hunks.
4. **La documentation actuelle** (inchangé, `_BORNE_DOC`).

Tout ce qui est tronqué se **nomme** (`[diff tronqué : N fichiers non
montrés : a, b…]`), et le prompt dit : sur un fichier non montré, aucun fait.

Deux défauts de `diff_du_ticket` à traiter dans le même changement :

- il s'exécute dans le dossier du projet et filtre sur `.` ; pour un projet
  `git_root: ancestor` comme celui-ci, `backend/` et `frontend/` n'y sont pas.
  Le diff se prend depuis la racine du dépôt (`racine_doc`), et les exclusions
  se préfixent du chemin du projet ;
- pour le ticket du run, encore sur sa branche, la référence est `main` quand
  HEAD est la branche. Sur un projet dont la base est `develop`, le diff
  contiendrait tout ce que `develop` a de plus que `main`. La base déclarée
  du projet doit être passée explicitement.

## Preuve et jetons vérifiables

Chaque édition porte `"preuve"` : une liste de `{fichier, extrait}`. Le service
refuse l'édition (donc le lot, comme aujourd'hui, avec le tour de correction du
ticket-395) si :

- la preuve est absente ou vide, sauf édition qui ne fait que **retirer** un
  texte de la doc (`nouveau` vide) ;
- un `extrait` n'apparaît pas, à la typographie près (`_normaliser_typo`), dans
  le diff ou les fichiers fournis ;
- le `nouveau` ou le `texte` introduit un **jeton vérifiable** absent du
  `ancien` et absent de la matière (tickets, diff, fichiers). Jetons : `ADR-N`,
  `ticket-N`, un nombre suivi d'une unité (`5 Mo`), un numéro de migration, une
  extension de fichier en capitales (`GIF`, `AVIF`), un mot entre guillemets.

La matière du contrôle exclut la documentation actuelle : c'est elle qui porte
les erreurs à corriger.

**Ce que ce contrôle n'attrape pas.** Un extrait existant ne prouve pas qu'il
soutient la phrase. Un modèle peut citer une ligne voisine. Le contrôle écarte
les faits qui n'ont aucune origine dans le code ; il ne remplace ni la relecture
ni la qualité du modèle. Il donne au relecteur la citation à vérifier.

## Périmètre : ne réécrire que ce qui est lié (cas du ticket 078)

Deux garde-fous, l'un par construction, l'autre en filet :

- **Par la preuve.** Une édition du guide qui réécrit « Gérer ton compte »
  doit citer un extrait du diff. Le diff d'un ticket d'en-têtes de sécurité
  n'en contient aucun qui touche au compte : l'édition est refusée.
- **Par le volume.** Une édition `ancien`/`nouveau` remplace au plus 2 000
  caractères ; un rôle, sur un lot, en remplace au plus 8 000. Au-delà, refus
  avec le motif. Une création (`contenu`) en est exempte, pas de la preuve.
  Les deux bornes sont des constantes, à ajuster après les premiers lots.

Le prompt ajoute la règle en clair : un ticket sans effet pour le lecteur
donne `{"editions": []}`.

## Taille du lot et tickets faits à la main

- `_PLAFOND` passe de 10 à **5**, et la borne de diff (60 000) coupe avant si
  nécessaire. Le lot garde les **plus anciens** d'abord, pas les plus récents :
  avec les plus récents, un retard ne se résorbe jamais, les anciens étant
  éliminés à chaque tour (`tickets[-_PLAFOND:]`). Le retard se vide par cinq,
  et la documentation avance dans l'ordre où le produit a changé.
- Un ticket **sans diff retrouvable** (fait à la main, message de commit sans
  son identifiant) n'entre pas dans le lot. Il est marqué documenté, et le
  journal du pipeline le dit : « ticket-N : pas de diff retrouvable, non
  documenté ». Le laisser en attente le ferait revenir à chaque run et occuper
  le plafond. Le coût : sa doc reste à écrire à la main. Mieux vaut une doc qui
  manque qu'une doc devinée.
- Un ticket dont le diff, filtré, est vide (docs seules, artefacts seuls) suit
  la même règle.

## Modèle

Par défaut, `doc-technique` et `doc-fonctionnelle` passent à Sonnet
(`MODELE_PRODUCTION`) : `modeles_par_defaut.py` et le repli `_MODELE` de
`documentation.py`. Ils lisent du code et le résument fidèlement, ce que la
politique du 12/10 (Haiku pour la documentation) ne prévoyait pas. La preuve
fait de Haiku un risque de refus plutôt qu'un risque de faux, mais un refus
laisse le lot à refaire : Sonnet réduit les deux.

Le coût monte avec la matière : au plafond, de l'ordre de 45 000 tokens
d'entrée par rôle et par lot, deux rôles. À mesurer sur le premier lot réel.

Un projet qui déclare son modèle dans `agents.json` ne change pas : un agent
n'écrit pas ce fichier. **C'est une action de Benjamin** pour Kadoomi, Devinoo
et les autres. Revenir sur la politique du 12/10 est aussi sa décision ; la
recommandation est Sonnet.

## Ticket-533

Non réglé ici. Des éditions plus étroites réduisent les chevauchements entre
PR d'une file, sans les supprimer : `memory/documentation.json` reste modifié
par chaque PR. 533 garde son périmètre.

## Les erreurs du 22/10 et ce qui les aurait empêchées

| Erreur relevée | Ce qui l'aurait empêchée |
|---|---|
| « trois onglets » pour quatre (Devinoo) | Le fichier du composant, fourni en entier avec ses quatre onglets. Et une preuve à citer : l'extrait qui soutient « trois » n'existe pas. |
| Groupes attribués à ADR-019 au lieu d'ADR-018 (Kadoomi) | Jeton `ADR-019` absent des tickets, du diff et des fichiers : édition refusée. Le numéro correct figure dans les tickets. |
| Migration 0021 au lieu de 0012 | Le diff porte le nom du fichier de migration. Jeton `0021` absent de la matière : refus. |
| 10 Mo et AVIF au lieu de 5 Mo et GIF | Jetons `10 Mo` et `AVIF` absents du diff, qui porte le seuil et la liste des formats : refus. |
| « Les réservations notifient le groupe », thème sombre « par défaut », e-mail de confirmation (Kadoomi) | Aucun extrait du code ne les soutient. La preuve est impossible à fournir, l'édition est refusée. |
| Le ticket 078 réécrit 94 lignes du guide (Devinoo) | Aucun extrait du diff d'en-têtes de sécurité ne touche au compte (preuve), et le plafond de 2 000 caractères par édition coupe en filet. |
| Statistiques de « revenus » inexistantes (Devinoo) | Même cas que les réservations : aucune preuve possible. |

## Tickets qui en découlent

1. **ticket-540** — la matière : diff filtré et borné par ticket et par lot,
   fichiers touchés, tickets sans diff. Nouveau module
   `services/documentation_code.py`, `diff_du_ticket` corrigé pour la racine
   du dépôt et la base.
2. **ticket-541** — le lot et le brief : `_brief` reçoit la matière,
   `_PLAFOND` à 5, les plus anciens d'abord, tickets sans diff marqués et
   journalisés, les deux prompts mis à jour sur ce qu'ils reçoivent.
3. **ticket-542** — le contrôle : `preuve`, jetons vérifiables, volume borné
   dans `appliquer_editions`, format de la preuve dans les prompts.
4. **ticket-543** — le modèle par défaut des deux rôles.

540 → 541 → 542 ; 543 est indépendant. Les prompts se changent avec le code
qui les rend vrais : changer « Pas les diffs » avant que le brief porte le diff
tromperait l'agent.
