---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 1
id: ticket-942
pr_number: null
priority: high
status: done
title: An app squatting port 5173 can no longer pick up the API token
type: fix
---

# ticket-942 — Une app qui occupe le port 5173 ne récupère plus le jeton de l'API

## Objectif

Qu'un serveur lancé par le code d'un projet sur `localhost:5173` ne puisse ni
lire le jeton de session, ni passer pour l'interface de Tessera.

## Contexte

Audit du 12/11 (F3). `frontend/vite.config.ts` ne fixe pas `strictPort` : si
5173 est pris, le Vite de Tessera glisse en silence sur 5174. La page de
l'intrus a alors l'origine `http://localhost:5173`. Elle lit le jeton que
`frontend/src/lib/auth.ts` garde dans `localStorage`, et ses requêtes portent
une origine que `auth.py` et `main.py` (CORS) tiennent pour déclarée :
écriture d'`agents.json` par `/fs/write`, puis `services/start`, exécuté sous
le compte du backend.

## Solution proposée

1. `server.strictPort: true` dans `frontend/vite.config.ts` : un port pris
   fait échouer le lancement, et `tessera.ps1 run` le dit.
2. Le jeton n'est plus gardé dans `localStorage` mais dans `sessionStorage`
   (perdu à la fermeture de l'onglet, relu par `#jeton=`). Un jeton déjà
   présent dans `localStorage` est effacé au chargement.
3. `tessera.ps1 doctor` signale un port 5173 déjà pris avant de lancer Vite.

## Critères d'acceptation

- [ ] `frontend/vite.config.ts` porte `strictPort: true`, et un test le
      vérifie.
- [ ] Un test vitest : après `#jeton=abc`, `localStorage` ne contient aucune
      clé de jeton, et `sessionStorage` le contient.
- [ ] Un test vitest : une clé de jeton héritée dans `localStorage` est
      effacée au chargement.
- [ ] Un test de `backend/tests/` vérifie que `tessera.ps1 doctor` teste le
      port 5173.

## Ce que ça ne fait pas

- Ne sert pas l'interface depuis le backend (origine unique) : piste plus
  lourde, à concevoir à part si besoin.
- Ne lance pas les `services` sous `AGENT_USER` (ADR-042 : lancés par
  l'utilisateur).