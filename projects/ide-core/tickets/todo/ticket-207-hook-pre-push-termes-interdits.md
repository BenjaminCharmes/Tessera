---
id: ticket-207
title: "Hook pre-push pour les commits manuels sur le dépôt Tessera"
type: chore
status: todo
---

# ticket-207 — Hook pre-push pour les commits manuels sur le dépôt Tessera

## Objectif

Couvrir les pushes manuels (hors IDE) sur le dépôt Tessera avec le même
contrôle de termes que ticket-206 — pour que la règle d'ADR-048 tienne aussi
quand l'humain pousse lui-même.

## Contexte

Ticket-206 couvre tous les pushes faits par le pipeline. Mais un `git push`
lancé à la main dans un terminal — depuis la branche d'un ticket ou depuis
`develop` — n'est pas intercepté par le service : il n'existe que dans le
backend.

ADR-027 ne s'oppose pas à un hook pour les commits manuels : il interdit
aux **agents** de toucher à git, et force `core.hooksPath` vers un dossier
vide *pendant les runs*. Hors run, le hook s'exécute normalement.

Le hook lit la même variable `FORBIDDEN_TERMS` depuis `.env` : une seule
liste à maintenir.

## Ce qu'il faut faire

### 1. Script `scripts/hooks/pre-push`

Script Python (shebang `python3`) exécuté par git avant un push.

- Charge `FORBIDDEN_TERMS` depuis `.env` à la racine du dépôt (parse
  `KEY=value`, ignore les lignes sans `FORBIDDEN_TERMS`)
- Si liste vide ou absente : exit 0 (pas de blocage)
- Lit stdin au format git (lignes `<local_ref> <local_sha> <remote_ref>
  <remote_sha>`), récupère les SHAs
- Pour chaque ref à pousser : `git log --format="%H %ae %s" <remote_sha>..<local_sha>`
  puis `git diff <remote_sha>..<local_sha>` pour les lignes ajoutées
- Applique la même normalisation que `TermesInterditsService` (factoriser
  dans un module partageable, ou dupliquer si le script doit rester autonome)
- Affiche la localisation (`commit:<sha7>` ou `file:<chemin>`) sur stderr
  **sans** nommer le terme ; exit 1

### 2. `Makefile` — cible `install-hooks`

```makefile
install-hooks:
	cp scripts/hooks/pre-push .git/hooks/pre-push
	chmod +x .git/hooks/pre-push
```

Documenter dans `CONTRIBUTING.md` que `make install-hooks` est recommandé
après le premier clone.

### 3. Test

- Test unitaire du script Python (en appelant la fonction de vérification
  directement, pas via subprocess)
- Cas : terme en message, terme dans diff ajouté, liste vide, sha inconnu
  (`0000000000000000000000000000000000000000` = nouvelle branche)

## Critères d'acceptation

- [ ] `make install-hooks` copie le hook et le rend exécutable
- [ ] Un `git push` manuel avec un terme dans un message de commit est bloqué,
      le message d'erreur contient `commit:<sha7>` et non le terme
- [ ] Un `git push` sans `FORBIDDEN_TERMS` déclaré n'est pas bloqué
- [ ] Le hook n'interfère pas avec les runs du pipeline (qui surchargent
      `core.hooksPath` de toute façon)
- [ ] `CONTRIBUTING.md` mentionne `make install-hooks`

## Ce que ça ne fait pas

- Pas de hook `commit-msg` : ADR-048 choisit le push comme point de contrôle
  (un commit local ne publie rien)
- Pas d'installation automatique : un hook dans `.git/` n'est pas versionné,
  et forcer son installation à chaque `make dev` serait intrusif

## Dépendances

ticket-206 (la logique de normalisation peut être partagée)
