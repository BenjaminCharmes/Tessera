---
agent: codeur
created: 2026-10-29
depends_on: []
id: ticket-681
pr_number: 803
priority: low
status: done
title: Shared duration, date and cost formatters
type: refactor
---

# ticket-681 — Formateurs de durée, de date et de coût partagés

## Objectif
Un module de formatage, au lieu de quatre durées, trois dates et deux coûts.

## Contexte
`docs/audit/doublons.md` §2.4. Durée : `design/charts/palette.ts:54`,
`EnCoursView/format.ts:9`, `FilDuRun/index.tsx:24`, `HistoriqueView/runs.ts:130`,
`Sidebar/RunHistory.tsx:19` (copie conforme de la précédente). Date :
`runs.ts:141`, `RunHistory.tsx:29`, `palette.ts:64`. Coût : `palette.ts:43`
(`0,42 $`) et `runs.ts:150` (`$0.42`) : deux notations pour la même grandeur.

## Critères d'acceptation
- [ ] `RunHistory.tsx` n'a plus de formateur local de durée ni de date : il appelle celui de `HistoriqueView/runs.ts` ou du module commun
- [ ] Chaque famille (durée de run, durée écoulée, date, coût) a une seule implémentation exportée, et chaque ancien appelant l'importe
- [ ] La notation du coût est fixée **avant** de coder, par l'utilisateur : la PR cite sa réponse ; sans réponse, elle ne change aucune des deux notations et les range dans le module commun sous deux noms
- [ ] Un test par fonction exportée couvre : valeur nulle, négative, < 1 min, ≥ 1 h
- [ ] `design/charts/` ne dépend d'aucun composant (la palette ADR-047 reste isolée)
- [ ] `npm run test`, `npx tsc --noEmit` et `npm run lint` passent ; les attendus des tests existants ne changent pas

## Ce que ça ne fait pas
- Ne tranche pas la notation du coût : c'est un choix d'affichage de l'utilisateur
- Ne touche pas `components/BureauView/`, `lib/bureau/`, `design/bureau/` (ticket-631)