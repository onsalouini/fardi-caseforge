"""Gabarits du générateur synthétique v4 : tableaux, listes, formulaires et rapports 8D.

Le Silver échoue sur les mises en page qui ne sont pas de la prose et sur trois étiquettes
(INDICATEUR, PROCESSUS, DONNEE_SENSIBLE) : ces gabarits en mettent beaucoup, dans des cellules
de tableau, des puces et des champs de formulaire. Aucun ne reprend une tournure du v3
(et donc aucune de la famille B, réservée au test gelé).

Emplacements annotés (entre accolades) :
  ORG, ACR -> ORG        PER, PERC, PER2 -> PERSONNE      SITE, SITEC -> SITE
  PROD -> PRODUIT        EQUIP, EQUIP2 -> EQUIPEMENT      PROC, PROC2 -> PROCESSUS
  IND, IND2, IND3 -> INDICATEUR                           CTR, CTR2 -> CONTRAINTE
  DS_LOT, DS_MAT, DS_NCR, DS_COUT, DS_MARGE, DS_MAIL, DS_TEL -> DONNEE_SENSIBLE
Emplacements non annotés : ROLE, ROLE2, SEM, CLIENT
"""

from __future__ import annotations

from typing import Final

TYPE_PASSAGE: Final[dict[str, str]] = {
    "entete": "autre",
    "contexte": "contexte",
    "tableau_ind": "probleme",
    "analyse": "probleme",
    "tableau_actions": "objectif",
    "contraintes": "contrainte",
    "confidentiel": "donnee",
    "contact": "autre",
    "probleme": "probleme",
    "causes": "probleme",
    "actions": "objectif",
    "donnees": "donnee",
    "identification": "donnee",
    "constat": "probleme",
    "mesures": "donnee",
    "signature": "autre",
    "d1": "autre",
    "d2": "probleme",
    "d3": "donnee",
    "d4": "probleme",
    "d5": "objectif",
    "d6": "contrainte",
}

FORMATS: Final[dict[str, tuple[str, ...]]] = {
    "tableau_suivi": (
        "entete",
        "contexte",
        "tableau_ind",
        "analyse",
        "tableau_actions",
        "contraintes",
        "confidentiel",
        "contact",
    ),
    "liste_actions": ("entete", "contexte", "probleme", "causes", "actions", "contraintes", "donnees", "contact"),
    "formulaire_audit": (
        "entete",
        "identification",
        "constat",
        "mesures",
        "analyse",
        "contraintes",
        "confidentiel",
        "signature",
    ),
    "rapport_8d": ("entete", "d1", "d2", "d3", "d4", "d5", "d6", "confidentiel"),
}

ENTETES: Final[dict[str, dict[str, str]]] = {
    "fr": {
        "tableau_suivi": "Tableau de bord hebdomadaire – semaine {SEM}",
        "liste_actions": "Plan d'actions – réunion du lundi, semaine {SEM}",
        "formulaire_audit": "Formulaire d'audit de poste – grille AUD-4",
        "rapport_8d": "Rapport 8D – réclamation client ouverte en semaine {SEM}",
    },
    "ar": {
        "tableau_suivi": "لوحة القيادة الأسبوعية – الأسبوع {SEM}",
        "liste_actions": "خطة العمل – اجتماع يوم الإثنين، الأسبوع {SEM}",
        "formulaire_audit": "استمارة تدقيق مركز العمل – الشبكة AUD-4",
        "rapport_8d": "تقرير 8D – شكوى حريف مفتوحة في الأسبوع {SEM}",
    },
    "en": {
        "tableau_suivi": "Weekly dashboard – week {SEM}",
        "liste_actions": "Action plan – Monday meeting, week {SEM}",
        "formulaire_audit": "Workstation audit form – grid AUD-4",
        "rapport_8d": "8D report – customer complaint opened in week {SEM}",
    },
}

PASSAGES: Final[dict[str, dict[str, str]]] = {
    "fr": {
        "contexte": "Site : {SITE} ({ORG}, {ACR}). Fabrication de {PROD} pour {CLIENT}.",
        "tableau_ind": (
            "| Poste | Indicateur suivi | Semaine précédente |\n| --- | --- | --- |\n"
            "| {EQUIP} | {IND} | {IND2} |\n"
            "| {EQUIP2} | {IND3} | stable |"
        ),
        "analyse": "Analyse menée par {PERC} ({ROLE}), outil utilisé : {PROC}. L'écart vient surtout du poste {EQUIP}.",
        "tableau_actions": (
            "| Action | Pilote | Outil |\n| --- | --- | --- |\n"
            "| Standardiser les réglages | {PERC} | {PROC2} |\n"
            "| Former l'équipe de nuit | {PER2} | {PROC} |"
        ),
        "contraintes": "- {CTR}\n- {CTR2}",
        "confidentiel": "Diffusion restreinte : coût de revient {DS_COUT}, {DS_MARGE}, lot concerné {DS_LOT}.",
        "contact": "Rédigé par {PER} ({ROLE}) · {DS_MAIL} · {DS_TEL}",
        "probleme": "Point bloquant : {IND} sur le poste {EQUIP} à {SITEC}, contre {IND2} il y a un mois.",
        "causes": (
            "Causes retenues :\n- réglages différents d'une équipe à l'autre sur {EQUIP} ;\n"
            "- {IND3} sur {EQUIP2} ;\n- démarche absente : {PROC2}."
        ),
        "actions": (
            "Actions décidées :\n- {PERC} : appliquer {PROC} sur {EQUIP} ;\n"
            "- {PER2} ({ROLE2}) : déployer {PROC2} ;\n- point d'avancement en semaine {SEM}."
        ),
        "donnees": "Données jointes : export des arrêts de {EQUIP2}, rapport {DS_NCR}, matricule opérateur {DS_MAT}.",
        "identification": ("Entreprise : {ORG}\nSite audité : {SITEC}\nProduit : {PROD}\nAuditeur : {PER2} ({ROLE2})"),
        "constat": "Constat : {IND} relevé sur {EQUIP} ; démarche non suivie en poste de nuit : {PROC}.",
        "mesures": "Mesures complémentaires :\n- {IND3}\n- {IND2} au dernier audit\n- poste voisin : {EQUIP2}",
        "signature": "Visa du responsable : {PER} – {ROLE} – {DS_TEL}",
        "d1": "D1 – Équipe : {PER} ({ROLE}), {PERC}, {PER2} ({ROLE2}) ; site {SITE}.",
        "d2": "D2 – Problème : réclamation {DS_NCR} sur {PROD}, lot {DS_LOT} ; {IND} constaté sur {EQUIP}.",
        "d3": "D3 – Confinement : tri à 100 % des stocks, {IND3} pendant le tri, arrêt de {EQUIP2}.",
        "d4": "D4 – Causes racines (outil : {PROC}) : usure de l'outillage de {EQUIP}, {IND2} avant la dérive.",
        "d5": "D5 – Actions correctives : {PROC2} sur {EQUIP}, suivi par {PERC} ; client informé ({CLIENT}).",
        "d6": "D6 – Contraintes de mise en œuvre : {CTR} ; {CTR2}.",
    },
    "ar": {
        "contexte": "الموقع: {SITE} ({ORG}). تصنيع {PROD} لفائدة {CLIENT}.",
        "tableau_ind": (
            "| مركز العمل | المؤشر المتابع | الأسبوع السابق |\n| --- | --- | --- |\n"
            "| {EQUIP} | {IND} | {IND2} |\n"
            "| {EQUIP2} | {IND3} | مستقر |"
        ),
        "analyse": "قام {PERC} ({ROLE}) بالتحليل باعتماد {PROC}: يعود الفارق أساسا إلى {EQUIP}.",
        "tableau_actions": (
            "| الإجراء | المسؤول | الأداة |\n| --- | --- | --- |\n"
            "| توحيد الضبط | {PERC} | {PROC2} |\n"
            "| تكوين الفريق الليلي | {PER2} | {PROC} |"
        ),
        "contraintes": "- {CTR}\n- {CTR2}",
        "confidentiel": "توزيع محدود: كلفة الإنتاج {DS_COUT}، {DS_MARGE}، الحصة المعنية {DS_LOT}.",
        "contact": "حرره {PER} ({ROLE}) · {DS_MAIL} · {DS_TEL}",
        "probleme": "نقطة الإشكال: {IND} على {EQUIP} في {SITEC}، مقابل {IND2} منذ شهر.",
        "causes": (
            "الأسباب المعتمدة:\n- اختلاف الضبط بين الفرق على {EQUIP}؛\n- {IND3} على {EQUIP2}؛\n- غياب {PROC2} موثقة."
        ),
        "actions": (
            "الإجراءات المقررة:\n- {PERC}: إطلاق {PROC} على {EQUIP}؛\n"
            "- {PER2} ({ROLE2}): تركيز {PROC2}؛\n- نقطة متابعة في الأسبوع {SEM}."
        ),
        "donnees": "المعطيات المرفقة: سجل توقفات {EQUIP2}، التقرير {DS_NCR}، رقم تسجيل العامل {DS_MAT}.",
        "identification": ("المؤسسة: {ORG}\nالموقع المدقق: {SITEC}\nالمنتوج: {PROD}\nالمدقق: {PER2} ({ROLE2})"),
        "constat": "المعاينة: تم تسجيل {IND} على {EQUIP}، ولا يتم تطبيق {PROC} في الفريق الليلي.",
        "mesures": "قياسات إضافية:\n- {IND3}\n- {IND2} في التدقيق الأخير\n- مركز العمل المجاور: {EQUIP2}",
        "signature": "تأشيرة المسؤول: {PER} – {ROLE} – {DS_TEL}",
        "d1": "D1 – الفريق: {PER} ({ROLE})، {PERC}، {PER2} ({ROLE2})؛ الموقع {SITE}.",
        "d2": "D2 – المشكل: الشكوى {DS_NCR} حول {PROD}، الحصة {DS_LOT}؛ تم تسجيل {IND} على {EQUIP}.",
        "d3": "D3 – الاحتواء: فرز كامل للمخزون، {IND3} أثناء الفرز، إيقاف {EQUIP2}.",
        "d4": "D4 – الأسباب الجذرية (عبر {PROC}): تآكل أدوات {EQUIP}، {IND2} قبل الانحراف.",
        "d5": "D5 – الإجراءات التصحيحية: {PROC2} على {EQUIP} بمتابعة {PERC}؛ تم إعلام الحريف ({CLIENT}).",
        "d6": "D6 – قيود التنفيذ: {CTR}؛ {CTR2}.",
    },
    "en": {
        "contexte": "Site: {SITE} ({ORG}, {ACR}). Manufacturing {PROD} for {CLIENT}.",
        "tableau_ind": (
            "| Workstation | Tracked indicator | Previous week |\n| --- | --- | --- |\n"
            "| {EQUIP} | {IND} | {IND2} |\n"
            "| {EQUIP2} | {IND3} | stable |"
        ),
        "analyse": "Analysis led by {PERC} ({ROLE}) using {PROC}: the gap mainly comes from the {EQUIP}.",
        "tableau_actions": (
            "| Action | Owner | Tool |\n| --- | --- | --- |\n"
            "| Standardise settings | {PERC} | {PROC2} |\n"
            "| Train the night shift | {PER2} | {PROC} |"
        ),
        "contraintes": "- {CTR}\n- {CTR2}",
        "confidentiel": "Restricted: unit cost {DS_COUT}, {DS_MARGE}, affected batch {DS_LOT}.",
        "contact": "Written by {PER} ({ROLE}) · {DS_MAIL} · {DS_TEL}",
        "probleme": "Blocking point: {IND} on the {EQUIP} in {SITEC}, against {IND2} a month ago.",
        "causes": (
            "Retained causes:\n- settings differ between shifts on the {EQUIP};\n"
            "- {IND3} on the {EQUIP2};\n- no formal {PROC2}."
        ),
        "actions": (
            "Agreed actions:\n- {PERC}: launch {PROC} on the {EQUIP};\n"
            "- {PER2} ({ROLE2}): set up {PROC2};\n- progress review in week {SEM}."
        ),
        "donnees": "Attached data: {EQUIP2} downtime export, report {DS_NCR}, operator ID {DS_MAT}.",
        "identification": ("Company: {ORG}\nAudited site: {SITEC}\nProduct: {PROD}\nAuditor: {PER2} ({ROLE2})"),
        "constat": "Finding: {IND} recorded on the {EQUIP}; {PROC} is not applied on the night shift.",
        "mesures": "Additional measurements:\n- {IND3}\n- {IND2} at the last audit\n- adjacent station: {EQUIP2}",
        "signature": "Manager sign-off: {PER} – {ROLE} – {DS_TEL}",
        "d1": "D1 – Team: {PER} ({ROLE}), {PERC}, {PER2} ({ROLE2}); site {SITE}.",
        "d2": "D2 – Problem: complaint {DS_NCR} on {PROD}, batch {DS_LOT}; {IND} found on the {EQUIP}.",
        "d3": "D3 – Containment: 100% sorting of stock, {IND3} during sorting, {EQUIP2} stopped.",
        "d4": "D4 – Root causes (via {PROC}): worn tooling on the {EQUIP}, {IND2} before the drift.",
        "d5": "D5 – Corrective actions: {PROC2} on the {EQUIP}, followed by {PERC}; customer informed ({CLIENT}).",
        "d6": "D6 – Implementation constraints: {CTR}; {CTR2}.",
    },
}

FICHE_FIXE: Final[dict[str, dict[str, object]]] = {
    "fr": {
        "titre": "Cas industriel – {secteur} : réduire une dérive sur un poste de production",
        "objectif_1": "Expliquer la dérive de l'indicateur suivant : {IND}.",
        "objectif_2": "Proposer un plan d'actions fondé sur la démarche suivante : {PROC}.",
        "donnees": "Relevés du poste {EQUIP} et indicateur de référence : {IND2}.",
        "consignes": ["Travailler par groupes de trois.", "Justifier chaque action par une donnée du cas."],
        "livrables": ["Une note d'analyse de deux pages.", "Un plan d'actions chiffré."],
        "criteres": ["Pertinence de l'analyse des causes.", "Réalisme du plan au regard des contraintes."],
    },
    "ar": {
        "titre": "حالة صناعية – {secteur}: الحد من انحراف في مركز إنتاج",
        "objectif_1": "تفسير انحراف المؤشر التالي: {IND}.",
        "objectif_2": "اقتراح خطة عمل تعتمد المنهجية التالية: {PROC}.",
        "donnees": "قياسات {EQUIP} والمؤشر المرجعي: {IND2}.",
        "consignes": ["العمل في مجموعات من ثلاثة طلبة.", "تبرير كل إجراء بمعطى من الحالة."],
        "livrables": ["مذكرة تحليل في صفحتين.", "خطة عمل مع تقدير الكلفة."],
        "criteres": ["وجاهة تحليل الأسباب.", "واقعية الخطة مقارنة بالقيود."],
    },
    "en": {
        "titre": "Industrial case – {secteur}: reducing a drift on a production workstation",
        "objectif_1": "Explain the drift of the following indicator: {IND}.",
        "objectif_2": "Propose an action plan based on the following approach: {PROC}.",
        "donnees": "Readings from the {EQUIP} and reference indicator: {IND2}.",
        "consignes": ["Work in groups of three.", "Justify each action with data from the case."],
        "livrables": ["A two-page analysis note.", "A costed action plan."],
        "criteres": ["Relevance of the root cause analysis.", "Realism of the plan given the constraints."],
    },
}

NOM_SECTEUR: Final[dict[str, dict[str, str]]] = {
    "fr": {
        "textile": "textile",
        "agroalimentaire": "agroalimentaire",
        "cablage": "câblage automobile",
        "mecanique": "mécanique",
        "plasturgie": "plasturgie",
        "pharma": "pharmaceutique",
    },
    "en": {
        "textile": "textile",
        "agroalimentaire": "food processing",
        "cablage": "automotive wiring",
        "mecanique": "mechanical engineering",
        "plasturgie": "plastics",
        "pharma": "pharmaceutical",
    },
    "ar": {
        "textile": "النسيج",
        "agroalimentaire": "الصناعات الغذائية",
        "cablage": "الأسلاك الكهربائية",
        "mecanique": "الميكانيك",
        "plasturgie": "البلاستيك",
        "pharma": "الأدوية",
    },
}
