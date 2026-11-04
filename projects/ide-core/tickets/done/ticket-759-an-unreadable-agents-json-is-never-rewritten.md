---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-759
pr_number: null
priority: high
status: done
title: An unreadable agents.json is never rewritten, and a BOM is read
type: fix
---

# ticket-759 — Un `agents.json` illisible n'est jamais réécrit, et un BOM se lit

## Objectif

Écrire une clé du manifeste ne peut plus effacer le reste de sa configuration.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-675.
- `ecrire_clef` (`backend/src/tessera/services/manifeste.py`) lit par `lire_fichier`, qui
  rend `{}` sur un fichier illisible, puis réécrit le fichier. Un `agents.json` en Latin-1,
  ou au JSON invalide, devient `{"github_remote": "o/r"}` quand on lie un remote (vérifié) :
  `agents`, `autonomy`, `worktree`… disparaissent, et les runs suivants tournent dans le
  checkout (contre ADR-056). Avant 675, une `UnicodeDecodeError` levait sans écrire.
  `lire_pour_modifier` existe justement pour refuser ce cas.
- `appliquer_description` (`documentation_description.py`) décode hors de son `try` : un
  manifeste non UTF-8 fait échouer tout le lot de documentation (vérifié).
- `lire_fichier` traite un manifeste avec BOM UTF-8 comme illisible, alors que
  `documentation_description` l'accepte.

## Critères d'acceptation

- [ ] Un test vérifie que, sur un manifeste au JSON invalide ou non UTF-8, `ecrire_clef` lève
      et le fichier reste identique octet pour octet
- [ ] Un test vérifie que `ecrire_clef` sur un manifeste absent le crée avec la seule clé
- [ ] Un test vérifie que `appliquer_description` sur un manifeste Latin-1 rend un refus sans
      lever
- [ ] Un test vérifie que `lire_fichier` lit un manifeste précédé d'un BOM UTF-8