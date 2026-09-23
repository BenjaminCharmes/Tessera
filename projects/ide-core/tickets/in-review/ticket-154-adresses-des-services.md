---
id: ticket-154
title: "L'adresse d'un service : toutes celles qu'il annonce, et aucune qui n'en soit pas une"
type: fix
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-153"]
estimated_days: 1
created: 2026-09-23
---

# ticket-154 — L'adresse d'un service, et la place que prend le projet bootstrap

## Objectif

Qu'un service lancé depuis l'IDE affiche des liens qui s'ouvrent, un par
adresse réellement annoncée — et que le message du projet bootstrap tienne
sur une ligne.

## Contexte

`fluentdb` affiche `http://localhost:5173"}` et le clic tombe sur
`about:blank#blocked`. Sa dernière ligne de sortie est un log JSON :

```
[server] {…,"msg":"Web UI not built — run `npm run dev:web` and open http://localhost:5173"}
```

Deux défauts se composent :

1. Le motif finit par `\S*`, qui avale le `"}` fermant. L'URL est corrompue,
   donc le navigateur refuse de l'ouvrir.
2. « La dernière l'emporte » choisit une **phrase qui mentionne** un port
   plutôt que l'adresse que Vite annonce trois lignes plus haut
   (`http://localhost:5174/`). Et 5173 est le port de l'IDE lui-même : c'est
   précisément pourquoi Vite a bougé — sa sortie dit
   `Port 5173 is in use, trying another one...`.

Corriger le seul motif ne suffit donc pas : on obtiendrait une URL propre qui
renvoie vers Tessera.

Ce projet lance deux serveurs sous `concurrently`, préfixés `[web]` et
`[server]`. Une seule adresse ne peut pas les représenter tous les deux —
c'est aussi la remarque déjà faite sur l'écran de supervision, où l'on ne
distingue pas le back du front.

Enfin, le message du projet bootstrap occupe quatre lignes dans un panneau
étroit pour dire qu'il n'y a rien à faire.

## Solution proposée

`adresse.ts` rend **toutes** les adresses distinctes, chacune avec son
étiquette — le préfixe `[web]` / `[server]` de la ligne quand il y en a un.

- Le motif exclut guillemets, accolades et chevrons du chemin.
- Une adresse qui pointe vers l'origine de l'IDE est écartée : le service ne
  peut pas écouter sur le port que le frontend de Tessera occupe.
- Par étiquette, la dernière l'emporte — un serveur qui redémarre sur un
  autre port annonce le nouveau, et c'est celui-là qui écoute.

`ServicesLances` affiche un lien par adresse, l'étiquette en légende.

Le bloc bootstrap se réduit à une ligne, le détail passe en `title`.

## Critères d'acceptation

- [ ] Sur la sortie réelle de `fluentdb` reproduite en test,
      `adressesDansLaSortie` rend exactement `http://localhost:5174/` (`web`)
      et `http://127.0.0.1:4983` (`server`)
- [ ] Aucune adresse rendue ne contient `"`, `}` ou `{`
- [ ] Une adresse égale à l'origine de l'IDE est absente du résultat, que
      l'hôte s'écrive `localhost`, `127.0.0.1` ou `[::1]`
- [ ] Un serveur qui redémarre sous la même étiquette ne rend que sa
      dernière adresse
- [ ] Le panneau du projet bootstrap tient en une ligne visible, le détail
      restant lisible au survol
- [ ] `npm run typecheck`, `npm run lint` et `npm run test -- --run` passent

## Dépendances

ticket-153 (l'arbre de processus), déjà en revue.

## Estimation

1 jour.

## Risques

L'écart « origine de l'IDE » se lit dans le navigateur : en test, il est
passé en argument plutôt que lu dans `window`, sinon le test dépend de
l'environnement jsdom.
