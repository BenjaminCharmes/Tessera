---
id: ticket-210
title: "Un fichier de ticket illisible se signale au lieu de disparaître"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-210 — Un ticket illisible se signale

## Objectif

Un fichier `ticket-*.md` que le modèle `Ticket` refuse apparaît dans l'IDE
comme illisible, avec la raison, au lieu d'être écarté sans trace.

## Contexte

`TicketService.list_tickets` fait `except Exception: continue`. Un ticket
sans `type` ni `agent`, deux champs obligatoires, est donc invisible. Rien
dans l'UI ni dans les logs ne le signale.

Cas observé : un architect a créé quatre tickets de suite avec un
frontmatter limité à `id`, `title`, `status`, `priority` et `depends_on`. Le
run a réussi, les fichiers étaient sur le disque, et l'IDE montrait un projet
sans aucun nouveau ticket. L'utilisateur en a conclu que le run n'avait rien
produit.

Les agents écrivent leurs tickets avec `Write`. Rien ne leur dit quel
frontmatter est exigé, et rien ne vérifie ce qu'ils écrivent.

## Solution proposée

1. `list_tickets` journalise chaque fichier rejeté (`ticket_unreadable`, avec
   le chemin et l'erreur de validation), puis le remonte dans la réponse de
   l'API. L'UI l'affiche dans la liste comme une entrée « illisible », avec
   la raison.
2. `agents/prompts/architect.md` (et tout prompt d'un rôle qui crée des
   tickets) donne le frontmatter obligatoire et les valeurs autorisées de
   `type`, `status` et `priority`.

## Critères d'acceptation

- [ ] Un test : un fichier `ticket-099-x.md` sans `type` dans `todo/` →
      `list_tickets` ne lève pas, et le fichier figure parmi les rejets avec
      le chemin et un message qui nomme `type`
- [ ] Un log `ticket_unreadable` est émis pour ce fichier
- [ ] La réponse de `GET /api/v1/projects/{id}/tickets` expose les rejets
      sans casser le format lu par le frontend actuel
- [ ] L'UI affiche un ticket rejeté avec sa raison (test Vitest)
- [ ] `agents/prompts/architect.md` liste `id`, `title`, `type`, `status`,
      `priority` et `agent` comme obligatoires, avec les valeurs de `type`
- [ ] `uv run pytest` et `npm run test` passent

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Changer la forme de la réponse de l'API peut casser les autres consommateurs
de cette route. Un champ ajouté vaut mieux qu'une liste qui change de type.
