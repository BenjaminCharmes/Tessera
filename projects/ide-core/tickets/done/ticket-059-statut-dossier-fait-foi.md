---
id: ticket-059
title: "Le dossier fait foi pour le statut d'un ticket, pas le frontmatter"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-15
---

# ticket-059 — Le dossier fait foi

## Objectif

Supprimer une source de divergence entre ce que l'UI affiche et ce que contient
le dépôt.

## Contexte

Signalé à l'usage : le projet `ide-core` affiche **12 tickets en `todo`** alors
que `tickets/todo/` est **vide** sur le disque.

Les douze fichiers sont dans `tickets/done/`, mais leur frontmatter porte
encore `status: todo`. `TicketService._parse` lit le statut depuis le
frontmatter et ignore le dossier : l'UI affiche donc des tickets terminés
depuis des mois comme étant à faire.

```
ticket-017-live-ticket-board.md    dossier=done   champ=todo
ticket-025-import-filesystem.md    dossier=done   champ=todo
ticket-043-docker-deploy.md        dossier=done   champ=todo
… 12 au total
```

## La question de fond

Deux sources de vérité coexistent pour un même fait. Laquelle doit gagner ?

**Le dossier.** C'est le service lui-même qui y place les fichiers
(`_STATUS_DIRS`, `update_status`) : le dossier ne peut pas mentir sur ce que le
service a fait. Le champ frontmatter, lui, dérive dès qu'un fichier est écrit
sans qu'on pense à le mettre à jour — ce qui est arrivé douze fois.

Le champ reste utile : il rend le fichier lisible seul, hors de l'IDE. Mais il
doit être **dérivé**, pas faire autorité.

## Solution proposée

1. `_parse` prend le statut du **dossier parent**, et retombe sur le
   frontmatter uniquement si le dossier n'est pas reconnu.
2. Un test verrouille le cas exact : fichier dans `done/`, champ `todo`.
3. Les douze fichiers existants sont réparés, pour que le dépôt ne porte plus
   la contradiction.

## Critères d'acceptation

- [x] Un ticket dans `done/` avec `status: todo` est lu comme `done`
- [x] Un dossier non reconnu retombe proprement sur le frontmatter
- [x] `GET /projects/ide-core/tickets?status=todo` ne renvoie plus les tickets
      terminés
- [x] Les douze fichiers du dépôt sont réparés
- [x] Aucun ticket du dépôt ne présente plus de contradiction dossier/champ
- [x] `uv run pytest -q` et `uv run mypy src/` verts

## Dépendances

Aucune.

## Estimation

**1j**.

## Risques

- **Faible** — le changement rend le comportement *plus* proche de ce que
  l'utilisateur voit dans son arborescence.

## Vérifié en réel

| | API | Disque |
|---|---|---|
| `todo` | 0 | 0 |
| `in-progress` | 1 | 1 |
| `done` | 59 | 59 |

Avant : l'API annonçait 12 `todo` pour un dossier vide.
