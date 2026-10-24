"""Read the language table (languagecore.pbo > stringtable.csv) and resolve config display names.

usage as a module:
    import stringtable
    tbl = stringtable.load(r"F:\\...\\DayZ\\dta\\languagecore.pbo")   # key (lower case) -> row dict
    stringtable.english(tbl, "$STR_cfgWeapons_M4A10")                   # 'M4-A1'

usage as a script (adds a displayName column to a CSV that has a 'name' column):
    py -I stringtable.py LANGUAGECORE_PBO CONFIG_JSON_DIR CSV [CSV ...]
Read-only on the game files.
"""
import csv
import io
import os
import struct
import sys


def _read_pbo_entry(path, wanted):
    with open(path, "rb") as f:
        buf = f.read()
    pos = 0

    def cstr():
        nonlocal pos
        end = buf.index(b"\x00", pos)
        s = buf[pos:end].decode("latin-1")
        pos = end + 1
        return s

    entries = []
    while True:
        name = cstr()
        packing, orig, _r, _ts, size = struct.unpack_from("<5I", buf, pos)
        pos += 20
        if name == "" and packing == 0x56657273:
            while cstr() != "":
                cstr()
            continue
        if name == "":
            break
        entries.append((name, packing, size))
    off = pos
    for name, packing, size in entries:
        if name.lower() == wanted:
            if packing != 0:
                raise ValueError("packed entry")
            return buf[off:off + size]
        off += size
    raise KeyError(wanted)


def load(pbo_path):
    raw = _read_pbo_entry(pbo_path, "stringtable.csv").decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(raw)))
    hdr = [h for h in rows[0] if h]
    table = {}
    for r in rows[1:]:
        if r and r[0]:
            table[r[0].lower()] = dict(zip(hdr, r))
    return table


def english(table, value):
    """Resolve a config value such as '$STR_Apple0' to its English text, or None."""
    if not isinstance(value, str):
        return None
    key = value[1:] if value.startswith("$") else value
    row = table.get(key.lower())
    return row.get("english") if row else None


def _main():
    pbo, cfgdir, *csvs = sys.argv[1:]
    os.environ["DAYZ_CFG_JSON"] = cfgdir
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import cfgmodel as m
    tbl = load(pbo)
    S = m.load()
    cache = {}
    secs = [S["cfgvehicles"], S["cfgweapons"], S["cfgmagazines"]]
    for path in csvs:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())
        if "displayName" not in fields:
            fields.insert(1, "displayName")
        hit = 0
        for r in rows:
            name = r["name"]
            text = None
            for sec in secs:
                if name.lower() in sec:
                    text = english(tbl, m.resolve(sec, name, cache).get("displayName"))
                    break
            r["displayName"] = text or ""
            hit += 1 if text else 0
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"{os.path.basename(path)}: {hit}/{len(rows)} names resolved")


if __name__ == "__main__":
    _main()
