---
id: ticket-242
title: "Un rôle déclare les skills qu'il voit, et le codeur d'ide-core vérifie son travail"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-29
---

# ticket-242 — Un rôle déclare les skills qu'il voit

## Objectif

Un rôle déclare dans `agents.json` la liste des skills qu'il peut charger
(`"skills": ["nom"]`). Le codeur d'ide-core en reçoit un premier : vérifier son
travail en lançant les tests qu'il a touchés.

## Contexte

Les agents du produit n'ont pas l'outil `Skill` : les skills de `.claude/` ne
servent qu'au développeur. Une règle utile une fois sur dix est donc soit
absente, soit recopiée dans le prompt et payée à chaque appel.

Donner l'outil sans filtre serait pire. Essai réel : depuis
`projects/demo/`, le CLI découvre les skills du projet, **ceux de la racine du
dépôt**, et une vingtaine de skills intégrés (`schedule`, `loop`, `batch`…).
Pour ide-core, le codeur verrait `ticket-workflow`, qui lui dit de committer et
de pousser, à l'inverse d'ADR-027. L'option `skills=[noms]` du SDK filtre la
liste, et un skill non listé est refusé par l'outil (« not in this session's
skills allowlist »).

Par ailleurs, le testeur est désactivé sur ide-core : rien ne lance un test
pendant un run, et les tickets 215 et 219 ont été approuvés avec des tests
rouges.

## Solution proposée

- `AgentConfig.skills: list[str] = []`.
- `provider_pour_role` la transmet au provider, repli compris ; `_build_options`
  ajoute alors `Skill` aux outils et passe `skills=[…]`. Liste vide : rien ne
  change, ni outil ni option.
- `projects/ide-core/.claude/skills/verifier-mon-travail/SKILL.md` : lancer les
  fichiers de test touchés depuis `../../backend` ou `../../frontend`, jamais
  la suite entière.
- `agents/prompts/codeur.md` : « tu ne lances pas les tests » devient
  conditionnel à l'absence d'un skill de vérification.
- ide-core déclare ce skill pour son codeur.

## Critères d'acceptation

- [ ] `test_skills_par_role.py` vérifie que `_build_options(skills=["x"])` ajoute `Skill` à `tools` et à `allowed_tools` et passe `skills == ["x"]`
- [ ] `test_skills_par_role.py` vérifie que sans skills, `options.skills` est `None` et `Skill` absent de `tools`
- [ ] `test_skills_par_role.py` vérifie que `provider_pour_role` transmet les skills déclarés par le rôle, au principal comme au repli
- [ ] `test_skills_par_role.py` vérifie que chaque skill déclaré dans `projects/ide-core/agents.json` existe sous `projects/ide-core/.claude/skills/<nom>/SKILL.md`
- [ ] `agents/prompts/codeur.md` dit d'utiliser le skill de vérification quand il est proposé

## Ce que ça ne fait pas

- Pas de réglage dans l'UI.
- Le filtre du SDK est un filtre de contexte, pas un bac à sable : les fichiers
  des autres skills restent lisibles par `Read`.
- Un agent ne crée pas de skill : `.claude/skills/` lui est refusé en écriture
  (ticket-240).
