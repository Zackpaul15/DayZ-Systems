"""Minimal PBO reader: lists entries and optionally extracts them. Read-only on the PBO."""
import os
import struct
import sys


def read_cstr(buf, pos):
    end = buf.index(b"\x00", pos)
    return buf[pos:end].decode("latin-1"), end + 1


def parse(path):
    with open(path, "rb") as f:
        buf = f.read()
    pos = 0
    props = {}
    entries = []
    while True:
        name, pos = read_cstr(buf, pos)
        packing, orig, _res, _ts, size = struct.unpack_from("<5I", buf, pos)
        pos += 20
        if name == "" and packing == 0x56657273:  # 'Vers' properties header
            while True:
                key, pos = read_cstr(buf, pos)
                if key == "":
                    break
                val, pos = read_cstr(buf, pos)
                props[key] = val
            continue
        if name == "":
            break  # terminator entry
        entries.append((name, packing, orig, size))
    data_pos = pos
    out = []
    for name, packing, orig, size in entries:
        out.append((name, packing, orig, size, data_pos))
        data_pos += size
    return buf, props, out


def main():
    path = sys.argv[1]
    dest = sys.argv[2] if len(sys.argv) > 2 else None
    buf, props, entries = parse(path)
    print("properties:", props)
    print("entries:", len(entries))
    compressed = [e for e in entries if e[1] != 0]
    print("non-stored (packing != 0):", len(compressed))
    if dest is None:
        for name, packing, orig, size, off in entries:
            print(f"{size:9d}  {name}")
        return
    root = os.path.abspath(dest)
    os.makedirs(root, exist_ok=True)
    written = 0
    for name, packing, orig, size, off in entries:
        if packing != 0:
            continue
        target = os.path.abspath(os.path.join(root, name.replace("\\", os.sep)))
        if os.path.commonpath([root, target]) != root:
            print("skipping path outside destination:", name)
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as out:
            out.write(buf[off:off + size])
        written += 1
    print("extracted:", written, "->", root)


main()
