"""Action catalog: every registered player action with its group, parent, texts, animation, conditions and time.

usage: actions.py SCRIPTS_DIR OUT_CSV [LANGUAGECORE_PBO]

SCRIPTS_DIR is an unpacked scripts.pbo (bootstrap.py). Reads the registration order from ActionConstructor.c (the
section comments give the group) and the class body of each action under 4_World/Classes/UserActionsComponent.
Columns come from simple constructor assignments, so values set by overrides at runtime (SetupAnimation and similar)
are not seen. Read-only; nothing is executed.
"""
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.join("4_World", "Classes", "UserActionsComponent")


def strip_comments(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def block(src, start):
    i = src.index("{", start)
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i + 1:j]
    return src[i + 1:]


def main():
    scripts, out = sys.argv[1:3]
    tbl = None
    if len(sys.argv) > 3:
        import stringtable
        tbl = stringtable.load(sys.argv[3])
    base = os.path.join(scripts, ROOT)
    raw = open(os.path.join(base, "ActionConstructor.c"), encoding="utf-8", errors="replace").read()
    group, order = "", []
    for line in raw.splitlines():
        s = line.strip()
        m = re.match(r"//\s*(.+)", s)
        if m and not s.startswith("//actions"):
            group = m.group(1).strip()
        m = re.match(r"actions\.Insert\((\w+)\);", s)
        if m:
            order.append((m.group(1), group))
    classes = {}
    for d, _s, files in os.walk(base):
        for fn in files:
            if not fn.endswith(".c"):
                continue
            src = strip_comments(open(os.path.join(d, fn), encoding="utf-8", errors="replace").read())
            for m in re.finditer(r"(?:^|\n)\s*(?:modded\s+)?class\s+(\w+)\s*(?:extends|:)\s*(\w+)", src):
                classes[m.group(1)] = {"parent": m.group(2), "body": block(src, m.end()), "file": os.path.relpath(os.path.join(d, fn), base)}

    def val(body, pat):
        m = re.search(pat, body)
        return m.group(1).strip() if m else ""

    rows = []
    for name, grp in order:
        c = classes.get(name)
        if not c:
            rows.append({"action": name, "group": grp})
            continue
        b = c["body"]
        cb = val(b, r"m_CallbackClass\s*=\s*(\w+)")
        comp = ""
        if cb and cb in classes:
            comp = " ".join(val(classes[cb]["body"], r"m_ActionComponent\s*=\s*new\s+([^;]+);").split())
        text = val(b, r'm_Text\s*=\s*"([^"]*)"')
        eng = ""
        if tbl and text.startswith("#"):
            import stringtable
            eng = stringtable.english(tbl, "$STR_" + text[1:]) or stringtable.english(tbl, "$" + text[1:]) or ""
        # constructor-less actions inherit the parent's values; show the chain so the reader can look up
        chain, p = [], c["parent"]
        while p in classes and len(chain) < 6:
            chain.append(p)
            p = classes[p]["parent"]
        rows.append({
            "action": name, "group": grp, "parent": c["parent"], "ancestors": " > ".join(chain + ([p] if p not in classes else [])),
            "file": c["file"].replace("\\", "/"), "text_key": text, "text": eng,
            "callback": cb, "component": comp,
            "full_body": val(b, r"m_FullBody\s*=\s*(\w+)"), "stance_mask": val(b, r"m_StanceMask\s*=\s*([\w.| ]+);"),
            "command": val(b, r"m_CommandUID\s*=\s*([\w.]+)"),
            "specialty_weight": val(b, r"m_SpecialtyWeight\s*=\s*([\w.\-]+)"),
            "condition_item": val(b, r"m_ConditionItem\s*=\s*new\s+(\w+)"),
            "condition_target": val(b, r"m_ConditionTarget\s*=\s*new\s+(\w+)"),
            "has_action_condition": "yes" if "ActionCondition(" in b else "",
            "has_custom_start": "yes" if re.search(r"override\s+void\s+On(Start|Execute)\w*\(", b) else "",
        })
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, restval="")
        w.writeheader()
        w.writerows(rows)
    missing = sum(1 for r in rows if "parent" not in r)
    print(f"registered actions: {len(rows)}; classes not found: {missing}; groups: {sorted({r['group'] for r in rows})}")


if __name__ == "__main__":
    main()
