---
agent: codeur
created: 2026-11-05
depends_on:
- ticket-862
estimated_days: 1
id: ticket-863
pr_number: null
priority: medium
status: done
title: Every tooled agent gets a signaler tool served by the backend
type: feat
---

# ticket-863 — Tout agent outillé reçoit `signaler`, servi par le backend

## Objectif

Un agent qui rencontre un défaut de Tessera le signale au backlog d'ide-core, sans écrire dans
ce dépôt et sans pouvoir désigner lui-même le projet source.

## Contexte

ADR-080, spec §3. `providers/ask_user.py` sert déjà `mcp__tessera__ask_user` depuis un serveur
MCP in-process ; le nom qualifié doit figurer dans `allowed_tools`, sinon le SDK refuse
chaque appel. Les signalements s'écrivent par `signalements_en_attente` (ticket-421), jamais
par l'agent (ADR-031).

## Ce qu'il faut faire

- `providers/signaler.py` : `build_signaler_tool(contexte)` et `SIGNALER_TOOL_NAME =
  "mcp__tessera__signaler"`, ajouté au serveur `tessera` à côté d'`ask_user`. `contexte` porte
  projet, ticket, rôle, confidentialité, compteurs du run : lus du run, jamais des arguments.
- Description de l'outil (français) : quand signaler (défaut de Tessera après tentative de
  contournement : garde trop stricte, outil cassé, consigne contradictoire), quand ne pas le
  faire (demande de fonctionnalité du projet, difficulté du ticket).
- Le handler appelle `valider_signal` ; accepté : mise en forme du corps (source
  `agent:<rôle>@<ticket>`, nature `bug`) et `signalements_en_attente.mettre_en_attente` ; la
  réponse à l'agent dit « reçu » ou la raison du refus. Aucun refus ne fait échouer le tour.
- Branché dans `agent_runner` et `pipeline_production` pour tout rôle qui reçoit des outils ;
  ni `lecons`, ni `validateur`, ni `superviseur` (aucune boucle).

## Critères d'acceptation

- [ ] `test_signaler.py::test_accepted_report_is_queued_not_written_into_the_repository`
- [ ] `test_signaler.py::test_source_project_comes_from_the_run_not_the_arguments`
- [ ] `test_signaler.py::test_refusal_is_returned_to_the_agent_without_failing_the_turn`
- [ ] `test_signaler.py::test_tool_name_is_in_allowed_tools_for_tooled_roles`
- [ ] `test_signaler.py::test_toolless_roles_and_the_supervisor_do_not_get_it`
- [ ] `test_signaler.py::test_professional_project_report_carries_no_free_text`

## Ce que ça ne fait pas

Ne trie pas le signalement (ticket-855). N'ajoute aucune route HTTP : un agent n'appelle jamais
l'API.