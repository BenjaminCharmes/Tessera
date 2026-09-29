---
id: ticket-145
title: "Rendre les services lisibles : état à jour, sortie visible, adresse cliquable"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-144"]
estimated_days: 1
created: 2026-09-23
---

# ticket-145 — Rendre les services lisibles à l'écran

## Objectif

Qu'après avoir cliqué « Lancer », on sache que ça a marché, où le serveur
écoute, et qu'on puisse l'arrêter.

## Contexte

Trois manques relevés au premier usage réel, tous à l'écran — le backend, lui,
fait ce qu'il faut depuis ticket-144.

**Le bouton ne ressemble pas à ses voisins.** « VSCode » et « Git » portent
`border border-zinc-700 px-2 py-1 text-mini` ; « Lancer » porte
`px-2 py-0.5 text-micro` sans bordure. Il est plus petit et plus plat, dans
une rangée où l'alignement est ce qui se voit en premier.

**L'état ne se met jamais à jour.** `useServices` lit la liste au montage et
après une action, et rien d'autre. Un service qui meurt trois secondes après
le clic reste affiché « en cours » indéfiniment, et le bouton continue de
proposer « Arrêter » pour un processus qui n'existe plus — ou l'inverse.

**La sortie n'est affichée nulle part.** ticket-137 la publie pourtant sur le
canal, en `service_output`. Conséquence directe : Vite annonce son adresse
dans cette sortie — `Local: http://localhost:5174/` — et l'information se
perd. On lance un serveur sans savoir où il écoute.

## Solution proposée

**Le bouton** reprend exactement les classes de ses voisins, en gardant ses
couleurs d'état (ADR-026 : `blue` en cours, `red` en échec, `zinc` au repos).
Pas de violet : il réservé à l'identité, et un bouton qui change d'état
n'en est pas.

**L'état se rafraîchit** tant qu'un service tourne. Deux façons, à trancher à
l'implémentation : relire périodiquement, ou écouter le canal d'observation —
un service qui meurt pourrait émettre sa fin, ce que le backend ne fait pas
encore. La seconde est plus juste et demande un événement de plus.

**La sortie s'affiche** dans la Supervision, sous la bande des services :
sélectionner un service montre ses dernières lignes, comme sélectionner un run
montre ses tokens. Elle est déjà soumise à l'abonnement (ADR-041), donc rien
de neuf côté canal.

**L'adresse devient cliquable.** La première URL `http://localhost:…` ou
`http://127.0.0.1:…` trouvée dans la sortie d'un service est retenue et
affichée à côté de son nom. Repérer une URL dans un flux est une heuristique,
donc elle ne remplace rien : la sortie reste lisible en entier.

## Critères d'acceptation

- [ ] Un test vérifie que le bouton porte les mêmes classes de taille et de
      bordure que « VSCode » et « Git »
- [ ] Un test vérifie que le bouton affiche « Arrêter » quand un service
      tourne, et « Lancer » quand la liste est vide
- [ ] Un test vérifie que l'état d'un service passe à « arrêté » sans action
      de l'utilisateur quand le processus meurt
- [ ] Un test vérifie que la sortie d'un service sélectionné s'affiche
- [ ] Un test vérifie qu'une URL trouvée dans la sortie devient un lien
- [ ] Un test vérifie qu'une sortie sans URL n'affiche aucun lien mort
- [ ] `npm run typecheck`, `npm run lint`, `npm run test` et `npm run build`
      passent
- [ ] Vérifié en lançant réellement `ide-core` : l'adresse de Vite est
      cliquable, le `backend` en échec se voit, et « Arrêter » fonctionne

## Dépendances

ticket-144.

## Estimation

1 jour.

## Risques

Un rafraîchissement périodique trop court fait battre l'interface pour rien ;
trop long, il ne sert à rien. Si le choix se porte sur le canal plutôt que sur
un intervalle, la question disparaît — mais il faut alors que le backend
annonce la fin d'un service, ce qu'il ne fait pas aujourd'hui.

## Comment ce ticket a été livré

Sa PR (#164) a été **close, pas fusionnée**. Les tickets 147 à 151 ont touché
les mêmes fichiers et ont réimplémenté l'état, la sortie et l'adresse des
services en allant plus loin — `design/etatDuService.ts`, la distinction
« arrêté à la main » et la capture de l'URL sans codes ANSI n'existaient pas
ici. La branche était restée en arrière : la fusionner aurait retiré 942
lignes de `develop`.

Le travail est livré, la PR ne l'est pas. Les deux se disent.
