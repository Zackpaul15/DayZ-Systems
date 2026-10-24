"""Reader for rapified (binary) Arma/Enfusion config files: config.bin ('\\0raP').

Parses into nested dicts. Class bodies become {"__parent__": name, "__ext__": [...], "__del__": [...], entries...}.
Arrays become Python lists. Read-only; never writes.
"""
import struct


class RapError(Exception):
    pass


class Reader:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self):
        v = struct.unpack_from("<f", self.d, self.p)[0]
        self.p += 4
        return v

    def cstr(self):
        end = self.d.index(b"\x00", self.p)
        s = self.d[self.p:end].decode("latin-1")
        self.p = end + 1
        return s

    def compressed(self):
        val = self.u8()
        tmp = val
        while tmp & 0x80:
            tmp = self.u8()
            val += (tmp - 1) * 0x80
        return val


def read_value(r, sub):
    if sub == 0:
        return r.cstr()
    if sub == 1:
        return r.f32()
    if sub == 2:
        return r.i32()
    raise RapError(f"unknown value subtype {sub} at {r.p}")


def read_array(r):
    n = r.compressed()
    out = []
    for _ in range(n):
        sub = r.u8()
        if sub == 3:
            out.append(read_array(r))
        else:
            out.append(read_value(r, sub))
    return out


def read_class(r, offset, depth=0, seen=None):
    saved = r.p
    r.p = offset
    node = {"__parent__": r.cstr()}
    n = r.compressed()
    pending = []
    for _ in range(n):
        t = r.u8()
        if t == 0:  # class with body at offset
            name = r.cstr()
            off = r.i32()
            pending.append((name, off))
        elif t == 1:  # scalar
            sub = r.u8()
            name = r.cstr()
            node[name] = read_value(r, sub)
        elif t == 2:  # array
            name = r.cstr()
            node[name] = read_array(r)
        elif t == 3:  # extern class
            name = r.cstr()
            node.setdefault("__ext__", []).append(name)
        elif t == 4:  # delete class
            name = r.cstr()
            node.setdefault("__del__", []).append(name)
        elif t == 5:  # array append (+=)
            r.i32()
            name = r.cstr()
            node[name] = read_array(r)
        else:
            raise RapError(f"unknown entry type {t} at {r.p}")
    for name, off in pending:
        node[name] = read_class(r, off, depth + 1)
    r.p = saved
    return node


def parse(data):
    if data[:4] != b"\x00raP":
        raise RapError("not a rapified config")
    r = Reader(data)
    r.p = 12
    enum_off = r.i32()
    root = read_class(r, 16)
    enums = []
    if 0 < enum_off < len(data):
        r.p = enum_off
        n = struct.unpack_from("<I", data, enum_off)[0]
        r.p = enum_off + 4
        for _ in range(n):
            enums.append((r.cstr(), r.i32()))
    return root, enums


if __name__ == "__main__":
    import sys
    root, enums = parse(open(sys.argv[1], "rb").read())
    print("top-level:", [k for k in root if not k.startswith("__")][:40])
    print("enums:", len(enums))
