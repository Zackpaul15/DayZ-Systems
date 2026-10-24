"""Fishing and trapping config values per item (the `Fishing` and `Trapping` bodies in cfgvehicles).

usage: catching.py CFG_JSON_DIR OUT_CSV [LANGUAGECORE_PBO]

One row per item class (scope >= 1) that carries a Fishing or Trapping body, with every key of that body as a column
prefixed by the body name. Read-only; nothing is executed.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


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
    cache, rows, keys = {}, [], []
    for key in sorted(S["cfgvehicles"]):
        r = m.resolve(S["cfgvehicles"], key, cache)
        if r.get("scope", 0) < 1:
            continue
        row = {}
        for body in ("Fishing", "Trapping"):
            b = r.get(body)
            if isinstance(b, dict):
                for k, v in b.items():
                    if k != "__parent__":
                        row[f"{body}.{k}"] = "|".join(str(x) for x in v) if isinstance(v, list) else v
        if not row:
            continue
        disp = r.get("displayName", "")
        if tbl and isinstance(disp, str):
            import stringtable
            disp = stringtable.english(tbl, disp) or disp
        row = {"name": S["cfgvehicles"][key].get("__name__", key), "displayName": disp, **row}
        for k in row:
            if k not in keys:
                keys.append(k)
        rows.append(row)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, restval="")
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "items with Fishing or Trapping bodies; columns:", [k for k in keys if "." in k])


if __name__ == "__main__":
    main()
