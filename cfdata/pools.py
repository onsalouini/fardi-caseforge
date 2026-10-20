"""Lexiques du générateur de problèmes industriels simulés (FR / AR / EN).

Tous les noms (entreprises, personnes, contrats, coordonnées) sont FICTIFS.
Les noms propres sont coupés en trois partitions (A train, B test, C dev) et le vocabulaire métier en deux
(A et C / B) : voir cfdata.generate.family_items et vocab_items. Le test contient donc des noms et des termes
jamais vus à l'entraînement : le modèle ne peut pas réussir en mémorisant.
"""

SECTORS = ["textile", "agroalimentaire", "cablage", "mecanique", "plasturgie", "pharma"]

# ---------------------------------------------------------------- personnes
FIRST_LAT = ["Karim", "Sonia", "Mehdi", "Amira", "Walid", "Rim", "Youssef", "Ines", "Hatem", "Nadia",
             "Sami", "Leila", "Anis", "Olfa", "Bilel", "Salma", "Fares", "Hela", "Nizar", "Yasmine",
             "Tarek", "Mouna", "Slim", "Emna", "Hamza", "Asma", "Riadh", "Dorra", "Khaled", "Wafa"]
LAST_LAT = ["Belhadj", "Trabelsi", "Gharbi", "Ben Salah", "Jebali", "Mansouri", "Chaabane", "Ayari",
            "Hammami", "Bouazizi", "Khelifi", "Mejri", "Sassi", "Dridi", "Zouari", "Ferchichi",
            "Kammoun", "Baccouche", "Riahi", "Chebbi", "Ghannouchi", "Mabrouk", "Tlili", "Jaziri",
            "Saidi", "Cherif", "Hadded", "Masmoudi", "Laabidi", "Ben Amor"]
FIRST_AR = ["كريم", "سنية", "مهدي", "أميرة", "وليد", "ريم", "يوسف", "إيناس", "حاتم", "نادية",
            "سامي", "ليلى", "أنيس", "ألفة", "بلال", "سلمى", "فارس", "هالة", "نزار", "ياسمين",
            "طارق", "منى", "سليم", "آمنة", "حمزة", "أسماء", "رياض", "درة", "خالد", "وفاء"]
LAST_AR = ["بالحاج", "الطرابلسي", "الغربي", "بن صالح", "الجبالي", "المنصوري", "شعبان", "العياري",
           "الحمامي", "البوعزيزي", "الخليفي", "المجري", "الساسي", "الدريدي", "الزواري", "الفرشيشي",
           "كمون", "بكوش", "الرياحي", "الشابي", "الغنوشي", "مبروك", "التليلي", "الجزيري",
           "السعيدي", "الشريف", "الحداد", "المصمودي", "العبيدي", "بن عمر"]
TITLE = {"fr": {"m": "M.", "f": "Mme"}, "en": {"m": "Mr.", "f": "Ms."}, "ar": {"m": "السيد", "f": "السيدة"}}
FEMALE_IDX = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29}

ROLES = {
    "fr": ["responsable qualité", "directeur de production", "responsable maintenance", "chef de projet méthodes",
           "responsable logistique", "directrice technique", "responsable HSE", "ingénieur process"],
    "en": ["quality manager", "production director", "maintenance manager", "methods project lead",
           "supply chain manager", "technical director", "HSE manager", "process engineer"],
    "ar": ["مسؤول الجودة", "مدير الإنتاج", "مسؤول الصيانة", "رئيس مشروع الطرق",
           "مسؤول اللوجستيك", "المديرة الفنية", "مسؤول السلامة والبيئة", "مهندس العمليات"],
}

# ---------------------------------------------------------------- lieux
CITIES = [("Sfax", "صفاقس"), ("Sousse", "سوسة"), ("Bizerte", "بنزرت"), ("Ben Arous", "بن عروس"),
          ("Monastir", "المنستير"), ("Nabeul", "نابل"), ("Gabès", "قابس"), ("Kairouan", "القيروان"),
          ("Béja", "باجة"), ("Médenine", "مدنين"), ("Mahdia", "المهدية"), ("Zaghouan", "زغوان"),
          ("Menzel Bourguiba", "منزل بورقيبة"), ("Ksar Hellal", "قصر هلال"), ("Enfidha", "النفيضة"),
          ("Mégrine", "مقرين"), ("Jendouba", "جندوبة"), ("Siliana", "سليانة")]
SITE_FORMS = {
    "fr": ["la zone industrielle de {c}", "l'usine de {c}", "le site de {c}", "la ZI de {c}"],
    "en": ["the {c} industrial zone", "{c}", "the {c} site", "the {c} free zone"],
    "ar": ["المنطقة الصناعية ب{c}", "ولاية {c}", "المنطقة الصناعية {c}", "مدينة {c}"],
}

# ---------------------------------------------------------------- entreprises
ORG_FORMS = {"fr": ["Société", "Groupe", "Établissements", "Compagnie", "Ateliers"],
             "ar": ["شركة", "مجمع", "مؤسسة", "شركة", "معامل"],
             "en": ["Industries", "Manufacturing", "Group", "Systems", "Ltd"]}
ORG_NAMES = [("du Cap Bon", "الوطن القبلي", "Cap Bon"), ("El Amal", "الأمل", "El Amal"),
             ("Méditerranée", "المتوسط", "Mediterranean"), ("du Sahel", "الساحل", "Sahel"),
             ("Carthage", "قرطاج", "Carthage"), ("Ennour", "النور", "Ennour"),
             ("Zitouna", "الزيتونة", "Zitouna"), ("Atlas", "الأطلس", "Atlas"),
             ("Jasmin", "الياسمين", "Jasmine"), ("Horizon", "الأفق", "Horizon"),
             ("El Baraka", "البركة", "Baraka"), ("Kerkennah", "قرقنة", "Kerkennah"),
             ("Medjerda", "مجردة", "Medjerda"), ("Ifriqiya", "إفريقية", "Ifriqiya"),
             ("Oasis", "الواحة", "Oasis"), ("Dar Chaabane", "دار شعبان", "Dar Chaabane"),
             ("Tabarka", "طبرقة", "Tabarka"), ("Hannibal", "حنبعل", "Hannibal")]

SECTOR_LEX = {
    "textile": {
        "act": {"fr": "Textiles", "ar": "للنسيج", "en": "Textiles"},
        "prod": {"fr": ["jeans stretch", "chemises en coton", "vêtements de travail", "tissu denim indigo"],
                 "ar": ["سراويل الجينز", "القمصان القطنية", "ملابس العمل", "قماش الدنيم"],
                 "en": ["stretch jeans", "cotton shirts", "workwear garments", "indigo denim fabric"]},
        "equip": {"fr": ["ligne de teinture n°2", "machine de coupe automatique", "rameuse", "presse à repasser"],
                  "ar": ["خط الصباغة رقم 2", "آلة القص الآلي", "آلة التجفيف", "مكبس الكي"],
                  "en": ["dyeing line 2", "automatic cutting machine", "stenter frame", "ironing press"]},
        "proc": {"fr": ["maîtrise statistique des procédés", "maintenance préventive", "AMDEC"],
                 "ar": ["التحكم الإحصائي في العمليات", "الصيانة الوقائية", "تحليل الأعطال وآثارها"],
                 "en": ["statistical process control", "preventive maintenance", "FMEA"]},
    },
    "agroalimentaire": {
        "act": {"fr": "Agroalimentaire", "ar": "للصناعات الغذائية", "en": "Foods"},
        "prod": {"fr": ["huile d'olive extra vierge", "conserves de tomate", "dattes conditionnées", "harissa en tube"],
                 "ar": ["زيت الزيتون البكر الممتاز", "معجون الطماطم", "التمور المعلبة", "الهريسة"],
                 "en": ["extra virgin olive oil", "canned tomato paste", "packed dates", "harissa paste"]},
        "equip": {"fr": ["ligne d'embouteillage n°1", "sertisseuse", "pasteurisateur", "étiqueteuse"],
                  "ar": ["خط التعبئة رقم 1", "آلة السدّ", "جهاز البسترة", "آلة التلصيق"],
                  "en": ["bottling line 1", "can seamer", "pasteurizer", "labelling machine"]},
        "proc": {"fr": ['méthode HACCP', "diagramme d'Ishikawa", 'maîtrise statistique des procédés'],
                 "ar": ["نظام تحليل المخاطر", "مخطط إيشيكاوا", "التحكم الإحصائي في العمليات"],
                 "en": ["HACCP plan", "Ishikawa diagram", "statistical process control"]},
    },
    "cablage": {
        "act": {"fr": "Câblage", "ar": "للأسلاك الكهربائية", "en": "Wiring"},
        "prod": {"fr": ["faisceaux de câbles X-200", "connecteurs étanches", "faisceaux moteur", "câbles de batterie"],
                 "ar": ["حزم الأسلاك X-200", "الموصلات العازلة", "حزم أسلاك المحرك", "كوابل البطارية"],
                 "en": ["X-200 cable harnesses", "sealed connectors", "engine harnesses", "battery cables"]},
        "equip": {"fr": ["banc de test électrique", "machine de sertissage", "planche de montage", "dénudeuse"],
                  "ar": ["منصة الاختبار الكهربائي", "آلة التثبيت", "لوحة التركيب", "آلة التعرية"],
                  "en": ["electrical test bench", "crimping machine", "assembly board", "wire stripper"]},
        "proc": {"fr": ["AMDEC processus", "analyse des causes racines", "maîtrise statistique des procédés"],
                 "ar": ["تحليل أعطال العملية وآثارها", "تحليل الأسباب الجذرية", "التحكم الإحصائي في العمليات"],
                 "en": ["process FMEA", "root cause analysis", "statistical process control"]},
    },
    "mecanique": {
        "act": {"fr": "Mécanique de Précision", "ar": "للميكانيك الدقيقة", "en": "Precision Engineering"},
        "prod": {"fr": ["pièces usinées en aluminium", "arbres de transmission", "brides en acier", "engrenages"],
                 "ar": ["القطع المصنعة من الألومنيوم", "أعمدة النقل", "الشفاه الفولاذية", "التروس"],
                 "en": ["machined aluminium parts", "drive shafts", "steel flanges", "gears"]},
        "equip": {"fr": ["centre d'usinage CN", "tour à commande numérique", "presse hydraulique 200 t", "machine à mesurer tridimensionnelle"],
                  "ar": ["مركز التشغيل الرقمي", "المخرطة الرقمية", "المكبس الهيدروليكي 200 طن", "آلة القياس ثلاثية الأبعاد"],
                  "en": ["CNC machining centre", "CNC lathe", "200 t hydraulic press", "coordinate measuring machine"]},
        "proc": {"fr": ["maîtrise statistique des procédés", "maintenance préventive", "AMDEC"],
                 "ar": ["التحكم الإحصائي في العمليات", "الصيانة الوقائية", "تحليل الأعطال وآثارها"],
                 "en": ["statistical process control", "preventive maintenance", "FMEA"]},
    },
    "plasturgie": {
        "act": {"fr": "Plastiques", "ar": "للبلاستيك", "en": "Plastics"},
        "prod": {"fr": ["bouteilles en PET", "caisses en polypropylène", "films d'emballage", "bouchons injectés"],
                 "ar": ["قوارير البلاستيك", "صناديق البولي بروبيلين", "أغشية التغليف", "السدادات المحقونة"],
                 "en": ["PET bottles", "polypropylene crates", "packaging films", "injected caps"]},
        "equip": {"fr": ["presse à injecter 350 t", "extrudeuse bi-vis", "souffleuse", "broyeur"],
                  "ar": ["آلة الحقن 350 طن", "آلة البثق", "آلة النفخ", "آلة الطحن"],
                  "en": ["350 t injection press", "twin-screw extruder", "blow moulder", "granulator"]},
        "proc": {"fr": ['réglage des paramètres de moulage', "plan d'expériences", 'maîtrise statistique des procédés'],
                 "ar": ["ضبط معايير القولبة", "تصميم التجارب", "التحكم الإحصائي في العمليات"],
                 "en": ["moulding parameter tuning", "design of experiments", "statistical process control"]},
    },
    "pharma": {
        "act": {"fr": "Pharmaceutique", "ar": "للأدوية", "en": "Pharma"},
        "prod": {"fr": ["comprimés pelliculés", "sirops pédiatriques", "gélules", "pommades"],
                 "ar": ["الأقراص المغلفة", "أشربة الأطفال", "الكبسولات", "المراهم"],
                 "en": ["film-coated tablets", "paediatric syrups", "capsules", "ointments"]},
        "equip": {"fr": ["comprimeuse rotative", "blistereuse", "mélangeur en V", "lit d'air fluidisé"],
                  "ar": ["آلة الضغط الدوارة", "آلة التعبئة في الأشرطة", "خلاط على شكل V", "مجفف الطبقة المميعة"],
                  "en": ["rotary tablet press", "blister machine", "V-blender", "fluid bed dryer"]},
        "proc": {"fr": ["analyse des risques qualité", "maintenance préventive", "AMDEC"],
                 "ar": ["تحليل مخاطر الجودة", "الصيانة الوقائية", "تحليل الأعطال وآثارها"],
                 "en": ["quality risk analysis", "preventive maintenance", "FMEA"]},
    },
}

# ---------------------------------------------------------------- indicateurs et contraintes ({n} = nombre)
INDICATORS = {
    "fr": ["TRS de {n} %", "taux de rebut de {n} %", "délai moyen de livraison de {n} jours",
           "MTBF de {n} heures", "taux de service de {n} %", "taux de réclamation de {n} %"],
    "ar": ["نسبة مردود إجمالي للمعدات تبلغ {n} %", "نسبة فضلات تبلغ {n} %", "معدل آجال تسليم يبلغ {n} أيام",
           "متوسط زمن بين الأعطال يبلغ {n} ساعة", "نسبة خدمة تبلغ {n} %", "نسبة شكايات تبلغ {n} %"],
    "en": ["OEE of {n}%", "scrap rate of {n}%", "average lead time of {n} days",
           "MTBF of {n} hours", "service level of {n}%", "complaint rate of {n}%"],
}
CONSTRAINTS = {
    "fr": ["la ligne ne peut pas être arrêtée plus de {n} heures par semaine",
           "le budget alloué ne doit pas dépasser {n}000 DT",
           "les livraisons doivent être réalisées sous {n} jours",
           "la solution doit respecter la norme {norm}",
           "aucun recrutement supplémentaire n'est autorisé",
           "le projet doit être terminé en {n} semaines"],
    "ar": ["يجب ألا تتجاوز مدة توقف الخط {n} ساعات في الأسبوع",
           "يجب ألا تتجاوز الميزانية المخصصة {n}000 دينار",
           "يجب إنجاز التسليمات في أجل {n} أيام",
           "يجب أن يحترم الحل المواصفة {norm}",
           "لا يسمح بأي انتداب إضافي",
           "يجب إنهاء المشروع في {n} أسابيع"],
    "en": ["the line cannot be stopped for more than {n} hours per week",
           "the budget must not exceed {n}000 TND",
           "deliveries must be completed within {n} days",
           "the solution must comply with {norm}",
           "no additional hiring is allowed",
           "the project must be completed within {n} weeks"],
}
NORMS = ["ISO 9001", "ISO 14001", "IATF 16949", "ISO 22000", "ISO 45001", "ISO 13485"]

# ---------------------------------------------------------------- abréviations (bruit réaliste sur le texte non annoté)
ABBREV = {
    "fr": {"production": "prod.", "semaine": "sem.", "maintenance": "maint.", "responsable": "resp.",
           "quantité": "qté", "référence": "réf.", "numéro": "n°", "environ": "env."},
    "en": {"production": "prod.", "maintenance": "maint.", "quantity": "qty", "approximately": "approx.",
           "department": "dept.", "reference": "ref."},
    "ar": {},
}

# ---------------------------------------------------------------- mots non annotés
MONTHS = {"fr": ["janvier", "mars", "mai", "septembre", "octobre"],
          "en": ["January", "March", "May", "September", "October"],
          "ar": ["جانفي", "مارس", "ماي", "سبتمبر", "أكتوبر"]}
CLIENTS = {"fr": ["un constructeur automobile européen", "deux donneurs d'ordre italiens", "la grande distribution locale", "des clients à l'export"],
           "en": ["a European car maker", "two Italian contractors", "local retail chains", "export customers"],
           "ar": ["مصنع سيارات أوروبي", "حريفين إيطاليين", "المساحات التجارية الكبرى", "حرفاء في الخارج"]}
MISSIONS = {"fr": ["analyse les causes du problème", "propose un plan d'amélioration", "dimensionne une solution chiffrée", "réorganise le flux de production"],
            "en": ["analyse the root causes", "propose an improvement plan", "size a costed solution", "redesign the production flow"],
            "ar": ["يحلل أسباب المشكل", "يقترح خطة تحسين", "يقترح حلا مع تقدير كلفته", "يعيد تنظيم تدفق الإنتاج"]}
