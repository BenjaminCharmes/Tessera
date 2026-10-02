---
agent: codeur
created: 2026-10-02
depends_on: []
estimated_days: 0.5
id: ticket-328
pr_number: null
priority: high
status: done
title: A background delivery always reports how it ended, even when it fails or hangs
type: fix
---

# ticket-328 — Une livraison en tâche de fond dit toujours comment elle a fini

## Objectif

Qu'une PR confiée à `CIWatcher` ne reste jamais ouverte sans que rien ne le
dise.

## Contexte

Le 2026-10-02, la PR #23 de `carriere` (ticket-020) a été ouverte à 15:07:50
UTC et confiée à `CIWatcher`. Ensuite, plus rien : ni merge, ni
`ci_merge_done`, pendant plus de quatre heures, alors que le backend tournait
sans interruption. Rejouée à la main, `livrer_phase_2(23)` a mergé du premier
coup : la logique de merge est saine.

`CIWatcher._surveiller_impl` (`services/ci_watcher.py`, vers les lignes
120-135) attrape toute `Exception` et se contente de la journaliser
(`_logger.exception`). Aucun `ci_merge_done` n'est émis dans ce cas. Une
tâche qui resterait bloquée n'en émet pas non plus.

## Solution proposée

- Une exception dans la phase 2 émet `ci_merge_done` avec `merged: false` et
  un `arret` qui nomme l'erreur. Le ticket passe en `blocked` (ADR-051 : sans
  relance).
- La phase 2 entière est bornée dans le temps (attente de CI comprise). Au-delà,
  même `ci_merge_done` avec un `arret` qui dit « délai dépassé ».

## Critères d'acceptation

- [ ] Un test vérifie qu'une exception levée par `livraison_phase_2` émet
      `ci_merge_done` avec `merged: false` et un `arret` qui contient le
      message de l'exception
- [ ] Un test vérifie que le ticket passe alors en `blocked`
- [ ] Un test vérifie qu'une phase 2 qui ne rend pas la main dans le délai
      émet `ci_merge_done` avec un `arret` qui dit que le délai est dépassé
- [ ] Un test vérifie qu'une annulation à l'arrêt du backend n'émet pas de
      faux `ci_merge_done` d'échec

## Dépendances

Aucune.