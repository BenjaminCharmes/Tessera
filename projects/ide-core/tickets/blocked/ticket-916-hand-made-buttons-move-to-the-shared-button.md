---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.5
id: ticket-916
pr_number: null
priority: low
status: blocked
title: Hand-made buttons move to the shared Button component
type: refactor
---

# ticket-916 — Les boutons faits à la main passent par le `Button` partagé

## Objectif

Qu'un bouton plein ou bordé ait le même aspect dans toutes les vues.

## Contexte

`design/ui/Button.tsx` porte les variantes `plein`, `borde`, `discret`,
`arret` et les tailles `normal`, `compact`, `pastille`. Il est importé dans une
cinquantaine de fichiers, mais l'audit du 11/11 a trouvé des boutons recopiés
à la main, avec des teintes et des rayons qui divergent :

- pleins violets : `components/BandeauJeton/index.tsx` (`bg-violet-600`),
  `components/ChatPanel/index.tsx` (`rounded-sm bg-violet-700`),
  `components/RituelsView/CarteRituel.tsx` (`rounded-md bg-violet-600`) ;
- bordés zinc : la constante `BOUTON` de `components/RituelsView/CarteRituel.tsx`,
  `components/AgentPanel/AgentDialogue.tsx`, `components/AgentDetail/Definition.tsx`,
  `components/SupervisionView/AdresseDuService.tsx`,
  `components/Sidebar/BandeAutonome.tsx`, `components/Sidebar/BranchCleanup.tsx`,
  `components/Sidebar/PanneauServices.tsx`, `components/Sidebar/ProjectHeader.tsx`.

## Solution proposée

Remplacer chacun de ces boutons par `<Button>` avec la variante et la taille
les plus proches. Ne pas toucher aux boutons-icônes ni aux onglets. Une
variante nouvelle seulement si un cas cité n'entre dans aucune.

## Critères d'acceptation

- [ ] Les trois pleins violets cités utilisent `<Button variante="plein">`.
- [ ] Les boutons bordés des huit fichiers cités utilisent `<Button>` ; la
      constante `BOUTON` de `CarteRituel.tsx` a disparu.
- [ ] Le diff n'ajoute aucune classe `bg-violet-600` ni `bg-violet-700` dans
      `components/`.
- [ ] Les tests existants de ces composants passent, adaptés si un sélecteur
      dépendait d'une classe retirée.

## Ce que ça ne fait pas

Ne migre pas les autres `<button>` (icônes, onglets, lignes cliquables).

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

`Button` a une hauteur fixe (`h-[30px]`) : un bouton d'une ligne dense peut
demander `compact`.