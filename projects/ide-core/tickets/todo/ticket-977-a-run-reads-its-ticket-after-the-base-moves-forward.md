---
agent: codeur
created: '2026-11-16'
depends_on: []
id: ticket-977
priority: high
status: todo
title: Un run relit son ticket une fois la base avancée
type: fix
---

## Signalement

- Projet source : curio (session Curio, 16/11 ; aussi déposé par
  `POST /signalements`, réponse 202 en attente : le ticket qu'il produira est
  un doublon de celui-ci, à passer en `cancelled`)
- Nature : bug, grave : une porte a approuvé un travail fait sur un texte
  périmé

## Contexte

Curio, run `c2c00c22`, 16/11 à 09:11 UTC, file 100 → 106. Le main local du
checkout était à `a214174`, **avant** la réécriture du ticket-100 (#146, le
14/11) : compter les échecs de connexion par couple pseudo + appareil. Le
reflog montre que Tessera a ensuite avancé main jusqu'à `d0348a8` (qui porte
le nouveau texte) au démarrage du run.

Le codeur a implémenté l'**ancien** texte (compteur par pseudo seul). Le
reviewer l'a relevé : « le ticket assigné et le fichier tickets/in-review/ ne
sont pas la même version ». Le validateur a **approuvé** sur l'ancien texte.
Sans l'arrêt demandé par la session Curio, le 100 partait en livraison.

Cause, dans `services/pipeline/orchestrator.py` :
`ticket_apres_avance.trouver_ticket` lit la fiche dans l'arbre local, puis
`PipelineRun(ticket=ticket)` la garde, puis `pipeline_branche.create_branch`
fait l'avance rapide de la base et crée la branche. Les agents reçoivent
`run.ticket`, lu avant l'avance. Le ticket-923 avait couvert le cas du ticket
**absent** de l'arbre, pas celui du ticket **présent mais périmé**.

## Ce qu'il faut faire

Après `create_branch` (base avancée, branche créée), relire la fiche depuis
l'arbre et remplacer `run.ticket` par cette lecture. Si le texte a changé,
émettre un événement (`ticket_relu_apres_avance`, avec l'ancien et le
nouveau SHA de base) et le noter dans `pipeline-log.md`. Le gel de
`preuve_reelle` (ticket-964) se refait sur la fiche relue.

Fiche introuvable après l'avance (renommée ou déplacée sur la base) : arrêt
`blocked` sans agent, motif explicite, comme `arret_ticket_absent`.

## Critères d'acceptation

- [ ] Test : un dépôt de test dont la base locale porte une version A du
      ticket et `origin/<base>` une version B ; après le démarrage du run,
      `run.ticket` porte B et le prompt du codeur contient le texte de B.
- [ ] Test : le texte inchangé ne produit ni événement ni ligne de journal.
- [ ] Test : `orch._preuves_reelles[ticket_id]` suit la fiche relue (A sans
      preuve réelle, B avec → `True`).
- [ ] Test : fiche absente de l'arbre après l'avance → résultat `blocked`,
      aucun agent appelé.
- [ ] Les projets à worktree (déjà partis d'`origin/<base>`) ne changent pas
      de comportement (test existant inchangé).

## Ce que ça ne fait pas

- Ne relit pas la fiche entre deux tours : le texte figé au départ du run
  reste celui de tout le run (ticket-964).
- Ne réaligne pas le checkout avant `services/start` (idée d'Affût du 16/11,
  à traiter après la stabilisation).
