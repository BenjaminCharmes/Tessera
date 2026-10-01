---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 0.5
id: ticket-254
pr_number: 131
priority: low
status: done
title: Chat send button sits beside the input instead of on its own row
type: feat
---

# ticket-254 — Le bouton d'envoi du chat passe à côté de la zone de saisie

## Objectif

Rendre de la hauteur au fil de la conversation en plaçant le bouton d'envoi sur
la même ligne que la zone de saisie.

## Contexte

Le formulaire de `components/ChatPanel/index.tsx` empile une `textarea` de deux
lignes puis une rangée entière (`mt-1.5 flex justify-end`) pour le seul bouton
« Envoyer ». Entrée envoie déjà : la rangée coûte une trentaine de pixels pour
un bouton secondaire.

Au passage, le bouton de bascule tableau / éditeur de
`components/Sidebar/TicketList.tsx` n'a qu'un `title`, sans `aria-label`,
contrairement à ses voisins de la même barre.

## Solution proposée

- Le formulaire devient une ligne : `textarea` qui prend la largeur restante,
  bouton-icône à droite, aligné en bas de la zone de saisie.
- Ajouter `IconSend` dans `design/icons.tsx` (grille de 24, trait 1.5, comme
  les autres — le test de cohérence interdit tout `<svg>` hors de `design/`).
- Le bouton porte `aria-label="Envoyer"` et `title="Envoyer (Entrée)"`. Pendant
  la réflexion de l'agent, il reste désactivé et son libellé accessible devient
  « Envoi en cours ».
- Entrée envoie toujours, Maj+Entrée fait un saut de ligne : comportement
  inchangé.
- Dans `TicketList.tsx`, ajouter au bouton de bascule un `aria-label` identique
  à son `title`.

## Critères d'acceptation

- [ ] `design/icons.tsx` exporte `IconSend`.
- [ ] Le bouton d'envoi du chat est un frère de la `textarea` dans un même
      conteneur flex, et la rangée `mt-1.5 flex justify-end` a disparu.
- [ ] Le bouton d'envoi est trouvable par `getByRole("button", { name: "Envoyer" })`
      et soumet le message au clic (test dans `ChatPanel`).
- [ ] Appuyer sur Entrée dans la `textarea` envoie toujours le message (test
      existant ou nouveau).
- [ ] Le bouton de bascule de `TicketList` est trouvable par
      `getByRole("button", { name: "Vue tableau" })` (test).

## Dépendances

Aucune.

## Estimation

Une demi-journée. Frontend uniquement.

## Risques

- Les tests existants qui cherchent le texte « Envoyer » ou « … » dans le bouton
  sont à adapter au libellé accessible.
- `AgentDialogue.tsx` a aussi un bouton « Envoyer » : hors périmètre, ne pas y
  toucher.