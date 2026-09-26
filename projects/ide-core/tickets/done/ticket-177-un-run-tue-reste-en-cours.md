---
id: ticket-177
title: "Un backend redémarré laisse ses runs « en cours » pour toujours"
type: fix
status: done
pr_number: 68
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-177 — Un run tué survit à son processus

## Objectif

Qu'un run interrompu par l'arrêt du backend se solde, et ne bloque pas la suite.

## Contexte

Le backend a été redémarré pendant qu'une file tournait. Trois conséquences,
toutes observées :

1. **Deux lignes restent ouvertes en base** — le run de file et son ticket
   courant, `finished_at` à `null`, pour toujours. L'historique annonce des
   runs en cours que rien n'exécute.
2. **Le travail du ticket reste non commité.** Le codeur avait écrit
   `partie.ts` (82 lignes) ; l'arbre est resté sale.
3. **La file suivante s'est bloquée aussitôt**, coût 0 : `ensure_clean_tree` a
   refusé, et trois tickets sont passés `blocked` sans qu'un agent tourne.

`RunRegistry` vit en mémoire (ADR-008), donc le redémarrage le vide — la
Supervision est juste. C'est la **base** qui garde les lignes ouvertes, et
l'arbre qui garde le travail.

ADR-037 couvre l'exception levée *pendant* la production : le run finit
`blocked`, le travail est commité, la cause part dans `arret`. Un processus tué
n'exécute aucun `finally` : rien de tout cela n'arrive.

## Solution proposée — à trancher

Deux moments possibles, pas exclusifs :

1. **Au démarrage** : les runs sans `finished_at` sont d'un processus qui n'est
   plus là — un backend local n'en a qu'un (ADR-038). Les solder en `blocked`,
   en nommant la cause, rend l'historique vrai.
2. **À l'arrêt propre** : un gestionnaire qui commite le travail en cours, dans
   l'esprit d'ADR-018. Ne couvre pas le `kill -9`, d'où le point 1.

L'arbre sale, lui, reste à la main de l'utilisateur : commiter du travail que
personne n'a relu, au redémarrage et sans qu'il l'ait demandé, serait pire que
le laisser voir.

## Critères d'acceptation

- [ ] Au démarrage, un run sans `finished_at` est soldé, avec une cause lisible
- [ ] Un run soldé ainsi n'est jamais marqué approuvé
- [ ] Le solde n'efface aucun événement ni aucun coût déjà enregistré
- [ ] `uv run pytest` passe

## Dépendances

Aucune.

## Estimation

Moins d'une journée.

## Risques

Solder au démarrage suppose qu'aucun autre processus ne tourne. Vrai d'un
backend local (ADR-038) ; faux le jour où il y en aurait deux. À nommer dans
le code, pas à supposer.
