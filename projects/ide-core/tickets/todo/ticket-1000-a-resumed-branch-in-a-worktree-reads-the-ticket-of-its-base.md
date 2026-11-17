---
id: ticket-1000
title: "A resumed branch in a worktree reads the ticket file of its base"
type: fix
status: todo
priority: high
agent: codeur
depends_on: [ticket-987]
preuve_reelle: true
---

## Signalement

- Audit sans contexte du 17/11, constat M2 (MEDIUM, relevé en priorité haute :
  il laisse un agent retirer la preuve réelle de son propre ticket).

## Contexte

`services/pipeline/ticket_apres_avance.py`, `relire_apres_branche`, ne fait
rien quand `_worktree` est posé, avec le commentaire « il part déjà
d'`origin/<base>` » — faux pour une branche reprise (`run_worktree._ajouter`
extrait la branche existante). Le ticket-987 ne réaligne donc la fiche que
pour les projets sans worktree.

Conséquence : au run précédent, le codeur peut passer `preuve_reelle` de vrai
à faux ou réécrire les critères ; la valeur figée au départ du run vient de
sa copie, le validateur juge ses critères à lui, et la PR peut partir au
merge sans preuve réelle.

## Ce qu'il faut faire

- Dans un worktree aussi, sur une branche reprise, la fiche du ticket est
  réalignée sur `origin/<base>` (même règle que le 987 : la base gagne, le
  statut et le numéro de PR restent ceux du pipeline).
- Les champs qui gouvernent les portes (`preuve_reelle`, critères
  d'acceptation, `type`) se lisent toujours sur la base, jamais sur la copie
  de la branche.

## Critères d'acceptation

- [ ] Test sur dépôt réel avec worktree : branche reprise dont la fiche a
      `preuve_reelle: false` alors que la base a `true` → le run lit `true`.
- [ ] Test : critères réécrits sur la branche → le validateur reçoit ceux de
      la base.

## Ce que ça ne fait pas

- Ne revient pas sur le travail de code commité sur la branche.
