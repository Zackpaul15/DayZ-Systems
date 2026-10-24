"""List the script proto declarations that native_api.csv did not match, with a reason.

usage: native_gaps.py NATIVE_API_CSV SCRIPTS_SRC_DIR OUT_CSV

Categories:
  dev/VR/console   class belongs to the Workbench, profiler, debug UI or VR/console layers (not used by the retail game)
  builtin type     methods of string, vector, array, int, float and similar (registered with a different mechanism)
  other class      the same method name is registered, but the table row was attributed to another script class;
                   `candidate_classes` and `candidate_reg_fns` show where (an attribution error or an inherited method)
  not registered   no registration with this method name was found at all
Read-only; nothing is executed.
"""
import collections
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import native_api  # noqa: E402

DEV = {"Workbench", "EnProfiler", "DbgUI", "DebugText", "WorkbenchPlugin", "WBModuleDef", "ScriptEditor",
       "ResourceBrowser", "WorldEditor", "WorldEditorTool", "WorkspaceTool"}
BUILTIN = {"string", "vector", "array", "map", "set", "int", "float", "bool", "Class", "typename", "Managed",
           "EnScript", "Math", "Math3D", "Param"}


def main():
    api, scripts, out = sys.argv[1:4]
    proto = native_api.script_protos(scripts)
    rows = list(csv.DictReader(open(api, encoding="utf-8")))
    have = collections.defaultdict(set)
    by_name = collections.defaultdict(list)
    for r in rows:
        by_name[r["method"]].append(r)
        if r["name_in_script_class"] == "yes":
            have[r["script_class"]].add(r["method"])
    res = []
    for c, ms in sorted(proto.items()):
        for m in sorted(ms - have[c]):
            others = [r for r in by_name.get(m, []) if r["script_class"] != c]
            if c in DEV or c.startswith("VR"):
                cat = "dev/VR/console"
            elif c in BUILTIN:
                cat = "builtin type"
            elif others:
                cat = "other class"
            else:
                cat = "not registered"
            res.append({"script_class": c, "method": m, "category": cat,
                        "candidate_classes": "|".join(sorted({r["script_class"] or "?" for r in others})),
                        "candidate_reg_fns": "|".join(sorted({r["reg_fn"] for r in others}))})
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0].keys()))
        w.writeheader()
        w.writerows(res)
    cnt = collections.Counter(r["category"] for r in res)
    print(len(res), "unmatched:", dict(cnt))


if __name__ == "__main__":
    main()
