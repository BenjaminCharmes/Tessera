---
id: ticket-492
title: "An approval is bound to the commit it reviewed, and nothing else gets merged under it"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-16
---

# ticket-492 — Une approbation vaut pour un commit précis

## Objectif

Ce qui est mergé est exactement ce que le reviewer et le validateur ont lu.

## Contexte

Aujourd'hui, `APPROVED` est un état du run, pas une propriété d'un commit.
Entre l'approbation et le merge, la branche peut changer : commit de
rangement du pipeline, rebase sur `develop`, résolution de conflit
(ADR-033), ou un push fait par une session humaine sur la branche du run.
`CIWatcher` merge la PR dès que la CI est verte, sans savoir si sa tête est
encore le commit approuvé. L'ADR-033 couvre la résolution de conflit (elle
n'est jamais mergée seule), pas les autres cas.

## Solution proposée

1. **À l'approbation**, le SHA de tête de la branche du run est enregistré
   dans `pipeline_runs` (`approved_sha`).
2. **À la livraison (phase 1)**, avant le push : les commits entre
   `approved_sha` et la tête doivent tous être des commits de rangement du
   pipeline, dont le diff ne touche que `projects/<id>/tickets/**` et
   `memory/pipeline-log.md`. Tout autre commit met le run en `blocked`, avec
   dans le journal : « la branche a changé depuis l'approbation : <sha> ».
   Le SHA poussé est enregistré (`pushed_sha`).
3. **Au merge (phase 2)**, `CIWatcher` compare la tête de la PR à
   `pushed_sha`. Si elle diffère, il ne merge pas : le ticket passe en
   `blocked`, la PR reste ouverte, et le journal dit pourquoi. Un rebase fait
   par le pipeline lui-même (ticket-457) met `pushed_sha` à jour.

## Ce que ça ne fait pas

- Ne relance pas une relecture automatique : un run bloqué pour cette raison
  se relit par un nouveau run, ou à la main.
- Ne touche pas au résolveur de conflit (ADR-033), déjà couvert.

## Critères d'acceptation

- [ ] Un test vérifie qu'un commit de code ajouté après `APPROVED` met le run
      en `blocked` sans push
- [ ] Un test vérifie que les commits de rangement du pipeline ne bloquent pas
- [ ] Un test vérifie que `CIWatcher` ne merge pas une PR dont la tête n'est
      plus `pushed_sha`, et que le ticket passe en `blocked`
- [ ] Un test vérifie qu'un rebase fait par le pipeline met `pushed_sha` à
      jour et que le merge suit
- [ ] La règle est ajoutée à `memory/contraintes.md` (Livraison et autonomie)
