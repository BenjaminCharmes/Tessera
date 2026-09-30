---
id: ticket-270
title: "Bookkeeping written after delivery is no longer stranded on the merged ticket branch"
type: fix
status: todo
pr_number: null
priority: critical
agent: codeur
plan: true
depends_on: []
estimated_days: 1
created: 2026-09-30
---

# ticket-270 — Le commit de suivi écrit après la livraison n'est plus perdu

## Objectif

Qu'aucun fichier ne disparaisse parce qu'il a été commité sur une branche de
ticket après que la livraison l'a mergée.

## Contexte

Constaté le 2026-09-30 sur le ticket-265. L'historique local de sa branche :

```
9ea23bb fix: ticket-265 — …                  ← commit du run
c3c762c chore: tessera pipeline bookkeeping   ← poussé, dans la PR #135
ebd9cc8 chore: tessera pipeline bookkeeping   ← APRÈS le merge de la PR
```

`ebd9cc8` a été créé **après** que la livraison a poussé la branche, ouvert la
PR #135 et l'a mergée. Il n'a jamais été poussé. Il contenait :
- le `pr_number` du ticket-265 dans son fichier `done/` ;
- trois tickets écrits pendant le run (non suivis au démarrage, balayés par ce
  commit de suivi).

Revenir ensuite sur `develop` a fait disparaître ces trois fichiers de l'arbre
— ils n'existaient plus que dans un commit orphelin. Ils ont été retrouvés à la
main.

Le `pr_number` d'un ticket livré n'arrive donc jamais sur `develop`, et tout ce
que ce dernier commit de suivi balaie est perdu à la sortie de la branche.

## Solution proposée

À concevoir au tour de plan (`plan: true`). Pistes :

- Écrire le suivi qui dépend de la livraison (`pr_number`, journal) **avant**
  le push, et ne plus rien commiter sur la branche une fois la PR mergée ; ou
- quand un suivi reste à écrire après un merge, le faire sur la base mise à
  jour, jamais sur la branche mergée ; et
- dans tous les cas, ne pas balayer dans un commit de suivi un fichier non
  suivi au démarrage du run (règle déjà tenue pour le commit du ticket).

## Critères d'acceptation

- [ ] Un test montre qu'après une livraison mergée, la branche du ticket n'a
      aucun commit absent de la branche distante.
- [ ] Un test montre que le `pr_number` d'un ticket livré figure dans le fichier
      du ticket tel qu'il est poussé.
- [ ] Un test montre qu'un fichier non suivi au démarrage du run n'entre dans
      aucun commit de suivi.

## Dépendances

Aucune.

## Estimation

1 jour. Backend uniquement.

## Risques

Lié au ticket-264 (la base locale à jour après un merge) : les deux touchent la
fin d'un run livré ; le tour de plan dit s'ils se font ensemble.
