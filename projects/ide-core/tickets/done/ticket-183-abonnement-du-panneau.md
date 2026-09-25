---
id: ticket-183
title: "Un panneau qui montre un run ne s'abonne jamais à son texte"
type: fix
status: done
pr_number: 44
priority: high
agent: codeur
depends_on: ["ticket-182"]
estimated_days: 1
created: 2026-09-25
---

## Le problème

Après un rechargement, le panneau Agents affiche les blocs du run en cours
(ticket-182) mais rien ne s'y écrit : l'agent semble figé.

ADR-041 sépare volontairement deux flux. Les **transitions** partent à tous les
observateurs ; le **texte** ne part qu'aux clients abonnés à ce run précis —
« tout reste disponible ; on ne paie que ce qu'on regarde ». Côté client,
l'abonnement n'est envoyé que par `selectionner()`, appelé au lancement d'un
run ou sur un clic dans Supervision. Une page rechargée n'appelle ni l'un ni
l'autre : elle reçoit l'instantané, puis plus une ligne.

## La cause de fond

Le serveur tient un **ensemble** d'abonnements par socket. Le client le réduit
à une seule valeur, `abonnementRef`, que deux consommateurs se disputent : le
panneau du projet actif, et la sélection de l'onglet Supervision. Un seul slot
pour deux besoins — celui qui ne parle pas perd son texte.

## Ce qu'il faut faire

- Deux slots nommés côté client — `selection` et `panneau` — et l'ensemble
  voulu s'en déduit. Un run demandé par les deux ne s'abonne qu'une fois, et
  ne se désabonne que lorsque plus personne ne le regarde.
- `useRunActif` déclare le run qu'il affiche dès qu'il en connaît un, y
  compris quand il vient de l'instantané.
- À la reconnexion, tout l'ensemble se redemande : le serveur repart d'une
  socket vierge.

## Ce que ça ne fait pas

Le texte déjà émis avant l'arrivée de l'observateur n'est pas rejoué : ADR-041
jette ce qu'aucun client ne regardait. Un observateur tardif voit l'agent
travailler à partir de son arrivée, pas depuis le début du tour.
