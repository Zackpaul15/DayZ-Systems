"""Central Economy tables from the server mission templates (the worlds_*_ce folders from bootstrap.py).

usage:
  ce_types.py types   CE_MAP_DIR OUT_CSV      one row per loot type from db/types.xml (same columns as loot_types_chernarus.csv)
  ce_types.py compare CE_ROOT_DIR OUT_CSV     one row per map: counts and settings side by side

CE_ROOT_DIR is the 'ce' folder written by bootstrap.py (it holds worlds_<map>_ce subfolders).
Read-only; nothing is executed.
"""
import csv
import json
import os
import sys
import xml.etree.ElementTree as ET

FIELDS = ["name", "nominal", "lifetime", "restock", "min", "quantmin", "quantmax", "cost", "category", "usage", "value",
          "count_in_cargo", "count_in_hoarder", "count_in_map", "count_in_player", "crafted", "deloot"]


def type_rows(map_dir):
    root = ET.parse(os.path.join(map_dir, "db", "types.xml")).getroot()
    rows = []
    for t in root.findall("type"):
        r = {"name": t.get("name")}
        for k in ("nominal", "lifetime", "restock", "min", "quantmin", "quantmax", "cost"):
            e = t.find(k)
            r[k] = e.text.strip() if e is not None and e.text else ""
        fl = t.find("flags")
        for k in ("count_in_cargo", "count_in_hoarder", "count_in_map", "count_in_player", "crafted", "deloot"):
            r[k] = fl.get(k, "") if fl is not None else ""
        c = t.find("category")
        r["category"] = c.get("name", "") if c is not None else ""
        r["usage"] = "|".join(u.get("name", "") for u in t.findall("usage"))
        r["value"] = "|".join(v.get("name", "") for v in t.findall("value"))
        rows.append(r)
    return rows


def map_summary(map_dir):
    rows = type_rows(map_dir)
    nom = [int(r["nominal"]) for r in rows if r["nominal"].lstrip("-").isdigit()]
    s = {"types": len(rows), "nominal_sum": sum(nom), "types_nominal_0": sum(1 for n in nom if n == 0)}
    cats = {}
    tiers = {}
    for r in rows:
        cats[r["category"] or "(none)"] = cats.get(r["category"] or "(none)", 0) + 1
        for v in r["value"].split("|"):
            if v:
                tiers[v] = tiers.get(v, 0) + 1
    s["categories"] = "; ".join(f"{k} {v}" for k, v in sorted(cats.items(), key=lambda kv: -kv[1]))
    s["tiers"] = "; ".join(f"{k} {v}" for k, v in sorted(tiers.items()))
    life = {}
    for r in rows:
        life[r["lifetime"]] = life.get(r["lifetime"], 0) + 1
    s["top_lifetimes"] = "; ".join(f"{k}s x{v}" for k, v in sorted(life.items(), key=lambda kv: -kv[1])[:3])
    ev = ET.parse(os.path.join(map_dir, "db", "events.xml")).getroot().findall("event")
    s["events"] = len(ev)
    s["events_inactive"] = sum(1 for e in ev if (e.findtext("active") or "1").strip() == "0")
    g = ET.parse(os.path.join(map_dir, "db", "globals.xml")).getroot().findall("var")
    gv = {v.get("name"): v.get("value") for v in g}
    for k in ("AnimalMaxCount", "ZombieMaxCount", "CleanupLifetimeDeadPlayer", "LootDamageMax", "InitialSpawn"):
        s["globals." + k] = gv.get(k, "")
    sp = os.path.join(map_dir, "cfgplayerspawnpoints.xml")
    if os.path.exists(sp):
        root = ET.parse(sp).getroot()
        for sec in ("fresh", "hop", "travel"):
            e = root.find(sec)
            if e is not None:
                s[f"spawn_{sec}_groups"] = len(e.findall(".//group"))
                s[f"spawn_{sec}_positions"] = len(e.findall(".//pos"))
    ea = os.path.join(map_dir, "cfgeffectarea.json")
    if os.path.exists(ea):
        try:
            s["contaminated_areas"] = len(json.load(open(ea, encoding="utf-8")).get("Areas", []))
        except Exception:
            s["contaminated_areas"] = ""
    gp = os.path.join(map_dir, "cfggameplay.json")
    if os.path.exists(gp):
        d = json.load(open(gp, encoding="utf-8"))
        s["gameplay_version"] = d.get("version", "")
        s["bunker_broadcast"] = d.get("GeneralData", {}).get("bunkerBroadcastEnabled", d.get("WorldsData", {}).get("bunkerBroadcastEnabled", ""))
        s["restricted_area_files"] = ",".join(d.get("WorldsData", {}).get("playerRestrictedAreaFiles", []) or [])
    return s


def main():
    cmd = sys.argv[1]
    if cmd == "types":
        rows = type_rows(sys.argv[2])
        with open(sys.argv[3], "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        print(len(rows), "types")
    elif cmd == "compare":
        root = sys.argv[2]
        rows = []
        for d in sorted(os.listdir(root)):
            if d.startswith("worlds_") and d.endswith("_ce"):
                s = map_summary(os.path.join(root, d))
                s = {"map": d[len("worlds_"):-len("_ce")], **s}
                rows.append(s)
        keys = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with open(sys.argv[3], "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
        print(len(rows), "maps")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
