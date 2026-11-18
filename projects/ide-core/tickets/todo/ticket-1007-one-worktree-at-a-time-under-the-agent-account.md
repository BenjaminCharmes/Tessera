---
id: ticket-1007
title: "Two worktrees never carry a call under the agent account at the same time"
type: fix
status: todo
priority: high
agent: codeur
depends_on: []
preuve_reelle: true
---

## Signalement

- Suite du ticket-998 (ADR-087), constat H3 : un agent d'un autre projet, même
  compte, écrit dans un worktree dont l'appel est en cours.

## Ce qu'il faut faire

Dans `services/providers/droits_appel.py` :

- `ouvrir_appel` attend (`asyncio.Condition` à la place du `_VERROU` nu) tant
  qu'un appel est actif sur **une autre** racine. Plusieurs appels sur la
  **même** racine restent permis (`_ACTIFS` compte déjà par racine). Attente
  équitable, dans l'ordre d'arrivée, journalisée au-delà de quelques secondes.
- `settings.agent_calls_parallel` (env `AGENT_CALLS_PARALLEL`, défaut `false`) :
  `true` rétablit le comportement actuel. À déclarer dans `.env.example`.
- La commande de test et l'app du contrôle visuel comptent comme des appels
  (ils passent déjà par `ouvrir_appel`) : l'app visuelle tient le compte tant
  qu'elle tourne ; le dire dans la docstring.
- Un appel annulé (run arrêté) libère sa place : `clore_appel` dans un `finally`
  chez chaque appelant, à vérifier.
- Le test `droits_appel` sans `AGENT_USER` ne change pas.

## Critères d'acceptation

- [ ] Un second `ouvrir_appel` sur une autre racine attend le `clore_appel` du premier ; sur la même racine il passe.
- [ ] Avec `AGENT_CALLS_PARALLEL=true`, les deux passent.
- [ ] Une annulation pendant l'attente ne laisse aucun compteur faux dans `_ACTIFS`.
- [ ] Sans `AGENT_USER`, aucune attente.
- [ ] `.env.example` documente `AGENT_CALLS_PARALLEL`.

## Preuve réelle

Lancer deux runs de deux projets à la fois sous `AGENT_USER` ; constater dans le
journal que les appels du second attendent ceux du premier, que les deux runs
aboutissent, et que `AGENT_CALLS_PARALLEL=true` les fait se recouvrir. Noter la
durée totale comparée.

## Ce que ça ne fait pas

- Ne sérialise pas le travail sans agent (git, CI, livraison) : deux projets
  continuent d'y tourner en parallèle (ADR-038).
- Décision de débit à relire par l'humain : le défaut ferme, l'opt-out s'énonce.
