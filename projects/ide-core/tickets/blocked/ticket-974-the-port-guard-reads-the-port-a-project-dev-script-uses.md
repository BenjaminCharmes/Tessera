---
agent: codeur
created: '2026-11-16'
depends_on: []
id: ticket-974
priority: high
status: blocked
title: La garde de port du ticket 967 lit le port que le script dev d'un projet fixe
type: fix
---

## Signalement

- Projet source : affut (session Affût, 16/11, signalement renuméroté : le
  numéro 973 qu'il avait reçu appartient déjà au ticket des hooks, PR #1115)
- Nature : bug, régression du ticket-967

## Contexte

Depuis le redémarrage du 16/11 qui a activé le 967,
`POST /api/v1/projects/affut/services/start` répond 409 « viserait le port
5173, qui est celui de Tessera ». Le service `frontend` d'Affût lance
`npm run dev` (cwd `frontend`) et Vite y écoute sur 5194, fixé par
`server.port` dans `frontend/vite.config.ts`.

`port_vise()` (`backend/src/tessera/services/verification/ports_de_tessera.py`)
compte toute commande `vite`, `npm run dev`, `pnpm dev` ou `yarn dev` sans
`--port` comme 5173, sans regarder le projet. Relevé le 16/11 : les
frontends d'affut (5194), carriere (5180), curio (5196), freelance (5190),
habit-tracker (5191), homelab-monitor (5192), repo-health (5193) et vigie
(5195) déclarent tous `npm run dev` et fixent leur port dans
`frontend/vite.config.ts`. **Tous sont refusés.** Un `npm run dev` qui lance
`next dev` serait refusé de même alors que Next écoute sur 3000.

## Ce qu'il faut faire

Quand la commande ne donne pas de port explicite, la garde le cherche dans le
dossier du service (`racine du projet / cwd`) avant de retomber sur 5173 :

1. Pour `npm run dev`, `pnpm dev`, `yarn dev` : lire le script `dev` du
   `package.json` de ce dossier. Un `--port N` / `-p N` / `PORT=N` dans ce
   script donne le port. Un script qui ne lance pas `vite` (par exemple
   `next dev`) ne vise pas 5173 : port inconnu, pas de refus.
2. Si le script lance `vite` (ou si la commande est `vite`) : lire
   `server.port` dans `vite.config.ts`, `.mts`, `.js` ou `.mjs` de ce dossier,
   par une expression régulière sur `port\s*:\s*(\d{2,5})` à l'intérieur du
   bloc `server` (pas d'exécution du fichier). Trouvé : ce port. Absent :
   5173, comme aujourd'hui.
3. Fichier absent, illisible ou JSON invalide : on garde le comportement
   actuel (5173 pour une commande Vite), la garde reste fermée.

`port_vise(commande)` garde sa signature pour les appels existants ; la
lecture du projet passe par un paramètre facultatif `dossier: Path | None`,
et `_refuser_un_port_de_tessera` (`routers/services.py`) lui passe
`racine / declare["cwd"]`.

## Critères d'acceptation

- [ ] Un service `npm run dev`, cwd `frontend`, dont `frontend/vite.config.ts`
      porte `server: { port: 5194 }`, n'est plus refusé (test sur dossier
      temporaire).
- [ ] Le même service sans `port` dans `vite.config.ts` reste refusé en 409
      avec le port 5173 (test).
- [ ] Un script `dev` de `package.json` qui porte `--port 5174` est refusé
      (5174 est un port de Tessera) ; un script `dev` qui lance `next dev`
      ne l'est pas (tests).
- [ ] `vite.config.ts` absent ou `package.json` illisible : refus comme
      aujourd'hui (test).
- [ ] Les cas paramétrés existants de `test_port_vise` passent inchangés.
- [ ] **Preuve réelle (session ide-core, après redémarrage)** :
      `POST /api/v1/projects/vigie/services/start` (ou un autre projet listé
      ci-dessus, avec l'accord de sa session) ne répond plus 409 ; le
      frontend écoute sur son port de `vite.config.ts`.

## Ce que ça ne fait pas

- N'exécute ni `vite.config` ni `package.json` : une config qui calcule son
  port (variable d'environnement, fonction) reste traitée comme 5173.
- Ne vérifie pas `strictPort` : un Vite qui glisse de 5194 à un port libre
  n'est pas suivi.
- Ne touche pas aux contournements déjà posés dans les dépôts des projets
  (`npm run dev -- --port N`) : ils restent valides.