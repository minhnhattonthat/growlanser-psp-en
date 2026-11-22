"""Phase 3 identity: every archive repacks byte-identical, a grown entry shifts the rest intact, and the whole image
rebuilds to the rom.sha1 dump. Skipped without the dump (clones without rom/)."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import dat  # noqa: E402
import datadat  # noqa: E402
import glb  # noqa: E402

pytestmark = pytest.mark.skipif(not build.ISO.is_file(), reason="no dump in rom/")
READERS = {dat.pack: None, datadat.pack: datadat.entries, glb.pack: glb.entries}


@pytest.mark.parametrize("path", list(build.ARCHIVES))
def test_archive_repack(path):
    pack = build.ARCHIVES[path]
    d = build.orig(path)
    assert pack(d, {}) == d
    if pack is dat.pack:
        es = dat.entries(d)
        i = next(k for k, (s, n) in enumerate(es) if n)
        j = max(k for k, (s, n) in enumerate(es) if n)
        new = dat.pack(d, {i: dat.entry(d, i) + b"x"})
        assert dat.entries(new)[i][1] == es[i][1] + 1
        assert dat.entry(new, i)[:-2047] == dat.entry(d, i) + b"x" and dat.entry(new, j) == dat.entry(d, j)
    else:
        es = READERS[pack](d)
        n0, n9 = es[0][0], es[-1][0]
        new = pack(d, {n0: b"abc"})
        ne = READERS[pack](new)
        assert [n for n, _, _ in ne] == [n for n, _, _ in es]
        get = dict((n, new[o:o + s]) for n, o, s in ne)
        assert get[n0] == b"abc" and get[n9] == d[es[-1][1]:]


def test_iso_identity():
    r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "build.py"), "--identity"], capture_output=True,
                       text=True)
    assert r.returncode == 0 and "identical" in r.stdout, r.stdout + r.stderr
