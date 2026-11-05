---
id: ticket-819
title: "The guard modules move to services/gardes"
type: refactor
status: done
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-818]
estimated_days: 1
created: 2026-11-05
---

# ticket-819 — Les modules de garde passent dans `services/gardes/`

## Objectif

Les six modules du domaine `gardes` (termes interdits, secrets, critères protégés, politique de
run, configuration des tests) vivent dans `services/gardes/`, à comportement constant.

## Contexte

ADR-076 ; section `gardes` de `memory/services-domaines.md`. Ces modules échouent fermés (ADR-050,
ADR-072). Le ticket-798 (le hook `pre-push` lit les termes interdits par le backend) touche
`termes_interdits` : sa PR est mergée avant ce ticket. Le hook `pre-push` appelle peut-être le
module par son chemin : le relire.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py gardes`, relit le diff, lance la suite.
- Relit `scripts/hooks/pre-push` et `.github/workflows/ci.yml` pour tout appel à un module déplacé ;
  `.github/workflows/` se refuse en écriture aux agents (ADR-067) : s'il faut le changer, le dire
  dans le commit plutôt que d'y toucher.

## Critères d'acceptation

- [x] Les six modules de la section `gardes` sont sous `services/gardes/`, aucun n'est resté à plat
- [x] `A_DEPLACER` n'a plus d'entrée `gardes`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [x] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [x] Les trois portes de termes interdits (push pipeline, `pre-push`, CI) appellent toujours le
      bon module
- [x] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement d'une garde.

## Risques

Une porte qui ne trouve plus son module refuse (ADR-050) : le hook bloquerait tout push. Le test
d'un push réel n'est pas possible ici : le hook se lance à la main une fois, hors du run.

## Notes de réalisation

Le domaine compte neuf modules, pas six : `scripts/domaines_services.py` fait foi. `scripts/hooks/pre-push` appelle `tessera.coffre_cli`, qui ne bouge pas, et `.github/workflows/ci.yml` n'appelle aucun module déplacé : ni l'un ni l'autre ne change. `scripts/seconde_revue_corpus.py` cite `secrets_diff.py` comme motif de nom de fichier, qui reste valable. `docs/architecture.md` suit le nouveau chemin de `worktree_politique`.
