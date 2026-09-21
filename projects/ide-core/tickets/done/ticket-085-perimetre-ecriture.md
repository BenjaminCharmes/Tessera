---
id: ticket-085
title: "Un agent n'écrit que dans son projet"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: [ticket-084]
estimated_days: 1
created: 2026-09-18
---

# ticket-085 — Le périmètre d'écriture d'un agent

## Pourquoi

`cwd` place l'agent dans le dossier du projet. Il ne l'y enferme pas : rien
n'empêchait un `Write` vers `../autre-client/src/app.py`, ni vers `backend/`.

Six dépôts clients voisins dans `projects/` — plus le
dépôt de vibe-ide au-dessus. C'est la même fuite qu'ADR-021 et ADR-023
cherchent à empêcher, prise par l'autre bout : on avait verrouillé ce qui
**part** dans un dépôt client, pas ce qui **y entre**.

Et ce n'est pas théorique : ADR-027 existe parce que des agents ont commité,
mergé et poussé pendant deux runs où l'utilisateur n'avait cliqué que sur
« lancer ».

## Critères d'acceptation

- [x] `Write`, `Edit` et `NotebookEdit` hors racine sont refusés au niveau du
      SDK, par un hook `PreToolUse`
- [x] La racine est le dossier du projet ; `git_root: ancestor` l'élargit au
      **dépôt** qui le contient, pas à `projects/`
- [x] Une valeur inconnue ou un `agents.json` illisible n'élargit rien
- [x] Les chemins sont résolus des deux côtés — les projets sont des symlinks
- [x] `client-a` n'ouvre pas `client-attaque` : comparaison par segments, pas
      par préfixe de chaîne
- [x] La lecture hors projet reste permise
- [x] Le message de refus dit que c'est *l'endroit* qui est refusé, pas le
      travail — sinon l'agent abandonne le ticket au lieu de réécrire ailleurs
- [x] Un test vérifie que le hook est réellement posé sur les options du SDK
- [x] ADR-031 écrite

## Ce que ça ne fait pas

**`Bash` n'est pas couvert.** Une redirection shell (`echo x > ../y`) échappe
au contrôle. La traquer demanderait d'analyser une ligne de shell pour y
trouver toutes les formes d'écriture — l'arms race que `git_guard` refuse
déjà, et qu'on perd en ratant une seule forme.
