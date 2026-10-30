"use strict";
/* Catalogue : par salle, chaque sprite en avant / jour / nuit, et ses matières de jour à choisir. */

const SALLES = [
  ["run", "Pièce de run", "Le mur du fond, les postes et ce qui se pose autour."],
  ["serveurs", "Salle des serveurs", "Le voyant reste le seul élément qui porte l'état du service (ADR-058) ; il gagne un halo."],
  ["communs", "Salles communes", "Pause, réunion, RH, bureau du directeur."],
  ["ambiance", "Ambiance", "Lumière, ciel, sol : ce qui fait le jour et la nuit."],
];
const reglages = { zoom: 3, outline: true, choix: {} };
try { Object.assign(reglages, JSON.parse(localStorage.getItem("atelier-v2") || "{}")); } catch (e) { /* stockage indisponible */ }
const sauver = () => { try { localStorage.setItem("atelier-v2", JSON.stringify(reglages)); } catch (e) { /* idem */ } };

function tuile(classe, titre, html, fond, info) {
  const t = document.createElement("div");
  t.className = "tile " + classe;
  t.innerHTML = `<div class="stage" style="background:${fond}">${html}</div><div class="lab"><b>${titre}</b><span>${info || ""}</span></div>`;
  return t;
}
const opts = mode => ({ mode, zoom: reglages.zoom, outline: reglages.outline, choix: reglages.choix });

/** Où chaque famille apparaît : pour dire qu'un choix touche aussi d'autres sprites. */
const OU = new Map();
for (const def of REGISTRE) for (const f of famillesDe(def.apres())) { if (!OU.has(f)) OU.set(f, []); OU.get(f).push(def.nom); }

function matieres(def, familles) {
  const box = document.createElement("div");
  box.className = "matieres";
  const choisibles = [...familles].filter(f => FAMILLES[f] && FAMILLES[f].chaud).sort();
  if (!choisibles.length) { box.innerHTML = `<span class="muted">Aucune matière à choisir : les teintes de ce sprite sont les mêmes dans les deux palettes de jour.</span>`; return box; }
  box.insertAdjacentHTML("beforeend", `<span class="eyebrow" style="color:var(--muted)">Matières de jour</span>`);
  for (const f of choisibles) {
    const actuel = reglages.choix[f] || JOUR_PAR_DEFAUT[f] || "tessera";
    const autres = (OU.get(f) || []).filter(n => n !== def.nom);
    const m = document.createElement("span");
    m.className = "m";
    m.title = autres.length ? `Aussi dans : ${autres.join(", ")}` : "Seulement dans ce sprite";
    m.innerHTML = `<span>${f}${autres.length ? ` +${autres.length}` : ""}</span>`;
    const seg = document.createElement("span");
    seg.className = "seg small";
    for (const [v, lab] of [["tessera", "Tessera"], ["chaud", "Chaud"]]) {
      const b = document.createElement("button");
      b.type = "button"; b.textContent = lab; b.setAttribute("aria-pressed", String(actuel === v));
      b.setAttribute("aria-label", `${f} : ${lab}`);
      b.addEventListener("click", () => {
        if (v === (JOUR_PAR_DEFAUT[f] || "tessera")) delete reglages.choix[f]; else reglages.choix[f] = v;
        sauver(); tout();
      });
      seg.append(b);
    }
    m.append(seg); box.append(m);
  }
  return box;
}

function carte(def) {
  const c = document.createElement("div");
  c.className = "card";
  c.id = "s-" + def.id;
  c.innerHTML = `<div class="card-head"><h3>${def.nom}${def.avant ? "" : ' <span class="badge new">nouveau</span>'}</h3><span class="mono">${def.fichier} · ${def.grille}</span></div>`;
  const row = document.createElement("div");
  row.className = "compare";
  if (def.avant) { const a = rendre(def, { ...opts("jour"), quoi: "avant" }); row.append(tuile("before", "Avant", a.html, C.sol, `${a.rects} rect`)); }
  if (def.meme) { const m = rendre(def, { ...opts("jour"), quoi: "meme" }); row.append(tuile("after", "Même grille", m.html, solDe("jour", reglages.choix), `${m.nodes} paths`)); }
  const j = rendre(def, opts("jour"));
  row.append(tuile("after", "Jour", j.html, solDe("jour", reglages.choix), `${j.nodes} paths · ${j.pixels} px`));
  const n = rendre(def, opts("nuit"));
  row.append(tuile("after", "Nuit", n.html, solDe("nuit"), `${n.nodes} paths`));
  if (def.variante) {
    const v = rendre(def, { ...opts("jour"), quoi: "variante" });
    const vn = rendre(def, { ...opts("nuit"), quoi: "variante" });
    row.append(tuile("after", def.variante.label, v.html + vn.html, solDe("jour", reglages.choix), "jour · nuit"));
  }
  const note = document.createElement("p");
  note.className = "note"; note.textContent = def.note;
  c.append(row, note, matieres(def, j.familles));
  return c;
}

function tout() {
  const host = document.getElementById("sections");
  const blocs = [];
  for (const [salle, titre, sous] of SALLES) {
    const defs = REGISTRE.filter(d => d.salle === salle);
    if (!defs.length) continue;
    const sec = document.createElement("section");
    sec.id = salle;
    sec.innerHTML = `<div class="sec-head"><span class="eyebrow">${defs.length} sprite${defs.length > 1 ? "s" : ""}</span><h2>${titre}</h2><p class="muted">${sous}</p></div>`;
    const cards = document.createElement("div");
    cards.className = "cards";
    cards.append(...defs.map(carte));
    sec.append(cards);
    blocs.push(sec);
  }
  blocs.push(nouveaux());
  host.replaceChildren(...blocs);
  document.querySelectorAll("#zoomSeg button").forEach(b => b.setAttribute("aria-pressed", String(+b.dataset.v === reglages.zoom)));
  document.getElementById("outlineChk").checked = reglages.outline;
}

/** Les sprites sans équivalent aujourd'hui : visages par santé, marche. */
function nouveaux() {
  const sec = document.createElement("section");
  sec.id = "nouveaux";
  sec.innerHTML = `<div class="sec-head"><span class="eyebrow">Proposition</span><h2>Visages et marche</h2><p class="muted">Le visage suit la santé de l'agent ; la marche remplace la glissade d'un bloc.</p></div>`;
  const z = reglages.zoom, cards = document.createElement("div");
  cards.className = "cards";
  const c1 = document.createElement("div");
  c1.className = "card";
  c1.innerHTML = `<div class="card-head"><h3>Visage selon la santé <span class="badge new">nouveau</span></h3><span class="mono">Tete · lit SanteAgent</span></div>`;
  const r1 = document.createElement("div");
  r1.className = "compare";
  for (const [e, lib] of [["actif", "actif"], ["attente", "attente"], ["question", "question"], ["blocage", "blocage_suspecte"], ["fait", "fait"]]) {
    const html = ["jour", "nuit"].map(mode => {
      const s = mk(18, 16); tete(s.L(), 3, 4, PH.codeur, e);
      return toSvg(bake(s, { outline: reglages.outline }), 30 * z, 27 * z, res(mode, reglages.choix)).html;
    }).join("");
    r1.append(tuile("after", lib, html, solDe("jour", reglages.choix)));
  }
  c1.append(r1);
  const c2 = document.createElement("div");
  c2.className = "card";
  c2.innerHTML = `<div class="card-head"><h3>Cycle de marche <span class="badge new">nouveau</span></h3><span class="mono">AgentDebout · 4 images · 24 × 40</span></div>`;
  const r2 = document.createElement("div");
  r2.className = "compare";
  for (const mode of ["jour", "nuit"]) {
    const images = MARCHE.map((f, i) => `<div class="frame" style="animation-delay:${i * .16}s">${toSvg(bake(debout({ role: "codeur", ph: PH.codeur, expr: "neutre", tasse: false, ...f }), { outline: reglages.outline }), 42 * z, 70 * z, res(mode, reglages.choix)).html}</div>`);
    r2.append(tuile("after", mode, `<div class="slide-anim"><div class="stack">${images.join("")}</div></div>`, solDe(mode, reglages.choix), "0,64 s par pas"));
  }
  c2.append(r2);
  cards.append(c1, c2);
  sec.append(cards);
  return sec;
}

const zoomSeg = document.getElementById("zoomSeg");
for (const [v, lab] of [[1, "×1 réel"], [2, "×2"], [3, "×3"], [4, "×4"]]) {
  const b = document.createElement("button");
  b.type = "button"; b.dataset.v = v; b.textContent = lab;
  b.addEventListener("click", () => { reglages.zoom = v; sauver(); tout(); });
  zoomSeg.append(b);
}
document.getElementById("outlineChk").addEventListener("change", e => { reglages.outline = e.target.checked; sauver(); tout(); });
document.getElementById("copyBtn").addEventListener("click", () => {
  const texte = JSON.stringify(reglages.choix);
  const out = document.getElementById("copyOut");
  navigator.clipboard.writeText(texte).then(() => { out.textContent = "Copié : " + texte; }, () => { out.textContent = texte; });
});
tout();
