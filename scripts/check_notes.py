"""Consistency check for the project folder (notes, tables, scripts, README).

usage: check_notes.py [--strict]

Errors (exit code 1):
  - a numbered section in notes\\*.md that is missing from notes\\README.md, or mapped to a different file, or mapped but absent
  - a "see N.N" / "section N.N" reference that points at no section
  - a data\\*.csv or scripts\\*.py file that README.md does not name, or a CSV that data\\PROVENANCE.md does not name
  - a CSV with an empty body or rows with a different number of columns than the header
  - control characters in text files
  - game content that should not be in the project: *.pbo, *.bin, *.p3d, *.c script sources, raw JSON dumps, any file over 5 MB
  - a 32-character hex token in the notes (the embedded signature of the report URL must not be copied)
Warnings (printed; errors with --strict): phrases that usually mean stale text ("not decoded", "not yet traced", "REA"),
tag counts per file, and duplicate section headings.
Read-only. Run from anywhere; paths are relative to the project folder.
"""
import csv
import glob
import os
import re
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES = os.path.join(PROJECT, "notes")
EXCLUDE_NOTES = {"README.md", "plan-history.md"}
STALE = ["not decoded", "not yet traced", "did not read the function", "leaning yes", "re-analyses", "REA CLI"]
HEAD = re.compile(r"^#{2,4} (\d+(?:\.\d+)?[a-z]?)\b[ .:]")
MAPROW = re.compile(r"^\| (\d+(?:\.\d+)?[a-z]?) \|[^|]*\| \[([\w.-]+)\]", re.M)
REF = re.compile(r"\b(?:see|See|in|section|sections|and)\s+(\d+\.\d+[a-z]?)\b")
BAD_EXT = (".pbo", ".bin", ".p3d", ".c", ".paa", ".rvmat", ".xob", ".exe", ".dll")


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def main():
    strict = "--strict" in sys.argv
    errors, warns = [], []

    # 1. section map
    heads = {}
    for p in sorted(glob.glob(os.path.join(NOTES, "*.md"))):
        name = os.path.basename(p)
        if name in EXCLUDE_NOTES:
            continue
        for i, line in enumerate(read(p).splitlines(), 1):
            m = HEAD.match(line)
            if m:
                heads.setdefault(m.group(1), []).append((name, i))
    mapped = dict(MAPROW.findall(read(os.path.join(NOTES, "README.md"))))
    for sec, where in sorted(heads.items()):
        if sec not in mapped:
            errors.append(f"section {sec} ({where[0][0]}:{where[0][1]}) is not in notes/README.md")
        elif mapped[sec] != where[0][0] and mapped[sec] != where[0][0][:-3]:
            errors.append(f"section {sec} is in {where[0][0]} but the map says {mapped[sec]}")
        if len(where) > 1:
            warns.append(f"section {sec} has {len(where)} headings: {where}")
    for sec in mapped:
        if sec not in heads:
            errors.append(f"notes/README.md maps section {sec} but no heading exists")

    # 2. cross-references
    for p in sorted(glob.glob(os.path.join(NOTES, "*.md"))):
        name = os.path.basename(p)
        if name in EXCLUDE_NOTES:
            continue
        for i, line in enumerate(read(p).splitlines(), 1):
            for ref in REF.findall(line):
                if ref not in heads and not re.search(r"\b" + re.escape(ref) + r"\s*(?:m|g|kg|%|x|s)\b", line):
                    # numbers such as "in 3.5 m" are values, not references
                    if re.search(r"(?:see|See|section|sections)\s+" + re.escape(ref), line):
                        errors.append(f"{name}:{i}: reference to {ref} resolves to no section")

    # 3. README and PROVENANCE coverage
    readme = read(os.path.join(PROJECT, "README.md"))
    prov = read(os.path.join(PROJECT, "data", "PROVENANCE.md"))
    tables = sorted(glob.glob(os.path.join(PROJECT, "data", "*.csv")))
    for p in tables:
        stem = os.path.basename(p)[:-4]
        if stem not in readme:
            errors.append(f"data/{stem}.csv is not named in README.md")
        if stem not in prov:
            errors.append(f"data/{stem}.csv is not named in data/PROVENANCE.md")
    for p in sorted(glob.glob(os.path.join(PROJECT, "scripts", "*.py"))):
        if os.path.basename(p)[:-3] not in readme:
            errors.append(f"scripts/{os.path.basename(p)} is not named in README.md")

    # 4. table sanity
    for p in tables:
        with open(p, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        if len(rows) < 2:
            errors.append(f"{os.path.basename(p)} has no data rows")
            continue
        bad = [i for i, r in enumerate(rows, 1) if len(r) != len(rows[0])]
        if bad:
            errors.append(f"{os.path.basename(p)}: {len(bad)} rows with a different column count (first: line {bad[0]})")

    # 4b. count invariants (CODEX.md CXR-004 and CXR-005)
    def rows_of(name):
        with open(os.path.join(PROJECT, "data", name), newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    try:
        bad = [r["method"] for r in rows_of("native_api.csv") if r["name_in_script_class"] == "yes" and not r["script_class"]]
        if bad:
            errors.append(f"native_api.csv: {len(bad)} rows count as matched without an accepted class (first: {bad[0]})")
        # independent recomputation of the recipe counts: distinct live recipe classes naming the item in either slot
        live = [r for r in rows_of("recipes.csv") if r["registered"] == "yes"]
        naming = {}
        for r in live:
            for col in ("ingredient1", "ingredient2"):
                for c in r[col].split("|"):
                    if c.strip():
                        naming.setdefault(c.strip().lower(), set()).add(r["class"])
        wrong = [(r["name"], r["recipes_as_ingredient_direct"], len(naming.get(r["name"].lower(), ())))
                 for r in rows_of("items_master.csv") if int(r["recipes_as_ingredient_direct"]) != len(naming.get(r["name"].lower(), ()))]
        if wrong:
            errors.append(f"items_master.csv: {len(wrong)} direct recipe counts differ from the distinct-recipe recount (first: {wrong[0]})")
    except (OSError, KeyError, ValueError) as e:
        errors.append(f"count invariants could not be checked: {e}")

    # 5. text hygiene and game content
    texts = glob.glob(os.path.join(PROJECT, "*.md")) + glob.glob(os.path.join(NOTES, "*.md")) + \
        glob.glob(os.path.join(PROJECT, "scripts", "*.py")) + glob.glob(os.path.join(PROJECT, "data", "*.md"))
    for p in texts:
        t = read(p)
        bad = sorted({hex(ord(c)) for c in t if ord(c) < 32 and c not in "\n\t\r"})
        if bad:
            errors.append(f"{os.path.relpath(p, PROJECT)}: control characters {bad}")
        if p.startswith(NOTES) and re.search(r"\b[0-9a-f]{32}\b", t):
            errors.append(f"{os.path.relpath(p, PROJECT)}: contains a 32-character hex token (do not copy embedded signatures)")
    for d, _s, files in os.walk(PROJECT):
        for f in files:
            full = os.path.join(d, f)
            rel = os.path.relpath(full, PROJECT)
            if f.lower().endswith(BAD_EXT) or (f.lower().endswith(".json") and os.path.getsize(full) > 100000):
                errors.append(f"{rel}: looks like game content, which must not be kept in the project")
            elif os.path.getsize(full) > 5 * 1048576:
                errors.append(f"{rel}: larger than 5 MB")

    # 6. warnings
    for p in sorted(glob.glob(os.path.join(NOTES, "*.md"))) + [os.path.join(PROJECT, "README.md")]:
        name = os.path.basename(p)
        if name in EXCLUDE_NOTES - {"README.md"}:
            continue
        t = read(p)
        for ph in STALE:
            for m in re.finditer(re.escape(ph), t):
                line = t.count("\n", 0, m.start()) + 1
                warns.append(f"{name}:{line}: phrase {ph!r} (check that it is still true)")
        print(f"tags in {name}: obs {t.count('[obs')}, inf {t.count('[inf')}, unknown {t.count('[?]')}")

    for w in warns:
        print("WARNING", w)
    for e in errors:
        print("ERROR", e)
    print(f"{len(heads)} sections, {len(mapped)} mapped, {len(tables)} tables, "
          f"{len(glob.glob(os.path.join(PROJECT, 'scripts', '*.py')))} scripts: {len(errors)} errors, {len(warns)} warnings")
    sys.exit(1 if errors or (strict and warns) else 0)


if __name__ == "__main__":
    main()
