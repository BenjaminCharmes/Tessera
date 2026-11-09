---
id: ticket-897
title: "The interface remembers the session token across tabs and restarts"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-11-09
---

# ticket-897 — L'interface se souvient du jeton de session d'un onglet à l'autre

## Objectif

Qu'avec un jeton fixe (`STATIC_TOKEN`), l'utilisateur ne saisisse le jeton
qu'une fois par navigateur, sans qu'il soit jamais servi par Vite.

## Contexte

Le 09/11, Benjamin a passé Tessera au jeton fixe pour ne plus voir le bandeau
« Jeton de session ». Le bandeau revient pourtant à chaque nouvel onglet :
`frontend/src/lib/auth.ts` range le jeton en `sessionStorage`, propre à
l'onglet.

`.env.example` indique encore « Côté frontend, la même valeur se déclare dans
`frontend/.env.local` : `VITE_STATIC_TOKEN=<token>` », alors que `auth.ts` ne lit
plus cette variable depuis le ticket-877. Et elle ne doit pas revenir : toute
variable `VITE_` est inscrite dans le code que Vite sert sur `localhost:5173`,
qu'un agent sous un autre compte peut lire par le réseau (ticket-894).

## Solution proposée

- `auth.ts` range le jeton en `localStorage` au lieu de `sessionStorage`, avec la
  même clé ; il lit d'abord `localStorage`, puis l'ancienne valeur de
  `sessionStorage` pour migrer.
- Une réponse 401 efface le jeton rangé (il est périmé : redémarrage sans jeton
  fixe) avant d'afficher le bandeau.
- `.env.example` : la ligne `VITE_STATIC_TOKEN` est retirée, remplacée par une
  phrase qui dit que l'interface retient le jeton saisi une fois.

## Critères d'acceptation

- [ ] `auth.ts` écrit le jeton en `localStorage` ; `auth.test.ts` le vérifie.
- [ ] Un jeton présent seulement en `sessionStorage` est relu et recopié en
      `localStorage` ; un test le vérifie.
- [ ] Après une réponse 401, le jeton rangé est effacé ; un test le vérifie.
- [ ] `.env.example` ne contient plus `VITE_STATIC_TOKEN`.
- [ ] Le diff n'ajoute aucune lecture de `import.meta.env` dans `auth.ts`.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

`localStorage` persiste sur le disque du profil du navigateur : acceptable pour
un jeton qui ne protège que le loopback, et qu'un agent sous un autre compte ne
peut pas lire.

## Ce que ça ne fait pas

- Ne change ni le backend ni la saisie du bandeau.
