---
id: ticket-786
title: "Journal lines written after a queue stops never leave the base dirty"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-786 — Les lignes de journal écrites après l'arrêt d'une file ne salissent jamais la base

## Objectif

Une file interrompue laisse l'arbre du checkout propre sur la branche de base (ADR-037).

## Contexte

04/11, file portfolio 159ff03b : ticket-021 approuvé, livraison arrêtée (GitHub 500 au push).
La file s'interrompt et laisse `memory/pipeline-log.md` **modifié et non commité sur `main`**
(« file interrompue : ticket-021 n'a pas été livré »).

`Orchestrator._interrompre` (`backend/src/tessera/services/orchestrator.py`) journalise après
que la livraison a ramené le checkout sur la base. Les lignes écrites après une livraison sont
d'ordinaire mises de côté et réécrites dans la branche du ticket suivant
(`backend/src/tessera/services/journal_en_attente.py`, ticket-331) ; quand la file s'arrête, il
n'y a pas de ticket suivant, et les lignes restent dans l'arbre de la base. Aucun commit ne se
fait sur la base (règle du dépôt).

## Solution proposée

- À la fermeture d'une file (interrompue ou finie), si le journal porte des lignes non
  commitées sur la base : les mettre de côté (`mettre_de_cote`) dans un fichier d'attente hors
  du suivi git (artefact Tessera, ADR-021), puis remettre le journal à `HEAD`.
- Au départ du run suivant sur ce projet, ce fichier d'attente est réécrit dans le journal de la
  nouvelle branche (`reecrire`), qui le commite avec sa tenue de livres, puis vidé.
- Un journal non suivi (artefacts locaux) n'est pas concerné.

## Critères d'acceptation

- [ ] Un test vérifie, sur un dépôt git temporaire, qu'après une file interrompue dont la
      dernière ligne est écrite sur la base, `git status --porcelain` est vide
- [ ] Un test vérifie que la ligne mise de côté figure dans le journal de la branche du run
      suivant, et que le fichier d'attente est vidé ensuite
- [ ] Un test vérifie qu'un journal non suivi par git n'est ni mis de côté ni remis à `HEAD`
