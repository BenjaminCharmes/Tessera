---
id: ticket-047
title: "Skills locaux : supprimer la dépendance aux plugins"
type: chore
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-15
---

# ticket-047 — Skills locaux, zéro dépendance plugin

## Objectif

Rendre le dépôt **autonome** : la discipline de travail et les workflows propres
à vibe-ide vivent dans `.claude/skills/`, versionnés avec le code, au lieu de
dépendre de plugins installés sur une machine.

## Contexte

Aujourd'hui `.claude/` ne contient que `settings.local.json`. **Aucun skill
local**, ni dans le projet ni dans `~/.claude/skills/`. Tout vient de plugins
(superpowers, claude-mem, planning-with-files). Conséquences :

- Un collègue qui clone le dépôt n'a rien de tout ça
- Les workflows propres à vibe-ide (lancer l'app, créer un ticket, ouvrir une
  PR, écrire un ADR) ne sont écrits nulle part — ils sont re-devinés à chaque
  session, et c'est exactement ce qui a produit les tickets 044 et 045 sans
  fichier de ticket
- Une mise à jour de plugin peut changer le comportement sans qu'on le décide

## Périmètre

### Noyau process (repris des plugins, réécrits en local)

| Skill | Rôle |
|-------|------|
| `brainstorming` | Explorer l'intention avant toute création de feature |
| `test-driven-development` | RED → GREEN → REFACTOR, test avant implémentation |
| `code-review` | Relire un diff : correction d'abord, simplification ensuite |
| `verification-before-completion` | Preuve avant toute affirmation de complétude |
| `writing-plans` | Passer d'une spec à un plan d'implémentation |

### Métier vibe-ide (spécifiques, inexistants ailleurs)

| Skill | Rôle |
|-------|------|
| `run-vibe-ide` | ✅ **déjà écrit** — lancer/vérifier/arrêter, pièges inclus |
| `new-ticket` | Créer un ticket au bon format, avec des critères vérifiables |
| `ticket-workflow` | branche → commits → push → PR → merge |
| `write-adr` | Écrire un ADR au format maison (46–72 mots), pas une mini-spec |

## Contraintes

1. **Format** : `.claude/skills/<nom>/SKILL.md`, frontmatter `name` +
   `description`. La `description` doit dire **quand** déclencher le skill, pas
   ce qu'il contient — c'est elle seule qui décide de son chargement.
2. **Chargement à la demande**, jamais par `@`-import dans `CLAUDE.md` : un
   import est payé à chaque session, un skill seulement quand il sert.
3. **`write-adr` doit borner la longueur.** ADR-017 et ADR-018 ont été écrits à
   448 et 571 mots contre 46–72 pour les seize précédents, et
   `memory/decisions.md` est injecté **en entier** dans le contexte de chaque
   appel d'agent (`routers/orchestrator.py`, `routers/agents.py`) : un ADR long
   est un coût par appel, pas seulement un défaut de style.
4. **`CLAUDE.md` ne peut pas être modifié sans ticket explicite** (règle 4).
   Ce ticket **est** cette autorisation, pour la seule section décrivant
   `.claude/skills/`.
5. **Ne pas déplacer `memory/decisions.md`** : le backend le lit à ce chemin.
6. **Ne pas déplacer `agents/prompts/`** dans `.claude/` : ce sont les prompts
   du *produit*, chargés par FastAPI, pas des sous-agents Claude Code.

## Hors périmètre

`claude-mem` et `mempalace` sont des **serveurs MCP**, pas des skills : ils ne
sont pas réécrivables en local et restent des dépendances externes assumées.

## Veille

Les skills des plugins restent installés comme **source d'inspiration**. Quand
l'un évolue de façon intéressante, on fait évoluer le nôtre — on ne revient pas
à la dépendance.

## Critères d'acceptation

- [x] `.claude/skills/` contient les 9 skills, chacun en `<nom>/SKILL.md`
- [x] Chaque frontmatter a `name` et une `description` formulée en « Use when… »
- [x] Chaque skill tient en moins de 200 lignes
- [x] `write-adr` impose explicitement le format maison et une borne de longueur
- [x] `new-ticket` produit un frontmatter valide au regard de `TicketType`,
      `TicketStatus` et `TicketPriority`
- [x] `ticket-workflow` couvre le cas qui a échoué sur ticket-045 : brancher,
      committer, **pousser**, ouvrir la PR
- [x] `CLAUDE.md` décrit `.claude/skills/` et la règle « skill à la demande,
      pas d'`@`-import »
- [x] Un clone neuf du dépôt dispose des 9 skills sans installer de plugin

## Dépendances

Aucune.

## Estimation

**2j**.

## Risques

- **Faible** — aucun code produit n'est touché. Le risque réel est un skill dont
  la `description` ne déclenche jamais : la vérifier en situation, pas seulement
  la relire.
