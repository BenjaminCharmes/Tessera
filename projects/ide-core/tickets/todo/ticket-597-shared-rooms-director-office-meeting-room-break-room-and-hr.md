---
id: ticket-597
title: "Shared rooms across the top: the director's office for questions, the meeting room, the break room and HR for model fallbacks"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-596"]
estimated_days: 0.75
created: 2026-10-27
plan: true
---

# ticket-597 — Les salles communes : directeur, réunion, pause, RH

## Objectif
Troisième ticket du « Bureau vivant » (`design/maquette/Bureau-vivant.dc.html`,
validée le 27/10). Benjamin a demandé un bureau du directeur (lui) et des RH ;
chaque salle reste liée à un événement réel (ADR-058).

## Ce que dit la maquette
Une rangée de quatre salles en haut de la vue, au-dessus des pièces des
projets, avec la colonne de droite réduite à « Agent choisi » et « À toi » :
- **Bureau du directeur** — toi, assis à un bureau en bois. Un agent dont le
  run a une question en attente (`StreamState.pendingQuestion`, ADR-025) quitte
  son poste et se tient devant toi avec une bulle « ? » ; le contour de la salle
  passe en ambre. Il revient à son poste quand la question a une réponse.
- **Salle de réunion** — la table ; le résolveur de conflit
  (`conflict_resolution`, ADR-033) s'y installe avec les deux versions et le
  nombre de fichiers. Existe déjà (`SalleReunion.tsx`) : elle rejoint la rangée.
- **Salle de pause** — inchangée dans son sens : quota, CI, dépendance
  (`SallePause.tsx`).
- **RH** — une recruteuse à son bureau. Sur `provider_fallback` (émis par
  `backend/src/tessera/services/providers/repli.py`, `data.role`,
  `data.tente`, `data.utilise`, `data.modele`), l'agent du rôle concerné y
  passe avec l'étiquette « <tenté> → <utilisé> », puis retourne à son poste au
  bout de 20 s. Contour ambre pendant ce temps.
- Dans les salles, chaque agent garde sa tenue et son physique (ticket-595),
  et son libellé dit son projet et son rôle.

## Solution proposée
- `components/BureauView/SallesCommunes.tsx` : la rangée (grille
  `auto-fit`), et `BureauDuDirecteur.tsx`, `SalleRh.tsx` à côté de
  `SalleReunion` et `SallePause`.
- Un agent présent dans une salle commune n'est plus dessiné à son poste
  (opacité nulle, non focalisable) : il ne peut être qu'à un endroit.
- `provider_fallback` porte `ticket_id: ""` : vérifier qu'il atteint le
  `StreamState` du run (sinon le relier par `project_id`), sans toucher au
  backend si possible ; le tour de plan le dit.

## Critères d'acceptation
- [ ] Avec une question en attente sur un run, le bureau du directeur rend l'agent du rôle en cours avec une bulle « ? », et ce poste n'a plus de personnage visible ; un test le vérifie
- [ ] Sans question, le bureau du directeur ne rend que toi ; un test le vérifie
- [ ] Un événement `provider_fallback` pour le rôle `validateur` fait apparaître cet agent aux RH avec « <tenté> → <utilisé> », et 20 s plus tard (temps simulé) il n'y est plus ; un test le vérifie
- [ ] Un `conflict_resolution` en phase `started` place le résolveur en salle de réunion avec le nombre de fichiers ; un test le vérifie
- [ ] La rangée rend les quatre salles dans l'ordre directeur, réunion, pause, RH ; un test le vérifie
- [ ] Le diff ne modifie aucun fichier de `backend/src/`
