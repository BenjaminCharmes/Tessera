---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 0.5
id: ticket-277
pr_number: 157
priority: medium
status: done
title: The codeur deletes a file with rm instead of emptying it, and an emptied tracked
  file is flagged
type: fix
---

# ticket-277 — Supprimer un fichier, pas le vider

## Objectif

Qu'un fichier que le codeur veut supprimer disparaisse du dépôt, au lieu d'y
rester vide.

## Contexte

Constaté le 2026-10-01 sur le ticket-258 : le codeur devait supprimer
`frontend/src/hooks/useUsage.ts` et son test. Il les a **vidés** (1 et 2
octets) au lieu de les supprimer. Le commit les montre « 143 lignes
supprimées », reviewer et validateur ont lu une suppression, mais le fichier de
test vide a fait échouer vitest en CI (« aucune suite de tests »). Corrigé à la
main.

`git rm` est refusé aux agents (`git_guard.py`, ADR-027), mais un `rm` simple
dans le projet est permis (ADR-031). Le prompt du codeur
(`agents/prompts/codeur.md`) ne dit rien de la suppression.

## Solution proposée

- `agents/prompts/codeur.md` : une ligne — « Pour supprimer un fichier, `rm
  <chemin>` ; ne jamais le vider : un fichier vide reste dans le dépôt. »
- Au commit d'un run (`GitWorkspaceService.commit_all` ou son appelant), un
  fichier **suivi** que le run a ramené à un contenu vide ou blanc est signalé
  dans le rapport du run (événement ou ligne de log lisible à l'écran), sans
  bloquer le commit.

## Critères d'acceptation

- [ ] `agents/prompts/codeur.md` contient la consigne de supprimer par `rm`
      plutôt que de vider.
- [ ] Un test montre qu'un fichier suivi vidé pendant un run est signalé.
- [ ] Un test montre qu'un fichier supprimé par `rm` pendant un run n'est pas
      signalé et que sa suppression est commitée.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Un fichier légitimement vide (`__init__.py`) créé vide n'est pas concerné :
seul un fichier suivi **ramené** à vide est signalé.