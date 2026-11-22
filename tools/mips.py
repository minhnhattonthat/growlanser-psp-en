"""mips.py: small recon helpers over a PSP RAM dump (work/qa/*/ram.bin, base 0x08800000).

    python -X utf8 tools/mips.py func RAM ADDR..          start of the function holding ADDR (addiu sp, sp, -N)
    python -X utf8 tools/mips.py calls RAM ADDR..         every jal to ADDR, with the caller's function start
    python -X utf8 tools/mips.py gp RAM OFF..             loads/stores at gp+OFF (gp = 0x08C8EA44)
"""
import struct
import sys

BASE = 0x08800000
GP = 0x08C8EA44
CODE = (0x08804024, 0x08804024 + 0x10E550)  # module .text in RAM


def words(ram):
    lo, hi = CODE
    return {a: struct.unpack_from("<I", ram, a - BASE)[0] for a in range(lo, hi, 4)}


def func(w, addr):
    a = addr & ~3
    while a >= CODE[0]:
        x = w[a]
        if x >> 16 == 0x27BD and x & 0x8000:  # addiu sp, sp, -N
            return a
        a -= 4
    return None


def main():
    cmd, ram = sys.argv[1], open(sys.argv[2], "rb").read()
    w = words(ram)
    for arg in sys.argv[3:]:
        v = int(arg, 16)
        if cmd == "func":
            f = func(w, v)
            print(f"{v:08X} in function {f:08X}" if f else f"{v:08X}: no prologue found")
        elif cmd == "calls":
            want = 0x0C000000 | ((v >> 2) & 0x3FFFFFF)
            hits = [a for a, x in w.items() if x == want]
            print(f"{v:08X}: {len(hits)} calls")
            for a in hits:
                print(f"  {a:08X}  (in {func(w, a) or 0:08X})")
        elif cmd == "gp":
            hits = [a for a, x in w.items() if (x >> 21) & 31 == 28 and x >> 26 in (0x20, 0x21, 0x23, 0x24, 0x25,
                    0x28, 0x29, 0x2B, 0x09) and (x & 0xFFFF) == (v & 0xFFFF)]
            print(f"gp+{v:X} (= {GP + v:08X}): {len(hits)} refs: " + " ".join(f"{a:08X}" for a in hits))


if __name__ == "__main__":
    main()
