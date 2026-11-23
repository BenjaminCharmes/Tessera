---
id: ticket-1037
title: "A documentation pass that wrote nothing says why, role by role"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-23
---

# ticket-1037 — Une passe de documentation qui n'écrit rien dit pourquoi, rôle par rôle

## Objectif

Que la ligne « documentation: 0 fichier(s) » du journal dise, pour chaque rôle,
ce qui s'est passé, et qu'une réponse perdue ne fasse plus passer un ticket pour
documenté.

## Contexte

Compté le 23/11 dans `memory/pipeline-log.md` d'ide-core : du 13 au 20/11, 62
passes de documentation, 9 ont écrit un fichier. Les 53 autres journalisent
« 0 fichier(s) », presque toujours sans un mot de plus, et le marqueur avance :
le ticket est compté comme documenté.

Trois issues différentes se cachent derrière cette même ligne, relevées dans
`backend/src/tessera/services/documentation/` :

1. **Le rôle n'a rien proposé** (`{"editions": []}`). Légitime pour un correctif
   interne. Rien ne le dit dans le journal du pipeline.
2. **La réponse est illisible.** `donnees_de` (`documentation_reponse.py`) prend
   le premier morceau qui contient `{` après un découpage sur les clôtures
   Markdown. Si la prose qui précède le bloc JSON contient une accolade (le
   prompt lui-même parle de `{fichier, extrait}`), c'est la prose qui est
   choisie, le JSON valide qui suit est jeté, et la réponse rend `{}`. Rejoué
   le 23/11 : une prose avec accolade suivie d'un bloc JSON valide rend `{}`.
   L'avertissement `reponse_doc_illisible` ne va que dans `tessera.log` (103
   fois pour `doc-technique`), jamais dans `pipeline-log.md`, et le marqueur
   avance comme si le rôle n'avait rien eu à écrire.
3. **Le tour de correction ne rend rien.** Dans `mettre_a_jour`
   (`documentation.py`), après un premier refus, `if not editions2: continue`
   abandonne le rôle sans verser le motif du premier refus à `refus`. Le
   journal dit « après tour de correction » et rien d'autre : le refus qui a
   coûté deux appels n'est écrit nulle part.

`documentation.py` est à son plafond exact dans `test_longueur_des_fichiers.py`
(326 lignes) : il ne peut pas grandir.

## Solution proposée

- `donnees_de` essaie chaque bloc clôturé, dans l'ordre, et garde le premier
  qui se lit comme un objet JSON ; sans bloc lisible, il essaie le texte entier
  comme aujourd'hui. Il rend de quoi distinguer « illisible » de « lisible et
  vide ».
- `ResultatDocumentation` porte l'issue de chaque rôle appelé, parmi :
  éditions appliquées, aucune édition proposée, réponse illisible, refusé.
- Une réponse illisible verse un motif à `refus` (« doc-technique : réponse
  illisible »), au premier tour comme au tour de correction : le lot suit alors
  la règle existante de `consigner_lot` (compté, abandonné au deuxième refus).
- Un tour de correction qui ne rend aucune édition verse à `refus` le motif du
  premier refus.
- `_journaliser` (`pipeline_documentation.py`) ajoute à la ligne
  « documentation: N fichier(s) » l'issue de chaque rôle qui n'a rien écrit.
- Le code nouveau vit hors de `documentation.py` (module voisin), qui ne
  dépasse pas sa longueur actuelle.

## Critères d'acceptation

- [ ] Un test de `donnees_de` donne une prose contenant `{fichier, extrait}`
      suivie d'un bloc ```` ```json ```` valide, et obtient les éditions du bloc.
- [ ] Un test de `donnees_de` donne deux blocs clôturés dont seul le second est
      un objet JSON, et obtient celui-ci.
- [ ] Un test de `mettre_a_jour` donne à un rôle une réponse illisible : le
      résultat porte un refus qui nomme le rôle et « réponse illisible », et,
      aucun rôle n'ayant rien écrit, le ticket du lot n'entre pas dans
      `documentes` du marqueur à ce premier refus.
- [ ] Un test de `mettre_a_jour` fait refuser le premier tour puis rend
      `{"editions": []}` au tour de correction : `refus` porte le motif du
      premier refus.
- [ ] Un test de `documenter_le_run` vérifie que la ligne du journal distingue
      « aucune édition proposée » de « réponse illisible », avec le nom du rôle.
- [ ] Le diff ne fait pas grandir `services/documentation/documentation.py` :
      son entrée dans `tests/test_longueur_des_fichiers.py` ne monte pas.

## Ce que ça ne fait pas

- Ne change ni le contenu du prompt ni sa taille : c'est le ticket-1038.
- Ne garde pas la réponse brute d'un agent sur disque.
- Ne rejoue pas les tickets déjà comptés comme documentés sans l'avoir été.

## Dépendances

Aucune. À livrer avant le ticket-1038, pour lire son effet dans le journal.

## Estimation

1 jour.

## Risques

Une réponse illisible compte désormais comme un refus : un rôle qui répond mal
deux fois de suite abandonne le lot (règle du ticket-940), là où il passait en
silence. C'est voulu, et le journal le dira.
