"""Re-sign a patched BOOT.BIN (plain PRX) into a ~PSP EBOOT.BIN (real PSP / Vita need it; PPSSPP boots either).

    python -X utf8 tools/sign.py IN.elf OUT.bin

Uses sign_np -elf (github.com/swarzesherz/sign_np @ ac77d56, GPLv3, source in tools/sign_np/src) built for Linux and
run through WSL. Build it once:  wsl -e sh -c "cd tools/sign_np/src && gcc -O2 -w -I./libkirk -o ../sign_np *.c libkirk/*.c -lz"
The original EBOOT's tag (0xC0CB167C, ~PSP +0xD0) is an old key sign_np cannot make; tag 0 = 0xD91609F0 is the
lowest-firmware tag it has (docs/re/build.md "EBOOT").
"""
import os, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = "tools/sign_np/sign_np"
TAG, TAG_WORD = 0, 0xD91609F0


def sign(elf):
    assert elf[:4] == b"\x7fELF", "not an ELF"
    tmp = os.path.join(ROOT, "work", "sign")
    os.makedirs(tmp, exist_ok=True)
    with open(os.path.join(tmp, "in.elf"), "wb") as f:
        f.write(elf)
    out = os.path.join(tmp, "out.bin")
    if os.path.exists(out):
        os.remove(out)
    assert os.path.exists(os.path.join(ROOT, BIN)), f"{BIN} missing: build it (see tools/sign.py docstring)"
    r = subprocess.run(["wsl", "-e", BIN, "-elf", "work/sign/in.elf", "work/sign/out.bin", str(TAG)],
                       cwd=ROOT, capture_output=True)
    assert r.returncode == 0 and os.path.exists(out), r.stdout.decode(errors="replace")[-500:]
    d = open(out, "rb").read()
    assert d[:4] == b"~PSP" and struct.unpack_from("<I", d, 0xD0)[0] == TAG_WORD, "sign_np output not ~PSP"
    assert struct.unpack_from("<I", d, 0x28)[0] == len(elf), "~PSP elf_size differs from the input"
    return d


if __name__ == "__main__":
    with open(sys.argv[2], "wb") as f:
        f.write(sign(open(sys.argv[1], "rb").read()))
