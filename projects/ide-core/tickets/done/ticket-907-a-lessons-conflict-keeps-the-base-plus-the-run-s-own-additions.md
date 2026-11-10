---
agent: codeur
created: 2026-11-10
depends_on: []
estimated_days: 1
id: ticket-907
plan: true
pr_number: null
priority: medium
status: done
title: A lessons conflict keeps the base plus the run's own additions
type: fix
---

# ticket-907 — Un conflit sur les leçons garde la base et les seuls ajouts du run

## Objectif

Quand `memory/lecons.md` entre en conflit à la livraison, la résolution
garde le fichier de la base et y ajoute, sous `## Proposées`, les seules
lignes que le run a écrites. Une leçon triée par un humain ne revient
jamais.

## Contexte

Le service des leçons ajoute une ligne sous `## Proposées` après chaque run
approuvé (ADR-074). Un humain trie ensuite ces lignes : il en déplace sous
`## En vigueur`, en fusionne, en retire. Les deux côtés touchent donc la même
zone, et chaque livraison dont la branche précède un tri entre en conflit sur
ce fichier.

`lecons.md` n'est pas dans `_JOURNAL_UNION_SUFFIXES` (`chemins.py`) :
`mise_a_jour_branche.py` refuse ce conflit, la PR reste ouverte et une session
le résout à la main. Le 2026-11-10, la résolution à la main a été une union.
Les 11 leçons que #1010 venait de trier sont revenues sous `## Proposées`
avec le merge de #1011, et il a fallu les retirer à la main dans #1012.

Une union est juste pour `pipeline-log.md`, où l'on ne fait qu'ajouter.
Elle est fausse pour un fichier qu'un humain trie.

## Solution proposée

- Une résolution propre à `memory/lecons.md`, dans `mise_a_jour_branche.py`
  et dans le rebase de livraison (`rebase.py`, `chemins.py`). Les lignes
  ajoutées par le run sont celles du côté branche qui n'existent ni dans
  l'ancêtre commun (stage 1) ni dans la base. Le résultat est le fichier de la
  base, avec ces lignes ajoutées à la fin de `## Proposées`.
- Si le côté branche a retiré ou modifié une ligne de l'ancêtre, la résolution
  refuse : un run n'a pas à trier les leçons (ADR-074).
- Une fonction pure dans `textes.py`, testée seule.

## Critères d'acceptation

- [ ] `textes.py` expose une fonction qui prend l'ancêtre, la base et la
      branche de `lecons.md` et renvoie le fichier résolu, ou `None` pour
      refuser
- [ ] Un test vérifie le cas du 2026-11-10 : l'ancêtre a 11 lignes sous
      `## Proposées`, la base les a retirées (déplacées sous `## En vigueur`),
      la branche en a ajouté une. Le résultat est la base plus cette seule
      ligne sous `## Proposées`
- [ ] Un test vérifie qu'une ligne de l'ancêtre retirée par la branche fait
      renvoyer `None`
- [ ] Un test vérifie qu'une ligne ajoutée par la branche et déjà présente
      dans la base n'est pas dupliquée
- [ ] `mise_a_jour_branche.py` applique cette résolution à
      `memory/lecons.md`, et un test, avec des doubles de git, vérifie qu'un
      conflit sur ce fichier ne lève plus `_Refus` quand la fonction renvoie
      un fichier

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Une session qui résout à la main peut toujours se tromper. Ce ticket couvre
le chemin automatique.