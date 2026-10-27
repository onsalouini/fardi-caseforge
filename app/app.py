"""Lot E · E2 : interface CaseForge (Streamlit).

    streamlit run app/app.py

Trois colonnes : texte original (entités colorées), texte anonymisé, fiche pédagogique ; puis validation par
l'enseignant, enregistrée dans reports/journal_validation.jsonl. Trois sources possibles pour la sortie :
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
    entree_journal,
    fiche_markdown,
    journaliser,
    legende,
    surligner,
    surligner_pseudonymes,
)

EXEMPLE = RACINE / "tests" / "fixtures" / "pipeline_exemple.json"

st.set_page_config(page_title="CaseForge", page_icon="📄", layout="wide")
st.title("CaseForge · du besoin industriel à l'étude de cas")
st.caption("Proposition générée automatiquement : elle doit être relue et validée par un enseignant avant tout usage.")

with st.sidebar:
    st.header("Réglages")
    source = st.radio("Source", ["Exemple factice", "Pipeline local", "API"], index=0)
    url = st.text_input("Adresse de l'API", "http://127.0.0.1:8000", disabled=source != "API")
    langue = st.selectbox("Langue", ["auto", "fr", "ar", "en"])
    st.markdown("**Légende**", unsafe_allow_html=True)
    st.markdown(legende(), unsafe_allow_html=True)


@st.cache_data
def exemple() -> dict:
    return json.loads(EXEMPLE.read_text(encoding="utf-8"))


def lancer(texte: str) -> dict:
    if source == "Exemple factice":
        return exemple()
    if source == "Pipeline local":
        from caseforge.pipeline import traiter

        return traiter(texte, langue)
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
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Langue", s["lang"])
    c2.metric("Passages", len(s["passages"]))
    c3.metric("Fuites détectées", m.get("fuites_detectees", "—"))
    c4.metric("Temps", f"{m['temps_ms']} ms" if m.get("temps_ms") is not None else "—")
    if m.get("fuites_detectees"):
        st.warning("Un nom masqué apparaît encore dans la sortie : ne pas diffuser avant correction.")

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
