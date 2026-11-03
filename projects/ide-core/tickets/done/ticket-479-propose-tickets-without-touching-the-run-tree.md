---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 1
id: ticket-479
plan: true
pr_number: 533
priority: medium
status: done
title: New tickets can be proposed to a project while a run holds its tree
type: feat
---

# ticket-479 — Proposer des tickets sans toucher l'arbre d'un run

## Objectif

Une session ou l'interface dépose de nouveaux tickets sur un projet pendant
qu'un run occupe son arbre, sans worktree ni PR faits à la main.

## Contexte

souhaito, 16/10 : poser un ticket pendant un run a demandé quatre fois le
même geste (worktree depuis `origin/main`, commit, push, PR, merge,
nettoyage). La session ide-core le refait à chaque ticket.

## Solution proposée

`POST /api/v1/projects/{id}/tickets/propose` avec un ou plusieurs fichiers
de ticket (nom et contenu) :
- valide chaque frontmatter avec le même modèle que le chargement des
  tickets, et refuse en 422 un ticket invalide ;
- crée un worktree temporaire depuis la base distante, écrit les fichiers
  dans `tickets/todo/`, commite, pousse une branche, ouvre la PR vers la
  base et la merge si le projet est en `autonomy: merge` (sinon la laisse
  ouverte), puis supprime le worktree ;
- ne touche jamais l'arbre principal du projet.

## Critères d'acceptation

- [ ] Un test vérifie qu'un ticket au frontmatter invalide est refusé en 422
      sans rien pousser
- [ ] Un test vérifie que l'arbre principal reste intact pendant et après
- [ ] Un test vérifie que le worktree temporaire est supprimé, y compris
      quand le push échoue
- [ ] Un test vérifie que la PR n'est mergée que pour `autonomy: merge`