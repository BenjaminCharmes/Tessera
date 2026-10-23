---
id: ticket-566
title: "The office to-you column and the sound alert"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-554", "ticket-562"]
estimated_days: 1.5
created: 2026-10-23
---

# ticket-566 — La colonne « À toi » et l'alerte sonore

## Objectif
Rassembler dans une colonne ce qui attend une action de Benjamin : les
questions d'agent (avec leur compte à rebours), les agents figés, les PR à
relire. Et sonner quand une question arrive.

## Contexte
Conception : `docs/superpowers/specs/2026-10-23-vue-bureau-design.md`,
lignes « Colonne À toi » et « Alerte sonore », et « Ce qui reste à confirmer ».
Maquette : `design/maquette/Bureau.dc.html`. `agent_question` porte
`expire_a` ; passé le délai, l'agent choisit seul (ADR-025). La réponse passe
par `supervision.envoyer(runId, { type: "answer" })`. Le ticket-554 possède le
réglage « Son » de l'événement « question ».

## Solution proposée
- `ColonneAToi.tsx` : trois groupes — questions (`pendingQuestion`, compte à
  rebours depuis `expire_a`, champ de réponse), figés (`santeAgent` =
  `blocage_suspecte`), PR à relire (`livraison_done` avec `conflits`, ADR-033).
  Le bouton « Laisser l'agent choisir » de la maquette n'est pas dessiné : le
  canal n'a pas ce message.
- `useAlerteSonore` : joue le son quand `pendingQuestion` passe de `null` à une
  valeur, **si** le réglage « Son » de la question (ticket-554) est actif. Le
  bouton du Bureau est un second interrupteur sur ce même réglage, pas un
  second réglage.

## Critères d'acceptation
- [ ] Une question en attente apparaît dans la colonne avec un compte à rebours dérivé de `expire_a`, et un test le vérifie avec une horloge simulée
- [ ] Envoyer une réponse appelle `envoyer(runId, { type: "answer" })` avec le texte saisi, et un test le vérifie
- [ ] Aucun bouton « Laisser l'agent choisir » n'est rendu, et un test le vérifie
- [ ] Un run « figé ? » apparaît dans le groupe des figés, et un test le vérifie
- [ ] Une PR à relire (conflit résolu) apparaît avec son numéro, et un test le vérifie
- [ ] Le son se joue au passage de `pendingQuestion` de `null` à une valeur, et pas à un rechargement qui la trouve déjà posée, et un test le vérifie
- [ ] Le son ne se joue pas quand le réglage du ticket-554 est coupé, et basculer le bouton du Bureau modifie ce réglage, sans en créer un second, et un test le vérifie
- [ ] Aucun fichier du diff ne dépasse 300 lignes, et le diff ne modifie aucun fichier de `backend/`
- [ ] `npm run test`, `tsc` et `eslint` passent

## Ce que ça ne fait pas
- Ne crée pas le réglage « Son » : il appartient au ticket-554.
- Ne notifie rien hors de la vue : les notifications de bureau sont dans les tickets 552 à 556.
- Ne répond pas à la place de l'agent à l'échéance (ADR-025).
