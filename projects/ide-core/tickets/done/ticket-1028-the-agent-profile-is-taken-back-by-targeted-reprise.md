---
agent: codeur
depends_on:
- ticket-1027
id: ticket-1028
preuve_reelle: true
priority: medium
status: done
title: The agent profile is taken back by targeted reprise
type: refactor
---

# ticket-1028 — Le profil de l'agent se reprend par reprise ciblée

## Objectif

Appliquer au profil de l'agent la reprise ciblée de l'ADR-091 : la remise au
backend de ce que le compte a créé coûte aujourd'hui 3,9 à 5,6 s par clôture
(mesure du 20/11, profil purgé compris) ; la lecture des propriétaires du profil
(1 697 entrées) ne prend que 0,1 s.

## À faire

**`profil_agent.py`**

- `_reprendre_la_main` : remplace `/setowner /T` et `/reset /T` par
  `reprendre_arbre` (ticket-1027) sur le dossier de profil. Mêmes règles : entrée
  du compte ou à DACL protégée, aucun lien suivi, refus nommant le chemin.
  `npm-cache`, gardé, est parcouru comme le reste : ce que npm y a écrit
  pendant l'appel appartient au compte et revient au backend.
- `_redonner_au_compte` : la racine du profil n'est plus remise à zéro, elle
  garde sa DACL. L'appel ne repose les quatre ACE que si la racine a été reprise
  ou si l'ACE du compte n'y est plus ; le Codeur mesure et retient le test le
  moins coûteux.
- `reinitialiser_profil` : l'ordre reste reprise, purge, recréation ; le
  drapeau `nettoyage_en_echec` (ticket-1014) et `_vider` (ticket-1008) ne changent
  pas.

## Critères d'acceptation

- [ ] `_reprendre_la_main` n'utilise plus `/T` ; un test avec faux
      `SecuriteFichiers` montre qu'une entrée du backend n'est pas reprise et
      qu'un lien n'est pas parcouru.
- [ ] Un test : une entrée illisible lève `DroitsAgentRefuses` et lève le
      drapeau `nettoyage_en_echec`.
- [ ] Un test : sans reprise de la racine, `_redonner_au_compte` ne lance aucun
      `icacls`.
- [ ] La purge garde `npm-cache` et retire encore tout le reste.
- [ ] `pytest` et `mypy` passent.

## Preuve réelle

Sur la machine, sous le compte agent, sur un run de Serpent : noter la durée
de `reinitialiser_profil` à chaque clôture (avant : 3,9 à 5,6 s) et la durée
d'ouverture et de clôture d'un appel entier. Constater qu'un `.npmrc` et un
`.bashrc` écrits par un appel ont disparu à la clôture, que `npm-cache` reste,
et qu'aucune entrée du profil n'appartient au compte une fois reprise.

## Ce que ça ne fait pas

- Ne change ni la purge ni la liste des chemins gardés.
- Ne promet aucune durée : le gain du profil n'a été que mesuré en lecture,
  l'ADR-091 le dit.