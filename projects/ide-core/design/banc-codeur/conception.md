# Banc d'essai du codeur (ADR-095)

Conception du ticket-1052. Aucun code ici : les tickets 1053 à 1058 portent la réalisation.
Modèle suivi : l'essai de la seconde revue (ADR-079, `scripts/seconde_revue*.py`).

## 1. La question

Quel couple modèle + prompt du codeur approuve le plus de tickets au premier tour, à quel coût ?
Aujourd'hui : `claude-sonnet-5-5`, `agents/prompts/codeur.md`, skill `verifier-mon-travail`.

## 2. Le corpus

Manifeste `docs/essais/banc-codeur/corpus.json`, projet **ide-core seul** (public, ADR-043).

Une entrée est retenue si, par l'historique git seul :
- merge de ticket `feat`/`fix`/`chore` sur `develop`, squash `sha` ; **base = `sha^`** (premier parent) ;
- le diff ne touche que `backend/`, `scripts/` et `projects/ide-core/` : pas de frontend (pas de `npm ci`) ;
- au moins un fichier de test dans le diff ; diff entre 30 et 600 lignes ajoutées (borne du coût) ;
- hors : `preuve_reelle: true`, compte agent (`worktrees/`, `*compte*`, ADR-083 à 094), `agents.json`,
  `.github/`, hooks, secrets, coffre ;
- **le ticket existe à la base** : `git ls-tree -r <base>` trouve `ticket-N-*.md` sous `tickets/`.
  Un ticket créé par le squash lui-même est écarté ;
- la suite `verifier.py` est verte sur `sha` (référence) : sinon écartée.

Champs par entrée : `id`, `ticket`, `sha`, `base_sha`, `ticket_chemin` (au commit de base),
`ticket_sha256` (du texte lu à `base_sha`, frontmatter retiré), `fichiers`, `lignes_ajoutees`,
`pilote` (booléen). Le fichier porte `gel_sha256` (somme des entrées non pilote).
L'exécuteur relit le texte par `git show base_sha:ticket_chemin` et refuse si la somme diffère.

**Taille** : 20 entrées, jamais moins de 16 ; 3 entrées `pilote` en plus, hors gel, qui servent à
calibrer le coût. Les entrées sont tirées dans l'ordre inverse des dates, les plus récentes
d'abord (le code d'aujourd'hui, pas celui de juin).

**Biais assumé** : tous ces tickets ont fini approuvés en production ; l'essai mesure le premier
tour, pas la capacité à finir.

## 3. Ce qu'on rejoue

Une **cellule** = (entrée, bras). Boucle : codeur → tests → reviewer → validateur, jusqu'à
approbation ou 3 tours (`max_review_rounds`), puis arrêt.

- **Copie sans historique** : `git archive base_sha` extrait dans un dossier neuf sous
  `~/.tessera/banc-codeur/<essai>/<cellule>/`, puis `git init` et un seul commit. Hors
  `IDE_WORKTREES_DIR`, et surtout **sans le futur** : l'agent lit git (ADR-067), la solution
  ne doit pas s'y trouver. Aucun remote, aucun `.env`.
- **Aucun effet de bord** : pas de push, pas de PR, pas de `RunLock`, pas de base SQLite, pas de
  `Orchestrator`. Le script importe seulement les fonctions qui composent l'entrée d'un rôle
  (`provider_pour_role`, `run_review`/`lire_verdict`, `run_validation`), en lecture seule.
- **Reviewer, validateur et testeur sont identiques pour tous les bras** : ceux de `agents.json`
  à la date du gel (reviewer Opus 5.5, validateur Haiku 4.5, `verifier.py --impact base`).
  Seul le codeur varie.
- **Environnement** : `uv sync` dans la copie (cache uv partagé). Séquentiel (`--jobs 1`) : le
  testeur dure ~6 min (ticket-295), et `AGENT_CALLS_PARALLEL` n'a pas de sens ici.
- **Compte agent** : l'essai tourne sous le compte de l'utilisateur, comme la seconde revue ; il
  ne vise aucun projet à `worktree.compte_agent` (corpus d'ide-core hors compte agent).

## 4. Les bras

Déclarés dans `docs/essais/banc-codeur/bras.json`, gelé avec le corpus :

| bras | modèle | prompt |
|---|---|---|
| `A` actuel | celui d'`agents.json` | `agents/prompts/codeur.md` copié à la date du gel |
| `M` autre modèle | `claude-opus-5-5` (hypothèse : le plus fort, pour savoir si payer plus rapporte) | idem A |
| `P` variante | modèle d'A | `docs/essais/banc-codeur/prompts/codeur-p.md` |

Une variante de prompt est **un fichier du dossier de l'essai**, jamais `agents/prompts/`. Le
script écrit un `agents.json` temporaire (rôle `codeur` du bras, rôles reviewer/validateur
copiés d'ide-core) et un dossier de prompts temporaire, puis appelle `provider_pour_role` : le
manifeste d'ide-core n'est jamais ouvert en écriture. Aucun repli (ADR-046) : un bras indisponible
se consigne `indisponible`.

**Une seule variable par variante.** Variante proposée pour P : ajouter au prompt l'instruction de
lire « Ce que ça ne fait pas » et les ADR cités avant de coder, et de lancer les tests ciblés avant de
rendre. Le texte exact s'écrit et se gèle avant toute mesure ; un humain le valide. Un autre modèle
ou une autre variable se change dans `bras.json`, sans toucher au script.

L'écart de bruit se mesure : en plus, le bras A est rejoué une seconde fois (`A2`) sur 5 entrées.

## 5. Les mesures

Par cellule, une ligne de `docs/essais/banc-codeur/resultats.jsonl` :
`id`, `bras`, `gel_sha256`, `modele`, `tours` (1 à 3, ou `null`), `approuve_t1`, `approuve_final`,
`tests_verts` (suite à l'état final), `tests_reference_verts` (à titre indicatif : les fichiers de
test du vrai diff, posés après coup — ils dépendent des noms choisis par le codeur de l'époque,
donc hors règle), `cout_codeur_usd`, `cout_controles_usd`, `jetons` (entrée, sortie, cache),
`duree_ms` (codeur, total), `etat` (`ok` / `indisponible` / `plafond_cellule` / `echec_env`).

**Approuvé au premier tour** = au tour 1, tests verts **et** reviewer approuve **et** validateur
approuve, par le même schéma que le pipeline (`lire_verdict`, ADR-061). Une cellule `echec_env`
(l'environnement de la copie ne s'installe pas) ne compte pour aucun bras et sort l'entrée de
**tous** les bras.

## 6. La règle de décision, fixée ici

Des entiers sur 20 entrées. Soit `T1(X)` le nombre d'entrées approuvées au tour 1, `V(X)` celui des
entrées à tests verts au dernier tour, `C(X)` le coût moyen par entrée (codeur + contrôles).

1. **Non concluant** si : `A` reproduit moins de 14 entrées sur 20 (approuvées à un tour quelconque) ;
   ou plus de 4 cellules (sur 20) d'un bras sont exclues ; ou `A` et `A2` divergent sur 3 des 5
   entrées rejouées pour `T1` ; ou le plafond a coupé l'essai. Jamais « abandonner ».
2. **Meilleur** : `T1(X) − T1(A) ≥ 3` **et** `V(X) ≥ V(A)` **et** durée moyenne ≤ 2 × celle d'A
   → recommandation d'adopter X.
3. **Moins cher** : `T1(X) ≥ T1(A) − 1` **et** `C(X) ≤ 0,6 × C(A)` → adopter X pour le coût.
4. Sinon : **garder A**.

Si deux bras satisfont 2, le plus grand `T1` ; à égalité, le moins cher. Le rapport donne ces
comptes et la recommandation ; **un humain tranche**, dans une ADR qui amende celle-ci.

## 7. Plafond et reprise

- `--budget-usd` : **100 $** (proposition, un humain le confirme au lancement), vérifié avant chaque
  cellule sur la somme des coûts déjà consignés ; un dépassement arrête, il ne tronque pas.
  Plafond par cellule : 6 $ (au-delà, `plafond_cellule`).
- Le pilote (3 entrées `pilote` × 3 bras, plafond 15 $) mesure le coût réel par cellule. Si
  `coût moyen × 65 cellules` dépasse le plafond, la taille du corpus baisse (jamais sous 16) avant le gel.
- 65 cellules = 20 × 3 + 5 rejeux d'A. Le JSONL se reprend : une cellule déjà `ok` ne se rejoue pas ;
  le `gel_sha256` de chaque ligne doit égaler celui du manifeste.
- Quota d'abonnement : le coût en dollars est l'estimation du SDK ; la dépense réelle se lit sur le
  quota, et l'essai se lance après le relevé de ce quota.

## 8. Ce qui reste hors du produit

Tout vit sous `scripts/` (code), `backend/tests/` (tests) et `docs/essais/banc-codeur/` (données,
rapport `docs/essais/banc-codeur.md`, bloc de conclusion balisé). Aucun fichier sous `backend/src`,
aucun rôle ajouté à `agents.json`, aucune étape de pipeline, aucun écran. Une adoption passe par une
autre ADR et un autre ticket.

## 9. Ce qui revient à l'humain

- Le plafond en dollars et le moment du lancement (quota).
- Le texte de la variante de prompt, avant son gel.
- Le choix du bras `M` (Opus par hypothèse).
- Lire le rapport et écrire l'ADR d'adoption ou d'abandon.

## 10. Tickets

1053 corpus et gel · 1054 bras et manifeste temporaire · 1055 exécuteur d'une cellule ·
1056 règle de décision et rapport · 1057 pilote · 1058 essai, lecture, conclusion.
