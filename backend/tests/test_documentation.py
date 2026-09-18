"""La doc se met à jour par lot, en modifications ciblées — ticket-092."""
import io
import json
from pathlib import Path

import pytest

from vibe_ide.services.documentation import (
    EditionRefusee,
    appliquer_editions,
    tickets_a_documenter,
    marquer_documente,
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
    marquer_documente(tmp_path, "ticket-002")

    assert [t.id for t in tickets_a_documenter(tmp_path)] == ["ticket-003"]


def test_un_marqueur_illisible_ne_bloque_pas(tmp_path: Path) -> None:
    # Mieux vaut re-documenter que ne plus jamais documenter.
    _ticket(tmp_path, "ticket-001")
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "documentation.json").write_text("{ cassé", encoding="utf-8")

    assert [t.id for t in tickets_a_documenter(tmp_path)] == ["ticket-001"]


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
    from vibe_ide.services.documentation import DocumentationService

    prompts = tmp_path / "prompts"
    prompts.mkdir(exist_ok=True)
    for role in ("doc-technique", "doc-fonctionnelle"):
        (prompts / f"{role}.md").write_text(f"prompt {role}", encoding="utf-8")
    provider = _FauxProvider(reponses)
    return DocumentationService(provider, prompts), provider  # type: ignore[arg-type]


async def test_un_lot_de_dix_tickets_fait_deux_appels(tmp_path: Path) -> None:
    # Le point du ticket : documenter par lot, pas par ticket. Dix tickets
    # documentés un par un, ce sont vingt appels ; ici il y en a deux.
    for n in range(1, 11):
        _ticket(tmp_path, f"ticket-{n:03d}")
    _doc(tmp_path, "architecture.md", "# Archi\n\nancien texte\n")
    _doc(tmp_path, "guide-utilisateur.md", "# Guide\n\nancien guide\n")

    svc, provider = _service(tmp_path, ['{"editions": []}', '{"editions": []}'])
    await svc.mettre_a_jour(tmp_path)

    assert len(provider.appels) == 2


async def test_les_deux_agents_recoivent_les_memes_tickets(tmp_path: Path) -> None:
    _ticket(tmp_path, "ticket-001", titre="Ajouter le mode autonome")
    svc, provider = _service(tmp_path, ['{"editions": []}', '{"editions": []}'])

    await svc.mettre_a_jour(tmp_path)

    for appel in provider.appels:
        assert "ticket-001" in str(appel["user"])
        assert "Ajouter le mode autonome" in str(appel["user"])


async def test_les_editions_proposees_sont_appliquees(tmp_path: Path) -> None:
    _ticket(tmp_path, "ticket-001")
    fichier = _doc(tmp_path, "architecture.md", "# Archi\n\ndeux agents\n")
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
    svc, _ = _service(tmp_path, ['{"editions": []}', '{"editions": []}'])

    await svc.mettre_a_jour(tmp_path)

    assert tickets_a_documenter(tmp_path) == []


async def test_sans_ticket_nouveau_aucun_appel(tmp_path: Path) -> None:
    # Un lot vide ne coûte rien : c'est ce qui permet de brancher la mise à
    # jour sur la fin de chaque file sans la payer à chaque fois.
    svc, provider = _service(tmp_path, [])

    resultat = await svc.mettre_a_jour(tmp_path)

    assert provider.appels == []
    assert resultat.fichiers_modifies == []
