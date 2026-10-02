---
agent: architect
created: 2026-10-02
depends_on: []
estimated_days: 1
id: ticket-310
pr_number: 203
priority: high
status: done
title: 'Design: audit the ADRs and draft the short constraints file agents will read
  instead'
type: design
---

# ticket-310 — Audit des ADR, et brouillon des contraintes en vigueur

## Objectif

Séparer, dans `memory/decisions.md`, ce qui est une **règle en vigueur** de ce
qui est l'**histoire** d'une décision, et rédiger le fichier court que les
agents liront à la place du journal complet. Ce ticket ne branche rien :
c'est le ticket-311.

## Contexte

`memory/decisions.md` compte 50 ADR (43 Ko). Il part dans chaque appel
d'agent, réduit par portée (ADR-032). Mesuré le 2026-10-02 :

| Rôle | ADR reçus | Taille |
|---|---|---|
| architect | 48 | ~9 900 tokens |
| codeur | 39 | ~8 600 tokens |
| reviewer | 37 | ~8 300 tokens |
| securite, validateur, doc | 28 | ~6 700 tokens |

Pour jusqu'à 18 appels par ticket, le coût compte, mais la dilution compte
davantage : un codeur reçoit 39 décisions, dont une bonne part racontent
pourquoi un choix a été fait (Tauri plutôt qu'Electron, renommage d'une
clef…), quand il n'a besoin que de ce qu'il doit respecter. Certaines sont
devenues sans objet (ADR-016, remplacé par ADR-040). D'autres ont été
amendées plusieurs fois en place. Les règles de design (ADR-026, ADR-047)
ont pourtant été régulièrement ignorées : une règle noyée se lit mal.

## Livrables

1. `memory/adr-audit.md` : un tableau avec une ligne par ADR (001 à 051).
   Colonnes : numéro, titre, classement, et justification en une phrase.
   Le classement prend une de ces valeurs :
   - **règle** : une contrainte qu'un agent doit respecter aujourd'hui ;
   - **histoire** : un choix passé, qui ne contraint plus le comportement ;
   - **obsolète** : remplacé ou sans objet, avec l'ADR qui le remplace ;
   - **fusion** : sa règle rejoint celle d'un autre ADR, nommé.
2. `memory/contraintes.md` : le brouillon des règles en vigueur.
   - Regroupées par thème (par exemple : git et périmètre d'écriture,
     livraison et autonomie, portes qui échouent fermées, confidentialité,
     interface et design, langue).
   - Chaque règle tient en une ou deux phrases à l'impératif, et finit par
     son ou ses numéros d'ADR entre parenthèses, par exemple `(ADR-027)`.
   - Une règle qui ne vaut que pour certains rôles l'indique, sur le modèle
     de la `**Portée**` d'ADR-032.
3. Un ADR-052, ajouté à la fin de `memory/decisions.md`, qui enregistre la
   séparation entre journal et contraintes, dans le budget du skill
   `write-adr`.

## Critères d'acceptation

- [ ] `memory/adr-audit.md` contient exactement une ligne par ADR de
      `decisions.md`, de 001 à 051, chacune classée avec l'une des quatre
      valeurs
- [ ] Chaque ADR classé « règle » ou « fusion » qui ne porte pas de
      `**Portée**` dans `decisions.md` est cité, par son numéro, dans au
      moins une règle de `memory/contraintes.md`
- [ ] Aucune règle de `memory/contraintes.md` ne cite un ADR classé
      « histoire » ou « obsolète »
- [ ] `memory/contraintes.md` fait moins de 12 000 caractères
- [ ] `memory/decisions.md` garde tous ses ADR existants, sans en modifier
      le texte, et gagne un ADR-052
- [ ] Aucun fichier sous `backend/` ou `frontend/` n'est modifié

## Ce que ça ne fait pas

Rien ne change pour les agents tant que le ticket-311 n'est pas livré.
`decisions.md` reste le journal complet, qu'on ne raccourcit pas : c'est
l'histoire, et c'est là qu'on comprend pourquoi.

## Risques

Reformuler une règle peut en changer le sens. Chaque règle de
`contraintes.md` doit pouvoir se relire à côté de son ADR, d'où le renvoi
obligatoire.