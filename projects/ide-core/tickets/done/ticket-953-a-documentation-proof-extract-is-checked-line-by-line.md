---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.5
id: ticket-953
pr_number: 1081
priority: high
status: done
title: A documentation proof extract is checked line by line, and a refusal says which
  line failed
type: fix
---

# ticket-953 — Un extrait de preuve se contrôle ligne à ligne, et un refus dit quelle ligne manque

## Objectif

Que le lot de documentation ne soit plus refusé en entier pour un extrait de
code réel recopié sur plusieurs lignes, et qu'un refus restant se comprenne
sans relancer le lot.

## Contexte

Le 12/11, trois lots de Vigie (tickets 080, 083, 084) ont été refusés en
entier, aucun fichier écrit, par la règle « preuve » (ADR-057). Les trois
extraits cités sont du vrai code, présent dans la matière fournie à l'agent
(diff ou fichier complet). Vérifié dans
`services/documentation/documentation_preuve.py` : l'agent et le contrôle
lisent bien la même `matiere`.

Les trois extraits portent sur plusieurs lignes (un objet JSON, une
docstring, deux lignes de commentaire). Le contrôle exige que l'extrait
aplati soit une sous-chaîne d'**un** bloc. Il ne tolère que les écarts de
blancs : une ligne reformatée, un `#` de début de ligne retiré, des
points de suspension, et tout l'extrait est refusé. Le message coupe l'extrait
à 60 caractères (`extrait.strip()[:60]`) et cache la partie qui a échoué.
Les exemples du prompt `agents/prompts/doc-technique.md` ne montrent que des
extraits d'une ligne, sans le dire.

## Solution proposée

1. Un extrait de plusieurs lignes est accepté quand **chacune** de ses
   lignes non vides, aplaties, figure dans un **même** bloc de la matière.
   Une ligne qui n'y figure pas refuse l'extrait, comme aujourd'hui.
2. Le refus cite la première ligne absente (jusqu'à 120 caractères), plus le
   début de l'extrait.
3. Les prompts `doc-technique.md` et `doc-fonctionnelle.md` demandent un
   extrait d'une seule ligne, recopiée telle quelle.

## Critères d'acceptation

- [ ] Un test : un extrait de trois lignes dont chaque ligne figure dans un
      même fichier fourni, mais séparées d'une ligne non citée, est accepté.
- [ ] Un test : un extrait de deux lignes dont la seconde n'est dans aucun
      bloc est refusé, et le message contient cette seconde ligne.
- [ ] Un test : deux lignes présentes chacune dans un bloc **différent**
      sont refusées.
- [ ] Un test : un extrait d'une ligne absent est refusé comme aujourd'hui.
- [ ] Un test lit les deux prompts et y trouve la consigne d'une seule ligne.
- [ ] Les tests existants de la preuve passent.

## Ce que ça ne fait pas

- N'assouplit pas la règle pour une ligne inventée ou modifiée : chaque
  ligne citée doit exister telle quelle, aux blancs près.
- Ne traite pas le `docs/architecture.md` de Vigie, qui dépasse le budget de
  60 000 caractères (`_BORNE_DOC`) : l'agent n'en voit que les titres. À
  voir dans un ticket à part si les refus « texte introuvable » de Vigie
  persistent.