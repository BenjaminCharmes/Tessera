---
agent: codeur
created: 2026-10-28
depends_on: []
estimated_days: 1
id: ticket-623
pr_number: null
priority: medium
status: done
title: In the Bureau, the architect has its own look and the plan step is drawn at
  the whiteboard
type: feat
---

# ticket-623 — L'architecte et le plan se voient dans le Bureau

## Objectif
Qu'on distingue, dans la pièce d'un projet, l'architecte du codeur, et qu'on voie
quand un plan se prépare.

## Contexte
Le 28/10, Benjamin n'a vu aucune action de l'architecte. Il tient le poste du
codeur (`posteDuRole` dans `lib/bureau/sallesCommunes.ts`, `transitionDe` dans
`lib/bureau/postesDuRun.ts`), avec la même tenue (`lib/bureau/physique.ts`) et le
même libellé « Codeur » (`lib/bureau/libelleDuPoste.ts`).

Le tour de plan (`plan: true`) émet `agent_started` puis `agent_done` avec
`agent: "codeur"` et `data.phase: "plan"` (`backend/src/tessera/services/pipeline_plan.py`).
La pièce le montre aujourd'hui comme du code.

## Solution proposée
- L'architecte garde le poste du codeur, puisqu'il le remplace sur un ticket
  `design`. Il prend sa propre tenue et le libellé « Architecte » tant que le
  dernier `agent_started` du poste vient de lui.
- Pendant le tour de plan, l'agent du poste se tient debout devant le tableau
  blanc de la pièce, avec l'activité « prépare le plan ». Le tableau existe déjà
  (`TableauDesCriteres`) : aucun nouvel objet n'est dessiné (ADR-058).

## Critères d'acceptation
- [ ] `lib/bureau/physique.ts` donne à `architect` une tenue différente de celle de `codeur`, et un test le vérifie
- [ ] Un test vérifie que le poste du codeur se lit « Architecte, … » après un `agent_started` d'`agent: "architect"`, et « Codeur, … » après un `agent_started` d'`agent: "codeur"`
- [ ] Un test de `lib/bureau/activites.ts` vérifie qu'entre un `agent_started` et un `agent_done` portant `data.phase: "plan"`, l'activité de l'agent du poste est « prépare le plan », ancrée au tableau blanc
- [ ] Un test vérifie qu'après l'`agent_done` du plan, l'agent revient à son poste

## Ce que ça ne fait pas
- Ne change rien au backend : les événements existent.
- Ne dessine ni la documentation, ni la livraison, ni le résolveur : c'est le ticket-624.