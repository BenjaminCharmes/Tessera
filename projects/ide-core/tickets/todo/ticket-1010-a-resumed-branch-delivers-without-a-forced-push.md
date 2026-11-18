---
agent: codeur
depends_on: []
id: ticket-1010
preuve_reelle: false
priority: high
status: todo
title: A resumed branch already on the remote is delivered without a forced push
type: fix
---

## Signalement

18/11, ticket-997, second passage (file `99a53d32`) : approuvé, puis
`livraison: arrêt — Livraison interrompue : GitCommandError … push
--set-upstream origin ticket-997-… ! [rejected] (non-fast-forward)`.

## Contexte

La branche `ticket-997-…` existait sur le remote (premier passage, PR #1157
fermée sans merge). Le second run a repris la branche locale, puis l'a
rejouée sur une base avancée. Ses commits ont changé de SHA, et le push
ordinaire est refusé. Ne jamais forcer un push est la bonne règle (ADR-022) :
le run approuvé reste pourtant sans PR, et il a fallu le pousser à la main
sous un autre nom (#1170).

## Ce qu'il faut faire

- À la livraison, quand la branche existe sur le remote et que la tête
  locale n'en descend pas : pousser sous un nom neuf et dérivé
  (`<branche>-2`, puis `-3`…), ouvrir la PR depuis ce nom, et l'écrire dans
  le journal. Jamais `--force`, jamais de suppression de la branche distante.
- L'arrêt actuel (« Livraison interrompue : GitCommandError ») ne doit plus
  être la seule issue de ce cas.

## Critères d'acceptation

- [ ] Test (dépôt réel et remote nu) : branche distante divergente → la
  livraison pousse `<branche>-2`, ouvre la PR depuis ce nom, et la branche
  distante d'origine est intacte.
- [ ] Test : une branche distante dont la tête locale descend se pousse
  normalement, sous son nom, comme aujourd'hui.
- [ ] Test : aucun appel git ne porte `--force` ni `--force-with-lease`.

## Ce que ça ne fait pas

- Ne ferme ni ne supprime l'ancienne PR ou l'ancienne branche.
- Ne change pas le rejeu sur la base avancée.
