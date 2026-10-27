---
agent: codeur
created: 2026-10-26
depends_on:
- ticket-582
estimated_days: 0.5
id: ticket-591
pr_number: 665
priority: high
status: done
title: 'Every agent of the pipeline stays visible: waiting at its desk, working, or
  done beside it'
type: fix
---

# ticket-591 — Chaque agent reste à l'écran : il attend, il travaille, ou il a fini

## Objectif
Le 26/10, Benjamin trouvait que le Bureau « display vraiment pas grand
chose » : un seul personnage par pièce, les autres postes vides. Il demande
que l'agent qui attend le travail du précédent soit quelque part, et que
celui qui a fini reste visible.

## Contexte
- `lib/bureau/postesDuRun.ts` donne à chaque poste un état `libre`, `occupe`
  ou `fait`, déduit des événements du ticket en cours : ce sont des états
  réels (ADR-058), pas un décor.
- `design/bureau/Poste.tsx` ne dessine le `Personnage` que sur un poste
  `occupe` ; `libre` est un bureau vide à 50 % d'opacité
  (`PosteDeTravail.tsx`), `fait` un bureau vide avec une coche.
- La maquette (`design/maquette/Bureau.dc.html`) suit ce modèle ; ce ticket
  le change à la demande de Benjamin. Le personnage de la salle de pause de
  la maquette (tasse à la main) sert de modèle à l'agent qui a fini.

## Solution proposée
- `libre` (pas encore son tour) : le personnage est assis à son poste,
  immobile, écran éteint, à 50 % d'opacité ; libellé « attend son tour ».
- `occupe` : inchangé.
- `fait` (fini pour ce ticket) : le personnage est debout à côté de son poste,
  tasse à la main, la coche reste sur l'écran ; libellé « a fini ».
- Aucune animation pour `libre` ni `fait` ; les tons restent des jetons
  `--sprite-*` (ADR-058).
- Hors run (pièce au repos), aucun personnage : rien ne se passe.

## Critères d'acceptation
- [ ] Un poste `libre` rend le sprite `personnage` sans animation et un libellé accessible contenant « attend son tour » ; un test le vérifie
- [ ] Un poste `fait` rend le sprite `personnage` debout (variante distincte, par exemple `data-pose="debout"`) et la coche ; un test le vérifie
- [ ] Un poste `occupe` rend toujours le personnage qui tape ; un test le vérifie
- [ ] Une pièce sans run ne rend aucun sprite `personnage` ; un test le vérifie
- [ ] `design/bureau/sources.test.ts` reste vert (jetons `--sprite-*`, pas de propriété animée coûteuse)
- [ ] Le diff ne modifie aucun fichier de `backend/`