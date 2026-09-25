---
id: ticket-186
title: "Une question en attente se voit, et son délai se lit"
type: feat
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-183"]
estimated_days: 1
created: 2026-09-25
---

## Le problème

Un agent a posé une question ce matin. Personne ne l'a vue, et le run a
semblé figé cinq minutes avant de repartir seul (ADR-025).

Elle s'affichait pourtant à deux endroits : l'encadré du panneau Agents, et
l'étiquette « attend une réponse » de la carte de Supervision. Les deux
supposent qu'on regarde déjà — le panneau ne montre que le projet
sélectionné, la carte demande d'être dans l'onglet Supervision. Depuis
l'onglet Tickets d'un autre projet, rien.

Et rien ne dit que l'attente est **bornée**. Cinq minutes de silence se lisent
comme une panne, pas comme une question.

## Ce qu'il faut faire

- L'événement `agent_question` porte le délai dont l'agent dispose, et
  `RunActif` le garde comme il garde déjà la question.
- Le panneau et la carte affichent le temps qui reste avant que l'agent
  reparte sur une hypothèse — un compte à rebours dit « ça attend », un
  silence dit « c'est cassé ».
- La sidebar marque en ambre le projet dont un run attend une réponse, pour
  que la question se voie depuis n'importe quel onglet.

## Ce que ça ne fait pas

Aucune notification hors de l'IDE, et aucun changement du délai lui-même :
`dialogue_timeout_s` reste un réglage de configuration, et ADR-025 garde sa
sémantique — l'agent reprend seul, il n'attend pas indéfiniment.
