---
agent: codeur
created: 2026-10-27
depends_on:
- ticket-595
estimated_days: 0.75
id: ticket-596
plan: true
pr_number: null
priority: high
status: done
title: Finished agents vary what they do, walk to the room's coffee corner, and leave
  through the door when the run closes
type: feat
---

# ticket-596 — L'agent qui a fini vit sa vie, et tous partent à la fin du run

## Objectif
Deuxième ticket du « Bureau vivant » (`design/maquette/Bureau-vivant.dc.html`,
validée le 27/10) : un bureau qui a l'air vivant, sans rien inventer
(ADR-058) — le hasard ne change que la façon de montrer un état réel.

## Ce que dit la maquette
- Chaque pièce de travail a, en plus des cinq postes : une plante (ticket-593),
  un **coin café** (machine à café) et une **porte** au fond.
- Un agent `fait` (`postesDuRun.ts`) prend une activité au hasard, et en change
  de temps en temps (probabilité ~25 % toutes les ~2 s dans la maquette) :
  café assis à son poste (tasse levée), s'étire debout à côté de son poste
  (bras levés), ou va à la machine (trois places au plus ; au-delà, café à son
  poste). La machine fume quand quelqu'un s'y sert.
- Un agent qui change de place **marche** : translation horizontale en
  `transform`, transition en paliers (`steps`), ~1,8 s.
- Après `run_closed`, tous les agents marchent jusqu'à la porte et
  s'effacent ; la pièce se vide. Au ticket suivant d'une file, ils reviennent
  à leur poste.
- `prefers-reduced-motion` coupe transitions et animations (les positions
  changent sans marche).

## Solution proposée
- `lib/bureau/activites.ts` : l'activité d'un agent `fait` est tirée par une
  fonction injectable (`hasard`) pour être testable ; un minuteur dans la
  pièce la renouvelle. Aucune activité n'existe pour `libre` ni `occupe`.
- Les agents sont positionnés en absolu sur le sol de la pièce ; les postes
  restent fixes. Les sprites `MachineACafe.tsx` (ticket-583) et une nouvelle
  `Porte.tsx` sont réutilisés.
- Le Bureau garde la règle de l'ADR-058 : un agent `fait` ne tape jamais, un
  agent `libre` ne bouge pas.

## Critères d'acceptation
- [ ] Avec un `hasard` injecté, un agent `fait` peut prendre chacune des trois activités, et son libellé accessible la dit (« boit un café à son poste », « s'étire », « prend un café à la machine ») ; un test le vérifie
- [ ] Un agent `libre` ou `occupe` n'a jamais d'activité de pause ; un test le vérifie
- [ ] Quatre agents à la machine : trois y sont, le quatrième boit son café à son poste ; un test le vérifie
- [ ] La machine rend sa vapeur si et seulement si un agent y est ; un test le vérifie
- [ ] Après `run_closed`, chaque agent a la position de la porte et une opacité nulle, et n'est plus focalisable ; un test le vérifie
- [ ] Sous `prefers-reduced-motion: reduce`, la règle CSS de marche n'a plus de transition ; `design/bureau/sources.test.ts` ou un test de la feuille le vérifie
- [ ] Le diff ne modifie aucun fichier de `backend/`