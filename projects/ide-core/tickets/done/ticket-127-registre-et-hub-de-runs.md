---
id: ticket-127
title: "Registre des runs actifs et hub de diffusion des événements"
type: feat
status: done
pr_number: 149
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-23
---

# ticket-127 — Registre des runs actifs et hub de diffusion des événements

## Objectif

Poser les deux objets en mémoire dont la supervision a besoin : un registre qui
sait ce qui tourne, et un hub qui diffuse les événements à plusieurs
observateurs au lieu d'un seul.

## Contexte

`pipeline_stream.emetteur()` construit un callback qui écrit sur **une** socket
et sur elle seule. Un run n'est donc observable que par le client qui l'a
lancé, et rien n'expose l'ensemble des runs de la machine.

`RunLock` (`services/run_lock.py`) tient déjà un `dict[str, str | None]` —
projet vers ticket en cours. C'est 80 % d'un registre : il lui manque le début,
l'étape courante, les compteurs et le canal de dialogue.

Ce ticket ne change **aucun** comportement visible. Il pose le contrat que
ticket-128 branchera.

## Solution proposée

`services/run_registry.py` :

- un dataclass `RunActif` : `run_id`, `project_id`, `mode`
  (`single` | `queue` | `autonomous`), `ticket_id` courant, étape courante,
  agent courant, `demarre_a`, tour de revue, tokens entrée/sortie, coût
  estimé, dernier verdict, `DialogueChannel` ;
- un `RunRegistry` à instance unique du process, qui ouvre, met à jour et
  ferme un `RunActif`, et rend un instantané sérialisable ;
- `RunLock` **délègue** au registre au lieu de tenir son propre dictionnaire.
  Son API publique (`is_running`, `ticket_en_cours`, `acquire`) et le message
  de `RunAlreadyInProgress` ne changent pas.

`services/event_hub.py` :

- `EventHub.publish(event)` diffuse à tous les abonnés ;
- `EventHub.subscribe()` rend une file `asyncio` **bornée** ;
- règle de débordement : une file pleine jette les `agent_token` et
  `agent_tool_use`, **jamais** les transitions. Un client lent ne doit ni
  ralentir un run, ni faire disparaître un verdict ou un commit.

## Critères d'acceptation

- [ ] `services/run_registry.py` et `services/event_hub.py` existent, chacun
      sous 200 lignes
- [ ] Un test vérifie que `EventHub` diffuse un événement publié à trois
      abonnés distincts
- [ ] Un test vérifie qu'un abonné dont la file est pleine perd un
      `agent_token` et conserve un `pipeline_done` publié ensuite
- [ ] Un test vérifie qu'un abonné lent ne bloque pas `publish()`
- [ ] Un test vérifie que `RunLock.is_running` et `ticket_en_cours` gardent
      leur comportement après délégation au registre
- [ ] Un test vérifie que `RunAlreadyInProgress` nomme toujours le ticket en
      cours dans son message
- [ ] Un test vérifie que le registre rend un instantané contenant les runs de
      deux projets simultanés
- [ ] `uv run pytest` passe ; `uv run mypy src/` passe sans erreur

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

`RunLock` est appelé par tous les points d'entrée (ADR-038). Une régression y
sérialise ou désérialise les runs sans que rien ne le signale — d'où les deux
critères qui verrouillent son comportement actuel.
