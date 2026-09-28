---
id: ticket-209
title: "Le validateur n'approuve que s'il a jugé chaque critère du ticket"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-209 — Le validateur juge chaque critère

## Objectif

Un ticket n'est validé que si chacun de ses critères d'acceptation a reçu un
verdict `passed: true` explicite. Un critère omis par le LLM compte comme
refusé.

## Contexte

`ValidatorService._parse_response` fait confiance au JSON rendu :

- le nombre de critères jugés n'est pas comparé à celui des critères envoyés ;
- `verdict` fourni par le LLM écrase `all_passed`. Un `"verdict": "APPROVED"`
  passe donc même quand `all_passed` est faux ou qu'un critère est à `false`.

Cas observé : sur un ticket `design` à onze critères, dont dix non cochés, le
validateur n'en a jugé que trois. Il a approuvé avec ce retour : « les autres
critères n'étaient pas identifiés comme restants par l'agent et sont présumés
satisfaits ». Parmi ces critères présumés, il y avait « la PR #1 est mergée »
et « la variable est posée sur Vercel », qui étaient faux.

ADR-039 demande que cette porte échoue fermée quand elle n'a pas pu juger.
Un critère qu'elle n'a pas jugé, c'est une porte qui n'a pas jugé.

## Solution proposée

1. Côté code, le verdict se **recalcule** : `APPROVED` si et seulement si
   chaque critère envoyé a un résultat `passed: true`. Le rapprochement se
   fait par position ou par texte normalisé, au choix de l'implémentation,
   pourvu qu'un critère absent de la réponse soit ajouté en `passed: false`
   avec la note « non jugé par le validateur ». Le `verdict` du LLM ne sert
   plus qu'à titre informatif, ou disparaît.
2. Côté prompt, `agents/prompts/validateur.md` dit qu'il faut rendre un objet
   par critère reçu, dans l'ordre, et qu'un critère hors de portée du diff
   (action humaine, état d'un service externe) est `passed: false`, avec une
   note qui le dit.

## Critères d'acceptation

- [ ] Un test : trois critères envoyés, deux jugés `true` dans la réponse →
      `verdict == "CHANGES_REQUESTED"` et le troisième figure en
      `passed: false`
- [ ] Un test : réponse `"verdict": "APPROVED"` avec un critère à
      `passed: false` → `verdict == "CHANGES_REQUESTED"`
- [ ] Un test : tous les critères jugés `true` → `APPROVED` (non-régression)
- [ ] `agents/prompts/validateur.md` exige un objet par critère reçu, et
      `passed: false` pour un critère invérifiable depuis le diff
- [ ] `uv run pytest` passe

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Les tickets `design` portent souvent des critères qui demandent un geste
humain (merger, poser une variable). Ils ne passeront plus sans ce geste.
C'est voulu, mais il faudra peut-être cocher ces cases à la main avant de
lancer, ou sortir ces critères du ticket.
