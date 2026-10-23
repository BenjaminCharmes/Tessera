---
id: ticket-550
title: "Design of the office view that replaces Supervision, where each running agent is a character"
type: design
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: ["ticket-549"]
estimated_days: 1
created: 2026-10-23
plan: true
---

# ticket-550 — Conception de la vue « Bureau », qui remplace Supervision

## Objectif
Concevoir l'implémentation de la vue Bureau validée par Benjamin le 23/10 :
la vue par défaut de Supervision, où chaque agent en cours est un personnage
et où chaque objet de la pièce montre un état réel de Tessera.

## Décisions déjà prises (Benjamin, 23/10)
- **Le Bureau remplace Supervision** et en garde toutes les fonctions : cartes
  de run et chrono, ouverture du fil, fermeture des runs clos un par un et par
  lot (« Ranger par lot »), services lancés (adresse, sortie, arrêt). La vue
  **Liste** reste dans le sélecteur, pour le détail dense et la lecture au
  clavier ou au lecteur d'écran.
- **Rien de décoratif** : chaque élément correspond à un état réel.

| Élément | État réel |
|---|---|
| Pièce par projet, un poste par étape du pipeline | run vivant, étape en cours, étapes faites |
| Personnage, écran, bulle, pastille | santé de l'agent (ticket-549) : travaille, silencieux, question, figé ? |
| Pièce rangée ou non, contour vert ou rouge | run clos et son issue, jusqu'à « Ranger » |
| Pile de dossiers à l'entrée | tickets restants de la file |
| Boîte aux lettres | PR ouverte, CI, mergée |
| Baie de serveur | services déclarés du projet, vivants ou arrêtés |
| Salle de pause, machine à café | attente extérieure : quota épuisé (heure de reprise), CI de la phase 2 (`CIWatcher`), `depends_on` |
| Salle de réunion | conflit de rebase confié à `resolveur-conflit`, puis relecture humaine (ADR-033) |
| Tableau du jour | dépense du jour, quota restant |
| Colonne « À toi » | questions en attente (réponse sur place), agents figés, PR à relire |
| Alerte sonore | une question arrive ; activable, coupée par défaut à trancher |
| Mode compact | au-delà de 6 projets : une rangée par projet |

## Maquette
`design/maquette/Bureau.dc.html` (vue normale) et
`design/maquette/Bureau-Compact.dc.html` (plus de 6 projets) —
https://claude.ai/artifact/WMqxQRWx8ndc7Jm2RWMPaE

## À trancher par la conception
- Pour chaque élément du tableau, la donnée de l'API qui l'alimente, et ce
  qui manque côté backend (heure de reprise du quota, phase CI d'un run,
  tickets restants d'une file vivante — l'état `restants` de
  `GET /runs/<id>` n'inclut pas les tickets ajoutés par `append`).
- Rendu des sprites (SVG en pixels, comme la maquette, ou canvas), coût dans
  Tauri avec dix agents, `prefers-reduced-motion`.
- Découpage : `SupervisionView` est déjà au-dessus de 200 lignes ; le Bureau
  vit dans ses propres composants, sous le plafond du ticket-545.

## Critères d'acceptation
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit la vue Bureau et pourquoi elle remplace Supervision en gardant la vue Liste
- [ ] Le livrable cite `design/maquette/Bureau.dc.html` et `design/maquette/Bureau-Compact.dc.html`, et donne pour chaque ligne du tableau ci-dessus la donnée de l'API qui l'alimente ou le ticket backend qui la fournira
- [ ] Le livrable liste les tickets d'implémentation qui en découlent, chacun avec ses critères vérifiables, aucun ne mêlant backend et frontend

## Ce que ça ne fait pas
- N'implémente rien : ticket de conception.
