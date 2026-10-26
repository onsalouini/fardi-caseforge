"""B1 — rapport ``reports/lotb_baseline_regles.md`` : règles (``cfdata.prelabel``) contre CRF, sur le dev.

    python -m scripts.eval_prelabel && python -m scripts.run_crf_baseline && python -m scripts.report_b1_baseline

Tous les chiffres du rapport sont recalculés ici à partir des prédictions de ``results/lotb/`` ; le bootstrap est
écrit dans ``results/lotb/b1_bootstrap.json``.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

import cfdata.pools as P
from caseforge.eval.bootstrap import paired_bootstrap
from caseforge.eval.data import FINAL, REPORTS, RESULTS, charger_dev, ecrire_json
from caseforge.eval.ner_metrics import INVENTE, MANQUE, evaluate, match_partial
from caseforge.labels import LABELS
from cfdata.common import read_jsonl
from cfdata.prelabel import R_ORG, R_PER, gazetteer

LABELS_GAZETTEER = ("PRODUIT", "EQUIPEMENT", "PROCESSUS")
TRAIN_JSONL = FINAL / "train.jsonl"


def f(x: float) -> str:
    """Nombre à 3 décimales, virgule décimale."""
    return f"{x:.3f}".replace(".", ",")


def _moy_ecart(x: dict[str, float]) -> str:
    """« moyenne ± écart-type » à 3 décimales."""
    return f"{f(x['moyenne'])} ± {f(x['ecart_type'])}"


def _sous_ensemble(rows: list[dict], ids: set[str]) -> list[dict]:
    return [r for r in rows if r["passage_id"] in ids]


def _ids_source(gold: list[dict], prefixe: str) -> set[str]:
    return {g["passage_id"] for g in gold if g["doc_id"].startswith(prefixe)}


def _extrait(text: str, s: int, e: int, marge: int = 30) -> str:
    """Court extrait autour du span, le span entre crochets, sans retour à la ligne ni barre verticale."""
    avant = ("…" if s > marge else "") + text[max(0, s - marge) : s]
    apres = text[e : e + marge] + ("…" if e + marge < len(text) else "")
    return f"{avant}[{text[s:e]}]{apres}".replace("\n", " ").replace("|", "/")


def erreurs_franches(gold: list[dict], pred: list[dict]) -> tuple[list[dict], list[dict]]:
    """Faux positifs et faux négatifs sans aucun chevauchement de même étiquette (mode partiel)."""
    pmap = {p["passage_id"]: p for p in pred}
    fps, fns = [], []
    for g in gold:
        sg = [(e["start"], e["end"], e["label"]) for e in g["entities"]]
        sp = [(e["start"], e["end"], e["label"]) for e in pmap[g["passage_id"]]["entities"]]
        pairs = match_partial(sg, sp)
        mg, mp = {i for i, _ in pairs}, {j for _, j in pairs}
        fns += [{"pid": g["passage_id"], "span": x, "text": g["text"]} for i, x in enumerate(sg) if i not in mg]
        fps += [{"pid": g["passage_id"], "span": x, "text": g["text"]} for j, x in enumerate(sp) if j not in mp]
    return fps, fns


def _echantillon(erreurs: list[dict], n: int = 10) -> list[dict]:
    """Échantillon déterministe : tour de rôle entre étiquettes, en alternant les sources d'un choix à l'autre."""
    pool: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for x in sorted(erreurs, key=lambda x: (x["pid"], x["span"][0])):
        pool[(x["span"][2], x["pid"][:4])].append(x)
    sources = sorted({src for _, src in pool})
    out: list[dict] = []
    k = 0
    while len(out) < n and any(pool.values()):
        for lab in LABELS:
            if len(out) >= n:
                break
            # source préférée à ce tour, sinon l'autre
            for src in sources[k % len(sources) :] + sources[: k % len(sources)]:
                if pool[(lab, src)]:
                    out.append(pool[(lab, src)].pop(0))
                    k += 1
                    break
    return out


def _table(entete: list[str], lignes: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(entete) + " |", "|" + "---|" * len(entete)] + [
        "| " + " | ".join(r) + " |" for r in lignes
    ]


def main() -> None:  # noqa: C901 - rapport linéaire, section par section
    """Calcule toutes les comparaisons et écrit le rapport Markdown."""
    gold = charger_dev()
    regles = read_jsonl(RESULTS / "b1_prelabel_dev.jsonl")
    crf = read_jsonl(RESULTS / "b1_crf_dev.jsonl")
    resume_crf = json.loads((RESULTS / "b1_crf_dev_summary.json").read_text(encoding="utf-8"))
    R, C = evaluate(gold, regles), evaluate(gold, crf)
    sous = resume_crf["sous_echantillons"]
    agr = sous["agrege"]
    complet = resume_crf["complet"]
    deterministe = "oui" if resume_crf["deterministe"] else "non"
    pl = resume_crf["plafond_tokens"]
    cv = json.loads((RESULTS / "b1_prelabel_lib_cv.json").read_text(encoding="utf-8"))

    boot = {
        f"{m}_{a}": paired_bootstrap(gold, regles, crf, mode=m, average=a)
        for m, a in (("strict", "micro"), ("partiel", "micro"), ("strict", "macro_9"))
    }
    ecrire_json(RESULTS / "b1_bootstrap.json", boot)

    L: list[str] = [
        "# Lot B · B1 — Baseline par règles (`cfdata.prelabel`) et CRF sur le dev",
        "",
        f"Dev uniquement ({R['n_passages']} passages, {R['n_documents']} documents ; test gelé non lu). "
        "Harnais `caseforge.eval.ner_metrics` : **strict** = bornes et étiquette exactes, **partiel** = "
        "chevauchement ≥ 1 caractère et même étiquette. F1 macro (9) = moyenne sur les 9 étiquettes.",
        "",
        "Règles : `cfdata.prelabel.predict` (`scripts/eval_prelabel.py`). CRF : `exemples/baseline_crf.py`, mêmes "
        "caractéristiques et hyperparamètres (`scripts/run_crf_baseline.py`), prédictions BIO reconverties en "
        "caractères. Plafond tokens = F1 stricte du gold lui-même passé en BIO sur les tokens de "
        "`cfdata.common.tokenize` puis reconverti (`token_ceiling`) : le maximum atteignable par un modèle BIO.",
        "",
        "## 1. Résultat global",
        "",
    ]
    lignes = []
    for nom, res in (("Règles", R), ("CRF (train complet)", C)):
        for mode in ("strict", "partiel"):
            g = res[mode]["global"]
            lignes.append(
                [
                    nom,
                    mode,
                    f(g["micro"]["p"]),
                    f(g["micro"]["r"]),
                    f(g["micro"]["f1"]),
                    f(g["macro_9"]["f1"]),
                    f(g["macro_presentes"]["f1"]),
                ]
            )
    for mode in ("strict", "partiel"):
        a, m = agr[f"harnais_{mode}_f1_micro"], agr[f"harnais_{mode}_f1_macro_9"]
        lignes.append(
            [
                "CRF (90 % du train, 3 tirages)",
                mode,
                "—",
                "—",
                f"{f(a['moyenne'])} ± {f(a['ecart_type'])}",
                f"{f(m['moyenne'])} ± {f(m['ecart_type'])}",
                "—",
            ]
        )
    lignes.append(["Plafond tokens", "strict", "—", "—", f(pl["global"]), "—", "—"])
    L += _table(["Système", "Mode", "P micro", "R micro", "F1 micro", "F1 macro (9)", "F1 macro (présentes)"], lignes)
    L += [
        "",
        "**Variance du CRF.** `sklearn-crfsuite` (L-BFGS) est déterministe et n'a pas de paramètre de graine (l'option "
        "`--seed` de `baseline_crf.py` n'est pas utilisée) : deux entraînements identiques donnent les mêmes "
        f"prédictions ({deterministe}). Changer de graine ne mesure donc rien. La variance est mesurée en "
        f"réentraînant le CRF sur {len(sous['graines'])} sous-échantillons de "
        f"{round(100 * sous['fraction_documents'])} % des documents du train (tirés avec les graines "
        f"{', '.join(map(str, sous['graines']))}) : moyenne ± écart-type ci-dessus. C'est une variance due aux "
        "données d'entraînement, pas à l'optimisation. Le bootstrap (section 6) utilise le CRF du train complet.",
        "",
        "### Reproduction de la valeur de référence du CRF (0,393)",
        "",
    ]
    L += _table(
        ["Mesure", "Global", "fr", "ar", "en"],
        [
            [
                "Script d'origine (spans de tokens, gold BIO)",
                f(complet["script_origine"]["f1_micro_spans_tokens"]),
                *[f(complet["script_origine"]["par_langue"].get(k, 0.0)) for k in ("fr", "ar", "en")],
            ],
            [
                "Harnais strict (spans de caractères)",
                f(C["strict"]["global"]["micro"]["f1"]),
                *[f(C["strict"]["par_langue"][k]["micro"]["f1"]) for k in ("fr", "ar", "en")],
            ],
            [
                "Plafond tokens : gold BIO reconverti en caractères",
                f(pl["global"]),
                *[f(pl["par_langue"][k]) for k in ("fr", "ar", "en")],
            ],
        ],
    )
    L += [
        "",
        "On retrouve exactement 0,393 avec le calcul du script d'origine. L'écart avec le harnais vient de l'unité "
        "de comparaison : le script compare des spans de **tokens** au gold BIO, le harnais compare des spans de "
        "**caractères** au gold `dev.jsonl`. Le gold BIO est construit par chevauchement (`spans_to_bio`) : un span "
        "qui ne tombe pas sur des frontières de tokens (proclitique arabe collé, ponctuation, mot partiel) ne peut "
        f"pas être retrouvé exactement. Même le gold BIO reconverti n'atteint que {f(pl['global'])} "
        "en strict : c'est le plafond de tout modèle BIO sur ces tokens. Par langue, le script d'origine ventile "
        "selon `lang` du passage (les 4 passages mixtes sont à part), le harnais selon `doc_lang`.",
        "",
        "## 2. Par étiquette",
        "",
    ]
    L += _table(
        ["Étiquette", "Gold", "Règles strict", "Règles partiel", "CRF strict", "CRF partiel"],
        [
            [
                lab,
                str(R["strict"]["par_etiquette"][lab]["support_gold"]),
                f(R["strict"]["par_etiquette"][lab]["f1"]),
                f(R["partiel"]["par_etiquette"][lab]["f1"]),
                f(C["strict"]["par_etiquette"][lab]["f1"]),
                f(C["partiel"]["par_etiquette"][lab]["f1"]),
            ]
            for lab in LABELS
        ],
    )
    L += ["", "F1 par étiquette. Les règles n'ont aucune règle SITE : F1 = 0 par construction.", ""]

    for titre, cle, cles in (
        ("## 3. Par langue (`doc_lang`)", "par_langue", ("fr", "ar", "en")),
        ("## 4. Par source", "par_source", ("syn", "lib")),
    ):
        L += [titre, ""]
        L += _table(
            [
                "Tranche",
                "Passages",
                "Gold",
                "Règles strict",
                "Règles partiel",
                "Règles macro (9)",
                "CRF strict",
                "CRF 90 % strict",
                "Plafond tokens",
                "CRF partiel",
                "CRF macro (9)",
            ],
            [
                [
                    k,
                    str(R["strict"][cle][k]["n_passages"]),
                    str(R["strict"][cle][k]["support_gold"]),
                    f(R["strict"][cle][k]["micro"]["f1"]),
                    f(R["partiel"][cle][k]["micro"]["f1"]),
                    f(R["strict"][cle][k]["macro_9"]["f1"]),
                    f(C["strict"][cle][k]["micro"]["f1"]),
                    _moy_ecart(agr[f"harnais_strict_{cle}"][k]),
                    f(pl[cle][k]),
                    f(C["partiel"][cle][k]["micro"]["f1"]),
                    f(C["strict"][cle][k]["macro_9"]["f1"]),
                ]
                for k in cles
            ],
        )
        L += ["", "F1 micro sauf mention « macro (9) ».", ""]

    abs_ = sorted(
        {lab for res in (R, C) for k in ("syn", "lib") for lab in res["strict"]["par_source"][k]["etiquettes_absentes"]}
    )
    if abs_:
        note = "Note : étiquettes absentes du gold et des prédictions dans au moins une tranche "
        note += f"(F1 = 0 dans la macro (9)) : {', '.join(abs_)}."
        L += [note, ""]

    L += [
        "## Validation croisée sur le texte libre (`lib_`, règles)",
        "",
        f"Protocole de développement des règles sur du vrai texte (`caseforge.eval.lib_cv`) : {cv['n_plis']} plis, "
        f"un document `lib_` de train ou de dev laissé de côté par pli ({cv['n_passages']} passages ; liste des plis "
        "dans `data/lotb/lib_cv_folds.json`). Moyenne ± écart-type sur les plis ; « regroupé » = F1 micro sur toutes "
        "les prédictions réunies. Le dev global reste la mesure de référence.",
        "",
    ]
    L += _table(
        ["Mode", "F1 micro (plis)", "F1 macro (9) (plis)", "Regroupé", "fr", "ar", "en"],
        [
            [
                mode,
                _moy_ecart(cv[mode]["f1_micro"]),
                _moy_ecart(cv[mode]["f1_macro_9"]),
                f(cv[mode]["regroupe_f1_micro"]),
                *[
                    f"{_moy_ecart(cv[mode]['par_langue'][k])} (n = {cv[mode]['par_langue'][k]['n_plis']})"
                    for k in ("fr", "ar", "en")
                ],
            ]
            for mode in ("strict", "partiel")
        ],
    )
    L += [""]
    L += _table(
        ["Étiquette", "F1 stricte (plis)", "Plis concernés"],
        [
            [lab, _moy_ecart(cv["strict"]["par_etiquette"][lab]), str(cv["strict"]["par_etiquette"][lab]["n_plis"])]
            for lab in LABELS
        ],
    )
    L += ["", "Par étiquette : moyenne sur les plis où l'étiquette apparaît (en gold ou en prédiction).", ""]

    mr, mc = R["strict"]["mixtes"], C["strict"]["mixtes"]
    L += ["## Annexe — passages mixtes (`lang == mixte`)", ""]
    L += _table(
        ["Passages", "Gold", "Règles manqués", "Règles inventés", "CRF manqués", "CRF inventés"],
        [[str(mr["n_passages"]), str(mr["support_gold"]), str(mr["fn"]), str(mr["fp"]), str(mc["fn"]), str(mc["fp"])]],
    )
    L += ["", f"Mode strict. n = {mr['n_passages']} < 30 : aucune conclusion sur la F1.", ""]

    L += ["## 5. Matrices de confusion (gold en ligne, prédiction en colonne)", ""]
    cols = [*LABELS, MANQUE]
    for nom, res in (("Règles", R), ("CRF", C)):
        L += [f"**{nom}**", ""]
        L += _table(
            ["gold \\ prédit", *cols], [[g, *[str(res["confusion"][g][c]) for c in cols]] for g in (*LABELS, INVENTE)]
        )
        L += [""]

    L += ["## 6. Bootstrap apparié CRF contre règles", ""]
    b0 = next(iter(boot.values()))
    L += _table(
        ["Mesure", "Règles", "CRF", "Δ (CRF − règles)", "IC 95 %", "p (unilatérale)"],
        [
            [
                k.replace("_", " · "),
                f(b["f1_a"]),
                f(b["f1_b"]),
                f(b["delta"]),
                f"[{f(b['ic95'][0])} ; {f(b['ic95'][1])}]",
                f"{b['p_value']:.3f}".replace(".", ","),
            ]
            for k, b in boot.items()
        ],
    )
    L += [
        "",
        f"Tirage avec remise de {b0['n_documents']} documents (`doc_id`), {b0['n_resamples']} rééchantillonnages, "
        f"graine {b0['seed']}. p = (1 + #{{Δ* ≤ 0}}) / {b0['n_resamples'] + 1} : probabilité que le CRF ne soit pas "
        "meilleur que les règles.",
        "",
    ]

    # ---------- Biais de construction ----------
    ids_syn, ids_lib = _ids_source(gold, "syn_"), _ids_source(gold, "lib_")
    formes_org = [x for lang in P.ORG_FORMS.values() for x in dict.fromkeys(lang)]
    formes_org_regex = [x for x in formes_org if x in R_ORG]
    titres = [t for d in P.TITLE.values() for t in d.values()]
    titres_regex = [t for t in titres if re.fullmatch(R_PER, f"{t} Karim")]
    gaz = gazetteer()
    gaz_set = {s.lower() for s, _ in gaz}
    familles_dev = sorted({g.get("famille") for g in gold if g["doc_id"].startswith("syn_")})

    def couverture(ids: set[str]) -> tuple[int, int]:
        ents = [e for g in gold if g["passage_id"] in ids for e in g["entities"] if e["label"] in LABELS_GAZETTEER]
        return sum(e["text"].lower() in gaz_set for e in ents), len(ents)

    cov_syn, cov_lib = couverture(ids_syn), couverture(ids_lib)
    train = read_jsonl(TRAIN_JSONL)
    ents_train = [
        e for t in train if t["doc_id"].startswith("syn_") for e in t["entities"] if e["label"] in LABELS_GAZETTEER
    ]
    cov_train = (sum(e["text"].lower() in gaz_set for e in ents_train), len(ents_train))
    n_train_syn = sum(t["doc_id"].startswith("syn_") for t in train)

    def tp_gazetteer(ids: set[str]) -> int:
        res = evaluate(_sous_ensemble(gold, ids), _sous_ensemble(regles, ids))
        return sum(res["partiel"]["par_etiquette"][lab]["tp"] for lab in LABELS_GAZETTEER)

    ecarts = []
    for nom, res in (("Règles", R), ("CRF", C)):
        for mode in ("strict", "partiel"):
            s, li = res[mode]["par_source"]["syn"]["micro"]["f1"], res[mode]["par_source"]["lib"]["micro"]["f1"]
            ecarts.append([nom, mode, f(s), f(li), f(s - li)])

    L += ["## 7. Biais de construction", ""]
    L += _table(["Système", "Mode", "syn_", "lib_", "Écart syn_ − lib_"], ecarts)
    L += [""]
    R_syn = evaluate(_sous_ensemble(gold, ids_syn), _sous_ensemble(regles, ids_syn))
    R_lib = evaluate(_sous_ensemble(gold, ids_lib), _sous_ensemble(regles, ids_lib))
    L += _table(
        ["Étiquette (règles, strict)", "Gold syn_", "F1 syn_", "Gold lib_", "F1 lib_", "Écart"],
        [
            [
                lab,
                str(R_syn["strict"]["par_etiquette"][lab]["support_gold"]),
                f(R_syn["strict"]["par_etiquette"][lab]["f1"]),
                str(R_lib["strict"]["par_etiquette"][lab]["support_gold"]),
                f(R_lib["strict"]["par_etiquette"][lab]["f1"]),
                f(R_syn["strict"]["par_etiquette"][lab]["f1"] - R_lib["strict"]["par_etiquette"][lab]["f1"]),
            ]
            for lab in LABELS
        ],
    )
    L += [
        "",
        "D'où vient l'écart :",
        "",
        f"- **Regex calquées sur le générateur.** Les passages `syn_` sont produits par `cfdata/generate.py` à partir "
        f"des listes de `cfdata/pools.py`. `R_ORG` contient {len(formes_org_regex)} des {len(formes_org)} formes "
        f"juridiques de `pools.ORG_FORMS` (fr, ar, en) et `R_PER` {len(titres_regex)} des {len(titres)} civilités "
        "de `pools.TITLE` ; les motifs DONNEE_SENSIBLE (« contrat n° », TND, téléphone +216) et CONTRAINTE "
        "(« doit », « must », « يجب ») reprennent les tournures des gabarits. Sur `syn_`, les règles reconnaissent "
        "donc la forme exacte qui a servi à écrire le texte ; sur `lib_` (rédaction libre), ces formes sont plus "
        "rares ou varient.",
        f"- **Gazetteer issu du lexique du générateur.** `prelabel.gazetteer()` ({len(gaz)} entrées) est construit à "
        "partir de `pools.SECTOR_LEX`, le lexique métier du générateur (PRODUIT, EQUIPEMENT, PROCESSUS), en ne "
        "gardant que la moitié « famille A » (indices pairs, celle du train). Les documents `syn_` du dev sont de la "
        f"famille {', '.join(map(str, familles_dev))} (vocabulaire impair). Sur le dev, le gazetteer retrouve à "
        f"l'identique {cov_syn[0]} des {cov_syn[1]} entités gold PRODUIT / EQUIPEMENT / PROCESSUS de `syn_` et "
        f"{cov_lib[0]} des {cov_lib[1]} de `lib_`, et produit en mode partiel {tp_gazetteer(ids_syn)} vrais positifs "
        f"sur `syn_` et {tp_gazetteer(ids_lib)} sur `lib_`. Sur le train (même moitié du lexique), il retrouve "
        f"{cov_train[0]} des {cov_train[1]} entités de `syn_`. Le gazetteer est donc une fuite du générateur vers "
        "le train, que le partage anti-fuite neutralise sur le dev : **l'écart syn_ − lib_ observé sur le dev ne vient "
        "pas du gazetteer mais des regex** (tableau par étiquette ci-dessus).",
        "- **Conséquence.** Le score des règles sur `syn_` mesure surtout l'accord avec les gabarits du générateur, "
        "pas la capacité à généraliser. Le chiffre à suivre pour le Lot B est celui de `lib_` (et du corpus externe), "
        f"en gardant à l'esprit sa petite taille ({R['strict']['par_source']['lib']['n_passages']} passages, "
        f"{R['strict']['par_source']['lib']['support_gold']} entités sur le dev : intervalle large). Toute règle "
        "nouvelle doit être écrite sans lire `cfdata/pools.py` ni `cfdata/templates.py`. Le CRF est entraîné sur un "
        f"train à {n_train_syn} passages `syn_` sur {len(train)} : il apprend les mêmes gabarits, d'où un écart "
        "syn_ − lib_ du même ordre.",
        "",
    ]

    fps, fns = erreurs_franches(gold, regles)
    L += [
        "## 8. Erreurs des règles sur le dev (10 faux positifs, 10 faux négatifs)",
        "",
        f"Erreurs franches : aucun chevauchement avec une entité de même étiquette (mode partiel). Total : {len(fps)} "
        f"faux positifs et {len(fns)} faux négatifs. Échantillon déterministe, une étiquette après l'autre. "
        "Le span est entre crochets.",
        "",
        "**Faux positifs (inventés)**",
        "",
    ]
    L += _table(
        ["Passage", "Étiquette prédite", "Extrait"],
        [[x["pid"], x["span"][2], _extrait(x["text"], *x["span"][:2])] for x in _echantillon(fps)],
    )
    L += ["", "**Faux négatifs (manqués)**", ""]
    L += _table(
        ["Passage", "Étiquette gold", "Extrait"],
        [[x["pid"], x["span"][2], _extrait(x["text"], *x["span"][:2])] for x in _echantillon(fns)],
    )
    L += [""]

    (REPORTS / "lotb_baseline_regles.md").write_text("\n".join(L), encoding="utf-8")
    print(f"Rapport écrit : {REPORTS / 'lotb_baseline_regles.md'}")
    _imprimer_chiffres(R, C, boot, cov_syn, cov_lib, len(fps), len(fns))
    print(f"couverture gazetteer train syn {cov_train}")


def _imprimer_chiffres(
    R: dict[str, Any], C: dict[str, Any], boot: dict, cov_syn: tuple, cov_lib: tuple, nfp: int, nfn: int
) -> None:
    """Affiche les chiffres clés (sans texte de passage) pour le journal des expériences."""
    for nom, res in (("règles", R), ("CRF", C)):
        s = res["strict"]
        print(
            f"{nom}: strict {s['global']['micro']['f1']:.3f} macro9 {s['global']['macro_9']['f1']:.3f} "
            f"partiel {res['partiel']['global']['micro']['f1']:.3f} | "
            + " ".join(f"{k} {s['par_langue'][k]['micro']['f1']:.3f}" for k in ("fr", "ar", "en"))
            + " | "
            + " ".join(f"{k} {s['par_source'][k]['micro']['f1']:.3f}" for k in ("syn", "lib"))
            + " | partiel "
            + " ".join(f"{k} {res['partiel']['par_source'][k]['micro']['f1']:.3f}" for k in ("syn", "lib"))
        )
    for k, b in boot.items():
        print(f"bootstrap {k}: delta {b['delta']:.3f} IC [{b['ic95'][0]:.3f}; {b['ic95'][1]:.3f}] p {b['p_value']:.3f}")
    print(f"couverture gazetteer syn {cov_syn} lib {cov_lib} ; FP {nfp} FN {nfn}")
    print(
        "règles par étiquette strict: "
        + " ".join(f"{lab} {R['strict']['par_etiquette'][lab]['f1']:.2f}" for lab in LABELS)
    )
    print(
        "CRF par étiquette strict: "
        + " ".join(f"{lab} {C['strict']['par_etiquette'][lab]['f1']:.2f}" for lab in LABELS)
    )


if __name__ == "__main__":
    main()
