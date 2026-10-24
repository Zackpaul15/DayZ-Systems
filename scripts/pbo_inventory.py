"""Inventory of PBO archives: size, prefix, entry count and file types, from headers only (no data is read).

usage: pbo_inventory.py OUT_CSV PBO_DIR [PBO_DIR ...]   (folders are searched recursively)
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbo_config_dump import read_header  # noqa: E402


def main():
    out = sys.argv[1]
    rows = []
    for folder in sys.argv[2:]:
        for dirpath, _dirs, files in os.walk(folder):
            for fn in sorted(files):
                if not fn.lower().endswith(".pbo"):
                    continue
                path = os.path.join(dirpath, fn)
                row = {"folder": os.path.relpath(dirpath, os.path.dirname(folder.rstrip("\\/"))), "pbo": fn,
                       "mb": round(os.path.getsize(path) / 1048576, 1)}
                try:
                    with open(path, "rb") as f:
                        props, entries, _ = read_header(f)
                except Exception as e:
                    row["error"] = f"{type(e).__name__}: {e}"
                    rows.append(row)
                    continue
                row["prefix"] = props.get("prefix", "")
                row["entries"] = len(entries)
                counts = {}
                for name, _packing, _orig, _size in entries:
                    ext = os.path.splitext(name)[1].lower().lstrip(".")
                    counts[ext] = counts.get(ext, 0) + 1
                for ext in ("p3d", "paa", "rvmat", "bin", "wss", "ogg", "c", "layout", "anm", "xob", "emat", "edds", "ptc"):
                    row[ext] = counts.get(ext, 0)
                other = sum(v for k, v in counts.items() if k not in row)
                row["other"] = other
                row["top_ext"] = " ".join(f"{k or '(none)'}:{v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:4])
                rows.append(row)
    fields = ["folder", "pbo", "mb", "prefix", "entries", "p3d", "paa", "rvmat", "bin", "wss", "ogg", "c", "layout", "anm", "xob", "emat", "edds", "ptc", "other", "top_ext", "error"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"archives: {len(rows)}  total MB: {sum(r['mb'] for r in rows):.0f}  errors: {sum(1 for r in rows if 'error' in r)}")


main()
