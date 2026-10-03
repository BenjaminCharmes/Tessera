"""Chaque agent ne reçoit que les contraintes qui le concernent — tickets 087 et 311."""
from pathlib import Path

from tessera.services.adr import (
    adr_pour,
    contraintes_pour,
    decouper,
    lire_contraintes,
    portee_de,
)

_FICHIER = """# Décisions

Préambule qui n'est pas un ADR.

---

## ADR-001 — Un choix de stack

**Date** : 2025-06
**Portée** : architect
**Décision** : on prend uv.

---

## ADR-002 — Une contrainte de comportement

**Date** : 2026-01
**Décision** : les agents ne touchent pas à git.

---

## ADR-003 — Une règle visuelle

**Date** : 2026-02
**Portée** : codeur, reviewer
**Décision** : cinq familles de couleurs.
"""


def test_le_decoupage_rend_un_bloc_par_adr() -> None:
    blocs = decouper(_FICHIER)

    assert [b.numero for b in blocs] == ["ADR-001", "ADR-002", "ADR-003"]
    assert "uv" in blocs[0].texte


def test_le_preambule_n_est_pas_un_adr() -> None:
    blocs = decouper(_FICHIER)

    assert all("Préambule" not in b.texte for b in blocs)


def test_sans_portee_un_adr_vaut_pour_tous() -> None:
    # Le défaut protège : un ADR non annoté reste devant tous les yeux. Le
    # rater serait silencieux, et une contrainte qu'un agent ignore n'en est
    # plus une.
    blocs = decouper(_FICHIER)

    assert portee_de(blocs[1]) is None


def test_une_portee_declaree_est_lue() -> None:
    blocs = decouper(_FICHIER)

    assert portee_de(blocs[0]) == {"architect"}
    assert portee_de(blocs[2]) == {"codeur", "reviewer"}


def test_un_agent_recoit_ce_qui_le_concerne_et_le_commun() -> None:
    texte = adr_pour(_FICHIER, "codeur")

    assert "ADR-002" in texte  # commun
    assert "ADR-003" in texte  # sa portée
    assert "ADR-001" not in texte  # celle de l'architecte


def test_l_architecte_recoit_les_choix_de_stack() -> None:
    texte = adr_pour(_FICHIER, "architect")

    assert "ADR-001" in texte
    assert "ADR-002" in texte
    assert "ADR-003" not in texte


def test_un_role_inconnu_recoit_toutes_les_contraintes() -> None:
    # Un agent que l'utilisateur vient de créer n'apparaît dans la portée
    # d'aucun ADR. Il reçoit malgré tout tout le tronc commun — et c'est là
    # que sont les contraintes de comportement. Ce qu'il perd, ce sont les
    # choix de stack passés, que personne ne lui demande de rediscuter.
    texte = adr_pour(_FICHIER, "mon-agent-maison")

    assert "ADR-002" in texte
    assert "ADR-001" not in texte
    assert "ADR-003" not in texte


def test_aucune_contrainte_de_comportement_n_est_annotee() -> None:
    # Le verrou du mécanisme : une portée posée par erreur sur une contrainte
    # de comportement la retirerait, en silence, à la plupart des agents.
    reel = Path(__file__).parent.parent.parent / "projects/ide-core/memory/decisions.md"
    contenu = reel.read_text(encoding="utf-8")

    annotes = {b.numero for b in decouper(contenu) if portee_de(b) is not None}

    assert not (annotes & _CONTRAINTES), sorted(annotes & _CONTRAINTES)


#: Les ADR qui énoncent une contrainte de comportement : git, artefacts,
#: périmètre d'écriture, plafonds, verrou de run, portes qui échouent fermées.
#: Une portée posée dessus la retirerait à la plupart des agents. La liste
#: s'allonge à chaque ADR de ce genre : elle s'arrêtait à ADR-031 quand
#: ADR-033 et ADR-037 à 040 existaient déjà (ticket-126).
_CONTRAINTES = {
    "ADR-017", "ADR-018", "ADR-019", "ADR-020", "ADR-021", "ADR-022",
    "ADR-023", "ADR-024", "ADR-025", "ADR-027", "ADR-028", "ADR-029",
    "ADR-030", "ADR-031", "ADR-033", "ADR-037", "ADR-038", "ADR-039",
    "ADR-040", "ADR-042", "ADR-043", "ADR-044", "ADR-045", "ADR-046",
    "ADR-048", "ADR-050",
}

#: Les ADR qui n'enregistrent qu'un choix passé ou une méta-règle sur les
#: ADR eux-mêmes : seul l'architecte a à les rediscuter. Sans portée, ils
#: partiraient dans chaque appel de codeur sans rien lui apprendre.
_CHOIX_PASSES = {
    "ADR-001", "ADR-003", "ADR-032", "ADR-034", "ADR-035", "ADR-036", "ADR-047",
}


def test_les_choix_passes_portent_une_portee() -> None:
    reel = Path(__file__).parent.parent.parent / "projects/ide-core/memory/decisions.md"
    contenu = reel.read_text(encoding="utf-8")

    annotes = {b.numero for b in decouper(contenu) if portee_de(b) is not None}

    assert _CHOIX_PASSES <= annotes, sorted(_CHOIX_PASSES - annotes)


def test_aucun_adr_n_est_a_la_fois_contrainte_et_choix_passe() -> None:
    assert not (_CONTRAINTES & _CHOIX_PASSES)


def test_le_preambule_est_conserve() -> None:
    # Il porte le titre et le format du fichier : le retirer rendrait la
    # section illisible pour l'agent.
    texte = adr_pour(_FICHIER, "codeur")

    assert "Préambule" in texte


def test_un_fichier_vide_ne_casse_rien() -> None:
    assert adr_pour("", "codeur") == ""


def test_le_fichier_reel_reste_lisible() -> None:
    # Garde-fou sur le vrai fichier : si le découpage cesse de reconnaître le
    # format, tous les agents perdraient d'un coup toutes leurs contraintes,
    # sans erreur.
    reel = Path(__file__).parent.parent.parent / "projects/ide-core/memory/decisions.md"
    contenu = reel.read_text(encoding="utf-8")

    blocs = decouper(contenu)

    assert len(blocs) >= 30
    assert all(b.numero.startswith("ADR-") for b in blocs)


def test_le_codeur_recoit_moins_que_tout_sur_le_fichier_reel() -> None:
    reel = Path(__file__).parent.parent.parent / "projects/ide-core/memory/decisions.md"
    contenu = reel.read_text(encoding="utf-8")

    pour_codeur = adr_pour(contenu, "codeur")

    assert len(pour_codeur) < len(contenu)


# ------------------------------------------------------------------
# Le filtrage est réellement appliqué au prompt
# ------------------------------------------------------------------


def test_le_prompt_du_codeur_ne_porte_pas_les_adr_de_l_architecte(
    tmp_path: Path,
) -> None:
    # Un filtre écrit mais jamais branché ne filtre rien : c'est exactement
    # l'erreur que le test des hooks d'ADR-027 empêchait déjà ailleurs.
    from tessera.services.agent_runner import AgentRunner

    runner = AgentRunner(provider=None, registry=None)  # type: ignore[arg-type]
    contexte = f"# projet\n\n## Décisions récentes\n{_FICHIER}"

    pour_codeur = runner._build_user_prompt(_ticket(), "codeur", contexte)
    pour_architecte = runner._build_user_prompt(_ticket(), "architect", contexte)

    assert "ADR-003" in pour_codeur
    assert "ADR-001" not in pour_codeur
    assert "ADR-001" in pour_architecte


def test_un_contexte_sans_section_de_decisions_traverse_intact(
    tmp_path: Path,
) -> None:
    from tessera.services.agent_runner import AgentRunner

    runner = AgentRunner(provider=None, registry=None)  # type: ignore[arg-type]

    prompt = runner._build_user_prompt(_ticket(), "codeur", "# projet\n\nRien ici.")

    assert "Rien ici." in prompt


# ------------------------------------------------------------------
# Tests pour contraintes_pour — ticket-311
# ------------------------------------------------------------------

_EXEMPLE_CONTRAINTES = """# Contraintes en vigueur

## Git et périmètre

- **Ne jamais écrire hors du projet.** (ADR-031)
- **Ne jamais écrire en git.** (ADR-027)

*(codeur, reviewer)*

- **Monaco bundlé localement.** (ADR-012)

## Provider

*(architect, codeur, reviewer)*

- **Passer par LLMProvider.** (ADR-017)
"""


def test_contraintes_regle_universelle_va_a_tous() -> None:
    texte = contraintes_pour(_EXEMPLE_CONTRAINTES, "validateur")

    assert "ADR-031" in texte
    assert "ADR-027" in texte


def test_contraintes_regle_scoped_va_au_bon_role() -> None:
    texte = contraintes_pour(_EXEMPLE_CONTRAINTES, "codeur")

    assert "ADR-012" in texte


def test_contraintes_regle_scoped_ne_va_pas_aux_autres_roles() -> None:
    texte = contraintes_pour(_EXEMPLE_CONTRAINTES, "validateur")

    assert "ADR-012" not in texte


def test_contraintes_regle_multirole_va_au_bon_role() -> None:
    texte = contraintes_pour(_EXEMPLE_CONTRAINTES, "architect")

    assert "ADR-017" in texte


def test_contraintes_regle_multirole_ne_va_pas_aux_autres_roles() -> None:
    texte = contraintes_pour(_EXEMPLE_CONTRAINTES, "validateur")

    assert "ADR-017" not in texte


def test_contraintes_section_reinitialise_la_portee() -> None:
    # Un `## Header` après un bloc scoped remet la portée à universel :
    # les règles qui suivent partent à tous les rôles.
    contenu = (
        "*(codeur)*\n\n"
        "- règle codeur\n\n"
        "## Nouvelle section\n\n"
        "- règle universelle\n"
    )

    texte = contraintes_pour(contenu, "validateur")

    assert "règle codeur" not in texte
    assert "règle universelle" in texte


def test_contraintes_vide_ne_casse_rien() -> None:
    assert contraintes_pour("", "codeur") == ""


def test_contraintes_role_inconnu_recoit_les_universelles() -> None:
    # Un rôle jamais déclaré dans un marqueur reçoit les règles universelles.
    texte = contraintes_pour(_EXEMPLE_CONTRAINTES, "mon-agent-inconnu")

    assert "ADR-031" in texte
    assert "ADR-012" not in texte
    assert "ADR-017" not in texte


# ------------------------------------------------------------------
# Tests pour lire_contraintes — ticket-311
# ------------------------------------------------------------------


def test_lire_contraintes_retourne_contraintes_si_present(tmp_path: Path) -> None:
    memory = tmp_path / "memory"
    memory.mkdir()
    (memory / "contraintes.md").write_text("# Contraintes\n- règle A\n", encoding="utf-8")
    (memory / "decisions.md").write_text("# Décisions\n## ADR-001\n...\n", encoding="utf-8")

    resultat = lire_contraintes(memory)

    assert "règle A" in resultat
    assert "ADR-001" not in resultat


def test_lire_contraintes_retombe_sur_decisions_si_contraintes_absent(tmp_path: Path) -> None:
    memory = tmp_path / "memory"
    memory.mkdir()
    (memory / "decisions.md").write_text("# Décisions\n## ADR-001\ncontenu\n", encoding="utf-8")

    resultat = lire_contraintes(memory)

    assert "ADR-001" in resultat


def test_lire_contraintes_retourne_vide_si_tout_absent(tmp_path: Path) -> None:
    memory = tmp_path / "memory"
    memory.mkdir()

    assert lire_contraintes(memory) == ""


# ------------------------------------------------------------------
# Critères d'acceptation ticket-311 — le prompt reçoit le bon fichier
# ------------------------------------------------------------------


def test_le_prompt_du_codeur_contient_une_regle_de_contraintes_et_non_le_titre_d_un_adr_histoire(
    tmp_path: Path,
) -> None:
    # Avec contraintes.md, le codeur reçoit les règles concises, pas les blocs
    # ADR du journal. « Tauri plutôt qu'Electron » (ADR-004) n'y figure pas.
    memory = tmp_path / "memory"
    memory.mkdir()
    (memory / "contraintes.md").write_text(
        "# Contraintes\n\n## Git\n- **Ne jamais écrire en git.** (ADR-027)\n",
        encoding="utf-8",
    )
    (memory / "decisions.md").write_text(
        "# Décisions\n\n## ADR-004 — Tauri plutôt qu'Electron\n**Date** : 2026\n",
        encoding="utf-8",
    )

    from tessera.services.agent_runner import AgentRunner
    runner = AgentRunner(provider=None, registry=None)  # type: ignore[arg-type]
    contenu = lire_contraintes(memory)
    contexte = f"# projet\n\n## Décisions récentes\n{contenu}"
    prompt = runner._build_user_prompt(_ticket(), "codeur", contexte)

    assert "ADR-027" in prompt
    assert "Tauri plutôt qu'Electron" not in prompt


def test_une_regle_scoped_n_atteint_pas_le_validateur(tmp_path: Path) -> None:
    memory = tmp_path / "memory"
    memory.mkdir()
    (memory / "contraintes.md").write_text(
        "# Contraintes\n\n## Tests\n\n*(codeur, reviewer)*\n\n"
        "- **Vitest + RTL pour les tests.** (ADR-014)\n",
        encoding="utf-8",
    )

    from tessera.services.agent_runner import AgentRunner
    runner = AgentRunner(provider=None, registry=None)  # type: ignore[arg-type]
    contenu = lire_contraintes(memory)
    contexte = f"# projet\n\n## Décisions récentes\n{contenu}"
    prompt = runner._build_user_prompt(_ticket(), "validateur", contexte)

    assert "ADR-014" not in prompt


def test_sans_contraintes_md_le_prompt_recoit_decisions_md(tmp_path: Path) -> None:
    # Sans contraintes.md, le pipeline retombe sur decisions.md : l'ancien
    # comportement est préservé pour les projets qui n'ont pas encore le fichier.
    memory = tmp_path / "memory"
    memory.mkdir()
    (memory / "decisions.md").write_text(
        "# Décisions\n\n## ADR-999 — Une décision passée\n**Date** : 2026\n**Décision** : x.\n",
        encoding="utf-8",
    )

    from tessera.services.agent_runner import AgentRunner
    runner = AgentRunner(provider=None, registry=None)  # type: ignore[arg-type]
    contenu = lire_contraintes(memory)
    contexte = f"# projet\n\n## Décisions récentes\n{contenu}"
    prompt = runner._build_user_prompt(_ticket(), "codeur", contexte)

    assert "ADR-999" in prompt


def _ticket():  # type: ignore[no-untyped-def]
    from tessera.models.ticket import (
        Ticket,
        TicketPriority,
        TicketStatus,
        TicketType,
    )

    return Ticket(
        id="ticket-001",
        title="T",
        type=TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
        body="corps",
        project_id="p",
        file_path="/w/t.md",
        created="",
    )
