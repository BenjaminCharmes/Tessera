---
agent: codeur
created: 2026-11-13
depends_on: []
estimated_days: 1
id: ticket-970
pr_number: null
priority: high
status: todo
title: "A local base that only diverges in history after a squash merge does not stop the queue, and a run refused at start leaves the tree clean"
type: fix
---

# ticket-970 — Une base locale qui ne diverge que d'historique après un squash n'arrête pas la file, et un run refusé au départ laisse l'arbre propre

## Objectif

Qu'une file d'un projet sans `worktree` ne s'arrête plus sur une divergence
d'historique que Tessera a lui-même créée, et qu'un run bloqué à son départ
ne laisse jamais de changement non commité.

## Contexte

Devinoo, 13/11 (session relayée par l'orchestrateur). Après le run du
ticket-126, le `develop` local du checkout portait le commit du ticket
(06a407a) et trois commits « chore: tessera pipeline bookkeeping ». La PR #217
les a squashés en c9f8eb5 sur `origin/develop`. `git diff origin/develop
develop` est vide : seule l'histoire diffère. Le run du ticket-127 a été
refusé par `GitWorkspace` (`services/git_workspace/base.py`, contrôle
`merge-base --is-ancestor`) : « La branche locale develop (21a1aa7) a divergé
de la base distante (c9f8eb5) ». Il a de plus déplacé son ticket vers
`tickets/blocked/` **sans commit** : l'arbre est resté sale, contre ADR-018
et ADR-037. Les tickets 123 à 125 étaient passés normalement.

Deux questions ouvertes, à trancher dans le code avant d'écrire le
correctif : par quel chemin les commits d'un run atterrissent-ils sur le
`develop` local d'un projet sans worktree (rangement après livraison,
avance de la base, merge local) ? Et pourquoi seulement après le 126 ?

## Solution proposée

1. Trouver et corriger le chemin qui avance le `develop` local avec les
   commits du run au lieu de l'aligner sur `origin/develop` après le merge.
   Le ticket décrit ce chemin dans son rapport.
2. Quand la base locale n'est pas un ancêtre de la base distante **mais** que
   les deux arbres sont identiques (`git diff --quiet <locale> <distante>`),
   que le checkout est sur la base et que l'arbre est propre, la base locale
   s'aligne sur la distante (`git update-ref`, pas de `reset --hard`) et la
   ligne `base_realignee` (ancien SHA, nouveau SHA) est journalisée. Aucun
   contenu n'est perdu : il est déjà sur la base distante. Dans tout autre
   cas, le refus actuel reste.
3. Un run refusé avant le premier agent ne déplace pas son ticket sans le
   commiter : soit le déplacement est commité (`chore: … — blocked`), soit
   il est annulé ; l'arbre finit propre.

## Critères d'acceptation

- [ ] Un test sur de vrais dépôts (`tmp_path`, distant nu) : la base locale
      porte des commits dont le contenu est squashé sur la distante (arbres
      égaux) ; le run suivant part, la base locale vaut la distante, et
      `base_realignee` est journalisé.
- [ ] Un test : arbres différents (un commit local absent de la distante) :
      le run est refusé comme aujourd'hui, la base locale ne bouge pas.
- [ ] Un test : arbre sale, ou checkout hors de la base : refus, rien ne
      bouge.
- [ ] Un test : un run refusé au départ laisse `git status --porcelain` vide.
- [ ] Un test qui reproduit le chemin trouvé au point 1 et montre qu'après
      un run livré, le `develop` local ne porte plus les commits du run.

## Ce que ça ne fait pas

- Ne touche pas aux projets à `worktree` (le checkout n'y bouge jamais).
- Ne remet pas en ordre le checkout actuel de Devinoo : c'est une action de
  Benjamin.
