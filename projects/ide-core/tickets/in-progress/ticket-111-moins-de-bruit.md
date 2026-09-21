---
id: ticket-111
title: "La CI ne notifie que ce qui mérite d'être lu"
type: chore
status: in-progress
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-21
---

# ticket-111 — La CI ne notifie que ce qui mérite d'être lu

## Objectif

Réduire le nombre de runs déclenchés, donc le nombre de courriels envoyés par
GitHub.

## Contexte

Depuis le passage en public, chaque run notifie. Le décompte par branche
montre où ils partent :

| Source | Runs | Cause |
|---|---|---|
| `main` (`dynamic`) | 10 | mises à jour du graphe de dépendances |
| `main` (`push`) | 4 | **doublon** de la PR de release |
| Branches Dependabot | 7 | une PR par mise à jour |

Le doublon est une erreur de raisonnement du ticket-095. Son commentaire dit :

> `push` ne garde que `main`, qui ne reçoit pas de PR de sa propre branche

C'est faux. `main` reçoit les PR de release depuis `develop`. Chaque release
déclenche donc **deux** runs identiques : celui de la `pull_request`, puis
celui du `push` après le merge. Le second ne vérifie rien que le premier n'ait
déjà vérifié — sauf si `develop` a bougé entre les deux, ce qui déclencherait
de toute façon un nouveau run de la PR.

## Solution proposée

1. Retirer `push: [main]` du déclencheur. `pull_request: [main, develop]`
   couvre tout, puisque rien n'entre dans `main` autrement que par une PR —
   la règle interdit les commits directs.
2. Corriger le commentaire qui porte le raisonnement faux, plutôt que de le
   laisser justifier une règle qu'on vient de changer.
3. Limiter Dependabot à trois PR ouvertes par écosystème
   (`open-pull-requests-limit`). Sept PR simultanées produisent sept runs et
   sept fils de discussion ; trois suffisent à garder le rythme sans noyer.

Ce ticket **ne touche pas** à `CLAUDE.md`.

## Critères d'acceptation

- [ ] `.github/workflows/ci.yml` ne déclenche plus sur `push`
- [ ] Le commentaire du fichier ne prétend plus que `main` ne reçoit pas de PR
- [ ] `.github/dependabot.yml` limite les PR ouvertes pour les quatre
      écosystèmes
- [ ] Une PR ouverte après ce changement déclenche toujours ses cinq jobs
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

**Ne change pas les réglages de notification du compte.** Le levier le plus
efficace n'est pas dans ce dépôt : il est dans les préférences GitHub de
l'utilisateur, qui décident si un run terminé envoie un courriel. Ce ticket
réduit le nombre de runs, pas ce que GitHub en fait.

Ne supprime pas non plus les runs `dynamic` du graphe de dépendances : ils
viennent d'une fonctionnalité de la plateforme, activée d'office sur un dépôt
public, et non d'un workflow de ce dépôt.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Sans `push: [main]`, un commit qui arriverait sur `main` autrement que par une
PR ne serait pas vérifié. La règle l'interdit déjà, et une protection de
branche le garantirait — mais tant qu'elle n'est pas posée, c'est un trou
assumé, étroit et connu.
