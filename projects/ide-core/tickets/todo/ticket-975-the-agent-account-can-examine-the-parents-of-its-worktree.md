---
agent: codeur
created: '2026-11-16'
depends_on: []
id: ticket-975
priority: high
status: todo
title: Le compte agent peut examiner les dossiers parents de son worktree
type: fix
---

## Contexte

Preuve réelle du 947, 16/11 à 09:15 UTC, Serpent ticket-009 sous
`tessera-agent` (run `fe1750cc`). Le worktree est bien créé sous
`C:\ProgramData\Tessera\worktrees\serpent\ticket-009`, et
`droits_worktree.poser_ecriture` y donne `tessera-agent:(OI)(CI)M`. Mais les
trois `Read` du codeur sont refusés par le CLI lui-même : « la destination ne
peut pas être déterminée, un lien du chemin n'a pas pu être examiné ». Le
codeur n'a rien pu lire, le tour est perdu.

Cause, lue par `icacls` le 16/11 :

- `C:\ProgramData\Tessera\worktrees` : ACL posé par `preparer_dossier_agent`
  (`dossier_agent.py`), `/inheritance:r`, SYSTEM, Administrateurs et le compte
  du backend seulement. **Aucune entrée pour le compte agent.**
- `worktrees\serpent` : hérite de ce qui précède, donc rien non plus.
- `worktrees\serpent\ticket-009` : `tessera-agent:(OI)(CI)M`.

Le compte ouvre `ticket-009` grâce au contournement de traversée de Windows,
mais ne peut ni lister ni lire les attributs de `worktrees` et de `serpent`.
Le CLI vérifie chaque segment d'un chemin à la recherche de liens
symboliques : un `lstat` refusé sur un parent fait refuser le chemin entier.
Node fait de même (`realpath`) : tout outil qui résout son chemin échouera.

## Ce qu'il faut faire

- `preparer_dossier_agent` ajoute au compte agent, sur `worktrees`, le droit
  de lister et de lire les attributs **de ce dossier seul**, sans héritage
  (`icacls <dossier> /grant <compte>:(RX)`, sans `(OI)(CI)`).
- À l'ouverture d'un worktree agent, le dossier du projet
  (`worktrees\<projet>`) reçoit le même droit, sans héritage. Rien de plus :
  le compte voit les noms des dossiers de tickets, pas leur contenu (les
  autres worktrees n'ont pas son entrée).
- Un dossier `worktrees` déjà créé sans ce droit (cas de ce poste) le reçoit
  au prochain run : l'appel est idempotent.

## Critères d'acceptation

- [ ] `preparer_dossier_agent` appelle `icacls` avec `<compte>:(RX)` sans
      `(OI)` ni `(CI)` sur le dossier des worktrees (test, lanceur simulé).
- [ ] L'ouverture d'un worktree agent pose le même droit sur
      `worktrees\<projet>` (test).
- [ ] Le droit d'écriture du ticket (`poser_ecriture`, `retirer_ecriture`)
      ne change pas (tests existants inchangés).
- [ ] **Preuve réelle (session ide-core, après redémarrage)** : relancer
      Serpent ticket-009 sous `tessera-agent` ; les `Read` du codeur dans
      `C:\ProgramData\Tessera\worktrees\serpent\ticket-009` aboutissent ;
      `icacls` montre `tessera-agent:(RX)` sans `(OI)(CI)` sur `worktrees` et
      `worktrees\serpent`.

## Ce que ça ne fait pas

- Ne donne au compte agent aucun droit sur le contenu des autres worktrees.
- Ne règle pas l'accès du compte agent à node, npm ou uv : ticket-976.
