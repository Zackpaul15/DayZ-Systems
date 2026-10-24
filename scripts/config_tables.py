"""Rebuild the config-derived tables: ammo, ammo_physics, explosives, body_zones, clothing and script_decls.

usage: config_tables.py CFG_JSON_DIR SCRIPTS_SRC_DIR OUT_DIR [LANGUAGECORE_PBO]

CFG_JSON_DIR and SCRIPTS_SRC_DIR come from bootstrap.py. Writes OUT_DIR\\<table>.csv for each table. Column meanings are
documented in data\\PROVENANCE.md. Read-only on the game files; nothing is executed.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

AMMO_PHYS = ["simulation", "SimulationScriptClass", "initSpeed", "typicalSpeed", "maxSpeed", "airFriction",
             "airFrictionChangeOnActivation", "coefGravity", "timeToLive", "caliber", "deflecting", "deflectingMultiplier",
             "deflectionSlowDown", "dispersion", "projectilesCount", "simulationStep", "slowdownThreshold", "maxLeadSpeed",
             "initTime", "explosionTime", "fuseDistance", "explosive", "indirectHit", "indirectHitRange",
             "indirectHitRangeMultiplier", "explosionType", "tracerScale", "tracerStartTime", "tracerEndTime", "nvgOnly"]


def write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, restval="")
        w.writeheader()
        w.writerows(rows)


def flag(v):
    """True for a non-zero numeric config value."""
    try:
        return float(v) != 0
    except (TypeError, ValueError):
        return False


def num(v):
    return v if isinstance(v, (int, float)) else ""


def ammo_tables(m, S, out):
    cache, rows, phys, expl = {}, [], [], []
    for key in sorted(S["cfgammo"]):
        r = m.resolve(S["cfgammo"], key, cache)
        name = S["cfgammo"][key].get("__name__", key)
        row = {"name": key}
        for c in AMMO_PHYS:
            v = r.get(c, "")
            row[c] = v if not isinstance(v, (dict, list)) else ""
        phys.append(row)
        if flag(row["explosive"]) or flag(row["indirectHit"]):
            expl.append({"name": name, "simulation": r.get("simulation", ""), "explosive": r.get("explosive", ""),
                         "indirectHit": r.get("indirectHit", ""), "indirectHitRange": r.get("indirectHitRange", ""),
                         "indirectHitRangeMultiplier": r.get("indirectHitRangeMultiplier", ""),
                         "explosionType": r.get("explosionType", ""), "hit": r.get("hit", ""),
                         "initTime": r.get("initTime", ""), "explosionTime": r.get("explosionTime", ""),
                         "fuseDistance": r.get("fuseDistance", "")})
        da = r.get("DamageApplied")
        if isinstance(da, dict):
            def g(t):
                b = da.get(t)
                return b.get("damage", "") if isinstance(b, dict) else ""
            rows.append({"name": name, "type": da.get("type", ""), "health": g("Health"), "blood": g("Blood"),
                         "shock": g("Shock"), "bleedThr": da.get("bleedThreshold", ""), "v0": r.get("initSpeed", ""),
                         "typ": r.get("typicalSpeed", ""), "caliber": r.get("caliber", ""),
                         "friction": r.get("airFriction", ""), "uncon": r.get("unconRefillModifier", ""),
                         "pellets": r.get("projectilesCount", ""), "deflect": r.get("deflecting", "")})
    write(os.path.join(out, "ammo.csv"), ["name", "type", "health", "blood", "shock", "bleedThr", "v0", "typ", "caliber",
                                          "friction", "uncon", "pellets", "deflect"], rows)
    write(os.path.join(out, "ammo_physics.csv"), ["name"] + AMMO_PHYS, phys)
    write(os.path.join(out, "explosives.csv"), ["name", "simulation", "explosive", "indirectHit", "indirectHitRange",
                                               "indirectHitRangeMultiplier", "explosionType", "hit", "initTime",
                                               "explosionTime", "fuseDistance"], expl)
    return len(rows), len(phys), len(expl)


def zone_tables(m, S, out):
    cache, rows = {}, []
    for cls in ("survivorbase", "zombiebase"):
        r = m.resolve(S["cfgvehicles"], cls, cache)
        zones = ((r.get("DamageSystem") or {}).get("DamageZones") or {})
        for z, b in zones.items():
            if not isinstance(b, dict):
                continue
            hp = (b.get("Health") or {}).get("hitpoints", "") if isinstance(b.get("Health"), dict) else ""

            def j(k):
                return "|".join(str(x) for x in b.get(k, [])) if isinstance(b.get(k), list) else ""
            rows.append({"class": cls, "zone": z, "hitpoints": hp, "fatalInjuryCoef": b.get("fatalInjuryCoef", ""),
                         "componentNames": j("componentNames"), "transferToZonesNames": j("transferToZonesNames"),
                         "transferToZonesCoefs": j("transferToZonesCoefs"), "inventorySlots": j("inventorySlots")})
    write(os.path.join(out, "body_zones.csv"), ["class", "zone", "hitpoints", "fatalInjuryCoef", "componentNames",
                                                "transferToZonesNames", "transferToZonesCoefs", "inventorySlots"], rows)
    return len(rows)


def clothing_table(m, S, out, tbl):
    cache, rows = {}, []
    for key in sorted(S["cfgvehicles"]):
        r = m.resolve(S["cfgvehicles"], key, cache)
        if r.get("scope", 0) < 2 or "clothing_base" not in [c.lower() for c in m.chain(S["cfgvehicles"], key)]:
            continue
        disp = r.get("displayName", "")
        if tbl and isinstance(disp, str):
            import stringtable
            disp = stringtable.english(tbl, disp) or disp
        slot = r.get("inventorySlot")
        slot = slot[0] if isinstance(slot, list) and slot else slot or ""
        prot = r.get("Protection") if isinstance(r.get("Protection"), dict) else {}
        ds = r.get("DamageSystem") or {}
        ga = ds.get("GlobalArmor") or {}
        hp = ((ds.get("GlobalHealth") or {}).get("Health") or {}).get("hitpoints", "")

        def dm(t, k):
            b = ga.get(t)
            b = b.get(k) if isinstance(b, dict) else None
            return b.get("damage", "") if isinstance(b, dict) else ""
        rows.append({"name": S["cfgvehicles"][key].get("__name__", key), "displayName": disp, "slot": slot,
                     "weight": num(r.get("weight")), "heat": num(r.get("heatIsolation")),
                     "absorb": num(r.get("absorbency")), "wetmax": num(r.get("varWetMax")),
                     "vis": num(r.get("visibilityModifier")), "bio": num(prot.get("biological")),
                     "chem": num(prot.get("chemical")), "hp": hp,
                     "p_health": dm("Projectile", "Health"), "p_shock": dm("Projectile", "Shock"),
                     "m_health": dm("Melee", "Health"), "m_shock": dm("Melee", "Shock"),
                     "size": str(r.get("itemSize", ""))})
    write(os.path.join(out, "clothing.csv"), ["name", "displayName", "slot", "weight", "heat", "absorb", "wetmax", "vis",
                                              "bio", "chem", "hp", "p_health", "p_shock", "m_health", "m_shock", "size"], rows)
    return len(rows)


DECL = re.compile(r"^\s*(?:(modded)\s+)?(?:(?:sealed|abstract|static|private|protected)\s+)*(class|enum|typedef)\s+(\w+)\s*(?:(?:extends|:)\s*(\w+))?")


def decl_table(scripts, out):
    rows = []
    for d, _s, files in os.walk(scripts):
        for f in sorted(files):
            if not f.endswith(".c"):
                continue
            rel = os.path.relpath(os.path.join(d, f), scripts)
            layer = rel.split(os.sep)[0] if os.sep in rel else rel
            for line in open(os.path.join(d, f), encoding="utf-8", errors="replace"):
                m = DECL.match(line)
                if m:
                    rows.append({"Kind": m.group(2), "Modded": "True" if m.group(1) else "False", "Name": m.group(3),
                                 "Base": m.group(4) or "", "Layer": layer, "File": rel})
    write(os.path.join(out, "script_decls.csv"), ["Kind", "Modded", "Name", "Base", "Layer", "File"], rows)
    return len(rows)


def melee_table(m, S, out, tbl):
    """Spawnable cfgVehicles items whose Default melee mode is not the fist, with the damage of the three modes."""
    cache, ac, rows = {}, {}, []

    def dmg(ammo):
        if ammo not in S["cfgammo"] and str(ammo).lower() not in S["cfgammo"]:
            return "", "", ""
        r = m.resolve(S["cfgammo"], ammo, ac)
        da = r.get("DamageApplied")
        if not isinstance(da, dict):
            return "", "", ""
        g = lambda t: da[t].get("damage", "") if isinstance(da.get(t), dict) else ""
        return g("Health"), g("Blood"), g("Shock")
    for key in sorted(S["cfgvehicles"]):
        r = m.resolve(S["cfgvehicles"], key, cache)
        mm = r.get("MeleeModes")
        if r.get("scope", 0) != 2 or not isinstance(mm, dict):
            continue
        d, h, sp = (mm.get(k) if isinstance(mm.get(k), dict) else {} for k in ("Default", "Heavy", "Sprint"))
        if d.get("ammo") in (None, "MeleeFist"):
            continue
        disp = r.get("displayName", "")
        if tbl and isinstance(disp, str):
            import stringtable
            disp = stringtable.english(tbl, disp) or disp
        lh, lb, ls = dmg(d.get("ammo", ""))
        hh, hb, hs = dmg(h.get("ammo", ""))
        rows.append({"name": key, "displayName": disp, "light_ammo": d.get("ammo", ""), "light_range": d.get("range", ""),
                     "light_health": lh, "light_blood": lb, "light_shock": ls, "heavy_ammo": h.get("ammo", ""),
                     "heavy_range": h.get("range", ""), "heavy_health": hh, "heavy_blood": hb, "heavy_shock": hs,
                     "sprint_ammo": sp.get("ammo", ""), "sprint_range": sp.get("range", ""), "weight": num(r.get("weight"))})
    write(os.path.join(out, "melee.csv"), ["name", "displayName", "light_ammo", "light_range", "light_health", "light_blood",
                                           "light_shock", "heavy_ammo", "heavy_range", "heavy_health", "heavy_blood",
                                           "heavy_shock", "sprint_ammo", "sprint_range", "weight"], rows)
    return len(rows)


def recoil_table(scripts, out):
    """One row per recoil profile class under 4_World/Classes/RecoilBase/Recoils."""
    d = os.path.join(scripts, "4_World", "Classes", "RecoilBase", "Recoils")
    rows = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".c"):
            continue
        src = open(os.path.join(d, fn), encoding="utf-8", errors="replace").read()
        cm = re.search(r"class\s+(\w+)\s*:\s*RecoilBase", src)
        if not cm:
            continue

        def val(name):
            v = re.search(name + r"\s*=\s*(-?[0-9.]+)", src)
            return v.group(1) if v else ""
        ys = [float(x) for x in re.findall(r"point_\d\[1\]\s*=\s*(-?[0-9.]+)", src)]
        rows.append({"Name": cm.group(1), "MouseDist": val("m_MouseOffsetDistance"), "MouseT": val("m_MouseOffsetRelativeTime"),
                     "HandsT": val("m_HandsOffsetRelativeTime"), "AngMin": val("m_MouseOffsetRangeMin"),
                     "AngMax": val("m_MouseOffsetRangeMax"), "CamDist": val("m_CamOffsetDistance"),
                     "HandPeak": max(ys) if ys else ""})
    write(os.path.join(out, "recoil.csv"), ["Name", "MouseDist", "MouseT", "HandsT", "AngMin", "AngMax", "CamDist", "HandPeak"], rows)
    return len(rows)


def food_table(m, S, out, tbl):
    """Spawnable cfgVehicles items derived from Edible_Base, with the Nutrition body of the item."""
    cache, rows = {}, []
    for key in sorted(S["cfgvehicles"]):
        r = m.resolve(S["cfgvehicles"], key, cache)
        if r.get("scope", 0) != 2 or "edible_base" not in [c.lower() for c in m.chain(S["cfgvehicles"], key)]:
            continue
        disp = r.get("displayName", "")
        if tbl and isinstance(disp, str):
            import stringtable
            disp = stringtable.english(tbl, disp) or disp
        n = r.get("Nutrition") if isinstance(r.get("Nutrition"), dict) else {}
        rows.append({"name": S["cfgvehicles"][key].get("__name__", key), "displayName": disp,
                     "weight": r.get("weight", "") if not isinstance(r.get("weight"), (dict, list)) else "",
                     "size": str(r.get("itemSize", "")), "full": n.get("fullnessIndex", ""), "energy": n.get("energy", ""),
                     "water": n.get("water", ""), "nut": n.get("nutritionalIndex", ""), "tox": n.get("toxicity", ""),
                     "dig": n.get("digestibility", ""), "agents": n.get("agents", ""), "qmax": num(r.get("varQuantityMax"))})
    write(os.path.join(out, "food.csv"), ["name", "displayName", "weight", "size", "full", "energy", "water", "nut", "tox",
                                          "dig", "agents", "qmax"], rows)
    return len(rows)


FAMILY_RULES = [("archery_base", "bow/crossbow"), ("launcher_base", "launcher"), ("nonlethalpistol", "nonlethal"),
                ("boltactionrifle_base", "bolt-action"), ("pistol_base", "pistol"), ("shotgun_base", "shotgun"),
                ("rifle_base", "rifle")]


def weapons_table(m, S, out, tbl):
    """Spawnable cfgWeapons items (scope 2): family from the base-class chain, mode list, rate of fire, first chamberable ammo."""
    cache, ac, rows = {}, {}, []
    for key in sorted(S["cfgweapons"]):
        r = m.resolve(S["cfgweapons"], key, cache)
        if r.get("scope", 0) != 2:
            continue
        chain = [c.lower() for c in m.chain(S["cfgweapons"], key)]
        fam = next((f for c, f in FAMILY_RULES if c in chain), "")
        modes = r.get("modes") if isinstance(r.get("modes"), list) else []
        rpm = ""
        for mode in modes:
            body = r.get(mode)
            if isinstance(body, dict) and isinstance(body.get("reloadTime"), (int, float)) and body["reloadTime"] > 0:
                rpm = max(rpm or 0, round(60.0 / body["reloadTime"]))
        cf = r.get("chamberableFrom") if isinstance(r.get("chamberableFrom"), list) else []
        chamber = cf[0] if cf else ""
        mags = r.get("magazines") if isinstance(r.get("magazines"), list) else []
        ammo = hp = blood = shock = v0 = ""
        mk = str(chamber).lower()
        if mk in S["cfgmagazines"]:
            ammo = m.resolve(S["cfgmagazines"], chamber, ac).get("ammo", "")
        if ammo and str(ammo).lower() in S["cfgammo"]:
            a = m.resolve(S["cfgammo"], ammo, ac)
            da = a.get("DamageApplied") if isinstance(a.get("DamageApplied"), dict) else {}
            g = lambda t: da[t].get("damage", "") if isinstance(da.get(t), dict) else ""
            hp, blood, shock, v0 = g("Health"), g("Blood"), g("Shock"), a.get("initSpeed", "")
        disp = r.get("displayName", "")
        if tbl and isinstance(disp, str):
            import stringtable
            disp = stringtable.english(tbl, disp) or disp
        rows.append({"name": S["cfgweapons"][key].get("__name__", key), "displayName": disp, "family": fam,
                     "weight": num(r.get("weight")), "size": str(r.get("itemSize", "")), "mags": len(mags),
                     "chamber": chamber, "modes": "/".join(modes), "rpm": rpm, "barrelArmor": num(r.get("barrelArmor")),
                     "initSpeedMult": num(r.get("initSpeedMultiplier")), "dispersion": num(r.get("dispersion")),
                     "ammo": ammo, "hp": hp, "blood": blood, "shock": shock, "initSpeed": v0})
    write(os.path.join(out, "weapons.csv"), ["name", "displayName", "family", "weight", "size", "mags", "chamber", "modes", "rpm",
                                             "barrelArmor", "initSpeedMult", "dispersion", "ammo", "hp", "blood", "shock",
                                             "initSpeed"], rows)
    return len(rows)


def main():
    cfgdir, scripts, out = sys.argv[1:4]
    pbo = sys.argv[4] if len(sys.argv) > 4 else None
    os.environ["DAYZ_CFG_JSON"] = cfgdir
    import cfgmodel as m
    S = m.load()
    tbl = None
    if pbo:
        import stringtable
        tbl = stringtable.load(pbo)
    os.makedirs(out, exist_ok=True)
    print("ammo/physics/explosives rows:", ammo_tables(m, S, out))
    print("body_zones rows:", zone_tables(m, S, out))
    print("clothing rows:", clothing_table(m, S, out, tbl))
    print("script_decls rows:", decl_table(scripts, out))
    print("melee rows:", melee_table(m, S, out, tbl))
    print("recoil rows:", recoil_table(scripts, out))
    print("food rows:", food_table(m, S, out, tbl))
    print("weapons rows:", weapons_table(m, S, out, tbl))


if __name__ == "__main__":
    main()
