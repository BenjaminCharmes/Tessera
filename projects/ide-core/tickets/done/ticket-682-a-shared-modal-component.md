---
agent: codeur
created: 2026-10-29
depends_on: []
id: ticket-682
priority: low
status: done
title: A shared modal component
type: refactor
---

# ticket-682 — Un composant `Modale`

## Objectif
Le fond, `role="dialog"`, `aria-modal` et la fermeture par `Escape` vivent à un
seul endroit.

## Contexte
Dix fonds `fixed inset-0 z-50 …` et six gestionnaires `Escape`
(`docs/audit/doublons.md` §2.2) : `Sidebar/CreateTicketModal.tsx:79`,
`CreateProjectModal.tsx:100,192`, `AgentList.tsx:171`, `AgentCreatorModal.tsx:65`,
`PlanEvolutionModal.tsx:112`, `ImportProjectModal.tsx:145`,
`RemoveProjectModal.tsx:56`, `SignalementModal.tsx:67`,
`MiseEnLigne/Fenetre.tsx:23` (teinte différente). Trois n'ont pas de gestionnaire
`Escape` repéré.

## Critères d'acceptation
- [ ] Un composant `Modale` porte le fond, les attributs ARIA et `Escape` ; une prop permet de suspendre la fermeture (cas de `PlanEvolutionModal.tsx:104`)
- [ ] `grep -rn "fixed inset-0 z-50" frontend/src` hors tests ne trouve plus que ce composant
- [ ] Un test du composant couvre : rendu, `Escape` ferme, `Escape` suspendu, clic sur le fond
- [ ] Les trois modales sans `Escape` aujourd'hui : la PR dit, pour chacune, si elle l'acquiert ou si elle en est exemptée et pourquoi
- [ ] Les tests existants de `CreateProjectModal`, `CreateTicketModal` et `PlanEvolutionModal` (`keyDown` `Escape`) passent sans modification
- [ ] Aucune couleur hors ADR-026 ; `npm run test`, `npx tsc --noEmit` et `npm run lint` passent

## Ce que ça ne fait pas
- Ne regroupe pas les popovers (`BoutonReglages.tsx:45`, `Cloche.tsx:61`)
- Ne refait pas le contenu des modales
- Ne touche pas `components/BureauView/` (ticket-631)