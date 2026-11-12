---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.5
id: ticket-954
pr_number: null
priority: high
status: done
title: The documentation batch sees the whole documentation of a project, and says
  when it cannot
type: fix
---

# ticket-954 — Le lot de documentation voit toute la documentation d'un projet, et dit quand il ne peut pas

## Objectif

Que les agents de documentation lisent en entier les fichiers qu'ils doivent
modifier, et qu'une documentation réduite à ses titres se voie dans le
journal.

## Contexte

`_contenu_documentable` (`services/documentation/documentation.py`) donne aux
agents le `README.md` puis chaque `docs/*.md` par ordre alphabétique, sous un
budget **total** de 60 000 caractères (`_BORNE_DOC`). Un fichier qui
dépasse le reste du budget est réduit à ses titres. L'agent ne peut alors
plus citer son texte exact (`ancien`) : ses éditions sont refusées en
« texte introuvable ».

Mesuré le 12/11 (README + `docs/*.md`) : vigie 111 261 caractères, kadoomi
138 137, affut 178 662, carriere 79 929. Pour ces quatre projets, une partie
de la documentation n'est jamais lue en entier. Scinder un fichier n'aide
pas : le budget est global.

## Solution proposée

1. `_BORNE_DOC` passe à 200 000 caractères (environ 50 000 jetons ; les
   rôles de documentation tournent sur Haiku).
2. Quand un fichier est réduit à ses titres, le lot l'écrit dans
   `memory/pipeline-log.md` : « documentation trop longue, titres seuls :
   docs/x.md (N caractères) ».

## Critères d'acceptation

- [ ] Un test : une documentation de 150 000 caractères en trois fichiers est
      rendue en entier.
- [ ] Un test : au-delà de 200 000, le fichier qui déborde est réduit à ses
      titres, et son chemin est rendu dans la liste des fichiers réduits.
- [ ] Un test : un lot dont un fichier est réduit écrit la ligne de journal
      avec son chemin et sa taille.
- [ ] Le test existant de `_contenu_documentable` passe (avec sa borne
      passée en paramètre).

## Ce que ça ne fait pas

- Ne choisit pas les fichiers selon le ticket : l'ordre reste alphabétique.
- Ne change ni les modèles ni les prompts des rôles de documentation.