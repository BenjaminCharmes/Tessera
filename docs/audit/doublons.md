# Audit des doublons et de la réutilisation

État au 2026-10-29, relevé sur `develop` @ `45eadca` (ref local, sans `fetch`),
branche du ticket-652. Lecture seule : aucun fichier de code n'a été modifié.
Les `fichier:ligne` sont ceux de ce SHA ; ils se décalent dès le premier ticket
de mise en commun mergé.

Périmètre : `backend/src/tessera/` et `frontend/src/`, tests exclus sauf mention.
Exclu : tout ce que couvre le ticket-631 (`components/BureauView/`,
`lib/bureau/`, `design/bureau/`).

---

## Ce que l'audit établit en une page

1. **Le manifeste `agents.json` est lu par 30 appels `json.loads` répartis dans
   21 fichiers**, chacun avec son `try/except`, son défaut et sa validation.
   Une seule clef (`git_root`, et trois autres de même forme) a un lecteur
   unique, dans `politique_run.py`. C'est le doublon le plus coûteux : chaque
   nouvelle clef ajoute un lecteur de plus, et deux lecteurs d'une même clef
   peuvent diverger sans qu'aucun diff ne le montre.
2. **La remontée vers le dépôt (`git_root: ancestor`, ADR-028) est écrite six
   fois**, avec deux façons différentes de décider qu'un dossier est un dépôt.
3. **Onze exécuteurs `git` locaux.** Trois neutralisent les hooks
   (`core.hooksPath`), les autres non : deux d'entre eux lancent pourtant une
   commande qui écrit (`checkout`, `pull`).
4. **Le coût par rôle est agrégé deux fois**, par deux requêtes SQL distinctes,
   et l'une des deux routes qui le servent n'a aucun `response_model`.
5. **Frontend : le client HTTP de `lib/api.ts` est recopié dans cinq autres
   modules** (`fetch` + `res.ok` + message `API <code>: …`). Certaines copies
   déclarent un type à la main sans que rien ne le confronte au modèle backend.
6. **Dix fonds de modale identiques**, six gestionnaires `Escape` identiques,
   cinq boucles de polling écrites à la main, quatre formateurs de durée, deux
   formateurs de date et deux de coût qui ne s'accordent pas.
7. **Quatre appels comparés en §3**, dont un écart réel (`StatutDuRun` ignore
   `arretes`) et un à vérifier à l'exécution (le `POST …/branches/cleanup` part
   sans `Content-Type`). Les autres routes n'ont pas été comparées : voir
   « Non examiné ».
8. **Dix tickets de mise en commun** (675 à 684), indépendants les uns des
   autres sauf mention. Aucun ne touche le périmètre du ticket-631.

---

## 1. Backend

### 1.1 Lecture de `agents.json` — 30 sites, 21 fichiers

Le seul lecteur mutualisé est `politique_run.py:125-182` (`_lire_chaine`,
`_lire_booleen`, `_lire_merge_method`, `_lire_git_root`). Toutes les autres
lignes ci-dessous refont `json.loads(<chemin>.read_text(...))` à la main.

| Fichier | Lignes | Ce qui est lu |
|---|---|---|
| `routers/projects.py` | 350 | `github_sync.label_map` (`import json as _json` local, 345) |
| `services/agent_registry.py` | 162 | agents de tous les projets (`glob("*/agents.json")`) |
| `services/artifacts.py` | 85, 139 | mode d'artefacts (deux lectures dans le même fichier) |
| `services/autonomie.py` | 45 | `autonomy` |
| `services/captures_config.py` | 146 | `captures` |
| `services/controle_visuel.py` | 79 | `pipeline.controle_visuel` |
| `services/declarations_activite.py` | 21 | `services[].activite` |
| `services/git_clone.py` | 126 | `github_remote` |
| `services/git_link.py` | 205 | lecture-modification-**écriture** de `agents.json` (`_store_github_remote`, 199-211) : un écrivain de plus, sans verrou |
| `services/git_workspace/socle.py` | 131 | `git_root` (booléen `== "ancestor"`) |
| `services/online_declaration.py` | 37 | `online` |
| `services/politique_run.py` | 147, 177 | booléens et chaînes (le lecteur commun) |
| `services/project_from_template.py` | 63 | agents du gabarit |
| `services/project_loader.py` | 144, 165, 178, 233, 256, 616, 633 | sept lecteurs dans un seul fichier : catégorie, remote, services, pipeline, agent |
| `services/project_overview.py` | 119 | `git_root` |
| `services/reprise_orphelin.py` | 91 | `base_branch`, `except Exception: pass` (95-96) |
| `services/providers/perimetre.py` | 76 | `git_root` |
| `services/providers/script_verification.py` | 33 | `pipeline.test_command` |
| `services/provisioning/online_config.py` | 139 | `online` |
| `services/template_claude_md.py` | 13 | rôles actifs |
| `services/worktree_politique.py` | 48 | `worktree` |

`git_root` est lu à trois endroits hors du lecteur commun (`socle.py:131-134`,
`project_overview.py:119-122`, `providers/perimetre.py:76-79`), et la valeur
`"ancestor"` est comparée en dur à ces trois endroits comme à
`politique_run.py:104`.

Écarts observés entre copies : une lecture absente ou illisible rend tantôt
`None`, tantôt `[]`, tantôt un objet par défaut (`AgentPipelineConfig()`,
`project_loader.py:254-256`), tantôt lève (`project_loader.py:614-633`) ;
`reprise_orphelin.py:95` et `projects.py:352` avalent toute exception, là où
`git_link.py:206` ne rattrape que `JSONDecodeError` et journalise.

### 1.2 Remontée vers le dépôt

| Fichier | Lignes | Critère « c'est un dépôt » |
|---|---|---|
| `services/politique_run.py` | 127-128 | `(candidat / ".git").exists()` sur `racine.parents` |
| `services/providers/perimetre.py` | 86-87 | idem, sur `depart.parents` |
| `services/providers/agent_sdk.py` | 105-106 | idem, sur `projet.parents` |
| `services/reprise_orphelin.py` | 122 | idem, en boucle `while`/`current` |
| `services/project_removal.py` | 136 | `while (courant / ".git").exists()` : sens inverse (descend tant que ça existe) |
| `services/project_overview.py` | 149-152 | `_git_dir`, suit un `.git` fichier (worktree) |

Deux critères coexistent : `.exists()` (accepte un `.git` fichier) et `_git_dir`
(le documente explicitement). `project_removal.py:136` fait l'inverse des
cinq autres. Rien ne dit si l'écart est voulu.

### 1.3 Exécuteurs `git`

| Fichier | Ligne | Retour | Hooks neutralisés |
|---|---|---|---|
| `services/temporary_worktree.py` | 21, 29 | `str` | oui |
| `services/reprise_orphelin.py` | 53, 65 | `str` | oui |
| `services/git_workspace/socle.py` | 221-233 | (méthode) | oui |
| `services/journal_en_attente.py` | 17 | `(int, str)` | **non** |
| `services/realignement_base.py` | 32 | `(int, str, str)` | **non** |
| `services/branch_cleanup.py` | 49 | `(int, str)` | non |
| `services/project_removal.py` | 50 | `(int, str)` | non |
| `services/ticket_diff.py` | 45 | `(int, str)` | non (lecture) |
| `services/git_link.py` | 75 | — | non |
| `services/project_overview.py` | 186 | `list[str]` | non (lecture) |
| `doctor.py` | 189 | `(int, str)` | non (lecture) |

Trois types de retour, trois façons de décoder la sortie. Deux copies qui
**écrivent** n'ont pas la protection que trois autres appliquent :
`journal_en_attente.py:48` (`checkout HEAD -- <journal>`) et
`realignement_base.py:116` (`fetch`), `:129` (`pull --ff-only`). ADR-027
neutralise les hooks pour les commandes d'un run ; ces deux chemins sont lancés
par le backend hors d'un run. Si l'écart est voulu, rien ne le dit ; s'il ne
l'est pas, un `post-checkout` ou `post-merge` du dépôt client s'exécute.

### 1.4 Coût par rôle

| Fichier | Lignes | Ce qui est fait |
|---|---|---|
| `services/database.py` | 618-691 (656 : `_agrege("role")`) | `get_usage_breakdown` : coût par rôle, modèle, projet, rendu en `dict` |
| `services/usage_stats.py` | 82-83 (`_breakdown(db, scope, "ac.role")`) | même agrégat, sur une autre fenêtre, rendu en `UsageStats` |

Les deux routes `GET /usage/breakdown` et `GET /{project_id}/usage/breakdown`
(`routers/projects.py:715-724`) rendent `dict[str, object]` sans
`response_model`, alors que `models/usage.py:90` porte déjà `per_agent` dans
`UsageStats`.

### 1.5 Routes sans `response_model`

`routers/services.py:97-153` : `start` rend `{"services": demarres}` (143),
`stop` rend `{"arretes": n}` (149), `lister` rend `list[dict[str, object]]`
(153) construit par `Service.en_dict()`. Le frontend les type à la main
(`lib/api.ts:193-196`). Rien ne lie les deux.

---

## 2. Frontend

### 2.1 Client HTTP recopié

Référence : `request<T>` de `lib/api.ts:60-67`. Les sept copies :

| Fichier | Ligne | Particularité |
|---|---|---|
| `lib/quota.ts` | 19 | recopie `res.ok` et le message |
| `lib/statutDuRun.ts` | 21 | idem, et type déclaré à la main (voir §3) |
| `lib/ventilation.ts` | 19 | idem, type déclaré à la main |
| `lib/capturesDuRun.ts` | 60 | idem |
| `lib/fs.ts` | 10, 16, 28, 42 | quatre `fetch` dans un fichier |
| `lib/api.ts` | 94 | `del` refait `request` pour ne pas lire de corps |

Cause : le cliquet de longueur sur `api.ts` et `types/api.ts` (ticket-545)
pousse chaque nouvelle lecture dans un fichier à part, qui ne peut pas
importer `request` (non exporté). La copie est une conséquence directe de la
règle de longueur.

### 2.2 Fonds de modale

Dix fonds `fixed inset-0 z-50 flex items-center justify-center` :

`Sidebar/CreateTicketModal.tsx:79`, `Sidebar/CreateProjectModal.tsx:100` et
`:192`, `Sidebar/AgentList.tsx:171`, `Sidebar/AgentCreatorModal.tsx:65`,
`MiseEnLigne/Fenetre.tsx:23` (teinte `bg-zinc-950/70`, les autres
`bg-black/60`), `Sidebar/PlanEvolutionModal.tsx:112`,
`Sidebar/ImportProjectModal.tsx:145`, `Sidebar/RemoveProjectModal.tsx:56`,
`Sidebar/SignalementModal.tsx:67`.

Fermeture par `Escape`, réécrite six fois : `AgentCreatorModal.tsx:58`,
`CreateProjectModal.tsx:88`, `CreateTicketModal.tsx:74`,
`ImportProjectModal.tsx:137`, `PlanEvolutionModal.tsx:104` (avec la garde
`!perteEnCours`), `SignalementModal.tsx:62`. `RemoveProjectModal.tsx`,
`AgentList.tsx` et `Fenetre.tsx` portent `role="dialog"` sans gestionnaire
`Escape` repéré dans le même fichier : à vérifier si c'est voulu.

Hors périmètre : `BoutonReglages.tsx:45` et `Cloche.tsx:61` sont des
popovers, pas des modales.

### 2.3 Boucles de temps et de polling

| Fichier | Ligne | Boucle |
|---|---|---|
| `hooks/usePrStatuses.ts` | 91 | `setInterval(doFetch, …)` |
| `hooks/useRestants.ts` | 45 | `setInterval(refresh, …)` |
| `hooks/useServices.ts` | 174 | `setInterval(refresh, …)` |
| `hooks/useTickets.ts` | 95 | `setInterval` qui incrémente une révision |
| `hooks/useAppsEnCours.ts` | 111 | `setInterval` qui incrémente un tick |
| `components/SupervisionView/Chrono.tsx` | 29 | refait `useMaintenant` : `setMaintenant(Date.now())` toutes les secondes |
| `components/AgentPanel/CompteARebours.tsx` | 23 | horloge locale |
| `components/AgentPanel/AgentDialogue.tsx` | 52 | horloge locale |

`hooks/useMaintenant.ts:8` existe et fait exactement ce que `Chrono.tsx:29`
refait. Les cinq hooks de lecture ci-dessus portent chacun leur
`setInterval` ; `hooks/useResource.ts` (cache et annulation partagés) n'offre
pas de cadence. Établi : cinq boucles écrites à la main. Non établi : que
chacune réécrive aussi son annulation et la condition de visibilité de la
fenêtre (`useFenetreVisible`) ; le ticket-683 commence par le relever.

### 2.4 Formateurs

Durée :

| Fichier | Ligne | Format |
|---|---|---|
| `design/charts/palette.ts` | 54 | `12 s`, `3 min 05`, `1 h 02` |
| `components/EnCoursView/format.ts` | 9 | `< 1 min`, `12 min`, `1 h 02`, `2 j 3 h` |
| `components/FilDuRun/index.tsx` | 24 | `3 min 5 s` |
| `components/HistoriqueView/runs.ts` | 130 | `3m 05s`, `En cours…` |
| `components/Sidebar/RunHistory.tsx` | 19 | `3m 05s`, `En cours…` : **copie conforme** de la précédente, sans l'exception « interrompu » |

Date : `HistoriqueView/runs.ts:141` (`formatDate`) et `Sidebar/RunHistory.tsx:29`
(`formatTime`) appellent `toLocaleString("fr-FR", …)` avec les mêmes options.
`design/charts/palette.ts:64` (`formatDay`) en est une troisième, pour un jour
UTC.

Coût : `design/charts/palette.ts:43` (`formatUsd` : `0,42 $`, `3 ¢`) et
`HistoriqueView/runs.ts:150` (`formatCout` : `$0.42`, `—`). **Deux notations
pour la même grandeur** dans deux écrans que l'utilisateur compare.

---

## 3. Types d'API divergents

Comparaison du type déclaré côté frontend au modèle de réponse de la route.

| Appel front | Type déclaré | Modèle backend | Écart |
|---|---|---|---|
| `statutsDuRun.lire` (`lib/statutDuRun.ts:5-14`, `:21`) | `StatutDuRun` | `RunStatus` (`services/run_status.py:36-59`) | **Réel.** Le backend rend `arretes: list[TicketArrete]` (`ticket_id`, `motif`) et `faits` (déprécié, calculé) ; le front ne déclare ni l'un ni l'autre. Un écran qui voudrait afficher les tickets arrêtés n'a pas le type pour. |
| `apiVentilation.parProjet` (`lib/ventilation.ts:5-15`, `:24`) | `VentilationDuProjet` (`per_agent`) | `dict[str, object]` (`routers/projects.py:721-724`) | Aucun modèle côté backend : le type front est une sous-vue écrite à la main, `res.json() as …` sans garde. Voulu pour ne garder que `per_agent` ; non confrontable. |
| `api.services.start`/`stop` (`lib/api.ts:193-196`) | `{ services: ServiceActif[] }`, `{ arretes: number }` | `dict[str, object]` (`routers/services.py:143`, `:149`) | Aucun modèle côté backend. `ServiceActif` n'est confronté à `Service.en_dict()` par aucun test. |
| `api.git.cleanup` (`lib/api.ts:283-287`) | `string[]` | `list[str]` (`routers/projects.py:733`) | Type juste. **Mais** le `POST` part sans `Content-Type: application/json`, contrairement à `post()` (`lib/api.ts:69-75`) : à vérifier à l'exécution, un FastAPI récent refuse un corps sans cet en-tête. |

`getPrStatuses` (ticket-367) est corrigé et n'apparaît plus ici. Le mécanisme
qui l'a laissé passer, lui, subsiste : voir la section suivante.

### Pourquoi un mock au mauvais format passe

Aucune fixture de test n'est produite à partir du modèle backend ; chaque test
écrit sa réponse à la main, du côté du type que le front croit lire. Un type
front faux et un mock faux s'accordent donc. Le ticket-684 y répond.

**Ticket-684.** `docs/openapi.json` est exporté et vérifié par un test backend ;
`frontend/src/test/contrat/` confronte les types de huit routes au schéma et
refuse, à la pose du mock, une valeur que la route ne rend pas. Les écarts qu'il
laisse, journalisés et non corrigés : `POST /services/running/{pid}/stop` n'a
toujours pas de modèle (le front type `{ pid, arretes }` à la main) ;
`ServiceActif.sortie` et `arrete_a_la_main` restent optionnels côté front alors
que le schéma les exige ; `faits`, déprécié, n'est pas déclaré par `StatutDuRun`.
Un `mockImplementation` n'est pas gardé, seulement `mockResolvedValue`.

---

## 4. Non examiné

À ne pas lire comme « sans écart » :

- Les types `Project`, `TicketListResponse`, `TicketActivity`, `UsageStats`,
  `Limites`, `ProjectOverview`, `PipelineReglages`, `ProjectAgents`,
  `ChatHistory`, `AgentDetail`, `QuotaWindows` de `types/api.ts` n'ont **pas**
  été comparés champ à champ à leurs modèles. Ils portent un `response_model`
  côté backend pour la plupart ; l'écart y est moins probable, pas exclu.
- Les composants d'UI voisins hors modales : `RoundBadge`, `QuotaBadge`,
  `PastilleSante`, `Toast`, `StatsView/Card`. Lus en diagonale, pas jugés. Aucun
  ticket n'est écrit pour les pastilles faute de preuve.
- Les tests : les mocks écrits à la main n'ont pas été énumérés un à un ; seul
  le mécanisme est établi.
- Les doublons backend dans `routers/` hors `services.py` et `projects.py`.
- Le ticket-653 (« audit des besoins de refactoring ») est susceptible de
  recouper §1.1 et §1.3 ; à rapprocher avant de lancer 675 à 677.

---

## 5. Tickets de mise en commun

Chaque ticket a des critères que `grep`, `pytest` ou `vitest` vérifient. Aucun
ne touche `components/BureauView/`, `lib/bureau/` ni `design/bureau/`.

| Ticket | Famille | Dépend de |
|---|---|---|
| 675 | Un lecteur unique du manifeste `agents.json` | — |
| 676 | Une seule remontée vers le dépôt | 675 |
| 677 | Un exécuteur `git` unique, hooks neutralisés | — |
| 678 | Un agrégat de coût par rôle, un modèle de réponse | — |
| 679 | Modèles de réponse de `routers/services.py` | — |
| 680 | Un seul client HTTP frontend | — |
| 681 | Formateurs de durée, de date et de coût partagés | — |
| 682 | Un composant `Modale` | — |
| 683 | Un hook de polling et une horloge partagés | 680 |
| 684 | Contrat route ↔ type ↔ fixture | 678, 679, 680 |

Les décisions que l'audit ne prend pas : la notation unique du coût (§2.4,
`0,42 $` ou `$0.42`) est un choix d'affichage de l'utilisateur ; le ticket-681
la pose comme paramètre à trancher, il ne la devine pas.
