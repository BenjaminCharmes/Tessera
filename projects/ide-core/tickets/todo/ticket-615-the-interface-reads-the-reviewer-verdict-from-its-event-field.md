---
id: ticket-615
title: "The interface reads the reviewer verdict from the event field, not from its text"
type: refactor
status: todo
priority: low
agent: codeur
created: 2026-10-27
depends_on: [ticket-614]
estimated_days: 0.5
---

# ticket-615 — Le frontend lit `verdict`, plus le mot-clé

## Objectif
Une seule source du verdict du reviewer : le champ `verdict` de `AGENT_DONE`
(ticket-614). Le frontend cesse de le deviner dans le texte.

## Contexte
Quatre endroits relisent le mot-clé dans `content` :
`components/FilDuRun/verdict.ts` (`verdictDuReviewer`) et son appel dans
`FilDuRun/index.tsx`, `components/AgentPanel/VerdictBanner.tsx` et
`lib/bureau/copie.ts`. `BottomPanel` lit déjà un champ. Deux
descriptions d'une même règle finissent par diverger (ADR-034) ; le seuil de
confiance rend d'ailleurs le texte seul faux : un `CHANGES_REQUESTED` sous le
seuil est un `APPROVED` pour le pipeline.

## À faire
- Typer `verdict` dans `types/api.ts` pour `agent_done` du reviewer.
- `verdictDuReviewer(entry)` lit `data.verdict` quand il est présent.
- Un événement **sans** `verdict` — un run enregistré avant le ticket-614, relu
  dans l'historique — garde la lecture par mot-clé, dans une seule fonction,
  nommée comme telle. C'est la seule trace du parseur côté interface.
- `VerdictBanner` et `lib/bureau/copie.ts` passent par cette fonction.

## Critères d'acceptation
- [ ] `verdictDuReviewer` renvoie `data.verdict` quand il est présent, même si `content` dit l'inverse, testé
- [ ] Un événement sans `verdict` est lu comme avant : les tests de `verdict.test.ts` existants passent
- [ ] `VerdictBanner`, `FilDuRun` et `lib/bureau/copie.ts` n'ont plus de comparaison de chaîne sur `APPROVED` / `CHANGES_REQUESTED` dans `content` : un `grep` sur ces fichiers ne montre que la fonction commune
- [ ] `npm run test`, `tsc` et `eslint` passent

## Ce que ça ne fait pas
- Ne change aucun écran ni aucune couleur (ADR-026).
- N'ajoute pas de champ aux événements de la sécurité ni du validateur : leurs événements ne passent pas par le mot-clé.
