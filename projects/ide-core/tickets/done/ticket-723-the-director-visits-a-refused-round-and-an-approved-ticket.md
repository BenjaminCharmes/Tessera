---
id: ticket-723
title: "The director visits a refused round and an approved ticket"
type: feat
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-30
---

# ticket-723 — Le directeur passe voir un tour refusé et un ticket approuvé

## Objectif
Donner au directeur d'autres raisons de quitter son bureau que le seul run
devenu silencieux, chacune liée à un fait du pipeline (ADR-058).

## Contexte
Demande de Benjamin le 30/10. Depuis le ticket-661, la ronde ne part que pour un run
qui passe « silencieux » ou « figé ? », ou pour un agent qu'il choisit.

## Fait
- Un tour de plus sur un run vivant (`currentRound` qui augmente) : il va derrière
  le reviewer, qui vient de refuser.
- Un nouveau ticket approuvé (`lastResult.approved`) : il va féliciter le validateur.
- Même délai entre deux visites que pour le silence ; un geste de l'utilisateur
  passe toujours avant ; un projet découvert (retour sur la vue) ne fait partir
  personne, seul un changement observé compte.
- L'infobulle du directeur dit pourquoi il est venu (`MotifDeVisite`).
Fait à la main.

## Critères d'acceptation
- [x] `ronde.test.ts` : un tour refusé l'envoie au reviewer, une approbation au validateur, une première vue ne fait partir personne
- [x] `BureauRonde.test.tsx` : son libellé dit la raison de sa visite
