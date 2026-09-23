---
id: ticket-148
title: "L'arrêt ne doit pas effacer le bouton, et la sortie d'un service doit survivre"
type: fix
status: done
pr_number: 167
priority: high
agent: codeur
depends_on: ["ticket-147"]
estimated_days: 1
created: 2026-09-23
---

# ticket-148 — L'arrêt, et la sortie qu'on perd

## Objectif

Qu'arrêter un service ne fasse pas croire que le projet n'en déclare aucun, et
qu'ouvrir le panneau montre ce que le service a écrit — y compris son adresse,
écrite avant qu'on regarde.

## Contexte

Deux défauts signalés en usage réel, tous deux introduits par les tickets
précédents.

**Arrêter efface le bouton.** `arreter()` pose `liste: AUCUN` juste après le
`stop`, et depuis ticket-146 `declare` vaut `services.length > 0`. Une liste
vide *parce qu'on vient d'arrêter* se lit donc comme « ce projet ne déclare
aucun service » : le bouton disparaît et le panneau affiche le mode d'emploi.
Il faut cliquer deux fois pour arrêter, la relecture ramenant la liste entre
les deux.

La confusion est nette : **« rien de déclaré » et « rien qui tourne » sont
deux choses différentes**, et le code les a mélangées.

**La sortie disparaît.** Le panneau affiche « Ce service n'a encore rien
écrit » alors que le service tourne. `EventHub` ne rejoue pas l'historique —
décision assumée pour la supervision, qui observe le présent et dont les runs
se relisent en base. Mais un service écrit ses lignes utiles, **dont son
adresse**, dans ses deux premières secondes. Qui n'écoutait pas à cet instant
ne les verra jamais, et l'adresse est perdue jusqu'au prochain redémarrage.

## Solution proposée

**`declare` vient de la déclaration, pas de la liste courante.** Le backend
sait quels services sont déclarés : `GET /services` les rend déjà tous
(ticket-146). Il suffit de ne plus vider la liste côté client — `arreter()`
relit au lieu de poser un état vide. Un service arrêté reste listé, au repos,
et le bouton propose « Lancer ».

**Le service garde ses dernières lignes.** `Service` conserve une fenêtre
bornée (les mêmes 200 lignes que le client), alimentée par la lecture qui
tourne déjà. `GET /services` les rend, et le panneau les affiche sans
dépendre d'avoir écouté au bon moment. Le canal continue de servir le direct ;
la mémoire sert le rattrapage.

L'adresse se déduit alors de cette fenêtre, donc elle survit à un
rechargement de l'IDE.

## Critères d'acceptation

- [ ] Un test vérifie qu'après `arreter()`, `declare` reste vrai et le bouton
      propose « Lancer »
- [ ] Un test vérifie qu'un seul clic sur « Arrêter » suffit
- [ ] Un test backend vérifie que `GET /services` rend les dernières lignes
      d'un service qui a écrit
- [ ] Un test backend vérifie que cette fenêtre est bornée et garde les plus
      récentes
- [ ] Un test vérifie que le panneau affiche la sortie d'un service lancé
      avant l'ouverture de l'app
- [ ] Un test vérifie que l'adresse est retrouvée depuis cette sortie
      conservée
- [ ] `uv run pytest`, `uv run mypy src/`, `npm run typecheck`,
      `npm run lint`, `npm run test` et `npm run build` passent
- [ ] Vérifié en vrai : lancer `fluentdb`, recharger l'IDE, voir la sortie et
      l'adresse ; arrêter en un clic

## Dépendances

ticket-147.

## Estimation

1 jour.

## Risques

Garder la sortie en mémoire fait grossir le registre : la borne est ce qui
l'empêche. Elle vaut par service, et un service qui écrit beaucoup n'en garde
pas plus qu'un autre.
