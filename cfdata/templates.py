"""Gabarits de documents industriels simulés.

Chaque rôle de passage a deux variantes : [0] = famille A (train/dev), [1] = famille B (test).
Les documents de test sont donc écrits avec des tournures jamais vues à l'entraînement.

Emplacements annotés (entre accolades) :
  ORG, ACR -> ORG      PER, PERC -> PERSONNE   SITE, SITEC -> SITE
  PROD -> PRODUIT      EQUIP, EQUIP2 -> EQUIPEMENT   PROC -> PROCESSUS
  IND, IND2 -> INDICATEUR   CTR, CTR2 -> CONTRAINTE
  DS_CA, DS_CTR, DS_PRIX, DS_MAIL, DS_TEL -> DONNEE_SENSIBLE
Emplacements non annotés : ROLE, MOIS, CLIENT, MISSION
"""

PTYPE = {"header": "autre", "contexte": "contexte", "champs": "donnee", "probleme": "probleme",
         "demandeur": "objectif", "contraintes": "contrainte", "donnees": "donnee",
         "confidentiel": "donnee", "contact": "autre", "existant": "contexte"}

FORMATS = {
    "email": ["header", "contexte", "probleme", "existant", "demandeur", "contraintes", "donnees", "confidentiel", "contact"],
    "cahier_charges": ["header", "contexte", "probleme", "existant", "contraintes", "donnees", "demandeur", "confidentiel"],
    "pv_reunion": ["header", "contexte", "probleme", "existant", "demandeur", "contraintes", "donnees", "contact"],
    "fiche_nc": ["header", "champs", "probleme", "existant", "contraintes", "donnees", "confidentiel", "contact"],
    "demande_pfe": ["header", "contexte", "probleme", "existant", "demandeur", "contraintes", "donnees", "confidentiel", "contact"],
}

HEADERS = {
    "fr": {"email": ["Objet : demande d'accompagnement pour un projet d'amélioration industrielle",
                     "Objet : proposition d'un sujet de projet pour vos étudiants"],
           "cahier_charges": ["Cahier des charges – Projet d'amélioration industrielle",
                              "Cahier des charges simplifié – Étude technique proposée par l'entreprise"],
           "pv_reunion": ["Procès-verbal de réunion – Revue mensuelle de la production",
                          "Compte rendu de réunion – Point d'avancement qualité et production"],
           "fiche_nc": ["Fiche de non-conformité – Référence interne à compléter",
                        "Rapport d'écart qualité – Formulaire de déclaration interne"],
           "demande_pfe": ["Demande de projet de fin d'études – Proposition d'entreprise",
                           "Proposition de stage de fin d'études – Sujet industriel"]},
    "ar": {"email": ["الموضوع: طلب مرافقة لمشروع تحسين صناعي",
                     "الموضوع: اقتراح موضوع مشروع لفائدة طلبتكم"],
           "cahier_charges": ["كراس الشروط – مشروع تحسين صناعي",
                              "كراس شروط مبسط – دراسة فنية مقترحة من المؤسسة"],
           "pv_reunion": ["محضر جلسة – المراجعة الشهرية للإنتاج",
                          "تقرير اجتماع – متابعة الجودة والإنتاج"],
           "fiche_nc": ["بطاقة عدم مطابقة – مرجع داخلي للتعمير",
                        "تقرير انحراف في الجودة – استمارة تصريح داخلية"],
           "demande_pfe": ["طلب مشروع ختم الدروس – مقترح من المؤسسة",
                           "اقتراح تربص ختم الدروس – موضوع صناعي"]},
    "en": {"email": ["Subject: request for support on an industrial improvement project",
                     "Subject: proposed project topic for your students"],
           "cahier_charges": ["Specifications – Industrial improvement project",
                              "Simplified specifications – Technical study proposed by the company"],
           "pv_reunion": ["Meeting minutes – Monthly production review",
                          "Meeting report – Quality and production progress review"],
           "fiche_nc": ["Non-conformity report – Internal reference to be completed",
                        "Quality deviation report – Internal declaration form"],
           "demande_pfe": ["Final-year project request – Company proposal",
                           "Final-year internship proposal – Industrial topic"]},
}

PASSAGES = {
    "fr": {
        "contexte": ["{ORG} ({ACR}) est implantée dans {SITE}. Son produit principal, {PROD}, est livré à {CLIENT}.",
                     "Basée dans {SITE}, l'entreprise {ORG} travaille pour {CLIENT} ; sa gamme phare reste la suivante : {PROD}."],
        "champs": ["Entreprise : {ORG} | Site : {SITEC} | Produit : {PROD} | Équipement concerné : {EQUIP}",
                   "Déclarant : {ORG} | Localisation : {SITEC} | Article : {PROD} | Poste : {EQUIP}"],
        "probleme": ["Depuis {MOIS}, l'atelier constate un {IND} sur l'équipement « {EQUIP} », loin de l'objectif fixé. Les mesures ont été faites à {SITEC}.",
                     "Le problème principal concerne l'équipement suivant : {EQUIP}. Indicateur relevé : {IND}. Relevés effectués sur le site de {SITEC}."],
        "existant": ["{ACR} a déjà mené une première action sur l'équipement « {EQUIP} » avec l'appui de {PERC}, sans amélioration durable sur {SITEC}. Produit concerné : {PROD}.",
                     "Une tentative antérieure pilotée par {PERC} sur la machine {EQUIP} n'a pas suffi ; la direction de {ACR} à {SITEC} attend une approche structurée. Gamme touchée : {PROD}."],
        "demandeur": ["{PER}, {ROLE}, souhaite qu'un groupe d'étudiants {MISSION} en s'appuyant sur la démarche suivante : {PROC}.",
                      "Le projet est suivi par {PER} ({ROLE}). Démarche attendue : {PROC}."],
        "contraintes": ["Contraintes : {CTR}. De plus, {CTR2}.",
                        "Le partenaire impose les conditions suivantes : {CTR} ; {CTR2}."],
        "donnees": ["Données disponibles : relevés de l'équipement « {EQUIP2} », historique de six mois indiquant un {IND2}, fiches de non-conformité. Un premier diagnostic par {PROC} est disponible.",
                    "L'entreprise fournira les extractions de l'ERP, les relevés de la machine {EQUIP2} et l'historique suivant : {IND2}. Un atelier de {PROC} a déjà été animé."],
        "confidentiel": ["Le chiffre d'affaires de {ACR} ({DS_CA}) et le {DS_CTR} restent confidentiels.",
                         "À ne pas diffuser : prix de vente de {DS_PRIX} et {DS_CTR}."],
        "contact": ["Contact : {PERC} – {DS_MAIL} – {DS_TEL}",
                    "Pour toute question, joindre {PERC} au {DS_TEL} ou par courriel à {DS_MAIL}."],
    },
    "ar": {
        "contexte": ["تتمركز {ORG} ب{SITE}، ومنتوجها الرئيسي هو {PROD} الموجه إلى {CLIENT}.",
                     "تنشط {ORG} انطلاقا من {SITE} وتعمل لفائدة {CLIENT}، وأهم منتوجاتها {PROD}."],
        "champs": ["المؤسسة: {ORG} | الموقع: {SITEC} | المنتوج: {PROD} | التجهيز المعني: {EQUIP}",
                   "الجهة المصرحة: {ORG} | المكان: {SITEC} | السلعة: {PROD} | مركز العمل: {EQUIP}"],
        "probleme": ["منذ شهر {MOIS}، تم تسجيل {IND} على مستوى {EQUIP}، وهو بعيد عن الهدف المحدد. أجريت القياسات في {SITEC}.",
                     "يتعلق المشكل الرئيسي ب{EQUIP}، حيث تظهر القياسات الأخيرة {IND}. تم جمع القياسات بموقع {SITEC}."],
        "existant": ["سبق ل{ACR} أن قامت بإجراء أول على {EQUIP} بمساعدة {PERC}، دون تحسن دائم في موقع {SITEC}. المنتوج المعني: {PROD}.",
                     "لم تكن المحاولة السابقة التي أشرف عليها {PERC} على {EQUIP} كافية، وتنتظر إدارة {ACR} في {SITEC} مقاربة منظمة. السلعة المتأثرة: {PROD}."],
        "demandeur": ["يرغب {PER}، {ROLE}، في أن يعمل فريق من الطلبة على هذا المشكل باعتماد {PROC}.",
                      "يتابع المشروع {PER} ({ROLE})، والمنهجية المطلوبة هي {PROC}."],
        "contraintes": ["القيود: {CTR}. كما {CTR2}.",
                        "يفرض الشريك الشروط التالية: {CTR}؛ {CTR2}."],
        "donnees": ["المعطيات المتوفرة: قياسات {EQUIP2}، وسجل لمدة ستة أشهر يبين {IND2}، وبطاقات عدم المطابقة. يتوفر تشخيص أولي ب{PROC}.",
                    "ستوفر المؤسسة مستخرجات من نظام التصرف المندمج وقياسات {EQUIP2} وسجلا يبين {IND2}. تم تنظيم ورشة حول {PROC}."],
        "confidentiel": ["رقم معاملات {ORG} ({DS_CA}) و{DS_CTR} سريان.",
                         "معلومات لا يجب نشرها: سعر البيع {DS_PRIX} و{DS_CTR}."],
        "contact": ["للاتصال: {PERC} – {DS_MAIL} – {DS_TEL}",
                    "لأي استفسار يمكن الاتصال ب{PERC} على الرقم {DS_TEL} أو عبر البريد {DS_MAIL}."],
    },
    "en": {
        "contexte": ["{ORG} ({ACR}) is based in {SITE} and its main product, {PROD}, is supplied to {CLIENT}.",
                     "Operating from {SITE}, {ORG} serves {CLIENT}; its flagship range is {PROD}."],
        "champs": ["Company: {ORG} | Site: {SITEC} | Product: {PROD} | Equipment concerned: {EQUIP}",
                   "Reporting entity: {ORG} | Location: {SITEC} | Item: {PROD} | Workstation: {EQUIP}"],
        "probleme": ["Since {MOIS}, the measured {IND} on the {EQUIP} is well below target. Measurements were taken in {SITEC}.",
                     "The main issue concerns the {EQUIP}. Key indicator: {IND}. Readings were collected at the {SITEC} site."],
        "existant": ["{ACR} already ran a first action on the {EQUIP} with the help of {PERC}, without lasting improvement at the {SITEC} site. Product concerned: {PROD}.",
                     "A previous attempt led by {PERC} on the {EQUIP} was not enough; {ACR} management in {SITEC} expects a structured approach. Affected range: {PROD}."],
        "demandeur": ["{PER}, {ROLE}, would like a student team to {MISSION} using {PROC}.",
                      "The project is supervised by {PER} ({ROLE}); the expected approach is {PROC}."],
        "contraintes": ["Constraints: {CTR}. In addition, {CTR2}.",
                        "The partner sets the following conditions: {CTR}; {CTR2}."],
        "donnees": ["Available data: readings from the {EQUIP2}, a six-month history of the {IND2}, non-conformity reports. A first {PROC} diagnosis is available.",
                    "The company will provide ERP extracts, {EQUIP2} logs and the following indicator history: {IND2}. A {PROC} workshop has already been held."],
        "confidentiel": ["The turnover of {ACR} ({DS_CA}) and {DS_CTR} are confidential.",
                         "Not for distribution: unit price of {DS_PRIX} and {DS_CTR}."],
        "contact": ["Contact: {PERC} – {DS_MAIL} – {DS_TEL}",
                    "For any question, contact {PERC} at {DS_TEL} or by e-mail at {DS_MAIL}."],
    },
}

# Fiche pédagogique de référence : textes fixes (origine = gabarit) par langue
FICHE_FIXED = {
    "fr": {"titre": "Cas industriel – {sector} : amélioration d'un indicateur de performance",
           "objectif_1": "Analyser les causes de la dégradation de l'indicateur suivant : {IND}.",
           "objectif_2": "Proposer et chiffrer une solution en appliquant la démarche : {PROC}.",
           "consignes": ["Travailler en équipe de 4 à 5 étudiants.",
                         "Justifier chaque proposition par une donnée du cas.",
                         "Respecter toutes les contraintes listées."],
           "livrables": ["Rapport d'analyse (10 pages maximum)", "Plan d'action chiffré", "Présentation orale de 15 minutes"],
           "criteres": ["Pertinence de l'analyse des causes (30 %)", "Faisabilité et respect des contraintes (30 %)",
                        "Qualité du chiffrage (20 %)", "Clarté de la présentation (20 %)"]},
    "ar": {"titre": "حالة صناعية – {sector}: تحسين مؤشر أداء",
           "objectif_1": "تحليل أسباب تدهور المؤشر التالي: {IND}.",
           "objectif_2": "اقتراح حل مع تقدير كلفته باعتماد المنهجية: {PROC}.",
           "consignes": ["العمل ضمن فريق من 4 إلى 5 طلبة.", "تبرير كل مقترح بمعطى من الحالة.", "احترام جميع القيود المذكورة."],
           "livrables": ["تقرير تحليل (10 صفحات على الأكثر)", "خطة عمل مع تقدير الكلفة", "عرض شفوي لمدة 15 دقيقة"],
           "criteres": ["وجاهة تحليل الأسباب (30 %)", "قابلية التنفيذ واحترام القيود (30 %)",
                        "جودة تقدير الكلفة (20 %)", "وضوح العرض (20 %)"]},
    "en": {"titre": "Industrial case – {sector}: improving a performance indicator",
           "objectif_1": "Analyse the root causes behind the following indicator: {IND}.",
           "objectif_2": "Propose and cost a solution applying the approach: {PROC}.",
           "consignes": ["Work in teams of 4 to 5 students.", "Support every proposal with data from the case.",
                         "Comply with every listed constraint."],
           "livrables": ["Analysis report (10 pages maximum)", "Costed action plan", "15-minute oral presentation"],
           "criteres": ["Relevance of the root-cause analysis (30%)", "Feasibility and compliance with constraints (30%)",
                        "Quality of the costing (20%)", "Clarity of the presentation (20%)"]},
}
