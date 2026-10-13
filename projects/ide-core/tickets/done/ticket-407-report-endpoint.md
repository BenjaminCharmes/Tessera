---
agent: codeur
created: 2026-10-13
depends_on: []
estimated_days: 0.5
id: ticket-407
pr_number: null
priority: high
status: done
title: Any project can report a Tessera bug or idea, which lands as an ide-core ticket
type: feat
---

# ticket-407 — Un signalement depuis un projet devient un ticket ide-core

## Objectif

Qu'un défaut ou une amélioration de Tessera repérés en travaillant sur un
autre projet arrivent dans le backlog d'ide-core par un seul appel HTTP, sans
passer par une session qui pilote ide-core.

## Contexte

Depuis le 07/10, les sessions de projet (affut, carriere, vigie…) remontent
les soucis de Tessera par message à la session ide-core, ou à défaut dans un
fichier de boîte de dépôt. Ce canal a produit une vingtaine de tickets
(375 à 406), mais il tient à une convention entre sessions : un message envoyé
à un nom de session périmé se perd, et rien n'existe dans le produit
lui-même. Le ticket-408 ajoutera le bouton dans l'IDE ; celui-ci pose
l'endpoint dont il a besoin, et que les agents peuvent aussi appeler.

`POST /api/v1/projects/{id}/tickets` sait déjà créer un ticket
(`routers/tickets.py`), mais il ne garde aucune trace de l'origine.

## Solution proposée

- Un nouveau routeur `routers/signalements.py`, monté sous `/api/v1` dans
  `main.py` : `POST /api/v1/signalements`, réponse 201 avec le `Ticket` créé.
- Corps `SignalementCreate` (Pydantic v2) : `projet: str`,
  `nature: Literal["bug", "idee"]`, `titre: str` (non vide après `strip`),
  `description: str` (non vide), `contexte: str = ""`.
- Le projet source doit exister (sinon 404). Le ticket est créé dans le
  projet `ide-core`, nommé par une constante du module, via le même service
  que `create_ticket` : `type` `fix` pour un bug, `feat` pour une idée,
  `priority: medium`, `agent: codeur`, `status: todo`, `title` = le titre.
- Le corps du ticket porte, dans cet ordre : une section `## Signalement`
  (projet source, nature, date UTC de réception), `## Description`,
  `## Contexte` si fourni, et `## Critères d'acceptation` avec la seule
  ligne `- [ ] À écrire au triage`. Un signalement brut lancé tel quel sera
  donc refusé par le validateur : le triage reste une étape humaine.

## Critères d'acceptation

- [ ] `POST /api/v1/signalements` avec `nature: "bug"` crée dans `ide-core`
      un ticket `type: fix`, `status: todo`, et renvoie 201 ; un test le couvre
- [ ] Avec `nature: "idee"`, le ticket créé est `type: feat` ; un test le couvre
- [ ] Le corps du ticket créé contient la section `## Signalement` avec le nom
      du projet source et la ligne `- [ ] À écrire au triage` ; un test le vérifie
- [ ] Un projet source inexistant renvoie 404 et ne crée aucun ticket ; un test le couvre
- [ ] Un `titre` vide ou fait d'espaces renvoie 422 ; un test le couvre
- [ ] `main.py` monte le routeur `signalements` sous le préfixe `/api/v1`

## Dépendances

Aucune. Le ticket-408 (bouton dans l'IDE) en dépend.

## Estimation

Une demi-journée.

## Risques

- Les tests ne doivent pas écrire dans le vrai `projects/ide-core/` :
  passer par le même mécanisme de dossier de projets temporaire que les
  tests existants de `routers/tickets.py`.
- Aucune authentification propre : l'endpoint suit `STATIC_TOKEN` comme le
  reste de l'API.

## Ce que ça ne fait pas

- Ni déduplication ni regroupement des signalements.
- Pas de lancement automatique : le ticket attend son triage.