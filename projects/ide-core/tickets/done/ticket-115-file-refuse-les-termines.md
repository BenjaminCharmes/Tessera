---
id: ticket-115
title: "La file refuse un ticket déjà terminé"
type: fix
status: done
pr_number: 132
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-21
---

# ticket-115 — La file refuse un ticket déjà terminé

## Objectif

Qu'un ticket `done` ou `cancelled` ne puisse pas être relancé par la file.

## Contexte

Le bouton **Lancer** est correctement caché sur un ticket terminé :

```ts
const canRun = ticket.status !== "done" && ticket.status !== "cancelled";
```

Le bouton **Ajouter à la file**, dans le même composant, n'a aucune condition
de statut. On ne peut donc pas lancer un ticket terminé directement, mais on
peut l'ajouter à la file — qui le lancera.

Et le backend ne rattrape pas : `run_queue` enchaîne les tickets « dans
l'ordre demandé » sans regarder leur statut. Un ticket `done` mis en file est
donc **réellement repris** : nouvelle branche, nouveaux appels d'agents,
quota d'abonnement dépensé, pour refaire un travail déjà livré.

Le risque n'est pas seulement le gaspillage. Le pipeline repart du ticket tel
qu'il est écrit, donc d'une description dont le travail est déjà fait : le
codeur peut réécrire ce qui existe, et le run finira par un commit sur une
branche neuve.

## Solution proposée

1. Côté UI, soumettre le bouton de file à la même condition que le bouton
   Lancer. Les deux mènent au même endroit, ils doivent obéir à la même règle.
2. Côté backend, `run_queue` **saute** les tickets terminés et le journalise,
   au lieu de les exécuter.

Le garde doit être aux deux endroits. Un garde uniquement dans l'UI n'en est
pas un : `POST /api/v1/orchestrator/run-queue` est appelable directement, et
c'est ce que fait déjà le chat.

**Sauter plutôt qu'arrêter** : une file où un ticket terminé s'est glissé doit
traiter les autres. S'arrêter net ferait payer aux suivants une erreur de
sélection.

## Critères d'acceptation

- [ ] Le bouton « Ajouter à la file » n'apparaît pas sur un ticket `done` ni
      `cancelled`, vérifié par un test
- [ ] `run_queue` sur une liste contenant un ticket `done` ne l'exécute pas
- [ ] Les autres tickets de la même file sont bien exécutés
- [ ] Le saut est journalisé, pour qu'il ne soit pas silencieux
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

Ne touche pas au mode autonome : `pick_next_ticket` ne choisit que parmi les
tickets `todo`, il n'a jamais eu ce défaut.

Ne bloque pas non plus le relancement volontaire d'un ticket terminé : il
suffit de le repasser en `todo`, ce qui est un geste explicite.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Sauter en silence serait pire que le défaut actuel : l'utilisateur croirait sa
file complète. D'où la trace dans le journal.
