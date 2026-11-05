---
id: ticket-832
title: "The Bureau marks an agent whose run has an anomaly"
type: feat
status: done
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-839]
estimated_days: 1
created: 2026-11-05
---

# ticket-832 — Le Bureau marque l'agent dont le run a une anomalie

## Objectif

Un agent au travail dont le run porte une anomalie se distingue d'un agent qui travaille
normalement, d'un coup d'œil, dans le Bureau (ADR-078, ADR-058).

## Contexte

ADR-058 : un état dessiné vient d'une donnée du store de run ou de l'API ; sans donnée, rien. La
donnée existe : `RunActif.anomalies` (ticket-834). ADR-070 : un état est un jeton `etat-*` fixe, de
jour comme de nuit, dessiné avec le moteur de `lib/bureau/sprites/` en `<use>` du `<defs>` commun.
ADR-026 : l'attente à vérifier est ambre. Un marqueur d'état existe déjà pour « question » et
« figé ? » : celui-ci s'y range, il ne crée ni disposition ni sprite d'agent.

## Solution

- Un jeton `etat-anomalie` (ambre) dans `sprites-theme.css`, et son calque dans le moteur, en
  `<use>` partagé.
- Le Bureau pose ce marqueur sur l'agent du run quand `anomalies.length > 0`, et le retire
  quand la liste est vide ou que le run se ferme. Le nombre d'anomalies figure dans le nom
  accessible du marqueur, pour le lecteur d'écran et la Liste.
- Un marqueur de plus par run, jamais par anomalie.

## Critères d'acceptation

- [x] `test_bureau_shows_the_anomaly_marker_when_the_run_has_one_anomaly`
- [x] `test_bureau_shows_no_anomaly_marker_when_the_run_has_none`
- [x] `test_bureau_shows_one_marker_for_a_run_with_three_anomalies` et son nom accessible dit
      « 3 anomalies »
- [x] `test_bureau_removes_the_marker_when_the_run_closes`
- [x] `test_anomaly_marker_is_a_use_of_the_shared_defs_and_adds_no_inline_path` : le plafond de
      nœuds SVG du Bureau (ADR-070) reste respecté
- [x] `test_etat_anomalie_token_is_amber_and_identical_by_day_and_by_night`
- [x] `test_the_marker_does_not_draw_an_agent_for_a_run_without_activity` : ADR-058 et ADR-064
      tiennent

## Ce que ça ne fait pas

Ne dessine pas d'agent qui n'existe pas dans les données, ne change aucune disposition de salle,
n'ajoute aucun autre état.
