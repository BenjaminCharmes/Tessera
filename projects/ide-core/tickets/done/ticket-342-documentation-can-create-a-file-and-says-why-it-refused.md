---
id: ticket-342
title: "Documentation agents can create a missing file, and the pipeline log says why a batch was refused"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-05
---

# ticket-342 — La documentation peut créer un fichier, et un refus se voit

## Objectif

Qu'un guide qui n'existe pas encore puisse naître, et qu'un lot refusé se
lise dans `pipeline-log.md` sans fouiller le journal du backend.

## Contexte

Démineur, 2026-10-05 : `doc-fonctionnelle` tient `docs/guide-utilisateur.md`,
qui n'a jamais existé dans le dépôt. `appliquer_editions` refusait toute
édition d'un fichier absent (« fichier introuvable »), et le lot étant tout ou
rien, rien n'était écrit : six passages, de 2 à 9 minutes de calcul chacun,
pour rien. `pipeline-log.md` ne disait que « documentation: 0 fichier(s) » ;
le motif n'était qu'au journal du backend (`documentation_refusee`, routeur),
et `editions_refusees` (service) ne le portait pas. `documentation.json` est
resté sur ticket-030.

## Solution proposée

- Une édition `{"fichier", "contenu"}` crée un fichier absent sous
  `README.md` ou `docs/`, dossiers compris. Elle est refusée si le fichier
  existe : elle n'écrase jamais.
- Une édition sur un fichier absent dit comment le créer.
- Un fichier créé dans un lot peut être prolongé par une édition suivante du
  même lot (la lecture `resultat.get(f, f.read_text())` lisait le disque
  avant le lot, et échouait).
- `editions_refusees` journalise le motif ; `pipeline-log.md` écrit
  « — refusé : <motif> » après le nombre de fichiers.
- Les prompts `doc-technique` et `doc-fonctionnelle` décrivent `contenu`.

## Critères d'acceptation

- [x] Un test vérifie qu'un fichier absent sous `docs/` est créé depuis
      `contenu`
- [x] Un test vérifie qu'un fichier créé peut être prolongé dans le même lot
- [x] Un test vérifie que `contenu` sur un fichier existant est refusé, sans
      rien écrire
- [x] Un test vérifie qu'une création hors de la documentation est refusée
- [x] Un test vérifie qu'éditer un fichier absent dit d'utiliser `contenu`
- [x] Un test vérifie que `pipeline-log.md` nomme le motif d'un refus

## Ce que ça ne fait pas

Le `docs/guide-utilisateur.md` posé à la main dans démineur le 2026-10-05,
non suivi par git, n'est pas traité ici : un fichier non suivi au démarrage
d'un run est exclu de ses commits.

## Dépendances

Aucune.

## Estimation

0,5 jour.
