---
agent: codeur
created: 2026-11-06
depends_on:
- ticket-878
estimated_days: 0.5
id: ticket-879
pr_number: 980
priority: high
status: done
title: The agent hook refuses reading the session token file like Tessera's .env
type: feat
---

# ticket-879 — Le hook refuse aux agents la lecture du fichier de jeton

## Objectif

Un agent qui tente `cat`, `Get-Content`, `Read`, `Grep` ou `python -c
"open(…)"` sur `ide_state_dir/jeton-de-session` est refusé, comme pour le
`.env` de Tessera.

## Contexte

Le ticket-878 écrit le jeton de session dans un fichier, seul point de
remise hors mémoire. `backend/src/tessera/services/providers/garde_jetons.py`
protège aujourd'hui le seul `.env` de Tessera, par un contrôle lexical sur le
chemin résolu. Un chemin écrit avec une variable (`$LOCALAPPDATA/…`,
`%LOCALAPPDATA%\…`, `~/…`) n'est pas reconnu.

## Solution proposée

- La cible protégée devient un ensemble : le `.env` et le fichier de jeton
  (chemin fourni par `jeton_de_session`, ticket-878).
- La résolution d'un chemin trouvé dans une commande applique
  `os.path.expandvars` et `expanduser` avant `resolve()`.
- Même contrôle pour `Read`, `Glob`, `Grep` et `Bash`.

Le plafond d'ADR-031 reste : un chemin construit en deux étapes passe. C'est
dit dans l'ADR du ticket-878.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_garde_jetons.py` vérifie que `cat
      <chemin absolu du fichier de jeton>` est refusé.
- [ ] Un test vérifie que `Get-Content $LOCALAPPDATA/Tessera/jeton-de-session`
      est refusé quand `LOCALAPPDATA` désigne le dossier d'état du test.
- [ ] Un test vérifie que `python -c "open('<chemin>')"` est refusé.
- [ ] Un test vérifie que `Read` et `Grep` sur ce chemin sont refusés.
- [ ] Un test vérifie que `cat ./jeton-de-session` dans le dossier d'un projet
      passe.

## Dépendances

ticket-878.

## Estimation

Une demi-journée.

## Risques

Aucun sur les runs : le fichier n'est lu que par l'app Tauri et le lanceur.