"""Garde-fou : aucun code ne doit mentionner ni construire un fichier de test gelé (CLAUDE.md, section 2).

Deux contrôles sur les fichiers de `caseforge/`, `scripts/` et `tests/` :

1. **texte** : un nom de fichier interdit écrit en clair (y compris dans un commentaire) ;
2. **construction** (constat M1 de l'audit Silver) : analyse `ast` des fichiers Python. Les
   f-strings, concaténations `+`, `.format()`, `os.path.join`, `Path(...)`, `Path / "..."` et
   `.joinpath()` sont évalués avec les valeurs constantes que peuvent prendre leurs morceaux
   (affectations, boucles `for` sur des littéraux, valeurs par défaut, arguments passés aux
   fonctions du module, `default` / `choices` d'argparse, expressions conditionnelles). Si une
   des valeurs possibles se termine par un nom de fichier interdit, l'accès est signalé.

Exceptions, et seulement celles de CLAUDE.md : `scripts/final_eval.py` pour le test gelé ;
`tests/test_non_regression_kappa.py` pour les fichiers du kappa. Ce fichier-ci est exclu du
balayage parce qu'il contient les motifs et des exemples inventés, en mémoire.
"""

from __future__ import annotations

import ast
import itertools
import re
import string
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

import pytest

from caseforge.labels import REPO_ROOT

DOSSIERS = ("caseforge", "scripts", "tests")
CE_FICHIER = Path(__file__).resolve()
EXC_TEST_GELE = frozenset({REPO_ROOT / "scripts" / "final_eval.py"})
EXC_KAPPA = frozenset({REPO_ROOT / "tests" / "test_non_regression_kappa.py"})

# Code du Lot C, que le Lot B ne modifie pas (CLAUDE.md, section 8).
LOT_C = (
    REPO_ROOT / "caseforge" / "models",
    REPO_ROOT / "caseforge" / "retrieval",
    REPO_ROOT / "caseforge" / "eval" / "ner_eval.py",
)

# (nom de la règle, motifs interdits dans le texte, fichiers autorisés)
REGLES: tuple[tuple[str, tuple[str, ...], frozenset[Path]], ...] = (
    (
        "test gelé",
        (
            r"test\.jsonl",
            r"test\.bio\.jsonl",
            r"test\.conll",
            r"documents_test\.jsonl",
            r"fiches_test\.jsonl",
            r"hf/test\.jsonl",
            r"externe_test",
        ),
        EXC_TEST_GELE,
    ),
    (
        "kappa (passages du test gelé)",
        (r"humain_kappa", r"kappa_\w*\.jsonl?", r"double_annotation_tasks"),
        EXC_KAPPA,
    ),
)

# Même partition pour les chemins construits : motif appliqué au dernier élément du chemin.
# Couvre test, externe_test, documents_test, fiches_test (.jsonl, .bio.jsonl, .conll) et hf/test.
REGLES_CONSTRUITES: tuple[tuple[str, re.Pattern[str], frozenset[Path]], ...] = (
    (
        "test gelé",
        re.compile(r"^(?:(?:documents|fiches|externe)_)?test(?:\.bio)?\.(?:jsonl|conll)$"),
        EXC_TEST_GELE,
    ),
    (
        "kappa (passages du test gelé)",
        re.compile(r"^(?:humain_kappa.*|kappa_\w*\.jsonl?|double_annotation_tasks.*)$"),
        EXC_KAPPA,
    ),
)

OPAQUE = "\x00"  # morceau de valeur inconnue : ne peut former aucun nom interdit
MAX_VALEURS = 4096
CONSTRUCTEURS_PATH = {"Path", "PurePath", "PosixPath", "WindowsPath", "PurePosixPath", "PureWindowsPath"}
MODULES_JOIN = {"path", "posixpath", "ntpath"}
METHODES_NEUTRES = {"resolve", "absolute", "as_posix", "expanduser", "strip", "lower"}

Valeurs = set[str] | None  # None : valeur inconnue
Appels = dict[tuple[str, int | str], set[str]]  # (fonction, position ou nom du paramètre) -> valeurs


def _produit(parts: list[set[str]], sep: str = "") -> set[str]:
    """Toutes les concaténations possibles des morceaux, plafonnées à MAX_VALEURS."""
    out: set[str] = set()
    for combo in itertools.product(*parts):
        out.add(sep.join(combo))
        if len(out) >= MAX_VALEURS:
            break
    return out


class _Analyse:
    """Valeurs constantes possibles des expressions d'un module (approximation prudente).

    La portée est ignorée : un nom (ou un attribut `x.nom`) prend toutes les valeurs qui lui
    sont liées quelque part dans le module. C'est volontairement large : un garde-fou doit
    préférer la fausse alerte à l'accès manqué.
    """

    def __init__(self, arbre: ast.Module, externes: Appels | None = None) -> None:
        self.liaisons: dict[str, list[tuple[str, ast.expr]]] = defaultdict(list)
        self.params: dict[str, list[str]] = {}
        for n in ast.walk(arbre):
            if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef):
                self._fonction(n)
        for n in ast.walk(arbre):
            self._lier_noeud(n)
        # Arguments constants passés à nos fonctions par d'autres modules qui les importent.
        for (fonction, position), valeurs in (externes or {}).items():
            params = self.params.get(fonction, [])
            cle = params[position] if isinstance(position, int) and position < len(params) else position
            if isinstance(cle, str):
                elts: list[ast.expr] = [ast.Constant(v) for v in sorted(valeurs)]
                self.liaisons[cle].append(("elt", ast.Tuple(elts=elts, ctx=ast.Load())))

    def appels(self, arbre: ast.Module, noms: Iterable[str]) -> Appels:
        """Valeurs constantes des arguments passés aux fonctions `noms` (importées) dans ce module."""
        noms = set(noms)
        out: Appels = defaultdict(set)
        for n in ast.walk(arbre):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in noms:
                cibles: list[tuple[int | str, ast.expr]] = list(enumerate(n.args))
                cibles += [(kw.arg, kw.value) for kw in n.keywords if kw.arg]
                for position, expr in cibles:
                    out[(n.func.id, position)] |= self.valeurs(expr) or set()
        return out

    # --- collecte des liaisons -------------------------------------------------------------

    def _fonction(self, f: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        a = f.args
        positionnels = [p.arg for p in a.posonlyargs + a.args]
        self.params[f.name] = positionnels
        for p, d in zip(positionnels[len(positionnels) - len(a.defaults) :], a.defaults, strict=True):
            self.liaisons[p].append(("val", d))
        for p, d in zip(a.kwonlyargs, a.kw_defaults, strict=True):
            if d is not None:
                self.liaisons[p.arg].append(("val", d))

    def _cle(self, cible: ast.expr) -> str | None:
        if isinstance(cible, ast.Name):
            return cible.id
        if isinstance(cible, ast.Attribute):
            return cible.attr
        return None

    def _lier(self, cible: ast.expr, valeur: ast.expr, genre: str = "val") -> None:
        if isinstance(cible, ast.Tuple | ast.List):
            if genre == "val" and isinstance(valeur, ast.Tuple | ast.List) and len(valeur.elts) == len(cible.elts):
                for c, v in zip(cible.elts, valeur.elts, strict=True):
                    self._lier(c, v)
            elif genre == "val" and isinstance(valeur, ast.IfExp):
                self._lier(cible, valeur.body)
                self._lier(cible, valeur.orelse)
            else:
                for c in cible.elts:
                    self._lier(c, valeur, "elt")
            return
        cle = self._cle(cible.value if isinstance(cible, ast.Starred) else cible)
        if cle is not None:
            self.liaisons[cle].append((genre, valeur))

    def _lier_noeud(self, n: ast.AST) -> None:
        if isinstance(n, ast.Assign):
            for c in n.targets:
                self._lier(c, n.value)
        elif isinstance(n, ast.AnnAssign | ast.NamedExpr) and n.value is not None:
            self._lier(n.target, n.value)
        elif isinstance(n, ast.For | ast.AsyncFor | ast.comprehension):
            self._lier(n.target, n.iter, "elt")
        elif isinstance(n, ast.Call):
            self._lier_appel(n)

    def _lier_appel(self, n: ast.Call) -> None:
        nom = n.func.id if isinstance(n.func, ast.Name) else n.func.attr if isinstance(n.func, ast.Attribute) else ""
        if nom in self.params:  # appel d'une fonction du module : arguments -> paramètres
            for p, v in zip(self.params[nom], n.args, strict=False):
                self.liaisons[p].append(("val", v))
        if nom in self.params or nom == "set_defaults":
            for kw in n.keywords:
                if kw.arg is not None:
                    self.liaisons[kw.arg].append(("val", kw.value))
        if nom == "add_argument":
            kws = {kw.arg: kw.value for kw in n.keywords if kw.arg}
            dest = kws.get("dest")
            cle = dest.value if isinstance(dest, ast.Constant) and isinstance(dest.value, str) else None
            if cle is None:
                options = [a.value for a in n.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                longues = [o for o in options if o.startswith("--")] or options
                cle = longues[0].lstrip("-").replace("-", "_") if longues else None
            if cle:
                if "default" in kws:
                    self.liaisons[cle].append(("val", kws["default"]))
                if "choices" in kws:
                    self.liaisons[cle].append(("elt", kws["choices"]))

    # --- évaluation -------------------------------------------------------------------------

    def _lie(self, cle: str, pile: frozenset[str]) -> Valeurs:
        if cle in pile or cle not in self.liaisons:
            return None
        pile = pile | {cle}
        out: set[str] = set()
        for genre, expr in self.liaisons[cle]:
            v = self.valeurs(expr, pile) if genre == "val" else self.elements(expr, pile)
            out |= v or set()
        return out or None

    def elements(self, expr: ast.expr, pile: frozenset[str] = frozenset()) -> Valeurs:
        """Valeurs possibles des éléments d'une collection (cible d'un `for`, `choices`)."""
        if isinstance(expr, ast.Tuple | ast.List | ast.Set):
            out: set[str] = set()
            for e in expr.elts:
                out |= self.valeurs(e, pile) or set()
            return out or None
        if isinstance(expr, ast.Name | ast.Attribute):
            cle = self._cle(expr)
            if cle is None or cle in pile or cle not in self.liaisons:
                return None
            out = set()
            for genre, e in self.liaisons[cle]:
                v = self.elements(e, pile | {cle}) if genre == "val" else None
                out |= v or set()
            return out or None
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.args:
            if expr.func.id in {"sorted", "list", "tuple", "set", "reversed"}:
                return self.elements(expr.args[0], pile)
        return None

    def _morceau(self, expr: ast.expr, pile: frozenset[str]) -> set[str]:
        return self.valeurs(expr, pile) or {OPAQUE}

    def valeurs(self, expr: ast.expr, pile: frozenset[str] = frozenset()) -> Valeurs:
        """Ensemble des chaînes que peut valoir `expr`, ou None si on n'en sait rien."""
        if isinstance(expr, ast.Constant):
            return {str(expr.value)} if isinstance(expr.value, str | int) and not isinstance(expr.value, bool) else None
        if isinstance(expr, ast.Name | ast.Attribute):
            cle = self._cle(expr)
            return self._lie(cle, pile) if cle else None
        if isinstance(expr, ast.JoinedStr):
            parts = [
                self._morceau(v.value, pile) if isinstance(v, ast.FormattedValue) else self._morceau(v, pile)
                for v in expr.values
            ]
            return _produit(parts)
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add | ast.Div):
            g, d = self.valeurs(expr.left, pile), self.valeurs(expr.right, pile)
            if g is None and d is None:
                return None
            sep = "/" if isinstance(expr.op, ast.Div) else ""
            return _produit([g or {OPAQUE}, d or {OPAQUE}], sep)
        if isinstance(expr, ast.IfExp | ast.BoolOp):
            branches = [expr.body, expr.orelse] if isinstance(expr, ast.IfExp) else expr.values
            out: set[str] = set()
            for b in branches:
                out |= self.valeurs(b, pile) or set()
            return out or None
        if isinstance(expr, ast.Call):
            return self._appel(expr, pile)
        return None

    def _appel(self, n: ast.Call, pile: frozenset[str]) -> Valeurs:
        f = n.func
        args = [a for a in n.args if not isinstance(a, ast.Starred)]
        if isinstance(f, ast.Name):
            if f.id in CONSTRUCTEURS_PATH or f.id == "join":
                return _produit([self._morceau(a, pile) for a in args], "/") if args else None
            if f.id in {"str", "fspath"} and args:
                return self.valeurs(args[0], pile)
            return None
        if not isinstance(f, ast.Attribute):
            return None
        if f.attr in CONSTRUCTEURS_PATH:  # pathlib.Path(...)
            return _produit([self._morceau(a, pile) for a in args], "/") if args else None
        if f.attr == "join":
            v = f.value
            module = v.attr if isinstance(v, ast.Attribute) else v.id if isinstance(v, ast.Name) else ""
            if module in MODULES_JOIN:  # os.path.join, posixpath.join…
                return _produit([self._morceau(a, pile) for a in args], "/") if args else None
            if isinstance(v, ast.Constant) and isinstance(v.value, str) and args:  # "sep".join([...])
                if isinstance(args[0], ast.Tuple | ast.List):
                    return _produit([self._morceau(e, pile) for e in args[0].elts], v.value)
            return None
        if f.attr == "joinpath":
            return _produit([self._morceau(a, pile) for a in [f.value, *args]], "/")
        if f.attr == "fspath" and args:
            return self.valeurs(args[0], pile)
        if f.attr in METHODES_NEUTRES:
            return self.valeurs(f.value, pile)
        if f.attr == "format":
            return self._format(f.value, n, pile)
        return None

    def _format(self, gabarit: ast.expr, n: ast.Call, pile: frozenset[str]) -> Valeurs:
        modeles = self.valeurs(gabarit, pile)
        if not modeles:
            return None
        kws = {kw.arg: kw.value for kw in n.keywords if kw.arg}
        out: set[str] = set()
        for modele in modeles:
            parts: list[set[str]] = []
            auto = 0
            try:
                champs = list(string.Formatter().parse(modele))
            except ValueError:
                continue
            for litteral, champ, _spec, _conv in champs:
                parts.append({litteral})
                if champ is None:
                    continue
                racine = re.split(r"[.\[]", champ, maxsplit=1)[0]
                if racine == "":
                    racine, auto = str(auto), auto + 1
                expr = n.args[int(racine)] if racine.isdigit() and int(racine) < len(n.args) else kws.get(racine)
                parts.append(self._morceau(expr, pile) if expr is not None else {OPAQUE})
            out |= _produit(parts)
        return out or None


def _est_construction(n: ast.AST) -> bool:
    if isinstance(n, ast.JoinedStr):
        return True
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add | ast.Div):
        return True
    if isinstance(n, ast.Call):
        f = n.func
        nom = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
        return nom in CONSTRUCTEURS_PATH | {"join", "joinpath", "format"}
    return False


def acces_construits(source: str, externes: Appels | None = None) -> list[tuple[int, str, str]]:
    """Accès construits à un fichier interdit dans `source` : (ligne, règle, valeur reconstituée).

    `externes` : arguments constants passés aux fonctions de ce module par d'autres modules.
    Toutes les règles sont appliquées ; les exceptions par fichier sont gérées par l'appelant.
    """
    arbre = ast.parse(source)
    analyse = _Analyse(arbre, externes)
    vus: dict[tuple[int, str], str] = {}
    for n in ast.walk(arbre):
        if not _est_construction(n):
            continue
        for valeur in sorted(analyse.valeurs(n) or ()):  # type: ignore[arg-type]
            dernier = valeur.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
            for nom, motif, _exc in REGLES_CONSTRUITES:
                if OPAQUE not in dernier and motif.match(dernier):
                    vus.setdefault((n.lineno, nom), valeur)
    return sorted((ligne, nom, v) for (ligne, nom), v in vus.items())


def _fichiers() -> list[Path]:
    """Liste les fichiers des dossiers surveillés, hors caches et hors ce fichier."""
    out = []
    for dossier in DOSSIERS:
        for p in sorted((REPO_ROOT / dossier).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.resolve() != CE_FICHIER:
                out.append(p.resolve())
    return out


def _du_lot_c(p: Path) -> bool:
    return any(p == c or c in p.parents for c in LOT_C)


def _module_importe(n: ast.ImportFrom, depuis: Path, racine: Path) -> Path | None:
    """Fichier du dépôt visé par `from … import …` (absolu ou relatif), s'il existe."""
    if n.level:
        base = depuis.parent
        for _ in range(n.level - 1):
            base = base.parent
        parties = [*base.relative_to(racine).parts, *(n.module or "").split(".")]
    else:
        parties = (n.module or "").split(".")
    cible = racine.joinpath(*[x for x in parties if x])
    for candidat in (cible.with_suffix(".py"), cible / "__init__.py"):
        if candidat.is_file():
            return candidat.resolve()
    return None


def appels_entre_modules(
    sources: dict[Path, str], racine: Path, appelants_exclus: frozenset[Path] = frozenset()
) -> dict[Path, Appels]:
    """Arguments constants passés aux fonctions importées d'un autre module du dépôt.

    Exemple : `from caseforge.x import charger` puis `charger("test")` lie le paramètre de
    `charger` à "test" dans l'analyse de `caseforge/x.py`. Un seul niveau d'appel est suivi.
    Les appels venant de `appelants_exclus` (fichiers en exception, comme `final_eval.py`, qui
    réutilise les chargeurs génériques sur le test) ne sont pas propagés.
    """
    out: dict[Path, Appels] = defaultdict(lambda: defaultdict(set))
    for chemin, source in sources.items():
        if chemin in appelants_exclus:
            continue
        arbre = ast.parse(source)
        imports: dict[str, tuple[Path, str]] = {}
        for n in ast.walk(arbre):
            if isinstance(n, ast.ImportFrom) and (cible := _module_importe(n, chemin, racine)):
                for alias in n.names:
                    imports[alias.asname or alias.name] = (cible, alias.name)
        if not imports:
            continue
        for (local, position), valeurs in _Analyse(arbre).appels(arbre, imports).items():
            cible, nom = imports[local]
            out[cible][(nom, position)] |= valeurs
    return out


def _fautes_construites(fichiers: Iterable[Path]) -> list[str]:
    exceptions = {nom: exc for nom, _m, exc in REGLES_CONSTRUITES}
    sources = {p: p.read_text(encoding="utf-8") for p in _fichiers() if p.suffix == ".py"}
    externes = appels_entre_modules(sources, REPO_ROOT, EXC_TEST_GELE | EXC_KAPPA)
    fautes = []
    for p in fichiers:
        if p.suffix != ".py":
            continue
        for ligne, nom, valeur in acces_construits(sources[p], externes.get(p)):
            if p not in exceptions[nom]:
                fautes.append(f"{p.relative_to(REPO_ROOT)}:{ligne} : {valeur!r} ({nom})")
    return fautes


# --- balayage du dépôt -----------------------------------------------------------------------


def test_aucune_mention_du_test_gele() -> None:
    fautes = []
    for p in _fichiers():
        try:
            texte = p.read_text(encoding="utf-8").replace("\\", "/")
        except UnicodeDecodeError:
            continue
        for nom, motifs, exceptions in REGLES:
            if p in exceptions:
                continue
            fautes += [f"{p.relative_to(REPO_ROOT)} : {m} ({nom})" for m in motifs if re.search(m, texte)]
    assert not fautes, "Fichier interdit mentionné :\n" + "\n".join(fautes)


def test_aucun_acces_construit_hors_lot_c() -> None:
    fautes = _fautes_construites(p for p in _fichiers() if not _du_lot_c(p))
    assert not fautes, "Accès construit à un fichier interdit :\n" + "\n".join(fautes)


def test_aucun_acces_construit_lot_c() -> None:
    """Constat H1 corrigé par le lot C et intégré (lot E, 24/11) : le test est de nouveau bloquant."""
    fautes = _fautes_construites(p for p in _fichiers() if _du_lot_c(p))
    assert not fautes, "Accès construit à un fichier interdit (Lot C) :\n" + "\n".join(fautes)


# --- exemples inventés, en mémoire -------------------------------------------------------------

ATTRAPES = {
    "fstring_variable": 's = "test"\nf = f"data/final/{s}.jsonl"\n',
    "concatenation": 'f = "data/final/" + "test" + ".jsonl"\n',
    "path_division": 'from pathlib import Path\nf = Path("data/final") / "test.jsonl"\n',
    "path_division_fstring": 'from pathlib import Path\ns = "test"\nf = Path("data/final") / f"{s}.jsonl"\n',
    "os_path_join": 'import os\nf = os.path.join("data", "final", "test" + ".conll")\n',
    "format_positionnel": 'f = "data/final/{}.bio.jsonl".format("test")\n',
    "format_nomme": 'f = "data/final/documents_{split}.jsonl".format(split="test")\n',
    "boucle": 'for s in ("train", "dev", "test"):\n    f = f"data/final/{s}.jsonl"\n',
    "boucle_constante": 'SPLITS = ["dev", "test"]\nfor s in SPLITS:\n    f = f"data/final/fiches_{s}.jsonl"\n',
    "argument_de_fonction": (
        'def charger(split):\n    return open(f"data/final/{split}.jsonl")\n\nrows = charger("test")\n'
    ),
    "argument_conditionnel": (
        'def charger(split):\n    return open(f"data/final/{split}.jsonl")\n\n'
        'rows = charger("test" if a.test else "dev")\n'
    ),
    "argparse_choices": (
        "import argparse\nap = argparse.ArgumentParser()\n"
        'ap.add_argument("--split", default="dev", choices=["dev", "test"])\n'
        'a = ap.parse_args()\nf = f"data/final/{a.split}.jsonl"\n'
    ),
    "tuple_conditionnel": 'split, nom = ("test", "x") if t else ("dev", "y")\nf = f"data/final/{split}.jsonl"\n',
    "valeur_par_defaut": 'def lire(split="test"):\n    return f"data/final/{split}.conll"\n',
    "hf_test": 'from pathlib import Path\nHF = Path("data/final") / "hf"\nf = HF / ("te" + "st.jsonl")\n',
    "externe": 's = "test"\nf = "data/final/externe_" + s + ".jsonl"\n',
    "joinpath": 'from pathlib import Path\nf = Path("data/final").joinpath("documents_" + "test.jsonl")\n',
    "str_join": 'f = "/".join(["data", "final", "test.bio.jsonl"])\n',
    "kappa": 'f = "data/annotated/" + "humain_" + "kappa" + ".jsonl"\n',
}

IGNORES = {
    "dev": 's = "dev"\nf = f"data/final/{s}.jsonl"\n',
    "train": 'from pathlib import Path\nf = Path("data/final") / ("train" + ".jsonl")\n',
    "dev_et_train": 'for s in ("train", "dev"):\n    f = f"data/final/documents_{s}.jsonl"\n',
    "fichiers_de_tests": (
        'from pathlib import Path\nnom = "test"\nf = Path("tests") / f"test_{nom}.py"\n'
        'g = Path("tests") / ("test_" + "regles.py")\n'
    ),
    "commentaire": '# on lit le test plus tard\ns = "dev"  # pas le test\nf = f"data/final/{s}.jsonl"\n',
    "variable_inconnue": 'import sys\nf = f"data/final/{sys.argv[1]}.jsonl"\n',
    "sortie_nommee_test": 's = "test"\nf = f"results/xlmr_{s}_s42.jsonl"\n',
}


@pytest.mark.parametrize("cas", sorted(ATTRAPES))
def test_garde_fou_attrape(cas: str) -> None:
    assert acces_construits(ATTRAPES[cas]), cas


@pytest.mark.parametrize("cas", sorted(IGNORES))
def test_garde_fou_ignore(cas: str) -> None:
    assert acces_construits(IGNORES[cas]) == [], cas


def test_garde_fou_ligne_et_regle() -> None:
    src = 'import os\n\nx = 1\nf = os.path.join("data/final", f"{\'test\'}.jsonl")\n'
    assert acces_construits(src) == [(4, "test gelé", "data/final/test.jsonl")]


def test_garde_fou_suit_les_imports(tmp_path: Path) -> None:
    # Arbre en mémoire écrit dans un dossier temporaire : aucun vrai fichier du dépôt n'est lu.
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    lib = tmp_path / "pkg" / "lib.py"
    lib.write_text('def charger(split):\n    return open(f"data/final/{split}.jsonl")\n')
    appli = tmp_path / "pkg" / "appli.py"
    appli.write_text('from pkg.lib import charger\n\nrows = charger("test" if t else "dev")\n')
    sage = tmp_path / "pkg" / "sage.py"
    sage.write_text('from .lib import charger as c\n\nrows = c(split="dev")\n')
    sources = {p.resolve(): p.read_text() for p in (lib, appli, sage)}
    externes = appels_entre_modules(sources, tmp_path.resolve())
    assert acces_construits(sources[lib.resolve()], externes.get(lib.resolve())) == [
        (2, "test gelé", "data/final/test.jsonl")
    ]
    # Appelant en exception (comme scripts/final_eval.py) : pas de propagation.
    externes = appels_entre_modules(sources, tmp_path.resolve(), frozenset({appli.resolve()}))
    assert acces_construits(sources[lib.resolve()], externes.get(lib.resolve())) == []


def test_exceptions_limitees_a_claude_md() -> None:
    assert {p.relative_to(REPO_ROOT).as_posix() for p in EXC_TEST_GELE} == {"scripts/final_eval.py"}
    assert {p.relative_to(REPO_ROOT).as_posix() for p in EXC_KAPPA} == {"tests/test_non_regression_kappa.py"}
