# Migration vers le Claude Agent SDK — design

Date : 2026-09-14
Statut : validé, spike d'authentification concluant, prêt pour plan d'implémentation

## Résultats du spike (phase 1 — terminée)

`claude-agent-sdk` 0.2.152, exécuté sans `ANTHROPIC_API_KEY` dans l'environnement.

| Vérification | Résultat |
|---|---|
| Appel abouti sans clé API | **OK** — l'hypothèse centrale est confirmée, le repli sur le CLI est écarté |
| Écriture de fichier par l'agent | OK, sous conditions (ci-dessous) |
| `CLAUDE.md` du `cwd` respecté | OK |
| Détail tokens / coût par appel | OK, via `ResultMessage.usage` (dict) et `total_cost_usd` |
| Télémétrie de quota officielle | OK, via `RateLimitEvent` |

Quatre enseignements qui modifient le design :

1. **`allowed_tools` doit être explicite.** `permission_mode="acceptEdits"` seul
   ne suffit pas : les écritures ont été refusées et listées dans
   `ResultMessage.permission_denials`. Il faut passer nommément
   `["Read", "Write", "Edit", "Bash", "Glob", "Grep"]`.
2. **Le `cwd` doit être un chemin long résolu.** Un chemin court Windows 8.3
   (`BENJAM~1.CHA`) fait refuser les écritures et gaspille des tours pendant que
   l'agent résout le chemin lui-même. `Path.resolve()` est obligatoire avant de
   passer `cwd`.
3. **Le quota est observable officiellement.** Le SDK émet un `RateLimitEvent`
   portant un `RateLimitInfo` : `status` (`allowed` / `allowed_warning` /
   `rejected`), `utilization` (0.0–1.0), `rate_limit_type` (la fenêtre
   concernée), `resets_at`. La réserve émise en conception est levée : le suivi
   de quota s'appuie sur des chiffres officiels, non sur une estimation locale.
4. **Le coût réel impose de la discipline.** Créer un `hello.py` trivial a
   consommé l'équivalent de 0,18 à 0,25 USD, dominé par 70 000 à 110 000 tokens
   de lecture de cache. Un pipeline à six agents sur trois tours se chiffre donc
   en unités de dollars-équivalents de quota. D'où : modèle choisi par agent
   (Sonnet par défaut, Opus à la demande), `max_budget_usd` en garde-fou, et
   pipeline réduit par défaut.

## Problème

Deux défauts distincts, qui se corrigent par le même changement.

**Les agents ne peuvent rien écrire.** Chaque agent est un appel unique à
`messages.create` sans `tools` (`services/agent_runner.py:139` et `:161`). Aucun
tool use n'existe dans le backend. Le codeur produit donc du code en Markdown
dans un stream ; rien ne l'écrit sur le disque. En conséquence le reviewer relit
une intention, le testeur lance les tests sur du code jamais écrit, le validateur
et l'auditeur sécurité valident du vide. Le pipeline est correctement câblé
mais tourne au-dessus du néant.

**Le projet ne démarre pas.** La facturation passe par l'API Messages, qui exige
des crédits prépayés. Aucun crédit n'est disponible. `Settings.anthropic_api_key`
est en outre déclaré sans valeur par défaut (`config.py:9`), donc le backend
refuse même de booter.

## Décisions

| Sujet | Décision |
|---|---|
| Périmètre | Tous les agents passent sur le Claude Agent SDK. Sortir de l'API n'est pas un confort mais la condition pour que le projet fonctionne. |
| Distribution | vibe-ide reste strictement personnel. Voir « Contrainte de licence ». |
| Architecture | Couche `LLMProvider` derrière `AgentRunner`, trois implémentations. |
| Autonomie | Agents autonomes, scopés au répertoire du projet, garde-fou git. |
| Suivi de coût | Conservé tel quel — le SDK expose le détail par appel. |
| Suivi de quota | Ajouté, avec mise en pause du mode autonome. |

### Contrainte de licence

La documentation du SDK précise qu'Anthropic n'autorise pas, sauf accord
préalable, un développeur tiers à *proposer* l'authentification claude.ai ou ses
limites de débit dans un produit destiné à d'autres. L'usage retenu ici — un
utilisateur unique, ses propres identifiants, sa propre machine — reste
équivalent à l'usage de Claude Code lui-même. Si vibe-ide devait un jour être
distribué, le provider API redeviendrait le chemin obligatoire ; c'est la raison
pour laquelle il est conservé à parité plutôt que supprimé.

## Architecture

Nouveau package `backend/src/vibe_ide/services/providers/` :

- **`base.py`** — protocole `LLMProvider` (`complete()`, `stream()`) et dataclass
  `ProviderResult` : `content`, `input_tokens`, `output_tokens`,
  `cache_read_tokens`, `cache_creation_tokens`, `cost_usd`, `provider_name`.
  Ce contrat est calqué sur le `usage` de l'API *et* sur le `ResultMessage` du
  SDK ; les deux le remplissent sans perte.
- **`agent_sdk.py`** — `ClaudeAgentSDKProvider`. Enveloppe `query()` avec
  `cwd` = répertoire du projet **résolu en chemin long**,
  `permission_mode="acceptEdits"`, `allowed_tools` explicite
  (`Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`), `setting_sources=["project"]`,
  `system_prompt` alimenté par le registre d'agents, `model` issu d'`AgentConfig`,
  `include_partial_messages=True`, et deux garde-fous contre une boucle qui
  viderait le quota : `max_turns` borné et `max_budget_usd`.
- **`anthropic_api.py`** — `AnthropicApiProvider`, recevant le code existant de
  `AgentRunner._complete` / `_stream` sans changement de comportement.
- **`__init__.py`** — fabrique `get_provider(name)`.

`AgentRunner` conserve sa signature publique et son `AgentResult`. Il reçoit un
`LLMProvider` à la construction au lieu d'un `AsyncAnthropic`, plus un
`project_path` pour scoper le SDK. L'orchestrateur, les routers, les events
WebSocket et la majorité des tests backend restent inchangés.

Le futur `LocalModelProvider` (serveur local, petits modèles) n'implémentera que
le même protocole — la migration ne sera pas à refaire.

### Configuration

- `Settings.llm_provider: str = "agent_sdk"`
- `Settings.anthropic_api_key: str = ""` — **doit devenir optionnel**, sinon le
  backend ne démarre pas sans crédits.
- `AgentConfig` gagne un champ `provider` facultatif, permettant à un agent de
  pointer plus tard vers le serveur local pendant que les autres restent sur
  l'abonnement.

## Flux d'exécution

### Contexte projet

`cwd` pointant sur le répertoire du projet, le SDK charge `CLAUDE.md` nativement.
L'injection manuelle de `project_context` dans chaque prompt est donc supprimée
pour les agents SDK : la conserver ferait payer le même contenu deux fois, à
chaque appel, pour chaque agent du pipeline. Ne subsiste dans le prompt que ce
qui est propre à l'exécution — corps du ticket et retours reviewer des tours
précédents.

Point de vigilance : la traversée de `CLAUDE.md` remonte les répertoires parents
et ajoute `~/.claude/CLAUDE.md`. Un `CLAUDE.md` placé à la racine de
`~/vibe-ide-workspace/` serait chargé pour tous les projets. Le projet
`ide-core` hérite quant à lui de la constitution du dépôt vibe-ide, ce qui est
souhaitable dans son cas.

### Pipeline

Le codeur écrivant réellement, le reste du pipeline change de nature :

- le **testeur** exécute les tests sur du code réel ;
- le **reviewer** lit le diff effectif en travaillant dans le même `cwd` ;
- l'**auditeur sécurité** audite le diff plutôt qu'un extrait de prose ;
- le **validateur** vérifie les critères d'acceptation contre l'état du code.

### Garde-fou git

Avant le premier tour, l'orchestrateur crée une branche `ticket-XXX-<slug>`
depuis le HEAD courant. Les agents travaillent dans l'arbre de travail ;
`git diff` donne l'état des modifications à tout instant. En fin de pipeline,
un verdict APPROVED déclenche un commit sur cette branche ; sinon l'arbre est
laissé en l'état pour inspection. Rien n'atteint `main` sans geste humain,
conformément à la convention déjà inscrite dans `CLAUDE.md`.

### Streaming

Les deltas de texte des `StreamEvent` alimentent l'event `AGENT_TOKEN` existant —
l'UI ne voit pas la différence. Un nouvel event `AGENT_TOOL_USE` expose les
appels d'outils, pour que le panneau d'agent affiche « lecture de `src/foo.py` »,
« écriture de `tests/test_foo.py` », « exécution de `pytest` » au lieu d'un mur
de Markdown.

`AgentResult` est inchangé : `content` porte le résumé textuel pour l'UI,
`suggested_status` est parsé comme aujourd'hui. Le véritable artefact du
pipeline devient le diff.

## Quota et erreurs

Le suivi repose sur la télémétrie officielle du SDK plutôt que sur une
estimation. `ClaudeAgentSDKProvider` intercepte les `RateLimitEvent` du flux et
les relaie au `QuotaTracker`, qui persiste dans une table `quota_events` :
`status`, `utilization`, `rate_limit_type`, `resets_at`, horodatage.

`/api/v1/usage` expose alors deux choses : la consommation propre à vibe-ide,
agrégée depuis `agent_calls` par fenêtre glissante et par provider, et l'état
réel du quota d'abonnement tel que rapporté par Anthropic.

Deux réactions automatiques :

- `status == "allowed_warning"` — event WebSocket d'avertissement, le pipeline en
  cours va à son terme ;
- `status == "rejected"` — le mode autonome se met en pause jusqu'à `resets_at`
  au lieu d'enchaîner les tickets en échec.

Pas de retry automatique sur un quota atteint — sans objet. Retry réservé aux
erreurs transitoires.

Trois modes de défaillance doivent produire un message actionnable au démarrage
plutôt qu'une pile d'appels : CLI Claude Code absent, session non authentifiée,
provider inconnu en configuration.

## Tests

La couture de test se déplace : `test_agent_runner.py` mocke aujourd'hui
`AsyncAnthropic` ; il mockera un `FakeProvider`, ce qui simplifie les cas. Les
providers sont testés unitairement. Le marqueur `integration` déjà déclaré dans
`pyproject.toml` couvre le test de bout en bout avec authentification réelle,
désactivé en CI.

## Séquencement

Cinq phases, chacune laissant le dépôt vert :

1. ~~**Spike d'authentification**~~ — **terminé**, concluant. Voir « Résultats du
   spike » en tête de document.
2. **Couche provider à isopérimètre** — extraction du code existant dans
   `AnthropicApiProvider`, aucun changement de comportement, tests verts. Point
   de reprise sûr.
3. **`ClaudeAgentSDKProvider` + codeur** — première tranche verticale
   fonctionnelle.
4. **Reste du pipeline + branche git.**
5. **Quota, events d'outils, UI.**

## Hors périmètre

- `LocalModelProvider` — conçu pour, non implémenté.
- Sélection du profil d'authentification entre plusieurs abonnements : traitée
  par la configuration de session Claude Code, hors de ce design.
- Refactorisation non liée d'`AgentRunner` (il concentre aujourd'hui prompt,
  appel, coût, persistance et parsing) — seul le point d'appel est déplacé.
