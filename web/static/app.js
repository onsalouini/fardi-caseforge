// CaseForge Studio : logique de la page (aucune dépendance externe). Tout texte venu du document est échappé.
"use strict";

const COULEURS = {
  ORG: "#e8590c", PERSONNE: "#c2255c", SITE: "#9c36b5", DONNEE_SENSIBLE: "#e03131", PRODUIT: "#2f9e44",
  EQUIPEMENT: "#1971c2", PROCESSUS: "#0c8599", INDICATEUR: "#f08c00", CONTRAINTE: "#5c940d",
};
const NOMS = {
  ORG: "Organisation", PERSONNE: "Personne", SITE: "Site", DONNEE_SENSIBLE: "Donnée sensible", PRODUIT: "Produit",
  EQUIPEMENT: "Équipement", PROCESSUS: "Processus", INDICATEUR: "Indicateur", CONTRAINTE: "Contrainte",
};
const RUBRIQUES = {
  fr: ["Contexte", "Objectifs", "Données", "Contraintes", "Consignes", "Livrables", "Critères d'évaluation"],
  en: ["Context", "Objectives", "Data", "Constraints", "Instructions", "Deliverables", "Assessment criteria"],
  ar: ["السياق", "الأهداف", "المعطيات", "القيود", "التعليمات", "المخرجات", "معايير التقييم"],
};
const MENTIONS = {
  fr: { vide: "Rien d'extrait pour cette rubrique.", fixe: "texte fixe" },
  en: { vide: "Nothing extracted for this section.", fixe: "fixed text" },
  ar: { vide: "لا شيء مستخرج لهذا القسم.", fixe: "نص ثابت" },
};
const CLES = ["contexte", "objectifs", "donnees", "contraintes", "consignes", "livrables", "criteres_evaluation"];
const ETAPES = [
  "Découpage en passages et détection de la langue…", "Repérage des entités (règles du Lot B)…",
  "Anonymisation : pseudonymes cohérents…", "Type de chaque passage…", "Génération de la fiche sous schéma…",
  "Recherche des cas similaires…", "Contrôle des fuites…",
];

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const etat = { palier: "Silver", exemples: {}, sortie: null };

function esc(t) {
  return String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function court(pid) { return String(pid).split("_").pop(); }
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toast.minuteur); toast.minuteur = setTimeout(() => (t.hidden = true), 3200);
}

// ---------- Thème, guide, infobulles ----------
function initialiserTheme() {
  let enregistre = null;
  try { enregistre = localStorage.getItem("cf-theme"); } catch (e) { /* stockage indisponible */ }
  if (enregistre) document.documentElement.dataset.theme = enregistre;
  $("#bouton-theme").addEventListener("click", () => {
    const sombre = matchMedia("(prefers-color-scheme: dark)").matches;
    const actuel = document.documentElement.dataset.theme || (sombre ? "sombre" : "clair");
    const suivant = actuel === "sombre" ? "clair" : "sombre";
    document.documentElement.dataset.theme = suivant;
    try { localStorage.setItem("cf-theme", suivant); } catch (e) { /* rien */ }
  });
}
function initialiserGuide() {
  let masque = false;
  try { masque = localStorage.getItem("cf-guide") === "masque"; } catch (e) { /* rien */ }
  $("#guide").hidden = masque;
  $("#fermer-guide").addEventListener("click", () => {
    $("#guide").hidden = true;
    try { localStorage.setItem("cf-guide", "masque"); } catch (e) { /* rien */ }
  });
  $("#bouton-aide").addEventListener("click", () => {
    $("#guide").hidden = !$("#guide").hidden;
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}
function initialiserInfobulles() {
  const bulle = $("#infobulle");
  document.addEventListener("mouseover", (e) => {
    const cible = e.target.closest("[data-aide]");
    if (!cible) { bulle.hidden = true; return; }
    bulle.textContent = cible.dataset.aide; bulle.hidden = false;
    const r = cible.getBoundingClientRect();
    bulle.style.left = Math.min(r.left, innerWidth - 300) + "px";
    bulle.style.top = r.bottom + 8 + "px";
  });
}

// ---------- Réglages ----------
function initialiserReglages() {
  $$(".segment button").forEach((b) => b.addEventListener("click", () => {
    etat.palier = b.dataset.palier;
    $$(".segment button").forEach((x) => {
      x.classList.toggle("actif", x === b); x.setAttribute("aria-checked", String(x === b));
    });
    $("#options-silver").classList.toggle("inactif", etat.palier === "Bronze");
  }));
  const legende = $("#legende");
  for (const [lab, c] of Object.entries(COULEURS)) {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = NOMS[lab]; b.style.borderColor = c; b.style.color = c;
    b.dataset.aide = lab === "DONNEE_SENSIBLE" || ["ORG", "PERSONNE", "SITE"].includes(lab)
      ? "Entité sensible : elle doit être masquée dans la version anonymisée." : "Entité métier : gardée pour la fiche.";
    b.addEventListener("click", () => { b.classList.toggle("eteint"); document.body.classList.toggle("sans-" + lab); });
    legende.appendChild(b);
  }
}
async function verifierSante() {
  try {
    const r = await fetch("/api/sante");
    const s = await r.json();
    const p = $("#etat-silver");
    p.classList.add(s.silver_disponible ? "ok" : "ko");
    p.dataset.aide = s.silver_disponible
      ? "Briques Silver installées (sentence-transformers)."
      : "sentence-transformers absent : seul le Bronze fonctionnera.";
  } catch (e) { /* serveur injoignable : l'erreur s'affichera à l'analyse */ }
}

// ---------- Saisie ----------
function mettreAJourCompteur() {
  const t = $("#texte").value;
  const paragraphes = t.split(/\n\s*\n/).filter((b) => b.trim()).length;
  $("#compteur").textContent = `${t.length} caractère${t.length > 1 ? "s" : ""} · ${paragraphes} paragraphe${paragraphes > 1 ? "s" : ""}`;
}
async function initialiserSaisie() {
  try { etat.exemples = await (await fetch("/api/exemples")).json(); } catch (e) { etat.exemples = {}; }
  $$("[data-exemple]").forEach((b) => b.addEventListener("click", () => {
    $("#texte").value = etat.exemples[b.dataset.exemple] || "";
    $("#langue").value = b.dataset.exemple;
    mettreAJourCompteur(); $("#texte").focus();
  }));
  $("#texte").addEventListener("input", mettreAJourCompteur);
  $("#texte").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) analyser(); });
  $("#effacer").addEventListener("click", () => { $("#texte").value = ""; mettreAJourCompteur(); $("#texte").focus(); });
  $("#analyser").addEventListener("click", analyser);
  mettreAJourCompteur();
  // Démo : ?exemple=fr|ar|en charge l'exemple et lance l'analyse (pratique en soutenance)
  const demande = new URLSearchParams(location.search).get("exemple");
  if (demande && etat.exemples[demande]) {
    $("#texte").value = etat.exemples[demande];
    $("#langue").value = demande;
    mettreAJourCompteur();
    analyser();
  }
}

// ---------- Analyse ----------
async function analyser() {
  const texte = $("#texte").value;
  if (!texte.trim()) { toast("Collez un document ou choisissez un exemple."); return; }
  const corps = {
    texte, langue: $("#langue").value, palier: etat.palier,
    ptype_e5: $("#ptype-e5").checked, similaires: $("#similaires").checked, comparer: $("#comparer").checked,
  };
  $("#analyser").disabled = true; $("#erreur").hidden = true; $("#chargement").hidden = false;
  let i = 0;
  $("#etape-chargement").textContent = ETAPES[0];
  const minuteur = setInterval(() => { i = (i + 1) % ETAPES.length; $("#etape-chargement").textContent = ETAPES[i]; }, 1800);
  try {
    const r = await fetch("/api/analyser", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps),
    });
    const s = await r.json();
    if (!r.ok) throw new Error(typeof s.detail === "string" ? s.detail : "Entrée invalide.");
    etat.sortie = s;
    afficher(s);
    $("#resultats").hidden = false;
    $("#resultats").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    $("#erreur").textContent = "Échec du traitement : " + e.message; $("#erreur").hidden = false;
  } finally {
    clearInterval(minuteur); $("#chargement").hidden = true; $("#analyser").disabled = false;
  }
}

// ---------- Rendu ----------
function surligner(texte, entites) {
  const tries = [...(entites || [])].sort((a, b) => a.start - b.start || b.end - a.end);
  let out = "", pos = 0;
  for (const e of tries) {
    if (e.start < pos) continue;
    const c = COULEURS[e.label] || "#868e96";
    out += esc(texte.slice(pos, e.start));
    out += `<mark class="ent ent-${esc(e.label)}" style="background:${c}22;border-bottom-color:${c}" data-aide="${esc(NOMS[e.label] || e.label)}">`
      + `${esc(texte.slice(e.start, e.end))}<sup style="color:${c}">${esc(e.label)}</sup></mark>`;
    pos = e.end;
  }
  return (out + esc(texte.slice(pos))).replace(/\n/g, "<br>");
}
function pseudonymes(texte) {
  return esc(texte).replace(/\[[A-Z_]+(?:_[A-Z0-9]+)?\]/g, (m) => `<span class="pseudo" data-aide="Pseudonyme : la valeur réelle est masquée.">${m}</span>`)
    .replace(/\n/g, "<br>");
}
function blocPassage(p, contenu, prefixe) {
  return `<div class="passage" id="${prefixe}-${esc(p.passage_id)}" dir="auto">
    <div class="meta"><span>${esc(court(p.passage_id))}</span>${p.ptype ? `<span class="type">${esc(p.ptype)}</span>` : ""}</div>
    <div class="texte">${contenu}</div></div>`;
}
function elementsDe(v) { return v == null ? [] : Array.isArray(v) ? v : [v]; }
function ficheHTML(fiche, lang) {
  const noms = RUBRIQUES[lang] || RUBRIQUES.fr;
  const mention = MENTIONS[lang] || MENTIONS.fr;
  let html = fiche.titre ? `<div class="titre-fiche" dir="auto"><strong>${esc(fiche.titre.texte)}</strong></div>` : "";
  CLES.forEach((cle, i) => {
    const els = elementsDe(fiche[cle]);
    html += `<div class="rubrique" dir="auto"><h4>${esc(noms[i])}</h4>`;
    if (!els.length) { html += `<p class="vide">${esc(mention.vide)}</p></div>`; return; }
    html += "<ul>" + els.map((e) => {
      const sources = (e.sources || []).map((s) =>
        `<button type="button" class="source" data-source="${esc(s)}" data-aide="Voir le passage source">${esc(court(s))}</button>`).join("");
      const origine = e.origine === "gabarit" ? `<span class="origine-gabarit">(${esc(mention.fixe)})</span>` : "";
      return `<li>${esc(e.texte)}${sources}${origine}</li>`;
    }).join("") + "</ul></div>";
  });
  return html;
}
function indicateur(nom, valeur, classe = "") {
  return `<div class="carte indicateur ${classe}"><div class="petit">${esc(nom)}</div><div class="valeur">${esc(valeur)}</div></div>`;
}
function afficher(s) {
  const m = s.metriques || {};
  const fuites = m.fuites_detectees ?? (s.fuites ? s.fuites.length : 0);
  const temps = s.duree_totale_ms != null ? s.duree_totale_ms : m.temps_ms;
  $("#indicateurs").innerHTML =
    indicateur("Palier", s.palier || "Bronze") + indicateur("Langue", (s.lang || "?").toUpperCase())
    + indicateur("Passages", s.passages.length) + indicateur("Fuites détectées", fuites, fuites ? "mauvais" : "bon")
    + indicateur("Temps", temps != null ? (temps >= 1000 ? (temps / 1000).toFixed(1) + " s" : temps + " ms") : "—");
  let alertes = "";
  if (fuites) alertes += `<div class="alerte grave">Un nom masqué apparaît encore dans la sortie : ne pas diffuser avant correction.</div>`;
  for (const a of m.alertes || []) alertes += `<div class="alerte">${esc(a)}</div>`;
  if (s.controle) {
    const na = s.controle.ajouts.length, no = s.controle.omissions.length;
    alertes += na || no
      ? `<div class="alerte">Contrôle de la fiche (Lot D) : ${na} ajout(s) et ${no} omission(s) à vérifier — onglet « Fiche pédagogique ».</div>`
      : `<div class="alerte ok">Contrôle de la fiche (Lot D) : aucun ajout ni omission détecté.</div>`;
  }
  $("#alertes").innerHTML = alertes;

  const anon = Object.fromEntries((s.anonymise?.passages || []).map((p) => [p.passage_id, p.texte]));
  $("#col-original").innerHTML = s.passages.map((p) => blocPassage(p, surligner(p.text, p.entities), "orig")).join("");
  $("#col-anonyme").innerHTML = s.passages.map((p) => blocPassage(p, pseudonymes(anon[p.passage_id] || ""), "anon")).join("");
  $("#col-fiche").innerHTML = ficheHTML(s.fiche, s.lang);
  $("#fiche-complete").innerHTML = ficheHTML(s.fiche, s.lang);
  $("#controle-fiche").innerHTML = controleHTML(s.controle);
  $("#json").textContent = JSON.stringify(s, null, 1);

  // Bronze ↔ Silver
  const bronze = s.bronze;
  $("#onglet-comparaison").hidden = !bronze;
  if (bronze) {
    const types = Object.fromEntries(bronze.passages.map((p) => [p.passage_id, p.ptype]));
    let changes = 0;
    const lignes = s.passages.map((p) => {
      const avant = types[p.passage_id] || "—", change = avant !== p.ptype;
      if (change) changes++;
      return `<tr><td>${esc(court(p.passage_id))}</td><td dir="auto">${esc(p.text.slice(0, 90))}${p.text.length > 90 ? "…" : ""}</td>
        <td>${esc(avant)}</td><td class="${change ? "change" : ""}">${esc(p.ptype)}${change ? " ⬅" : ""}</td></tr>`;
    }).join("");
    const fb = bronze.metriques?.fuites_detectees ?? 0;
    $("#comparaison").innerHTML = `<h2>Bronze ↔ Silver</h2>
      <p class="petit">${changes} type(s) de passage changé(s) · fuites ${fb} → ${fuites}.</p>
      <table><thead><tr><th>Passage</th><th>Début du texte</th><th>Bronze (TF-IDF)</th><th>Silver (e5)</th></tr></thead><tbody>${lignes}</tbody></table>`;
  }
  // Cas similaires
  const cas = s.cas_similaires;
  $("#onglet-similaires").hidden = !cas;
  if (cas) {
    $("#similaires-liste").innerHTML = `<h2>Cas similaires du train</h2>
      <p class="petit">Recherche dense LaBSE sur les termes métier prédits ; aucune donnée de référence n'entre dans le pipeline.</p>`
      + (cas.length ? cas.map((c, i) => `<div class="cas"><span class="rang">${i + 1}</span>
          <div><strong>${esc(c.doc_id)}</strong><div class="petit">secteur : ${esc(c.secteur)} · langue : ${esc(c.lang)}</div></div>
          <div class="jauge-bloc"><div class="petit">similarité ${Number(c.score).toFixed(3)}</div>
          <div class="jauge"><span style="width:${Math.max(4, Math.min(100, c.score * 100))}%"></span></div></div></div>`).join("")
        : `<p class="vide">Aucun terme métier reconnu : pas de cas similaire proposé.</p>`);
  }
  ouvrirOnglet("vue");
}

// ---------- Contrôle des ajouts et omissions (Lot D, Gold) ----------
const MOTIFS = { nombre_absent: "nombre absent du document", non_ancre: "aucun passage ne porte cet élément" };
function controleHTML(c) {
  if (!c) return "";
  const lignes = (els, rendu) => els.length ? "<ul>" + els.map(rendu).join("") + "</ul>" : `<p class="vide">Aucun.</p>`;
  return `<div class="controle"><h3>Contrôle automatique <small>Lot D · à vérifier avant de valider</small></h3>
    <div class="deux-colonnes">
      <div><h4>Ajouts possibles (${c.ajouts.length})</h4>${lignes(c.ajouts, (a) =>
        `<li dir="auto">${esc(a.texte)} <span class="motif">${esc(a.rubrique)} · ${esc(MOTIFS[a.motif] || a.motif)}${
          Array.isArray(a.detail) ? " : " + esc(a.detail.join(", ")) : ""}</span></li>`)}</div>
      <div><h4>Omissions possibles (${c.omissions.length})</h4>${lignes(c.omissions, (o) =>
        `<li dir="auto">${esc(o.texte)} <span class="motif">${esc(NOMS[o.label] || o.label)}</span>
         <button type="button" class="source" data-source="${esc(o.passage_id)}" data-aide="Voir le passage source">${esc(court(o.passage_id))}</button></li>`)}</div>
    </div>
    <p class="petit">Contrôle lexical : il repère les nombres inventés et les contraintes ou indicateurs oubliés, pas les inventions de sens. Il guide la relecture sans la remplacer.</p>
    <p class="petit">Anonymisation : un texte tapé ici est anonymisé par le Bronze (règles), car le modèle XLM-R n'est pas chargé dans Studio. Le gel Gold du Lot B (XLM-R v4) ne s'applique qu'aux documents du dev : fuite 6,6 % → 0,9 % de bout en bout (reports/gold_bout_en_bout.md).</p></div>`;
}

// ---------- Explications XLM-R (Lot C, Gold) ----------
const CATEGORIES = { correcte: "correcte", bornes: "erreur de bornes", "étiquette": "erreur d'étiquette", manquee: "manquée", "manquée": "manquée", en_trop: "en trop", "en trop": "en trop" };
async function chargerExplications() {
  const zone = $("#explications");
  if (zone.dataset.charge) return;
  zone.innerHTML = `<p class="petit">Chargement…</p>`;
  try {
    const r = await fetch("/api/explications");
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "indisponible");
    zone.dataset.charge = "1";
    const cats = [...new Set(d.cas.map((c) => c.categorie))];
    zone.innerHTML = `<h2>Pourquoi XLM-R a-t-il prédit cette entité ?</h2>
      <p class="petit">Gradients intégrés (Lot C) sur XLM-R v4, ${d.cas.length} cas du dev calculés hors ligne. Vert : le mot pousse vers l'étiquette ; rouge : il l'en éloigne. L'entité est encadrée.</p>
      <div class="filtres">${["toutes", ...cats].map((c, i) =>
        `<button type="button" class="puce${i ? "" : " actif"}" data-categorie="${esc(c)}">${esc(CATEGORIES[c] || c)}</button>`).join("")}</div>
      <div id="liste-explications">${d.cas.map(casHTML).join("")}</div>`;
    zone.querySelectorAll("[data-categorie]").forEach((b) => b.addEventListener("click", () => {
      zone.querySelectorAll("[data-categorie]").forEach((x) => x.classList.toggle("actif", x === b));
      zone.querySelectorAll(".cas-expl").forEach((el) =>
        (el.hidden = b.dataset.categorie !== "toutes" && el.dataset.categorie !== b.dataset.categorie));
    }));
  } catch (e) {
    zone.innerHTML = `<p class="vide">Explications indisponibles : ${esc(e.message)}</p>`;
  }
}
function casHTML(c) {
  const e = c.entite || {};
  const mots = (c.mots || []).map((m) => {
    const v = Math.max(-1, Math.min(1, Number(m.score) || 0));
    const fond = v >= 0 ? `rgba(47,158,68,${(0.75 * v).toFixed(2)})` : `rgba(224,49,49,${(-0.75 * v).toFixed(2)})`;
    const dans = m.start >= e.start && m.end <= e.end ? " dans-entite" : "";
    return `<span class="mot${dans}" style="background:${fond}" data-aide="score ${v.toFixed(2)}">${esc(m.texte)}</span>`;
  }).join(" ");
  const etiq = (x) => (x ? `${esc(NOMS[x.label] || x.label)}` : "—");
  return `<div class="cas-expl" data-categorie="${esc(c.categorie)}">
    <div class="meta"><strong>#${esc(c.id)}</strong> · ${esc(CATEGORIES[c.categorie] || c.categorie)} · ${esc((c.langue || "").toUpperCase())} · ${esc(c.passage_id)}
      · référence : ${etiq(c.gold)} · prédiction : ${etiq(c.prediction)} · part sur l'entité ${Math.round(100 * (c.part_attribution_entite || 0))} %</div>
    <div class="phrase" dir="auto">${mots}</div></div>`;
}

// ---------- Interactions des résultats ----------
function ouvrirOnglet(nom) {
  $$(".onglets button").forEach((b) => b.classList.toggle("actif", b.dataset.onglet === nom));
  $$(".panneau-onglet").forEach((p) => (p.hidden = p.dataset.panneau !== nom));
}
function initialiserResultats() {
  $$(".onglets button").forEach((b) => b.addEventListener("click", () => {
    ouvrirOnglet(b.dataset.onglet);
    if (b.dataset.onglet === "explications") chargerExplications();
  }));
  document.addEventListener("click", (e) => {
    const src = e.target.closest("[data-source]");
    if (!src) return;
    ouvrirOnglet("vue");
    for (const pre of ["orig", "anon"]) {
      const el = document.getElementById(`${pre}-${src.dataset.source}`);
      if (!el) continue;
      el.classList.add("eclaire");
      if (pre === "orig") el.scrollIntoView({ behavior: "smooth", block: "center" });
      setTimeout(() => el.classList.remove("eclaire"), 2200);
    }
  });
  $("#telecharger").addEventListener("click", () => {
    if (!etat.sortie) return;
    const blob = new Blob([JSON.stringify(etat.sortie, null, 1)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `${etat.sortie.doc_id || "fiche"}.json`; a.click();
    URL.revokeObjectURL(a.href);
  });
  $("#copier-fiche").addEventListener("click", async () => {
    const texte = $("#fiche-complete").innerText;
    try { await navigator.clipboard.writeText(texte); toast("Fiche copiée dans le presse-papiers."); }
    catch (e) { toast("Copie impossible dans ce navigateur."); }
  });
  $$("[data-statut]").forEach((b) => b.addEventListener("click", async () => {
    if (!etat.sortie) return;
    const valide_par = $("#valide-par").value.trim();
    if (!valide_par) { toast("Indiquez le nom de l'enseignant."); $("#valide-par").focus(); return; }
    const r = await fetch("/api/validation", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: etat.sortie.doc_id, statut: b.dataset.statut, valide_par, commentaire: $("#commentaire").value }),
    });
    const d = await r.json();
    toast(r.ok ? `Décision enregistrée : ${d.statut === "validee" ? "fiche validée" : "fiche rejetée"} par ${d.valide_par}.`
      : "Échec : " + (d.detail || "entrée invalide"));
  }));
}

initialiserTheme();
initialiserGuide();
initialiserInfobulles();
initialiserReglages();
initialiserSaisie();
initialiserResultats();
verifierSante();
