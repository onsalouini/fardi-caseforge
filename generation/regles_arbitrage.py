"""LOT D (Gold) : application aux 242 textes libres v4 des règles d'annotation arbitrées le 25/11/2026.

Contexte : kappa Boutheina / Ali 0,695 sur 37 passages (``reports/gold_kappa_v4_1.md``) ; arbitrage à trois (Boutheina,
Ali, Ons) de quatre règles du guide v2 (``reports/gold_kappa_v4_1_arbitrage.md``) :

1. ce qui sert à produire (machine, robot, ligne, logiciel) = EQUIPEMENT ; ce qui est produit ou vendu = PRODUIT ;
2. CONTRAINTE = l'exigence entière, sans l'introduction (« Nous devons veiller à ce que… », « ensure that… ») ;
3. PERSONNE = un nom (titre compris), jamais une fonction ni un groupe (« étudiants », « ingénieur méthodes ») ;
4. PROCESSUS = une méthode ou une opération qui a un nom (« amélioration continue », « changement de série »), pas
   une tâche du projet (« analyser ces données ») ni un mot générique (« production »).

Les règles 1 et 3 ne demandent aucune correction dans l'annotation d'Ons. Ce script **propose** des corrections pour
les règles 2 et 4 ; chaque proposition est acceptée ou refusée par un humain dans une page de validation, puis
seules les propositions acceptées sont appliquées (aucune annotation automatique n'entre sans validation).

    python generation/regles_arbitrage.py proposer
    python generation/regles_arbitrage.py appliquer decisions_regles_ons.json

``proposer`` -> ``data/gold/libres_v4/arbitrage/propositions.jsonl`` et ``…/valider.html`` ;
``appliquer`` -> ``data/gold/libres_v4/annotations_ons_v2.json`` puis réintégration (``textes_libres.integrer``).
Rien ici ne lit le dev ni le test gelé.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "generation"))
sys.path.insert(0, str(RACINE))

import textes_libres as T  # noqa: E402

DOSSIER = T.DOSSIER / "arbitrage"
ANNOTATIONS = T.DOSSIER / "annotations_ons.json"
ANNOTATIONS_V2 = T.DOSSIER / "annotations_ons_v2.json"

# Règle 2 : introductions d'une contrainte (à retirer du span), en tête du span seulement.
INTRO_CONTRAINTE = re.compile(
    r"^(nous devons (également )?veiller à ce que|il est (important|nécessaire|essentiel) de|il faut"
    r"|we (must|need to) ensure that|ensure that|please note that|it is (important|essential|necessary) to"
    r"|we must|nous devons|من المهم أن|يجب أن نتأكد من أن)\s+",
    re.IGNORECASE,
)
# Règle 4 : méthodes et opérations nommées (manuels de génie industriel), fr / en / ar.
METHODES = re.compile(
    r"amélioration continue|continuous improvement|التحسين المستمر|changements? de série|changeovers?"
    r"|تغيير السلسلة|\bSMED\b|\b5S\b|\b8D\b|DMAIC|QRQC|Kaizen|Kanban|Lean|AMDEC|FMEA|Ishikawa"
    r"|5 (?:Whys|pourquoi)|Poka[- ]?Yoke|\bTPM\b|cartographie des flux|value stream mapping"
    r"|maintenance préventive|preventive maintenance|الصيانة الوقائية|qualification des équipements",
    re.IGNORECASE,
)


def proposer(passages: list[dict], annotations: dict[str, list[dict]]) -> list[dict]:
    """Propositions de correction (règles 2 et 4) sur l'annotation vérifiée, une par entité touchée."""
    props: list[dict] = []
    for p in passages:
        ents = annotations[p["passage_id"]]
        for e in ents:
            m = INTRO_CONTRAINTE.match(e["text"]) if e["label"] == "CONTRAINTE" else None
            if m and e["text"][m.end() :].strip():
                debut = e["start"] + m.end()
                props.append(
                    {
                        "regle": 2,
                        "passage_id": p["passage_id"],
                        "avant": e,
                        "apres": {**e, "start": debut, "text": p["text"][debut : e["end"]]},
                    }
                )
        for m in METHODES.finditer(p["text"]):
            if any(x["start"] < m.end() and m.start() < x["end"] for x in ents):
                continue  # déjà dans une entité (une contrainte qui cite l'opération reste une contrainte)
            nouv = {"start": m.start(), "end": m.end(), "label": "PROCESSUS", "text": m.group(0)}
            props.append({"regle": 4, "passage_id": p["passage_id"], "avant": None, "apres": nouv})
    for i, x in enumerate(props):
        x["id"] = f"R{x['regle']}-{i:03d}"
    return props


def appliquer(annotations: dict[str, list[dict]], props: list[dict], acceptees: set[str]) -> dict[str, list[dict]]:
    """Applique seulement les propositions acceptées ; contrôle qu'aucune entité ne se chevauche ensuite."""
    out = {k: [dict(e) for e in v] for k, v in annotations.items()}
    for x in props:
        if x["id"] not in acceptees:
            continue
        ents = out[x["passage_id"]]
        if x["avant"] is not None:
            i = next(
                i
                for i, e in enumerate(ents)
                if (e["start"], e["end"], e["label"]) == (x["avant"]["start"], x["avant"]["end"], x["avant"]["label"])
            )
            ents[i] = dict(x["apres"])
        else:
            ents.append(dict(x["apres"]))
        ents.sort(key=lambda e: e["start"])
        for a, b in zip(ents, ents[1:], strict=False):
            if b["start"] < a["end"]:
                raise SystemExit(f"{x['passage_id']} : chevauchement après {x['id']}")
    return out


def ecrire_page(passages: dict[str, dict], props: list[dict], chemin: Path) -> None:
    """Page autonome : une carte par proposition, Accepter / Refuser, export des décisions (JSON)."""
    cartes = []
    for x in props:
        p = passages[x["passage_id"]]
        cartes.append(
            {
                "id": x["id"],
                "regle": x["regle"],
                "passage_id": x["passage_id"],
                "lang": p["lang"],
                "texte": p["text"],
                "avant": x["avant"],
                "apres": x["apres"],
            }
        )
    page = PAGE.replace("__CARTES__", json.dumps(cartes, ensure_ascii=False))
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(page, encoding="utf-8")


PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Règles arbitrées · textes libres v4</title>
<style>
:root{--fond:#f7f7f5;--carte:#fff;--texte:#1d1d1b;--doux:#6b6b66;--bord:#e2e1dc;--ok:#1f7a4d;--non:#b3261e;
--avant:#fde7e4;--apres:#dff3e8}
body{margin:0;background:var(--fond);color:var(--texte);font:15px/1.55 system-ui,sans-serif}
header{position:sticky;top:0;background:var(--fond);border-bottom:1px solid var(--bord);padding:12px 16px;z-index:1}
h1{font-size:17px;margin:0 0 4px}.barre{display:flex;gap:12px;align-items:center;flex-wrap:wrap;color:var(--doux)}
main{max-width:860px;margin:0 auto;padding:16px}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:10px;padding:14px 16px;margin:0 0 12px}
.carte.ok{border-color:var(--ok)}.carte.non{border-color:var(--non);opacity:.7}
.meta{font-size:13px;color:var(--doux);margin-bottom:6px}.texte{white-space:pre-wrap}
.texte[dir=rtl]{text-align:right}.avant{background:var(--avant)}.apres{background:var(--apres);font-weight:600}
.diff{margin:8px 0;font-size:14px}button{font:inherit;border:1px solid var(--bord);background:#fff;border-radius:8px;
padding:6px 14px;cursor:pointer}button.ok{border-color:var(--ok);color:var(--ok)}button.non{border-color:var(--non);
color:var(--non)}button:active{transform:translateY(1px)}#exporter{background:var(--texte);color:#fff;border:0}
</style></head><body>
<header><h1>Règles arbitrées le 25/11 · validation de l'annotation d'Ons</h1>
<div class="barre"><span id="compte"></span><button id="exporter">Exporter mes décisions</button></div></header>
<main id="liste"></main>
<script>
const CARTES=__CARTES__;const CLE="cf_regles_arbitrees_v1";
let dec={};try{dec=JSON.parse(localStorage.getItem(CLE)||"{}")}catch(e){}
const REGLES={2:"Règle 2 · contrainte sans son introduction",4:"Règle 4 · méthode nommée → PROCESSUS"};
function esc(s){return s.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}
function marque(t,s,e,cl){return esc(t.slice(0,s))+'<span class="'+cl+'">'+esc(t.slice(s,e))+"</span>"+esc(t.slice(e))}
function rendre(){const L=document.getElementById("liste");L.innerHTML="";let n=0;
for(const c of CARTES){const d=dec[c.id];if(d)n++;const div=document.createElement("div");
div.className="carte"+(d==="ok"?" ok":d==="non"?" non":"");const rtl=c.lang==="ar"?' dir="rtl"':"";
let diff;if(c.avant){diff='<div class="diff">Avant : <span class="avant">'+esc(c.avant.text)+
'</span><br>Après : <span class="apres">'+esc(c.apres.text)+"</span> ("+c.apres.label+")</div>"}
else{diff='<div class="diff">Ajouter : <span class="apres">'+esc(c.apres.text)+"</span> en "+c.apres.label+"</div>"}
div.innerHTML='<div class="meta">'+c.id+" · "+REGLES[c.regle]+" · <code>"+c.passage_id+"</code></div>"+diff+
'<div class="texte"'+rtl+">"+marque(c.texte,c.apres.start,c.apres.end,"apres")+"</div>"+
'<p><button class="ok">Accepter</button> <button class="non">Refuser</button></p>';
div.querySelector(".ok").onclick=()=>{dec[c.id]="ok";sauver()};div.querySelector(".non").onclick=()=>{dec[c.id]="non";sauver()};
L.appendChild(div)}document.getElementById("compte").textContent=n+" / "+CARTES.length+" décidées"}
function sauver(){try{localStorage.setItem(CLE,JSON.stringify(dec))}catch(e){}rendre()}
document.getElementById("exporter").onclick=()=>{const manque=CARTES.filter(c=>!dec[c.id]).length;
if(manque&&!confirm(manque+" proposition(s) sans décision : elles seront refusées. Exporter quand même ?"))return;
const blob=new Blob([JSON.stringify({annotateur:"ons",date:new Date().toISOString(),decisions:dec},null,1)],
{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);
a.download="decisions_regles_ons.json";a.click()};rendre();
</script></body></html>
"""


def charger_passages() -> list[dict]:
    return T.lire_jsonl(T.DOSSIER / "passages.jsonl")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]  # console Windows (cp1252)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = ap.add_subparsers(dest="etape", required=True)
    sous.add_parser("proposer")
    a = sous.add_parser("appliquer")
    a.add_argument("decisions", type=Path, help="fichier exporté par la page de validation")
    args = ap.parse_args()
    passages = charger_passages()
    annotations = {p["passage_id"]: p["entities"] for p in passages}
    if args.etape == "proposer":
        props = proposer(passages, annotations)
        T.ecrire_jsonl(DOSSIER / "propositions.jsonl", props)
        ecrire_page({p["passage_id"]: p for p in passages}, props, DOSSIER / "valider.html")
        par_regle = {r: sum(x["regle"] == r for x in props) for r in (2, 4)}
        print(
            f"{len(props)} propositions (règle 2 : {par_regle[2]}, règle 4 : {par_regle[4]}) "
            f"-> {DOSSIER / 'valider.html'}"
        )
        return
    props = T.lire_jsonl(DOSSIER / "propositions.jsonl")
    decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
    acceptees = {k for k, v in decisions["decisions"].items() if v == "ok"}
    corrigees = appliquer(annotations, props, acceptees)
    # base = l'export d'origine (267 passages, avant nettoyage) ; les passages gardés reçoivent leur version corrigée
    origine = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    export = {
        "annotateur": "ons",
        "date": decisions.get("date"),
        "note": f"règles arbitrées du 25/11/2026 ; {len(acceptees)} / {len(props)} propositions acceptées par Ons",
        "annotations": [
            {"passage_id": a["passage_id"], "entities": corrigees.get(a["passage_id"], a["entities"])}
            for a in origine["annotations"]
        ],
    }
    ANNOTATIONS_V2.write_text(json.dumps(export, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(acceptees)} / {len(props)} propositions appliquées -> {ANNOTATIONS_V2}")
    preannotes = T.lire_jsonl(T.DOSSIER / "a_verifier/passages_preannotes.jsonl")
    n = T.integrer(T.lire_jsonl(T.DOSSIER / "plan.jsonl"), preannotes, export)
    print(f"{n} passages réintégrés -> {T.DOSSIER / 'passages.jsonl'}")


if __name__ == "__main__":
    main()
