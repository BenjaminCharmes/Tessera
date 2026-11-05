# Essai mesuré d'une seconde revue par un autre modèle (ADR-075)

Conception du ticket-783. Aucun code n'est écrit ici : les tickets 805 à 810 portent
l'implémentation et l'exécution.

## 1. La question

Une seconde revue, par un modèle différent, attrape-t-elle des défauts que le reviewer
actuel (`claude-opus-5-5`, ADR-009, ADR-061) laisse passer, et à quel coût ? Cas d'origine :
le ticket-733 (une résolution de conflit effaçait une fonctionnalité, approuvée) et l'audit du
30/10 (quatre contournements de gravité haute dans du code approuvé, `docs/audit/securite.md`).

Ce qui existe déjà et qu'on réutilise, sans rien y changer :

- l'entrée du reviewer se compose dans `pipeline_controles.run_review` ; son schéma est
  `REVIEWER_SCHEMA`, sa lecture `lire_verdict` / `juger_revue` (fonctions pures) ;
- tout provider se construit par `provider_pour_role` (ADR-046) ; `complete(..., schema=)` rend
  une sortie structurée chez Ollama comme chez le SDK ;
- le précédent d'un essai hors du produit : `scripts/mesurer_compression.py` et
  `scripts/mesure_verdict.py` (ticket-605), testés depuis `backend/tests/`.

## 2. Le corpus, figé avant tout appel

Manifeste : `docs/essais/seconde-revue/corpus.json`. Une entrée = un run passé, approuvé
et mergé.

| champ | sens |
|---|---|
| `id`, `ticket` | identifiant stable, ticket d'origine |
| `sha` | commit de squash sur `develop` ; le diff est `sha^..sha` |
| `classe` | `defaut` ou `sain` |
| `preuve` | pour `defaut` : SHA ou ticket de la correction, ou numéro de constat d'audit |
| `fichiers_defaut` | pour `defaut` : les fichiers où le défaut se trouve |
| `defaut` | une phrase, écrite avant tout rejeu |
| `sensible` | vrai si le diff touche une garde (liste ci-dessous) |

**Étiquetage par l'historique git seul.** `defaut` : un commit de correction ou un constat
d'audit postérieur porte sur les mêmes lignes. `sain` : aucune correction ni constat dans les
sept jours qui suivent le merge. Jamais d'étiquette posée après avoir vu une sortie de modèle.

**Taille.** Au moins 10 `defaut` et 10 `sain`, dont au moins 4 `defaut` sensibles. Le fichier
porte `gel_sha256`, la somme de ses entrées ; chaque résultat la recopie. Une entrée ajoutée
ensuite est un autre essai.

**Diffs sensibles**, liste fixée ici, stockée dans l'entrée à l'étiquetage : fichiers
`services/providers/*guard*`, `garde_*`, `chemins_proteges.py`, `redirections_bash.py`,
`refus_*.py`, `secrets_diff.py`, le coffre, la livraison (`approved_sha`, `pushed_sha`),
`scripts/hooks/`, `.github/workflows/`.

**Biais assumé.** Le corpus est choisi sur l'approbation du reviewer de production : le rappel
du reviewer actuel n'y est pas mesurable, seul l'**apport** d'un second regard l'est. C'est la
question posée. Le reviewer rejoué (bras B) sert de plancher de bruit : un défaut qu'il
rattrape au rejeu n'est pas un apport du candidat.

## 3. Le rejeu

Un script `scripts/seconde_revue.py`, hors de `backend/src`, jamais importé par le produit.

- **Entrée** : le corps du ticket, puis `git diff sha^..sha`. Pas de contexte de test ni
  d'audit, pas d'outils (`allow_tools=False`) : les deux bras reçoivent exactement la même
  chose. Prompt : `agents/prompts/reviewer.md`, tel quel. Schéma : `REVIEWER_SCHEMA`. Lecture :
  `lire_verdict` au seuil `reviewer_confidence_threshold`.
- **Providers** : le script écrit dans un dossier temporaire un `agents.json` qui déclare un
  rôle `reviewer` (bras B) et un rôle `candidat` (bras C), puis appelle `provider_pour_role`.
  Le manifeste d'ide-core n'est jamais lu en écriture. **Aucun repli** : un candidat
  indisponible est consigné `indisponible`, un autre modèle ne juge pas à sa place (ADR-046).
- **Rien n'est touché** : lecture git seule, aucun worktree, aucun run, aucune base ; les
  résultats s'ajoutent à `docs/essais/seconde-revue/resultats.jsonl`, une ligne par appel, ce
  qui rend le script reprenable.
- **Plafond de dépense** : `--budget-usd`, 10 par défaut, vérifié avant chaque appel sur la
  somme des `cost_usd` déjà consignés. Un dépassement arrête, il ne tronque pas.
- **Fenêtre** : pour un candidat `ollama`, un prompt au-delà de `--fenetre-caracteres` n'est pas
  envoyé : l'entrée est consignée `hors_fenetre` (ADR-071).

Chaque ligne de résultat : `id`, `bras` (`B` ou `C`), `modele`, `gel_sha256`, `verdict` lu,
`remarques` (texte, lieu, confiance), `cout_usd`, `duree_ms`, `etat`
(`ok` / `indisponible` / `hors_fenetre` / `hors_schema`).

## 4. Les critères

Un verdict est **levé** quand `lire_verdict` rend refus : une remarque au moins au seuil.

1. **Défaut en plus** : sur une entrée `defaut`, C lève un verdict et B non, **et** la relecture
   humaine confirme qu'une remarque de C désigne le défaut étiqueté (ou un autre défaut réel,
   compté à part). Un appariement automatique (le fichier de `fichiers_defaut` apparaît dans
   `location` ou `text`) propose, l'humain tranche.
2. **Faux positif en plus** : sur une entrée `sain`, C lève un verdict et B non, et la
   relecture juge la remarque infondée.
3. **Coût et durée** : moyenne et maximum de `cout_usd` et `duree_ms` par revue, bras par bras.
   Un candidat local coûte 0 en dollars : on rapporte sa durée, et ce qu'elle ajoute à un tour.
4. **Validité du rejeu**, avant tout calcul : B doit approuver au moins 80 % du corpus (le
   reviewer d'origine l'a approuvé en entier) ; les `hors_fenetre` et `indisponible` de C
   doivent rester sous 25 %. Sinon : `non concluant`, jamais `abandonner`.

La relecture est un fichier : `docs/essais/seconde-revue/relecture.json`, une ligne par
remarque levée (`id`, `bras`, `rang`, `jugement` : `confirme` / `autre_defaut` / `infonde`).
Elle est faite par un humain, sur un tirage non aveugle mais sans le nom du modèle affiché.

## 5. La règle de décision

Des entiers, pas des pourcentages : sur une vingtaine d'entrées, un point de pourcentage n'est
pas un signal. Dans l'ordre :

1. Rejeu non valide → `non concluant`.
2. ≥ 3 défauts en plus **et** ≤ 2 faux positifs en plus **et** durée ajoutée ≤ 5 min par revue
   **et** coût moyen de C ≤ celui de B → `adopter`.
3. Sinon, sur les seules entrées sensibles : ≥ 2 défauts en plus **et** ≤ 1 faux positif en
   plus → `reserver` aux diffs sensibles.
4. Sinon → `abandonner`.

Le résultat est une **recommandation**. L'adoption, la réserve ou l'abandon sont décidés par
un humain, dans une ADR qui amende ADR-009 et ADR-061 : elle devrait dire comment deux verdicts
se combinent (un refus de l'un bloque), et qu'un second reviewer indisponible refuse (ADR-039).

## 6. Ce qui reste hors du produit tant que l'essai n'a pas conclu

- aucun fichier sous `backend/src/`, aucun rôle dans `agents.json`, aucun événement, aucune
  étape de pipeline, aucun écran ;
- `run_review` et les gardes ne sont pas modifiés ;
- tout vit sous `scripts/` (code), `backend/tests/` (tests) et `docs/essais/seconde-revue/`
  (corpus, résultats, relecture) ; le rapport est `docs/essais/seconde-revue.md`, avec un bloc
  de conclusion balisé comme celui du ticket-605.

## 7. Ce qui revient à l'humain

- **Un fournisseur externe** (`openai_compatible`) : compte, coût, et surtout l'envoi d'un diff
  hors de la machine. Le corpus d'ide-core est public ; un autre projet déclaré
  `confidentiality: professional` ne devrait pas servir sans accord (ADR-043).
- **Un témoin Claude** (`claude-sonnet-5-5`, sans autre fournisseur) pour séparer l'apport du
  second regard de celui d'une autre famille de modèles : il consomme du quota d'abonnement. Le
  script accepte tout couple `provider:modele` ; l'essai de base n'en lance qu'un, Ollama.
- Le plafond de dépense (10 $ proposés), la relecture des remarques, et l'ADR d'adoption.

## 8. Tickets

805 corpus (lecture, validation) · 806 étiquetage du corpus · 807 construction de l'entrée et
lecture des résultats · 808 exécuteur de rejeu · 809 fonction de décision et rapport · 810
exécution, relecture, conclusion.
