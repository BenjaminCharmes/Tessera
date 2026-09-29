---
id: ticket-211
title: "Les appels des rôles sans outils s'enregistrent dans agent_calls, avec leur provider"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-211 — Enregistrer les appels des rôles sans outils

## Objectif

Chaque appel LLM d'un run apparaît dans `agent_calls` avec son rôle, son
modèle et son provider : l'audit sécurité, la validation et la mise à jour de
la documentation aussi, pas seulement le codeur, le reviewer et l'architect.

## Contexte

`save_agent_call` n'a qu'un appelant : `AgentRunner`. Les services
`SecurityAuditorService`, `ValidatorService` et ceux de `doc-technique` et
`doc-fonctionnelle` appellent `provider.complete` directement, et rien ne
garde de trace de ces appels.

Sur la base locale, on compte 64 événements `security_audit_done` et
`validation_done`, et 0 ligne `securite` ou `validateur` dans `agent_calls`.
Conséquences :

- le tableau des coûts sous-estime chaque run qui active ces portes ;
- rien ne permet de dire si un rôle déclaré sur Ollama (ADR-046) a vraiment
  été servi par Ollama, ou s'il a basculé sur son repli. L'événement
  `provider_fallback` le dit sur le moment, mais pas après coup.

## Solution proposée

Un seul point d'enregistrement pour tout appel fait dans le cadre d'un run.
Par exemple, un décorateur ou une enveloppe de `LLMProvider` construite par
`provider_pour_role`, qui connaît `run_id`, `ticket_id` et `role`. Chaque
service n'a alors pas à y penser. `provider` enregistre le provider qui a
**effectivement** répondu : celui du repli si le repli a servi.

## Critères d'acceptation

- [ ] Un test : un run avec sécurité et validateur activés produit une ligne
      `agent_calls` pour `securite` et une pour `validateur`, avec `run_id`
      et `ticket_id` renseignés
- [ ] Un test : un rôle déclaré sur `ollama`, dont le provider lève
      `ProviderIndisponible`, enregistre `provider = "agent_sdk"` et le
      modèle du repli
- [ ] Un appel Ollama s'enregistre avec `cost_usd = 0.0` et
      `provider = "ollama"`
- [ ] Aucun service n'appelle `save_agent_call` directement en dehors du point
      d'enregistrement unique

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Les appels hors run (chat, analyse de projet) n'ont pas de `run_id`. Il faut
les laisser hors du périmètre ou leur donner un identifiant explicite, mais
ne jamais les rattacher au run en cours par erreur.
