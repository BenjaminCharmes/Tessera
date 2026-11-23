---
id: ticket-1040
title: "Decide whether tool-less roles run under the agent account"
type: design
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-11-23
---

# ticket-1040 — Trancher : les rôles sans outils tournent-ils sous le compte agent ?

## Objectif

Décider, et écrire dans une ADR, si les rôles appelés sans outils d'un projet
qui déclare `worktree.compte_agent` doivent eux aussi partir sous le compte
agent, avant d'étendre ce compte à un troisième projet.

## Contexte

Constaté le 23/11 sur le run de preuve de Démineur (ticket-1039) : six appels
d'agent, trois `agent_lance_sous_compte` dans `tessera.log`. Le code
l'explique, et Serpent se comporte de même depuis le début :

- `assemblage_run.py` passe `compte_agent=isole` à `_par_role` (codeur,
  reviewer, plan) et à `_en_lecture` (audit sécurité) ;
- `_sans_outils` (validateur) ne le passe pas ;
- `documenteur_run.py` (doc-technique, doc-fonctionnelle) et `lecons_run.py`
  appellent `provider_pour_role` sans `compte_agent`.

Ces rôles lancent donc le CLI sous le compte de l'utilisateur, sans outils.
ADR-083 dit « le CLI part sous ce compte » sans nommer cette exception. Ils
lisent pourtant du contenu produit par le run : diff, fichiers touchés, tickets.

Deux coûts à peser : chaque appel sous le compte paie une ouverture et une
clôture (mesurées pour ADR-091), et le compte n'a qu'un worktree à la fois
(ADR-087).

## Solution proposée

Un run `design`, borné à `memory/**` et `tickets/**` : une ADR au prochain
numéro libre qui tranche entre

1. les rôles sans outils passent aussi par le compte (même chemin que les
   autres, coût par appel en plus) ;
2. l'exception est assumée et écrite : ce qu'un CLI sans outils peut encore
   lire ou faire sous le compte de l'utilisateur, et pourquoi c'est accepté.

Si l'option 1 est retenue, la fiche du ticket de réalisation est écrite par ce
run.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` nomme les
      rôles appelés sans outils et dit s'ils passent par le compte agent.
- [ ] L'ADR dit ce qu'un CLI lancé sans outils peut encore lire sous le compte
      de l'utilisateur, d'après `backend/src/tessera/services/providers/agent_sdk.py`.
- [ ] Si l'ADR retient le passage par le compte, une fiche de ticket de
      réalisation existe sous `tickets/todo/`.

## Ce que ça ne fait pas

- Ne change aucun code.
- Ne traite pas les avertissements `agent_non_rattache` et
  `tache_du_compte_non_supprimable`, connus et sans effet (ticket-943, et les
  tâches OneDrive que Windows crée pour le compte).

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Aucun pour le code. Sans décision, l'écart entre ADR-083 et le code reste.
