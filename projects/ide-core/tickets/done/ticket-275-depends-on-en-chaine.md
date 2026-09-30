---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 0.5
id: ticket-275
pr_number: null
priority: high
status: done
title: A depends_on written as a string is read as ticket ids, not characters
type: fix
---

# ticket-275 — Un `depends_on` écrit en chaîne se lit comme des identifiants

## Objectif

Qu'un ticket dont le frontmatter porte `depends_on: ticket-001` ou
`depends_on: ticket-008, ticket-009` ait les bonnes dépendances.

## Contexte

Constaté le 2026-09-30 sur six tickets écrits par l'architecte dans
`freelance`. L'API les renvoyait avec
`depends_on: ['t', 'i', 'c', 'k', 'e', 't', '-', '0', '0', '1']` : la chaîne
YAML est passée telle quelle à un champ `list[str]`, qui l'a découpée
caractère par caractère. Aucune erreur, aucun ticket illisible signalé : les
dépendances étaient simplement fausses, et le choix du ticket suivant en mode
autonome s'appuie dessus.

Le skill `new-ticket` impose la forme liste, mais un agent peut l'oublier.

## Solution proposée

- Dans le parsing du frontmatter (modèle de ticket ou service de lecture), un
  `depends_on` de type chaîne est découpé sur les virgules, chaque morceau
  débarrassé de ses espaces ; une chaîne vide donne `[]`.
- Un identifiant qui ne ressemble pas à `ticket-NNN` après ce découpage est
  écarté et signalé dans le log, sans rendre le ticket illisible.

## Critères d'acceptation

- [ ] Un test montre que `depends_on: ticket-001` donne `["ticket-001"]`.
- [ ] Un test montre que `depends_on: ticket-008, ticket-009` donne
      `["ticket-008", "ticket-009"]`.
- [ ] Un test montre que `depends_on: ["ticket-001"]` est inchangé.
- [ ] Un test montre que `depends_on:` vide donne `[]`.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Backend uniquement.

## Risques

Aucun sur les tickets existants, tous écrits en liste.