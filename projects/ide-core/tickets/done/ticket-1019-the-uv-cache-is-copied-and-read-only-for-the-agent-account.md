---
agent: codeur
created: 2026-11-19
depends_on: []
estimated_days: 1
id: ticket-1019
pr_number: null
preuve_reelle: true
priority: high
status: done
title: The uv cache is copied and no longer survives the profile wipe
type: fix
---

# ticket-1019 — Le cache uv se copie et ne survit plus au nettoyage du profil

## Objectif

ADR-088, point 2. `uv` ne revérifie pas un paquet déjà décompressé, et le
cache de uv survit au nettoyage du profil (ticket-1008) : un fichier modifié
par un run y attend le run suivant.

## Essais faits le 19/11, avant de coder

- Le compte écrit le cache uv dès `uv run --no-project python --version`
  (la ligne « python (uv run) » d'`agent doctor`) : après un `agent doctor`,
  le dossier contient `interpreter-v4` et `sdists-v9`.
- Un cache en lecture seule pour le compte, prévu d'abord, ferait donc
  échouer `agent doctor` et toute commande `uv run`. C'est le repli prévu par
  l'ADR-088 qui s'applique : le cache uv ne se garde plus.

## Ce qu'il faut faire

- `services/providers/env_agent.py`, `env_du_profil` : ajouter
  `UV_LINK_MODE=copy` (jamais de lien physique entre un `.venv` et le cache),
  et la clé à `CLES_AUTORISEES`.
- `services/providers/profil_agent.py` : `_GARDES` ne garde plus que le cache
  npm. Le cache uv part avec le reste du profil à chaque nettoyage.
- Les docstrings de `profil_de` et de `profil_agent.py` disent pourquoi : npm
  vérifie l'intégrité de ce qu'il sort de son cache, uv non.
- `CACHE_UV` et `UV_CACHE_DIR` restent : le cache vit toujours dans le profil,
  le temps d'un appel.

## Critères d'acceptation

- [ ] Un test vérifie que `env_du_profil` rend `UV_LINK_MODE` égal à `copy`,
  et que la clé est dans `CLES_AUTORISEES`.
- [ ] Un test : après `reinitialiser_profil`, un fichier posé sous
  `uv/cache/` du profil n'existe plus, et un fichier posé sous `npm-cache/`
  existe encore.
- [ ] La docstring de `profil_agent.py` ne dit plus que le cache uv survit.

## Preuve réelle

Sous le compte, sur le poste : `agent doctor` reste vert sur ses cinq lignes ;
après la clôture d'un appel, le dossier du cache uv du profil est vide ou
absent, et `npm-cache` est toujours là.

## Ce que ça ne fait pas

- Ne remplit pas le cache par le backend : un projet sous le compte qui
  utilise uv retélécharge ses paquets à chaque run. Aucun n'en utilise
  aujourd'hui.
- Ne touche pas au cache npm (accepté, ADR-088).