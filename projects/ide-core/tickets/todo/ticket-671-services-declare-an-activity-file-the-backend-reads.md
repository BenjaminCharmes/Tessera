---
id: ticket-671
title: "A service declares an activity file, and the backend reads it closed on failure"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-29
---

# ticket-671 — Un service déclare un fichier d'activité, que le backend lit

## Objectif
Que le backend sache lire l'activité des agents d'un produit dans le fichier que
ce produit écrit, et ne rende **aucun agent** à la moindre anomalie.

## Contexte
ADR-064 et `docs/superpowers/specs/2026-10-29-salle-des-serveurs-design.md`,
sections 4 et 5 : le contrat du fichier et les interfaces y sont fixés. Ce ticket
n'écrit que le backend ; aucun produit n'émet encore.

## Solution proposée
- `ServiceDeclare` (`backend/src/tessera/models/agent.py`) gagne `activite: str | None = None`.
- `backend/src/tessera/models/activite.py` : `AgentDeProduit` et `ActiviteDeService`,
  champs et bornes de la section 4 de la spec ; un champ inconnu est refusé.
- `backend/src/tessera/services/activite_produit.py` : `lire_activite(racine,
  chemin, maintenant) -> list[AgentDeProduit]`. Elle renvoie `[]` sur tout échec
  et ne lève jamais ; le chemin résolu (liens compris) doit rester dans le projet.
- `GET /services/running/activite` dans un routeur à part
  (`routers/services_activite.py`) : une entrée par service qui déclare `activite`
  et dont l'app figure dans l'inventaire courant.

## Critères d'acceptation
- [ ] `activite` dans `services[]` d'un `agents.json` est accepté, et un `agents.json` sans ce champ se charge comme avant
- [ ] Un fichier valide rend ses agents, dans l'ordre du fichier
- [ ] Chacune de ces causes rend `[]`, avec un test par cause : fichier absent, JSON invalide, plus de 16 Ko, `version` autre que 1, champ inconnu, plus de 12 agents, `id` en double, `libelle` de plus de 80 signes, `maj` vieille de plus de 30 s, `maj` à plus de 5 s dans le futur
- [ ] Un chemin qui sort du projet (`..` ou lien) rend `[]`, avec un test
- [ ] `GET /services/running/activite` ne rend rien pour un service dont l'app ne tourne pas, même avec un fichier frais

## Ce que ça ne fait pas
- Ne dessine rien : c'est ticket-672 et ticket-673.
- N'écrit jamais le fichier et n'interroge aucune route d'un produit.
- Ne touche à aucun `agents.json` de projet : la déclaration est un geste humain (ADR-027).
