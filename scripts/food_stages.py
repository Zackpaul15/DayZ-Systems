"""Food stage table: per food item and stage, cooking thresholds, nutrition and stage transitions.

usage: food_stages.py CFG_JSON_DIR OUT_CSV [LANGUAGECORE_PBO]

Reads the merged configs (cfgmodel.py), keeps every cfgvehicles class that has a Food >> FoodStages body, and writes one
row per item and stage:
  cook_min_temp, cook_time_s, cook_max_temp   cooking_properties [min temperature, time, max temperature (drying only)]
  nutrition_properties                        as in config (index meaning: see notes 6.20)
  transitions                                 FoodStageTransitions, as ToX:method->stage with cooking method names
Stage ids: 1 Raw, 2 Baked, 3 Boiled, 4 Dried, 5 Burned, 6 Rotten. Cooking methods: 1 baking, 2 boiling, 3 drying, 4 time.
Read-only; nothing is executed.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = {1: "Raw", 2: "Baked", 3: "Boiled", 4: "Dried", 5: "Burned", 6: "Rotten"}
METHOD = {0: "none", 1: "baking", 2: "boiling", 3: "drying", 4: "time"}


def fmt(v):
    return "|".join(str(x) for x in v) if isinstance(v, list) else ("" if v is None else str(v))


def main():
    cfgdir, out = sys.argv[1:3]
    pbo = sys.argv[3] if len(sys.argv) > 3 else None
    os.environ["DAYZ_CFG_JSON"] = cfgdir
    sys.path.insert(0, HERE)
    import cfgmodel as m
    S = m.load()
    tbl = None
    if pbo:
        import stringtable
        tbl = stringtable.load(pbo)
    cache = {}
    rows = []
    items = 0
    for name in sorted(S["cfgvehicles"]):
        r = m.resolve(S["cfgvehicles"], name, cache)
        food = r.get("Food")
        if not isinstance(food, dict) or not isinstance(food.get("FoodStages"), dict):
            continue
        if r.get("scope", 0) < 2:
            continue
        stages = {k: v for k, v in food["FoodStages"].items() if isinstance(v, dict)}
        if not stages:
            continue
        items += 1
        name = S["cfgvehicles"][name].get("__name__", name)
        trans = food.get("FoodStageTransitions") or {}
        disp = r.get("displayName", "")
        if tbl and isinstance(disp, str):
            import stringtable
            disp = stringtable.english(tbl, disp) or disp
        for st, body in stages.items():
            cp = body.get("cooking_properties") or []
            cp = list(cp) + [None] * (3 - len(cp))
            tr = []
            for tn, tb in (trans.get(st) or {}).items():
                if isinstance(tb, dict) and "transition_to" in tb:
                    tr.append(f"{tn}:{METHOD.get(tb.get('cooking_method'), tb.get('cooking_method'))}->"
                              f"{STAGE.get(tb['transition_to'], tb['transition_to'])}")
            rows.append({"item": name, "displayName": disp, "stage": st, "cook_min_temp": fmt(cp[0]),
                         "cook_time_s": fmt(cp[1]), "cook_max_temp": fmt(cp[2]),
                         "nutrition_properties": fmt(body.get("nutrition_properties")),
                         "transitions": "; ".join(tr)})
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{items} food items, {len(rows)} stage rows")


if __name__ == "__main__":
    main()
