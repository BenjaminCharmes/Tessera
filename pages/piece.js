"use strict";
/*
 * Pièce témoin : la pièce de run, la salle des serveurs et la salle de pause, aux
 * abscisses du repère de 800 px de FondDeLaPiece / SalleDeProjet. L'heure choisit le mode.
 */
const LARGEUR_DU_SOL = 800;
const etatPiece = { heure: 10.5, lumiere: true, echelle: 1.5, choix: {} };
try { const v = JSON.parse(localStorage.getItem("atelier-v2") || "{}"); etatPiece.choix = v.choix || {}; } catch (e) { /* stockage indisponible */ }
const modeDe = h => (h >= 7 && h < 19 ? "jour" : "nuit");

/** Un sprite rendu à l'échelle commune : `s` déjà dessiné, `dw` × `dh` sa taille réelle. */
function px(s, dw, dh, mode, { relatif = 1, lumiere = null } = {}) {
  const k = etatPiece.echelle * relatif, b = bake(s, { outline: true, rim: true });
  if (mode === "nuit" && lumiere) eclairer(b, lumiere);
  return { html: toSvg(b, dw * k, dh * k, res(mode, etatPiece.choix)).html, w: dw * k, h: dh * k };
}
/** Un objet posé contre le mur : abscisse du repère, accroche (« bottom:0 », « top:36px »). */
function pose(x, accroche, r, { ombre = false, decal = 0 } = {}) {
  // « sol » : l'objet se tient sur le sol, devant la plinthe, et non sur elle.
  if (accroche === "sol") accroche = `bottom:-${plintheH() + 4}px`;
  const left = `calc(${(x / LARGEUR_DU_SOL) * 100}% + ${decal}px)`;
  const o = ombre ? `<span class="ombre" style="left:calc(${left} - ${r.w * .1}px);bottom:-${r.w * .08}px;width:${r.w * 1.2}px;height:${r.w * .22}px"></span>` : "";
  return `${o}<span class="pose" style="left:${left};${accroche}">${r.html}</span>`;
}
/** Incruste une scène 12 × 8 dans l'écran d'un poste (zone 26, 12), à la place de sa lueur. */
function incruster(poste, scene) {
  poste.layers[5].g.p.fill(null);
  for (const l of scene.layers) {
    const g = new G(poste.w, poste.h);
    l.g.p.forEach((t, i) => { if (t) g.set(26 + (i % scene.w), 12 + Math.floor(i / scene.w), t); });
    poste.layers.push({ g, cls: l.cls, style: l.style });
  }
  return poste;
}
const plintheH = () => 10.5 * etatPiece.echelle / 1.5;
const hhmm = h => `${String(Math.floor(h)).padStart(2, "0")} h ${String(Math.round((h % 1) * 60)).padStart(2, "0")}`;

function entete(titre, sousTitre, pastille) {
  return `<header><span class="pastille" style="background:${ETATS[pastille]}"></span><b>${titre}</b><span class="muted">${sousTitre}</span></header>`;
}

function pieceDeRun(mode) {
  const E1 = etatPiece.echelle, nuit = mode === "nuit", h = etatPiece.heure, allume = nuit && etatPiece.lumiere;
  const mur = fondDeTuile(murEnduit(), 56 * E1 / 1.5, 56 * E1 / 1.5, mode, etatPiece.choix);
  const fondPlinthe = fondDeTuile(plinthe(), 28 * E1 / 1.5, 10.5 * E1 / 1.5, mode, etatPiece.choix, { repeat: "repeat-x" });
  const sol = fondDeTuile(solParquet(), 112 * E1 / 1.5, 21 * E1 / 1.5, mode, etatPiece.choix);
  const fen = i => murFenetre({ jour: !nuit, soleil: i === 1, nuages: i === 1 ? 1 : 2 - (i % 2) });
  let murHtml = "";
  [134, 274, 616].forEach((x, i) => { murHtml += pose(x, "top:36px", px(fen(i), 60, 36, mode)); });
  murHtml += pose(14, "top:24px", px(murTableau(["passe", "passe", "echoue", "attente"]), 88, 54, mode));
  murHtml += pose(208, "sol", px(bibliotheque(), 48, 54, mode), { ombre: true });
  murHtml += pose(348, "sol", px(plante("ficus"), 40, 80, mode), { ombre: true });
  const imp = px(objImprimante(), 72, 42, mode);
  murHtml += pose(392, "sol", imp, { ombre: true });
  murHtml += pose(392, `bottom:${imp.h * 16 / 28 - plintheH() - 4}px`, px(objDossier(), 20, 16, mode), { decal: imp.w * .55 });
  murHtml += pose(488, "top:20px", px(murHorloge(Math.floor(h) % 12 || 12, Math.round((h % 1) * 60)), 16, 16, mode));
  murHtml += pose(470, "sol", px(machineACafe(), 36, 48, mode), { ombre: true });
  murHtml += pose(470, `bottom:${48 * etatPiece.echelle - plintheH()}px`, px(objVapeur(), 36, 24, mode));
  murHtml += pose(528, "top:36px", px(murEtagere(), 32, 20, mode));
  murHtml += pose(528, "sol", px(srvPetiteBaie(), 36, 42, mode), { ombre: true });
  murHtml += pose(572, "sol", px(plante("cactus"), 40, 50, mode), { ombre: true });
  murHtml += pose(634, "sol", px(objCorbeille(2), 20, 24, mode), { ombre: true });
  murHtml += pose(676, "sol", px(objBoite("ci"), 36, 36, mode), { ombre: true });
  murHtml += pose(684, "top:44px", px(murCadre(0), 20, 24, mode));
  murHtml += pose(727, "bottom:40px", px(murInterrupteur(etatPiece.lumiere), 5.5, 8.25, mode));
  murHtml += pose(738, "sol", px(murPorte(), 36, 54, mode, { relatif: 1.5 }));
  murHtml += pose(512, "bottom:-14px", px(debout({ role: "reviewer", ph: PH.reviewer }), 42, 70, mode), { ombre: true });
  [250, 432, 590].forEach(x => {
    const lampe = px(murPlafonnier(!nuit || etatPiece.lumiere), 36, 24, mode);
    if (allume) murHtml += `<span class="cone" style="left:calc(${(x / LARGEUR_DU_SOL) * 100}% - ${lampe.w}px);top:${lampe.h}px;width:${lampe.w * 3}px;height:260px"></span>`;
    murHtml += pose(x, "top:0", lampe);
  });
  const postes = [
    { role: "codeur", etat: "actif", scene: () => srvEcranCode({ ton: "actif" }) },
    { role: "testeur", etat: "attente", scene: null },
    { role: "securite", etat: "blocage", scene: () => srvEcranAudit({ ton: "blocage" }) },
    { role: "reviewer", etat: "attente", scene: null },
    { role: "validateur", etat: "question", scene: () => srvEcranCriteres({ ton: "question" }) },
  ].map(p => {
    let s = poste({ role: p.role, ph: PH[p.role], etat: p.etat });
    if (p.scene) s = incruster(s, p.scene());
    const r = px(s, 70, 63, mode, { lumiere: p.etat });
    return `<div class="poste-cell"><span class="ombre" style="left:${r.w * .02}px;bottom:-${r.w * .06}px;width:${r.w * .96}px;height:${r.w * .14}px"></span>${r.html}</div>`;
  }).join("");
  const voile = nuit && !etatPiece.lumiere ? `<div class="voile"></div>` : "";
  return `<article class="salle">${entete("tessera", "ticket-718 · pièce de run", "actif")}
    <div class="scene"><div class="scene-inner">
      <div class="mur" style="height:144px;background:${mur}">${murHtml}</div>
      <div style="height:${10.5 * E1 / 1.5}px;background:${fondPlinthe}"></div>
      <div class="postes" style="height:124px;background:${sol}">${postes}</div>
      ${voile}
    </div></div></article>`;
}

function salleDesServeurs(mode) {
  const E1 = etatPiece.echelle;
  const mur = fondDeTuile(murEnduit("salle-mur"), 56 * E1 / 1.5, 56 * E1 / 1.5, mode, etatPiece.choix);
  const chemin = fondDeTuile(srvChemin(), 120 * E1, 24 * E1, mode, etatPiece.choix, { cuire: true, repeat: "repeat-x" });
  const dalles = Array.from({ length: 4 }, (_, i) => srvDalle(i === 1));
  const sol = dalles.map(d => fondDeTuile(d, 36 * E1, 36 * E1, mode, etatPiece.choix, { repeat: "no-repeat" }));
  // quatre dalles côte à côte, une perforée : une seule tuile de 4 × 36 px répétée
  const solCss = sol.map((s, i) => s.replace(" 0 0 / ", ` ${i * 36 * E1}px 0 / `).replace("no-repeat", "repeat-x")).join(",");
  const bas = (x, r, o = {}) => pose(x, `bottom:-${6 * E1 + 3}px`, r, { ombre: true, ...o });
  let h = "";
  h += bas(40, px(climatiseur(), 48, 66, mode));
  h += bas(130, px(baieHaute({ etat: "actif", activite: true }), 36, 90, mode));
  h += bas(200, px(baieHaute({ etat: "actif", activite: true }), 36, 90, mode));
  h += bas(270, px(baieHaute({ etat: "blocage" }), 36, 90, mode));
  h += pose(560, "top:56px", px(srvVmc({ regime: "moyen" }), 42, 42, mode));
  h += pose(640, "bottom:44px", px(srvExtincteur(), 18, 42, mode));
  h += bas(700, px(srvPorte(), 42, 54, mode, { relatif: 2 }));
  h += bas(420, px(debout({ role: "securite", ph: PH.securite, expr: "question", tasse: false }), 42, 70, mode));
  return `<article class="salle">${entete("tessera", "salle des serveurs · 3 services, 1 en échec", "blocage")}
    <div class="scene"><div class="scene-inner">
      <div class="mur" style="height:${36 * E1}px;background:${chemin},${mur}"></div>
      <div class="mur" style="height:200px;background:${mur}">${h}</div>
      <div style="height:${6 * E1}px;background:${res(mode, etatPiece.choix)("salle-plinthe.b")}"></div>
      <div style="height:${36 * E1}px;background:${solCss};background-size:${36 * E1 * 4}px ${36 * E1}px"></div>
    </div></div></article>`;
}

function sallePause(mode) {
  const E1 = etatPiece.echelle;
  const mur = fondDeTuile(murEnduit(), 56 * E1 / 1.5, 56 * E1 / 1.5, mode, etatPiece.choix);
  const sol = fondDeTuile(solParquet(), 112 * E1 / 1.5, 21 * E1 / 1.5, mode, etatPiece.choix);
  let h = "";
  h += pose(60, "sol", px(comFrigo(), 30, 54, mode), { ombre: true });
  h += pose(170, "sol", px(comCanape(), 72, 30, mode), { ombre: true });
  h += pose(330, "sol", px(plante("pot"), 40, 50, mode), { ombre: true });
  h += pose(420, "sol", px(comTableReunion(), 72, 36, mode), { ombre: true });
  h += pose(560, "sol", px(comClasseur(), 30, 48, mode), { ombre: true });
  h += pose(640, "top:30px", px(murFenetre({ jour: mode === "jour", soleil: true, nuages: 1 }), 60, 36, mode));
  h += pose(260, "bottom:-10px", px(debout({ role: "codeur", ph: PH.codeur, expr: "fait", tasse: true }), 42, 70, mode), { ombre: true });
  return `<article class="salle">${entete("Salle de pause", "salles communes", "fait")}
    <div class="scene"><div class="scene-inner">
      <div class="mur" style="height:130px;background:${mur}">${h}</div>
      <div style="height:48px;background:${sol}"></div>
    </div></div></article>`;
}

function rendrePiece() {
  const mode = modeDe(etatPiece.heure);
  document.getElementById("heureTxt").textContent = `${hhmm(etatPiece.heure)} · ${mode}`;
  document.getElementById("heure").value = etatPiece.heure;
  document.getElementById("salles").innerHTML = pieceDeRun(mode) + salleDesServeurs(mode) + sallePause(mode);
  document.querySelectorAll("#echelleSeg button").forEach(b => b.setAttribute("aria-pressed", String(+b.dataset.v === etatPiece.echelle)));
}

document.getElementById("heure").addEventListener("input", e => { etatPiece.heure = +e.target.value; rendrePiece(); });
document.getElementById("lumiere").addEventListener("change", e => { etatPiece.lumiere = e.target.checked; rendrePiece(); });
const echelleSeg = document.getElementById("echelleSeg");
for (const v of [0.9, 1.2, 1.5]) {
  const b = document.createElement("button");
  b.type = "button"; b.dataset.v = v; b.textContent = "×" + String(v).replace(".", ",");
  b.addEventListener("click", () => { etatPiece.echelle = v; rendrePiece(); });
  echelleSeg.append(b);
}
let minuterie = null;
document.getElementById("cycle").addEventListener("click", e => {
  if (minuterie) { clearInterval(minuterie); minuterie = null; e.target.textContent = "Faire défiler la journée"; return; }
  e.target.textContent = "Arrêter";
  minuterie = setInterval(() => { etatPiece.heure = (etatPiece.heure + .25) % 24; rendrePiece(); }, 180);
});
rendrePiece();
