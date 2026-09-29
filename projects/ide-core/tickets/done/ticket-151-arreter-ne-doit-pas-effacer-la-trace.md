---
id: ticket-151
title: "Arrêter un service ne doit pas effacer sa trace, et l'IDE doit se reconnaître"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-150"]
estimated_days: 1
created: 2026-09-23
---

# ticket-151 — Ce qu'arrêter efface, et l'IDE qui s'ignore

## Objectif

Qu'un service arrêté garde son histoire — pid, code de sortie, dernières
lignes — et que l'IDE cesse de dire « pas lancé par l'IDE » des serveurs qui
le font tourner.

## Contexte

**Deux constats d'usage, le premier étant un bug.**

`ProcessRegistry.arreter()` fait `self._services.pop(project_id, [])` : il
**efface** les entrées au lieu de les marquer arrêtées. Dès qu'on clique
« Arrêter », toute trace disparaît — pid, code de sortie, sortie conservée.
`GET /services` reconstruit alors le service déclaré de zéro, sans `pid`, et
l'écran affiche « pas lancé par l'IDE ».

C'est exactement la distinction que ticket-149 avait introduite — « jamais
lancé » contre « arrêté » — détruite par le backend, qui supprime ce dont
l'affichage a besoin pour la faire.

ticket-144 avait pourtant établi qu'un service mort **reste visible**. La
règle valait pour un service qui meurt seul, pas pour un service arrêté : les
deux chemins devraient garder la trace, et un seul le fait.

**Second constat.** `ide-core` affiche « pas lancé par l'IDE » pour son
backend et son frontend — ce qui est exact, l'IDE ne les a pas démarrés, et
absurde, puisque ce sont eux qui le font vivre. On ne lancera jamais l'IDE
depuis l'IDE ; on pourrait en revanche voir ses logs, et l'arrêter.

## Solution proposée

**`arreter()` conserve les entrées.** Il termine les processus et laisse les
`Service` en place, avec leur pid, leur code de sortie et leur sortie. Un
`start` suivant purge l'entrée du même nom, comme aujourd'hui (ticket-144),
donc rien ne s'accumule.

**L'IDE se reconnaît.** Un service déclaré dont le port répond, alors que le
registre l'ignore, s'affiche « tourne hors de l'IDE » plutôt que « pas lancé
par l'IDE ». C'est vrai du projet bootstrap comme d'un service qu'on a
démarré à la main dans un terminal.

Afficher les logs d'un processus qu'on n'a pas lancé demande de lire ailleurs
que sur son tube, et **sort du périmètre** : à consigner si le besoin se
confirme. L'arrêter demande de tuer un processus que l'IDE n'a pas créé, ce
qui est une décision d'un autre ordre — également hors périmètre ici.

## Critères d'acceptation

- [ ] Un test vérifie qu'après `arreter()`, le service reste listé avec son
      pid, son code de sortie et sa sortie conservée
- [ ] Un test vérifie qu'un `start` après un `stop` ne laisse qu'une entrée
- [ ] Un test vérifie qu'un service jamais lancé reste distinct d'un service
      arrêté
- [ ] Un test vérifie qu'un service déclaré dont le port répond n'est pas
      annoncé comme « pas lancé »
- [ ] `uv run pytest`, `uv run mypy src/`, `npm run typecheck`,
      `npm run lint`, `npm run test` et `npm run build` passent
- [ ] Vérifié en vrai : lancer `fluentdb`, l'arrêter, voir « à l'arrêt » et
      non « pas lancé par l'IDE »

## Dépendances

ticket-150.

## Estimation

1 jour.

## Risques

Détecter qu'un port répond n'est pas détecter que *ce* service tourne : un
autre programme peut l'occuper. Le libellé doit donc rester prudent — « tourne
hors de l'IDE » dit ce qu'on observe, pas ce qu'on suppose.
