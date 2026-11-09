---
agent: codeur
created: 2026-11-06
depends_on:
- ticket-867
estimated_days: 1
id: ticket-868
pr_number: 994
priority: medium
status: done
title: The supervisor writes its a_toi cases to its journal
type: feat
---

# ticket-868 — Le superviseur journalise ses cas « À toi » dans `memory/supervision.md`

## Objectif

Un cas que la boucle range en « À toi » (`a_toi`) laisse une ligne dans
`memory/supervision.md`, pour qu'il se relise sans l'IDE ouvert.

## Contexte

Découvert au ticket-867, point (d) : « si ce n'est pas déjà le cas, vérifier ». Ce n'est pas le
cas. Aujourd'hui personne n'écrit de ligne `a_toi` : la boucle (`superviseur_boucle._echec`,
`_un`) ne fait que l'annoncer une fois sur le hub (`superviseur_action`). Les lignes du journal ne
sont écrites que par `intervention.intervenir`, et seulement pour une action qui a modifié des
fichiers, dans le même commit.

Le faire dans le ticket-867 aurait changé `intervention.py` : la ligne de journal d'une action y
suppose un commit préalable, et le journal lui-même est refusé comme fichier d'action
(`intervention_controle.py`, ADR-055). Une ligne sans autre changement est un cas à concevoir.

## Ce qu'il faut faire

- Une écriture d'intervention qui ne porte que la ligne de journal, pour un verdict `a_toi`.
- La boucle l'appelle une fois par clé marquée « À toi » (déjà fait, déjà annoncé : pas de doublon).
- Un test par verdict : `a_toi` écrit sa ligne, `agir` n'en ajoute pas une seconde, `rien` aucune.

## Ce que ça ne fait pas

- Ne change pas le registre d'actions ni la liste des fichiers que le superviseur peut écrire.
- Ne touche ni `agents.json` ni le détecteur d'anomalies.

## Critères d'acceptation

- [ ] Un cas `a_toi` laisse exactement une ligne dans `memory/supervision.md`.
- [ ] Un cas déjà journalisé n'en laisse pas de seconde au balayage suivant.
- [ ] Un diff de run qui touche ce journal met toujours le run en `blocked` (ADR-080).