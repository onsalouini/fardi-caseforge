"""Lexiques du générateur synthétique v4 (FR / AR / EN).

Tous les noms sont FICTIFS et **disjoints** de ceux du générateur v3 (``cfdata/pools.py``) :
personnes, villes, entreprises, vocabulaire métier, indicateurs, contraintes et normes. Le v3
réservait une partition de ses lexiques au test gelé (famille B) : en n'en réutilisant aucun
terme, le v4 ne peut pas ressembler au test sans avoir à le lire.
``tests/test_gold_generateur.py`` vérifie cette disjonction.
"""

from __future__ import annotations

from typing import Final

SECTEURS: Final[tuple[str, ...]] = ("textile", "agroalimentaire", "cablage", "mecanique", "plasturgie", "pharma")

# ---------------------------------------------------------------- personnes : (latin, arabe, genre)
PRENOMS: Final[tuple[tuple[str, str, str], ...]] = (
    ("Achraf", "أشرف", "m"),
    ("Lamia", "لمياء", "f"),
    ("Oussama", "أسامة", "m"),
    ("Sirine", "سيرين", "f"),
    ("Moez", "معز", "m"),
    ("Rania", "رانية", "f"),
    ("Zied", "زياد", "m"),
    ("Hiba", "هبة", "f"),
    ("Aymen", "أيمن", "m"),
    ("Nesrine", "نسرين", "f"),
    ("Chokri", "شكري", "m"),
    ("Imen", "إيمان", "f"),
    ("Haythem", "هيثم", "m"),
    ("Marwa", "مروى", "f"),
    ("Lotfi", "لطفي", "m"),
    ("Abir", "عبير", "f"),
    ("Wael", "وائل", "m"),
    ("Ghada", "غادة", "f"),
    ("Adel", "عادل", "m"),
    ("Kaouther", "كوثر", "f"),
    ("Skander", "إسكندر", "m"),
    ("Najla", "نجلاء", "f"),
    ("Montassar", "منتصر", "m"),
    ("Feriel", "فريال", "f"),
)
NOMS: Final[tuple[tuple[str, str], ...]] = (
    ("Bouslama", "بوسلامة"),
    ("Chouchane", "الشوشان"),
    ("Ghorbel", "الغربال"),
    ("Brahmi", "البراهمي"),
    ("Turki", "التركي"),
    ("Ksouri", "القصوري"),
    ("Fakhfakh", "الفخفاخ"),
    ("Bouraoui", "البوراوي"),
    ("Mzali", "المزالي"),
    ("Sghaier", "الصغير"),
    ("Guesmi", "القاسمي"),
    ("Nasri", "الناصري"),
    ("Amri", "العمري"),
    ("Ellouze", "اللوز"),
    ("Kchaou", "الكشاو"),
    ("Belaid", "بلعيد"),
    ("Zribi", "الزريبي"),
    ("Chtioui", "الشتيوي"),
    ("Sellami", "السلامي"),
    ("Bahri", "البحري"),
)
TITRES: Final[dict[str, dict[str, str]]] = {
    "fr": {"m": "M.", "f": "Mme"},
    "en": {"m": "Mr.", "f": "Ms."},
    "ar": {"m": "السيد", "f": "السيدة"},
}
FONCTIONS: Final[dict[str, tuple[tuple[str, str], ...]]] = {  # (masculin, féminin)
    "fr": (
        ("chef d'atelier", "cheffe d'atelier"),
        ("responsable amélioration continue", "responsable amélioration continue"),
        ("ingénieur méthodes", "ingénieure méthodes"),
        ("auditeur interne", "auditrice interne"),
        ("responsable des achats", "responsable des achats"),
        ("pilote de ligne", "pilote de ligne"),
    ),
    "en": (
        ("workshop supervisor",) * 2,
        ("continuous improvement lead",) * 2,
        ("industrial engineer",) * 2,
        ("internal auditor",) * 2,
        ("purchasing manager",) * 2,
        ("line leader",) * 2,
    ),
    "ar": (
        ("رئيس الورشة", "رئيسة الورشة"),
        ("مسؤول التحسين المستمر", "مسؤولة التحسين المستمر"),
        ("مهندس الطرق الصناعية", "مهندسة الطرق الصناعية"),
        ("مدقق داخلي", "مدققة داخلية"),
        ("مسؤول المشتريات", "مسؤولة المشتريات"),
        ("قائد الخط", "قائدة الخط"),
    ),
}

# ---------------------------------------------------------------- lieux : (latin, arabe)
VILLES: Final[tuple[tuple[str, str], ...]] = (
    ("Tozeur", "توزر"),
    ("Gafsa", "قفصة"),
    ("Kasserine", "القصرين"),
    ("Le Kef", "الكاف"),
    ("Sidi Bouzid", "سيدي بوزيد"),
    ("Tataouine", "تطاوين"),
    ("Manouba", "منوبة"),
    ("Ariana", "أريانة"),
    ("Hammamet", "الحمامات"),
    ("Sayada", "الصيادة"),
    ("Jemmal", "جمال"),
    ("El Jem", "الجم"),
    ("Bekalta", "البقالطة"),
    ("Teboulba", "طبلبة"),
    ("Mateur", "ماطر"),
    ("Soliman", "سليمان"),
)
FORMES_SITE: Final[dict[str, tuple[str, ...]]] = {
    "fr": ("le pôle industriel de {c}", "l'unité de {c}", "l'atelier de {c}"),
    "en": ("the {c} plant", "the {c} industrial park", "the {c} unit"),
    "ar": ("القطب الصناعي ب{c}", "وحدة {c}", "ورشة {c}"),
}

# ---------------------------------------------------------------- entreprises : (fr, ar, en)
FORMES_ORG: Final[dict[str, tuple[str, ...]]] = {
    "fr": ("SARL", "Manufacture", "Usines", "Comptoir"),
    "ar": ("مصانع", "الشركة التونسية", "المصنع", "دار"),
    "en": ("Works", "Co.", "Holding", "Plants"),
}
NOMS_ORG: Final[tuple[tuple[str, str, str], ...]] = (
    ("Nakhla", "النخلة", "Nakhla"),
    ("El Fajr", "الفجر", "Fajr"),
    ("Rimel", "الرمال", "Rimel"),
    ("Chams", "الشمس", "Chams"),
    ("Bassatine", "البساتين", "Bassatine"),
    ("Kantaoui", "القنطاوي", "Kantaoui"),
    ("Djerba", "جربة", "Djerba"),
    ("Thala", "تالة", "Thala"),
    ("Dougga", "دقة", "Dougga"),
    ("Sbeitla", "سبيطلة", "Sbeitla"),
    ("Elissa", "عليسة", "Elissa"),
    ("Najma", "النجمة", "Najma"),
    ("Essalam", "السلام", "Essalam"),
    ("Bou Kornine", "بوقرنين", "Bou Kornine"),
    ("Chenini", "شنني", "Chenini"),
)

# ---------------------------------------------------------------- vocabulaire métier (listes alignées fr / ar / en)
LEXIQUE_SECTEUR: Final[dict[str, dict[str, dict[str, tuple[str, ...]]]]] = {
    "textile": {
        "act": {"fr": ("Confection",), "ar": ("للملابس الجاهزة",), "en": ("Apparel",)},
        "prod": {
            "fr": ("polos piqués", "pulls en maille", "uniformes hospitaliers", "linge de lit"),
            "ar": ("قمصان البولو", "الأقمصة الصوفية", "أزياء المستشفيات", "أغطية الأسرة"),
            "en": ("piqué polo shirts", "knitted sweaters", "hospital uniforms", "bed linen"),
        },
        "equip": {
            "fr": ("métier à tricoter circulaire", "machine à broder", "table de matelassage", "tunnel de vaporisage"),
            "ar": ("آلة الحياكة الدائرية", "آلة التطريز", "طاولة فرد القماش", "نفق التبخير"),
            "en": ("circular knitting machine", "embroidery machine", "spreading table", "steam tunnel"),
        },
        "proc": {
            "fr": ("équilibrage de chaîne", "méthode SMED", "contrôle par échantillonnage"),
            "ar": ("توازن سلسلة الإنتاج", "طريقة تغيير السلسلة السريع", "المراقبة بالعينات"),
            "en": ("line balancing", "SMED method", "acceptance sampling"),
        },
    },
    "agroalimentaire": {
        "act": {"fr": ("Conserverie",), "ar": ("للمصبرات",), "en": ("Canning",)},
        "prod": {
            "fr": ("thon à l'huile", "confiture de figues", "couscous précuit", "jus d'orange maltaise"),
            "ar": ("التن المصبر", "معجون التين", "الكسكسي المطهو مسبقا", "عصير البرتقال المالطي"),
            "en": ("canned tuna in oil", "fig jam", "pre-cooked couscous", "maltese orange juice"),
        },
        "equip": {
            "fr": ("autoclave de stérilisation", "doseuse volumétrique", "four tunnel", "trieuse optique"),
            "ar": ("جهاز التعقيم بالضغط", "آلة التعبئة الحجمية", "الفرن النفقي", "آلة الفرز البصري"),
            "en": ("sterilisation retort", "volumetric filler", "tunnel oven", "optical sorter"),
        },
        "proc": {
            "fr": ("méthode des 5 pourquoi", "analyse de Pareto", "démarche 5S"),
            "ar": ("طريقة لماذا الخمس", "تحليل باريتو", "منهجية 5S"),
            "en": ("5 Whys method", "Pareto analysis", "5S approach"),
        },
    },
    "cablage": {
        "act": {"fr": ("Connectique",), "ar": ("للربط الكهربائي",), "en": ("Connectors",)},
        "prod": {
            "fr": ("faisceaux de portière", "câbles coaxiaux", "boîtiers de fusibles", "faisceaux de tableau de bord"),
            "ar": ("حزم أسلاك الأبواب", "الكوابل المحورية", "علب المصاهر", "حزم أسلاك لوحة القيادة"),
            "en": ("door harnesses", "coaxial cables", "fuse boxes", "dashboard harnesses"),
        },
        "equip": {
            "fr": ("machine de coupe-dénudage", "poste de soudure ultrasons", "testeur de continuité", "enrouleuse"),
            "ar": ("آلة القص والتعرية", "محطة اللحام بالموجات فوق الصوتية", "جهاز اختبار الاستمرارية", "آلة اللف"),
            "en": ("cut-and-strip machine", "ultrasonic welding station", "continuity tester", "coiling machine"),
        },
        "proc": {
            "fr": ("méthode 8D", "détrompage Poka-Yoke", "cartographie des flux"),
            "ar": ("منهجية 8D", "نظام منع الأخطاء", "رسم خرائط التدفق"),
            "en": ("8D method", "Poka-Yoke error proofing", "value stream mapping"),
        },
    },
    "mecanique": {
        "act": {"fr": ("Fonderie",), "ar": ("للمسبوكات",), "en": ("Foundry",)},
        "prod": {
            "fr": ("carters de pompe", "vannes en fonte", "pignons trempés", "supports moteur"),
            "ar": ("أغلفة المضخات", "الصمامات الحديدية", "المسننات المقساة", "حوامل المحركات"),
            "en": ("pump housings", "cast iron valves", "hardened pinions", "engine mounts"),
        },
        "equip": {
            "fr": ("four à induction", "rectifieuse plane", "cellule de grenaillage", "robot de soudage"),
            "ar": ("فرن الحث", "آلة التجليخ المستوي", "خلية السفع بالحبيبات", "روبوت اللحام"),
            "en": ("induction furnace", "surface grinder", "shot blasting cell", "welding robot"),
        },
        "proc": {
            "fr": ("maintenance productive totale", "démarche Kaizen", "méthode DMAIC"),
            "ar": ("الصيانة الإنتاجية الشاملة", "منهجية كايزن", "منهجية DMAIC"),
            "en": ("total productive maintenance", "Kaizen approach", "DMAIC method"),
        },
    },
    "plasturgie": {
        "act": {"fr": ("Emballages",), "ar": ("للتغليف",), "en": ("Packaging",)},
        "prod": {
            "fr": ("gobelets thermoformés", "sacs tissés", "flacons cosmétiques", "tubes en PEHD"),
            "ar": ("الأكواب المشكلة حراريا", "الأكياس المنسوجة", "قوارير مواد التجميل", "أنابيب البولي إيثيلين"),
            "en": ("thermoformed cups", "woven bags", "cosmetic bottles", "HDPE pipes"),
        },
        "equip": {
            "fr": ("thermoformeuse", "ligne de calandrage", "sécheur de granulés", "robot de dépose"),
            "ar": ("آلة التشكيل الحراري", "خط الصقل", "مجفف الحبيبات", "روبوت الوضع"),
            "en": ("thermoforming machine", "calendering line", "pellet dryer", "pick-and-place robot"),
        },
        "proc": {
            "fr": ("gestion visuelle Kanban", "méthode QRQC", "démarche 5S"),
            "ar": ("الإدارة البصرية كانبان", "منهجية الاستجابة السريعة للجودة", "منهجية 5S"),
            "en": ("Kanban visual management", "QRQC method", "5S approach"),
        },
    },
    "pharma": {
        "act": {"fr": ("Laboratoires",), "ar": ("للمخابر",), "en": ("Laboratories",)},
        "prod": {
            "fr": ("sachets effervescents", "collyres stériles", "suppositoires", "poudres orales"),
            "ar": ("الأكياس الفوارة", "قطرات العين المعقمة", "التحاميل", "المساحيق الفموية"),
            "en": ("effervescent sachets", "sterile eye drops", "suppositories", "oral powders"),
        },
        "equip": {
            "fr": ("granulateur à haut cisaillement", "remplisseuse aseptique", "étuve de séchage", "encartonneuse"),
            "ar": ("المحبب عالي القص", "آلة التعبئة المعقمة", "فرن التجفيف", "آلة التعليب في الكرتون"),
            "en": ("high-shear granulator", "aseptic filler", "drying oven", "cartoning machine"),
        },
        "proc": {
            "fr": ("revue annuelle qualité produit", "méthode des 5 pourquoi", "qualification des équipements"),
            "ar": ("المراجعة السنوية لجودة المنتوج", "طريقة لماذا الخمس", "تأهيل التجهيزات"),
            "en": ("annual product quality review", "5 Whys method", "equipment qualification"),
        },
    },
}

# ------------------------------------------ indicateurs : gabarits, puis (plage plausible, plus haut = mieux)
INDICATEURS: Final[dict[str, tuple[str, ...]]] = {
    "fr": (
        "taux de non-conformité de {n} %",
        "temps de cycle de {n} secondes",
        "taux de disponibilité de {n} %",
        "consommation d'énergie de {n} kWh par tonne",
        "taux d'absentéisme de {n} %",
        "MTTR de {n} minutes",
        "rendement au premier passage de {n} %",
        "stock moyen de {n} jours",
    ),
    "ar": (
        "نسبة عدم المطابقة تبلغ {n} %",
        "زمن الدورة يبلغ {n} ثانية",
        "نسبة الجاهزية تبلغ {n} %",
        "استهلاك الطاقة يبلغ {n} كيلوواط ساعة للطن",
        "نسبة التغيب تبلغ {n} %",
        "متوسط زمن الإصلاح يبلغ {n} دقيقة",
        "مردود المرور الأول يبلغ {n} %",
        "متوسط المخزون يبلغ {n} يوما",
    ),
    "en": (
        "non-conformity rate of {n}%",
        "cycle time of {n} seconds",
        "availability rate of {n}%",
        "energy use of {n} kWh per tonne",
        "absenteeism rate of {n}%",
        "MTTR of {n} minutes",
        "first pass yield of {n}%",
        "average stock of {n} days",
    ),
}
PLAGES_INDICATEUR: Final[tuple[tuple[tuple[int, ...], bool], ...]] = (
    ((3, 4, 5, 6, 8, 9, 11), False),
    ((38, 42, 45, 48, 52, 55, 60), False),
    ((74, 78, 81, 84, 87, 90, 93), True),
    ((310, 340, 365, 390, 420, 450, 480), False),
    ((4, 5, 6, 7, 8, 9, 10), False),
    ((25, 30, 35, 40, 45, 55, 70), False),
    ((76, 80, 83, 86, 89, 92, 95), True),
    ((12, 15, 18, 21, 24, 28, 32), False),
)

# ---------------------------------------------------------------- contraintes ({n} = nombre, {norm} = norme)
CONTRAINTES: Final[dict[str, tuple[str, ...]]] = {
    "fr": (
        "les essais ne peuvent avoir lieu que le samedi",
        "l'investissement est plafonné à {n}000 DT",
        "un changement de série ne doit pas dépasser {n} minutes",
        "la certification {norm} doit être conservée",
        "toute modification doit être validée par le client final",
        "l'étude doit durer au plus {n} semaines",
    ),
    "ar": (
        "لا يمكن إجراء التجارب إلا يوم السبت",
        "الاستثمار محدد بسقف {n}000 دينار",
        "يجب ألا يتجاوز تغيير السلسلة {n} دقيقة",
        "يجب المحافظة على شهادة {norm}",
        "يجب أن يصادق الحريف النهائي على كل تعديل",
        "يجب ألا تتجاوز مدة الدراسة {n} أسابيع",
    ),
    "en": (
        "trials can only take place on Saturdays",
        "investment is capped at TND {n},000",
        "a changeover must not exceed {n} minutes",
        "the {norm} certification must be kept",
        "any change must be approved by the end customer",
        "the study must last no more than {n} weeks",
    ),
}
VALEURS_CONTRAINTE: Final[dict[int, tuple[int, ...]]] = {1: (15, 20, 25, 40, 60), 2: (10, 15, 20, 30), 5: (5, 6, 7, 8)}
NORMES: Final[tuple[str, ...]] = ("ISO 50001", "ISO 22716", "BRCGS", "FSSC 22000", "OEKO-TEX", "ISO 15378")

# ---------------------------------------------------------------- abréviations (bruit sur le texte non annoté)
ABREVIATIONS: Final[dict[str, dict[str, str]]] = {
    "fr": {
        "responsable": "resp.",
        "production": "prod.",
        "semaine": "sem.",
        "numéro": "n°",
        "ligne": "lg",
        "commande": "cde",
        "fournisseur": "fourn.",
        "contrôle": "ctrl",
    },
    "en": {
        "production": "prod.",
        "number": "no.",
        "week": "wk",
        "department": "dept.",
        "quality": "QA",
        "maintenance": "maint.",
        "supplier": "supp.",
    },
    "ar": {},
}

# ---------------------------------------------------------------- mots non annotés
SEMAINES: Final[tuple[int, ...]] = (6, 11, 15, 19, 23, 37, 42, 47)
CLIENTS: Final[dict[str, tuple[str, ...]]] = {
    "fr": (
        "un équipementier allemand",
        "des hôpitaux publics",
        "une chaîne de pharmacies",
        "des distributeurs libyens",
    ),
    "en": ("a German supplier", "public hospitals", "a pharmacy chain", "Libyan distributors"),
    "ar": ("مزود ألماني", "المستشفيات العمومية", "سلسلة صيدليات", "موزعين ليبيين"),
}
