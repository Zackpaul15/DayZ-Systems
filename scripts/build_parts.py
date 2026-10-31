"""Base-building parts and construction tools from the merged configs (task S1).

usage: build_parts.py CFG_JSON_DIR SCRIPTS_DIR OUT_PARTS_CSV OUT_TOOLS_CSV [LANGUAGECORE_PBO]

Parts table: one row per part of every cfgvehicles class with scope >= 1 that has a `Construction` tree (fence,
watchtower, territory flag, shelter site, and the rebuildable map buildings): requirements, conflicts, the tool masks
for building and dismantling (decoded with the script enum `EConstructionTools`), the material type (`ConstructionMaterialType`),
materials, the materials yielded on build (rubble), decay settings, essential attachments, and the hitpoints and
damage multipliers of the damage zone that carries the part's name.

Tools table: one row per cfgvehicles class with scope >= 2 that defines `build_action_type` or `dismantle_action_type`,
with the decoded masks and which of the build, dismantle and destroy actions its script class (or a script parent)
registers with `AddAction`. A tool needs both: a matching mask and the action. Read-only; nothing is executed.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Values copied from the script enums (4_World/Classes/BaseBuilding/ConstructionConstants.c, ConstructionBase.c).
TOOLS = [(1, "wire"), (2, "nail"), (4, "dig_base"), (8, "mount_log"), (16, "heavy"), (32, "excavation"),
         (64, "woodwork"), (128, "hands"), (256, "bricklaying")]
MATERIAL = {0: "none", 1: "log", 2: "wood", 3: "stairs", 4: "metal", 5: "wire", 6: "brick", 7: "rubble"}
ACTIONS = {"ActionBuildPart": "build", "ActionDismantlePart": "dismantle", "ActionDestroyPart": "destroy"}


def mask_names(v):
    if not isinstance(v, int):
        return ""
    if v == 0:
        return "none"
    return "|".join(n for b, n in TOOLS if v & b)


def kids(d):
    return [(k, v) for k, v in d.items() if not k.startswith("__") and isinstance(v, dict)]


def mats(block, with_slot=True):
    out = []
    for _, m in kids(block or {}):
        s = f"{m.get('type', '')} x{m.get('quantity', '')}"
        if with_slot and m.get("slot_name"):
            s += f" ({m['slot_name']})"
        out.append(s)
    return "; ".join(out)


def lst(v):
    return "|".join(str(x) for x in v) if isinstance(v, list) else ""


def num(v):
    return v if isinstance(v, (int, float)) else ""


def zone_for(zones, part):
    p = part.lower()
    for zname, z in zones:
        names = [str(c).lower() for c in (z.get("componentNames") or [])]
        if zname.lower() == p or p in names:
            return z
    return None


def coef(z, kind):
    return num((((z.get("ArmorType") or {}).get(kind) or {}).get("Health") or {}).get("damage"))


def script_actions(scripts):
    """Map lower-case script class name to (parent, set of registered construction actions)."""
    decl = re.compile(r"^\s*(?:modded\s+)?class\s+(\w+)\s*(?:(?::|extends)\s*(\w+))?", re.M)
    add = re.compile(r"AddAction\(\s*(\w+)\s*\)")
    classes = {}
    for root, _, files in os.walk(scripts):
        for fn in files:
            if not fn.endswith(".c"):
                continue
            with open(os.path.join(root, fn), encoding="utf-8", errors="replace") as f:
                text = f.read()
            text = re.sub(r"//[^\n]*", "", text)
            spans = [(m.start(), m.group(1), m.group(2)) for m in decl.finditer(text)]
            for i, (start, name, parent) in enumerate(spans):
                end = spans[i + 1][0] if i + 1 < len(spans) else len(text)
                acts = {ACTIONS[a] for a in add.findall(text[start:end]) if a in ACTIONS}
                old = classes.get(name.lower(), (None, set()))
                classes[name.lower()] = (parent or old[0], old[1] | acts)
    return classes


def actions_of(classes, name):
    seen, out = set(), set()
    k = name.lower()
    while k and k in classes and k not in seen:
        seen.add(k)
        parent, acts = classes[k]
        out |= acts
        k = parent.lower() if parent else None
    return "|".join(a for a in ("build", "dismantle", "destroy") if a in out)


def main():
    cfgdir, scripts, out_parts, out_tools = sys.argv[1:5]
    pbo = sys.argv[5] if len(sys.argv) > 5 else None
    os.environ["DAYZ_CFG_JSON"] = cfgdir
    sys.path.insert(0, HERE)
    import cfgmodel as m
    S = m.load()
    cv = S["cfgvehicles"]
    tbl = None
    if pbo:
        import stringtable
        tbl = stringtable.load(pbo)

    def eng(s):
        if tbl and isinstance(s, str) and s:
            import stringtable
            return stringtable.english(tbl, s) or s
        return s if isinstance(s, str) else ""

    cache, parts, tools = {}, [], []
    for key in sorted(cv):
        r = m.resolve(cv, key, cache)
        name = cv[key].get("__name__", key)
        scope = r.get("scope", 0)
        con = r.get("Construction")
        if scope >= 1 and isinstance(con, dict):
            zones = kids((r.get("DamageSystem") or {}).get("DamageZones") or {})
            for gname, group in kids(con):
                for pname, p in kids(group):
                    z = zone_for(zones, pname)
                    variants = [lst(v.get("partVariants")) for _, v in kids(p.get("RequiredPartsVariants") or {})]
                    parts.append({
                        "object": name, "scope": scope, "group": gname, "part": pname, "id": num(p.get("id")),
                        "displayName": eng(p.get("name", "")), "is_base": num(p.get("is_base")),
                        "is_gate": num(p.get("is_gate")), "is_utility": num(p.get("is_utility")),
                        "custom_part_type": p.get("custom_part_type", ""),
                        "required_parts": lst(p.get("required_parts")), "required_variants": "; ".join(variants),
                        "conflicted_parts": lst(p.get("conflicted_parts")),
                        "build_tools": mask_names(p.get("build_action_type")),
                        "dismantle_tools": mask_names(p.get("dismantle_action_type")),
                        "material_type": MATERIAL.get(p.get("material_type"), num(p.get("material_type"))),
                        "materials": mats(p.get("Materials")), "yield_on_built": mats(p.get("MaterialsYieldOnBuilt"), False),
                        "can_part_decay": num(p.get("can_part_decay")),
                        "decay_threshold": num(p.get("part_decay_threshold")), "decay_rate": num(p.get("part_decay_rate")),
                        "essential_attachments": lst(p.get("essential_attachments")),
                        "zone_hitpoints": num(((z or {}).get("Health") or {}).get("hitpoints")),
                        "coef_projectile": coef(z, "Projectile") if z else "", "coef_melee": coef(z, "Melee") if z else "",
                        "coef_fraggrenade": coef(z, "FragGrenade") if z else "",
                    })
        if scope >= 2 and ("build_action_type" in r or "dismantle_action_type" in r):
            tools.append({"tool": name, "displayName": eng(r.get("displayName", "")),
                          "build_action_type": num(r.get("build_action_type")),
                          "build_tools": mask_names(r.get("build_action_type")),
                          "dismantle_action_type": num(r.get("dismantle_action_type")),
                          "dismantle_tools": mask_names(r.get("dismantle_action_type"))})
    classes = script_actions(scripts)
    for t in tools:
        # a config class without a script class of its own runs the script class of its nearest config ancestor that has one
        script = next((c for c in m.chain(cv, t["tool"]) if c.lower() in classes), t["tool"])
        t["script_actions"] = actions_of(classes, script)
    for path, rows in ((out_parts, parts), (out_tools, tools)):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(len(parts), "parts in", len({p["object"] for p in parts}), "objects;", len(tools), "tools")


if __name__ == "__main__":
    main()
