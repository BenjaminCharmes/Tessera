---
id: ticket-074
title: "Enchaîner une sélection de tickets"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-073]
estimated_days: 1
created: 2026-09-17
---

# ticket-074 — File de tickets

## Pourquoi

Le backend savait enchaîner depuis longtemps (`run_autonomous`), mais rien ne
l'exposait : on lançait les tickets un par un, en surveillant l'écran pour
savoir quand relancer. Un lot produit par le planificateur en compte deux à
cinq.

## Décision

`run_queue` est distinct de `run_autonomous` : celui-ci choisit lui-même le
prochain ticket, celui-là exécute **une sélection, dans l'ordre demandé**.
L'ordre est celui des clics, pas celui de la liste — un lot du planificateur a
presque toujours des dépendances, et c'est à l'utilisateur de les ordonner.

**Un ticket non approuvé arrête la file.** Enchaîner sur une base que personne
n'a validée ferait travailler le suivant sur un état douteux.

L'arrêt et le budget sont vérifiés **entre** deux tickets, jamais au milieu de
l'un : s'arrêter en cours laisserait son travail non commité (ADR-018, ADR-020).
Le canal de dialogue est partagé par toute la file, pour qu'un seul arrêt la
vide entière.

## Livré

- `Orchestrator.run_queue`, événement `QUEUE_PROGRESS`
- Le WebSocket accepte `ticket_ids`
- `connectQueue` dans le hook, avancement `queue` dans l'état
- Sélection par ticket, `QueueBar` en tête de liste
