---
agent: codeur
created: 2026-10-05
depends_on: []
estimated_days: 0.5
id: ticket-358
pr_number: 282
priority: high
status: done
title: An agent's question survives the text replay, and a transmitted answer is acknowledged
type: fix
---

# ticket-358 — La question d'un agent ne disparaît plus, et la réponse se voit partir

## Objectif

Que la question d'un agent reste affichée tant qu'elle attend, et que
l'utilisateur voie que sa réponse est arrivée.

## Contexte

Deux symptômes signalés, une seule famille de cause, entièrement dans le
frontend. Le backend transmet bien la réponse : `observation.py` appelle
`dialogue.answer()`, qui résout la question en attente, puis publie
`answer_ack` avec `outcome: "transmitted"`.

**1. La question disparaît au clic sur la carte.**
`frontend/src/hooks/streamState.ts`, branche `agent_token` / `agent_tool_use` :
tout événement de texte remet `pendingQuestion`, `questionExpireA` et
`answerAck` à `null`. Or un clic sur la carte dans Supervision appelle
`selectionner`, qui abonne la socket au run, et l'abonnement **rejoue le
journal du texte** (`JOURNAL_DU_TEXTE.relire`, ticket-185) — donc les tokens
écrits **avant** la question. Le rejeu efface une question toujours en
attente.

**2. La réponse semble ne jamais partir.**
Dans la branche `answer_ack` de `streamState.ts`, `"transmitted"` ne retire
pas la question ; dans `frontend/src/components/AgentPanel/AgentDialogue.tsx`,
seul `"deposited"` affiche un message. Une réponse transmise laisse donc la
question, le champ et le bouton exactement comme avant : rien ne dit qu'elle
est partie. Et la question ne s'efface ensuite qu'au premier token de l'agent
— qui n'arrive jamais au panneau tant que la socket n'est pas abonnée au
texte du run.

## Solution proposée

Dans `streamState.ts` :

1. `agent_token` et `agent_tool_use` ne touchent plus à `pendingQuestion`,
   `questionExpireA` ni `answerAck`.
2. `answer_ack` avec `outcome: "transmitted"` met `pendingQuestion` et
   `questionExpireA` à `null`, et garde `answerAck: "transmitted"`. Il part à
   tous les observateurs : une réponse donnée depuis un autre onglet retire
   aussi la question ici.
3. `agent_done` met `pendingQuestion` et `questionExpireA` à `null` : l'agent
   qui avait demandé a fini, sa question n'attend plus rien.

Une question expirée sans réponse reste affichée comme aujourd'hui
(« Question expirée… »), jusqu'au `agent_done` de l'agent.

Dans `AgentDialogue.tsx` : quand `answerAck === "transmitted"`, afficher
« Réponse transmise à l'agent. » à l'endroit du message `deposited`, en
`zinc` (ADR-026).

Le backend ne change pas.

## Critères d'acceptation

- [ ] Un test de `frontend/src/hooks/streamState.test.ts` (ou d'un fichier de
      test voisin) montre qu'après `agent_question` puis un `agent_token`,
      `pendingQuestion` vaut toujours la question
- [ ] Un test montre la même chose pour `agent_tool_use`
- [ ] Un test montre qu'`answer_ack` avec `outcome: "transmitted"` met
      `pendingQuestion` à `null` et `answerAck` à `"transmitted"`
- [ ] Un test montre qu'`answer_ack` avec `outcome: "deposited"` ne retire
      pas une question en attente
- [ ] Un test montre qu'`agent_done` met `pendingQuestion` à `null`
- [ ] Un test de `AgentDialogue.test.tsx` montre que « Réponse transmise à
      l'agent. » s'affiche quand `answerAck` vaut `"transmitted"`
- [ ] Aucun fichier sous `backend/` n'est modifié

## Ce que ça ne fait pas

- Ne change pas le délai d'ADR-025 ni le comportement de l'agent sans
  réponse.
- N'ajoute pas d'historique des questions posées : seule la question en
  attente s'affiche.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

- Un test existant qui attend l'effacement de la question sur un token
  devient faux : il faut le réécrire, il décrivait précisément le défaut.