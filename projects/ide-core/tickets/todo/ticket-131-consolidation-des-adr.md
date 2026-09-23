---
id: ticket-131
title: "Consolider les ADR : archiver les choix éteints, fusionner les amendements"
type: docs
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-09-23
---

# ticket-131 — Consolider les ADR

## Objectif

Réduire ce que `decisions.md` coûte à chaque appel d'agent, sans perdre une
seule contrainte en vigueur.

## Contexte

Quarante ADR, dont quatre portent un amendement inséré après coup. Le fichier
est injecté **dans chaque appel d'agent**, jusqu'à dix-huit par ticket
(ADR-032) : sa longueur est un coût produit, pas un coût de session.

Trois symptômes visibles :

- des ADR décrivent un mécanisme que le code a remplacé depuis. ADR-016
  (scope filesystem Tauri) est explicitement déclaré sans objet par ADR-040 et
  reste pourtant dans le fichier ;
- des ADR amendés se lisent en deux temps — la décision, puis ce qui l'a
  corrigée — alors qu'un agent n'a besoin que de l'état en vigueur ;
- ADR-032 réduit déjà le prompt par `Portée`, mais un ADR éteint sans portée
  part à tout le monde.

## Solution proposée

Trois gestes, dans cet ordre :

1. **Fusionner** chaque amendement dans le corps de son ADR. L'historique reste
   dans git ; le fichier dit ce qui s'applique aujourd'hui.
2. **Archiver** les ADR éteints vers `memory/decisions-archive.md`, qui n'est
   ni importé ni injecté. Un ADR est éteint quand un ADR postérieur le déclare
   sans objet, ou quand le code qu'il contraint n'existe plus.
3. **Vérifier** qu'aucune contrainte n'est perdue : tout ADR archivé est soit
   remplacé nommément par un autre, soit sans code correspondant.

Ce n'est **pas** une réécriture. Une décision conservée garde son texte et son
numéro : les numéros sont cités dans le code, les tickets et les prompts.

## Critères d'acceptation

- [ ] Aucun ADR de `decisions.md` ne contient de ligne « Amendée » — les
      amendements sont fusionnés dans le corps
- [ ] `memory/decisions-archive.md` existe et n'est importé par aucun
      `CLAUDE.md`
- [ ] Chaque ADR archivé nomme l'ADR qui le remplace, ou justifie son
      extinction en une phrase
- [ ] Aucun numéro d'ADR n'est réattribué ni renuméroté
- [ ] Un test vérifie que tout numéro d'ADR cité dans `backend/src/`,
      `agents/prompts/` ou `.claude/skills/` existe encore dans l'un des deux
      fichiers
- [ ] `test_consignes_coherentes.py` passe, budget par ADR compris
- [ ] `decisions.md` est plus court qu'avant le ticket

## Dépendances

Aucune. À faire de préférence après ticket-129, pour que l'ADR de la
supervision soit consolidé avec les autres.

## Estimation

1 jour.

## Risques

Le vrai risque est d'archiver une contrainte encore appliquée : elle
disparaîtrait du prompt sans que rien n'échoue, et un agent la violerait des
semaines plus tard sans qu'on sache pourquoi. D'où le test qui relie les
numéros cités au fichier qui les porte.
