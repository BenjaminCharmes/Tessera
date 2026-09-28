---
id: ticket-208
title: "Relancer un ticket fait relire tout le travail de sa branche, pas seulement le dernier tour"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-208 — Relancer un ticket fait relire toute sa branche

## Objectif

Un run qui reprend une branche de ticket existante soumet à la sécurité, au
reviewer et au validateur tout ce que la branche ajoute à sa base, et pas
seulement ce que le dernier tour a écrit.

## Contexte

`GitWorkspaceService.create_branch` est idempotent : si
`ticket-<id>-<slug>` existe, il fait un `checkout` de la branche au lieu de
la recréer depuis la base. Les étapes de relecture reçoivent ensuite
`git diff HEAD`, c'est-à-dire le seul travail non commité du tour en cours.

Conséquence observée sur un projet personnel : un premier run finit en
`blocked` sur une faille HIGH (traversée de chemin) et commite son travail en
`chore: … — unapproved work`, comme ADR-018 le prévoit. Au second run du même
ticket, l'architect n'écrit que des tickets et un ADR. L'audit voit donc un
diff sans code, rend `PASS`, et le ticket passe en `done`. Pourtant sa branche
contient encore le code bloqué, qui n'a jamais été relu. À `autonomy: pr` ou
`merge`, la livraison l'aurait poussé.

ADR-018 dit que seul un run approuvé avance la base. Ici, l'approbation du
second run couvre sans le dire le commit refusé du premier.

## Solution proposée

Le diff soumis aux portes (sécurité, reviewer, validateur) est calculé
**depuis la base du run** (`_base_ref`, ou le merge-base avec elle) jusqu'à
l'arbre de travail. Il n'est plus calculé depuis `HEAD`. Sur une branche
neuve, rien ne change. Sur une branche reprise, les commits antérieurs entrent
dans la relecture.

La troncature à 8 000 caractères du validateur s'applique toujours. Le
prompt dit déjà quoi faire d'un critère invisible.

## Critères d'acceptation

- [ ] Un test : branche existante portant un commit non approuvé qui ajoute
      `a.py`, nouveau tour qui n'écrit que `b.md` → le diff remis à l'audit
      sécurité contient `a.py`
- [ ] Un test : sur une branche neuve, le diff remis aux portes est identique
      à celui d'avant le changement
- [ ] Le diff utilisé par le reviewer et le validateur est le même que celui
      de l'audit sécurité (une seule fonction le calcule)
- [ ] `uv run pytest` passe

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Un diff plus long peut dépasser la troncature et rendre la validation moins
précise sur les branches reprises. C'est moins grave que de ne rien relire.
