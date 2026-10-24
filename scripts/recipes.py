"""Parse the crafting recipe scripts into one CSV row per recipe class.

usage: recipes.py SCRIPTS_DIR OUT_CSV [LANGUAGECORE_PBO]

SCRIPTS_DIR is an unpacked scripts.pbo (see pbo_unpack.py). Reads
4_World/Classes/Recipes/Recipes/*.c and the registration list in
PluginRecipesManagerBase.c. With the language archive, adds the English recipe name.
Read-only on the game files.
"""
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REC_DIR = os.path.join("4_World", "Classes", "Recipes", "Recipes")
UNIT_SECONDS = 4.0  # CRAFTING_TIME_UNIT_SIZE in 3_Game/constants.c


def strip_comments(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def block(src, start):
    """Text between the brace that follows `start` and its match."""
    i = src.index("{", start)
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i + 1:j]
    return src[i + 1:]


def new_state():
    return {"ing": {0: [], 1: []}, "snd": {0: {}, 1: {}}, "results": [], "vals": {}, "res": {}}


def copy_state(s):
    return {"ing": {k: list(v) for k, v in s["ing"].items()}, "snd": {k: dict(v) for k, v in s["snd"].items()},
            "results": list(s["results"]), "vals": dict(s["vals"]), "res": {k: dict(v) for k, v in s["res"].items()}}


def num(v):
    v = v.strip().rstrip(";")
    if v in ("true", "false"):
        return v == "true"
    try:
        return float(v) if "." in v else int(v)
    except ValueError:
        return v


def run_init(body, parent_state):
    st = copy_state(parent_state) if parent_state else new_state()
    for stmt in body.split(";"):
        stmt = " ".join(stmt.split())
        if not stmt:
            continue
        if stmt == "super.Init()":
            continue
        m = re.match(r'm_Name\s*=\s*"([^"]*)"', stmt)
        if m:
            st["vals"]["name_key"] = m.group(1)
            continue
        m = re.match(r"m_(IsInstaRecipe|AnimationLength|Specialty|AnywhereInInventory)\s*=\s*(.+)", stmt)
        if m:
            st["vals"][m.group(1)] = num(m.group(2))
            continue
        m = re.match(r"m_(Min|Max)(Damage|Quantity)Ingredient\[(\d)\]\s*=\s*(.+)", stmt)
        if m:
            st["vals"][f"{m.group(1).lower()}{m.group(2)}{m.group(3)}"] = num(m.group(4))
            continue
        m = re.match(r"m_Ingredient(AddHealth|SetHealth|AddQuantity|Destroy|UseSoftSkills)\[(\d)\]\s*=\s*(.+)", stmt)
        if m:
            st["vals"][f"ing{m.group(1)}{m.group(2)}"] = num(m.group(3))
            continue
        m = re.match(r'InsertIngredient(Ex)?\s*\(\s*(\d)\s*,\s*"([^"]+)"(?:\s*,\s*"([^"]*)")?', stmt)
        if m:
            idx, name = int(m.group(2)), m.group(3)
            if name not in st["ing"][idx]:
                st["ing"][idx].append(name)
            if m.group(1) and m.group(4):
                st["snd"][idx][name] = m.group(4)
            continue
        m = re.match(r'RemoveIngredient\s*\(\s*(\d)\s*,\s*"([^"]+)"', stmt)
        if m:
            idx, name = int(m.group(1)), m.group(2)
            if name in st["ing"][idx]:
                st["ing"][idx].remove(name)
            continue
        m = re.match(r'AddResult\s*\(\s*"([^"]+)"', stmt)
        if m:
            st["results"].append(m.group(1))
            continue
        m = re.match(r"m_Result(\w+)\[(\d+)\]\s*=\s*(.+)", stmt)
        if m:
            st["res"].setdefault(int(m.group(2)), {})[m.group(1)] = num(m.group(3))
    return st


def parse_registration(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    reg, com = set(), set()
    for blk in re.findall(r"/\*.*?\*/", src, flags=re.S):  # block-commented registrations
        com.update(re.findall(r"RegisterRecipe\s*\(\s*new\s+(\w+)", blk))
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    for line in src.splitlines():
        m = re.match(r"\s*(//)?\s*RegisterRecipe\s*\(\s*new\s+(\w+)", line)
        if m:
            (com if m.group(1) else reg).add(m.group(2))
    return reg, com - reg


def effect(vals, i):
    out = []
    if vals.get(f"ingDestroy{i}") is True:
        out.append("destroyed")
    q = vals.get(f"ingAddQuantity{i}", 0)
    if q:
        out.append(f"quantity {q:+g}" if isinstance(q, (int, float)) else f"quantity {q}")
    h = vals.get(f"ingAddHealth{i}", 0)
    if h:
        out.append(f"health {h:+g}")
    sh = vals.get(f"ingSetHealth{i}", -1)
    if sh not in (-1, None):
        out.append(f"set health {sh}")
    return "; ".join(out) or "kept"


def where(v):
    if isinstance(v, bool):  # a literal true/false in the source is 1/0 in Enforce
        v = int(v)
    if v == -2:
        return "ground"
    if v == -1:
        return "inventory"
    return f"swap with ingredient {v}"

# What a custom Do() does, from the calls in its body: (regex on the body, tag).
DO_TAGS = [
    (r"PaintItem\.Paint|\bPaint\s*\(", "repaints the item (swaps it for the painted type)"),
    (r"TurnItemIntoItem", "turns the item into another type"),
    (r"OpenAndSwitch", "opens the item (swaps it for its opened type)"),
    (r"TransferItemProperties", "copies quantity, health and other properties to the result"),
    (r"\b(Set|Add)Quantity(Normalized)?\s*\(", "changes ingredient or result quantity"),
    (r"\b(Set|Add|Decrease)Health\w*\s*\(", "changes health"),
    (r"\bRepair\s*\(", "repairs the item"),
    (r"SpawnEntity\w*\s*\(|CreateObject\w*\s*\(|CreateAttachment", "spawns extra items"),
    (r"\bRandom\w*\s*\(", "random outcome"),
    (r"SetBloodyHands|UpdateBloodyHandsVisibility", "bloodies the player's hands"),
    (r"SetCleanness", "sets cleanness"),
    (r"RemoveAllAgents\w*\s*\(|InsertAgent", "changes agents on the item"),
    (r"AttemptAddBleedingSource|GetBleedingManagerServer", "can cause a bleeding wound on the player"),
    (r"\b(Open|Close)\s*\(", "opens or closes a container"),
    (r"\bTransfer\s*\(|GetLiquidType|SetLiquidType|PourLiquid|DrainLiquid|Liquid\w*\.", "moves or checks liquid"),
    (r"GetCompEM|EnergyManager", "uses the item's energy manager"),
    (r"DeleteSafe|\.Delete\s*\(", "deletes an item"),
    (r"\bSetPosition\s*\(|ServerTakeEntityToTargetAttachment|LocalTakeEntityToTargetAttachment", "places or attaches the result"),
    (r"DropAllItemsInInventoryInBounds", "drops cargo on the ground"),
    (r"\.Upgrade\s*\(", "upgrades a torch (lard or liquid fuel)"),
    (r"SetWireType", "records the wire material on the trap result"),
    (r"StandUp", "stands the player up"),
    (r"SetBloodTypeVisible|GetBloodType", "reveals the blood type"),
    (r"ConfigGet\w*\s*\(", "reads values from item config"),
    (r"GetPlugin\s*\(", "uses a plugin (for example the weapon cleaning / repair plugin)"),
]


def do_summary(do_body):
    tags = [t for rx, t in DO_TAGS if re.search(rx, do_body)]
    return "; ".join(tags) if tags else "(other / not classified)"


def effective(classes, name, field, super_call):
    """Declaring classes and bodies of the effective implementation of a method.

    Walks from the class up its parent chain; the nearest class that declares the method contributes its body, and the
    walk continues to the parent only when that body calls the parent implementation (`super.Method(`)."""
    declared, bodies, cur, n = [], [], name, 0
    while cur in classes and n < 40:
        body = classes[cur][field]
        if body is not None:
            declared.append(cur)
            bodies.append(body)
            if not re.search(super_call, body):
                break
        cur = classes[cur]["parent"]
        n += 1
    return declared, bodies


def main():
    scripts, out = sys.argv[1], sys.argv[2]
    tbl = None
    if len(sys.argv) > 3:
        import stringtable
        tbl = stringtable.load(sys.argv[3])
    rec = os.path.join(scripts, REC_DIR)
    classes = {}
    for fn in sorted(os.listdir(rec)):
        if not fn.endswith(".c") or fn == "PluginRecipesManagerBase.c":
            continue
        src = strip_comments(open(os.path.join(rec, fn), encoding="utf-8", errors="replace").read())
        for m in re.finditer(r"class\s+(\w+)\s*(?:extends|:)\s*(\w+)", src):
            name, parent = m.group(1), m.group(2)
            cls = block(src, m.end())
            init = re.search(r"override\s+void\s+Init\s*\(\s*\)", cls)
            cando = re.search(r"bool\s+CanDo\s*\([^)]*\)", cls)
            do = re.search(r"void\s+Do\s*\(", cls)
            classes[name] = {"parent": parent, "file": fn, "init": block(cls, init.start()) if init else "",
                             "can_body": block(cls, cando.start()) if cando else None,
                             "do_body": block(cls, do.start()) if do else None}
    for name, c in classes.items():
        can_in, can_bodies = effective(classes, name, "can_body", r"super\s*\.\s*CanDo\s*\(")
        do_in, do_bodies = effective(classes, name, "do_body", r"super\s*\.\s*Do\s*\(")
        c["custom_can"] = any(" ".join(b.split()) != "return true;" for b in can_bodies)
        c["can_declared_in"] = "|".join(can_in)
        c["custom_do"] = bool(do_bodies)
        c["do_declared_in"] = "|".join(do_in)
        c["do_effects"] = do_summary(chr(10).join(do_bodies)) if do_bodies else ""
    reg, com = parse_registration(os.path.join(rec, "PluginRecipesManagerBase.c"))
    states = {}

    def state(name):
        if name in states:
            return states[name]
        c = classes[name]
        ps = state(c["parent"]) if c["parent"] in classes else None
        states[name] = run_init(c["init"], ps)
        return states[name]

    rows = []
    for name, c in classes.items():
        if name in ("PrepareAnimal", "PrepareFish", "CutOutSeeds") and name not in reg and name not in com:
            kind = "base class"
        else:
            kind = ""
        st = state(name)
        v = st["vals"]
        key = v.get("name_key", "")
        eng = ""
        if tbl and key.startswith("#"):
            import stringtable
            eng = stringtable.english(tbl, "$" + key[1:]) or ""
        res_to = []
        for i in range(len(st["results"])):
            r = st["res"].get(i, {})
            res_to.append(where(r.get("ToInventory", -2)))
        rows.append({
            "class": name, "parent": c["parent"], "file": c["file"],
            "registered": "yes" if name in reg else ("commented out" if name in com else ("base class" if kind else "no")),
            "name_key": key, "name": eng,
            "instant": v.get("IsInstaRecipe", False),
            "seconds": round(float(v.get("AnimationLength", 1)) * UNIT_SECONDS, 2),
            "specialty": v.get("Specialty", 0),
            "anywhere_in_inventory": v.get("AnywhereInInventory", False),
            "ingredient1": " | ".join(st["ing"][0]), "ingredient1_effect": effect(v, 0),
            "ingredient2": " | ".join(st["ing"][1]), "ingredient2_effect": effect(v, 1),
            "min_qty1": v.get("minQuantity0", ""), "min_qty2": v.get("minQuantity1", ""),
            "max_dmg1": v.get("maxDamage0", ""), "max_dmg2": v.get("maxDamage1", ""),
            "results": " | ".join(st["results"]), "result_goes": " | ".join(res_to),
            "inherits_color": any(r.get("InheritsColor", -1) != -1 for r in st["res"].values()),
            "extra_condition": c["custom_can"],
            "custom_do": c["custom_do"], "do_effects": c["do_effects"],
            "can_declared_in": c["can_declared_in"], "do_declared_in": c["do_declared_in"],
        })
    fields = list(rows[0].keys())
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"classes: {len(rows)}  registered: {sum(r['registered'] == 'yes' for r in rows)}  "
          f"commented out: {sum(r['registered'] == 'commented out' for r in rows)}  "
          f"not registered: {sum(r['registered'] == 'no' for r in rows)}")


if __name__ == "__main__":
    main()
