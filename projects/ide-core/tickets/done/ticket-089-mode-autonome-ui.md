---
id: ticket-089
title: "Le mode autonome a enfin un bouton"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-088]
estimated_days: 1
created: 2026-09-18
---

# ticket-089 — Une surface pour le mode autonome

## Pourquoi

`run_autonomous` existe depuis la phase 5 : il choisit lui-même le prochain
ticket, par priorité et par dépendances. ticket-084 lui a ajouté
`depuis_github`, qui tire les issues `agent-ready` avant de démarrer.

Ni l'un ni l'autre n'avait de bouton. C'était du code que personne ne pouvait
atteindre depuis l'application — et c'est précisément le chemin qui permet
d'écrire une issue sur GitHub et de ne plus toucher à l'IDE.

## Critères d'acceptation

- [x] `connectAutonome({ depuisGithub })` ouvre le flux en `mode: autonomous`
- [x] La bande prend la place de la file quand la sélection est **vide** : les
      deux répondent à la même question, la différence est qui tranche
- [x] La case « partir des issues » n'apparaît que sur un projet lié à GitHub
- [x] Elle est décochée par défaut — un appel réseau vers le dépôt d'un client
      ne part pas de lui-même
- [x] Le bouton est désactivé pendant un run

## Ce que ça ne fait pas

Pas de réglage du nombre de tickets dans l'UI : le backend en prend cinq par
défaut, et les deux plafonds d'ADR-020 — dépense estimée et quota réel —
arrêtent la série avant ça la plupart du temps. Un réglage de plus à côté de
deux plafonds qui décident vraiment serait trompeur.
