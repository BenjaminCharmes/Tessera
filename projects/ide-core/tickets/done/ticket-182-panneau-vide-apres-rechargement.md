---
id: ticket-182
title: "Recharger la page vide le panneau Agents d'un run qui tourne"
type: fix
status: done
pr_number: 42
priority: high
agent: codeur
depends_on: ["ticket-163"]
estimated_days: 1
created: 2026-09-25
---

# ticket-182 — Le panneau Agents est vide après un rechargement

## Objectif

Qu'un run en cours se montre au travail, même pour qui arrive après son début.

## Contexte

Page rechargée pendant une file. La carte de Supervision est juste —
`file 3/5`, ticket-018, 12 min 50 — mais le **panneau Agents est vide** : aucun
bloc codeur, aucun token. Le run travaille, l'écran dit qu'il ne fait rien.

### La cause

Ticket-163 a fait semer l'état par l'instantané :

```ts
export function etatDepuisRun(run: RunActif): StreamState {
  return { ...INITIAL, status: "running", currentAgent: run.agent, ... };
}
```

`...INITIAL` porte `events: []`. Or les blocs se dérivent des événements :

```tsx
const coderStarted = events.some(
  (e) => e.type === "agent_started" && e.agent === "codeur",
);
```

Un observateur tardif n'a aucun événement — ils sont passés avant lui. Les
drapeaux restent donc faux, et le panneau ne rend rien, alors que l'état sait
parfaitement quel agent parle.

C'est le **quatrième** défaut de la même famille : ticket-163 pour la question
en attente, ticket-172 pour l'avancement, ticket-181 pour le chemin par
événement, celui-ci pour les blocs. À chaque fois, une information existe dans
l'état et un consommateur la cherche ailleurs.

## Solution proposée

Les blocs se déduisent de l'état, les événements ne faisant que l'enrichir. Le
pipeline a un ordre — codeur, sécurité, reviewer, validateur — et cet ordre
suffit : si le reviewer parle, le codeur a parlé avant lui.

## Critères d'acceptation

- [ ] Un état semé par l'instantané avec `currentAgent: codeur` montre le bloc
      codeur
- [ ] Un `currentAgent` postérieur au codeur le montre comme terminé
- [ ] `currentAgent: reviewer` montre les deux blocs
- [ ] Un agent intermédiaire — sécurité — montre le codeur terminé et pas le
      reviewer
- [ ] Les événements gardent leur effet quand ils sont là
- [ ] Un état au repos ne montre aucun bloc
- [ ] `npx vitest run`, `tsc`, `eslint` et `npm run build` passent

## Dépendances

ticket-163, dont il termine ce qu'il avait commencé.

## Estimation

Moins d'une journée.

## Risques

Déduire d'un ordre suppose que cet ordre ne change pas. Il est déjà celui du
pipeline, et le nommer à un seul endroit vaut mieux que de le supposer partout.
