"""Compare two CSV tables exactly: schema, row multiset and per-row values.

usage: csv_diff.py OLD_CSV NEW_CSV KEY_COLUMN[,KEY_COLUMN...] [--quiet]

The comparison is complete (CODEX.md CXR-006):
  - the column lists must be identical (columns only in the old or only in the new file are reported and fail);
  - every row takes part, including rows that repeat a key: the two files are compared as multisets of whole rows, so a
    changed, added, removed or duplicated row is always detected;
  - cells are compared after trimming, with numbers compared to six decimals ("1" equals "1.0");
  - every row must have exactly as many cells as its file's header; a file with a longer or shorter row is malformed and
    the comparison fails, naming the file and line (CXR-009);
  - the key columns (one or several) only make the report readable: they pair a changed row with its old version when the
    key is unique in both files, and the report says so when it is not.
Exit code 0 only when the tables are identical, 1 otherwise. Read-only.
"""
import collections
import csv
import os
import sys


def load(p):
    with open(p, newline="", encoding="utf-8-sig") as f:
        r = csv.reader(f)
        header = next(r, [])
        return header, [row for row in r]


def row_width_problems(p):
    """Rows whose cell count differs from the header: a list of (1-based line number, cells, expected) (CODEX.md CXR-009)."""
    with open(p, newline="", encoding="utf-8-sig") as f:
        r = csv.reader(f)
        header = next(r, [])
        return [(i, len(row), len(header)) for i, row in enumerate(r, start=2) if len(row) != len(header)]


def norm(x):
    x = str(x).strip()
    try:
        return repr(round(float(x), 6)) if x not in ("", "nan", "inf", "-inf") else x
    except ValueError:
        return x


def rows_as_tuples(header, rows):
    return [tuple(norm(row[i]) if i < len(row) else "" for i in range(len(header))) for row in rows]


def compare(old_path, new_path, key, quiet=False):
    keys = [k.strip() for k in (key.split(",") if isinstance(key, str) else key)]
    oh, orows = load(old_path)
    nh, nrows = load(new_path)
    name = os.path.basename(old_path)
    problems = []
    only_old_cols = [c for c in oh if c not in nh]
    only_new_cols = [c for c in nh if c not in oh]
    if only_old_cols or only_new_cols:
        problems.append(f"columns only in old {only_old_cols}, only in new {only_new_cols}")
    if oh != nh and not (only_old_cols or only_new_cols):
        problems.append("same columns in a different order")
    for label, path in (("old", old_path), ("new", new_path)):
        bad = row_width_problems(path)
        if bad:
            shown = ", ".join(f"line {i} has {n} cells" for i, n, _ in bad[:3])
            problems.append(f"{label} file {os.path.basename(path)}: {len(bad)} rows do not have {bad[0][2]} cells ({shown})")
    if any("do not have" in p for p in problems):
        print(f"{name}: malformed rows -> DIFFERENT")
        for p in problems:
            print("   " + p)
        return False
    if not orows or not nrows:
        print(f"{name}: empty table (old {len(orows)}, new {len(nrows)}) -> DIFFERENT")
        return False
    cols = [c for c in oh if c in nh]  # compare the shared columns in the old order
    oi, ni = [oh.index(c) for c in cols], [nh.index(c) for c in cols]
    ot = [tuple(norm(r[i]) if i < len(r) else "" for i in oi) for r in orows]
    nt = [tuple(norm(r[i]) if i < len(r) else "" for i in ni) for r in nrows]
    co, cn = collections.Counter(ot), collections.Counter(nt)
    only_old, only_new = co - cn, cn - co
    n_old, n_new = sum(only_old.values()), sum(only_new.values())
    if len(orows) != len(nrows):
        problems.append(f"row counts differ (old {len(orows)}, new {len(nrows)})")
    if n_old or n_new:
        problems.append(f"{n_old} old rows have no identical new row, {n_new} new rows have no identical old row")
    missing_keys = [k for k in keys if k not in cols]
    if missing_keys:
        problems.append(f"key columns {missing_keys} are not in both files")
    ok = not problems
    print(f"{name}: rows old {len(orows)} new {len(nrows)}; columns {len(oh)}/{len(nh)} -> {'IDENTICAL' if ok else 'DIFFERENT'}")
    if ok or quiet:
        return ok
    for p in problems:
        print("   " + p)
    if not missing_keys and (n_old or n_new):
        kidx = [cols.index(k) for k in keys]
        okey = collections.defaultdict(list)
        nkey = collections.defaultdict(list)
        for t in only_old.elements():
            okey[tuple(t[i] for i in kidx)].append(t)
        for t in only_new.elements():
            nkey[tuple(t[i] for i in kidx)].append(t)
        dup_old = sum(1 for v in collections.Counter(tuple(t[i] for i in kidx) for t in ot).values() if v > 1)
        dup_new = sum(1 for v in collections.Counter(tuple(t[i] for i in kidx) for t in nt).values() if v > 1)
        print(f"   key {keys}: {dup_old} repeated keys in old, {dup_new} in new (rows with repeated keys are compared whole)")
        shown = 0
        for k in sorted(set(okey) | set(nkey)):
            if shown >= 4:
                break
            a, b = okey.get(k, []), nkey.get(k, [])
            if len(a) == 1 and len(b) == 1:
                diffs = [(cols[i], a[0][i], b[0][i]) for i in range(len(cols)) if a[0][i] != b[0][i]]
                print(f"   {k}: {diffs[:3]}")
            else:
                print(f"   {k}: {len(a)} old and {len(b)} new differing rows")
            shown += 1
    return False


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sys.exit(0 if compare(args[0], args[1], args[2], "--quiet" in sys.argv) else 1)
