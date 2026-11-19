---
id: ticket-1019
title: "The uv cache is copied and read-only for the agent account"
type: feat
status: todo
priority: high
agent: codeur
preuve_reelle: true
---

# ticket-1019 — Le cache uv se copie et passe en lecture seule pour le compte

## Objectif

ADR-088, point 2. `uv` ne revérifie pas un paquet déjà décompressé, et le
cache `uv\cache` survit au nettoyage du profil (ticket-1008). En mode lien
physique, écrire dans un `.venv` modifie aussi l'entrée du cache.

## Ce qu'il faut faire

- `env_du_profil` (`services/providers/env_agent.py`) ajoute
  `UV_LINK_MODE=copy` à l'environnement du compte.
- Le cache uv n'est plus écrit par le compte : ACL en lecture-exécution pour
  lui, contrôle total au backend, rempli par le backend lors du setup du
  worktree (ADR-085). `UV_CACHE_DIR` reste celui d'`env_agent`.
- Le cache npm reste tel quel (accepté, ADR-088) : une ligne le dit dans la
  docstring de `profil_agent.py`.
- Si la preuve montre que `uv run` sous le compte écrit dans le cache, le
  repli est de retirer `uv\cache` des `_GARDES` de `profil_agent.py` : ce
  choix se note dans la PR, pas en silence.

## Critères d'acceptation

- [ ] Un test vérifie `UV_LINK_MODE=copy` dans l'environnement bâti pour le
  compte.
- [ ] Un test vérifie que les ACL du cache uv passent par `Icacls` (lecture
  seule du compte, `F` du backend) et que l'échec est une `DroitsAgentRefuses`.
- [ ] `agent doctor` signale un cache uv que le compte peut encore écrire.

## Preuve réelle

Sur le poste, hors dépôt :

1. **Avant de coder** : lancer sous le compte la commande de test d'un projet
   (`uv run pytest`) et constater si le cache uv est écrit (horodatages).
2. Constater le mode de liaison de uv : un fichier du `.venv` est-il un lien
   physique du cache (`fsutil hardlink list`) ?
3. Après le code : sous le compte, tenter d'écrire dans le cache uv, constater
   le refus ; relancer les tests d'un projet, constater qu'ils passent.

## Ce que ça ne fait pas

- Ne vérifie pas l'intégrité d'un cache que le backend aurait rempli depuis
  une source compromise.
