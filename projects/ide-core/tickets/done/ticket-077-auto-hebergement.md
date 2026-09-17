---
id: ticket-077
title: "Auto-hébergement, coûts par projet, et un Markdown réellement stylé"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-076]
estimated_days: 1
created: 2026-09-17
---

# ticket-077 — Auto-hébergement, coûts par projet, Markdown stylé

## L'auto-hébergement était cassé — par moi

ADR-024 refuse qu'un projet agisse sur un dépôt **ancêtre**. Elle est née d'un
dossier client posé dans `projects/`, dont l'ancêtre était vibe-ide : un
accident, et un run y aurait commité dans l'IDE.

Mais c'est exactement ce que fait le projet bootstrap d'ADR-001. `ide-core`
n'est pas la racine de son dépôt, et son travail est dans `backend/` et
`frontend/`, au-dessus de lui. Traiter les deux cas pareil supprimait
l'auto-hébergement, c'est-à-dire le principe fondateur du projet.

Un projet déclare donc `"git_root": "ancestor"` dans son `agents.json`. Il
stage alors depuis la racine du dépôt (`:/`) et non depuis son dossier — sans
quoi la branche se créait mais le commit ne voyait rien. Même forme que le mode
des artefacts : le défaut protège, le cas particulier s'énonce, une valeur
inconnue ne désarme rien (ADR-028).

## Le Markdown n'avait aucun style

Les règles avaient atterri dans un `src/styles.css` **que rien n'importait**.
Le build passait, les tests aussi, et la vue « Rendu » s'affichait en texte nu :
titres sans hiérarchie, listes sans puces ni numéros, blocs de code sans cadre.

Les règles sont passées dans `src/index.css`, après les directives Tailwind pour
l'emporter sur son *preflight*. Et un test refuse désormais toute feuille de
style que personne n'importe — c'est la troisième fois qu'un garde-fou de cette
session laisse passer ce qu'il prétendait couvrir.

## Coûts par projet

`« Combien me coûte vibe-ide, et sur quel projet »` n'avait aucune réponse :
chaque endpoint était borné à un projet. La ventilation par projet apparaît
quand aucun n'est sélectionné ; elle reste vide sinon, où elle n'apprendrait
rien.

## Vérifié

910 tests backend, mypy sur 65 fichiers, 367 tests frontend, 5 flows E2E,
`npm run build`.
