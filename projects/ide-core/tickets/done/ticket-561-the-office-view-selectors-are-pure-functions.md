---
agent: codeur
created: 2026-10-23
depends_on: []
estimated_days: 0.5
id: ticket-561
pr_number: null
priority: medium
status: done
title: The office view selectors are pure functions
type: feat
---

# ticket-561 — Les sélecteurs purs du Bureau

## Objectif
Isoler, dans des fonctions pures testées, ce que le Bureau déduit du store de
run : les postes, l'issue d'une pièce, la boîte aux lettres, le mode compact.
Les composants des tickets suivants ne font que les afficher.

## Contexte
Conception : `docs/superpowers/specs/2026-10-23-vue-bureau-design.md`. Piège :
`run_closed` remet `etape` à `null` et `etapesEnCours` à `[]`
(`hooks/streamState.ts`), donc les étapes faites d'un run clos ne se lisent
pas là ; elles se lisent dans `ticketEvents`. `livraisonPrNumber` et `ciMerge`
existent déjà dans `StreamState`, mais `livraison_done` porte aussi `arret`,
`conflits` et `pr_orpheline`, que le store jette.

## Solution proposée
Dans `frontend/src/lib/bureau/`, un fichier par sélecteur, sans React :
- `postesDuRun(etat)` — les cinq postes (codeur, testeur, sécurité,
  reviewer, validateur), chacun `occupe`, `fait` ou `libre`, déduits de
  `agent_started` / `agent_done` / `security_audit_*` / `validation_*` de
  `ticketEvents`, que le run soit clos ou non ;
- `contourDeLaPiece(etat, sante)` — `neutre`, `vert`, `rouge` ou `amber`, d'après
  `issueDuRun` et la santé ;
- `boiteAuxLettres(etat)` — `aucune`, `ouverte`, `ci`, `mergee` ou `refusee`, avec
  le numéro de PR : `ci` = `livraison_done` avec une PR et sans `arret` (ou
  `pr_orpheline`), tant que `ci_merge_done` n'est pas venu ;
- `modeCompact(nombreDeProjetsAvecUnRun)` — vrai au-delà de 6.

## Critères d'acceptation
- [ ] `postesDuRun` rend un poste `fait` pour chaque agent terminé d'un run **clos**, et un test le vérifie avec un store passé par `run_closed`
- [ ] `postesDuRun` rend le poste du reviewer `occupe` et ceux du codeur et du testeur `fait` pour un run à la revue, et un test le vérifie
- [ ] `boiteAuxLettres` distingue les cinq états, et un test le vérifie pour chacun, dont `ci` puis `mergee` après `ci_merge_done`
- [ ] `contourDeLaPiece` rend `vert` pour un run terminé, `rouge` pour un run bloqué, en erreur ou figé, `amber` pour une question, et un test le vérifie
- [ ] `modeCompact(6)` est faux et `modeCompact(7)` est vrai, et un test le vérifie
- [ ] Aucun fichier du diff n'importe React, et aucun fichier ne dépasse 300 lignes
- [ ] Le diff ne modifie aucun fichier de `backend/`, ni `hooks/streamState.ts`

## Ce que ça ne fait pas
- N'affiche rien et ne lit aucune API.
- Ne traite ni l'attente extérieure ni le conflit : ils dépendent des événements du ticket-559 et sont dans le ticket-564.