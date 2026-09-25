# Contribuer

Avant tout, la chose qui surprend : **ce dépôt est public, pas open source.**

La licence est [PolyForm Noncommercial 1.0.0](LICENSE.md). Vous pouvez lire le
code, l'utiliser et le modifier à des fins non commerciales. Vous ne pouvez pas
le vendre ni le faire tourner dans un produit ou un service commercial. En
proposant une contribution, vous acceptez qu'elle soit distribuée sous cette
même licence, et vous confirmez avoir le droit de la donner — en particulier
si votre employeur détient ce que vous écrivez sur votre temps de travail.

Dit autrement : les contributions sont bienvenues, mais elles sont un cadeau à
un projet dont je garde les droits d'exploitation. Autant le savoir avant
d'écrire trois cents lignes.

## Ce qui aide le plus

Par ordre décroissant d'utilité, et sans ironie : **un rapport de bug
reproductible** vaut mieux qu'un correctif approximatif. Le projet a une
feuille de route personnelle ; une PR non sollicitée sur une fonctionnalité
peut rester longtemps ouverte, ou être refusée parce qu'elle va contre une
décision déjà prise.

Ouvrir une [discussion](https://github.com/BenjaminCharmes/Tessera/discussions)
avant de coder évite ce gâchis.

## Si vous ouvrez une PR

Le flux est `ticket-XXX` → `develop` → `main`. Les PR ciblent **`develop`**,
jamais `main`.

```bash
git checkout develop && git pull
git checkout -b ticket-XXX-description-courte
```

Trois règles qui feront refuser la PR si elles ne sont pas tenues :

1. **Les commits sont en anglais**, au format
   [Conventional Commits](https://www.conventionalcommits.org) — `feat:`,
   `fix:`, `chore:`, `docs:`, `refactor:`, `test:`. Le corps explique le
   *pourquoi* ; le diff dit déjà le *quoi*.
2. **Aucune attribution à un outil d'IA** : ni `Co-Authored-By`, ni mention
   d'assistant dans un message de commit, un titre de PR ou un commentaire de
   code. Ce que ce dépôt produit atterrit chez ses utilisateurs, parfois chez
   leurs clients : la provenance du code n'y a pas sa place.
3. **Les fichiers se stagent nommément.** `git add -A` balaie les projets
   importés sous `projects/`, les artefacts de couverture et les logs locaux.

## Vérifier avant de proposer

```bash
.\scripts\tessera.ps1 verify     # pytest, mypy, types + tests frontend, Playwright
```

La CI tourne sur chaque PR et c'est elle qui tranche. Lancer `verify` avant de
pousser vous évite un aller-retour, sans la remplacer : il tourne sur un seul
OS, et le premier run qui a suivi la réouverture de la CI a trouvé en
trente-cinq secondes deux tests qui ne passaient que sur le poste de leur
auteur.

Le détail des conventions de code — TypeScript strict sans `any`, type hints
Python partout, fichiers sous 200 lignes, un test par fonction publique — est
dans [CLAUDE.md](CLAUDE.md). Les contraintes d'architecture en vigueur sont
dans `projects/ide-core/memory/decisions.md` : ce sont des décisions prises,
pas des archives, et une PR qui en viole une sera refusée même si elle marche.

## Ce que vous n'avez pas à faire

Signer un CLA, demander la permission d'ouvrir une issue, ou justifier votre
niveau. Un bug mal décrit mais réel reste plus utile qu'un silence poli.
