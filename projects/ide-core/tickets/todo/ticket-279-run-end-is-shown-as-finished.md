---
id: ticket-279
title: "A finished run looks finished: stage strip, timer, close button and verdict lines"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-01
---

# ticket-279 — Un run terminé a l'air terminé

## Objectif

Qu'après « PR #N mergée », la vue du run et la Supervision disent que le run
est fini, et que le Pipeline log rende les verdicts tels qu'ils sont.

## Contexte

Retour d'usage du 2026-10-01, sur `freelance` et `carriere` :

- `streamState.applyEvent` met `etape` à `"livraison"` sur `livraison_started`
  et rien ne la remet à `null` : ni `livraison_done` ni `run_closed`.
  `StageStrip.etatEtape` renvoie `"active"` dès que `etape === id`
  (`AgentPanel/StageStrip.tsx:72`), avant de regarder `livraison_done` : le
  rond Livraison clignote en bleu après le merge. Même chose pour Docs quand
  aucun `doc_updated` n'est émis.
- `SupervisionView/Chrono.tsx` calcule `Date.now() - demarre_a` chaque seconde
  sans condition d'arrêt : le temps court après `run_closed`.
- La croix « Effacer le run » (`AgentPanel/index.tsx:105-114`) apparaît dès
  `status === "done"`, donc dès `pipeline_done`, pendant la doc et la
  livraison. Cliquée là, le prochain événement du run recrée la carte via la
  branche « run inconnu » de `supervisionEvents.majDesRuns`, avec un chrono
  reparti de zéro.
- `validation_done` est émis avec `verdict`, sans clef `approved`
  (`backend/src/tessera/services/pipeline_stages.py:505-515`) ; le Pipeline log
  lit `ev.data["approved"]` (`BottomPanel/index.tsx:86`) et affiche donc
  toujours « Validation : refusée ».
- `test_result` n'a pas de ligne dans `eventToLine` : une suite rouge renvoie
  au codeur sans revue (ticket-098), et le log montre trois tours de codeur
  d'affilée sans dire pourquoi.
- La carte de fin (`PipelineSummary`) reste sur « Revue terminée — livraison
  en cours » sans jamais dire ce que la livraison a produit.

## Solution proposée

- `run_closed` remet `etape` à `null` ; une étape terminée par son événement
  de fin (`livraison_done`, `doc_updated`, `documentation_failed`) n'est plus
  `"active"`.
- Le chrono se fige à l'heure de `run_closed`.
- La croix et « Fermer » partagent la même condition : `runClosed` ou
  `status === "error"`.
- Le backend ajoute `approved: verdict == "APPROVED"` à `validation_done` ; le
  frontend le lit, ou retombe sur `verdict` s'il manque.
- `eventToLine` rend `test_result` (« Tests : verts » / « Tests : rouges —
  retour au codeur »).
- `PipelineSummary` affiche, après `livraison_done`, le numéro de PR et
  « mergée », ou la cause d'arrêt (`arret`).

## Critères d'acceptation

- [ ] Un test de `streamState` vérifie qu'après `livraison_started` puis
      `run_closed`, `etape` vaut `null`, et un test de `StageStrip` qu'une
      étape Livraison suivie de `livraison_done` n'est pas rendue active
- [ ] Un test de `Chrono` vérifie que la durée affichée ne change plus une
      fois le run clos
- [ ] Un test d'`AgentPanel` vérifie que la croix « Effacer le run » est
      absente quand `status === "done"` et `runClosed === false`
- [ ] Un test backend vérifie que `validation_done` porte `approved: true`
      pour un verdict `APPROVED` et `false` pour `CHANGES_REQUESTED`
- [ ] Un test de `BottomPanel` vérifie une ligne pour un `test_result` rouge,
      et « Validation : approuvée » pour un `validation_done` sans `approved`
      mais de verdict `APPROVED`
- [ ] Un test de `PipelineSummary` vérifie l'affichage du numéro de PR et de
      `arret` issus de `livraison_done`

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

`etape` sert aussi hors Supervision (`useRunActif`) : la remise à `null` sur
`run_closed` doit y tenir aussi.
