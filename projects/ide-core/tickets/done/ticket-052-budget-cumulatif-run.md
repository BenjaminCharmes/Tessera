---
id: ticket-052
title: "Plafond de dépense cumulée d'un run autonome"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-046]
estimated_days: 1
created: 2026-09-15
---

# ticket-052 — Budget cumulatif par run

Ferme l'**issue #61**, relevée par la revue finale de ticket-044.

## Objectif

Borner la dépense d'une **exécution complète**, et pas seulement celle d'un
appel isolé.

## Contexte

`LLM_MAX_BUDGET_USD` (défaut 1.0) est passé à `ClaudeAgentOptions.max_budget_usd`,
donc il borne **un appel `query()`**.

Or `run_autonomous` enchaîne jusqu'à `max_tickets=5` tickets, chacun sur N tours
de revue, chacun mobilisant codeur + reviewer + testeur + auditeur sécurité +
validateur + doc-updater. Le plafond effectif d'un seul clic sur « mode
autonome » se chiffrait donc en dizaines de dollars-équivalents de quota, sans
aucun garde-fou agrégé.

C'est précisément la ressource que l'abonnement rend finie : un plafond par
appel ne protège pas ce que le design prétend protéger.

## Solution livrée

1. **`AgentResult.cost_usd`** — le coût n'existait que dans la branche qui
   écrit en base, donc uniquement lorsqu'un `run_id` était fourni. Il est
   désormais calculé dans tous les cas, y compris en mode autonome où il n'y
   en a pas.
2. **Compteur sur l'orchestrateur** — `record_spend`, `spent_usd`,
   `budget_exhausted`, alimentés par les étapes codeur et reviewer.
3. **Point d'arrêt** — `run_autonomous` vérifie le plafond **entre** les
   tickets. Interrompre un ticket en cours laisserait son travail non commité,
   ce que l'isolation par branche interdit (ADR-018).
4. **`RUN_MAX_BUDGET_USD`** — défaut 5.0 ; `0` désactive la borne.

## Critères d'acceptation

- [x] `AgentResult` porte le coût réel de l'appel
- [x] Le coût est calculé même sans `run_id`
- [x] Un run autonome s'arrête au dépassement du plafond cumulé
- [x] Un plafond à `0` laisse le run aller au bout
- [x] L'arrêt se fait entre deux tickets, jamais au milieu d'un
- [x] `uv run pytest -q` et `uv run mypy src/` verts

## Dépendances

`ticket-046` — les étapes décomposées sont le point où le coût se collecte.

## Estimation

**1j**.

## Non couvert

Le suivi de quota côté abonnement (`RateLimitEvent` → `QuotaTracker`) évoqué
dans l'issue reste à faire : ce ticket borne la **dépense estimée**, pas le
quota réel rapporté par le fournisseur.
