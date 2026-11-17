---
id: ticket-987
title: "A resumed ticket reads the file of its base"
type: fix
status: todo
priority: medium
agent: codeur
depends_on: [ticket-977]
---

## Signalement

- Projet source : finances (session Finances, 16/11 à 16:35 UTC, par la boîte)
- Nature : bug : un run travaille sur un texte de ticket périmé

## Contexte

Finances, ticket-003 : bloqué, sa fiche a été corrigée sur la base (critères
réécrits), puis le ticket a été relancé. Le run a repris la branche du ticket
et les agents ont reçu la fiche **portée par la branche**, pas la correction
de la base. Il s'est débloqué quand même au tour 2, par chance.

Le ticket-977 relit la fiche après `create_branch`, mais sur une branche
reprise cette relecture lit l'arbre de la branche. Or la branche a déplacé la
fiche (`todo/` → `in-progress/` → `blocked/`, ou retour en `todo/` par le
commit de travail non approuvé) et en a modifié le frontmatter, pendant que la
base modifiait le texte sous `todo/`. `_rejouer_branche_en_retard`
(`services/git_workspace/branche.py`) rejoue la branche sur la base ; ce
qu'il advient alors de la correction — portée sur la copie déplacée, perdue,
ou laissée dans un second fichier — n'est couvert par aucun test.

Déjà vu le 23/10 sur ide-core (tickets 571 et 552 : « un ticket repris garde
sa copie »).

## Ce qu'il faut faire

- D'abord un test qui reproduit, sur un vrai dépôt git temporaire : la branche
  d'un ticket a déplacé sa fiche hors de `todo/` et changé son statut ; la base
  a ensuite réécrit le corps de la fiche sous `todo/` ; le ticket est relancé.
  Constater ce que le run lit.
- Faire que le texte lu par le run soit celui de la base : après la reprise
  de la branche (rejeu réussi comme branche neuve après `stale/`), le corps de
  la fiche du ticket est celui de `_base_ref`. Le frontmatter de statut reste
  celui que le pipeline tient.
- La fiche n'existe qu'à un endroit après la reprise : pas de copie périmée
  dans un second dossier de statut.
- Quand le corps a changé, émettre l'événement que le ticket-977 a introduit
  (`ticket_relu_apres_avance`) et une ligne au journal du pipeline.

## Critères d'acceptation

- [ ] Test sur dépôt réel : branche reprise dont la base a réécrit la fiche —
      `run.ticket` porte le corps de la base.
- [ ] Test : même cas quand le rejeu échoue en conflit (branche renommée
      `stale/`, branche neuve) — corps de la base.
- [ ] Test : après la reprise, un seul fichier porte l'identifiant du ticket
      dans `tickets/`.
- [ ] Test : fiche inchangée sur la base — aucun événement, aucun commit de
      plus.

## Ce que ça ne fait pas

- Ne fusionne pas deux rédactions concurrentes d'un même critère : la base
  gagne, le travail déjà commité sur la branche reste et sera relu.
- Ne touche pas aux cases cochées par le validateur d'un tour précédent : un
  critère réécrit est rejugé.
