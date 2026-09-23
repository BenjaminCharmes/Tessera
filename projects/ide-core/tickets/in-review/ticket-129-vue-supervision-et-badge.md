---
id: ticket-129
title: "Vue Supervision de tous les runs, et badge permanent dans le NavRail"
type: feat
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-128"]
estimated_days: 2
created: 2026-09-23
---

# ticket-129 — Vue Supervision de tous les runs, et badge permanent

## Objectif

Voir d'un coup d'œil ce que l'IDE est en train de faire, sur tous les projets,
et ouvrir le détail complet de n'importe quel run sans changer de projet actif.

## Contexte

`AgentPanel/` montre un run à la fois, celui du projet actif, et seulement
dans l'onglet qui l'a lancé. Le parallélisme réel de Tessera est **entre
projets** (ADR-038) : c'est exactement ce que l'UI ne montre pas.

ticket-128 pose le canal ; ce ticket l'affiche. Les briques existent :
`TokenStream`, `AgentBlock`, `VerdictBanner`, `AgentDialogue`, `RoundBadge`
sont réutilisés tels quels.

## Solution proposée

**`useSupervision`** — un seul WebSocket, monté une fois dans `App`, diffusé
par un Context React. Il gère l'instantané initial, l'abonnement et le
désabonnement au changement de sélection, et la reconnexion avec renvoi de
l'abonnement courant. Il remplace `useOrchestratorStream`.

Un Context natif n'est ni Zustand ni Jotai : ADR-013 n'est pas enfreint, et
l'alternative — un socket par composant — ouvrirait N connexions pour une
source unique.

**Badge** — une pastille sur une destination « Supervision » du `NavRail` :
`blue` quand n runs tournent, `amber` dès qu'un agent attend une réponse,
`red` si un run est bloqué, rien quand tout dort. Le nombre est celui des
**runs**, pas des agents : un pipeline est séquentiel, il n'y a jamais deux
agents simultanés dans un même run.

**Vue Supervision** — vue centrale, deux colonnes.

- Gauche : une carte par run actif — projet, mode, ticket, étape et agent
  courants, chrono depuis le début, tokens, coût, tour de revue. La carte
  sélectionnée porte une **barre** violette, jamais de texte coloré (ADR-026).
- Droite : le run sélectionné — flux de tokens, outils appelés, verdict, et
  de quoi répondre, interjeter ou arrêter.

**État vide** : la vue dit qu'aucun run ne tourne et renvoie vers le Kanban.

**`AgentPanel`** garde son rôle dans la colonne de droite, mais consomme le
canal partagé filtré sur le projet actif.

## Critères d'acceptation

- [ ] Une destination « Supervision » existe dans `NavRail` et ouvre la vue
- [ ] Un test vérifie que le badge affiche le nombre de runs actifs, et rien
      quand il n'y en a aucun
- [ ] Un test vérifie les trois couleurs du badge : activité, attente de
      réponse, run bloqué
- [ ] Un test vérifie que la colonne gauche liste un run par projet actif
      quand deux projets tournent
- [ ] Un test vérifie que sélectionner un run émet `subscribe` avec son
      `run_id`, et que changer de sélection émet `unsubscribe` sur le premier
- [ ] Un test vérifie que la vue sans run actif affiche l'état vide
- [ ] Un test vérifie que `useSupervision` renvoie son abonnement courant
      après une reconnexion
- [ ] `useOrchestratorStream` n'existe plus
- [ ] `design/coherence.test.ts` et `design/identite.test.ts` passent sans
      modification
- [ ] Aucun fichier ajouté ne dépasse 200 lignes
- [ ] `npm run build`, `npm run test` et `npx tsc --noEmit` passent
- [ ] `npm run lint` ne signale aucune erreur nouvelle

## Dépendances

ticket-128.

## Estimation

2 jours.

## Risques

ADR-026 est verrouillé par un test : une couleur hors des cinq familles
d'état, ou un accent d'identité posé sur du texte au lieu d'une barre, fait
échouer la CI. Le chrono qui tourne est un `setInterval` dans un composant —
c'est le motif exact des 16 erreurs `react-hooks/set-state-in-effect`
corrigées par ticket-123, à ne pas réintroduire.
