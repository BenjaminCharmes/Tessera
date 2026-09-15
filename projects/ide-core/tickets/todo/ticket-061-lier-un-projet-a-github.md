---
id: ticket-061
title: "Lier un projet existant à un dépôt GitHub"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-15
---

# ticket-061 — Lier un projet à un dépôt GitHub

## Objectif

Qu'un projet créé de zéro, ou importé depuis un dossier local, puisse être
relié à un dépôt GitHub après coup.

## Contexte

Trois façons d'obtenir un projet, trois situations très différentes :

| Origine | État git aujourd'hui |
|---|---|
| Cloné depuis GitHub | Vrai dépôt, `origin` configuré — **rien à changer** |
| Importé en `symlink` | Le dépôt d'origine, avec son `origin` s'il en a un |
| Importé en `copy` | **Aucun dépôt** — `.git` est exclu de la copie |
| Créé de zéro | **Aucun dépôt** |

Les deux derniers cas n'ont donc ni versionnement ni remote. Or c'est
précisément le filet sur lequel repose tout le pipeline : sans dépôt,
`GitWorkspaceService` échoue, aucune branche n'est créée et **aucun commit
n'est fait** — le travail de l'agent reste dans l'arbre, sans trace, et tout
l'apport d'ADR-018 disparaît.

## Solution proposée

1. **`POST /projects/{id}/git/init`** — initialise un dépôt dans le projet s'il
   n'en a pas, avec un premier commit de l'état courant.
2. **`POST /projects/{id}/git/link`** — attache un remote `origin` à une URL
   GitHub fournie, et le consigne dans `agents.json` (`github_remote`), qui est
   déjà lu par les endpoints PR et sync.
3. **Vérification avant d'attacher** : le dépôt distant existe, le token y a
   accès, et il est vide *ou* l'utilisateur confirme explicitement — attacher
   un remote non vide à un projet local est une source de conflits.
4. **UI** : un état « non versionné » visible sur le projet, et l'action de
   lier depuis la sidebar.
5. Un projet déjà lié n'est pas modifié.

## Hors périmètre

Créer le dépôt sur GitHub depuis l'IDE. L'utilisateur le crée, l'IDE s'y
attache.

## Critères d'acceptation

- [ ] Un projet sans dépôt peut être initialisé depuis l'IDE
- [ ] Un remote `origin` peut être attaché à un projet existant
- [ ] `agents.json` porte le `github_remote` après liaison
- [ ] Une URL invalide ou inaccessible est refusée avec un message exploitable
- [ ] Attacher un remote non vide exige une confirmation explicite
- [ ] Un projet déjà lié reste inchangé
- [ ] L'UI montre qu'un projet n'est pas versionné, et propose de le lier
- [ ] Après liaison, un pipeline crée bien branche et commit

## Dépendances

Aucune.

## Estimation

**2j**.

## Risques

- **Moyen** — `git init` puis `git remote add` sur un dossier de l'utilisateur
  touche à ses données. Aucune opération destructive : on n'initialise que si
  `.git` est absent, on n'écrase jamais un remote existant sans confirmation.
