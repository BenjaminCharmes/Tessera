---
id: ticket-256
title: "The run view shows every pipeline stage: a stage strip and one log line each"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-255"]
estimated_days: 1
created: 2026-09-30
---

# ticket-256 — La vue du run montre chaque étape du pipeline

## Objectif

Qu'en regardant la supervision, on sache quelle étape tourne, lesquelles sont
finies et lesquelles restent, sans jamais voir un écran figé.

## Contexte

Le ticket-255 fait émettre au backend un début et une fin pour chaque étape, et
expose `etape` dans l'instantané du run. Rien ne les affiche encore :

- `components/BottomPanel/index.tsx` (`eventToLine`) ne traduit que les agents,
  les statuts, la livraison, l'échec de documentation et les erreurs.
  `security_audit_started`, `security_audit_done`, `validation_done` et
  `doc_updated` tombent dans `default: return null`.
- Le panneau Agents (`components/AgentPanel/`) ne connaît que deux rôles,
  `codeur` et `reviewer` (`blocsDuPanneau.ts`). Constaté en réel : une fois le
  reviewer lancé, le bloc codeur n'est plus visible, et après le reviewer plus
  rien ne bouge alors que validation, documentation et livraison tournent.

## Solution proposée

- **Log** : une ligne par événement d'étape dans `eventToLine` —
  `security_audit_started` / `_done` (verdict si présent dans `data`),
  `validation_started` / `validation_done` (approuvé ou non),
  `documentation_started` / `doc_updated`, `livraison_started`.
- **Frise d'étapes** : un composant `StageStrip` en tête du panneau Agents, une
  pastille par étape **active sur ce projet** — production, sécurité, revue,
  validation, documentation, livraison. Trois états : faite, en cours, à venir.
  L'étape en cours se déduit d'abord de `etape` dans l'instantané, puis des
  événements (même principe que `blocsDuPanneau` : l'état décide, les
  événements enrichissent).
- Couleurs ADR-026 : `blue` pour l'étape en cours, `green` pour une étape
  faite, `red` pour un refus (audit `BLOCK`, validation refusée), `zinc` pour
  une étape à venir. Pas de violet en texte. Les glyphes viennent de
  `design/icons.tsx`.
- Les blocs codeur et reviewer restent tels quels : la frise s'ajoute au-dessus,
  elle ne les remplace pas.

## Critères d'acceptation

- [ ] `eventToLine` renvoie une ligne non nulle pour `security_audit_started`,
      `security_audit_done`, `validation_started`, `validation_done`,
      `documentation_started`, `doc_updated` et `livraison_started` (test).
- [ ] `StageStrip` existe dans `components/AgentPanel/` et affiche l'étape
      `validation` comme en cours quand l'instantané porte
      `etape: "validation"`, sans aucun événement reçu (test).
- [ ] Après `validation_started` puis `validation_done` approuvé, la pastille
      validation passe à l'état « faite » (test).
- [ ] Une étape que le projet n'active pas (sécurité désactivée par exemple)
      n'a pas de pastille (test).
- [ ] Aucune classe `text-violet-*` et aucun `<svg>` hors de `design/` ne sont
      ajoutés (les tests de cohérence existants le vérifient).

## Dépendances

ticket-255 — les événements et le champ `etape`.

## Estimation

1 jour. Frontend uniquement.

## Risques

- Le champ `etape` doit être ajouté au type TypeScript de l'instantané de run :
  vérifier où il est déclaré (`types/api.ts`) et l'y ajouter en optionnel.
- Savoir quelles étapes sont actives demande la configuration du pipeline
  (`PipelineReglages` : `securite_enabled`, `validateur_enabled`,
  `testeur_enabled`). La lire là où elle est déjà chargée, sans nouvel appel.
