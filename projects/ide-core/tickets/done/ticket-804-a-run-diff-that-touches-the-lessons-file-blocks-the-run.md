---
agent: codeur
created: 2026-11-05
depends_on: [ticket-801]
estimated_days: 1
id: ticket-804
pr_number: null
priority: medium
status: done
title: A run diff that touches the lessons file blocks the run
type: feat
---

# ticket-804 — Un diff de run qui touche le fichier de leçons met le run en `blocked`

## Objectif

Seul le service écrit `memory/lecons.md`. Un codeur qui y ajoute une ligne — ou en déplace
une sous `## En vigueur` — change la consigne de tous les agents suivants sans relecture :
c'est le cas d'ADR-055, étendu à ce fichier (ADR-074).

## Contexte

`contraintes_touchees.lignes_hors_proposees` lit le diff du run et rend les lignes de
`contraintes.md` écrites hors `## Proposées` ; `pipeline_contraintes.arret_contraintes_hors_proposees`
arrête le run à la fin du tour du codeur (`blocked`, commit « unapproved », événement
`ERROR`). Le même mécanisme sert ici, en plus strict : pour `lecons.md`, **aucune** ligne
n'est admise au tour du codeur, pas même sous `## Proposées` — la production d'une
proposition appartient au service (ticket-803), qui écrit après ce contrôle.

## Ce qu'il faut faire

- Un module voisin de `contraintes_touchees.py` rend les lignes du diff qui touchent
  `memory/lecons.md` (le fichier lui-même, résolu comme `contraintes.md` : racines du
  projet et dépôt ancêtre), sans dupliquer l'analyse du diff : la partager.
- `arret_lecons_modifiees(orch, run)` sur le modèle de `arret_contraintes_hors_proposees` :
  raison `lessons_file_modified`, message « lecons.md modifié par un agent — seul le service
  écrit ce fichier ; un humain déplace une leçon sous `## En vigueur` ».
- Appelé à la fin du tour du codeur, au même endroit que le contrôle de `contraintes.md`.
- Un humain qui déplace une leçon le fait hors run (checkout ou éditeur) : aucun run n'est
  concerné.

## Critères d'acceptation

- [x] `backend/tests/test_lecons_gardees.py` : un diff qui ajoute une ligne sous
      `## En vigueur` → `blocked`, raison `lessons_file_modified`, commit « unapproved »
- [x] Même test pour une ligne ajoutée sous `## Proposées` au tour du codeur, et pour une
      suppression de ligne
- [x] Un diff qui ne touche pas `lecons.md` → `None`, le run continue
- [x] Une leçon ajoutée par le service après la fin du tour du codeur (ticket-803) ne
      déclenche pas l'arrêt : un test fixe l'ordre des deux étapes
- [x] Le contrôle de `contraintes.md` garde ses tests inchangés

## Ce que ça ne fait pas

Ne refuse pas l'écriture elle-même (le hook d'ADR-031 ne la bloque pas) : l'arrêt se joue au
diff, comme pour `contraintes.md`.

## Dépendances

ticket-801.
