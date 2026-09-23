---
id: ticket-158
title: "Le testeur lance sur le lien symbolique et pas sur le vrai dossier"
type: fix
status: in-review
pr_number: null
priority: critical
agent: codeur
depends_on: ["ticket-157"]
estimated_days: 1
created: 2026-09-23
---

# ticket-158 — Le testeur lance sur le lien, pas sur le dossier

## Objectif

Qu'un projet atteint par un lien symbolique voie ses tests s'exécuter.

## Contexte

Second blocage du premier ticket du démineur, découvert juste après le
ticket-157. Le testeur démarrait enfin, et rendait :

```
Failed to load url C:/Users/.../Desktop/demineur/src/setup-tests.ts
(resolved id: …). Does the file exist?
```

Le fichier existait. La même commande, lancée à la main dans le même dossier
au même instant, passait — huit tests au vert.

`projects/` ne contient que des **liens symboliques** vers les vrais dépôts :
`projects/demineur` pointe sur `Desktop/demineur`. Lancé avec le chemin du
lien comme `cwd`, Vite résout sa racine sur le chemin réel tout en servant
depuis le lien, et ne retrouve plus son fichier de setup.

L'écart entre les deux exécutions venait de là : un shell résout le lien en
entrant dans le dossier, `create_subprocess_exec` le conserve tel quel.

### Ce que ça a coûté à mesurer

Deux tours de revue par run, sur trois runs. Le codeur a « corrigé » à chaque
fois l'import de `setup-tests.ts` — `@testing-library/jest-dom/vitest` vers
`@testing-library/jest-dom` — parce que c'est ce que le message d'erreur
désignait. Ce sous-chemin existe pourtant bien en 6.9.1 : l'agent a suivi un
message qui accusait le mauvais fichier.

## La règle qui existait déjà

ADR-017 pose « `cwd` résolu » comme invariant du provider, documenté dans
`services/providers/agent_sdk.py`. Il n'a jamais été appliqué au testeur.

Même forme qu'au ticket-157, pour la troisième fois de suite : une règle que
le dépôt connaît, tenue à un endroit et pas à l'autre.

## Solution proposée

`TestRunnerService.run_tests` résout `project_path` avant tout le reste. La
détection de commande et le lancement travaillent alors sur le vrai dossier.

## Critères d'acceptation

- [ ] Un projet atteint par un lien symbolique lance ses tests
- [ ] Un test vérifie que le `cwd` transmis au lancement est le chemin résolu,
      pas celui du lien (`@requires_symlinks`)
- [ ] `ticket-001` du démineur atteint le reviewer

## Dépendances

ticket-157.

## Estimation

Moins d'une journée.

## Risques

Résoudre un chemin change ce que voient les contrôles de périmètre. Ceux
d'ADR-031 résolvent déjà les deux côtés, symlinks compris : cette correction
les rejoint au lieu de s'en écarter.
