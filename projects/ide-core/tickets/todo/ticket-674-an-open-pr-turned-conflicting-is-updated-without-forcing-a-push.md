---
agent: architect
created: '2026-10-29'
depends_on:
- ticket-533
id: ticket-674
priority: low
status: todo
title: An open PR turned conflicting is brought up to date without forcing a push
type: design
---

## Contexte

Le ticket-533 évite les conflits entre PR d'une même file en faisant attendre
la livraison d'un ticket jusqu'au merge des PR déjà confiées au watcher. Une PR
rendue conflictuelle par autre chose (commit poussé à la main sur la base, PR
reprise au démarrage, délai d'attente dépassé) s'arrête toujours sur « à
rebaser » (ticket-452).

## Piste

Mettre la branche à jour par un **merge** de `origin/<base>` (jamais un rebase
suivi d'un push forcé, ADR-022), les conflits de `documentation.json` résolus
en union comme au rebase, puis pousser normalement. Le watcher n'a plus de
worktree à ce stade et `pushed_sha` change : la conception doit dire comment la
nouvelle tête reste liée à l'approbation (ADR-039, ticket-492) et si la PR se
merge seule (ADR-033 dit non pour une résolution de conflit).

## Critères d'acceptation

- [ ] Une conception tranche la liaison entre la nouvelle tête et l'approbation, et le sort du merge automatique
- [ ] Le livrable liste les tickets d'implémentation, chacun avec ses critères vérifiables

## Ce que ça ne fait pas

- N'implémente rien : ticket de conception.
