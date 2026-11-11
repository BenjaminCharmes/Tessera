---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 1
id: ticket-923
plan: true
pr_number: null
priority: high
status: done
title: A run finds tickets merged on the remote base of a project without worktree
type: fix
---

# ticket-923 — Un run trouve les tickets mergés sur la base distante d'un projet sans worktree

## Objectif

Qu'un ticket mergé sur `origin/<base>` puisse être lancé sur un projet sans
`worktree`, sans que quelqu'un avance d'abord le checkout à la main.

## Contexte

La règle est d'écrire un ticket sur une branche, de le merger sur la base,
puis de lancer le run. Pour un projet à `worktree`, `refus_avant_ouverture`
(`services/pipeline/controle_base.py`) cherche le ticket sur `origin/<base>`
après un `fetch` : ça marche. Pour un projet **sans** worktree, il ne le
cherche que dans l'arbre du projet (`ticket_svc.get_ticket`). Or le run, lui,
réaligne la base locale sur le distant **avant** de bifurquer
(`_realigner_base_au_depart`, `services/pipeline/pipeline_branche.py`,
ticket-406). Le refus tombe donc avant l'avance rapide qui aurait amené le
ticket.

Le 11/11, une file Curio (tickets 088 à 091, mergés sur `main` par la PR
#125) a été refusée « Ticket(s) introuvable(s) dans le projet ». Tous les
projets sans `worktree` sont concernés, c'est-à-dire tous sauf Kadoomi. La
seule issue était un `git pull` dans le checkout, à la main.

## Solution proposée

- Pour un projet sans worktree, un ticket absent de l'arbre mais présent sur
  `origin/<base>` (même lecture que pour un projet à worktree :
  `_absents_sur_la_base`) est accepté à l'ouverture et à l'ajout en file
  (`refuser_absents_de_la_base`). Absent des deux : refusé comme aujourd'hui.
- Au départ du run, après `_realigner_base_au_depart`, le ticket est relu dans
  l'arbre. S'il manque encore (avance rapide refusée : arbre sale, branche
  divergente), le run s'arrête **sans rien créer**, avec une raison qui dit
  pourquoi l'avance a été refusée — pas une erreur serveur.
- Le titre lu avant la réservation (`_lire_titre`, `routers/orchestrator.py`)
  tolère un ticket encore absent de l'arbre.
- Au plan de dire comment le mode `single` suit la même règle.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_file_preflight.py` vérifie qu'un projet
      sans worktree dont le ticket n'existe que sur `origin/<base>` n'est pas
      refusé à l'ouverture d'une file.
- [ ] Un test vérifie qu'un ticket absent de l'arbre **et** de
      `origin/<base>` reste refusé avec « introuvable ».
- [ ] Un test vérifie qu'un ajout en file vivante (`append`) suit la même
      règle pour un projet sans worktree.
- [ ] Un test vérifie, avec des doubles, qu'un run dont l'avance rapide est
      refusée et dont le ticket reste absent s'arrête sans créer de branche,
      avec la raison du refus.
- [ ] Un test vérifie qu'un `fetch` impossible (pas de remote) laisse le
      comportement actuel : le ticket absent de l'arbre est refusé.

## Ce que ça ne fait pas

- N'avance pas le checkout en dehors d'un run, et ne force rien (ADR-022) :
  un arbre sale reste sale.
- Ne change rien aux projets à worktree.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Une file vivante réaligne la base entre deux tickets : un ticket ajouté en
cours de file n'est relu qu'au départ de son propre run, ce qui est déjà le
cas pour un projet à worktree.