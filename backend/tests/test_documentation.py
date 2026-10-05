"""La doc se met à jour par lot, en modifications ciblées — ticket-092, ticket-213."""
import json
from pathlib import Path

import pytest

from tessera.services.documentation import (
    EditionRefusee,
    appliquer_editions,
    tickets_a_documenter,
    marquer_documente,
    _PLAFOND,
)


# ------------------------------------------------------------------
# Le contrat de sortie : des modifications, jamais un fichier entier
# ------------------------------------------------------------------


def _doc(tmp_path: Path, nom: str, contenu: str) -> Path:
    (tmp_path / "docs").mkdir(exist_ok=True)
    chemin = tmp_path / "docs" / nom
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_une_edition_remplace_exactement_son_ancien_texte(tmp_path: Path) -> None:
    fichier = _doc(tmp_path, "archi.md", "# Titre\n\nLe pipeline a deux agents.\n")

    appliquer_editions(
        tmp_path,
        [{"fichier": "docs/archi.md", "ancien": "deux agents", "nouveau": "six agents"}],
    )

    assert "six agents" in fichier.read_text(encoding="utf-8")
    assert fichier.read_text(encoding="utf-8").startswith("# Titre")


def test_un_ancien_texte_absent_est_refuse(tmp_path: Path) -> None:
    # L'agent a inventé un texte qu'il croyait présent. L'appliquer « au mieux »
    # écrirait au mauvais endroit, et personne ne le verrait dans un diff de
    # doc de trois cents lignes.
    fichier = _doc(tmp_path, "archi.md", "# Titre\n\nContenu.\n")

    with pytest.raises(EditionRefusee) as exc:
        appliquer_editions(
            tmp_path,
            [{"fichier": "docs/archi.md", "ancien": "jamais écrit", "nouveau": "x"}],
        )

    assert "introuvable" in str(exc.value)
    assert fichier.read_text(encoding="utf-8") == "# Titre\n\nContenu.\n"


def test_un_ancien_texte_ambigu_est_refuse(tmp_path: Path) -> None:
    # Deux occurrences : on ne devine pas laquelle. Un remplacement global
    # toucherait celle qu'on ne voulait pas.
    _doc(tmp_path, "archi.md", "Le run commite.\nLe run commite.\n")

    with pytest.raises(EditionRefusee) as exc:
        appliquer_editions(
            tmp_path,
            [{"fichier": "docs/archi.md", "ancien": "Le run commite.", "nouveau": "x"}],
        )

    assert "2 fois" in str(exc.value)


def test_rien_n_est_ecrit_si_une_seule_edition_echoue(tmp_path: Path) -> None:
    # Tout ou rien : une doc à moitié mise à jour est pire qu'une doc en
    # retard, parce qu'elle a l'air à jour.
    a = _doc(tmp_path, "a.md", "alpha\n")
    b = _doc(tmp_path, "b.md", "beta\n")

    with pytest.raises(EditionRefusee):
        appliquer_editions(
            tmp_path,
            [
                {"fichier": "docs/a.md", "ancien": "alpha", "nouveau": "ALPHA"},
                {"fichier": "docs/b.md", "ancien": "absent", "nouveau": "x"},
            ],
        )

    assert a.read_text(encoding="utf-8") == "alpha\n"
    assert b.read_text(encoding="utf-8") == "beta\n"


def test_une_edition_hors_documentation_est_refusee(tmp_path: Path) -> None:
    # L'agent documente ; il ne touche pas au code, ni aux tickets, ni aux ADR.
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(EditionRefusee) as exc:
        appliquer_editions(
            tmp_path,
            [{"fichier": "src/main.py", "ancien": "x = 1", "nouveau": "x = 2"}],
        )

    assert "documentation" in str(exc.value)


def test_un_ajout_s_insere_apres_une_section(tmp_path: Path) -> None:
    fichier = _doc(tmp_path, "archi.md", "# Titre\n\n## A\n\nun\n\n## B\n\ndeux\n")

    appliquer_editions(
        tmp_path,
        [{"fichier": "docs/archi.md", "apres_section": "## A", "texte": "trois"}],
    )

    contenu = fichier.read_text(encoding="utf-8")
    assert contenu.index("trois") < contenu.index("## B")


def test_un_ajout_apres_une_section_absente_est_refuse(tmp_path: Path) -> None:
    _doc(tmp_path, "archi.md", "# Titre\n")

    with pytest.raises(EditionRefusee):
        appliquer_editions(
            tmp_path,
            [{"fichier": "docs/archi.md", "apres_section": "## Z", "texte": "x"}],
        )


def test_insertion_section_niveau_different_leve_edition_refusee(tmp_path: Path) -> None:
    """'## Supervision' absent quand seul '### Supervision' existe → EditionRefusee, pas StopIteration."""
    fichier = _doc(tmp_path, "archi.md", "# Titre\n\n### Supervision\n\nDu texte.\n")

    with pytest.raises(EditionRefusee) as exc:
        appliquer_editions(
            tmp_path,
            [{"fichier": "docs/archi.md", "apres_section": "## Supervision", "texte": "ajout"}],
        )

    message = str(exc.value)
    assert "## Supervision" in message
    assert "docs/archi.md" in message
    assert fichier.read_text(encoding="utf-8") == "# Titre\n\n### Supervision\n\nDu texte.\n"


def test_insertion_section_au_milieu_dune_phrase_leve_edition_refusee(tmp_path: Path) -> None:
    """Section visée présente uniquement au milieu d'une phrase → EditionRefusee."""
    contenu = "# Titre\n\nVoir aussi ## Supervision pour les détails.\n"
    fichier = _doc(tmp_path, "archi.md", contenu)

    with pytest.raises(EditionRefusee) as exc:
        appliquer_editions(
            tmp_path,
            [{"fichier": "docs/archi.md", "apres_section": "## Supervision", "texte": "ajout"}],
        )

    message = str(exc.value)
    assert "## Supervision" in message
    assert "docs/archi.md" in message
    assert fichier.read_text(encoding="utf-8") == contenu


def test_une_edition_ne_peut_pas_vider_un_fichier(tmp_path: Path) -> None:
    # Le garde-fou contre la panne d'origine : `doc-updater` réécrivait le
    # fichier entier depuis une vue tronquée à 8 000 caractères, sur un README
    # de 24 000. Il ne pouvait pas faire autrement que le mutiler.
    gros = "ligne\n" * 4000
    fichier = _doc(tmp_path, "gros.md", gros)

    with pytest.raises(EditionRefusee) as exc:
        appliquer_editions(
            tmp_path, [{"fichier": "docs/gros.md", "ancien": gros, "nouveau": "court"}]
        )

    assert "amput" in str(exc.value)
    assert fichier.read_text(encoding="utf-8") == gros


# ------------------------------------------------------------------
# Quels tickets restent à documenter
# ------------------------------------------------------------------


def _ticket(tmp_path: Path, tid: str, titre: str = "T") -> None:
    dossier = tmp_path / "tickets" / "done"
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{tid}-slug.md").write_text(
        f"---\nid: {tid}\ntitle: \"{titre}\"\ntype: feat\nstatus: done\n"
        f"priority: medium\nagent: codeur\n---\n\n# {tid}\n\n## Objectif\n\nFaire X.\n",
        encoding="utf-8",
    )


def test_sans_marqueur_tout_est_a_documenter(tmp_path: Path) -> None:
    _ticket(tmp_path, "ticket-001")
    _ticket(tmp_path, "ticket-002")

    assert [t.id for t in tickets_a_documenter(tmp_path)] == [
        "ticket-001",
        "ticket-002",
    ]


def test_le_marqueur_borne_ce_qui_reste(tmp_path: Path) -> None:
    for n in (1, 2, 3):
        _ticket(tmp_path, f"ticket-00{n}")
    # Marquer les deux premiers comme documentés
    marquer_documente(tmp_path, ["ticket-001", "ticket-002"])

    assert [t.id for t in tickets_a_documenter(tmp_path)] == ["ticket-003"]


def test_un_marqueur_illisible_ne_bloque_pas(tmp_path: Path) -> None:
    # Mieux vaut re-documenter que ne plus jamais documenter.
    _ticket(tmp_path, "ticket-001")
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "documentation.json").write_text("{ cassé", encoding="utf-8")

    assert [t.id for t in tickets_a_documenter(tmp_path)] == ["ticket-001"]


def test_ticket_hors_ordre_nest_pas_oublie(tmp_path: Path) -> None:
    """ticket-208 livré après ticket-209 déjà documenté figure dans le lot suivant.

    L'ancien filtre ``identifiant <= dernier`` excluait définitivement tout
    ticket dont l'identifiant était inférieur au dernier documenté — même si
    ce ticket avait été livré après. Le nouveau filtre par ensemble d'IDs
    documentés ne fait que ça : exclure les IDs déjà vus.
    """
    _ticket(tmp_path, "ticket-209")
    marquer_documente(tmp_path, ["ticket-209"])
    # ticket-208 arrive dans done/ plus tard
    _ticket(tmp_path, "ticket-208")

    ids = [t.id for t in tickets_a_documenter(tmp_path)]
    assert "ticket-208" in ids
    assert "ticket-209" not in ids


def test_ancien_format_encore_lu(tmp_path: Path) -> None:
    """Un documentation.json à l'ancien format reste lisible (ADR-036)."""
    for n in (1, 2, 3):
        _ticket(tmp_path, f"ticket-00{n}")
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "documentation.json").write_text(
        '{"dernier_ticket": "ticket-002"}', encoding="utf-8"
    )

    assert [t.id for t in tickets_a_documenter(tmp_path)] == ["ticket-003"]


# ------------------------------------------------------------------
# Le service : deux agents, un lot, un seul appel chacun
# ------------------------------------------------------------------


class _FauxProvider:
    def __init__(self, reponses: list[str]) -> None:
        self.reponses = list(reponses)
        self.appels: list[dict[str, object]] = []

    async def complete(self, **kwargs: object) -> object:
        self.appels.append(kwargs)

        class _R:
            content = self.reponses.pop(0) if self.reponses else '{"editions": []}'
            input_tokens = output_tokens = cache_read_tokens = 0
            cost_usd = 0.0

        return _R()


def _service(tmp_path: Path, reponses: list[str]):  # type: ignore[no-untyped-def]
    from tessera.services.documentation import DocumentationService

    prompts = tmp_path / "prompts"
    prompts.mkdir(exist_ok=True)
    for role in ("doc-technique", "doc-fonctionnelle"):
        (prompts / f"{role}.md").write_text(f"prompt {role}", encoding="utf-8")
    provider = _FauxProvider(reponses)
    return DocumentationService(provider, prompts), provider  # type: ignore[arg-type]


def _avec_marqueur(tmp_path: Path) -> None:
    """Crée un marqueur vide pour que `mettre_a_jour` ne fasse pas l'initialisation."""
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "documentation.json").write_text(
        '{"documentes": []}', encoding="utf-8"
    )


async def test_sans_marqueur_le_service_initialise_sans_appel_provider(
    tmp_path: Path,
) -> None:
    """Projet sans documentation.json : le service pose le marqueur, n'appelle pas le provider."""
    for n in (1, 2, 3):
        _ticket(tmp_path, f"ticket-{n:03d}")
    svc, provider = _service(tmp_path, [])

    resultat = await svc.mettre_a_jour(tmp_path)

    assert provider.appels == []
    assert resultat.fichiers_modifies == []
    assert resultat.marqueur_ecrit is True
    # Le marqueur est créé avec tous les tickets existants
    assert (tmp_path / "memory" / "documentation.json").is_file()
    assert tickets_a_documenter(tmp_path) == []


async def test_plafond_de_tickets_par_lot(tmp_path: Path) -> None:
    """15 tickets à documenter → le brief n'en contient que _PLAFOND, tronque=True."""
    n_tickets = _PLAFOND + 5
    for n in range(1, n_tickets + 1):
        _ticket(tmp_path, f"ticket-{n:03d}")
    _avec_marqueur(tmp_path)

    svc, provider = _service(tmp_path, ['{"editions": []}', '{"editions": []}'])
    resultat = await svc.mettre_a_jour(tmp_path)

    assert resultat.tronque is True
    assert len(resultat.tickets) == _PLAFOND
    # Le brief n'inclut que les _PLAFOND tickets les plus récents
    user_content = str(provider.appels[0]["user"])
    # Les premiers tickets (hors plafond) ne sont pas dans le brief
    assert "ticket-001" not in user_content


async def test_un_lot_de_dix_tickets_fait_deux_appels(tmp_path: Path) -> None:
    # Le point du ticket : documenter par lot, pas par ticket. Dix tickets
    # documentés un par un, ce sont vingt appels ; ici il y en a deux.
    for n in range(1, 11):
        _ticket(tmp_path, f"ticket-{n:03d}")
    _doc(tmp_path, "architecture.md", "# Archi\n\nancien texte\n")
    _doc(tmp_path, "guide-utilisateur.md", "# Guide\n\nancien guide\n")
    _avec_marqueur(tmp_path)

    svc, provider = _service(tmp_path, ['{"editions": []}', '{"editions": []}'])
    await svc.mettre_a_jour(tmp_path)

    assert len(provider.appels) == 2


async def test_les_deux_agents_recoivent_les_memes_tickets(tmp_path: Path) -> None:
    _ticket(tmp_path, "ticket-001", titre="Ajouter le mode autonome")
    _avec_marqueur(tmp_path)
    svc, provider = _service(tmp_path, ['{"editions": []}', '{"editions": []}'])

    await svc.mettre_a_jour(tmp_path)

    for appel in provider.appels:
        assert "ticket-001" in str(appel["user"])
        assert "Ajouter le mode autonome" in str(appel["user"])


async def test_les_editions_proposees_sont_appliquees(tmp_path: Path) -> None:
    _ticket(tmp_path, "ticket-001")
    fichier = _doc(tmp_path, "architecture.md", "# Archi\n\ndeux agents\n")
    _avec_marqueur(tmp_path)
    reponse = json.dumps(
        {
            "editions": [
                {
                    "fichier": "docs/architecture.md",
                    "ancien": "deux agents",
                    "nouveau": "six agents",
                }
            ]
        }
    )
    svc, _ = _service(tmp_path, [reponse, '{"editions": []}'])

    resultat = await svc.mettre_a_jour(tmp_path)

    assert "six agents" in fichier.read_text(encoding="utf-8")
    assert resultat.fichiers_modifies


async def test_une_edition_refusee_ne_casse_pas_la_mise_a_jour(tmp_path: Path) -> None:
    # L'agent a proposé une modification sur un texte inexistant. On le dit,
    # on n'écrit rien de sa part, et l'autre agent garde sa chance.
    _ticket(tmp_path, "ticket-001")
    _doc(tmp_path, "architecture.md", "# Archi\n")
    guide = _doc(tmp_path, "guide-utilisateur.md", "# Guide\n\nvieux\n")
    _avec_marqueur(tmp_path)
    mauvaise = json.dumps(
        {"editions": [{"fichier": "docs/architecture.md", "ancien": "absent", "nouveau": "x"}]}
    )
    bonne = json.dumps(
        {"editions": [{"fichier": "docs/guide-utilisateur.md", "ancien": "vieux", "nouveau": "neuf"}]}
    )
    svc, _ = _service(tmp_path, [mauvaise, bonne])

    resultat = await svc.mettre_a_jour(tmp_path)

    assert resultat.refus
    assert "neuf" in guide.read_text(encoding="utf-8")


async def test_le_marqueur_avance_apres_une_mise_a_jour(tmp_path: Path) -> None:
    _ticket(tmp_path, "ticket-001")
    _ticket(tmp_path, "ticket-002")
    _avec_marqueur(tmp_path)
    svc, _ = _service(tmp_path, ['{"editions": []}', '{"editions": []}'])

    await svc.mettre_a_jour(tmp_path)

    assert tickets_a_documenter(tmp_path) == []


async def test_le_marqueur_navance_pas_si_toutes_editions_refusees(
    tmp_path: Path,
) -> None:
    """Si toutes les éditions proposées sont refusées, le marqueur n'avance pas."""
    _ticket(tmp_path, "ticket-001")
    _doc(tmp_path, "architecture.md", "# Archi\n")
    _avec_marqueur(tmp_path)
    mauvaise = json.dumps(
        {"editions": [{"fichier": "docs/architecture.md", "ancien": "absent", "nouveau": "x"}]}
    )
    svc, _ = _service(tmp_path, [mauvaise, mauvaise])

    resultat = await svc.mettre_a_jour(tmp_path)

    assert resultat.refus
    assert resultat.fichiers_modifies == []
    assert resultat.marqueur_ecrit is False
    # ticket-001 doit réapparaître dans le prochain lot
    assert "ticket-001" in [t.id for t in tickets_a_documenter(tmp_path)]


async def test_sans_ticket_nouveau_aucun_appel(tmp_path: Path) -> None:
    # Un lot vide ne coûte rien : c'est ce qui permet de brancher la mise à
    # jour sur la fin de chaque file sans la payer à chaque fois.
    svc, provider = _service(tmp_path, [])

    resultat = await svc.mettre_a_jour(tmp_path)

    assert provider.appels == []
    assert resultat.fichiers_modifies == []


# ------------------------------------------------------------------
# ticket-228 : les agents voient les fichiers qu'ils modifient
# ------------------------------------------------------------------


async def test_brief_contient_une_section_du_readme(tmp_path: Path) -> None:
    """Le message envoyé au provider contient le texte d'une section de README.md."""
    _ticket(tmp_path, "ticket-001")
    _avec_marqueur(tmp_path)
    (tmp_path / "README.md").write_text(
        "# Mon projet\n\n## Pipeline\n\nLe pipeline enchaîne les agents.\n",
        encoding="utf-8",
    )
    svc, provider = _service(tmp_path, ['{"editions": []}', '{"editions": []}'])

    await svc.mettre_a_jour(tmp_path)

    msg = str(provider.appels[0]["user"])
    assert "Le pipeline enchaîne les agents." in msg


async def test_brief_contient_fichier_docs_sous_son_chemin_relatif(tmp_path: Path) -> None:
    """Un fichier docs/ apparaît sous son chemin relatif dans le message."""
    _ticket(tmp_path, "ticket-001")
    _avec_marqueur(tmp_path)
    _doc(tmp_path, "architecture.md", "# Architecture\n\nSection initiale.\n")
    svc, provider = _service(tmp_path, ['{"editions": []}', '{"editions": []}'])

    await svc.mettre_a_jour(tmp_path)

    msg = str(provider.appels[0]["user"])
    assert "docs/architecture.md" in msg
    assert "Section initiale." in msg


def test_fichier_trop_long_remplace_par_ses_titres_et_borne_respectee(
    tmp_path: Path,
) -> None:
    """Au-delà de la borne, un fichier est remplacé par ses titres et le message
    ne dépasse pas la borne."""
    from tessera.services.documentation import _contenu_documentable

    corps = "paragraphe " * 500  # ~5 500 caractères de corps
    (tmp_path / "README.md").write_text(
        f"# Grand titre\n\n## Section A\n\n{corps}",
        encoding="utf-8",
    )

    borne = 200
    contenu = _contenu_documentable(tmp_path, borne=borne)

    # Les titres sont présents, pas le corps répété
    assert "# Grand titre" in contenu
    assert "## Section A" in contenu
    assert "titres uniquement" in contenu
    assert "paragraphe " * 10 not in contenu
    # La section documentation reste dans la borne (+ tolérance pour les en-têtes fixes)
    assert len(contenu) <= borne + len("\n---\nDocumentation actuelle :\n\n### README.md\n\n") + 100
