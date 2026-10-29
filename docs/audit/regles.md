# Audit des règles — tests, écarts, conventions

État au 2026-10-29. Complète `docs/audit/adr.md` (statuts des ADR) : les règles de
`projects/ide-core/memory/contraintes.md` sont prises avec les statuts de son §3, sans
les redécouvrir.

## Méthode et limites

Lu par recherche dans `backend/tests/`, `backend/src/tessera/` et `frontend/src/`. Pas de
shell : aucun test n'a été lancé, aucun script exécuté. Deux niveaux de preuve :

- **gardée** : un test dont le nom et la cible disent la règle. Le corps n'a été relu que
  là où l'écart est signalé en §2 ; un test qui porte le bon nom peut garder moins que la
  règle.
- **partielle** : un test garde une partie de la règle, ou la garde par un moyen faible.
- **aucun test** : plusieurs recherches (nom de la règle, noms de fichiers, noms de
  champs) ne rendent aucun test.

Les comptes de fichiers et de docstrings viennent d'expressions régulières : ce sont des
planchers, pas des totaux.

## Ce que l'audit établit en une page

- Sur **50 règles** de `contraintes.md` (4 non injectées, sous « Proposées ») : **6 n'ont
  aucun test**, **8 sont partielles**, **5 sont à relire** (corps de test non lu),
  **1 est périmée**, **30 sont gardées**.
- Le plus gros trou est la **langue (ADR-044)** : aucun test, et la règle est fausse dans
  les deux sens (voir §3).
- **Deux règles de `CLAUDE.md` disent autre chose que la pratique ou que le test** :
  « fichiers en kebab-case » (presque aucun fichier ne l'est) et « < 200 lignes »
  (le plafond testé est 300).
- Les trois règles déjà signalées fausses dans `adr.md` §3 le restent ; la règle
  « `local` est le défaut » est incomplète.
- `any` et `console.log` : conformes, sauf un `any` supprimé à la main dans un test.

## 1. Règles et tests

Section de `contraintes.md` entre parenthèses. « P » : non injectée.

### Proposées (non injectées)

| Règle | ADR | Test | Verdict |
|---|---|---|---|
| Verdict en sortie structurée | 061, 009 | `test_verdict_reviewer.py::test_absent_structured_output_refuses`, `::test_prose_in_the_summary_never_overrides_the_verdict_field` ; `test_validateur_sortie_structuree.py` | partielle : l'audit sécurité n'a pas de test nommé sur la sortie structurée |
| Pas de serveur ni de capture sans `controle_visuel` | 062 | `test_controle_visuel.py::test_lire_le_controle_without_declared_mode_is_none` ; `test_app_du_run.py`, `test_relecture_visuelle.py` | partielle : « port libre » et « ne tue jamais un processus » non lus |
| Agent de produit depuis `services[].activite` seul | 064, 058 | `test_activite_produit.py::test_stale_file_returns_nothing`, `::test_path_leaving_the_project_returns_nothing`, `::test_file_over_16_kib_returns_nothing` | partielle : « Tessera ne l'écrit jamais » sans test |
| La livraison attend les PR du watcher | 065, 051 | `test_attente_des_merges.py::test_timeout_ends_the_wait_without_raising`, `::test_delivery_starts_only_after_the_wait` | gardée |

### Git et périmètre d'écriture

| Règle | ADR | Test | Verdict |
|---|---|---|---|
| Un run dans son worktree | 056 | `test_perimetre_ecriture.py::test_le_hook_refuse_le_checkout_et_accepte_le_worktree` ; `test_run_dans_un_worktree.py` | gardée |
| `populate` : lien seulement sur ce que git ignore | 056, 053 | `test_run_worktree_populate.py::test_peupler_refuses_to_link_what_git_does_not_ignore`, `::test_retirer_les_liens_never_enters_the_target_of_a_link`, `::test_peupler_reports_a_missing_entry_and_populates_the_others` | partielle : « jamais le `.env` de Tessera » sans test |
| Jamais d'écriture hors de la racine | 031, 053 | `test_perimetre_ecriture.py::test_le_hook_refuse_une_ecriture_hors_perimetre`, `::test_le_hook_refuse_un_bash_qui_ecrit_dehors`, `::test_le_hook_refuse_une_ecriture_a_travers_un_lien` | gardée (texte incomplet, §2) |
| Aucun git ou `gh` en écriture ; fichiers protégés | 027 | `test_git_guard.py::test_les_commandes_qui_modifient_l_historique_sont_refusees`, `::test_les_formes_detournees_sont_couvertes` ; `test_chemins_proteges.py` | gardée |
| Script de `test_command` en lecture seule ; avertissement | 027 | `test_script_verification.py` ; `test_config_tests_touchee.py::test_conftest_et_vitest_sont_nommes`, `::test_le_message_du_reviewer_commence_par_lavertissement` | gardée (ADR muette, `adr.md`) |
| Règle nouvelle sous « Proposées » | 055 | `test_contraintes_proposees.py::test_run_adding_a_rule_outside_proposed_is_blocked` | gardée |
| `rev-parse --show-toplevel` avant toute branche | 024, 028 | `test_git_workspace.py::test_repertoire_sans_depot_git_leve_not_a_git_repository`, `::test_ensure_own_repository_refuse_un_depot_etranger` | gardée |

### Livraison et autonomie

| Règle | ADR | Test | Verdict |
|---|---|---|---|
| Une branche, un commit par run | 018 | `test_commit_sur_toutes_les_sorties.py` ; `test_plafond_entre_deux_tours.py::test_le_travail_du_tour_1_est_commite_en_unapproved_work` | gardée |
| Le chat commite sur `chat-<horodatage>` | 019 | `test_chat_service.py`, `test_verrou_du_chat.py` (motif `chat-`) | à lire : « arbre jamais sale » non confirmé |
| Jamais de push forcé | 022 | `test_git_push.py::test_le_push_n_est_jamais_force`, `test_git_push_course.py::test_remote_behind_head_is_pushed_again_without_force` | partielle : le premier lit le source (`test_git_push.py:95-96`) |
| `autonomy` et CI verte pour merger | 029, 045 | `test_niveau_autonomie.py` ; `test_merger_sans_ci.py` | gardée |
| `approved_sha` / `pushed_sha` | 492, 039 | `test_approbation_sha.py::test_changed_branch_blocks_the_ticket` ; `test_merge_lie_au_sha.py::test_head_moved_during_ci_wait_prevents_merge`, `::test_unreadable_head_prevents_merge` | gardée (aucune ADR, `adr.md`) |
| Un run non approuvé ne se livre pas | 030 | `test_orchestrator_livraison.py` | à lire |
| Conflit de rebase : tenter, jamais merger seul | 033 | `test_resolveur_conflit.py`, `test_ci_watcher_conflit.py`, `test_livraison_regles_conflit.py` | gardée |
| Phase 1 libère le verrou ; CI rouge = `blocked` | 051 | `test_ci_watcher.py`, `test_attente_dependance.py` | à lire |

### Portes qui échouent fermées

| Règle | ADR | Test | Verdict |
|---|---|---|---|
| Toute exception : `blocked` avec commit | 037 | `test_commit_sur_toutes_les_sorties.py`, `test_run_interrompu_arbre_propre.py` | à lire |
| Worktree sale : jamais supprimé | 056, 037 | `test_reprise_worktrees.py::test_dirty_worktree_is_committed_as_unapproved_work_then_removed`, `::test_a_failed_commit_keeps_the_folder_and_the_startup_goes_on` | gardée |
| Un run à la fois par projet | 038 | `test_verrou_par_projet.py::test_le_refus_nomme_le_ticket_en_cours`, `::test_un_projet_a_worktree_refuse_aussi_un_second_run_en_409` | gardée |
| Audit et validateur échouent fermés | 039 | `test_security_auditor.py` (33 tests), `test_validator.py` (37) | à lire |
| Autonome : dépense et quota entre deux tickets | 020 | `test_run_budget.py::test_le_run_autonome_s_arrete_au_plafond_cumule`, `::test_le_run_autonome_s_arrete_quand_le_quota_est_bas`, `::test_un_quota_inconnu_ne_bloque_pas_le_run` | gardée |
| Question sans réponse : hypothèse énoncée | 025 | `test_question_dans_l_instantane.py` (délai à 0,01 s) ; `test_dialogue_channel.py::test_en_mode_autonome_la_question_ne_bloque_jamais` | gardée |

### Artefacts, projets, provider, orchestration

| Règle | ADR | Test | Verdict |
|---|---|---|---|
| Artefacts via `.git/info/exclude` | 021 | `test_artifacts.py::test_le_mode_local_exclut_les_artefacts_sans_toucher_au_gitignore` | gardée |
| `local` par défaut | 023 | `test_artifacts.py::test_sans_agents_json_le_mode_est_local`, `::test_un_agents_json_sans_la_cle_est_local` | gardée (texte incomplet, §2) |
| Services déclarés dans `agents.json` | 042 | `test_services_du_projet.py` (23), `test_services_running.py` | gardée |
| `list_projects` filtre sur `CLAUDE.md` | 006 | `test_project_loader.py::test_project_loader_list_filters_claude_md` | gardée |
| `name` depuis le premier `# Titre` | 007 | `test_project_loader.py::test_load_project_with_claude_md`, `::test_un_titre_qui_ne_serait_que_la_decoration_retombe_sur_le_dossier` | gardée |
| Services passent par `LLMProvider` | 017 | `test_provider_par_role.py::test_aucun_routeur_n_appelle_get_provider_directement` | partielle : routeurs seuls ; le SDK n'est importé que sous `services/providers/` (aujourd'hui vrai, sans test) |
| `provider_pour_role`, repli sur indisponibilité | 046 | `test_provider_par_role.py::test_la_fabrique_construit_le_provider_declare_pour_le_role`, `::test_une_reponse_illisible_ne_declenche_pas_le_repli`, `::test_un_repli_utilise_se_voit_sur_le_canal_d_observation` | gardée (texte périmé, `adr.md`) |
| Rôle `web` reçoit `WebFetch`, perd `Bash` | 049 | `test_web_sans_shell.py::test_un_role_web_lit_le_web_et_perd_bash` | gardée |
| Run par `POST`, observé par WS | 041 | `test_canal_d_observation.py` | gardée |
| Orchestrateur sans état | 008 | aucun | **aucun test** |
| Verdict reviewer par mot-clé | 009 | `test_verdict_reviewer.py::test_prose_in_the_summary_never_overrides_the_verdict_field` garde **l'inverse** | périmée (§2) |
| `github-sync` dans `/agents/run` | 010 | `test_github_sync.py`, `test_agents_router_endpoints.py` | gardée |

### Confidentialité

| Règle | ADR | Test | Verdict |
|---|---|---|---|
| Aucune donnée professionnelle | 043 | `test_aucune_trace_professionnelle.py` | gardée |
| `FORBIDDEN_TERMS` avant tout push | 048 | `test_hook_pre_push.py::test_terme_dans_message_commit`, `::test_terme_dans_auteur_commit`, `::test_terme_dans_diff_ajoute` | gardée |
| Jetons de service hors des agents | 053 | `test_garde_jetons.py::test_read_refuses_the_tessera_env` ; `test_jetons_de_mise_en_ligne.py` | gardée |
| Trois portes de termes interdits | 050 | `test_hook_pre_push.py`, `test_termes_interdits_ci.py::test_a_missing_list_refuses_the_pr`, `test_termes_interdits.py` | gardée |

### Interface, documentation, langue, stack

| Règle | ADR | Test | Verdict |
|---|---|---|---|
| Cinq familles ; violet jamais en texte | 026 | `coherence.test.ts` : « n'utilise que les cinq familles… », « n'écrit jamais le violet en couleur de texte » | gardée |
| Graphiques : `data-1..3` dans `design/charts/` | 047 | `coherence.test.ts:79` (hors de `design/charts/`) | partielle : « dans cet ordre fixe » non lu |
| Tauri sans `fs:*` ni `shell:*` | 040 | aucun | **aucun test** (`capabilities/default.json` ne porte que `core:default` et `notification:default`, à ce jour) |
| Rien de décoratif dans le Bureau | 058 | `sources.test.ts` (jetons `--sprite-*`), `Personnage.test.tsx` | partielle : le tout-ou-rien « une donnée par objet dessiné » n'est pas testable tel quel |
| Doc : cite le code livré | 057 | `test_documentation_preuve.py`, `test_documentation_code.py` | gardée |
| Langue : anglais | 044 | aucun | **aucun test** |
| Vitest, pas Jest | 014 | aucun (`package.json` : `vitest`, pas de `jest`) | **aucun test** |
| Monaco bundlé, pas de CDN | 012 | aucun (`lib/monaco.ts:30` : `loader.config({ monaco })`) | **aucun test** |
| Pas d'état global tant que… | 013 | `useActiveProject.test.ts` teste le hook, pas la règle | **aucun test** (condition périmée, `adr.md` paire 7) |

Total : 6 sans test (ADR-008, 040, 044, 014, 012, 013), 8 partielles (dont la clause
`.env` de 056), 5 à lire, 1 périmée, 30 gardées.

## 2. Écarts de contenu (règle ≠ test ≠ code)

Les trois premiers viennent de `adr.md` §3 ; ils sont cités, pas refaits.

| # | `contraintes.md` | Écart |
|---|---|---|
| E1 | `:159` verdict par mot-clé | Fausse. `test_verdict_reviewer.py:149` garde « la prose ne passe jamais devant le champ verdict ». |
| E2 | `:145` « seule une indisponibilité déclenche le repli » | Incomplète. `test_run_rapide.py::test_fast_run_builds_only_the_fallback_with_its_model` (`:48`) prouve le second déclencheur (ADR-059). |
| E3 | `:44` « hors de la racine du projet » | Dit « projet » ; `test_perimetre_ecriture.py:305` prouve que la racine d'un run est son worktree (ADR-056). |
| E4 | `:125` « `local` est le défaut quand `agents.json` est absent » | Incomplète : `test_artifacts.py:46` `test_un_projet_cree_est_versionne_par_defaut` — un projet créé est versionné par défaut ; `artifacts.py:55` : « selon la façon dont le projet est arrivé » (ADR-023). |
| E5 | `:141` « les services passent par `LLMProvider` » | Gardée pour les routeurs seulement (`test_provider_par_role.py:522`). |
| E6 | `:225` ADR-013 | `runStore.ts` existe en `useSyncExternalStore` ; la règle nomme `useActiveProject` seul. |
| E7 | `:145` « déclarer `provider`… pour chaque rôle » | `test_provider_par_role.py:73` : un manifeste sans `provider` charge sur `agent_sdk`. La règle dit « déclarer pour chaque rôle » ; le chargeur a un défaut. |

Garde faible : `test_git_push.py:89-96` cherche `--force` et `-f` dans le **texte du
source** d'une fonction. Un push forcé par un autre chemin, ou une option écrite
autrement (`--force-with-lease`), n'y est pas vu. Il garde la lettre, pas l'effet.

## 3. Conventions de `CLAUDE.md`

| # | Convention | Constat | Où |
|---|---|---|---|
| K1 | « fichiers en kebab-case » | **Écart** : trois fichiers de `frontend/src` le sont (`longueur-des-fichiers.test.ts`, `favicon-contraste.test.ts`, `vite-env.d.ts`) ; composants en PascalCase, hooks et `lib/` en camelCase (`useCockpit.ts`, `lib/api.ts`). | `CLAUDE.md:59-60` |
| K2 | « préférer < 200 lignes » | **Écart texte/test** : le plafond testé est **300** (`test_longueur_des_fichiers.py:5`, `longueur-des-fichiers.test.ts:7`). Au moins 52 fichiers backend et 27 fichiers source frontend atteignent 200 lignes ; 20 et 11 sont au-dessus de 300, avec un plafond déclaré (`test_longueur_des_fichiers.py:10-32`, `longueur-des-fichiers.test.ts:12-24`). Restent **33 backend et 16 frontend entre 200 et 300 sans plafond déclaré** : le texte les vise, aucun test ne les voit. Le plus gros : `services/orchestrator.py`, 1299 lignes. | `CLAUDE.md:111` |
| K3 | « docstrings en anglais » | **Écart**, aucun test : au moins **217** docstrings qui s'ouvrent sur un mot français, dans 88 fichiers de `backend/src/tessera/` (exemples : `doctor.py:70`, `routers/chat.py:75`, `services/adr.py:50`, `routers/projects.py:234`, `services/activite_produit.py:1`). | `CLAUDE.md:57` |
| K4 | « noms de tests en anglais » (`contraintes.md`, ADR-044) | **Écart massif**, aucun test : au moins 795 fonctions de test dont le nom s'ouvre sur un article ou une préposition français, dans 119 fichiers (`test_perimetre_ecriture.py`, `test_provider_par_role.py`, `test_git_guard.py`). Les fichiers de test aussi portent des noms français. | `contraintes.md` « Langue » |
| K5 | `strict: true`, jamais de `any` | **Conforme** : `tsconfig.app.json:6` ; `tseslint.configs.recommended` (`eslint.config.js:14`) porte `no-explicit-any`, non nommée. **Un seul** `any` : `useSupervisionReplay.test.ts:20`, `vi.fn<any>()`, supprimé par `eslint-disable` à la ligne 19. | `CLAUDE.md:59` |
| K6 | pas de `console.log`, logger structuré | **Conforme** : `no-console` en erreur sur `src/**` (`eslint.config.js:35`), levé pour le seul `lib/logger.ts` (`:40-43`) ; `logger.ts:16` appelle `console[level]`. Les deux autres occurrences de « console.log » sont des commentaires. | `CLAUDE.md:60` |
| K7 | « un test par fonction publique » | **Non mesuré** : sans shell, pas de rapprochement fonction publique / test. Le cliquet de longueur et le nombre de fichiers de test n'en disent rien (ticket C10). | `CLAUDE.md:112` |
| K8 | Tailwind sans `tailwind.config.ts` | **Conforme** : aucun `frontend/tailwind.config.*`. | `CLAUDE.md` pile |

Hors règle, à noter : huit `eslint-disable-next-line react-hooks/exhaustive-deps` dans
`frontend/src/hooks/` (`useCockpit.ts:199`, `useBlockedArrets.ts:50`, `useQuotaLu.ts:22`,
`useRestants.ts:34`, `useResource.ts:121`, `useWeekEmployee.ts:38`, `useTickets.ts:88`,
`useServices.ts:74`). Aucune convention ne les interdit ; ce sont des dépendances de hook
désarmées à la main.

## 4. Tickets de correction

Pas de numéros : ils s'allouent à la création (ticket-659). D'abord les règles sans test,
puis les écarts. « À la main » : un run ne peut pas écrire ce fichier (ADR-055,
`CLAUDE.md` sans ticket explicite).

### Règles sans test

**C1 — Tauri n'expose aucune permission `fs:*` ni `shell:*` (ADR-040), backend.**
- Un test `test_tauri_exposes_no_fs_or_shell_permission` lit `frontend/src-tauri/capabilities/*.json`
  et échoue sur toute permission commençant par `fs:` ou `shell:`.
- Il échoue aussi si `frontend/src-tauri/Cargo.toml` ou `package.json` déclare
  `tauri-plugin-fs`, `tauri-plugin-shell`, `@tauri-apps/plugin-fs` ou `@tauri-apps/plugin-shell`.
- Contrôle de mutation : ajouter `"fs:default"` à `default.json` fait échouer le test.

**C2 — L'orchestrateur ne garde aucun état entre deux requêtes (ADR-008), backend.**
- Un test `test_no_orchestrator_is_kept_at_module_level` parcourt l'AST de `routers/` et
  `services/` et échoue sur toute affectation de niveau module dont la valeur est un appel
  à `Orchestrator(`.
- Un second test construit deux `Orchestrator` sur le même projet : le second ne voit
  aucune modification de l'état du premier (`vars()` identique à un orchestrateur neuf).
- Contrôle de mutation : `_ORCH = Orchestrator(...)` en tête de `routers/orchestrator.py`
  fait échouer le premier.

**C3 — Les règles de la pile frontend sont testées (ADR-012, ADR-013, ADR-014), frontend.**
- `no jest dependency` : `package.json` ne contient ni `jest`, ni `ts-jest`, ni `@types/jest`.
- `monaco is bundled` : `src/lib/monaco.ts` appelle `loader.config({ monaco })` ; aucun
  fichier de `src/` ne contient `cdn.jsdelivr` ni `paths: { vs`.
- `no global state library` : `package.json` ne contient ni `zustand` ni `jotai` ; un
  second test compte les fichiers de `hooks/` qui utilisent `useSyncExternalStore` et
  échoue au-delà de 5 (le seuil de l'ADR).
- Taille : un seul fichier de test, trois cas.

**C4 — La langue des identifiants est testée, ou la règle est réécrite (ADR-044).**
Décision à prendre d'abord (voir « Ce que l'audit ne tranche pas »). Si la règle reste :
- Un cliquet `test_no_new_french_docstring` lit les docstrings de `backend/src/tessera/`
  avec `ast`, détecte celles dont le premier mot est dans une liste de mots français, et
  compare à une liste de base (`dict` fichier → compte, comme `PLAFONDS`). Un fichier ne
  gagne pas de docstring française ; la liste ne remonte pas.
- Contrôle de mutation : une docstring `"""Retourne la liste."""` dans un fichier neuf
  fait échouer le test.
- Les noms de tests ne sont pas couverts (voir décision).
Si la règle change : une ADR et une proposition sous `## Proposées` qui disent ce qui est
vrai (voir C9).

**C5 — `populate` ne lie jamais le `.env` de Tessera (ADR-056, ADR-053), backend.**
- Un test `test_peupler_refuses_the_tessera_env` : une entrée `populate` qui désigne le
  `.env` de Tessera est refusée et journalisée, sans bloquer les autres entrées.

**C6 — Les services passent par `LLMProvider`, partout (ADR-017), backend.**
- Un test `test_sdk_is_imported_only_under_providers` échoue si `anthropic` ou
  `claude_agent_sdk` est importé hors de `services/providers/` (état actuel : conforme).
- Contrôle de mutation : `import anthropic` dans `services/validator.py` fait échouer.

### Règles partielles

**C7 — Compléter les gardes partielles, un cas par ligne.**
- Push : `test_the_push_command_never_carries_a_force_option` espionne l'appel git réel
  (arguments) au lieu de lire le source ; `--force-with-lease` doit aussi échouer
  (remplace `test_git_push.py:89`).
- ADR-064 : `test_tessera_never_writes_the_activity_file` échoue si le service lecteur
  ouvre le fichier en écriture.
- ADR-062 : un test par clause « port libre » et « ne tue jamais un processus existant ».
- ADR-061 : un test sur la sortie structurée de l'audit sécurité, comme pour le reviewer.
- ADR-047 : un test sur l'ordre `data-1`, `data-2`, `data-3` dans `design/charts/palette.ts`.

### Écarts

**C8 — À la main : dire quelle règle de longueur fait foi (`CLAUDE.md`).**
- `CLAUDE.md:111` dit la valeur que le test fait respecter (300), et que 200 est une
  direction, pas une limite.
- Un test `test_claude_md_states_the_enforced_length` (dans `test_consignes_coherentes.py`)
  extrait le nombre de la ligne et le compare à `PLAFOND_GENERAL`.
- Critère : changer `PLAFOND_GENERAL` sans changer `CLAUDE.md` fait échouer le test.

**C9 — À la main : mettre `CLAUDE.md` en accord avec la pratique.**
- `CLAUDE.md:59-60` : « fichiers en kebab-case » remplacé par ce que fait le dépôt
  (PascalCase pour les composants, camelCase pour les hooks et `lib/`).
- Critère : `grep -n "kebab-case" CLAUDE.md` ne rend plus la phrase sur les composants ;
  le choix est noté, pas appliqué par un renommage (voir plus bas).

**C10 — Mesurer « un test par fonction publique » (K7).**
- Un script de `scripts/` (nommé à la création) rend, par module de `services/` et
  `routers/`, les fonctions publiques que ni un fichier de test du même nom ni un import
  dans `backend/tests/` ne touche ; sortie en liste, exit 0.
- Critère : le script tourne sur le dépôt et rend une liste triée ; la liste est jointe au
  ticket, qui ne corrige rien.

**C11 — Une règle ESLint `no-explicit-any` nommée, un `any` retiré.**
- `eslint.config.js` active `@typescript-eslint/no-explicit-any` en `error` pour `src/**`.
- `useSupervisionReplay.test.ts:20` : `vi.fn<any>()` remplacé par un type précis et le
  `eslint-disable` retiré.
- Critère : `grep -rn "no-explicit-any" frontend/src` ne rend rien.

**C12 — Les écarts de texte de `contraintes.md` (E1-E7).**
Déjà portés par les tickets C4 et C5 de `adr.md` §5 pour E1, E2, E3 et E6. Reste à
y ajouter, sous `## Proposées` seulement : E4 (« selon la façon dont le projet est
arrivé », ADR-023), E5 (clause « services » à porter par C6) et E7 (« déclarer » devient
« déclarer ou prendre le défaut `agent_sdk` »).
- Critère : `git diff` de `contraintes.md` ne touche que `## Proposées`.

## Ce que cet audit ne tranche pas

- **ADR-044 : quelle règle de langue ?** Les identifiants et les docstrings sont mêlés,
  les noms de tests sont français dans leur grande majorité. Réécrire la règle (ce que la
  pratique fait) ou imposer un cliquet sur le neuf et traduire au fil de l'eau : choix de
  l'humain. Recommandé : un cliquet sur les docstrings neuves (C4), la règle réécrite pour
  les noms de tests, aucun renommage de masse.
- **`CLAUDE.md` ou renommage (K1) ?** Recommandé : le texte s'aligne sur le dépôt. Renommer
  des centaines de fichiers pour un style n'achète rien.
- **Les 49 fichiers entre 200 et 300 lignes** : pas de plafond déclaré, donc aucun
  ticket ; un cliquet à 200 casserait le cliquet de 300 qui marche.
- **Les règles « à lire »** (5) : leur test porte le bon nom, son corps n'a pas été
  relu. C'est la première chose à vérifier avant de tenir ces règles pour gardées.
- **L'ancienne rédaction de `contraintes.md` et `adr-audit.md` périmé** : déjà au
  ticket-650.
