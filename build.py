"""build.py: rebuild the UMD image with patched files swapped in.

  python -X utf8 build.py             -> build/growlanser_en.iso (tools/insert.py: text, asm/vwf.asm, signed EBOOT)
  python -X utf8 build.py --mode marker [--qa ID=TEXT].. -> build/growlanser_marker.iso ("[id] The quick..." lines)
  python -X utf8 build.py --identity  -> work/ident/identity.iso: every archive repacked with no edits; exit 1 unless
                                         its SHA-1 equals rom.sha1

Steps: check the dump (rom.sha1), unpack the ISO into work/iso/ if missing (read only, never written to), repack the
archives through their pack() (dat.py sector archives, datadat.py named archives, glb.py), copy the original ISO and
swap the files in with iso9660.patch (a file that grows moves to the end of the image).
EBOOT.BIN: code patches go into BOOT.BIN (the decrypted module) and are re-signed into EBOOT.BIN (tools/sign.py,
sign_np under WSL), never shipped as the plain ELF; --mode jp keeps the shipped EBOOT."""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import check_rom  # noqa: E402
import dat  # noqa: E402
import datadat  # noqa: E402
import glb  # noqa: E402
import iso9660  # noqa: E402

ISO = ROOT / "rom/Growlanser (Japan).iso"
TREE = ROOT / "work/iso"
G = "/PSP_GAME/USRDIR/gr_data1/"
ARCHIVES = {  # ISO path -> pack(orig_bytes, {entry: bytes})
    G + "SCEN.DAT": dat.pack,
    G + "MAP.DAT": dat.pack,
    G + "MAGD.BIN": dat.pack,
    G + "DATA.DAT": datadat.pack,
    "/PSP_GAME/USRDIR/DATA_BOOT.DAT": datadat.pack,
    G + "GLB.DAT": glb.pack,
}


def unpack():
    if not (TREE / "PSP_GAME").is_dir():
        with open(ISO, "rb") as f:
            for p, lba, ln, _ in iso9660.listing(f):
                d = TREE / p.lstrip("/")
                d.parent.mkdir(parents=True, exist_ok=True)
                f.seek(lba * 2048)
                d.write_bytes(f.read(ln))


def orig(path):
    p = TREE / path.lstrip("/")
    if not p.is_file():  # work/iso may skip big files nobody edits (VOICE.DAT)
        with open(ISO, "rb") as f:
            lba, ln = next((lba, ln) for q, lba, ln, _ in iso9660.listing(f) if q == path)
            f.seek(lba * 2048)
            return f.read(ln)
    return p.read_bytes()


def patches(edits):
    """edits: {iso_path: {entry: bytes}} -> {iso_path: new file bytes}; every archive is repacked even with no edits,
    so the identity build exercises each pack()."""
    assert not set(edits) - set(ARCHIVES), "edits for a file with no packer"
    return {p: pack(orig(p), edits.get(p, {})) for p, pack in ARCHIVES.items()}


def build(out, files):
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ISO, out)
    iso9660.patch(out, out, files)


def check_leaves(out, files, may_change):
    """Disc gate: a swapped-in file outside may_change is byte-identical to the original, only may_change files move
    or resize, and no two file extents overlap in the new image."""
    same = [p for p, d in files.items() if p not in may_change and d != orig(p)]
    with open(ISO, "rb") as f:
        old = {p: (lba, ln) for p, lba, ln, _ in iso9660.listing(f)}
    with open(out, "rb") as f:
        new = {p: (lba, ln) for p, lba, ln, _ in iso9660.listing(f)}
    moved = [p for p in new if new[p] != old.get(p) and p not in may_change]
    ext = sorted((lba, lba + -(-ln // 2048), p) for p, (lba, ln) in new.items() if ln)
    over = [(a[2], b[2]) for a, b in zip(ext, ext[1:]) if b[0] < a[1]]
    if same or moved or over or set(new) != set(old):
        raise SystemExit(f"disc gate: changed {same}, moved {moved}, overlapping {over}, "
                         f"files {sorted(set(new) ^ set(old))}")


def sha1(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha1").hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--identity", action="store_true", help="repack with no edits and compare to rom.sha1")
    ap.add_argument("--mode", choices=("en", "marker", "jp"), default="en",
                    help="text: English where translated (default), [id] markers everywhere, or the Japanese re-encoded")
    ap.add_argument("--qa", action="append", default=[], metavar="ID=TEXT", help="override one string (stress tests)")
    ap.add_argument("--qa-file", metavar="TSV", help="overrides from a file, one 'ID<tab>TEXT' per line (tools/stress.py)")
    ap.add_argument("--out", help="output ISO (default build/growlanser_<mode>.iso)")
    args = ap.parse_args()
    check_rom.check()
    unpack()
    if args.identity:
        out = ROOT / "work/ident/identity.iso"
        build(out, patches({}))
        want = next(ln for ln in (ROOT / "rom.sha1").read_text(encoding="utf-8").splitlines()
                    if ln.strip() and not ln.startswith("#")).split()[0]
        got = sha1(out)
        print(f"{out}: {got}", "identical" if got == want else f"DIFFERS (want {want})")
        sys.exit(0 if got == want else 1)
    import insert
    overrides = dict(q.split("=", 1) for q in args.qa)
    if args.qa_file:
        rows = Path(args.qa_file).read_text(encoding="utf-8").splitlines()
        overrides.update(r.split("\t", 1) for r in rows if r.strip())
    flat, edits = insert.patched(args.mode, overrides)
    if args.mode == "en":
        import gfx
        gfx.apply(flat, edits)
    out = Path(args.out) if args.out else \
        ROOT / ("build/growlanser_en.iso" if args.mode == "en" else f"build/growlanser_{args.mode}.iso")
    files = {**patches(edits), **flat}
    build(out, files)
    check_leaves(out, files, set(flat) | set(edits))
    print(f"{out}: {sha1(out)}")


if __name__ == "__main__":
    main()
