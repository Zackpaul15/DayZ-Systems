"""Noise sources: every config class named Noise* (strength and type) in cfgVehicles, cfgWeapons, cfgAmmo and cfgMagazines.

usage: noise_sources.py CFG_JSON_DIR OUT_CSV

One row per (section, class, noise class): strength, type and any other keys, with inheritance resolved with cfgmodel.
The classes are read from the script call sites listed in the notes (footsteps, landing, voice, doors, weapons, ammo hits
and explosions, fireplaces, horns, alarm clocks, smoke grenades and flares). Read-only; nothing is executed.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    cfgdir, out = sys.argv[1:3]
    os.environ["DAYZ_CFG_JSON"] = cfgdir
    sys.path.insert(0, HERE)
    import cfgmodel as m
    S = m.load()
    rows, extra = [], []
    for sec in ("cfgvehicles", "cfgweapons", "cfgammo", "cfgmagazines"):
        cache = {}
        for key in sorted(S[sec]):
            r = m.resolve(S[sec], key, cache)
            for k, v in r.items():
                if isinstance(v, dict) and k.lower().startswith("noise") and "strength" in v:
                    name = S[sec][key].get("__name__", key)
                    row = {"section": sec, "class": name, "noise": k, "scope": r.get("scope", ""),
                           "strength": v.get("strength", ""), "type": v.get("type", "")}
                    for kk, vv in v.items():
                        if kk not in ("strength", "type", "__parent__") and not isinstance(vv, dict):
                            row[kk] = vv
                            if kk not in extra:
                                extra.append(kk)
                    rows.append(row)
    cols = ["section", "class", "noise", "scope", "strength", "type"] + extra
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, restval="")
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "noise entries; extra keys:", extra)


if __name__ == "__main__":
    main()
