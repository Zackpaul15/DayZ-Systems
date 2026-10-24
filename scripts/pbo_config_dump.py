"""Pull config.bin out of every PBO in the given folders (read-only, seeks past data),
parse each with rap_reader, and write one JSON per PBO plus a summary.

usage: pbo_config_dump.py OUT_DIR PBO_DIR [PBO_DIR ...]
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rap_reader  # noqa: E402


def read_header(f):
    """Return (properties, entries[(name, packing, orig, size)], data_start)."""
    f.seek(0)
    buf = f.read(4 * 1024 * 1024)
    pos = 0

    def cstr():
        nonlocal pos, buf
        while True:
            end = buf.find(b"\x00", pos)
            if end != -1:
                s = buf[pos:end].decode("latin-1")
                pos = end + 1
                return s
            more = f.read(4 * 1024 * 1024)
            if not more:
                raise ValueError("truncated header")
            buf += more

    def need(n):
        nonlocal buf
        while len(buf) - pos < n:
            more = f.read(4 * 1024 * 1024)
            if not more:
                raise ValueError("truncated header")
            buf += more

    props, entries = {}, []
    while True:
        name = cstr()
        need(20)
        packing, orig, _r, _ts, size = struct.unpack_from("<5I", buf, pos)
        pos += 20
        if name == "" and packing == 0x56657273:
            while True:
                k = cstr()
                if k == "":
                    break
                props[k] = cstr()
            continue
        if name == "":
            break
        entries.append((name, packing, orig, size))
    return props, entries, pos


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    summary = []
    for folder in sys.argv[2:]:
        for fn in sorted(os.listdir(folder)):
            if not fn.lower().endswith(".pbo"):
                continue
            path = os.path.join(folder, fn)
            row = {"pbo": fn, "folder": os.path.basename(folder.rstrip("\\/"))}
            try:
                with open(path, "rb") as f:
                    props, entries, data_start = read_header(f)
                    row["entries"] = len(entries)
                    row["prefix"] = props.get("prefix")
                    off = data_start
                    cfgs = []
                    for name, packing, orig, size in entries:
                        if name.lower().replace("/", "\\").split("\\")[-1] == "config.bin":
                            cfgs.append((name, off, size, packing))
                        off += size
                    if not cfgs:
                        row["config"] = None
                        summary.append(row)
                        continue
                    row["config_files"] = len(cfgs)
                    row["config_bytes"] = sum(c[2] for c in cfgs)
                    row["top"] = []
                    for name, coff, csize, packing in cfgs:
                        if packing != 0:
                            row.setdefault("errors", []).append(name + ": packed")
                            continue
                        f.seek(coff)
                        data = f.read(csize)
                        try:
                            root, enums = rap_reader.parse(data)
                        except Exception as e:
                            row.setdefault("errors", []).append(f"{name}: {type(e).__name__}: {e}")
                            continue
                        safe = name.replace("\\", "__").replace("/", "__")
                        with open(os.path.join(out, f"{fn}.{safe}.json"), "w", encoding="utf-8") as o:
                            json.dump(root, o)
                        row["top"] += [k for k in root if not k.startswith("__")]
            except Exception as e:  # keep going, report
                row["error"] = f"{type(e).__name__}: {e}"
            summary.append(row)
    with open(os.path.join(out, "_summary.json"), "w", encoding="utf-8") as o:
        json.dump(summary, o, indent=1)
    ok = sum(r.get("config_files", 0) for r in summary)
    errs = sum(len(r.get("errors", [])) + (1 if "error" in r else 0) for r in summary)
    print(f"pbos: {len(summary)}  config.bin files found: {ok}  pbos with none: {sum(1 for r in summary if r.get('config', 1) is None)}  errors: {errs}")


if __name__ == "__main__":
    main()
