---
id: ticket-137
title: "Déclarer les services d'un projet et les lancer depuis le backend"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-132"]
estimated_days: 2
created: 2026-09-23
---

# ticket-137 — Déclarer les services d'un projet et les lancer

## Objectif

Permettre à un projet de déclarer ses services (backend, frontend, base) et à
l'IDE de les démarrer et de les arrêter, sans agent et sans shell.

## Contexte

ADR-042 tranche : la commande se **déclare**, elle ne se devine pas. Les six
projets de `projects/` décrivent leur démarrage dans des sections aux noms
différents — « Commandes », « Lancement du projet », « Commandes clés » —
mêlé aux commandes de test et d'installation.

Le précédent est `test_command` : détecté par heuristique, surchargeable dans
`agents.json`, exécuté par `create_subprocess_exec` **sans shell**. Trois de
ses propriétés ne transposent pas :

- un serveur ne se termine jamais, donc pas de `communicate()` avec timeout ;
- un projet peut avoir **plusieurs** processus — `orion-backend` veut uvicorn
  *et* un worker Celery ;
- l'installation (`npm ci`, `conda env create`) est dans la même section du
  `CLAUDE.md` mais n'est pas un lancement.

## Solution proposée

**Manifeste** — `agents.json` accepte `services`, une liste de
`{"nom": "...", "commande": "...", "cwd": "..."}`. `cwd` est optionnel et
relatif à la racine du projet. Absent ou vide : le projet n'est pas lançable.

**`ProcessRegistry`** — en mémoire du process, comme `RunLock` et
`RunRegistry` (ADR-038, ADR-041) : nom, projet, PID, démarré à, état. Les
processus sont des **enfants** du backend et sont tués à son arrêt, y compris
sur une extinction brutale du backend — c'est ce qui rend inutile toute
reprise après redémarrage.

**Endpoints** — `POST /api/v1/projects/{id}/services/start`,
`POST .../services/stop`, `GET .../services`. Un projet sans `services`
déclarés répond 409 avec un message qui dit quoi déclarer.

**Sortie** — chaque ligne de `stdout`/`stderr` part sur l'`EventHub`
d'ADR-041, avec un type dédié, soumise à la même règle d'abonnement que les
tokens : un serveur bavard ne doit pas noyer les transitions d'un run.

## Critères d'acceptation

- [ ] Un projet sans `services` dans `agents.json` répond 409 à `start`, avec
      un message qui nomme la clef attendue
- [ ] Un test vérifie qu'un service déclaré démarre et apparaît dans
      `GET .../services` avec son PID
- [ ] Un test vérifie que `stop` termine le processus et le retire du registre
- [ ] Un test vérifie que deux services d'un même projet démarrent ensemble
- [ ] Un test vérifie que la commande est exécutée **sans shell** : une
      commande contenant `&&` ou `|` échoue au lieu d'être interprétée
- [ ] Un test vérifie qu'un `cwd` sortant de la racine du projet est refusé
- [ ] Un test vérifie que la sortie du service part sur l'`EventHub` et n'est
      reçue qu'après abonnement
- [ ] Les processus enfants sont arrêtés à l'extinction du backend
- [ ] `uv run pytest` et `uv run mypy src/` passent

## Dépendances

ticket-132 (l'ADR). S'appuie sur l'`EventHub` de ticket-127.

## Estimation

2 jours.

## Risques

Un processus qui survit à l'IDE garde un port et n'a plus rien pour l'arrêter
— c'est l'alternative qu'ADR-042 rejette, et le test d'extinction est ce qui
l'empêche de revenir par accident. Sur Windows, tuer un enfant ne tue pas
forcément ses petits-enfants : `npm run dev` lance souvent un sous-processus.
