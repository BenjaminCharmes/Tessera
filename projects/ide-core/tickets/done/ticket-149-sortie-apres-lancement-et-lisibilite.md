---
id: ticket-149
title: "La sortie doit apparaître après le lancement, et on doit savoir à qui elle est"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-148"]
estimated_days: 1
created: 2026-09-23
---

# ticket-149 — La sortie après le clic, et à qui elle appartient

## Objectif

Qu'après avoir cliqué « Lancer », les lignes du service apparaissent sans
intervention, et qu'on sache dans la Supervision quelle sortie appartient à
quel service.

## Contexte

**Trois observations d'usage, toutes vérifiées.**

**La sortie n'apparaît pas.** L'API rend pourtant 28 lignes pour
`fluentdb/dev`, sortie conservée comprise. Le défaut est côté client :
`demarrer()` **fige** la liste avec ce que `start` a renvoyé, c'est-à-dire
l'état à la milliseconde du démarrage — où rien n'a encore été écrit. Cette
liste figée n'est remplacée que si un événement du canal fait changer
`signal`. Sans ce signal, `sortie: []` reste affiché indéfiniment.

C'est exactement l'erreur corrigée pour `arreter()` dans ticket-148, laissée
en place pour `demarrer()` : **croire savoir l'état après une action, quand
seul le serveur le sait.**

**On ne sait pas à qui est la sortie.** Dans la Supervision, deux services
dépliés donnent deux blocs sans titre visible. Le libellé accessible existe,
mais rien ne le montre à l'œil.

**`ide-core` s'affiche « à l'arrêt » alors que l'IDE tourne.** Ce n'est pas un
défaut : les serveurs qui font tourner l'IDE ont été lancés à la main, et le
registre ne connaît que les processus qu'il a démarrés. Le mot est exact côté
registre et trompeur côté lecteur.

## Solution proposée

**`demarrer()` ne fige plus rien.** Comme `arreter()`, il déclenche une
relecture. La réponse de `start` sert à savoir que le lancement a réussi, pas
à remplacer la liste.

**Une relecture périodique tant qu'un service tourne**, en plus du canal.
ticket-145 avait écarté le minuteur au profit des événements, et l'argument
tenait — mais il fait dépendre l'affichage d'un canal dont on ne peut pas
prouver le bon fonctionnement depuis un test. Le minuteur ne tourne que
lorsqu'un service est en cours, donc il ne bat pas dans le vide. Le canal
reste la voie rapide.

**Chaque bloc de sortie porte le nom de son service**, visiblement.

**Le mot « à l'arrêt » devient « pas lancé par l'IDE »** quand aucun `pid`
n'a jamais existé — ce qui distingue « je l'ai arrêté » de « je ne l'ai
jamais démarré ».

## Critères d'acceptation

- [ ] Un test vérifie qu'après `demarrer()`, une relecture a lieu et que la
      liste affichée vient du serveur, pas de la réponse de `start`
- [ ] Un test vérifie qu'une relecture périodique a lieu tant qu'un service
      tourne, et **aucune** quand rien ne tourne
- [ ] Un test vérifie que chaque bloc de sortie affiche le nom de son service
- [ ] Un test vérifie qu'un service jamais lancé se distingue d'un service
      arrêté
- [ ] `npm run typecheck`, `npm run lint`, `npm run test` et `npm run build`
      passent
- [ ] Vérifié en vrai : lancer `fluentdb`, voir ses lignes arriver sans rien
      faire, et son adresse devenir cliquable

## Dépendances

ticket-148.

## Estimation

1 jour.

## Risques

Un minuteur mal borné fait battre l'interface pour rien. Celui-ci ne tourne
que lorsqu'un service est en cours, et son intervalle doit rester assez long
pour qu'une relecture coûte moins qu'elle n'apporte.
