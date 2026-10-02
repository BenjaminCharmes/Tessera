---
agent: codeur
created: 2026-10-02
depends_on: []
estimated_days: 1
id: ticket-316
plan: true
pr_number: null
priority: medium
status: done
title: The validator also receives the current content of the test files a criterion
  names
type: fix
---

# ticket-316 — Le validateur lit aussi les fichiers qu'un critère nomme

## Objectif

Qu'un critère déjà rempli par du code existant ne soit plus refusé parce que
ce code n'apparaît pas dans le diff.

## Contexte

Le 2026-10-02, le ticket-015 de `freelance` s'est bloqué après trois tours sur
un critère : « Les onglets Projets, Facturation, Prospection et Offres
affichent un message quand leur liste est vide, et un test le vérifie pour
chacun ». Les quatre tests existaient (`BillingTab.test.tsx:44`,
`OffersTab.test.tsx:32`, `ProspectionTab.test.tsx:189` et `:235`, plus celui
que le ticket ajoutait). Le validateur ne reçoit que le diff
(`ValidatorService.validate(criteria, code_produced, test_result)`) : il a
répondu que les tests de trois onglets n'étaient « pas visibles dans le
diff », et il a refusé.

Le validateur tourne sur un modèle local, sans outil pour lire le dépôt.

## Solution proposée

- Avant l'appel au validateur, relever dans les critères les fichiers qu'ils
  nomment (chemins entre backticks, ou noms de fichiers de test), et joindre
  leur contenu actuel, borné en taille, dans une section distincte du diff
  (« Fichiers cités par les critères, tels qu'ils sont après le run »).
- Le prompt du validateur dit qu'un critère peut être rempli par du code
  préexistant visible dans cette section.

## Critères d'acceptation

- [x] Un test vérifie qu'un critère qui cite `BillingTab.test.tsx` fait
      joindre le contenu de ce fichier au message du validateur
- [x] Un test vérifie qu'un fichier cité mais absent du dépôt est signalé
      comme absent, sans lever d'exception
- [x] Un test vérifie que la section jointe reste sous une taille maximale,
      et qu'au-delà le fichier est tronqué avec une mention
- [x] `agents/prompts/validateur.md` dit comment lire cette section

## Dépendances

Aucune.

## Risques

Un message plus long ralentit le modèle local. La borne de taille s'applique
au total de la section, pas par fichier.