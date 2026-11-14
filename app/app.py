"""Lot E · E2 : interface CaseForge (Streamlit).

    streamlit run app/app.py

Trois colonnes : texte original (entités colorées), texte anonymisé, fiche pédagogique ; puis validation par
l'enseignant, enregistrée dans reports/journal_validation.jsonl. Palier Bronze ou Silver (pipeline local) : type de
passage e5 (Lot C), cas similaires LaBSE (Lot E), comparaison Bronze / Silver. Trois sources possibles :
  - « Exemple factice » : tests/fixtures/pipeline_exemple.json (contrat), pour développer sans le pipeline ;
  - « Pipeline local » : caseforge.pipeline.traiter (Lot E · E1) ;
  - « API » : POST {url}/pipeline (Lot E · E3), même format.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import streamlit as st

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from app.rendu import (  # noqa: E402
    bloc,
    cas_similaires_markdown,
    comparaison_ptypes,
    entree_journal,
    fiche_markdown,
    journaliser,
    legende,
    surligner,
    surligner_pseudonymes,
)

EXEMPLE = RACINE / "tests" / "fixtures" / "pipeline_exemple.json"

LOGO = RACINE / "web" / "static" / "logo.svg"
STYLE = """
<style>
  .block-container { padding-top: 1.6rem; }
  .cf-entete { display:flex; align-items:center; gap:14px; padding:14px 18px; border-radius:16px; margin-bottom:10px;
    background: linear-gradient(120deg, rgba(79,70,229,.12), rgba(13,148,136,.12));
    border:1px solid rgba(79,70,229,.25); }
  .cf-entete img { width:52px; height:52px; filter: drop-shadow(0 6px 14px rgba(79,70,229,.35)); }
  .cf-entete h1 { font-size:1.65rem; margin:0; padding:0; letter-spacing:-.02em; }
  .cf-entete .studio { background:linear-gradient(90deg,#4f46e5,#0d9488); -webkit-background-clip:text;
    background-clip:text; color:transparent; }
  .cf-entete p { margin:2px 0 0; opacity:.75; font-size:.92rem; }
  .cf-pastille { font-size:.72rem; font-weight:700; padding:3px 10px; border-radius:999px; margin-left:auto;
    background:linear-gradient(90deg,#c7d2fe,#99f6e4); color:#1e1b4b; white-space:nowrap; }
  .cf-etapes { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:4px 0 6px; }
  .cf-etape { display:flex; gap:10px; font-size:.86rem; }
  .cf-etape b { display:block; }
  .cf-num { flex:none; width:26px; height:26px; border-radius:50%; display:grid; place-items:center; color:#fff;
    font-weight:700; font-size:.8rem; background:linear-gradient(135deg,#4f46e5,#0d9488); }
  div[data-testid="stMetric"] { border:1px solid rgba(128,128,128,.25); border-radius:14px; padding:12px 16px;
    box-shadow:0 8px 24px -14px rgba(30,41,59,.35); }
  div[data-testid="stExpander"] { border-radius:14px; }
  .stButton > button[kind="primary"] { background:linear-gradient(90deg,#4f46e5,#0d9488); border:none;
    box-shadow:0 8px 20px -8px rgba(79,70,229,.7); }
  section[data-testid="stSidebar"] h2 { font-size:1.15rem; }
  @media (max-width: 900px) { .cf-etapes { grid-template-columns:1fr 1fr; } }
</style>
"""
GUIDE = [
    ("Choisissez la source", "« Pipeline local » pour analyser votre texte ; « Exemple factice » pour découvrir."),
    ("Réglez le palier", "Bronze : règles et TF-IDF. Silver : type de passage e5, cas similaires LaBSE."),
    ("Collez le document", "FR, AR ou EN, un paragraphe par ligne vide, puis « Analyser »."),
    ("Relisez et validez", "Comparez original, anonymisé et fiche ; un enseignant valide la fiche."),
]


def logo_data_uri() -> str:
    """Logo du projet en data URI (affiché sans serveur de fichiers)."""
    import base64

    return "data:image/svg+xml;base64," + base64.b64encode(LOGO.read_bytes()).decode("ascii")


st.set_page_config(page_title="CaseForge", page_icon="📄", layout="wide")
st.markdown(STYLE, unsafe_allow_html=True)
st.markdown(
    f'<div class="cf-entete"><img src="{logo_data_uri()}" alt="CaseForge">'
    '<div><h1>CaseForge <span class="studio">· interface d\'évaluation</span></h1>'
    "<p>Du besoin industriel à l'étude de cas : anonymisée, sourcée, validable (FR · AR · EN).</p></div>"
    '<span class="cf-pastille">Paliers Bronze et Silver</span></div>',
    unsafe_allow_html=True,
)
with st.expander("Mode d'emploi", expanded=False):
    st.markdown(
        '<div class="cf-etapes">'
        + "".join(
            f'<div class="cf-etape"><span class="cf-num">{i}</span><div><b>{t}</b>{d}</div></div>'
            for i, (t, d) in enumerate(GUIDE, 1)
        )
        + "</div>",
        unsafe_allow_html=True,
    )
st.caption("Proposition générée automatiquement : elle doit être relue et validée par un enseignant avant tout usage.")

with st.sidebar:
    st.header("Réglages")
    source = st.radio(
        "Source",
        ["Exemple factice", "Pipeline local", "API"],
        index=0,
        help="Exemple factice : sortie du contrat, sans calcul. Pipeline local : votre texte, sur ce PC. "
        "API : le serveur FastAPI (uvicorn api.main:app).",
    )
    url = st.text_input("Adresse de l'API", "http://127.0.0.1:8000", disabled=source != "API")
    langue = st.selectbox("Langue", ["auto", "fr", "ar", "en"], help="« auto » détecte la langue du document.")
    st.subheader("Palier")
    palier = st.radio(
        "Palier",
        ["Bronze", "Silver"],
        index=1,
        horizontal=True,
        disabled=source != "Pipeline local",
        help="Bronze : briques classiques. Silver : modèles appris (encodeurs multilingues).",
    )
    silver = source == "Pipeline local" and palier == "Silver"
    ptype_e5 = st.checkbox(
        "Type de passage e5 (Lot C, 0,948)",
        value=True,
        disabled=not silver,
        help="Encodeur e5 + TF-IDF + position : macro-F1 0,948 contre 0,896 au Bronze (dev).",
    )
    similaires = st.checkbox(
        "Cas similaires LaBSE (Lot E, P@5 0,36)",
        value=True,
        disabled=not silver,
        help="Les 3 cas du train les plus proches. Premier usage : téléchargement du modèle (≈ 1,8 Go).",
    )
    comparer = st.checkbox(
        "Comparer avec le Bronze",
        value=True,
        disabled=not silver,
        help="Relance le Bronze sur le même texte et montre les types de passage qui changent.",
    )
    st.info(
        "Fiche LLM (Lot D) et anonymisation XLM-R (Lot B) : GPU nécessaire, démontrées dans leurs notebooks. "
        "Interface web alternative : `uvicorn web.serveur:app --port 8600`.",
        icon="ℹ️",
    )
    st.markdown("**Légende des entités**", unsafe_allow_html=True)
    st.markdown(legende(), unsafe_allow_html=True)


@st.cache_data
def exemple() -> dict:
    return json.loads(EXEMPLE.read_text(encoding="utf-8"))


def lancer(texte: str) -> dict:
    if source == "Exemple factice":
        return exemple()
    if source == "Pipeline local":
        from caseforge.pipeline import traiter

        if not silver:
            return traiter(texte, langue)
        options = {"ptype": "e5" if ptype_e5 else "tfidf", "recherche": "dense" if similaires else None}
        sortie = traiter(texte, langue, **options)
        sortie["palier"] = "Silver"
        if comparer:
            sortie["bronze"] = traiter(texte, langue)
        return sortie
    req = urllib.request.Request(
        f"{url.rstrip('/')}/pipeline",
        method="POST",
        data=json.dumps({"texte": texte, "langue": langue}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


texte_exemple = "\n\n".join(p["text"] for p in exemple()["passages"])
texte = st.text_area(
    "Texte du besoin industriel (paragraphes séparés par une ligne vide)",
    help="Collez un e-mail, un compte rendu ou un formulaire. Le texte reste sur ce PC.",
    value=texte_exemple if source == "Exemple factice" else "",
    height=180,
    disabled=source == "Exemple factice",
)

if st.button("Analyser", type="primary"):
    try:
        with st.spinner("Traitement…"):
            st.session_state["sortie"] = lancer(texte)
    except ValueError as e:
        st.error(f"Entrée invalide : {e}")
    except Exception as e:  # API absente, réseau, etc.
        st.error(f"Échec du traitement : {e}")

s = st.session_state.get("sortie")
if s:
    m = s.get("metriques", {})
    c0, c1, c2, c3, c4 = st.columns(5)
    c0.metric("Palier", s.get("palier", "Bronze"))
    c1.metric("Langue", s["lang"])
    c2.metric("Passages", len(s["passages"]))
    c3.metric("Fuites détectées", m.get("fuites_detectees", "—"))
    c4.metric("Temps", f"{m['temps_ms']} ms" if m.get("temps_ms") is not None else "—")
    if m.get("fuites_detectees"):
        st.warning("Un nom masqué apparaît encore dans la sortie : ne pas diffuser avant correction.")
    for alerte in m.get("alertes", []):
        st.warning(f"Alerte : {alerte}")
    with st.expander("Détails du traitement (mode debug)"):
        st.write("Passages, types et entités prédits, remplacements et fiche, tels que renvoyés par le pipeline :")
        st.json(s, expanded=False)

    if "bronze" in s:
        tableau, changes = comparaison_ptypes(s["bronze"], s)
        fb, fs = s["bronze"]["metriques"].get("fuites_detectees", 0), m.get("fuites_detectees", 0)
        with st.expander(
            f"Bronze / Silver : {changes} type(s) de passage changé(s), fuites {fb} → {fs}", expanded=True
        ):
            st.markdown(tableau)
    if "cas_similaires" in s:
        with st.expander("Cas similaires du train (recherche dense LaBSE sur les termes métier)", expanded=True):
            st.markdown(cas_similaires_markdown(s["cas_similaires"]))

    anon = {p["passage_id"]: p["texte"] for p in s["anonymise"]["passages"]}
    g, mil, d = st.columns(3)
    with g:
        st.subheader("Original")
        for p in s["passages"]:
            st.markdown(
                f"<small>{p['passage_id'].rsplit('_', 1)[-1]} · {p.get('ptype', '')}</small>", unsafe_allow_html=True
            )
            st.markdown(bloc(surligner(p["text"], p["entities"])), unsafe_allow_html=True)
    with mil:
        st.subheader("Anonymisé")
        for p in s["passages"]:
            st.markdown(f"<small>{p['passage_id'].rsplit('_', 1)[-1]}</small>", unsafe_allow_html=True)
            st.markdown(bloc(surligner_pseudonymes(anon.get(p["passage_id"], ""))), unsafe_allow_html=True)
    with d:
        st.subheader("Fiche pédagogique")
        st.markdown(f'<div dir="auto">\n\n{fiche_markdown(s["fiche"], s["lang"])}\n\n</div>', unsafe_allow_html=True)
        st.download_button(
            "Télécharger la sortie (JSON)",
            json.dumps(s, ensure_ascii=False, indent=1),
            file_name=f"{s['doc_id']}.json",
            mime="application/json",
        )

    st.divider()
    st.subheader("Validation enseignante")
    with st.form("validation"):
        nom = st.text_input("Validé par")
        commentaire = st.text_area("Commentaire", height=80)
        ok, non = st.columns(2)
        valider = ok.form_submit_button("✅ Valider la fiche")
        rejeter = non.form_submit_button("❌ Rejeter la fiche")
    if valider or rejeter:
        try:
            e = entree_journal(s["doc_id"], "validee" if valider else "rejetee", nom, commentaire)
            journaliser(e)
            s["validation"] = {k: e[k] for k in ("statut", "valide_par", "date", "commentaire")}
            st.success(f"Décision enregistrée : {e['statut']} par {e['valide_par']}.")
        except ValueError as err:
            st.error(str(err))
