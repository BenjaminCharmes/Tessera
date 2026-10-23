---
agent: codeur
created: 2026-10-23
depends_on:
- ticket-546
estimated_days: 1
id: ticket-548
plan: true
pr_number: 628
priority: medium
status: done
title: Trivial rebase conflicts are settled by rules before the conflict resolver
  is called
type: feat
---

# ticket-548 — Règles de conflit déterministes avant `resolveur-conflit`

## Objectif
Qu'un conflit de rebase trivial se règle sans appel LLM, et que seuls les
vrais conflits partent à `resolveur-conflit`.

## Contexte
Hors artefacts, journal et migrations Prisma (déjà résolus par règle dans
`git_workspace`), tout conflit part à `services/resolveur_conflit.py`
(ADR-033). KrumIA (revue du 23/10) applique d'abord quatre règles, dans cet
ordre : côtés identiques ; écart d'espacement seul ; un seul côté a changé
par rapport à la base ; union des lignes d'import ajoutées des deux côtés.

## Solution proposée
Une fonction pure prend les trois versions d'un bloc en conflit (base, nôtre,
leur) et rend soit une résolution, soit « pas de règle ». Un fichier dont
tous les blocs sont résolus par règle ne part pas au résolveur ; un seul bloc
sans règle envoie tout le fichier au résolveur, comme aujourd'hui. Les
résolutions par règle sont journalisées (fichier, règle appliquée). La règle
des imports ne vaut que pour des blocs faits uniquement de lignes
`import`/`from … import` (Python) ou `import … from` (TypeScript).

## Critères d'acceptation
- [ ] Un module de règles expose une fonction pure (base, nôtre, leur) → résolution ou `None`, avec un test par règle
- [ ] Un test montre qu'un bloc mêlant un import et une autre ligne n'est pas résolu par la règle des imports
- [ ] Un test montre qu'un bloc où les deux côtés changent la même ligne différemment rend `None`
- [ ] Un test, avec des doubles, montre qu'un fichier entièrement résolu par règle n'appelle pas `ResolveurConflitService`, et qu'un fichier avec un bloc sans règle l'appelle
- [ ] Chaque résolution par règle écrit une ligne dans `memory/pipeline-log.md` qui nomme le fichier et la règle

## Ce que ça ne fait pas
- Ne change pas l'ADR-033 : une résolution, par règle ou par le résolveur,
  ouvre sa PR et ne se merge jamais seule.