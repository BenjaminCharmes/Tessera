---
id: ticket-833
title: "The Tessera room counts the anomalies of each live run"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-839]
estimated_days: 1
created: 2026-11-05
---

# ticket-833 — La salle Tessera compte les anomalies de chaque run vivant

## Objectif

La salle des serveurs de Tessera dit, pour chaque run vivant, combien d'anomalies le détecteur y a
relevées (ADR-078).

## Contexte

`services/salle_tessera.py` assemble la salle depuis ce que le backend sait déjà, dont le registre
des runs (ticket-726) ; `models/salle_tessera.py` porte `RunVivant`. La salle « ne montre que ce
qu'elle sait » (ticket-766) : le compte vient de `RunActif.anomalies` (ticket-834), il n'est jamais
inventé.

## Solution

- `RunVivant.anomalies: int` (`models/salle_tessera.py`), lu de `len(run.anomalies)` à
  l'assemblage de la salle.
- `types/api.ts` et la ligne du run dans le composant de la salle : « n anomalie(s) » en ambre
  quand `n > 0`, rien quand `n = 0`.
- Le test de contrat des types (ticket-765) couvre le champ ajouté.

## Critères d'acceptation

- [ ] `test_salle_tessera_counts_the_anomalies_of_a_live_run` (backend) : 2 anomalies, `anomalies == 2`
- [ ] `test_salle_tessera_run_without_anomaly_has_a_zero_count`
- [ ] `test_salle_tessera_run_row_shows_nothing_for_zero_anomalies`
- [ ] `test_salle_tessera_run_row_says_1_anomaly_in_the_singular`
- [ ] `test_salle_tessera_run_row_says_2_anomalies_in_the_plural`
- [ ] `test_salle_tessera_anomaly_count_uses_amber_never_violet_text`

## Ce que ça ne fait pas

N'affiche pas le détail des anomalies (la cloche et le fil du run le font). Ne lit pas
`agent_events` : le compte est celui du registre.
