"""Find strings in DayZ_x64.exe with their virtual address and section (for Ghidra xrefs).

usage:
  find_strings.py WORD [WORD ...]     printable strings containing any WORD (case-insensitive)
  find_strings.py range LO HI         strings between two hex file offsets

Reads the file bytes only; nothing is executed. Then run `xrefs <address>` in a Ghidra batch task file.
"""
import re, struct, sys
EXE = r"F:\SteamLibrary\steamapps\common\DayZ\DayZ_x64.exe"
d = open(EXE, "rb").read()
pe = struct.unpack_from("<I", d, 0x3c)[0]
nsec = struct.unpack_from("<H", d, pe + 6)[0]
opt = struct.unpack_from("<H", d, pe + 20)[0]
base = struct.unpack_from("<Q", d, pe + 24 + 24)[0]
sec = []
o = pe + 24 + opt
for i in range(nsec):
    nm = d[o:o + 8].rstrip(b"\0").decode()
    vs, va, rs, ro = struct.unpack_from("<IIII", d, o + 8)
    sec.append((nm, va, vs, ro, rs))
    o += 40


def va(off):
    for nm, v, vs, ro, rs in sec:
        if ro <= off < ro + rs:
            return base + v + off - ro, nm
    return None, None


if sys.argv[1] == "range":
    lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
    for m in re.finditer(rb"[\x20-\x7e]{4,}", d):
        a, nm = va(m.start())
        if a and lo <= a < hi:
            print(f"0x{a:x} {m.group()[:150].decode()}")
    sys.exit(0)
words = [w.encode() for w in sys.argv[1:]]
pat = re.compile(rb"[\x20-\x7e]{4,}")
for m in pat.finditer(d):
    s = m.group()
    low = s.lower()
    if any(w.lower() in low for w in words):
        a, nm = va(m.start())
        if a:
            print(f"0x{a:x} {nm} {s[:140].decode()}")
