---
id: ticket-091
title: "Des consignes qui ne se contredisent pas, et un budget mesuré"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: [ticket-090]
estimated_days: 1
created: 2026-09-18
---

# ticket-091 — Revue de tout ce que les agents lisent

## Ce qui a été trouvé

### 1. Les deux fichiers `@`-importés se contredisaient sur git

`projects/ide-core/CLAUDE.md` enseignait :

```
gh pr create --base main …
gh pr merge --squash --auto
```

L'exact inverse du flux du dépôt — `ticket → develop → main`, avec un **merge
commit** vers `main`. Le skill `ticket-workflow` était juste, mais il se charge
à la demande : **la consigne fausse était toujours en contexte, la bonne
seulement parfois.**

Il portait aussi `GH_CONFIG_DIR=/Users/<moi>/.config/gh`, un chemin d'une autre
machine, dans un dépôt utilisé sur deux postes.

### 2. Deux réglages de pipeline ne réglaient rien

`pipeline.default` et `auto_merge_on_approve` n'étaient lus nulle part, et
`_default_agents_json` écrivait le second à `true` dans **chaque projet créé**.
Dans un produit dont toute la question récente est de savoir qui a le droit de
merger, un réglage nommé « merge automatique » qui ne fait rien est pire
qu'absent : on le lit, et on le croit.

### 3. `CLAUDE.md` décrivait un dépôt imaginaire

`.claude/settings.json` n'existe pas. L'« État actuel » s'était arrêté à la
phase 7 ; on est au ticket 091. `projects/ide-core/CLAUDE.md` portait soixante
lignes d'archive de phases — du travail terminé, payé à **chaque** session.

### 4. Douze ADR sur trente et un dépassaient leur budget

Dont trois écrits le jour même où le skill `write-adr` rappelait ce budget.

## Critères d'acceptation

- [x] Une règle n'est décrite qu'à un endroit ; les autres renvoient à elle
- [x] Aucun chemin de machine dans un fichier de consigne
- [x] `pipeline.default` et `auto_merge_on_approve` retirés, sans casser les
      `agents.json` existants qui les portent encore
- [x] `CLAUDE.md` décrit ce qui existe, et dit ce qui **n'existe pas**
- [x] L'archive de phases est remplacée par ce qui sert avant d'ouvrir un
      ticket
- [x] Zéro ADR au-dessus de 160 mots
- [x] ADR-022 est marquée comme amendée par ADR-029 — elle énonçait encore
      « aucun appel ne merge », faux depuis ticket-082
- [x] `test_consignes_coherentes.py` verrouille les cinq points
- [x] Le skill `ticket-workflow` distingue ce que je fais à la main de ce que
      le produit livre tout seul
- [x] ADR-034 écrite

## Ce que ça ne fait pas

**Le pipeline de `ide-core` reste à deux agents.** Testeur, sécurité,
validateur et doc-updater sont désactivés sur ce projet, et le `CLAUDE.md` le
dit maintenant au lieu de laisser croire le contraire. Les activer demande un
`test_command` qui atteigne `../../backend` sans passer par un shell —
`TestRunnerService` lance sa commande depuis le dossier du projet avec
`create_subprocess_exec`. C'est un ticket à part, et un choix de coût qui
revient à l'utilisateur.
