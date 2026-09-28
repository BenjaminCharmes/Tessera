---
id: ticket-105
title: "Un projet créé déclare son pipeline"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-104"]
estimated_days: 1
created: 2026-09-21
---

# ticket-105 — Un projet créé déclare son pipeline

## Objectif

Qu'un projet créé depuis l'IDE parte avec un `agents.json` complet et explicite,
plutôt qu'avec aucun fichier du tout.

## Contexte

`create_project` n'écrit `agents.json` **que si** `active_agents` est non vide.
Or la modale de création n'envoie que `project_id`, `name` et `description` :
un projet créé depuis l'UI n'a donc **aucun manifeste**.

Sans manifeste, `load_pipeline_config` rend un `AgentPipelineConfig()` par
défaut, où `testeur_enabled`, `securite_enabled` et `validateur_enabled` sont
faux. Les services correspondants sont pourtant déjà câblés dans le routeur :
ils sont seulement **éteints**. Le pipeline tombe à `codeur → reviewer`, et
rien ne le dit.

Le manifeste généré porte aussi `max_instances: 2` pour le codeur. Rien ne le
lit — le backend ne contient aucun `asyncio.gather`, le pipeline est
strictement séquentiel. C'est le même défaut que ticket-091 a nettoyé sur
`auto_merge_on_approve` : un réglage qu'on lit et qu'on croit.

## Solution proposée

1. Écrire le manifeste **toujours**, même sans `active_agents` — auquel cas il
   pose les rôles du pipeline par défaut, `codeur` et `reviewer`.
2. Y déclarer `pipeline` avec `max_review_rounds`, `securite_enabled: true`,
   `validateur_enabled: true`, plus `testeur_enabled` et `test_command`.
3. `autonomy: "commit"`. Le défaut protège (ADR-029) : on n'écrit pas `merge`
   dans un fichier généré.
4. `artifacts` : la valeur que rend déjà `default_mode_for("create")`, pour que
   le manifeste soit explicite au lieu de dépendre d'un défaut de lecture
   (ADR-023).
5. Retirer `max_instances`.

Ce ticket **ne touche pas** à `CLAUDE.md`.

## Critères d'acceptation

- [ ] Un projet créé **sans** `active_agents` a un `agents.json` valide, qui
      déclare `codeur` et `reviewer`
- [ ] `load_pipeline_config` sur ce projet rend `securite_enabled` et
      `validateur_enabled` à vrai
- [ ] `lire_niveau` sur ce projet rend `commit`
- [ ] `read_artifact_mode` rend la même valeur que `default_mode_for("create")`
- [ ] Le manifeste généré ne contient plus `max_instances`
- [ ] Aucune clef écrite n'est morte : un test vérifie que chaque clef du
      manifeste généré est lue quelque part
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

**`testeur_enabled` reste à faux**, avec `test_command: null`.

Un projet neuf n'a ni stack ni tests : aucune commande ne peut être devinée à
la création. Or un flag à vrai sans commande valide est **pire** qu'un flag à
faux — le lanceur avale l'erreur et rend `True`, si bien que l'absence de tests
se lirait comme des tests verts. C'est précisément la panne qu'un pipeline de
qualité doit éviter.

La commande se pose quand le projet a une stack, depuis le panneau Agents.

## Dépendances

ticket-104 — qui donne au projet créé son dépôt. Les deux touchent la création,
et celui-ci part de `develop` après le merge du précédent.

## Estimation

1 jour.

## Risques

Activer sécurité et validateur allonge chaque run de deux appels d'agent. C'est
le but : ils étaient éteints par accident, pas par choix. Un projet qui veut
s'en passer le déclare dans son manifeste, qui est désormais écrit et donc
modifiable.
