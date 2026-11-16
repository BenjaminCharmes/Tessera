---
agent: architect
created: '2026-11-16'
depends_on: []
id: ticket-976
priority: high
status: todo
title: Le compte agent lance des outils qu'il peut lire, hors du profil de l'utilisateur
type: design
---

## Contexte

Preuve réelle du 16/11, Serpent ticket-009 sous `tessera-agent` (run
`fe1750cc`). L'étape de test (`npm run typecheck`, lancée sous le compte agent
depuis ADR-085) échoue en 109 s :

```
Error: EPERM: operation not permitted, lstat 'C:\Users\Benjamin.CHARMES\scoop'
```

Le `PATH` hérité du backend mène à node et npm installés par scoop dans le
profil de l'utilisateur. Le compte agent n'a, à juste titre, aucun droit sur
ce profil : node ne peut pas résoudre son propre chemin. `npm ci` du
`setup` passe parce qu'il tourne, lui, sous le compte du backend.
`tessera.ps1 agent doctor` dit « node trouvé sur ce poste » sans vérifier que
le compte agent peut le lancer. Le même défaut attend uv et Python (dans
`%APPDATA%\uv` et `~\.local\bin`) pour tout projet Python à compte agent.

Le CLI de l'agent a déjà réglé ce problème pour lui seul : copie partagée
dans `C:\ProgramData\Tessera\bin\claude.exe`.

## Ce qu'il faut décider

Comment le compte agent obtient node, npm, uv et Python sans aucun droit sur
le profil de l'utilisateur. Pistes à comparer, avec leur coût de mise à jour :

1. Une chaîne d'outils partagée sous `C:\ProgramData\Tessera\toolchain\`
   (copie ou installation portable), mise à jour par `agent setup`, et un
   `PATH` réduit à elle pour tout processus du compte agent.
2. Installer node et uv pour tous les utilisateurs (`C:\Program Files`), et
   retirer du `PATH` du compte agent toute entrée sous un profil.
3. Donner au compte agent la lecture d'un sous-dossier du profil : à
   écarter sauf argument fort, c'est ce que l'isolation veut éviter.

Le ticket écrit l'ADR et découpe la réalisation en tickets `fix`.

## Critères d'acceptation

- [ ] ADR qui tranche, avec la règle proposée sous `## Proposées` de
      `contraintes.md` si elle en crée une.
- [ ] Tickets de réalisation écrits, dont un qui fait vérifier par
      `agent doctor` que **le compte agent** lance `node --version` et
      `uv --version` (pas seulement qu'ils existent).
- [ ] Chaque ticket de réalisation porte un critère de preuve réelle :
      Serpent ticket-009 sous `tessera-agent` passe l'étape de test.

## Ce que ça ne fait pas

- Ne touche pas aux droits du dossier des worktrees : ticket-975.
