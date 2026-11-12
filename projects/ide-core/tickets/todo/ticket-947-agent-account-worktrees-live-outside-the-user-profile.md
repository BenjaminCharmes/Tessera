---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 1
id: ticket-947
pr_number: null
priority: high
status: todo
title: "Worktrees of an agent-account project live outside the user profile"
type: fix
---

# ticket-947 — Les worktrees d'un projet au compte dédié vivent hors du profil de l'utilisateur

## Objectif

Qu'un agent lancé sous `AGENT_USER` puisse écrire dans le worktree de son run.
Aujourd'hui, il ne le peut pas.

## Contexte

Preuve réelle du 12/11 (ticket-946) : sous `tessera-agent`, le CLI démarre et
répond, mais refuse d'écrire dans un dossier de
`C:\Users\<utilisateur>\.tessera\…` (« chemin non résolvable »), alors que le
compte y a le droit `M`. Le compte peut traverser les dossiers du profil, mais
pas en lire les attributs, et le CLI résout chaque chemin avant d'écrire. Dans
`C:\ProgramData\Tessera\preuve-946`, avec le même droit, tout marche :
`whoami` → `tessera-agent`, `.env` de Tessera refusé, fichier écrit.

Or `IDE_WORKTREES_DIR` place par défaut tous les worktrees sous
`~/.tessera/worktrees` (ADR-056). Tant que c'est le cas, aucun run sous compte
ne peut écrire.

## Solution proposée

1. Un réglage `IDE_WORKTREES_DIR_AGENT` (défaut
   `C:\ProgramData\Tessera\worktrees`) : un projet à `worktree.compte_agent`,
   avec `AGENT_USER` renseigné, crée ses worktrees là, sous
   `<projet>/<ticket>` comme aujourd'hui. Les autres projets ne changent pas.
2. Au premier usage, le dossier est créé avec une ACL explicite, sans
   héritage : SYSTEM et Administrateurs (F), l'utilisateur du backend (M).
   Le compte agent n'y reçoit rien de plus que ce que
   `accorder_droits_agent` pose sur le worktree du run.
3. `tessera.ps1 agent doctor` vérifie ce dossier et son ACL.

## Critères d'acceptation

- [ ] Un test : avec `AGENT_USER` et `compte_agent: true`, la racine du
      worktree d'un run est sous `IDE_WORKTREES_DIR_AGENT`.
- [ ] Un test : sans `compte_agent`, ou avec `AGENT_USER` vide, elle reste
      sous `IDE_WORKTREES_DIR`.
- [ ] Un test, avec un double d'`icacls` : la création du dossier pose
      l'ACL sans héritage décrite ci-dessus.
- [ ] Un test : le nettoyage des worktrees orphelins au démarrage parcourt
      aussi `IDE_WORKTREES_DIR_AGENT`.
- [ ] Un test de `backend/tests/` vérifie que `agent doctor` contrôle ce
      dossier.

## Ce que ça ne fait pas

- Ne déplace pas les worktrees existants ni ceux des projets sans compte
  dédié.
- Ne sépare pas le bureau du compte (ticket-944) et ne crée pas de job
  (ticket-943).
