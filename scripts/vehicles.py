"""Vehicle table (cars, motorbikes, boats) from the merged configs.

usage: vehicles.py CFG_JSON_DIR OUT_CSV [LANGUAGECORE_PBO]

One row per cfgvehicles class with scope >= 2 and simulation car, motorbike or boat: fuel, crew seats, doors,
engine (torque peak, idle and redline rpm), gearbox, drive type, steering angle, aerodynamics, wheel count and
global hitpoints. Read-only; nothing is executed.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def num(v):
    return v if isinstance(v, (int, float)) else ""


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
    cache, rows = {}, []
    for key in sorted(S["cfgvehicles"]):
        r = m.resolve(S["cfgvehicles"], key, cache)
        sim = str(r.get("simulation", "")).lower()
        if r.get("scope", 0) < 2 or sim not in ("car", "motorbike", "boat"):
            continue
        name = S["cfgvehicles"][key].get("__name__", key)
        disp = r.get("displayName", "")
        if tbl and isinstance(disp, str):
            import stringtable
            disp = stringtable.english(tbl, disp) or disp
        sm = r.get("SimulationModule") or {}
        eng, gb = sm.get("Engine") or {}, sm.get("Gearbox") or {}
        tc = eng.get("torqueCurve") or []
        peak = max(((tc[i + 1], tc[i]) for i in range(0, len(tc) - 1, 2)), default=("", ""))
        crew = [k for k, v in (r.get("Crew") or {}).items() if isinstance(v, dict)]
        anim = r.get("AnimationSources") or {}
        doors = [k for k, v in anim.items() if isinstance(v, dict) and k.lower().startswith(("doors", "door"))]
        axles = sm.get("Axles") or {}
        wheels = 0
        for ax in axles.values():
            if isinstance(ax, dict):
                w = ax.get("Wheels") or {}
                wheels += sum(1 for v in w.values() if isinstance(v, dict))
        if not wheels and isinstance(sm.get("Wheels"), dict):
            wheels = sum(1 for v in sm["Wheels"].values() if isinstance(v, dict))
        dz = ((r.get("DamageSystem") or {}).get("DamageZones") or {})
        gh = (((r.get("DamageSystem") or {}).get("GlobalHealth") or {}).get("Health") or {}).get("hitpoints", "")
        steer = sm.get("Steering") or {}
        aero = sm.get("Aerodynamics") or {}
        rows.append({
            "name": name, "displayName": disp, "simulation": sim, "parent": S["cfgvehicles"][key].get("__parent__", ""),
            "fuelCapacity_l": num(r.get("fuelCapacity")), "fuelConsumption": num(r.get("fuelConsumption")),
            "seats": len(crew), "crew_slots": "|".join(crew), "doors": "|".join(doors),
            "drive": sm.get("drive", ""), "gearbox": gb.get("type", ""), "gears": len(gb.get("ratios") or []),
            "reverse_ratio": num(gb.get("reverse")), "torque_peak_nm": peak[0], "torque_peak_rpm": peak[1],
            "rpm_idle": num(eng.get("rpmIdle")), "rpm_redline": num(eng.get("rpmRedline")),
            "max_steer_deg": num(steer.get("maxSteeringAngle")), "drag_coef": num(aero.get("dragCoefficient")),
            "frontal_area": num(aero.get("frontalArea")), "wheels": wheels or "",
            "damage_zones": len(dz), "global_hitpoints": num(gh),
            "attachment_slots": "|".join(r.get("attachments") or []) if isinstance(r.get("attachments"), list) else "",
        })
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "vehicles")


if __name__ == "__main__":
    main()
