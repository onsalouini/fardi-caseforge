"""B12 — lexiques de familles (PRODUIT) et de catégories (EQUIPEMENT) pour la généralisation des indices rares.

    python -m scripts.b12_lexiques

Source : entités gold PRODUIT et EQUIPEMENT de ``data/final/train.jsonl`` uniquement (le dev n'est pas lu).
Sorties : ``data/lexicons/familles_produits.txt`` et ``data/lexicons/categories_equipements.txt``, au format
``forme<TAB>famille<TAB>langue`` lu par ``caseforge.anonymization.generalisation``. Relancer le script redonne
les mêmes fichiers (ordre trié, aucun tirage).

Méthode, pour chaque forme gold du train :

1. retrait des références, codes et marques (``sans_references`` : « presse hydraulique 200 t » -> « presse
   hydraulique », « centre d'usinage DMG n°4 » -> « centre d'usinage ») ;
2. clé normalisée (``cle_generalisation`` : casse, accents, tatweel, articles « la », « the », « ال ») ;
3. tête nominale : la plus longue tête de ``TETES_EQUIPEMENT`` / ``TETES_PRODUIT`` qui débute la clé (fr, ar : tête
   à gauche) ou la termine (en : tête à droite) ; à défaut, la même recherche à une faute d'OCR près
   (``coref_simple.proches`` : mots d'au moins 5 lettres à une édition près, « pastcurizer ») ;
4. regroupement : la tête donne la famille, écrite dans la langue de la tête (``FAMILLES_*``). Une forme sans
   tête connue arrête le script (la table doit couvrir tout le train).

Les tables de têtes ont été écrites à partir des formes du train et, pour les équipements, des termes de
``data/lexicons/equipement_tetes.txt`` (le script signale les termes de ce lexique restés sans catégorie). Le
lexique écrit contient les formes du train (sans référence), les têtes et les noms de familles eux-mêmes, dans les
trois langues.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from caseforge.anonymization.coref_simple import proches
from caseforge.anonymization.generalisation import (
    LEXIQUES_GENERALISATION,
    chercher_tete,
    cle_generalisation,
    famille,
    lexique_familles,
    mots_cle,
    sans_references,
)
from caseforge.eval.data import FINAL
from caseforge.extraction.rules.lexicons import LEXIQUES, charger, est_arabe
from caseforge.labels import GENERALISABLE_LABELS
from cfdata.common import read_jsonl

TRAIN = FINAL / "train.jsonl"
Table = dict[str, dict[str, list[str]]]

# ---------- EQUIPEMENT : catégories ----------
FAMILLES_EQUIPEMENT: dict[str, dict[str, str]] = {
    "presse": {"fr": "presse", "en": "press", "ar": "مكبس"},
    "machine_production": {"fr": "machine de production", "en": "production machine", "ar": "آلة إنتاج"},
    "ligne": {"fr": "ligne de production", "en": "production line", "ar": "خط إنتاج"},
    "machine_outil": {"fr": "machine-outil", "en": "machine tool", "ar": "آلة تشغيل"},
    "thermique": {"fr": "équipement thermique", "en": "thermal equipment", "ar": "معدات حرارية"},
    "controle": {"fr": "équipement de contrôle", "en": "inspection equipment", "ar": "معدات المراقبة"},
    "outillage": {"fr": "outillage", "en": "tooling", "ar": "أدوات الإنتاج"},
    "electrique": {"fr": "équipement électrique", "en": "electrical equipment", "ar": "معدات كهربائية"},
    "fluides": {"fr": "pompe ou compresseur", "en": "pump or compressor", "ar": "مضخة أو ضاغط"},
    "manutention": {"fr": "équipement de manutention", "en": "handling equipment", "ar": "معدات المناولة"},
    "logiciel": {"fr": "logiciel", "en": "software", "ar": "برمجية"},
    "pieces": {"fr": "pièces de rechange", "en": "spare parts", "ar": "قطع الغيار"},
    "stockage": {"fr": "installation de stockage", "en": "storage facility", "ar": "منشأة تخزين"},
}
_SIGLES_LOGICIELS = ["ERP", "MES", "WMS", "GMAO", "SCADA", "PLM", "TMS", "CMMS"]
TETES_EQUIPEMENT: Table = {
    "presse": {
        "fr": ["presse", "presse à injecter", "comprimeuse", "injecteuse"],
        "en": ["press", "injection press", "tablet press"],
        "ar": ["مكبس", "آلة الحقن"],
    },
    "machine_production": {
        "fr": [
            "machine",
            "souffleuse",
            "mélangeur",
            "rameuse",
            "poste",
            "extrudeuse",
            "broyeur",
            "remplisseuse",
            "étiqueteuse",
            "encartonneuse",
            "dragéifieuse",
            "turbine",
            "cellule",
            "métier à tisser",
        ],
        "en": [
            "machine",
            "blow moulder",
            "moulder",
            "blender",
            "v-blender",
            "mixer",
            "stenter",
            "stenter frame",
            "coating pan",
            "roller mill",
            "mill",
            "extruder",
            "filler",
            "labeller",
            "labeler",
            "turbine",
            "workstation",
            "station",
            "cell",
        ],
        "ar": ["آلة", "ماكينة", "جهاز", "خلاط", "آلة الغلق", "مطحنة"],
    },  # fmt: skip
    "ligne": {
        "fr": ["ligne", "chaîne", "ligne de montage"],
        "en": ["line", "bottling line", "assembly line"],
        "ar": ["خط"],
    },
    "machine_outil": {
        "fr": ["centre d'usinage", "tour", "fraiseuse", "rectifieuse", "machine-outil"],
        "en": ["machining centre", "machining center", "lathe", "milling machine", "machine tool"],
        "ar": ["مركز التشغيل"],
    },
    "thermique": {
        "fr": ["four", "étuve", "autoclave", "sécheur", "séchoir", "pasteurisateur", "stérilisateur", "chaudière"],
        "en": ["oven", "furnace", "kiln", "dryer", "pasteurizer", "pasteuriser", "sterilizer", "boiler", "autoclave"],
        "ar": ["فرن", "آلة التجفيف", "مجفف", "جهاز التعقيم"],
    },
    "controle": {
        "fr": ["banc", "banc de test", "banc d'essai", "caméra", "détecteur", "capteur", "scanner"],
        "en": ["test bench", "bench", "camera", "detector", "metal detector", "sensor", "scanner"],
        "ar": ["منصة الاختبار"],
    },
    "outillage": {
        "fr": [
            "planche de montage",
            "montage d'usinage",
            "montage",
            "gabarit",
            "pochoir",
            "outil",
            "outillage",
            "moule",
        ],
        "en": ["assembly board", "stencil", "jig", "fixture", "tool", "tooling", "mould", "mold"],
        "ar": ["قالب"],
    },
    "electrique": {
        "fr": [
            "carte de puissance",
            "dissipateur",
            "transformateur",
            "onduleur",
            "générateur",
            "groupe électrogène",
            "automate",
            "panneau solaire",
            "électrode",
        ],
        "en": ["transformer", "inverter", "generator", "PLC", "solar panel", "heat sink", "electrode", "coil"],
        "ar": ["الأقطاب الكهربائية", "الألواح الشمسية", "اللفات", "المحولات", "محول", "مولد", "محطة شمسية", "محطة"],
    },  # fmt: skip
    "fluides": {
        "fr": ["compresseur", "pompe", "cuve", "réservoir"],
        "en": ["compressor", "pump", "tank"],
        "ar": ["مضخة", "ضاغط", "خزان"],
    },
    "manutention": {
        "fr": ["convoyeur", "robot", "chariot élévateur"],
        "en": ["conveyor", "robot", "forklift"],
        "ar": ["روبوت", "ناقل"],
    },
    "logiciel": {
        "fr": ["logiciel", "progiciel", "tableau de bord", *_SIGLES_LOGICIELS],
        "en": ["software", "dashboard", *_SIGLES_LOGICIELS],
        "ar": ["برمجية", "حاسوب"],
    },
    "pieces": {"fr": ["pièces de rechange"], "en": ["spare parts"], "ar": ["قطع الغيار"]},
    "stockage": {
        "fr": ["entrepôt", "entrepôt sous douane", "silo"],
        "en": ["warehouse", "silo"],
        "ar": ["مستودع"],
    },
}

# ---------- PRODUIT : familles ----------
FAMILLES_PRODUIT: dict[str, dict[str, str]] = {
    "habillement": {"fr": "articles d'habillement", "en": "apparel", "ar": "ملابس"},
    "alimentaire": {"fr": "produits alimentaires", "en": "food products", "ar": "منتجات غذائية"},
    "pharma": {"fr": "médicaments", "en": "pharmaceutical products", "ar": "أدوية"},
    "emballage": {"fr": "emballages", "en": "packaging", "ar": "مواد تغليف"},
    "electrique": {"fr": "composants électriques", "en": "electrical components", "ar": "مكونات كهربائية"},
    "metal": {"fr": "pièces métalliques", "en": "metal parts", "ar": "قطع معدنية"},
    "energie": {"fr": "énergie", "en": "energy", "ar": "طاقة"},
}
TETES_PRODUIT: Table = {
    "habillement": {
        "fr": ["jeans", "pantalon", "veste", "vêtement", "chemise", "chaussure", "botte", "tenue"],
        "en": ["jeans", "garment", "workwear", "boots", "shoes", "clothing", "trousers", "jacket", "shirt"],
        "ar": ["سراويل", "سروال", "ملابس", "أحذية", "قمصان"],
    },
    "alimentaire": {
        "fr": ["huile", "huile d'olive", "dattes", "semoule", "concentré de tomate", "conserves"],
        "en": ["oil", "olive oil", "dates", "semolina", "tomato paste"],
        "ar": ["زيت", "زيت الزيتون", "التمور", "معجون", "معجون الطماطم", "سميد"],
    },
    "pharma": {
        "fr": ["comprimés", "gélules", "médicaments", "sirop"],
        "en": ["tablets", "capsules", "drugs", "syrup"],
        "ar": ["الأقراص", "الكبسولات", "أدوية"],
    },
    "emballage": {
        "fr": ["films d'emballage", "film", "emballage", "bouteilles", "flacons", "cartons", "boîtes", "sacs"],
        "en": ["packaging films", "packaging", "films", "bottles", "cartons", "cans", "bags"],
        "ar": ["أغشية", "أغلفة", "قوارير", "صناديق", "علب", "أكياس"],
    },
    "electrique": {
        "fr": [
            "faisceaux",
            "faisceaux de câbles",
            "câbles",
            "onduleur",
            "kits photovoltaïques",
            "condensateurs",
            "carte électronique",
            "composants électroniques",
        ],
        "en": ["harnesses", "cable harnesses", "cables", "capacitors", "main board", "inverter", "solar kits"],
        "ar": ["حزم الأسلاك", "حزم", "كابلات", "مكثفات"],
    },  # fmt: skip
    "metal": {
        "fr": ["brides", "pièces usinées", "pièces", "support moteur", "support", "acier", "ferraille", "tôles"],
        "en": ["flanges", "parts", "machined parts", "steel", "scrap", "brackets"],
        "ar": ["الشفاه", "القطع", "حديد", "حديد التسليح", "أسلاك الحديد", "الخردة"],
    },
    "energie": {
        "fr": ["électricité", "énergie"],
        "en": ["electricity", "energy", "power"],
        "ar": ["الكهرباء", "طاقة"],
    },
}

TABLES: dict[str, tuple[dict[str, dict[str, str]], Table]] = {
    "EQUIPEMENT": (FAMILLES_EQUIPEMENT, TETES_EQUIPEMENT),
    "PRODUIT": (FAMILLES_PRODUIT, TETES_PRODUIT),
}
ENTETES = {
    "EQUIPEMENT": "Catégories d'équipements",
    "PRODUIT": "Familles de produits",
}


def index_tetes(tetes: Table) -> dict[str, list[tuple[str, str]]]:
    """Clé de tête -> ``[(famille, langue)]`` ; une même clé ne peut pas désigner deux familles dans une langue."""
    out: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for fid, par_langue in tetes.items():
        for langue, formes in par_langue.items():
            for f in formes:
                k = cle_generalisation(f)
                autre = [x for x, lg in out[k] if lg == langue and x != fid]
                if autre:
                    raise SystemExit(f"tête {f!r} ({langue}) dans deux familles : {fid}, {autre[0]}")
                if (fid, langue) not in out[k]:
                    out[k].append((fid, langue))
    return dict(out)


def tete_ocr(mots: tuple[str, ...], index: dict[str, list[tuple[str, str]]]) -> str | None:
    """Tête qui débute ou termine la clé à une faute d'OCR près (``proches``), la plus longue d'abord."""
    for n in range(len(mots), 0, -1):
        for k in sorted(index):
            t = tuple(k.split())
            if len(t) == n and (proches(t, mots[:n]) or proches(t, mots[-n:])):
                return k
    return None


def langue_forme(forme: str, lang_passage: str, cands: list[tuple[str, str]]) -> tuple[str, str]:
    """Famille et langue d'une forme : la langue du passage si la tête y figure, sinon la première langue."""
    langue = "ar" if est_arabe(forme) else lang_passage
    for fid, lg in cands:
        if lg == langue:
            return fid, lg
    return cands[0]


def formes_train(label: str) -> Counter[tuple[str, str]]:
    """Formes gold ``(surface, langue du passage)`` de l'étiquette dans le train, avec leur effectif."""
    out: Counter[tuple[str, str]] = Counter()
    for r in read_jsonl(TRAIN):
        for e in r["entities"]:
            if e["label"] == label:
                out[(r["text"][e["start"] : e["end"]], r["lang"])] += 1
    return out


def affichage(forme: str) -> str:
    """Forme écrite dans le lexique : sans référence, sans tatweel, espaces simples."""
    return " ".join(sans_references(forme).replace("ـ", "").split())


def construire(label: str) -> tuple[list[tuple[str, str, str]], dict[str, object]]:
    """Lignes ``(forme, famille, langue)`` du lexique d'une étiquette et statistiques de construction."""
    familles, tetes = TABLES[label]
    index = index_tetes(tetes)
    lignes: dict[tuple[str, str], tuple[str, str, str]] = {}  # (clé, langue) -> ligne
    attendu: list[tuple[str, str, str]] = []  # (forme, langue, famille) pour la vérification
    stats: Counter[str] = Counter()
    par_famille: Counter[str] = Counter()  # occurrences du train par famille
    sans_tete: list[str] = []

    def ajouter(forme: str, fid: str, langue: str) -> None:
        k = cle_generalisation(forme)
        fam = familles[fid][langue]
        if (k, langue) in lignes and lignes[(k, langue)][1] != fam:
            raise SystemExit(f"{label} : clé {k!r} ({langue}) dans deux familles : {lignes[(k, langue)][1]}, {fam}")
        lignes.setdefault((k, langue), (forme, fam, langue))

    train = formes_train(label)
    for (forme, lang), n in sorted(train.items()):
        mots = mots_cle(forme)
        k = chercher_tete(mots, index)
        if k is not None:
            stats["tete_exacte"] += n
        else:
            k = tete_ocr(mots, index)
            stats["tete_ocr"] += n if k else 0
        if k is None:
            sans_tete.append(forme)
            continue
        fid, lg = langue_forme(forme, lang, index[k])
        ajouter(affichage(forme), fid, lg)
        attendu.append((forme, lg, familles[fid][lg]))
        par_famille[fid] += n
    if sans_tete:
        raise SystemExit(f"{label} : formes du train sans tête connue : {sans_tete}")
    for fid, par_langue in tetes.items():
        for langue, formes in par_langue.items():
            for f in formes:
                ajouter(f, fid, langue)
    for fid, noms in familles.items():
        for langue, nom in noms.items():
            ajouter(nom, fid, langue)
    stats["occurrences_train"] = sum(train.values())
    stats["formes_train"] = len(train)
    return sorted(lignes.values(), key=lambda x: (x[2], x[1], x[0].casefold())), {
        **stats,
        "lignes": len(lignes),
        "attendu": attendu,
        "occurrences_par_famille": dict(par_famille.most_common()),
    }


def ecrire(label: str, lignes: list[tuple[str, str, str]], path: Path) -> None:
    """Écrit le lexique avec un en-tête qui rappelle son origine."""
    entete = [
        f"# {ENTETES[label]} (B12, généralisation des {label}) : forme<TAB>famille<TAB>langue.",
        "# Source : entités gold PRODUIT / EQUIPEMENT du TRAIN (data/final/train.jsonl), têtes d'equipement_tetes.",
        "# Fichier GÉNÉRÉ par scripts/b12_lexiques.py ;",
        "# ne pas l'éditer à la main : modifier les tables du script puis le relancer. Formes sans référence, code ni",
        "# marque, têtes nominales et noms de familles ; famille écrite dans la langue de la forme. Lecture :",
        "# caseforge.anonymization.generalisation (forme entière, puis tête, sinon famille générique « [ÉTIQUETTE] »).",
    ]
    path.write_text("\n".join([*entete, *("\t".join(x) for x in lignes)]) + "\n", encoding="utf-8")


def termes_equipement_sans_categorie() -> list[str]:
    """Termes de ``equipement_tetes.txt`` (hors libellés de champ) qu'aucune tête de la table ne couvre."""
    index = index_tetes(TETES_EQUIPEMENT)
    return [
        t for t, a in charger("equipement_tetes") if a != "champ" and chercher_tete(mots_cle(t, False), index) is None
    ]


def main() -> None:
    for label in sorted(GENERALISABLE_LABELS):
        lignes, stats = construire(label)
        path = LEXIQUES / f"{LEXIQUES_GENERALISATION[label]}.txt"
        ecrire(label, lignes, path)
        lexique_familles.cache_clear()
        erreurs = [(f, lg, fam, famille(label, f, lg)) for f, lg, fam in stats.pop("attendu")]  # type: ignore[union-attr]
        erreurs = [e for e in erreurs if e[2] != e[3]]
        if erreurs:
            raise SystemExit(f"{label} : relecture du lexique incohérente : {erreurs}")
        print(f"{label} -> {path.relative_to(LEXIQUES.parents[1])}")
        for k, v in stats.items():
            print(f"  {k} : {v}")
    print(f"termes de equipement_tetes sans catégorie : {termes_equipement_sans_categorie()}")


if __name__ == "__main__":
    main()
