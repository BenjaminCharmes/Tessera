---
id: ticket-126
title: "Remettre d'équerre les prompts d'agents, les ADR et les skills"
type: docs
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-125"]
estimated_days: 1
created: 2026-09-22
---

# ticket-126 — Remettre d'équerre les prompts d'agents, les ADR et les skills

## Objectif

Que la couche de consignes — prompts produit, `decisions.md`, skills et
commandes Claude Code — dise ce que le code fait, sans doublon ni renvoi mort,
et que les agents ne reçoivent que ce qui les contraint.

Ce ticket **autorise explicitement** l'édition de `.claude/skills/*`,
`.claude/commands/*`, `agents/prompts/*` et `projects/ide-core/memory/decisions.md`.
Il n'autorise pas la modification de `CLAUDE.md`.

## Contexte

Relecture du 2026-09-22, après ticket-125 (codeur, reviewer, project-creator
déjà réécrits).

**Prompts produit**
- `architect.md` date d'avant ADR-017/018/032/034 : « documenter les ADR »
  sans budget ni portée (un ADR de 300 mots casse la CI du run suivant),
  « répondre à l'Orchestrateur » (rôle sans prompt), aucune section « Statut
  suggéré », ne sait pas qu'il écrit sur disque et que le diff est relu.
- `planificateur.md` : `type` sans `docs|test|design`, `agent` avec
  `architect` alors que seul `design` le route (`_role_qui_produit`) → un
  plan d'architecture produit un ticket `feat` confié au codeur.
- `validateur.md` / `securite.md` disent « le code » : c'est un **diff
  tronqué** (8 000 / 16 000 caractères). `validator.py` a `max_tokens=1024`,
  insuffisant pour 10 critères avec une `note` chacun → JSON tronqué →
  `CHANGES_REQUESTED` « non parseable ».
- `agent-creator.md` : le prompt généré n'hérite d'aucune règle maison
  (aucune trace d'IA, pas de git en écriture).
- `project-creator.md` : le JSON n'a pas de `description`, mais
  `project_creator.py:80` la lit → bootstrap des agents avec description vide.
- `doc-fonctionnelle.md` : `apres_section` accepté par le parseur mais non
  documenté (il l'est dans doc-technique).
- `resolveur_conflit.py:59-68` recopie dans le ticket les trois règles déjà
  dans le prompt (ADR-034).
- Le reviewer reçoit tous les outils du codeur (`Write`, `Edit`, `Bash`)
  via `AgentRunner` ; son prompt dit « tu ne modifies rien ».

**ADR**
- ADR-008 : « zéro lock à gérer » — faux depuis `RunLock` (ADR-038).
- ADR-015 amendé par ticket-125 : vérifier.
- ADR-014 porte `testeur`, rôle qui n'appelle jamais de modèle.
- Portée manquante sur des ADR d'histoire pure : ADR-001, 003, 036 ; et sur
  les méta-règles ADR-032, 034, 035 (concernent `architect`).
- `test_adr_pertinents.py:102-106` n'interdit une portée que sur ADR-017→031 ;
  ADR-033, 037, 038, 039, 040 sont des contraintes non protégées.
- `routers/chat.py:79` titre la section `## Décisions d'architecture`, que
  `adr.py` ne reconnaît pas : le chat reçoit le fichier entier.
- Préambule de deux phrases : ne dit pas qu'un ADR sans portée est une
  contrainte pour tous ni que l'ordre est celui d'écriture.
- `agent_registry.MomentAgent` docstring : « personne ne charge architect »,
  périmé depuis ticket-098.

**Skills et commandes**
- `brainstorming` renvoie à `systematic-debugging` (plugin, absent d'un
  clone neuf) ; l.35 liste des fichiers en les appelant « chemins en dur ».
- `new-ticket` cite la « règle 4 » pour CLAUDE.md : c'est la règle 5.
- `code-review` : « injecté à chaque appel — `routers/agents.py` » ; c'est
  aussi `orchestrator.py` et `chat.py`, et filtré par `adr.py`.
- `ticket-workflow` recopie la règle d'attribution IA de CLAUDE.md, dit deux
  fois `git add -A`, recopie les commandes de
  `verification-before-completion` ; l.100-110 est un récit.
- `verification-before-completion` : « une seule commande » puis « les
  commandes » ; la phrase-clé l.40 flotte ; histoire de ticket-067 dans un
  bloc de code.
- `writing-plans` exige un ticket avant ; `brainstorming` place `new-ticket`
  après `writing-plans` : trancher (le ticket d'abord).
- `write-adr` : ajouter `routers/chat.py` aux injecteurs ; dire que la liste
  verrouillée s'arrête à ADR-031.
- `run-tessera` : renvoyer à `tessera.ps1 run|stop` plutôt que décrire le
  contournement Windows à la main.

## Solution proposée

1. **Prompts** : réécrire `architect.md` sur le contrat outils/diff (même
   forme que `codeur.md`), avec budget ADR et portée, section « Statut
   suggéré ». Aligner `planificateur.md` (`design` ⇔ `architect`, tous les
   `TicketType`). « Diff, éventuellement tronqué » dans validateur/securite ;
   `validator.py` `_MAX_TOKENS` 1024 → 2048. `agent-creator.md` : exiger les
   deux rappels maison dans tout `system_prompt` généré. `project-creator.md` :
   champ `description`. `doc-fonctionnelle.md` : documenter `apres_section`.
   `resolveur_conflit.py` : ne garder que la liste des fichiers.
2. **Reviewer en lecture seule** : `AgentRunner` passe `allowed_tools`
   `["Read", "Glob", "Grep"]` pour le rôle `reviewer` (ADR-017 : `tools` et
   `allowed_tools` explicites), avec test.
3. **ADR** : amender ADR-008 (une ligne), retirer `testeur` d'ADR-014, poser
   `**Portée** : architect` sur ADR-001, 003, 032, 034, 035, 036 ; étendre
   `interdits` de `test_adr_pertinents.py` à ADR-033→040 ; préambule de
   trois lignes ; `routers/chat.py` titre `## Décisions récentes` pour
   bénéficier du filtrage ; docstring `MomentAgent`.
4. **Skills** : appliquer chaque correction listée ; dédoublonner
   `ticket-workflow` par renvois ; réordonner
   `verification-before-completion` (principe → `verify` → pièges →
   rapport).

Hors périmètre : `analyste-carriere.md`, `CLAUDE.md`, découpage de fichiers.

## Critères d'acceptation

- [ ] `grep -n "Orchestrateur" agents/prompts/architect.md` vide ;
      `architect.md` mentionne le budget de 160 mots et « Statut suggéré »
- [ ] `planificateur.md` liste `design` dans `type` et lie `design` à
      `architect`
- [ ] Test : `AgentRunner` construit le provider du `reviewer` avec
      `allowed_tools == ["Read", "Glob", "Grep"]`
- [ ] `grep -n "_MAX_TOKENS = 2048" backend/src/tessera/services/validator.py`
- [ ] `test_adr_pertinents.py` : une portée sur ADR-033→040 fait échouer le
      test ; ADR-001, 003, 032, 034, 035, 036 portent une portée
- [ ] Test : le contexte du chat passe par `adr_pertinents` (section
      `## Décisions récentes`)
- [ ] `grep -rn "systematic-debugging" .claude/skills` vide ;
      `grep -n "règle 4" .claude/skills/new-ticket/SKILL.md` vide
- [ ] `uv run pytest -q` (dont `test_consignes_coherentes.py`,
      `test_adr_pertinents.py`, `test_agents_livres.py`) et `uv run mypy src/`
      verts

## Dépendances
ticket-125.

## Estimation
1 jour.

## Risques
Poser une portée retire l'ADR des prompts codeur/reviewer : ne le faire que
sur des ADR qui n'énoncent aucune contrainte de comportement.

## Ce que ça ne fait pas

- **`CLAUDE.md` et `analyste-carriere.md`** ne bougent pas : hors périmètre
  explicite. La règle 5 exige un ticket dédié pour le premier.
- **Le reviewer garde `Bash` hors de portée, mais rien ne lui interdit de
  lire hors du projet** : lire ailleurs est permis à tous (ADR-031), c'est
  voulu.
- **Le chat lit les ADR sous un rôle `chat` qu'aucun ADR ne nomme** : il
  reçoit toutes les contraintes et aucun choix passé. Un ADR qui voudrait
  viser le chat devra l'écrire dans sa portée.
- **Les listes de `test_adr_pertinents.py` restent écrites à la main** : un
  ADR nouveau doit y être rangé le jour où il est écrit. Le skill `write-adr`
  le dit ; rien ne le mesure encore automatiquement.
- **`_MAX_TOKENS = 2048` n'est honoré que par `anthropic_api`** : le provider
  `agent_sdk` n'a pas de plafond de sortie équivalent, donc la troncature
  n'était un risque que dans ce mode-là.
- **Le validateur et l'audit reçoivent toujours un diff tronqué** (8 000 /
  16 000 caractères) : le prompt le dit désormais, il ne le change pas.
