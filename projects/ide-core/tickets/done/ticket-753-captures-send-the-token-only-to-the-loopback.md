---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-753
pr_number: null
priority: medium
status: done
title: Captures send the session token only to a loopback address
type: fix
---

# ticket-753 — Les captures n'envoient le jeton de session qu'à une adresse locale

## Objectif

Un `agents.json` importé ne peut pas faire envoyer le jeton de session du projet à une
adresse étrangère.

## Contexte

C-09 de `docs/audit/securite.md` (S-14), jamais ticketée. `captures_config.py` accepte tout
`http(s)://` comme `url` ; `captures.py` transmet le jeton lu dans le `.env` du projet à
l'exécuteur avec cette URL. Un projet cloné qui déclare une adresse étrangère reçoit le
jeton. ADR-062 : l'app démarre en local, sur un port libre.

## Critères d'acceptation

- [ ] `test_session_token_is_withheld_from_a_foreign_host` : une URL `https://exemple.org`
      lance la capture sans jeton
- [ ] `test_loopback_url_still_receives_it` : `http://127.0.0.1:<port>`, `http://localhost:<port>`
      et `http://[::1]:<port>` reçoivent le jeton