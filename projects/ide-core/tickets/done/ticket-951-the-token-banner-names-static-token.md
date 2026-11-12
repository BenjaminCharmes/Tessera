---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.1
id: ticket-951
pr_number: null
priority: medium
status: done
title: "The token banner says where the token comes from when STATIC_TOKEN is set"
type: fix
---

# ticket-951 — Le bandeau du jeton dit d'où il vient quand `STATIC_TOKEN` est défini

## Objectif

Qu'un utilisateur à qui l'interface demande le jeton sache quelle valeur
coller, quel que soit le mode du backend.

## Contexte

Depuis le ticket-942, le jeton saisi est gardé en `sessionStorage` : il se
redemande à chaque nouvel onglet, et l'ancienne copie de `localStorage` a été
effacée. Le bandeau renvoie alors au fichier `jeton-de-session`, que le
backend n'écrit **pas** quand `STATIC_TOKEN` est défini
(`services/noyau/jeton_de_session.py`). Le 12/11, Benjamin a reçu la demande
avec un chemin vers un fichier absent.

## Solution

Le texte du bandeau donne les deux cas : avec `STATIC_TOKEN`, c'est sa
valeur ; sinon, le fichier tiré au démarrage. Il dit aussi que la saisie vaut
jusqu'à la fermeture de l'onglet.

Pour ne pas ressaisir le jeton chaque jour (demande de Benjamin), le champ se
déclare mot de passe (`autocomplete="current-password"`, identifiant fixe
`tessera`) : le gestionnaire du navigateur propose de l'enregistrer et le
remplit au prochain onglet. Le jeton reste dans le coffre du navigateur,
jamais en `localStorage` : la protection du ticket-942 tient.

## Critères d'acceptation

- [x] Après un 401, le bandeau nomme `STATIC_TOKEN` et les deux chemins du
      fichier (test vitest).
- [x] Il dit que le jeton est gardé jusqu'à la fermeture de l'onglet (test
      vitest).
- [x] Le champ porte `autocomplete="current-password"` et le formulaire un
      identifiant `username` fixe (test vitest).

## Ce que ça ne fait pas

- Ne remet pas le jeton en `localStorage` : c'est le choix du ticket-942.
- N'affiche jamais la valeur du jeton.
