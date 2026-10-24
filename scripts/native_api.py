"""Build data/native_api.csv: the engine's native script registrations, matched to script proto declarations.

usage: native_api.py DECOMPILED_REG_FUNCS.txt NAME_STRINGS.txt SCRIPTS_SRC_DIR OUT_CSV

Inputs (produced with scripts/ghidra/run_batch.ps1, see notes 4.4):
  DECOMPILED_REG_FUNCS.txt  'decompile FUN_x' output for every function that calls the two registrars
                            FUN_1402724e0 (static methods) and FUN_1402725a0 (instance methods)
  NAME_STRINGS.txt          'string 0xADDR' output for method names that Ghidra did not define as strings
  SCRIPTS_SRC_DIR           unpacked scripts.pbo (scripts/bootstrap.py)
Each registration call is  registrar(context, classObject, "Name", nativeFunction, ...).
Because the class object is passed in, the class is attributed by name overlap between a registration
function's method names and the proto declarations of each script class (a creation call with the class
name is used when present). Read-only; nothing is executed.
"""
import collections
import csv
import os
import re
import sys

REGISTRARS = ("FUN_1402724e0", "FUN_1402725a0")
CALL = re.compile(r'(FUN_1402724e0|FUN_1402725a0)\(\s*([^,]+),\s*([^,]+),\s*(?:"([^"]+)"|&DAT_([0-9a-f]+)),\s*(&?[A-Za-z_0-9]+)')
CLS = re.compile(r"^(?:sealed\s+|modded\s+|abstract\s+)*class\s+(\w+)")  # column 0 only: an indented "class X" inside a body is a forward declaration
PROTO = re.compile(r"\bproto\b[^;(]*?\b(\w+)\s*\(")


def script_protos(root):
    proto = collections.defaultdict(set)
    for d, _s, files in os.walk(root):
        for f in files:
            if not f.endswith(".c"):
                continue
            cur = None
            for line in open(os.path.join(d, f), encoding="utf-8", errors="replace"):
                m = CLS.match(line)
                if m:
                    cur = m.group(1)
                if "proto" in line and cur and not line.lstrip().startswith("//"):
                    m = PROTO.search(line)
                    if m:
                        proto[cur].add(m.group(1))
    return proto


def main():
    dump, strs, scripts, out = sys.argv[1:5]
    text = open(dump, encoding="utf-8").read()
    secs = re.split(r"\n=== decompile (FUN_[0-9a-f]+) ===\n", text)
    dat = dict(re.findall(r"=== string 0x([0-9a-f]+) ===\n[0-9a-f]+: (.*)", open(strs, encoding="utf-8").read()))
    rows, hints = [], {}
    for k in range(1, len(secs), 2):
        fn, body = secs[k], re.sub(r"\s+", " ", secs[k + 1])
        h = re.findall(r'"([A-Za-z_][A-Za-z_0-9]*)",\s*0x[0-9a-f]+\s*,', body)
        if h:
            hints[fn] = h[0]
        for c in re.findall(r"(?:%s)\([^;]*;" % "|".join(REGISTRARS), body):
            m = CALL.match(c)
            if not m:
                continue
            name = m.group(4) or dat.get(m.group(5), "?" + str(m.group(5)))
            rows.append({"reg_fn": fn, "kind": "static" if m.group(1) == REGISTRARS[0] else "instance",
                         "method": name, "native_fn": m.group(6)})
    proto = script_protos(scripts)
    by_fn = collections.defaultdict(list)
    for r in rows:
        by_fn[r["reg_fn"]].append(r)
    result = []
    for fn, rs in by_fn.items():
        names = {r["method"] for r in rs}
        scored = sorted(((len(names & ms) / len(names | ms), c) for c, ms in proto.items()), reverse=True)
        score, cls = scored[0] if scored else (0.0, "")
        hint = hints.get(fn)
        if hint in proto and len(names & proto[hint]) / len(names | proto[hint]) >= score:
            cls, score = hint, len(names & proto[hint]) / len(names | proto[hint])
        for r in rs:
            r["script_class"] = cls if score >= 0.2 else ""
            r["class_score"] = round(score, 2)
            accepted = r["script_class"]  # a class rejected by the score threshold must not count as a match
            r["name_in_script_class"] = "yes" if accepted and accepted in proto and r["method"] in proto[accepted] else "no"
            result.append(r)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["script_class", "method", "kind", "native_fn", "reg_fn", "class_score",
                                          "name_in_script_class"], extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(result, key=lambda r: (r["script_class"], r["method"])))
    declared = sum(len(v) for v in proto.values())
    matched = len({(r["script_class"], r["method"]) for r in result if r["name_in_script_class"] == "yes"})
    print(f"registrations: {len(result)} in {len(by_fn)} functions; script proto declarations: {declared} in "
          f"{len(proto)} classes; matched: {matched}; attributed rows: {sum(1 for r in result if r['script_class'])}")


if __name__ == "__main__":
    main()
