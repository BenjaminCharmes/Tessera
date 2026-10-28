---
id: ticket-628
title: "Each Bureau agent has a stable name, shown on hover and in the chosen-agent panel"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-624]
estimated_days: 1
created: 2026-10-28
---

# ticket-628 — Un nom pour chaque agent du Bureau

## Objectif
Qu'on reconnaisse un agent d'un run à l'autre, et qu'on en parle par son nom.

## Contexte
Idée de Benjamin du 28/10, validée telle quelle. Un agent a déjà une tenue et un
physique stables par projet et par rôle (`physique(projet, role)` dans
`lib/bureau/physique.ts`), mais aucun nom. Un nom est une identité, comme la
tenue, et non un état : il ne contredit pas ADR-058.

Le nom ne s'affiche pas en permanence au-dessus des têtes : avec deux ou trois
pièces de cinq agents, en plus des bulles d'outil, la vue deviendrait illisible.

## Solution proposée
- `lib/bureau/noms.ts` exporte `nomDeLAgent(projet, role)`. Il tire, de façon
  déterministe, un prénom dans une liste fixe, avec la même graine que `physique`.
  Deux rôles d'un même projet n'ont jamais le même prénom.
- Le nom ouvre l'`aria-label` et l'infobulle de l'agent : « Camille, codeur, travaille ».
- Le panneau « Agent choisi » (`PanneauAgentChoisi.tsx`) prend le nom pour titre.

## Critères d'acceptation
- [ ] Un test de `lib/bureau/noms.ts` vérifie que `nomDeLAgent` rend le même nom pour le même projet et le même rôle, et des noms différents pour les rôles d'un même projet
- [ ] Un test vérifie que l'`aria-label` d'un poste de `PosteDeTravail.tsx` commence par le nom de son agent
- [ ] Un test vérifie que l'`aria-label` d'un agent debout dans `AgentsDeLaPiece.tsx` commence par son nom
- [ ] Un test vérifie que `PanneauAgentChoisi.tsx` affiche le nom de l'agent choisi en titre

## Ce que ça ne fait pas
- N'affiche pas les noms en permanence au-dessus des têtes.
- Ne nomme ni le directeur ni les RH : ce sont des figures de salle, pas des rôles.
