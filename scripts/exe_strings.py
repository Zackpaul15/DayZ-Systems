"""Extract printable strings from a PE file and diff two executables.

usage:
  exe_strings.py dump  EXE OUT_TXT [MIN_LEN]           one string per line, sorted, unique (ASCII and UTF-16LE)
  exe_strings.py diff  EXE_A EXE_B OUT_PREFIX [MIN_LEN]  writes OUT_PREFIX.only_a.txt, .only_b.txt, .common_count

Reads the file bytes only; nothing is executed. Default minimum length is 6.
"""
import re
import sys


def extract(path, min_len=6):
    data = open(path, "rb").read()
    out = set()
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, data):
        out.add(m.group().decode("ascii"))
    # UTF-16LE strings: printable ASCII character followed by a zero byte, repeated
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){%d,}" % min_len, data):
        out.add(m.group().decode("utf-16-le"))
    return out


def main():
    cmd = sys.argv[1]
    if cmd == "dump":
        exe, out = sys.argv[2], sys.argv[3]
        min_len = int(sys.argv[4]) if len(sys.argv) > 4 else 6
        s = sorted(extract(exe, min_len))
        open(out, "w", encoding="utf-8").write("\n".join(s))
        print(f"{len(s)} strings")
    elif cmd == "diff":
        a, b, prefix = sys.argv[2], sys.argv[3], sys.argv[4]
        min_len = int(sys.argv[5]) if len(sys.argv) > 5 else 6
        sa, sb = extract(a, min_len), extract(b, min_len)
        only_a, only_b = sorted(sa - sb), sorted(sb - sa)
        open(prefix + ".only_a.txt", "w", encoding="utf-8").write("\n".join(only_a))
        open(prefix + ".only_b.txt", "w", encoding="utf-8").write("\n".join(only_b))
        print(f"A: {len(sa)}  B: {len(sb)}  common: {len(sa & sb)}  only A: {len(only_a)}  only B: {len(only_b)}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
