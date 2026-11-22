"""getters.py: summarise the string-table getters of the Growlanser PSP module from a RAM dump (recon).

Splits code into blocks ending at `jr $ra` (+ delay slot) and prints, per block: the bound (sltiu imm), the
addresses built by lui+addiu/lhu/lw (module-relocated RAM addresses, and file offsets in BOOT.BIN), and jal targets.

    python -X utf8 tools/getters.py RAM.bin START END [MODULE_BASE]
"""
import struct
import sys

from capstone import CS_ARCH_MIPS, CS_MODE_LITTLE_ENDIAN, CS_MODE_MIPS32, Cs

RAM = 0x08800000
DATA_VADDR, DATA_FILE = 0x11D3C0, 0x11D480


def file_off(addr, base):
    va = addr - base
    return va + (DATA_FILE - DATA_VADDR) if va >= DATA_VADDR else va + 0xA0


def main():
    ram = open(sys.argv[1], "rb").read()
    start, end = int(sys.argv[2], 16), int(sys.argv[3], 16)
    base = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x08804000
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)
    code = ram[start - RAM:end - RAM]
    hi, blk, out = {}, None, []
    after_jr = False
    for ins in md.disasm(code, start):
        if blk is None:
            blk = {"at": ins.address, "bound": [], "addr": [], "jal": []}
        ops = ins.op_str.replace("$", "").split(", ")
        m = ins.mnemonic
        if m == "lui":
            hi[ops[0]] = int(ops[1], 0) << 16
        elif m in ("addiu", "ori") and len(ops) == 3 and ops[1] in hi:
            v = hi[ops[1]] + int(ops[2], 0)
            blk["addr"].append(v)
            if ops[0] == ops[1]:
                del hi[ops[1]]
        elif m in ("lhu", "lh", "lw", "lbu", "lb", "sh", "sw", "sb") and "(" in ops[-1]:
            off, reg = ops[-1].rstrip(")").split("(")
            if reg in hi:
                blk["addr"].append(hi[reg] + int(off or "0", 0))
        elif m == "sltiu" or m == "slti":
            blk["bound"].append(int(ops[2], 0))
        elif m == "jal":
            blk["jal"].append(int(ops[0], 0))
        if after_jr:
            out.append(blk)
            blk, hi, after_jr = None, {}, False
        elif m == "jr" and ops[0] == "ra":
            after_jr = True
    for b in out:
        addrs = " ".join("%X(f%X)" % (a, file_off(a, base)) if base <= a < base + 0x600000 else "%X" % a
                         for a in dict.fromkeys(b["addr"]))
        print("%08X bound=%s jal=%s  %s" % (b["at"], ",".join(hex(x) for x in b["bound"]) or "-",
                                            ",".join("%X" % x for x in b["jal"]) or "-", addrs))


if __name__ == "__main__":
    main()
