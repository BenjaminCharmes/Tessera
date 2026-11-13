---
agent: codeur
created: 2026-11-13
depends_on: []
estimated_days: 0.5
id: ticket-967
pr_number: null
priority: medium
status: done
title: A project service never starts on a port Tessera uses
type: fix
---

# ticket-967 — Un service de projet ne démarre jamais sur un port de Tessera

## Objectif

Qu'une app de projet ne puisse pas occuper l'origine du frontend de Tessera
(`localhost:5173`) ni celle de son backend (`localhost:8100`).

## Contexte

Relevé de cohérence entre projets (13/11) : demineur et serpent déclarent un
service `npm run dev` sans port, donc sur 5173, le port de Tessera. Depuis le
ticket-951, le navigateur peut enregistrer le jeton de session pour l'origine
`localhost:5173` : quand le Vite de Tessera est arrêté, l'app d'un projet sur
ce port reçoit les identifiants que le gestionnaire de mots de passe y
remplit. Les `agents.json` de ces deux projets se corrigent à la main ; il
manque la porte côté Tessera.

## Solution proposée

1. Au lancement d'un service de projet (`routers/services.py` et la reprise
   de `services_reprise.py`), le port déclaré, ou à défaut celui que la
   commande vise (`--port N`, `-p N`, `PORT=N`), est comparé aux ports de
   Tessera : 5173 (et ceux de `auth.py` pour l'origine du frontend) et 8100.
2. Un service `npm run dev` / `vite` sans port explicite compte comme 5173.
3. Un port de Tessera refuse le lancement en **409** avec un message qui nomme
   le port et dit de le déclarer autrement dans `agents.json`.

## Critères d'acceptation

- [ ] Un test : un service déclaré sur 5173 est refusé en 409, le message
      nomme le port.
- [ ] Un test : `npm run dev` sans port est refusé de la même façon.
- [ ] Un test : `npm run dev -- --port 5180` démarre.
- [ ] Un test : 8100 est refusé.
- [ ] Un test : la reprise des services au démarrage ne relance pas un
      service refusé, et le journalise.

## Ce que ça ne fait pas

- Ne corrige pas les `agents.json` des projets : c'est fait à la main.
- Ne change pas le comportement du bandeau du jeton (ticket-951) : c'est un
  arbitrage de Benjamin.