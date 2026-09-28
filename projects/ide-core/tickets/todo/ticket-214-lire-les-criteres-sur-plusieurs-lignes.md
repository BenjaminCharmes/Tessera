---
id: ticket-214
title: "Un critère d'acceptation écrit sur plusieurs lignes est lu en entier"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-214 — Lire les critères sur plusieurs lignes

## Objectif

Le validateur reçoit chaque critère d'acceptation en entier, y compris quand
le ticket le coupe sur plusieurs lignes.

## Contexte

`_extract_criteria` (`services/pipeline_text.py`) ne garde que la ligne qui
porte la case `- [ ]`. Les lignes de continuation, indentées, sont ignorées.
Or les tickets de ce dépôt coupent leurs critères à 80 colonnes : sur un
critère comme

```
- [ ] Aucun second script de termes interdits n'est créé à côté de
      `scripts/check-forbidden-terms.mjs`
```

le validateur n'a reçu que la première ligne, et a répondu : « La description
du critère est incomplète ». Depuis le ticket-209, un critère que le
validateur ne peut pas juger fait refuser le run. Un critère tronqué devient
donc un refus injuste.

## Solution proposée

Une ligne qui suit un critère, indentée et sans nouvelle case, prolonge ce
critère. On la rattache avec une espace. Une ligne vide ou une nouvelle case
termine le critère.

## Critères d'acceptation

- [ ] Un test : un critère sur deux lignes (seconde indentée) donne une seule entrée avec le texte des deux
- [ ] Un test : deux critères d'une ligne chacun donnent deux entrées (non-régression)
- [ ] Un test : une ligne vide après un critère ne le prolonge pas
- [ ] Les critères cochés `- [x]` sont lus de la même façon
- [ ] `uv run pytest` passe

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Un paragraphe indenté placé sous la liste pourrait être pris pour une
continuation. La règle « indentée, et juste après un critère » le limite.
