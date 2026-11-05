---
id: ticket-820
title: "The git modules join services/git_workspace"
type: refactor
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-819]
estimated_days: 1
created: 2026-11-05
---

# ticket-820 — Les modules git à plat rejoignent `services/git_workspace/`

## Objectif

Les cinq modules à plat du domaine `git_workspace` (`git_attributes`, `git_runner`,
`prisma_conflits`, `regles_conflit`, `worktree_dossiers`) rejoignent le dossier existant, à
comportement constant.

## Contexte

ADR-076 ; section `git_workspace` de `memory/services-domaines.md`. Le dossier est déjà un domaine
et son `__init__.py` réexporte : celui-ci ne change pas, sauf son import de `_dossier_sans_hooks`.
Les gardes git (ADR-067) vivent dans `providers/`, hors de ce ticket.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py git_workspace`, relit le diff, lance la suite.
- Vérifie que `git_runner._dossier_sans_hooks`, importé par `git_workspace/__init__.py` et
  `socle.py`, se résout depuis le nouvel emplacement sans import circulaire.

## Critères d'acceptation

- [ ] Les cinq modules sont sous `services/git_workspace/`, aucun n'est resté à plat
- [ ] `A_DEPLACER` n'a plus d'entrée `git_workspace`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [ ] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [ ] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement, aucune API de `GitWorkspace` modifiée.

## Risques

Un import circulaire avec l'`__init__.py` du dossier, qui importe lui-même `git_runner` : si le
cycle apparaît, importer `git_runner` par son module plutôt que par le paquet, sans changer d'API.
