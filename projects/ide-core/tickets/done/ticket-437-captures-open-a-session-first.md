---
agent: codeur
created: '2026-10-14'
depends_on: []
estimated_days: 0.5
id: ticket-437
pr_number: null
priority: medium
status: done
title: Screen captures can open a session on a project that requires a token, without
  the token ever leaving the server
type: feat
---

# ticket-437 — Les captures savent ouvrir une session

## Signalement

- Projet source : vigie
- Nature : idee
- Reçu le : 2026-10-14

## Description

Vigie exige un jeton (ACCESS_TOKEN, échangé contre un cookie HttpOnly par POST /api/session). scripts/captures.mjs n'a aucun moyen de s'authentifier : sur Vigie, chaque capture montrerait l'écran « Jeton d'accès requis ». Proposition : une clé facultative dans la section captures d'agents.json, par exemple "session": {"chemin": "/api/session", "jeton_env": "ACCESS_TOKEN", "fichier_env": "backend/.env"}. Tessera lit le jeton côté serveur dans le .env du projet, le passe au script hors ligne de commande (stdin ou variable d'environnement), le script fait le POST dans le contexte du navigateur, puis capture. Le jeton n'apparaît ni dans la réponse, ni dans les logs, ni dans agents.json. Contournement actuel : mon propre script Playwright dans le scratchpad.

## Contexte

Session vigie, vérification de la refonte v3, 2026-10-14

## Critères d'acceptation

- [ ] Un test vérifie la lecture d'une clé `session` facultative dans la
      section `captures` d'`agents.json` (chemin, nom de la variable,
      fichier .env), et qu'une section sans elle se comporte comme avant
- [ ] Un test vérifie que le jeton est lu côté serveur dans le fichier .env
      du projet et transmis au script hors ligne de commande (variable
      d'environnement ou entrée standard)
- [ ] Un test vérifie que le jeton n'apparaît ni dans la réponse de
      `POST …/captures`, ni dans les journaux, ni dans les arguments du
      processus lancé
- [ ] Un test vérifie qu'un jeton absent du .env donne une erreur 409 claire,
      sans lancer de capture
- [ ] `docs/guide-utilisateur.md` documente la clé `session`