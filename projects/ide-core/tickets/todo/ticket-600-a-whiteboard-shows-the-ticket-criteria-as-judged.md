---
id: ticket-600
title: "A whiteboard on the room's wall shows the ticket's criteria as the validator judges them"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-593"]
estimated_days: 0.25
created: 2026-10-27
---

# ticket-600 — Le tableau blanc des critères

## Objectif
Idée 3 du « Bureau vivant » (`design/maquette/Bureau-vivant.dc.html`, tableau
blanc au mur de chaque pièce), validée le 27/10.

## Contexte
`validation_done` porte `data.criteria` : une liste
`{criterion, passed, note}`. Avant ce verdict, le nombre de critères du ticket
se lit dans son fichier (section « Critères d'acceptation ») — le tour de plan
dit si l'API des tickets le donne déjà, sinon le tableau reste vierge jusqu'au
verdict (ADR-058 : rien d'inventé).

## Ce que dit la maquette
Un tableau blanc au mur (132 × 42 px, sprite `TableauBlanc.tsx` sous
`design/bureau/`), une ligne par critère : case grise tant que rien n'est jugé,
verte si le critère passe, rouge sinon. Son libellé accessible : « Tableau
blanc : X critères sur N validés ». Au survol ou au focus, l'infobulle liste
les critères avec leur état (même portail que la pile, ticket-593).

## Critères d'acceptation
- [ ] Après un `validation_done` à 5 critères dont 4 passés, le tableau rend 4 cases vertes et 1 rouge, et le libellé « 4 critères sur 5 validés » ; un test le vérifie
- [ ] Sans `validation_done` ni nombre connu, le tableau est rendu vierge sans ligne ; un test le vérifie
- [ ] Au focus du tableau, l'infobulle liste chaque critère avec son état ; un test le vérifie
- [ ] `TableauBlanc.tsx` n'utilise que des jetons `--sprite-*` et les familles d'état permises ; `design/bureau/sources.test.ts` reste vert
- [ ] Le diff ne modifie aucun fichier de `backend/src/`
