"""Merged view of the parsed configs with inheritance resolution (read-only helper).

Rules implemented (see notes/data-config.md, 5.1 addenda, and CODEX.md CXR-001 and CXR-002):
- Classes of the same section and name are merged across archives. When the declarations name different parents, a
  parent that is a descendant of the other wins (a refinement such as `Man: All` then `Man: AllVehicles`); unrelated
  parents are recorded in `CONFLICTS` and the first one is kept.
- A class inherits the properties and nested classes of its parent chain.
- A nested class may name its own parent (`class RightArm: LeftArm`, `class AnimationSources: FoodAnimationSources`). The
  parent is looked up first as a sibling in the same container (inherited or defined earlier), then as a root class. If the
  class also exists in the inherited body, the explicit parent is laid underneath the inherited content and any key defined
  by both with different values is recorded in `CONFLICTS`.
"""
import json
import os

SP = os.path.dirname(os.path.abspath(__file__))
DIRS = [os.environ.get("DAYZ_CFG_JSON", os.path.join(SP, "cfg_json"))]  # folder written by pbo_config_dump.py

# Root-level classes (any config root class, not only Cfg*) by lower-case name, and their own parent class names.
_ROOTS = {}
_ROOT_PARENTS = {}

# Unresolved or notable inheritance situations found while loading and resolving: dicts with a "kind" key.
CONFLICTS = []


def is_cls(v):
    return isinstance(v, dict) and "__parent__" in v


def merge_into(dst, src, path=""):
    """Merge class src into dst: later definitions add/override entries; distinct parents are collected."""
    sp = src.get("__parent__")
    if sp and not path:  # top-level class: collect every declared parent, settled after loading
        seen = dst.setdefault("__parents__", [])
        if dst.get("__parent__") and dst["__parent__"] not in seen:
            seen.append(dst["__parent__"])
        if not dst.get("__parent__"):
            dst["__parent__"] = sp
        if sp not in seen:
            seen.append(sp)
    elif sp:  # nested class: keep the first parent, record a disagreement
        if not dst.get("__parent__"):
            dst["__parent__"] = sp
        elif dst["__parent__"].lower() != sp.lower():
            CONFLICTS.append({"kind": "nested-parent-redeclared", "path": path, "kept": dst["__parent__"], "other": sp})
    for k, v in src.items():
        if k.startswith("__"):
            continue
        if is_cls(v) and k.lower() in {x.lower() for x in dst if is_cls(dst.get(x))}:
            key = next(x for x in dst if x.lower() == k.lower() and is_cls(dst[x]))
            merge_into(dst[key], v, path + "/" + k)
        else:
            dst[k] = v


def _ancestors(sec, name):
    out, k, n = [], name.lower(), 0
    while k in sec and n < 80:
        out.append(k)
        k = (sec[k].get("__parent__") or "").lower()
        n += 1
    return out


def _settle_parents(sections):
    """Choose one parent for classes declared with several: the descendant of the others, else the first (and record it)."""
    for secname, sec in sections.items():
        for k, c in sec.items():
            ps = c.pop("__parents__", None)
            if not ps or len(ps) < 2:
                continue
            best = None
            for cand in ps:
                anc = {a for a in _ancestors(sec, cand)}
                if all(o.lower() in anc for o in ps if o != cand):
                    best = cand
                    break
            if best:
                c["__parent__"] = best
                CONFLICTS.append({"kind": "parent-refined", "section": secname, "class": c.get("__name__", k),
                                  "parents": ps, "chosen": best})
            else:
                c["__parent__"] = ps[0]
                CONFLICTS.append({"kind": "parent-unresolved", "section": secname, "class": c.get("__name__", k),
                                  "parents": ps, "chosen": ps[0]})


def load():
    sections = {}
    CONFLICTS.clear()
    for d in DIRS:
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json") or fn.startswith("_"):
                continue
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                root = json.load(f)
            for sec, body in root.items():
                if sec.startswith("__") or not is_cls(body):
                    continue
                tgt = sections.setdefault(sec.lower(), {})
                if body.get("__parent__"):
                    _ROOT_PARENTS[sec.lower()] = body["__parent__"]
                for cname, cbody in body.items():
                    if cname.startswith("__") or not is_cls(cbody):
                        continue
                    key = cname.lower()
                    if key in tgt:
                        merge_into(tgt[key], cbody)
                        tgt[key]["__name__"] = tgt[key].get("__name__", cname)
                    else:
                        cbody["__name__"] = cname
                        if cbody.get("__parent__"):
                            cbody["__parents__"] = [cbody["__parent__"]]
                        tgt[key] = cbody
    _settle_parents(sections)
    _ROOTS.clear()
    _ROOTS.update(sections)
    return sections


def resolve(sec, name, cache=None, depth=0):
    """Return a flat-ish dict with parent properties merged under child's."""
    cache = cache if cache is not None else {}
    k = name.lower()
    if k in cache:
        return cache[k]
    c = sec.get(k)
    if c is None or depth > 60:
        return {}
    base = {}
    p = c.get("__parent__")
    if p:
        pr = resolve(sec, p, cache, depth + 1)
        base = json.loads(json.dumps(pr))
    base = resolve_nested(c, base, c.get("__name__", name))
    cache[k] = base
    return base


def _find_ci(d, name):
    """Key of d whose lower-case form equals name's, or None."""
    low = name.lower()
    return next((x for x in d if not x.startswith("__") and x.lower() == low), None)


def _overlay(base, top, owner, path=""):
    """Lay `top` over `base` (both flat class bodies); record keys both define with different values."""
    for k, v in top.items():
        if k.startswith("__"):
            continue
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _overlay(base[k], v, owner, path + "/" + k)
        else:
            if k in base and not isinstance(base[k], dict) and base[k] != v:
                CONFLICTS.append({"kind": "nested-parent-vs-inherited", "class": owner, "path": path + "/" + k,
                                  "explicit_parent_value": base[k], "inherited_value": v})
            base[k] = json.loads(json.dumps(v))
    return base


def resolve_nested(own, base, owner=""):
    """Return the flat body of class `own` laid over the already-flat `base` (its parent's body).

    A nested class may name its own parent (`class RightArm: LeftArm`); that parent is a sibling in the same
    enclosing class, either inherited from `base` or defined earlier in `own`, or a root-level class. An explicit parent is
    always honoured: its content is laid under the same-named class inherited from `base`, if there is one."""
    out = json.loads(json.dumps({k: v for k, v in base.items() if not k.startswith("__")}))
    for kk, vv in own.items():
        if kk.startswith("__"):
            continue
        if not is_cls(vv):
            out[kk] = vv
            continue
        existing = _find_ci(out, kk)
        inherited = out[existing] if existing is not None and isinstance(out[existing], dict) else None
        key = existing if inherited is not None else kk
        start = {}
        par = vv.get("__parent__")
        if par and par.lower() != kk.lower():
            sib = _find_ci(out, par)
            if sib is not None and isinstance(out[sib], dict):
                start = json.loads(json.dumps(out[sib]))
            elif par.lower() in _ROOTS:
                start = flatten_root(par)  # the parent is a root-level class outside this container
            else:
                CONFLICTS.append({"kind": "nested-parent-not-found", "class": owner, "path": kk, "parent": par})
        if inherited is not None:
            start = _overlay(start, inherited, owner or "?", kk) if start else json.loads(json.dumps(inherited))
        out[key] = {"__parent__": "", **resolve_nested(vv, start, owner)}  # keep the class marker is_cls() relies on
    return out


def flatten_root(name, depth=0):
    """Flat children of a root-level class, laid over its own parent root class (or {} if unknown)."""
    k = name.lower()
    if k not in _ROOTS or depth > 40:
        return {}
    own = {c.get("__name__", n): c for n, c in _ROOTS[k].items()}
    parent = _ROOT_PARENTS.get(k)
    base = flatten_root(parent, depth + 1) if parent else {}
    return resolve_nested(own, base, name)


def chain(sec, name):
    out, k, n = [], name.lower(), 0
    while k in sec and n < 80:
        out.append(sec[k]["__name__"])
        k = (sec[k].get("__parent__") or "").lower()
        n += 1
    return out


def descendants(sec, root):
    root = root.lower()
    memo = {}

    def is_desc(k, d=0):
        if k == root:
            return True
        if k in memo:
            return memo[k]
        if k not in sec or d > 80:
            return False
        p = (sec[k].get("__parent__") or "").lower()
        memo[k] = bool(p) and is_desc(p, d + 1)
        return memo[k]

    return [sec[k]["__name__"] for k in sec if k != root and is_desc(k)]
