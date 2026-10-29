# Audit des refactos nécessaires

État au 2026-10-29, branche du ticket-653. Lecture seule : aucun fichier de code
ni aucun plafond n'a été modifié. Les `fichier:ligne` se décalent dès le premier
ticket de découpe mergé.

SHA : aucune commande git n'était disponible pendant ce tour. `packed-refs`
donne `develop` = `6d40b60` et `origin/develop` = `bba280c` ; ces refs peuvent
être en retard sur les refs libres. Relever `git rev-parse develop` avant de
s'appuyer sur un numéro de ligne.

Périmètre : `backend/src/tessera/` et `frontend/src/`, tests exclus. Les
doublons sont dans `docs/audit/doublons.md` (ticket-652) et ne sont pas
repris : ce document les cite quand un découpage les recoupe.

## Méthode, et ce qu'elle vaut

- **Plafonds** : lus dans `PLAFONDS` de `backend/tests/test_longueur_des_fichiers.py`
  (19 entrées) et de `frontend/src/longueur-des-fichiers.test.ts` (11 entrées).
- **Tailles** : comptées par `Grep ^` fichier par fichier. Les 30 fichiers
  valent exactement leur plafond, comme le cliquet l'impose.
- **Longueur d'une fonction** : aucun outil ne la mesure et aucun script n'a pu
  être lancé. Elle est déduite de l'écart entre deux lignes `def` / `class` /
  `function` consécutives, relevées par `Grep`. C'est un **majorant** : les
  lignes blanches, les décorateurs et les fonctions imbriquées sont comptés.
  Au-dessus de 100 lignes le chiffre est sûr ; entre 80 et 90 il est à
  confirmer.
- **« Ce que le fichier mélange »** : déduit des noms et des positions de ses
  déclarations. Seuls `Orchestrator.run_queue` et le début de `useCockpit` ont
  été lus en entier. Un rôle listé ci-dessous est une lecture de la structure,
  pas un constat sur le corps des fonctions.

## 1. Fichiers sous plafond

### Backend (19)

| Fichier | Taille = plafond | Ce qu'il mélange |
|---|---|---|
| `services/orchestrator.py` | 1299 | Une seule classe `Orchestrator` (82-1244, 25 méthodes) : `__init__` de 121 lignes ; comptabilité de dépense (204-240) ; trois modes de run (`run_pipeline`, `run_queue` 274 lignes, `run_autonomous`) ; tours de production (`_run_rounds`) ; fin de file : documentation, attente de merge, réalignement, nettoyage (991-1210) ; journal |
| `routers/orchestrator.py` | 1089 | Modèles de requête (97-178), **assemblage de l'orchestrateur** (`_build_orchestrator` 169 lignes, `_livreur`, `_documenteur`, `_surveillance_pour`, `_workflow_de_lecture` : 180-884, soit 65 % du fichier), puis les endpoints (`run_pipeline`, `append_to_run`, `remove_from_run`, `get_limits`) |
| `services/pipeline_stages.py` | 840 | Quatre étapes en un module : branche (`ensure_clean_tree`, `create_branch`, `_basculer` : 62-285), production (`run_coder` 107 lignes, captures de diff : 286-549), tests (`run_tests` : 550-649), audit/revue/validation (650-840) |
| `routers/projects.py` | 826 | Huit ressources sous un seul routeur : projets et import/clone (98-387), git (388-513), mode d'artefacts (514-520, 746-779), agents (531-612), réglages du pipeline (614-715), usage (716-727), nettoyage (728-745), retrait (780-826). Les handlers sont courts (le plus long : 52 lignes) ; la longueur vient du nombre de routes |
| `services/documentation.py` | 714 | Application d'éditions Markdown, pures (`appliquer_editions` 84 lignes, `_localiser`, `_inserer` : 89-283) ; sélection des tickets à documenter (284-372) ; service et composition du brief (373-714, dont `mettre_a_jour` 131 lignes) |
| `services/database.py` | 691 | Fonctions de module sur six domaines : schéma (`init_db`), runs, événements, usage, messages de chat, conversations ; `get_usage_breakdown` (83 lignes) recoupe `usage_stats.py` (doublons §1.4) |
| `services/project_loader.py` | 646 | Lecteurs du manifeste (7 copies, doublons §1.1) ; **écrivains** du manifeste (`set_agent_model`, `set_agent_provider`, `set_pipeline_settings`, `_ecrire_manifeste` : 541-646) ; extraction depuis `CLAUDE.md` et README (339-458) ; gabarits par défaut (459-540) ; `ProjectLoader.create_project` |
| `services/ci_watcher.py` | 607 | Surveillance et attente (`CIWatcher`), émission d'événements de succès et d'échec, contrôle de tête de PR (397-465), réalignement de la base, et **écriture du journal** (4 méthodes, 554-607) |
| `services/livraison.py` | 606 | Deux protocoles locaux (`_Git`, `_Workflow`, 49-80) ; `livrer_phase_1` (**163 lignes**) ; `livrer_phase_2` (88) ; merge, attente de CI, contrôle de tête |
| `services/github_service.py` | 592 | Issues, labels, PR, état de CI (4 aides), mergeabilité, merge, infos du dépôt : 24 méthodes sur une classe |
| `routers/tickets.py` | 563 | Tickets (CRUD, statut), PR (création, état, ouverture, merge), historique de runs, activité, diff ; dix classes de modèle écrites dans le routeur |
| `services/test_runner.py` | 533 | Sémaphore, résultats, détection de la commande, exécution (`run_tests` 89 lignes), marquage des coupures et des pannes, analyse de sortie (481-533) |
| `services/pipeline_outcomes.py` | 490 | Dix fonctions `finish_*`, une par issue de run, plus `commit_work`. Cohérent : la taille vient du nombre d'issues, pas d'un mélange |
| `services/github_workflow.py` | 520 | Deux protocoles (`_GitWorkspace`, `_GitHub`, 58-105) qui répètent `GitHubService` ; corps de PR ; ouverture de PR avec contrôle des termes interdits ; **méthodes de passage** (`pr_state`, `tete_pr`, `has_workflows`…, 291-363) ; merge ; **analyse du remote et noms de forge** (444-520, sans lien avec le reste) |
| `services/providers/agent_sdk.py` | 464 | Résolution du périmètre des consignes (94-130), `_build_options` (117 lignes), provider |
| `services/ticket_service.py` | 461 | CRUD, archivage, rotation du journal, numéro de PR, allocation d'identifiant, cache d'analyse |
| `services/run_executor.py` | 414 | Journal, émetteur d'événements, suivi du run, dialogue, `executer` (86 lignes), clôture |
| `services/process_registry.py` | 405 | Validation de commande, résolution du cwd, dataclass `Service`, cycle de vie (`demarrer`, `arreter`) |
| `services/reprise_orphelin.py` | 383 | Exécuteur git (doublons §1.3), lecture de `base_branch`, écriture de fiche ticket, détection de dépôt imbriqué, fichiers nouveaux, `_reprendre_depot_seul` (100 lignes) |
| `routers/chat.py` | 378 | Historique, flux de tour de chat, assemblage du service, et `run_pipeline_from_chat` qui **importe `_build_orchestrator` depuis `routers/orchestrator.py`** (357) |

### Frontend (11)

| Fichier | Taille = plafond | Ce qu'il mélange |
|---|---|---|
| `types/api.ts` | 676 | Plus de soixante types de huit domaines : tickets, runs et événements, projets, chat, usage et statistiques, agents, git/artefacts, mise en ligne. Pas de mélange de logique : un seul domaine par type, mais tous dans un fichier |
| `hooks/streamState.ts` | 627 | État initial et types (41-240), puis `appliquerEvenement` (256-627, **372 lignes**) : un réducteur pour tous les types d'événement |
| `hooks/useCockpit.ts` | 532 | Un hook de **421 lignes** qui assemble une vingtaine de hooks et rend des groupes de props par région (ticket-252, ADR-013). C'est un compositeur voulu ; la longueur vient du nombre de groupes |
| `components/Sidebar/ImportProjectModal.tsx` | 428 | Cadre de modale, validation, deux sources (dossier local, GitHub), barre de progression, étapes ; un composant de 383 lignes |
| `hooks/useSupervision.ts` | 385 | Planification par `requestAnimationFrame`, socket, store ; un hook de 293 lignes |
| `components/FilDuRun/index.tsx` | 360 | `formatDuree` (doublon, ticket-681) et six vues (en-tête, entrée pipeline, sécurité, validateur, testeur, composant) dans un fichier |
| `hooks/useChat.ts` | 336 | État, socket, application de trames ; un hook de 196 lignes |
| `lib/api.ts` | 334 | Helpers HTTP (58-100, copiés ailleurs, ticket-680) et un objet `api` de 231 lignes qui regroupe tous les domaines |
| `components/Sidebar/TicketCard.tsx` | 314 | Six tables de styles et de libellés (17-68), puis un composant de 202 lignes |
| `components/Sidebar/TicketList.tsx` | 309 | Groupes de statut et un composant de 237 lignes |
| `components/Sidebar/CreateProjectModal.tsx` | 309 | Cadre de modale (ticket-682), validation, ports du gabarit ; un composant de 287 lignes |

## 2. Couplages

### 2.1 Imports locaux — 64 lignes dans 36 fichiers

Motif relevé : `from … import` ou `import` indenté, hors le seul fichier
`services/orchestrator.py` détaillé à part. Le comptage inclut le bloc
`if TYPE_CHECKING:`.

| Famille | Occurrences | Ce que ça dit |
|---|---|---|
| Sous `TYPE_CHECKING` | 11 dans `services/orchestrator.py` (57-67) ; `Orchestrator` dans 11 modules `pipeline_*`, `preparation_worktree`, `run_dans_worktree` ; quelques types de service | **Ne cache aucun cycle d'exécution.** Mais `pipeline_*` reçoit l'orchestrateur entier (`orch: Orchestrator`) : le couplage est de conception, pas de syntaxe |
| Plateforme (`ctypes`, `_winapi`, `asyncio as _asyncio`) | 7 | Import paresseux voulu. Hors sujet |
| Faux positif | 1 (`regles_conflit.py:72`) | Le mot « import » dans une docstring |
| Imports de providers à la demande | 2 (`providers/__init__.py:122,127`) | Choix du provider à l'exécution. Voulu |
| `tessera.config.settings` | 7 (`ollama.py` ×3, `ticket_check`, `test_runner`, `termes_interdits`, `agent_sdk`) | Import paresseux d'un singleton. Cycle probable avec la configuration, **non vérifié** |
| Un service importé dans un autre, à l'intérieur d'une fonction | 8 : `project_loader.py:159` (`github_workflow`), `:213` (`providers.perimetre`), `:561` (`cost_calculator`) ; `routers/orchestrator.py:339,714,715` (`ci_watcher`, `pipeline_events`) ; `routers/tickets.py:301` ; `pipeline_stages.py:574` | Cycle ou coût de démarrage évité. **Non vérifié** : aucun script n'a pu remonter l'import en tête de fichier pour voir si Python proteste |
| Un routeur importe le nom privé d'un autre routeur | 2 : `routers/chat.py:357` → `routers.orchestrator._build_orchestrator` (dans une fonction) ; `routers/ticket_proposals.py:11` → `routers.tickets._require_github_service` (en tête de fichier) | **Le plus net.** Un `_` privé importé entre routeurs : du code partagé est au mauvais étage |
| Un routeur importe un module partagé de `routers/` | 10 lignes : `routers.dependencies` (`require_valid_project_id`, 8 routeurs : `chat`, `captures`, `projects`, `provisioning`, `services`, `tickets`, `tickets_archive`, `ticket_proposals`) et `routers.services_running` (`get_sonde`, par `services.py` et `services_activite.py`) | Voulu : ce sont des modules de dépendances, pas des routeurs. Un test du ticket-670 doit les autoriser |

Conséquence : le ticket-670 (test du sens des imports, `routers → services →
models`) échouera sur les deux imports de nom privé tels quels. Le ticket-687
règle le premier (`chat.py:357`), le ticket-701 le second.

### 2.2 Fonctions de plus de 80 lignes (majorant)

| Fonction | Lignes | Fichier |
|---|---|---|
| `Orchestrator.run_queue` | 274 | `services/orchestrator.py:650` |
| `appliquerEvenement` | 372 | `hooks/streamState.ts:256` |
| `useCockpit` | 421 | `hooks/useCockpit.ts:112` |
| `ImportProjectModal` | 383 | `components/Sidebar/ImportProjectModal.tsx:46` |
| `useSupervision` | 293 | `hooks/useSupervision.ts:93` |
| `CreateProjectModal` | 287 | `components/Sidebar/CreateProjectModal.tsx:23` |
| `TicketList` | 237 | `components/Sidebar/TicketList.tsx:73` |
| `TicketCard` | 202 | `components/Sidebar/TicketCard.tsx:113` |
| `useChat` | 196 | `hooks/useChat.ts:80` |
| `_build_orchestrator` | 169 | `routers/orchestrator.py:224` |
| `livrer_phase_1` | 163 | `services/livraison.py:122` |
| `mettre_a_jour` | 131 | `services/documentation.py:441` |
| `Orchestrator.__init__` | 121 | `services/orchestrator.py:83` |
| `_build_options` | 117 | `providers/agent_sdk.py:131` |
| `run_coder` | 107 | `services/pipeline_stages.py:371` |
| `_livreur` | 104 | `routers/orchestrator.py:564` |
| `_reprendre_depot_seul` | 100 | `services/reprise_orphelin.py:257` |
| `_documenter_le_run` | 89 | `services/orchestrator.py:991` |
| `run_tests` (stage / runner) | 89 / 89 | `pipeline_stages.py:550`, `test_runner.py:222` |
| `livrer_phase_2` | 88 | `services/livraison.py:372` |
| `executer` | 86 | `services/run_executor.py:250` |
| `_basculer`, `_run_pipeline`, `_mener_le_run` | 85 chacune | `pipeline_stages.py:201`, `orchestrator.py:410, 267` |
| `appliquer_editions`, `_surveillance_pour`, `get_usage_breakdown` | 84, 84, 83 | à confirmer (voir méthode) |

`run_queue` mélange, dans une boucle, le calcul du plafond de dépense, le test
d'arrêt, l'émission de `QUEUE_PROGRESS`, le saut des tickets terminés, l'appel
d'un run, et trois politiques d'arrêt après un ticket non approuvé (budget,
limite de session, quota). Ce sont des étapes nommables, aujourd'hui des blocs
séparés par des commentaires.

### 2.3 Classes à plusieurs rôles (jugement, pas mesure)

- **`Orchestrator`** : exécute (trois modes), compte la dépense, orchestre la
  fin de file (documentation, merge, nettoyage), journalise. Les modules
  `pipeline_*` ont déjà montré la voie : fonctions de module qui reçoivent
  `orch`. Le découpage la prolonge, sans nouveau patron.
- **`GitHubService`** (24 méthodes) : client d'API, lecteur d'état de CI, et
  logique de merge conditionnel (`merge_quand_fusionnable`, 70 lignes).
- **`GitHubWorkflowService` / `LivraisonService`** : trois couches, chacune
  avec son protocole, répètent les mêmes noms (`has_workflows` apparaît dans
  `github_service.py:321`, `github_workflow.py:88` et `:346`, `livraison.py:72`).
  C'est de la délégation sans logique. **Aucun ticket** : le correctif touche
  les trois fichiers et le ticket-677 (`livraison.py`, `github_workflow.py`) ;
  voir « Non ticketé ».
- **`ProjectLoader` (module)** : lit, écrit, analyse du texte et gabarise.
- **`Database` (module)** : pas de classe ; six domaines en fonctions libres.

## 3. Classement

Coût : **S** ≤ une demi-journée de run, **M** quelques fichiers déplacés avec
des tests à rattacher, **L** un fichier de plus de 1000 lignes ou une frontière
à tracer. Risque : de régression au comportement, pas de difficulté.

| Ticket | Refacto | Fichiers touchés | Coût | Risque | Dépend de |
|---|---|---|---|---|---|
| 685 | `run_queue` et `run_autonomous` hors de `Orchestrator` | `services/orchestrator.py`, nouveau module de file | L | élevé : chemin de tous les runs en file, arrêts de dépense et de quota | — |
| 686 | Fin de file hors de `Orchestrator` | `services/orchestrator.py`, nouveau module | M | moyen : livraison et documentation | 685 |
| 687 | Assemblage de l'orchestrateur hors du routeur | `routers/orchestrator.py`, `routers/chat.py`, nouveau module de service | L | élevé : tout run passe par là ; le nombre de tests qui patchent ces noms n'a pas été relevé | — (avant 670) |
| 688 | `pipeline_stages.py` par étape | `services/pipeline_stages.py`, importeurs | M | moyen : les tests patchent des noms de module | — |
| 689 | `routers/projects.py` par ressource | `routers/projects.py`, `main` | M | faible : handlers courts, chemins inchangés | 678, 679 |
| 690 | `database.py` par domaine | `services/database.py`, importeurs | M | moyen : tous les services l'importent | 678 |
| 691 | `project_loader.py` : écriture, extraction, gabarits | `services/project_loader.py` | M | faible | 675 |
| 692 | `documentation.py` : éditions pures, sélection, service | `services/documentation.py` | S | faible : fonctions pures | — |
| 693 | `types/api.ts` par domaine | `types/api.ts`, importeurs si le fichier ne devient pas un simple ré-export | M | faible : `tsc` attrape tout | — |
| 694 | `lib/api.ts` par domaine | `lib/api.ts`, `lib/api/*` | M | faible | 680 |
| 695 | `appliquerEvenement` par famille d'événements | `hooks/streamState.ts` | M | moyen : rejeu et état en jeu | — |
| 696 | `useCockpit` par région | `hooks/useCockpit.ts` | M | moyen : un hook de composition | — |
| 697 | `ImportProjectModal` par étape | `components/Sidebar/ImportProjectModal.tsx` | M | faible | 682 |
| 698 | `FilDuRun`, `TicketCard`, `TicketList` sous 300 | trois composants | S | faible | 681 |
| 699 | Remote et noms de forge hors de `github_workflow.py` | `services/github_workflow.py` | S | faible : fonctions pures | — |
| 700 | `livrer_phase_1` en étapes nommées | `services/livraison.py` | M | élevé : portes de livraison (ADR-030, ADR-039) | 677 |
| 701 | `_require_github_service` hors de `routers/tickets.py` | `routers/tickets.py`, `routers/ticket_proposals.py`, `routers/dependencies.py` | S | faible | — (avant 670) |

### Recoupements avec les tickets de `doublons.md`

- **675 → 691** : 675 remplace les sept lecteurs de `project_loader.py`.
  Découper avant 675 ferait migrer sept copies dans un fichier neuf.
- **677 → 700** : 677 unifie l'exécuteur git de `livraison.py` ; 700 découpe
  la fonction qui l'appelle.
- **678, 679 → 689, 690** : les routes d'usage et la requête d'agrégat
  changent de place dans 678 ; les découper avant produirait un conflit.
- **680 et `lib/api.ts`** : le §2.1 de `doublons.md` attribue la copie du client
  au cliquet. Mais le ticket-680 extrait `request` dans `lib/http.ts` et exige
  que le plafond de `api.ts` ne soit pas relevé : **680 passe avant** et n'a
  pas besoin d'une découpe préalable. La découpe de `lib/api.ts` (694) vient
  après, et n'importe plus que `http`.
- **681 → 698** : `formatDuree` quitte `FilDuRun` dans 681 ; c'est lui qui
  remonte `FilDuRun` vers 300.
- **682 → 697** : le composant `Modale` remplace le cadre de modale et le
  gestionnaire `Escape` de `ImportProjectModal` et de `CreateProjectModal`.
  `CreateProjectModal` (309) pourrait repasser sous 300 sans ticket propre ;
  c'est une hypothèse, pas un constat.
- **670 ← 687, 701** : le test d'imports échoue sur `chat.py:357` et sur
  `ticket_proposals.py:11` tant que 687 et 701 ne sont pas passés.
- **Tickets ouverts qui touchent les mêmes fichiers** : 668 (design des
  sous-tâches d'un run, touche `Orchestrator._run_rounds` et `_mener_le_run`),
  665, 667, 539 et 533 (livraison et documentation du pipeline). Lancer 685 et
  686 avant l'implémentation de 668, pas pendant.

Ordre proposé, par vagues indépendantes :

1. 680, 681, 682, 675, 677, 678, 679 (doublons) en parallèle de 692, 693, 699.
2. 691, 694, 697, 698, 689, 690 (ce que les doublons ont dégagé).
3. 687 et 701, puis 670 ; 688 ; 695, 696.
4. 685, puis 686 ; 700 en dernier : ce sont les chemins de livraison.

Deux tickets qui touchent le même fichier ne se lancent pas en parallèle :
deux branches sur `services/orchestrator.py` donnent des conflits au rebase.

## 4. Tickets de refacto

Chacun a pour critère la baisse du plafond de son fichier dans le cliquet
(l'entrée se resserre, ou disparaît sous 300 lignes), des tests existants qui
passent sans modification de leurs attendus, et `grep` pour la preuve du
déplacement. Les cibles de taille sont des estimations issues des plages de
lignes ci-dessus, pas des mesures.

Voir le tableau du §3 pour l'ordre et les dépendances. Les fiches sont dans
`projects/ide-core/tickets/todo/ticket-685` à `ticket-701`.

## 5. Non ticketé, et pourquoi

Un cliquet interdit déjà au fichier de grossir ; un ticket de découpe coûte un
run complet. Ces fichiers ne portent pas de ticket :

- **`pipeline_outcomes.py` (490)** : dix issues, une fonction chacune.
  Aucun mélange, la taille suit le nombre de cas.
- **`ticket_service.py` (461)** : les tickets 659 (allocation des numéros) et
  660 (archivage par centaines) en changent la forme ; découper avant ferait
  deux fois le travail.
- **`routers/tickets.py` (563)** et **`routers/chat.py` (378)** : même
  découpe que 689 (un routeur par ressource) ; à faire quand 689 aura prouvé le
  patron sur `projects.py`.
- **`ci_watcher.py` (607)**, **`github_service.py` (592)** : le plafond tient, et
  les tickets 533, 539, 674 y touchent. Le correctif utile, supprimer les
  méthodes de passage entre `GitHubService`, `GitHubWorkflowService` et
  `LivraisonService`, dépend du ticket-677 et d'un choix de frontière
  (quel port `CIWatcher` voit) que cet audit ne prend pas.
- **`test_runner.py`, `process_registry.py`, `run_executor.py`,
  `reprise_orphelin.py`, `agent_sdk.py`** : de 383 à 533 lignes, chacun avec
  une fonction entre 86 et 117 lignes. Trop proches de 300 pour justifier un
  ticket seul ; à traiter dans le ticket qui les modifie.
- **`useChat.ts` (336)** et **`useSupervision.ts` (385)** : 36 et 85 lignes
  au-dessus du plafond général, sans mélange de rôles relevé.

## 6. Non examiné

- Le corps de la plupart des fonctions : seuls `run_queue` (650-779) et le
  début de `useCockpit` (100-209) ont été lus. « Ce que le fichier mélange » est
  déduit des noms.
- Les fichiers de moins de 300 lignes : aucune fonction de plus de 80 lignes
  n'y a été cherchée.
- `components/BureauView/`, `lib/bureau/` et `design/bureau/`, exclus par le
  ticket-631.
- Les cycles évités par import local : non confirmés (voir §2.1).
- Le nombre d'importeurs de chaque fichier à découper, donc le coût réel de
  mise à jour des `patch("…")` et des `import`. Chaque ticket commence par le
  relever.
- L'écriture de numéros de ticket : le script `prochain_numero.py` n'a pas pu
  tourner (pas de `Bash`). 685 à 701 sont le suivant le plus grand relevé par
  `Glob` dans `tickets/` et par `Grep` dans les refs git ; si une autre branche
  a pris un de ces numéros, le renuméroter avant merge.
