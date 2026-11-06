---
agent: codeur
created: 2026-11-06
depends_on:
- ticket-859
estimated_days: 1
id: ticket-867
pr_number: null
priority: medium
status: done
title: The supervisor loop reads the inputs of the PR hand-back and the queue restart
type: feat
---

# ticket-867 — La boucle du superviseur lit les entrées de `reconfier_pr` et `relancer_file`

## Objectif

La tâche de fond (ticket-859) lance le tri et la décision, seules actions dont l'entrée se lit
dans le dossier du projet. Les deux autres actions, sans modèle, restent sans candidat : ce
ticket les branche.

## Contexte

ADR-080. `superviseur_collecte.collecter` ne produit aujourd'hui que des candidats `trier` et
`decider`. `superviseur_pr.py` (`reconfier_pr`) et `superviseur_file.py` (`relancer_file`)
existent et sont testés, mais rien ne leur fournit leurs entrées dans la boucle.

## Ce qu'il faut faire

- Un collecteur de runs livrés : pour un run approuvé, dont la PR est ouverte, la tête encore
  `pushed_sha` et hors `resolveur-conflit`, un candidat `reconfier_pr` (`sans_modele=True`,
  `sha = pushed_sha`).
- Un collecteur de files interrompues par une coupure d'infrastructure, quand
  `relance_file` est déclaré : un candidat `relancer_file`, une fois par cause (`sha` = la
  cause), jamais sur « non approuvé ».
- Les deux restent des actions sans modèle : le plafond du jour ne les retient pas.
- Faire écrire à la boucle les cas `a_toi` dans `memory/supervision.md` par `intervenir`, si
  ce n'est pas déjà le cas pour une action qui n'écrit rien (à vérifier d'abord).

## Critères d'acceptation

- [ ] `test_a_delivered_run_with_a_moved_head_offers_no_hand_back`
- [ ] `test_an_approved_run_with_its_pushed_head_offers_one_hand_back`
- [ ] `test_a_queue_cut_by_the_infrastructure_offers_one_restart_per_cause`
- [ ] `test_a_not_approved_queue_offers_no_restart`

## Ce que ça ne fait pas

- Ne merge jamais : `reconfier_pr` confie à `CIWatcher`.
- Ne modifie ni le détecteur ni `agents.json`.