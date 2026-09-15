# Guide utilisateur — vibe-ide

vibe-ide est un IDE qui fait travailler des **agents IA** sur tes projets. Tu décris
ce que tu veux sous forme de **tickets**, et une chaîne d'agents écrit le code, le
teste, l'audite, le relit, le valide et le committe — pendant que tu regardes.

Ce guide s'adresse à quelqu'un qui **utilise** vibe-ide. Pour comprendre comment il
est construit, va voir [`architecture.md`](architecture.md).

---

## Sommaire

1. [Installer et lancer](#1-installer-et-lancer)
2. [Ajouter un projet](#2-ajouter-un-projet)
3. [Écrire des tickets](#3-écrire-des-tickets)
4. [Lancer un agent sur un ticket](#4-lancer-un-agent-sur-un-ticket)
5. [Lire ce qui se passe](#5-lire-ce-qui-se-passe)
6. [Récupérer le travail des agents](#6-récupérer-le-travail-des-agents)
7. [Le mode autonome](#7-le-mode-autonome)
8. [Discuter avec l'agent](#8-discuter-avec-lagent)
9. [Les agents disponibles](#9-les-agents-disponibles)
10. [Intégration GitHub](#10-intégration-github)
11. [Configuration](#11-configuration)
12. [Problèmes fréquents](#12-problèmes-fréquents)

---

## 1. Installer et lancer

### Ce qu'il te faut

vibe-ide parle à Claude de deux façons — choisis-en une :

| Mode | Quand l'utiliser | Coût |
|------|------------------|------|
| **Abonnement Claude** (défaut) | Usage quotidien sur ta machine | Inclus dans ton abonnement |
| **Clef API Anthropic** | Docker, CI, serveur sans session interactive | Facturé au token |

En mode abonnement (`LLM_PROVIDER=agent_sdk`, la valeur par défaut) **tu n'as pas
besoin de clef API** : il te faut une session Claude Code authentifiée sur la
machine.

### Lancement le plus simple : Docker

```bash
cp .env.example .env
docker compose up --build
```

> En Docker il n'y a pas de session interactive : passe en `LLM_PROVIDER=anthropic_api`
> et renseigne `ANTHROPIC_API_KEY` dans `.env`.

### Lancement local

Prérequis : Python 3.11+ avec [uv](https://docs.astral.sh/uv/), Node.js 24 LTS.

```bash
make setup    # dépendances + création du .env
make run      # backend + frontend dans un seul terminal
```

Une fois lancé :

- **L'IDE** → <http://localhost:5173>
- **L'API et sa doc interactive** → <http://localhost:8000/docs>

Pour arrêter : `Ctrl+C`.

### Version desktop

```bash
make dev          # terminal 1 — le backend
make tauri-dev    # terminal 2 — la fenêtre native
```

---

## 2. Ajouter un projet

Un **projet** est un dossier contenant du code, des tickets et un `CLAUDE.md` qui
explique aux agents le contexte, la stack et les conventions. Tu as quatre façons
d'en obtenir un.

### Créer un projet from scratch

Sidebar → **Nouveau projet**. Tu décris ton idée en langage naturel, l'agent
*project-creator* génère la structure, le `CLAUDE.md` et les premiers tickets.

### Importer un projet existant de ta machine

Sidebar → **Importer un projet**. Deux modes :

- **copy** — vibe-ide copie le dossier dans son workspace. Ton original n'est jamais
  touché. **C'est le mode recommandé.**
- **symlink** — vibe-ide crée un lien vers ton dossier. Les agents modifient
  directement tes fichiers. Sous Windows, ce mode exige le **mode développeur** ou
  un lancement en administrateur.

> **Le chemin doit être absolu** : `C:\Users\moi\Desktop\mon-projet`, pas
> `mon-projet`. Si tu colles un chemin depuis l'explorateur Windows
> (« Copier en tant que chemin d'accès »), les guillemets sont retirés
> automatiquement.

> **Non, ton projet n'a pas besoin d'être rangé à côté de l'IDE.** Il peut être
> n'importe où sur ta machine : l'import le copie (ou le lie) vers le dossier
> workspace configuré par `IDE_WORKSPACE_DIR`.

### Cloner un dépôt GitHub

Sidebar → **Cloner un repo**. Colle l'URL, vibe-ide clone dans le workspace.

### Analyser un projet sans `CLAUDE.md`

Si le projet importé n'a pas de `CLAUDE.md`, lance l'agent *project-analyzer* : il
lit le code et rédige le `CLAUDE.md` à ta place. Relis-le — c'est le document que
**tous** les agents liront avant chaque tâche.

---

## 3. Écrire des tickets

Un ticket est un **fichier Markdown**. Pas de base de données propriétaire : tu peux
les lire, les éditer et les versionner avec git, sans lancer l'IDE.

```
mon-projet/
  tickets/
    todo/          ← en attente
    in-progress/   ← le codeur travaille dessus
    in-review/     ← le reviewer relit
    done/          ← approuvé
    blocked/       ← bloqué (sécurité, ou 3 tours sans approbation)
```

### Anatomie d'un ticket

```markdown
---
id: ticket-007
title: "Ajouter un endpoint de santé"
type: feat          # feat | fix | chore | docs | refactor | test | design
status: todo
priority: high      # critical | high | medium | low
agent: codeur
depends_on: []
created: 2026-09-15
---

# ticket-007 — Ajouter un endpoint de santé

## Objectif

Une phrase : ce que ça doit faire, et pour qui.

## Contexte

Pourquoi c'est nécessaire. Ce qui existe déjà et pourquoi ça ne suffit pas.

## Critères d'acceptation

- [ ] `GET /health` renvoie 200 avec `{"status": "ok"}`
- [ ] Un test couvre le cas nominal
```

### Les critères d'acceptation comptent vraiment

Ce ne sont pas de la décoration : l'agent **validateur** les reprend un par un et
vérifie chacun contre le code produit. Un critère vague (« que ce soit propre »)
donne une validation vague. Un critère vérifiable (« `GET /health` renvoie 200 »)
donne une validation nette.

### Trois façons de créer un ticket

1. **À la main** — crée le fichier `.md` dans `tickets/todo/`.
2. **Depuis l'UI** — Sidebar → **Nouveau ticket**.
3. **Via le planificateur** — Sidebar → **Planifier une évolution**. Tu décris une
   évolution en langage naturel, l'agent découpe en plusieurs tickets cohérents,
   avec leurs dépendances. Tu relis et valides avant écriture.

---

## 4. Lancer un agent sur un ticket

Sélectionne un ticket dans le board, clique sur **Lancer le pipeline**.

Voici ce qui s'enchaîne :

```
1. git checkout -b ticket-007-ajouter-un-endpoint-de-sante
2. Codeur          → écrit réellement les fichiers
3. Testeur         → lance la suite de tests du projet
4. Sécurité        → audit OWASP du diff
5. Reviewer        → relit le diff
6. Validateur      → vérifie les critères d'acceptation un par un
7. Doc-updater     → met à jour README / docs / CLAUDE.md
8. git commit
```

Trois points importants :

- **Le codeur écrit vraiment sur le disque.** Il ne décrit pas le code, il le
  produit.
- **Ce que relisent les agents suivants, c'est le `git diff` réel** — pas le résumé
  du codeur. Ils valident l'implémentation, pas l'intention.
- **Chaque run a sa propre branche git.** Ton travail en cours n'est jamais écrasé.

### Si le reviewer n'est pas d'accord

Il renvoie `CHANGES_REQUESTED` avec sa raison, et le codeur repart pour un tour en
tenant compte du retour. Au bout de **3 tours** sans approbation, le ticket passe en
`blocked/` — et le travail produit est **quand même commité** (voir plus bas).

### Si l'audit de sécurité bloque

Une faille `CRITICAL` ou `HIGH` arrête le pipeline immédiatement : le ticket passe
en `blocked/` et le reviewer n'est même pas appelé.

---

## 5. Lire ce qui se passe

Le panneau **Agent Stream** montre le déroulé en direct via WebSocket : quel agent
tourne, ce qu'il écrit token par token, quels outils il utilise, et le verdict de
chaque étape.

Le panneau **Historique** liste tous les runs passés (persistés en SQLite), avec
leur durée, leur verdict et leur nombre de tours.

Les statuts que tu verras passer :

| Statut | Ce que ça veut dire |
|--------|---------------------|
| `in-progress` | Le codeur travaille |
| `in-review` | Le reviewer relit le diff |
| `done` | Approuvé et commité |
| `blocked` | Sécurité, 3 tours sans accord, ou arbre de travail sale |

---

## 6. Récupérer le travail des agents

**À chaque run, quel que soit le verdict, le travail est commité** sur la branche du
ticket. Rien n'est jamais perdu, et l'arbre de travail reste propre pour le ticket
suivant.

Deux messages de commit possibles :

| Verdict | Message |
|---------|---------|
| Approuvé | `feat: ticket-007 — Ajouter un endpoint de santé` (le type vient du ticket) |
| Non approuvé | `chore: ticket-007 — unapproved work (security block: ...)` |

Pour inspecter ce qu'un agent a produit :

```bash
cd <ton-projet>
git log --oneline --all           # voir toutes les branches de tickets
git show ticket-007-ajouter-un-endpoint-de-sante
git diff main..ticket-007-ajouter-un-endpoint-de-sante
```

Pour récupérer un travail approuvé :

```bash
git merge ticket-007-ajouter-un-endpoint-de-sante
```

> **La comptabilité de vibe-ide fait l'objet d'un commit séparé.** Les changements de
> statut de tickets et le journal de pipeline arrivent dans un commit
> `chore: vibe-ide pipeline bookkeeping`, jamais mélangés au travail du codeur.

---

## 7. Le mode autonome

`POST /api/v1/orchestrator/run-autonomous` enchaîne les tickets `todo/` tout seul,
par ordre de priorité, en respectant les dépendances.

Ce qu'il faut savoir avant de le lancer :

- **Chaque ticket approuvé devient la base du suivant.** Un plan de tickets
  séquentiels s'empile donc correctement.
- **Un ticket rejeté ne contamine pas le suivant.** Son travail reste sur sa branche,
  et le ticket d'après repart de la dernière base approuvée.
- **Un ticket bloqué ne gèle pas la file.** Il passe en `blocked` et l'orchestrateur
  passe au suivant.

Le run s'arrête aussi de lui-même s'il atteint `RUN_MAX_BUDGET_USD` (5 $ par
défaut) : le plafond est vérifié **entre** deux tickets, jamais au milieu d'un,
pour qu'aucun travail ne reste non commité.

Commence par des lots courts (`max_tickets: 3`) le temps de calibrer la qualité de
tes tickets.

---

## 8. Discuter avec l'agent

Le panneau de droite a deux onglets : **Agents**, qui observe un run de
pipeline, et **Chat**, où tu discutes librement du projet.

Le chat n'est pas un pipeline. Il sert à décider **quoi** ticketiser, à
comprendre un bout de code, à faire une modification ponctuelle — sans passer
par le cycle complet codeur → reviewer → validateur.

### Ce que l'agent peut faire

- Lire n'importe quel fichier du projet, chercher dedans
- Écrire et modifier des fichiers, y compris créer des tickets
- Lire le `CLAUDE.md`, les tickets ouverts et les ADR du projet

### Ce qu'il ne peut pas faire

- **Exécuter des commandes** — aucun outil shell ne lui est donné
- Lancer un pipeline lui-même : il peut le suggérer, tu décides

### Ses écritures sont commitées, pas laissées en vrac

Quand l'agent modifie des fichiers, son travail est **commité automatiquement**
sur une branche `chat-<horodatage>`, jamais sur ta branche courante. Deux
raisons :

1. Tu peux inspecter, récupérer ou jeter son travail sans rien risquer :
   `git show chat-20260915-143000`
2. L'arbre de travail reste propre. Sinon, le prochain ticket que tu lances
   partirait en `blocked` sans qu'aucun agent n'ait tourné.

Un échange purement conversationnel ne crée ni branche ni commit.

### Le coût est affiché

En haut du panneau : `0.250 / 2.00 $`. C'est le cumul de **cette
conversation**, et son plafond. Atteint, la conversation refuse de continuer —
ouvre-en une nouvelle, ou relève `CHAT_MAX_CONVERSATION_USD`.

> Le garde-fou `LLM_MAX_BUDGET_USD` borne **un appel**. Sans ce second plafond,
> une longue discussion épuiserait ton quota sans que rien ne le montre.

La conversation survit à un rechargement de la page.

---

## 9. Les agents disponibles

| Agent | Rôle |
|-------|------|
| `codeur` | Implémente le ticket, écrit les fichiers |
| `reviewer` | Relit le diff, approuve ou demande des changements |
| `testeur` | Lance la suite de tests du projet (pytest / npm / cargo) |
| `securite` | Audit OWASP du diff — bloque sur CRITICAL/HIGH |
| `validateur` | Vérifie les critères d'acceptation un par un |
| `doc-updater` | Met à jour README, docs et `CLAUDE.md` après approbation |
| `chat` | Discute du projet, lit et écrit ses fichiers (onglet Chat) |
| `planificateur` | Découpe une évolution décrite en langage naturel en tickets |
| `architect` | Intervient sur les tickets de type `design` |
| `project-creator` | Crée un projet de zéro par conversation |
| `project-analyzer` | Génère un `CLAUDE.md` en lisant un code existant |
| `agent-creator` | Crée un nouvel agent sur mesure, par conversation |

Chaque agent est un **prompt Markdown** dans `agents/prompts/`. Tu peux les lire, les
modifier, et en ajouter — via **Sidebar → ⚙ Agents**, ou en déposant un fichier.

### Activer ou désactiver des étapes

Toutes les étapes ne sont pas obligatoires. La configuration du pipeline de chaque
projet permet de désactiver le testeur, la sécurité, le validateur ou le doc-updater,
et de régler `max_review_rounds`.

---

## 10. Intégration GitHub

Renseigne `GITHUB_TOKEN` et `GITHUB_REPO` dans `.env` pour débloquer :

- **Import d'issues** → chaque issue devient un ticket
- **Synchronisation bidirectionnelle** tickets ↔ issues
- **Création de PR** depuis un ticket terminé
- **Statut CI** de la PR remonté dans l'UI

---

## 11. Configuration

Tout est dans `.env` (copié depuis `.env.example`) :

| Variable | Défaut | À quoi ça sert |
|----------|--------|----------------|
| `LLM_PROVIDER` | `agent_sdk` | `agent_sdk` (abonnement) ou `anthropic_api` (crédits) |
| `ANTHROPIC_API_KEY` | — | Requis **uniquement** en mode `anthropic_api` |
| `LLM_MAX_TURNS` | `30` | Plafond d'allers-retours outil pour un agent |
| `LLM_MAX_BUDGET_USD` | `1.0` | Plafond de dépense d'un **seul** appel agent |
| `RUN_MAX_BUDGET_USD` | `5.0` | Plafond cumulé d'un **run autonome** (`0` = aucun) |
| `CHAT_MAX_CONVERSATION_USD` | `2.0` | Plafond de dépense d'une **conversation** du chat |
| `IDE_WORKSPACE_DIR` | `~/vibe-ide-workspace` | Où vivent tes projets |
| `IDE_PROMPTS_DIR` | `agents/prompts/` | Où vivent les prompts des agents |
| `IDE_LOG_LEVEL` | `INFO` | Verbosité des logs |
| `GITHUB_TOKEN` | — | Token GitHub |
| `GITHUB_REPO` | — | Dépôt cible, format `owner/repo` |
| `STATIC_TOKEN` | — | Si défini, l'API exige `Authorization: Bearer <token>` |

`LLM_MAX_TURNS` et `LLM_MAX_BUDGET_USD` sont tes garde-fous contre un agent qui part
en boucle. Ne les augmente qu'en connaissance de cause.

> **Si tu exposes vibe-ide sur un réseau**, définis `STATIC_TOKEN`. Sans lui l'API
> est ouverte — c'est acceptable en local, pas ailleurs.

---

## 12. Problèmes fréquents

### « Le dossier source n'existe pas : ...\backend\"C:\..." »

Ton chemin est relatif ou entouré de guillemets. Donne un chemin **absolu**. Les
guillemets sont désormais retirés automatiquement.

### « Impossible de créer le lien symbolique » (Windows)

Les symlinks demandent le **mode développeur** Windows ou un lancement en
administrateur. Le plus simple : réimporte en mode **copy**.

### Un ticket passe en `blocked` sans qu'aucun agent n'ait tourné

L'arbre de travail du projet était sale au démarrage. C'est un filet de sécurité :
quelque chose a modifié des fichiers **suivis** en dehors de vibe-ide. Committe ou
annule ces changements, puis repasse le ticket en `todo`.

### Le pipeline tourne mais rien ne change dans les fichiers

Vérifie `LLM_PROVIDER`. Seul le mode `agent_sdk` donne les outils fichier au codeur.

### Les agents ignorent mes conventions

Ils lisent le `CLAUDE.md` **du projet**. S'il est vide, générique, ou périmé, ils
travaillent à l'aveugle. C'est le fichier le plus rentable à soigner.

### Le reviewer refuse systématiquement

Tes critères d'acceptation sont probablement trop vagues, ou le ticket demande trop
de choses à la fois. Un ticket = un changement cohérent.

### Les tests échouent alors qu'ils passent chez moi

Le testeur lance la commande configurée dans le pipeline du projet, depuis la racine
du projet, avec un timeout de 120 s.

---

## Pour aller plus loin

- [`architecture.md`](architecture.md) — comment vibe-ide est construit
- [`ticket-strategy.md`](ticket-strategy.md) — comment découper un backlog
- `projects/ide-core/memory/decisions.md` — les ADR, dont **ADR-017** (couche LLM) et
  **ADR-018** (isolation git du pipeline)
