---
id: ticket-163
title: "L'observation d'un run ne survit ni à une déconnexion ni à une arrivée tardive"
type: fix
status: in-review
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-163 — L'observation ne survit pas à une déconnexion

## Objectif

Qu'un observateur voie l'état d'un run, qu'il soit là depuis le début ou non.

## Contexte

Premier run du banc d'essai observé depuis l'IDE. Le panneau Agents est resté
vide du début à la fin, la carte de Supervision est restée « en cours » après
la fermeture du run, et surtout : **un agent a posé une question et attendu
5 min 39 sans que rien ne s'affiche**, jusqu'à reprendre seul sur une
hypothèse (ADR-025).

Pendant ce temps le Kanban, lui, était juste — il lit l'API REST.

Deux défauts, une même promesse rompue.

### 1. La socket ne se rouvre jamais

```ts
ws.onclose = () => setConnecte(false);
```

Et rien d'autre. Le `useEffect` ouvre la socket une fois ; quand elle tombe —
un redémarrage du backend suffit — l'onglet devient aveugle **définitivement**.
Le seul signe est une étiquette « hors ligne » de dix pixels.

### 2. Le `snapshot` ne porte pas l'état des runs

À la connexion, le serveur envoie la liste des runs vivants. Le client la
range et s'arrête là : l'état par run ne s'accumule que par les événements
reçus **en direct**. Or `status` ne passe à `running` que sur `agent_started`,
émis **une seule fois**, trois secondes après le début.

Conséquence : un observateur qui arrive après cette seconde-là reste `idle`
pour toute la durée du run. Et `AgentDialogue` commence par
`if (!enCours) return null` — donc la question en attente n'est affichée nulle
part, alors qu'ADR-025 suppose qu'un humain peut y répondre.

C'est le trou laissé par ADR-041 : il a rendu le run observable par n'importe
qui, pas observable à n'importe quel moment.

## Solution proposée

1. `RunActif` retient la question en attente ; `en_dict` la publie. La poser
   la fixe, la première activité qui suit l'efface.
2. `useSupervision` rouvre la socket, avec un délai qui croît puis plafonne.
3. Le `snapshot` sème l'état de chaque run : en cours, agent, tour, question.

## Critères d'acceptation

- [ ] `RunActif` porte la question en attente et `en_dict` la rend
- [ ] Une activité de l'agent après la question efface la question
- [ ] Le client rouvre la socket après une fermeture, sans la marteler
- [ ] Un client qui se connecte pendant un run affiche l'agent en cours et la
      question en attente, sans avoir reçu `agent_started`
- [ ] `uv run pytest`, `npx vitest run`, `tsc` et `eslint` passent

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Une reconnexion qui martèle un backend éteint. Le délai croissant borne ça ;
le plafond évite qu'un onglet oublié interroge indéfiniment.
