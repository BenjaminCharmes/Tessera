# Classement de `backend/src/tessera/services/` par domaine

Détail d'ADR-076. Photo de départ : `scripts/domaines_services.py` (ticket-826)
en reprend la table, et c'est lui que lisent le test et le script de
déplacement ; ce fichier se supprime au ticket-825.

## Règle de dépendance

Les domaines sont ordonnés (1 = le plus bas). Un module importe son domaine
ou un domaine de rang plus bas, jamais un rang plus haut. `routers/` importe
tout ; `models/` n'importe aucun domaine. Un import à contresens se mesure
par `test_sens_des_imports.py` (cliquet : les écarts connus ne font que
diminuer, un écart corrigé se retire de la liste).

| Rang | Domaine | Rôle |
|---|---|---|
| 1 | `noyau` | base, événements, journaux, processus, texte et diff sans règle métier |
| 2 | `projets` | lire un projet : manifeste, tickets, ADR, artefacts, autonomie |
| 3 | `usage` | coûts, quotas, appels d'agent |
| 4 | `provisioning` | mise en ligne (dossier existant, inchangé) |
| 5 | `gardes` | contrôles sans modèle : termes interdits, secrets, critères protégés, politique |
| 6 | `git_workspace` | tout ce qui parle à git en local (dossier existant) |
| 7 | `worktrees` | cycle de vie des worktrees de run |
| 8 | `github` | API GitHub, issues, workflow de proposition |
| 9 | `providers` | LLMProvider et gardes d'outils (dossier existant, inchangé) |
| 10 | `verification` | lancer les tests, contrôle visuel, captures |
| 11 | `verdicts` | reviewer, audit sécurité, validateur |
| 12 | `agents` | registre, exécution d'un agent, chat |
| 13 | `documentation` | service de documentation par lot |
| 14 | `creation_projet` | créer, importer, cloner, retirer un projet |
| 15 | `livraison` | rebase, PR, CI, merge, surveillance |
| 16 | `pipeline` | les phases et l'orchestration d'un run |
| 17 | `file` | la file, le mode autonome, le planificateur |
| 18 | `supervision` | processus, services, apps, salles |

## Règles de forme

- Un domaine est `services/<domaine>/`. Son `__init__.py` reste vide (aucune
  réexportation, pas de travail à l'import) ; les trois dossiers existants
  gardent le leur.
- Un import entre domaines vise le module : `tessera.services.livraison.ci_watcher`.
- Un module nouveau naît dans son domaine. Tant que son dossier n'existe pas,
  il s'inscrit dans la table du test, sinon le test échoue.
- `tessera/agents/` disparaît. `github_sync.py` rejoint `github/` ; le test
  refuse tout paquet de premier niveau de `tessera/` hors `models`, `services`,
  `routers`, `utils`.
- Le tableau est la décision de départ, la case d'un module non : si le test
  mesure un import montant, reclasser le module (ou l'importé) vaut mieux
  que l'écart listé. Trois écarts sur la même paire de domaines disent que le
  tableau se trompe.

## Pièges connus du déplacement

- `captures.py` : `Path(__file__).resolve().parents[4]` devient `parents[5]`.
- `Makefile` et `scripts/tessera.ps1` lancent `python -m tessera.services.ticket_check`.
- `scripts/prochain_numero.py`, `scripts/mesure_calculs.py` et
  `backend/tests/conftest.py` importent des modules déplacés.
- Les tests patchent par chaîne (`monkeypatch.setattr("tessera.services.x.f")`) :
  une réécriture qui rate une chaîne ne casse rien à l'import, et le patch
  ne s'applique plus. Aucune façade à l'ancien chemin.
- Les agents n'émettent aucune commande git en écriture : le déplacement se
  fait par `mv`, git reconnaît la renommée à la similarité.

## Les modules, par domaine

`noyau` (25) : arret_de_service, database, database_chat, database_events,
database_runs, database_usage, diff_changements, diff_sections, event_hub,
groupe_de_processus, journal_attente, journal_du_texte, journal_en_attente,
journal_pipeline, lancement, minuteur_d_etape, modeles_par_defaut,
numerotation, pipeline_events, prompt_loader, racine_depot,
reecriture_des_numeros, releve_du_diff, shell_detection, statut_suggere.

`projets` (11) : adr, artifact_snapshot, artifacts, autonomie, manifeste,
manifeste_ecriture, online_declaration, project_loader, ticket_archive,
ticket_check, ticket_service.

`usage` (8) : agent_calls, cost_aggregate, cost_calculator, quota_exhaustion,
quota_registry, quota_tracker, session_limit, usage_stats.

`provisioning` : inchangé.

`gardes` (6) : config_tests_touchee, contraintes_touchees, critere_protege,
politique_run, secrets_diff, termes_interdits.

`git_workspace` : son contenu, plus 5 modules : git_attributes, git_runner,
prisma_conflits, regles_conflit, worktree_dossiers.

`worktrees` (8) : preparation_worktree, reprise_orphelin, reprise_worktrees,
run_dans_worktree, run_worktree, run_worktree_populate, temporary_worktree,
worktree_politique.

`github` (8, plus `agents/github_sync.py`) : forge, github_retry,
github_service, github_workflow, issues_agent_ready, proposal_workspace,
sync_map, ticket_proposal.

`providers` : inchangé.

`verification` (15) : app_du_run, build_warning, captures, captures_config,
captures_session, chaines_de_test, commande_chainee, commande_effective,
controle_visuel, detail_du_delai, erreur_de_sortie, groupe_d_etape,
outil_introuvable, sortie_de_test, test_runner.

`verdicts` (12) : reviewer_schema, security_auditor, security_contexte,
security_schema, validator, validator_binary, validator_cited_dirs,
validator_cited_files, validator_decisions, validator_file_extensions,
validator_schema, verdict_reviewer.

`agents` (6) : agent_creator, agent_registry, agent_runner, carte_du_depot,
chat_service, chat_suggestion.

`documentation` (12) : documentation, documentation_base,
documentation_claude_md, documentation_code, documentation_description,
documentation_diff, documentation_editions, documentation_preuve,
documentation_reponse, documentation_selection, documenteur_run,
roles_documentation.

`creation_projet` (10) : extraction_claude_md, gabarits_projet, git_clone,
git_link, project_analyzer, project_creator, project_from_template,
project_importer, project_removal, template_claude_md.

`livraison` (29) : attente_dependance, attente_des_merges, branch_cleanup,
ci_watcher, controle_tete, journal_ci_watcher, livraison, livraison_apres,
livraison_arrets, livraison_conflit, livraison_evenements, livraison_merge,
livraison_possible, livraison_rebase, livraison_resultat, livreur_run,
mise_a_jour_branche, mise_a_jour_pr, pr_status_cache, pr_statuses,
realignement_base, renumeroter, reprise_marqueur, reprise_outils,
reprise_surveillance, resolveur_conflit, retest_apres_rebase, sha_approbation,
surveillance_run.

`pipeline` (31) : assemblage_run, controles_depart, dialogue, etape_de_capture,
orchestrator, pipeline_approbation, pipeline_branche, pipeline_capture,
pipeline_contraintes, pipeline_controles, pipeline_critere_protege,
pipeline_documentation, pipeline_livraison, pipeline_outcomes, pipeline_plan,
pipeline_production, pipeline_rangement, pipeline_reprise, pipeline_run,
pipeline_testeur, pipeline_text, pipeline_tickets, preparation_run,
refus_precedent, run_executor, run_lock, run_recorder, run_registry,
run_status, signalements_en_attente, ticket_diff.

`file` (7) : file_vivante, pipeline_file, pipeline_file_livraison,
pipeline_file_reprise, pipeline_file_tour, pipeline_fin_de_file, planner.

`supervision` (14) : activite_produit, arbre_de_processus,
attribution_processus, declarations_activite, eveil, inventaire_apps,
ports_declares, process_registry, project_overview, salle_tessera,
service_etat, services_sans_port, signature_commande, sonde_systeme.

Total : 207 modules à plat, contre 203 dans le ticket-776 (trois tickets ont
ajouté des modules depuis). Le test de couverture du ticket-826 est l'arbitre :
un module absent de ce fichier s'y ajoute, un module inexistant s'en retire.

## Ordre des déplacements

Du moins importé au plus importé, pour que chaque ticket réécrive peu de
fichiers : supervision, documentation, file, verdicts, agents, creation_projet,
verification, github, worktrees, usage, gardes, git_workspace, livraison,
pipeline, projets, noyau. Chaque ticket attend le merge du précédent
(`depends_on`), et la suite se lance dans une file à elle, quand aucune autre
PR du projet n'est ouverte : un déplacement et une PR qui touche les mêmes
fichiers se rebasent mal.
