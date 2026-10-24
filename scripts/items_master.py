"""One cross-linked table of items: stats, loot economy on every map and recipe usage.

usage: items_master.py DATA_DIR CFG_JSON_DIR OUT_CSV [LANGUAGECORE_PBO]

Joins, on lower-cased class name: clothing.csv, weapons.csv, food.csv, loot_types_<map>.csv, recipes.csv and the
merged configs (parent class, weight, display name). Recipe columns: `recipes_as_ingredient_direct` counts live recipes
that list the item's own class; `recipes_as_ingredient_via_ancestor` counts those that list an ancestor class (often a
generic base such as Inventory_Base, so it is large for nearly every item) and not the item itself; `recipes_as_result`
counts recipes that create it. All three count distinct recipe classes, whatever the number of slots that match. Kind `unknown` means the name is in a loot table but in none of the parsed config sections.
Read-only; nothing is executed.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAPS = [("chernarus", "chernarus"), ("enoch", "livonia"), ("nasdara", "nasdara"), ("sakhal", "sakhal")]


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    data, cfgdir, out = sys.argv[1:4]
    pbo = sys.argv[4] if len(sys.argv) > 4 else None
    os.environ["DAYZ_CFG_JSON"] = cfgdir
    sys.path.insert(0, HERE)
    import cfgmodel as m
    S = m.load()
    secs = [("cfgweapons", "other (cfgweapons)"), ("cfgmagazines", "magazine"), ("cfgvehicles", "other (cfgvehicles)")]
    tbl = None
    if pbo:
        import stringtable
        tbl = stringtable.load(pbo)

    clothing = {r["name"].lower(): r for r in read(os.path.join(data, "clothing.csv"))}
    weapons = {r["name"].lower(): r for r in read(os.path.join(data, "weapons.csv"))}
    food = {r["name"].lower(): r for r in read(os.path.join(data, "food.csv"))}
    loot = {}
    names = {}
    for fn, label in MAPS:
        for r in read(os.path.join(data, f"loot_types_{fn}.csv")):
            k = r["name"].lower()
            loot.setdefault(k, {})[label] = r
            names.setdefault(k, r["name"])
    for d in (clothing, weapons, food):
        for k, r in d.items():
            names.setdefault(k, r["name"])

    recipes = [r for r in read(os.path.join(data, "recipes.csv")) if r["registered"] == "yes"]
    # distinct recipe identities per class name: a recipe that lists a class in both ingredient slots counts once
    ingr_recipes, result_recipes = {}, {}
    for r in recipes:
        for x in {c.strip().lower() for col in ("ingredient1", "ingredient2") for c in r[col].split("|") if c.strip()}:
            ingr_recipes.setdefault(x, set()).add(r["class"])
        for x in {c.strip().lower() for c in r["results"].split("|") if c.strip()}:
            result_recipes.setdefault(x, set()).add(r["class"])

    cache = {}
    rows = []
    for k in sorted(names):
        name = names[k]
        sec = next((s for s, _ in secs if k in S.get(s, {})), None)
        kind = ("clothing" if k in clothing else "weapon" if k in weapons else "food" if k in food else
                "building-or-object" if name.startswith("Land_") else
                dict(secs).get(sec, "unknown") if sec else "unknown")
        chain = [c.lower() for c in m.chain(S[sec], name)] if sec else [k]
        parent = chain[1] if len(chain) > 1 else ""
        res = m.resolve(S[sec], name, cache) if sec else {}
        src = clothing.get(k) or weapons.get(k) or food.get(k) or {}
        disp = src.get("displayName", "")
        if not disp and tbl and isinstance(res.get("displayName"), str):
            import stringtable
            disp = stringtable.english(tbl, res["displayName"]) or ""
        weight = src.get("weight") or res.get("weight", "")
        l0 = next((loot[k][lab] for _, lab in MAPS if k in loot and lab in loot[k]), {})
        row = {"name": name, "displayName": disp, "kind": kind, "parent": parent,
               "slot": clothing.get(k, {}).get("slot", ""), "weight_g": weight}
        for _, lab in MAPS:
            row[f"nominal_{lab}"] = loot.get(k, {}).get(lab, {}).get("nominal", "")
        row["category"] = l0.get("category", "")
        row["usage"] = l0.get("usage", "")
        row["tier"] = l0.get("value", "")
        row["lifetime_s"] = l0.get("lifetime", "")
        row["maps_with_loot"] = len(loot.get(k, {}))
        direct = ingr_recipes.get(k, set())
        via = set().union(*(ingr_recipes.get(c, set()) for c in set(chain[1:]))) - direct if len(chain) > 1 else set()
        row["recipes_as_ingredient_direct"] = len(direct)
        row["recipes_as_ingredient_via_ancestor"] = len(via)
        row["recipes_as_result"] = len(result_recipes.get(k, set()))
        row["has_clothing_stats"] = "yes" if k in clothing else ""
        row["has_weapon_stats"] = "yes" if k in weapons else ""
        row["has_food_stats"] = "yes" if k in food else ""
        rows.append(row)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} items; with loot on at least one map: {sum(1 for r in rows if r['maps_with_loot'])}; "
          f"named directly in a live recipe: {sum(1 for r in rows if r['recipes_as_ingredient_direct'] or r['recipes_as_result'])}")


if __name__ == "__main__":
    main()
