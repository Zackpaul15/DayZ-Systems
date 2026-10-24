"""AI perception table: the TargetSystem (vision), NoiseSystemParams (hearing) and AlertSystem bodies of every CfgAIBehaviours class.

usage: ai_perception.py CFG_JSON_DIR OUT_CSV

One row per behaviour (36); columns are the merged values of every key found in the bodies whose name contains
TargetSystem, NoiseSystemParams or AlertSystem anywhere in the behaviour tree (inheritance resolved with cfgmodel).
Read-only; nothing is executed.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WANT = ("TargetSystem", "NoiseSystemParams", "AlertSystem")


def walk(d, path=""):
    for k, v in d.items():
        if k.startswith("__"):
            continue
        if isinstance(v, dict):
            yield from walk(v, path + "/" + k)
        else:
            yield path + "/" + k, v


def main():
    cfgdir, out = sys.argv[1:3]
    os.environ["DAYZ_CFG_JSON"] = cfgdir
    sys.path.insert(0, HERE)
    import cfgmodel as m
    S = m.load()
    ab = S["cfgaibehaviours"]
    cache, rows, cols = {}, [], []
    for key in sorted(ab):
        r = m.resolve(ab, key, cache)
        row = {"behaviour": ab[key].get("__name__", key), "parent": ab[key].get("__parent__", "")}
        for p, v in walk(r):
            top = p.split("/")[-2] if p.count("/") >= 2 else ""
            if any(w in p for w in WANT):
                col = "/".join(p.strip("/").split("/")[-2:]) if p.count("/") > 2 else p.strip("/")
                row[col] = "|".join(str(x) for x in v) if isinstance(v, list) else v
        for c in row:
            if c not in cols:
                cols.append(c)
        rows.append(row)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, restval="")
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "behaviours;", len(cols), "columns")


if __name__ == "__main__":
    main()
