---
agent: codeur
created: 2026-10-26
depends_on:
- ticket-581
estimated_days: 0.25
id: ticket-585
pr_number: 670
priority: high
status: done
title: The office shows when a run is writing its documentation or delivering
type: fix
---

# ticket-585 — Le Bureau montre la documentation et la livraison

## Objectif
Qu'une pièce ne paraisse pas à l'arrêt pendant la documentation et la
livraison : le 26/10, le 579 a passé 2 min 20 en documentation puis plus de
10 min en livraison (rebase, retest, push, PR), et le Bureau n'affichait rien.

## Contexte
- Les cinq postes (`frontend/src/lib/bureau/postesDuRun.ts`, `POSTES`) sont
  tous `fait` après `pipeline_done` ; aucun ne couvre la suite.
- `StreamState.etape` vaut `"documentation"` puis `"livraison"`
  (`hooks/streamState.ts`, sur `documentation_started` et
  `livraison_started`), jusqu'à `run_closed` : la donnée existe déjà, aucun
  ticket backend n'est nécessaire (ADR-058).
- La maquette (`design/maquette/Bureau.dc.html`) place la livraison dans
  l'en-tête de la pièce (la boîte aux lettres, `BoiteAuxLettres.tsx`).

## Solution proposée
Pendant `etape === "documentation"`, la pastille du pied de la pièce
(`Piece.tsx`) dit « documentation » ; pendant `etape === "livraison"`, elle
dit « livraison : rebase, tests, PR » ; la boîte aux lettres
(`lib/bureau/boiteAuxLettres.ts`) ne change pas. Les deux en ton `blue`
(ADR-026). Aucune sous-étape inventée :
la livraison n'émet pas d'événement par étape.

## Critères d'acceptation
- [ ] Après `pipeline_done` puis `documentation_started`, la pièce affiche « documentation » ; un test le vérifie
- [ ] Après `livraison_started`, la pièce affiche « livraison : rebase, tests, PR » ; un test le vérifie
- [ ] Après `run_closed`, ni l'un ni l'autre n'est affiché ; un test le vérifie
- [ ] Les deux libellés n'utilisent que la famille `blue` ; le test `design/bureau/sources.test.ts` reste vert
- [ ] Le diff ne modifie aucun fichier de `backend/`