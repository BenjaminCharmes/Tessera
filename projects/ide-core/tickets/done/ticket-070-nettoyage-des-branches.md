---
id: ticket-070
title: "Nettoyage des branches laissées par vibe-ide, sans jamais perdre de travail"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-069]
estimated_days: 1
created: 2026-09-17
---

# ticket-070 — Nettoyage des branches

## Pourquoi

Chaque run crée `ticket-XXX-…`, chaque session de chat `chat/<horodatage>`, et
rien ne les retirait jamais. Après **une seule** session d'usage réel, `tmp` en
portait deux, mortes, identiques à `main`. Sur un dépôt client, l'accumulation
devient visible — et se dégrade toute seule.

## Décision

Supprimer une branche est irréversible, et sur le dépôt de quelqu'un d'autre
c'est le genre d'automatisme qu'on regrette. Le nettoyage **montre avant
d'agir** : l'utilisateur lit ce qui partira et pourquoi le reste demeure, puis
décide. Rien ne se supprime sans un clic.

Quatre garde-fous :

1. **Seulement ce que vibe-ide a créé** — `ticket-*` et `chat/*`. Le reste
   appartient à l'utilisateur.
2. **Jamais la branche courante.**
3. **Jamais une branche poussée** — elle existe ailleurs, et la retirer ici
   laisserait local et distant incohérents.
4. **Jamais une branche qui porte du travail absent de la base.** Un run rejeté
   commite quand même (ADR-018) : sa branche est le seul exemplaire de ce
   travail.

Le quatrième est le seul qui compte vraiment : une branche dont tous les commits
sont déjà dans la base ne contient rien qui puisse être perdu. C'est la seule
condition sous laquelle une suppression est sans conséquence.

**Le plan est recalculé côté serveur** à la suppression. Entre l'affichage et le
clic, un run a pu committer sur l'une de ces branches ; se fier à la liste
envoyée par l'interface reviendrait à supprimer sur la foi d'un état périmé.

## Livré

- `services/branch_cleanup.py` — `plan_de_nettoyage` et `supprimer_branches`
- `GET` et `POST /projects/{id}/branches/cleanup`
- `components/Sidebar/BranchCleanup` — dans le panneau Git & artefacts,
  invisible quand il n'y a rien à dire

## Vérifié

891 tests backend, mypy sur 65 fichiers, 331 tests frontend, 5 flows E2E,
`npm run build`.
