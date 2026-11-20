---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-758
pr_number: 908
priority: low
status: done
title: 'Hardening: no token in access logs or remote URLs, strict clone URLs, bounded
  reports'
type: chore
---

# ticket-758 — Durcissements : jeton hors des journaux et des remotes, URL de clone stricte, signalements bornés

## Objectif

Clore les durcissements C-11 de `docs/audit/securite.md` (S-19, S-20, S-21), jamais ticketés.

## Contexte

- S-19 : le jeton de la WebSocket passe en query string (`backend/src/tessera/auth.py`), et
  peut finir dans le journal d'accès d'uvicorn.
- S-20 : `git_clone._GITHUB_URL_RE` et `git_link._REPO_URL` finissent par `$` : un saut de
  ligne final passe en Python.
- S-21 : `git_clone.py` sait insérer `github_token` dans l'URL de clone, donc dans
  `.git/config` ; aucun appelant ne le passe aujourd'hui.
- `SignalementCreate` n'a pas de borne de taille.

## Critères d'acceptation

- [ ] `test_access_log_does_not_show_the_ws_token` : une ligne de journal d'accès d'une
      requête `?token=abc` ne contient pas `abc`
- [ ] `test_clone_url_with_a_trailing_newline_is_refused` : les deux motifs refusent une URL
      suivie de `\n` (`fullmatch` ou `\Z`)
- [ ] `test_clone_never_writes_a_token_into_the_remote_url` : le paramètre `github_token` de
      `git_clone.py` est supprimé, et l'URL de clone n'en contient jamais
- [ ] `test_signalement_over_the_size_limit_is_refused` : un signalement au-delà de la borne
      rend 422