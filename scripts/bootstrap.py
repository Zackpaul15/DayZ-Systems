"""Regenerate everything the analysis needs from a DayZ install, outside the project folder.

usage: py -I scripts\\bootstrap.py OUT_DIR [--game GAME_DIR] [--max-mb N] [--steps a,b,...]

Steps (default: all):
  scripts  unpack dta\\scripts.pbo                       -> OUT_DIR\\scripts_src
  configs  parse every config.bin in every archive      -> OUT_DIR\\cfg   (set DAYZ_CFG_JSON to this)
  ce       unpack the worlds_*_ce.pbo mission templates -> OUT_DIR\\ce\\<archive>   (files above --max-mb are skipped)
  lang     stringtable.csv from dta\\languagecore.pbo    -> OUT_DIR\\lang\\stringtable.csv
  dz       the data\\penetration material files of dz.pbo -> OUT_DIR\\dz
  stamp    OUT_DIR\\STAMP.json with exe version, sizes, dates and the counts from the steps above

Read-only on the game files. Refuses an OUT_DIR inside the project folder, because the extracted
output is game content and must not be kept in the project (see README.md).
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from pbo_config_dump import read_header  # noqa: E402

DEFAULT_GAME = r"F:\SteamLibrary\steamapps\common\DayZ"
CONFIG_FOLDERS = ["Addons", "dta", r"nasdara\addons", r"sakhal\Addons"]


def extract_pbo(path, dest, name_filter=None, max_bytes=None):
    """Extract stored entries of one PBO by seeking (never loads the whole archive).

    Returns (written, skipped_packed, skipped_large, skipped_unsafe)."""
    root = os.path.abspath(dest)
    os.makedirs(root, exist_ok=True)
    written = packed = large = unsafe = 0
    with open(path, "rb") as f:
        _props, entries, off = read_header(f)
        for name, packing, _orig, size in entries:
            here = off
            off += size
            if name_filter and not name_filter(name):
                continue
            if packing != 0:
                packed += 1
                continue
            if max_bytes is not None and size > max_bytes:
                large += 1
                continue
            target = os.path.abspath(os.path.join(root, name.replace("\\", os.sep)))
            if os.path.commonpath([root, target]) != root:
                unsafe += 1
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            f.seek(here)
            with open(target, "wb") as out:
                out.write(f.read(size))
            written += 1
    return written, packed, large, unsafe


def exe_build(path):
    """Build strings found in the exe (the PE file-version resource is empty for DayZ), plus the Steam build id.

    Looks for NUL-terminated strings shaped like 1.30.164.200 in the exe bytes."""
    import re
    with open(path, "rb") as f:
        data = f.read()
    # two shapes occur in the exe: 1.30.164200.56 (file) and 1.30.164.200 (runtime-filled, so absent from the file)
    found = sorted({m.group().rstrip(b"\x00").decode()
                    for m in re.finditer(rb"(?<![\d.])\d\.\d{2}\.\d{3,6}\.\d{2,3}\x00", data)})
    build_id = None
    manifest = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(path))), "appmanifest_221100.acf")
    try:
        with open(manifest, encoding="utf-8") as f:
            m = re.search(r'"buildid"\s+"(\d+)"', f.read())
            build_id = m.group(1) if m else None
    except OSError:
        pass
    return {"version_strings": found[:5], "steam_build_id": build_id}


def count_files(root, suffix=None):
    n = 0
    for _d, _s, files in os.walk(root):
        n += sum(1 for x in files if suffix is None or x.lower().endswith(suffix))
    return n


def step_scripts(game, out, report, **_):
    pbo = os.path.join(game, "dta", "scripts.pbo")
    dest = os.path.join(out, "scripts_src")
    w, p, l, u = extract_pbo(pbo, dest)
    report["scripts"] = {"files": w, "packed_skipped": p, "c_files": count_files(dest, ".c")}
    print(f"scripts: {w} files ({report['scripts']['c_files']} .c) -> {dest}")


def step_configs(game, out, report, **_):
    dest = os.path.join(out, "cfg")
    folders = [os.path.join(game, f) for f in CONFIG_FOLDERS if os.path.isdir(os.path.join(game, f))]
    r = subprocess.run([sys.executable, "-I", os.path.join(HERE, "pbo_config_dump.py"), dest, *folders],
                       capture_output=True, text=True)
    print("configs:", r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        raise SystemExit("pbo_config_dump failed: " + r.stderr)
    report["configs"] = {"json_files": count_files(dest, ".json") - 1, "tool_output": r.stdout.strip()}


def ce_archives(game):
    found = []
    for rel in CONFIG_FOLDERS:
        d = os.path.join(game, rel)
        if os.path.isdir(d):
            found += [os.path.join(d, x) for x in sorted(os.listdir(d))
                      if x.lower().startswith("worlds_") and x.lower().endswith("_ce.pbo")]
    return found


def step_ce(game, out, report, max_mb, **_):
    report["ce"] = {}
    for pbo in ce_archives(game):
        stem = os.path.splitext(os.path.basename(pbo))[0]
        w, p, l, u = extract_pbo(pbo, os.path.join(out, "ce", stem), max_bytes=int(max_mb * 1048576))
        report["ce"][stem] = {"files": w, "skipped_large": l, "skipped_packed": p}
        print(f"ce: {stem}: {w} files, {l} skipped as larger than {max_mb} MB")


def step_lang(game, out, report, **_):
    pbo = os.path.join(game, "dta", "languagecore.pbo")
    dest = os.path.join(out, "lang")
    w, *_rest = extract_pbo(pbo, dest, name_filter=lambda n: n.lower() == "stringtable.csv")
    report["lang"] = {"files": w}
    print(f"lang: {w} file -> {dest}")


def step_dz(game, out, report, **_):
    """The bullet penetration material files (the penetration folder under data in dz.pbo)."""
    pbo = os.path.join(game, "Addons", "dz.pbo")
    dest = os.path.join(out, "dz")
    w, *_rest = extract_pbo(pbo, dest, name_filter=lambda n: n.lower().replace("/", "\\").startswith("data\\penetration\\"))
    report["dz"] = {"files": w}
    print(f"dz: {w} penetration material files -> {dest}")


def step_stamp(game, out, report, **_):
    exe = os.path.join(game, "DayZ_x64.exe")
    spbo = os.path.join(game, "dta", "scripts.pbo")
    stamp = {
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "game_dir": game,
        "exe": {"path": exe, **exe_build(exe), "bytes": os.path.getsize(exe),
                "modified": datetime.datetime.fromtimestamp(os.path.getmtime(exe)).isoformat(timespec="seconds")},
        "scripts_pbo": {"bytes": os.path.getsize(spbo),
                        "modified": datetime.datetime.fromtimestamp(os.path.getmtime(spbo)).isoformat(timespec="seconds")},
        "steps": report,
    }
    with open(os.path.join(out, "STAMP.json"), "w", encoding="utf-8") as f:
        json.dump(stamp, f, indent=1)
    print("stamp: exe build", stamp["exe"]["version_strings"], "steam build", stamp["exe"]["steam_build_id"], "->", os.path.join(out, "STAMP.json"))


STEPS = {"scripts": step_scripts, "configs": step_configs, "ce": step_ce, "lang": step_lang, "dz": step_dz, "stamp": step_stamp}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir")
    ap.add_argument("--game", default=DEFAULT_GAME)
    ap.add_argument("--max-mb", type=float, default=20.0)
    ap.add_argument("--steps", default=",".join(STEPS))
    a = ap.parse_args()
    out = os.path.abspath(a.out_dir)
    if os.path.commonpath([out, PROJECT]) == PROJECT:
        sys.exit(f"refusing: {out} is inside the project folder; extracted game content must live elsewhere")
    os.makedirs(out, exist_ok=True)
    report = {}
    for s in a.steps.split(","):
        s = s.strip()
        if s not in STEPS:
            sys.exit(f"unknown step {s!r}; choose from {', '.join(STEPS)}")
        if s == "stamp":
            continue
        STEPS[s](game=a.game, out=out, report=report, max_mb=a.max_mb)
    if "stamp" in a.steps.split(","):
        step_stamp(game=a.game, out=out, report=report)
    print("done:", out)


if __name__ == "__main__":
    main()
