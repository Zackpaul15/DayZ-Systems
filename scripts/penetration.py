"""Bullet material table from the rapified .bisurf files in the data/penetration folder of dz.pbo.

usage: penetration.py DZ_UNPACKED_DIR OUT_CSV

DZ_UNPACKED_DIR is dz.pbo extracted with pbo_unpack.py (outside the project). One row per material: density,
thickness, bullet penetrability (with and without thickness), deflection, transparency, friction, restitution,
impact effect, hit sound. Read-only; nothing is executed.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rap_reader  # noqa: E402

FIELDS = ["Density", "Thickness", "bulletPenetrability", "bulletPenetrabilityWithThickness", "deflection",
          "transparency", "rough", "dust", "audibility", "friction", "restitution", "isLiquid", "impact",
          "soundHit", "soundEnviron"]


def main():
    root, out = sys.argv[1:3]
    d = os.path.join(root, "data", "penetration")
    rows = []
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(".bisurf"):
            continue
        cfg, _enums = rap_reader.parse(open(os.path.join(d, fn), "rb").read())
        row = {"material": fn[:-7]}
        for k in FIELDS:
            v = cfg.get(k, "")
            row[k] = round(v, 4) if isinstance(v, float) else v
        rows.append(row)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["material"] + FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "materials")


if __name__ == "__main__":
    main()
