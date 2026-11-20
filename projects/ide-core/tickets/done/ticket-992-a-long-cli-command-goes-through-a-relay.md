---
agent: codeur
depends_on:
- ticket-946
id: ticket-992
preuve_reelle: true
priority: high
status: done
title: A CLI command still too long for the agent account goes through a relay
type: fix
---

## Contexte

Troisième preuve réelle du 17/11 (Serpent ticket-009, run `5039a3f8`) :
`securite: BLOCK — Audit sécurité indisponible : ligne de commande de 1051
caractères, au plus 1024`.

Le ticket-946 déporte dans des fichiers les valeurs longues des options qui
savent lire un fichier (prompt système, MCP, réglages). `--json-schema`, que
le SDK ajoute pour la sortie validée de l'audit, du reviewer et du validateur
(ADR-061), n'accepte que du JSON en ligne (vérifié sur le CLI 2.1.321 : un
chemin est refusé, « not valid JSON ») : 660 caractères une fois échappé pour
l'audit, 555 pour le reviewer. Compacter le JSON n'en ôte qu'une cinquantaine.
Le codeur, sans schéma, restait sous la limite : la preuve du 946 ne pouvait
pas le voir.

## Ce qu'il faut faire

- `providers/relais_cli.py` : quand la ligne dépasse encore 1 024 caractères
  après le déport, la commande complète est écrite en JSON dans le dossier
  d'appel, avec un script `relais.js`, et le compte lance
  `node relais.js relais.json`. Le relais relance la commande sans shell
  (`spawn`, limite de 32 767 caractères), entrées et sorties héritées, et rend
  son code de sortie. Le processus relayé hérite du job de l'appel (943).
- node vient du `PATH` du compte (ADR-086) ; absent : `ProviderIndisponible`.
- Une commande sous la limite ne change pas.

## Critères d'acceptation

- [x] Test : une commande courte est rendue telle quelle, sans fichier.
- [x] Test : une commande longue devient `node relais.js relais.json`, sous
      la limite, et `relais.json` porte la commande entière.
- [x] Test : sans node sur le `PATH` du compte, refus.
- [x] Test : le relais transmet un argument de 3 000 caractères, l'entrée,
      la sortie et le code de sortie.
- [x] Test : la commande réaliste de l'audit, avec son schéma, passe par le
      relais et tient sous la limite.

## Preuve réelle

Après merge et redémarrage : l'audit de Serpent ticket-009 sous
`tessera-agent` rend un verdict au lieu de « ligne de commande de 1051
caractères ».

## Ce que ça ne fait pas

- Ne passe pas la commande de test d'un projet par le relais : elle tient
  sous la limite (ADR-085) et `lancer_sous_compte` refuse toujours au-delà.
- Ne raccourcit pas les schémas de verdict.
