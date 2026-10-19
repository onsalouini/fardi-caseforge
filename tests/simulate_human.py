"""TEST UNIQUEMENT — simule les étapes humaines (Label Studio) pour vérifier que toute la chaîne fonctionne.
Transforme les pré-annotations d'un fichier de tâches en faux export Label Studio (1 ou 2 « annotateurs »).
Ne JAMAIS utiliser sa sortie comme vraie annotation.

    python tests/simulate_human.py <tasks.json> <export.json>
"""
import json, random, sys

tasks = json.load(open(sys.argv[1], encoding="utf-8"))
rng = random.Random(0)
for i, t in enumerate(tasks):
    pred = t.pop("predictions")[0]["result"]
    choices = [r for r in pred if r["type"] == "choices"]
    if not choices:  # documents réels : attributs à remplir
        choices = [{"from_name": n, "to_name": "text", "type": "choices", "value": {"choices": [v]}}
                   for n, v in (("lang", t["data"].get("lang_auto", "fr")), ("sensitivity", "forte"), ("ptype", "contexte"))]
    labels = [r for r in pred if r["type"] == "labels"]
    anns = [{"completed_by": {"email": "annotateur_A@test"}, "was_cancelled": False, "result": labels + choices}]
    if i % 5 == 0:  # 20 % en double annotation, le second oublie parfois une entité
        b = [l for l in labels if rng.random() > 0.1]
        anns.append({"completed_by": {"email": "annotateur_B@test"}, "was_cancelled": False, "result": b + choices})
    t["annotations"] = anns
json.dump(tasks, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
print(f"{len(tasks)} tâches simulées -> {sys.argv[2]}")
