---
agent: architect
created: 2026-10-28
depends_on: []
estimated_days: 1
id: ticket-650
plan: true
pr_number: null
priority: medium
status: done
title: 'Audit: give every ADR a status, and find the ones replaced, duplicated or
  contradicted'
type: design
---

# ticket-650 — Audit des ADR : statut, doublons, contradictions

## Objectif
Savoir, pour chaque ADR de `memory/decisions.md`, si elle est en vigueur,
remplacée ou historique, et repérer celles qui se doublonnent ou se contredisent.

## Contexte
`decisions.md` compte plus de soixante ADR. Il n'est plus injecté dans les
appels d'agents depuis le ticket-311 : c'est `contraintes.md` qui l'est, par rôle.
Le volume ne coûte donc pas de tokens. Les risques sont ailleurs :
- une douzaine d'ADR sont amendées ou remplacées par une autre (ADR-009 par
  ADR-061, par exemple), sans que le journal dise laquelle compte ;
- le 28/10, deux tickets de conception ont pris le même numéro d'ADR, et la
  résolution de conflit a écrasé l'une ;
- le skill `write-adr` dit encore que `decisions.md` est « injecté en entier
  dans chaque appel d'agent », ce qui est faux depuis le ticket-311.

## Solution proposée
- Lire chaque ADR et lui donner un statut : en vigueur, remplacée (par laquelle),
  historique (le fait reste vrai mais ne guide plus de décision).
- Relever les paires qui se doublonnent ou se contredisent.
- Pour chaque règle de `memory/contraintes.md`, vérifier qu'elle renvoie à une
  ADR en vigueur.
- Proposer une forme : une ligne `**Statut**` par ADR, et une archive pour les
  ADR historiques.

## Critères d'acceptation
- [ ] `docs/audit/adr.md` liste chaque ADR avec son statut et, pour une ADR remplacée, l'ADR qui la remplace
- [ ] `docs/audit/adr.md` liste les paires d'ADR qui se doublonnent ou se contredisent, avec la phrase de chacune qui le montre
- [ ] `docs/audit/adr.md` liste les règles de `memory/contraintes.md` qui renvoient à une ADR remplacée ou historique
- [ ] Le livrable liste les tickets de correction qui en découlent, chacun avec ses critères vérifiables ; l'attribution des numéros par le code est déjà le ticket-659

## Ce que ça ne fait pas
- Ne modifie ni `decisions.md` ni `contraintes.md` : les tickets de correction le feront.
- Le skill `write-adr` vit sous `.claude/` : sa correction se fait à la main.