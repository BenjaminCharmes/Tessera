---
id: ticket-048
title: "Chat conversationnel avec outils dans l'IDE"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 4
created: 2026-09-15
---

# ticket-048 — Chat conversationnel avec outils

## Objectif

Un panneau de chat dans l'IDE pour **discuter d'un projet et le faire avancer**,
comme dans Claude Code : l'agent a le contexte du projet, lit et écrit des
fichiers, crée des tickets, lance un pipeline — et streame ses réponses.

## Contexte

vibe-ide ne sait aujourd'hui converser que dans trois modales fermées et
mono-tâches : création d'agent, création de projet, planification d'évolution.
Rien ne permet d'ouvrir une discussion libre sur un projet — alors que c'est le
mode d'interaction le plus naturel pour décider *quoi* ticketiser avant de
lancer la machine à tickets.

## Solution proposée

### Backend

- **`ChatService`** — tient une conversation multi-tours, s'appuie sur
  `get_provider(allow_tools=True)` (ADR-017). Ne pas créer un second chemin
  d'appel LLM : toute la couche provider existe déjà.
- **`WS /api/v1/projects/{id}/chat`** — streaming des tokens et des appels
  d'outil, sur le modèle exact du stream orchestrateur existant
  (`OrchestratorEvent` → réutiliser les types `agent_token` / `agent_tool_use`).
- **Persistance SQLite** — une table `chat_messages` adossée au schéma
  existant, pour que la conversation survive au rechargement de la page.
- **Contexte projet** — réutiliser le `_build_project_context` des routers
  (CLAUDE.md, agents actifs, tickets ouverts, décisions récentes). Attention :
  ce contexte est déjà volumineux, ne pas le renvoyer intégralement à chaque
  tour d'une conversation longue.

### Frontend

- Panneau latéral redimensionnable, coexiste avec l'Agent Stream (ne le
  remplace pas : l'un est conversationnel, l'autre observe un run)
- Rendu Markdown des réponses, appels d'outil affichés repliés
- Historique par projet, reprise de conversation

### Outils exposés

Démarrer **volontairement restreint**, élargir ensuite :

| Outil | Statut |
|-------|--------|
| Lecture de fichiers, recherche | ✅ v1 |
| Écriture / édition de fichiers | ✅ v1 |
| Création et modification de tickets | ✅ v1 |
| Lancement d'un pipeline | ⏸ v2 |
| Exécution de commandes shell | ❌ hors périmètre (surface d'attaque) |

## Le point dur : cohabitation avec l'isolation git

C'est le vrai sujet de conception, à trancher **avant** de coder.

ADR-018 garantit qu'un run de pipeline part d'un arbre propre et commite tout
son travail sur la branche du ticket. Un chat qui écrit dans l'arbre de travail
casse cette garantie : au run suivant, `is_clean()` échoue et le ticket part en
`blocked` sans qu'aucun agent n'ait tourné.

Trois pistes, à arbitrer dans un ADR-019 :

1. **Le chat commite lui-même** sur une branche `chat/<horodatage>`, comme un
   run. Cohérent avec ADR-018, mais multiplie les branches.
2. **Le chat n'écrit que hors de l'arbre suivi** (tickets, `memory/`) et
   propose un diff à appliquer pour le reste. Plus sûr, moins direct.
3. **Le chat pose un verrou** pendant qu'il écrit, et le pipeline refuse de
   démarrer tant qu'il est posé. Simple, mais sérialise tout.

## Coût

Chaque tour est un appel agent facturé sur l'abonnement. `LLM_MAX_BUDGET_USD`
(défaut 1.0) borne **un appel**, pas une conversation : prévoir un plafond par
conversation et l'afficher dans l'UI, sinon une longue discussion consomme le
quota sans que personne ne le voie.

## Critères d'acceptation

- [ ] Un panneau de chat est accessible depuis un projet ouvert
- [ ] Les réponses sont streamées token par token via WebSocket
- [ ] Les appels d'outil sont visibles dans le fil, repliés par défaut
- [ ] L'agent lit et écrit réellement des fichiers du projet
- [ ] L'agent peut créer un ticket valide au regard des enums du modèle
- [ ] La conversation survit à un rechargement de la page
- [ ] **Une écriture par le chat ne fait pas passer le ticket suivant en
      `blocked`** (la piste retenue en ADR-019 est implémentée et testée)
- [ ] Le coût cumulé de la conversation est visible dans l'UI
- [ ] Aucun outil shell n'est exposé
- [ ] ADR-019 documente l'arbitrage de cohabitation git

## Dépendances

Aucune technique, mais à ne pas mener en parallèle de
[ticket-046](ticket-046-decomposer-orchestrator.md) : les deux touchent la
couche d'événements.

## Estimation

**4j** — 1j de conception (ADR-019), 2j backend, 1j frontend.

## Risques

- **Élevé sur la cohabitation git** — c'est le point qui peut casser le
  pipeline existant. Mitigation : trancher l'ADR-019 et écrire le test de
  non-régression *avant* d'exposer le moindre outil d'écriture.
- **Moyen sur le coût** — une conversation longue est un multiplicateur de
  tokens silencieux. Mitigation : plafond par conversation, visible.
