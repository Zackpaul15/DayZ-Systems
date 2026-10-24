"""Weapon state machine tables: stable states and every transition, per firearm mechanism class.

usage: weapon_states.py SCRIPTS_DIR OUT_STATES_CSV OUT_TRANSITIONS_CSV

Reads 4_World/Entities/Firearms/**/*.c. For each class with an InitStateMachine():
  states       variable -> state class (stable states are WeaponStableState subclasses, the rest are action states)
  events       variable -> event class
  transitions  m_fsm.AddTransition(new WeaponTransition(from, event, to [, action, guard]))
Stable-state flags (bullet, magazine, jammed, bolt open) come from the state class bodies in the same file.
Read-only; nothing is executed.
"""
import csv
import os
import re
import sys

ROOT = os.path.join("4_World", "Entities", "Firearms")


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


def split_args(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def main():
    scripts, out_states, out_trans = sys.argv[1:4]
    base = os.path.join(scripts, ROOT)
    states, trans = [], []
    for d, _s, files in os.walk(base):
        for fn in sorted(files):
            if not fn.endswith(".c"):
                continue
            src = strip_comments(open(os.path.join(d, fn), encoding="utf-8", errors="replace").read())
            stable = {}
            for m in re.finditer(r"class\s+(\w+)\s+extends\s+WeaponStableState\s*\{", src):
                body = block(src, m.start())
                sid = re.search(r"GetCurrentStateID\s*\(\s*\)\s*\{\s*return\s+([\w.]+)", body)
                flags = {k: (re.search(k + r"\s*\(\s*\)\s*\{\s*return\s+(true|false)", body) or [None, ""])[1]
                         for k in ("HasBullet", "HasMagazine", "IsJammed", "IsBoltOpen", "IsRepairEnabled")}
                mz = re.search(r"m_muzzleHasBullet\s*=\s*\{([^}]*)\}", body)
                stable[m.group(1)] = (sid.group(1) if sid else "", flags, mz.group(1).replace("MuzzleState.", "").strip() if mz else "")
            for m in re.finditer(r"class\s+(\w+)\s*(?:extends|:)\s*(\w+)\s*\{", src):
                body = block(src, m.start())
                im = re.search(r"void\s+InitStateMachine\s*\(\s*\)", body)
                if not im:
                    continue
                cls = m.group(1)
                ib = block(body, im.start())
                var_cls = {}
                for vm in re.finditer(r"(?:^|;|\{)\s*(?:\w+\s+)?(\w+)\s*=\s*new\s+(\w+)\s*(?:\(([^;]*?)\))?\s*;", ib):
                    var_cls[vm.group(1)] = vm.group(2)
                for vm in re.finditer(r"(\w+)\s*=\s*new\s+(\w+)", ib):
                    var_cls.setdefault(vm.group(1), vm.group(2))
                for var, c in var_cls.items():
                    if c in stable:
                        sid, fl, mz = stable[c]
                        states.append({"mechanism": cls, "file": os.path.relpath(os.path.join(d, fn), base).replace("\\", "/"),
                                       "var": var, "state_class": c, "state_id": sid, "has_bullet": fl["HasBullet"],
                                       "has_magazine": fl["HasMagazine"], "jammed": fl["IsJammed"], "bolt_open": fl["IsBoltOpen"],
                                       "muzzle_state": mz})
                for tm in re.finditer(r"AddTransition\s*\(\s*new\s+WeaponTransition\s*\((.*?)\)\s*\)\s*;", ib, flags=re.S):
                    a = split_args(tm.group(1))
                    if len(a) < 3:
                        continue
                    guard = ""
                    for x in a[3:]:
                        g = re.match(r"new\s+(\w+)", x)
                        if g and g.group(1) != "NULL":
                            guard = g.group(1)
                    trans.append({"mechanism": cls, "from": a[0], "from_class": var_cls.get(a[0], ""),
                                  "event": a[1], "event_class": var_cls.get(a[1], ""),
                                  "to": a[2], "to_class": var_cls.get(a[2], ""), "guard": guard})
    for path, rows in ((out_states, states), (out_trans, trans)):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    mechs = sorted({t["mechanism"] for t in trans})
    print(f"{len(mechs)} mechanisms, {len(states)} stable states, {len(trans)} transitions")


if __name__ == "__main__":
    main()
