---
agent: codeur
created: 2026-10-29
depends_on: []
id: ticket-685
priority: medium
status: done
title: Queue and autonomous run modes leave the Orchestrator class
type: refactor
---

# ticket-685 — `run_queue` et `run_autonomous` hors de la classe `Orchestrator`

## Objectif
La classe ne porte plus la boucle de file ni la boucle autonome ; elle les
délègue à un module à part, comme les modules `pipeline_*` le font déjà.

## Contexte
`services/orchestrator.py` fait 1299 lignes (`docs/audit/refactos.md` §1).
`run_queue` en occupe 274 (650-923) : plafond de dépense, arrêt demandé, saut
d'un ticket terminé, événement `QUEUE_PROGRESS`, appel du run, et trois
politiques d'arrêt après un ticket non approuvé. `run_autonomous` en ajoute 67.

## Critères d'acceptation
- [ ] `run_queue` et `run_autonomous` sont définis dans un module séparé ; les méthodes de `Orchestrator` du même nom ne sont que des délégations (`grep -n "def run_queue" backend/src` en rend deux, la seconde de moins de 10 lignes)
- [ ] La boucle de file est découpée en étapes nommées (plafond effectif, arrêt demandé, saut d'un ticket terminé, arrêt après un ticket non approuvé) ; la PR cite la longueur de chaque fonction du module, mesurée par un `ast` jetable non commité, aucune ne dépassant 80 lignes
- [ ] L'entrée de `services/orchestrator.py` dans `PLAFONDS` (`backend/tests/test_longueur_des_fichiers.py`) est baissée à 1000 ou moins, sans autre modification du cliquet
- [ ] Les signatures publiques, les événements émis et l'ordre des vérifications entre deux tickets (ADR-018, ADR-020) sont inchangés : les tests existants de file et de mode autonome passent sans changement de leurs attendus (seule une cible de `patch` peut changer de nom)
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne change aucune politique d'arrêt, aucun plafond, aucun message de journal
- Ne touche pas à `_run_pipeline`, `_mener_le_run` ni `_run_rounds` (ticket-668)
- Ne déplace pas la fin de file (ticket-686)