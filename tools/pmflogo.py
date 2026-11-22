"""pmflogo.py: P9, drop the katakana subtitle グローランサー under the GROWLANSER logo in op1.pmf / op2.pmf (D5, D15;
the PS1 G8 fix, ../growlanser-en/tools/fmvlogo.py, ported to PSMF).

The logo shows twice per movie (over clouds, then a zoom into white; and at the end). The video is H.264 Main
(CABAC, 1 ref, P only, poc type 2, AUD + SEI per frame) in MPEG-PS packs. Only the GOPs (IDR to IDR) that hold logo
frames are touched: their frames are decoded, cleaned (fmvlogo's mask + fill), re-encoded with x264 and each new
slice is put back into the original access unit, keeping its AUD / SPS / PPS / SEI and its exact byte size (filler
NAL + zero bytes). So every PES header, PTS and audio packet stays as it was. The x264 slice headers are rewritten
for the original SPS/PPS (frame_num bits, pic_init_qp 26, no deblocking-control fields).

    python -X utf8 tools/pmflogo.py build          -> work/pmf/en/op1.pmf, op2.pmf (+ before/after pngs)
patched() returns {iso path: bytes} for build.py (cached by the source hash in work/pmf/en).
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "work/iso/PSP_GAME/USRDIR"
OUT = ROOT / "work/pmf/en"
W, H = 480, 272
MOVIES = ("op1.pmf", "op2.pmf")
# from fmvlogo.py (PS1): subtitle x0, x1 (from the bar line's left end) and bottom (below the bar), per unit of
# line length, with the hero figure (first logo) and without (end logo)
FIGURE = (21 / 175, 85 / 175, 11 / 175)
PLAIN = (2 / 190, 72 / 190, 13 / 190)
PAD = 2
DARK = 110
# the logo spans (frame a..b-1; a full scan of the red bar also hits fire and red hair, so only these are cleaned)
WINDOWS = {"op1.pmf": [(1500, 1650, FIGURE), (3020, 3120, PLAIN)],
           "op2.pmf": [(1515, 1654, FIGURE), (3035, 3165, PLAIN)]}  # op2 1654 = the cut to Melfie


# ---- subtitle mask + fill (fmvlogo.py) ----
def redness(a):
    return a[:, :, 0] - (a[:, :, 1] + a[:, :, 2]) / 2


def barline(red, t):
    """(length, y, left, right) of the longest run of red > t in any row."""
    best = (0, 0, 0, 0)
    for y in range(red.shape[0]):
        r = np.concatenate(([0], (red[y] > t).astype(np.int8), [0]))
        d = np.diff(r)
        s, e = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        if len(s):
            k = (e - s).argmax()
            if e[k] - s[k] > best[0]:
                best = (e[k] - s[k], y, s[k], e[k] - 1)
    return best


def subtitle_rect(red, rel):
    h, w = red.shape
    t = 40
    n, y, left, right = barline(red, t)
    if n < 150:
        t = 8
        n, y, left, right = barline(red, t)
        if n < 150:
            return None
    bottom = y
    while bottom + 1 < h and (red[bottom + 1, left:right + 1] > t).sum() > .8 * (right - left):
        bottom += 1
    if left > 0 and right < w - 1:
        width = right - left
        x0, x1 = left + rel[0] * width, left + rel[1] * width
        y0, y1 = bottom + 1, bottom + rel[2] * width
    else:  # zoomed past the screen edges: the reddish pixels below the bar, left of the middle
        ys, xs = (red[bottom + 2:, : w // 2 + 60] > 6).nonzero()
        if not len(ys):
            return None
        x0, x1, y0, y1 = xs.min(), xs.max(), bottom + 1, ys.max() + bottom + 2
    x0, y0 = max(0, int(x0)), int(y0)
    x1, y1 = min(w - 1, int(x1 + .5) + PAD), min(h - 1, int(y1 + .5) + PAD)
    return x0, y0, x1, y1


def inpaint(a, mask, block, iters=20):
    out = a.astype(float).copy()
    src = ~mask & ~block
    for y in np.nonzero(mask.any(1))[0]:
        m = np.nonzero(mask[y])[0]
        xs = [x for x in range(m.max() + 1, min(m.max() + 25, mask.shape[1])) if src[y, x]]
        if not xs:
            xs = [x for x in range(max(0, m.min() - 24), m.min()) if src[y, x]]
        if xs:
            out[y, m] = np.median(out[y, xs], 0)
    w = (~block).astype(float)
    for _ in range(iters):
        p = np.pad(out * w[:, :, None], ((1, 1), (1, 1), (0, 0)), mode="edge")
        q = np.pad(w, 1, mode="edge")
        n = q[:-2, 1:-1] + q[2:, 1:-1] + q[1:-1, :-2] + q[1:-1, 2:]
        s = p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
        out[mask] = (s / np.maximum(n, 1)[:, :, None])[mask]
    return out.clip(0, 255).astype("uint8")


def clean(a, rel):
    """(edited RGB array, rect or None)."""
    red = redness(a.astype(int))
    rect = subtitle_rect(red, rel)
    if rect is None:
        return a, None
    x0, y0, x1, y1 = rect
    mask = np.zeros(red.shape, bool)
    lum = a.astype(int).mean(2)
    for y in range(y0, y1 + 1):
        sl = slice(x1 + 1, x1 + 25) if x1 + 1 < red.shape[1] else slice(max(0, x0 - 24), x0)
        base = max(0.0, float(np.median(red[y, sl]))) if red[y, sl].size else 0.0
        lbase = float(np.median(lum[y, sl])) if lum[y, sl].size else 255.0
        row, lrow = red[y, x0:x1 + 1], lum[y, x0:x1 + 1]
        mask[y, x0:x1 + 1] = (row > base + 8) | ((lrow < lbase - 20) & (lrow > DARK))
    box = np.zeros_like(mask)
    box[y0:y1 + 1, x0:x1 + 1] = True
    for _ in range(2):
        m = mask.copy()
        m[1:] |= mask[:-1]
        m[:-1] |= mask[1:]
        m[:, 1:] |= mask[:, :-1]
        m[:, :-1] |= mask[:, 1:]
        mask = m & box
    if not mask.any():
        return a, None
    block = ((red > 40) | (lum <= DARK)) & ~mask
    return inpaint(a, mask, block), rect


# ---- PSMF / MPEG-PS ----
def video_es(data):
    """(ES bytes, [(es offset, file offset, length)]) of the video PES (0xE0) payloads."""
    p = int.from_bytes(data[8:12], "big")
    end = p + int.from_bytes(data[12:16], "big")
    es, runs = bytearray(), []
    while p < end:
        assert data[p:p + 3] == b"\0\0\1", hex(p)
        sid = data[p + 3]
        if sid == 0xBA:
            p += 14 + (data[p + 13] & 7)
            continue
        if sid == 0xB9:
            p += 4
            continue
        n = int.from_bytes(data[p + 4:p + 6], "big")
        if sid == 0xE0:
            q = p + 9 + data[p + 8]
            runs.append((len(es), q, p + 6 + n - q, data[p + 7] >> 7))  # .., has a PTS
            es += data[q:p + 6 + n]
        p += 6 + n
    return bytes(es), runs


def put_es(data, runs, off, new):
    """Write new over ES bytes [off, off + len(new)) in the file."""
    for e, f, n, _ in runs:
        a, b = max(off, e), min(off + len(new), e + n)
        if a < b:
            data[f + a - e:f + b - e] = new[a - off:b - off]


def nals(buf):
    """[(start of start code, start of NAL header, end)] in an Annex B buffer."""
    out, i = [], 0
    while True:
        j = buf.find(b"\0\0\1", i)
        if j < 0:
            break
        s = j - 1 if j > 0 and buf[j - 1] == 0 else j
        out.append([s, j + 3, None])
        i = j + 3
    for k in range(len(out)):
        e = out[k + 1][0] if k + 1 < len(out) else len(buf)
        while e > out[k][1] and buf[e - 1] == 0:  # trailing zero bytes
            e -= 1
        out[k][2] = e
    return [tuple(x) for x in out]


def access_units(es):
    """ES offsets of each AU (AUD NAL starts), plus len(es)."""
    starts = [s for s, h, e in nals(es) if es[h] & 0x1F == 9]
    return starts + [len(es)]


def unescape(b):
    out, z = bytearray(), 0
    for x in b:
        if z >= 2 and x == 3:
            z = 0
            continue
        out.append(x)
        z = z + 1 if x == 0 else 0
    return bytes(out)


def escape(b):
    out, z = bytearray(), 0
    for x in b:
        if z >= 2 and x <= 3:
            out.append(3)
            z = 0
        out.append(x)
        z = z + 1 if x == 0 else 0
    return bytes(out)


class Bits:
    def __init__(self, b):
        self.b, self.p = b, 0

    def u(self, n):
        v = 0
        for _ in range(n):
            v = v << 1 | (self.b[self.p >> 3] >> (7 - (self.p & 7))) & 1
            self.p += 1
        return v

    def ue(self):
        z = 0
        while not self.u(1):
            z += 1
        return (1 << z) - 1 + self.u(z)

    def se(self):
        v = self.ue()
        return (v + 1) // 2 if v & 1 else -(v // 2)


class Out:
    def __init__(self):
        self.bits = []

    def u(self, n, v):
        self.bits += [(v >> (n - 1 - i)) & 1 for i in range(n)]

    def ue(self, v):
        v += 1
        n = v.bit_length()
        self.u(n - 1, 0)
        self.u(n, v)

    def se(self, v):
        self.ue(2 * v - 1 if v > 0 else -2 * v)


def x264_params(sps, pps):
    """The fields of x264's SPS / PPS the slice header needs."""
    r = Bits(unescape(sps[1:]))
    profile = r.u(8)
    r.u(16)
    r.ue()
    assert profile == 77, profile
    fn_bits = r.ue() + 4
    assert r.ue() == 2, "poc type"
    r = Bits(unescape(pps[1:]))
    r.ue(), r.ue()
    assert r.u(1) == 1, "CABAC"
    r.u(1)
    assert r.ue() == 0
    ref_l0 = r.ue() + 1
    r.ue()
    assert r.u(1) == 0 and r.u(2) == 0, "weighted pred"
    init_qp = 26 + r.se()
    r.se()
    assert r.se() == 0, "chroma_qp_index_offset"
    deblock_ctl = r.u(1)
    assert r.u(1) == 0 and r.u(1) == 0
    return fn_bits, ref_l0, init_qp, deblock_ctl


def rewrite_slice(nal, xp, op, frame_num, idr_pic_id):
    """An x264 slice NAL -> the same slice for the original SPS/PPS (op = x264_params of the GOP's own IDR AU: the
    movies change pic_init_qp from GOP to GOP)."""
    fn_bits, ref_l0, init_qp, deblock_ctl = xp
    o_fn_bits, o_ref_l0, o_init_qp, o_deblock_ctl = op
    hdr = nal[0]
    idr = hdr & 0x1F == 5
    r = Bits(unescape(nal[1:]))
    o = Out()
    assert r.ue() == 0, "one slice per picture"
    o.ue(0)
    st = r.ue()
    o.ue(st)
    assert st % 5 in (0, 2), st  # P or I
    o.ue(r.ue())  # pps id
    r.u(fn_bits)
    o.u(o_fn_bits, frame_num % (1 << o_fn_bits))
    if idr:
        r.ue()
        o.ue(idr_pic_id)
    if st % 5 == 0:
        ov = r.u(1)
        n = r.ue() + 1 if ov else ref_l0
        assert n == 1, "one ref"
        o.u(1, int(o_ref_l0 != 1))
        if o_ref_l0 != 1:
            o.ue(0)
        assert r.u(1) == 0, "ref list modification"
        o.u(1, 0)
    if idr:
        o.u(1, r.u(1))
        o.u(1, r.u(1))
    else:
        assert r.u(1) == 0, "adaptive ref pic marking"
        o.u(1, 0)
    if st % 5 != 2:
        o.ue(r.ue())  # cabac_init_idc
    o.se(init_qp + r.se() - o_init_qp)
    if deblock_ctl:
        assert r.ue() == 0 and r.se() == 0 and r.se() == 0, "default deblocking"
    if o_deblock_ctl:
        o.ue(0), o.se(0), o.se(0)
    while r.p & 7:
        assert r.u(1) == 1
    o.bits += [1] * (-len(o.bits) % 8)
    head = bytes(int("".join(map(str, o.bits[i:i + 8])), 2) for i in range(0, len(o.bits), 8))
    return bytes([hdr]) + escape(head + r.b[r.p >> 3:])


def filler(n):
    """Exactly n bytes to pad an AU: a filler NAL (type 12) and / or trailing zero bytes."""
    if n < 6:
        return b"\0" * n
    return b"\0\0\1\x0c" + b"\xff" * (n - 5) + b"\x80"


# ---- frames ----
def decode(path, a, b):
    """RGB frames a..b-1."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v", "-vf",
                          f"select='between(n\\,{a}\\,{b - 1})'", "-fps_mode", "passthrough", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    assert len(f) == b - a, (len(f), a, b)
    return f


def encode(frames, qps):
    """x264 Annex B for the frames at the given per-frame QPs: one IDR then P, 1 ref, CABAC, Main 2.1, full range."""
    (OUT / "qp.txt").write_text("".join(f"{k} {'I' if k == 0 else 'P'} {q}\n" for k, q in enumerate(qps)))
    p = ("psy=0:chroma-qp-offset=0:weightp=0:aud=1:keyint=9999:min-keyint=9999:scenecut=0:bframes=0:ref=1:"
         f"8x8dct=0:slices=1:deblock=0,0:qp={qps[0]}:qpfile=qp.txt")
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r",
                        "30000/1001", "-i", "-", "-c:v", "libx264", "-profile:v", "main", "-level", "2.1",
                        "-pix_fmt", "yuvj420p", "-x264-params", p, "-f", "h264", "-"], cwd=OUT,
                       input=np.ascontiguousarray(frames).tobytes(), capture_output=True, check=True)
    return r.stdout


def fit_gop(es, au, runs, g, end, frames):
    """The lowest even QP (one for the whole GOP) whose AUs fit build_gop's layout; (GOP bytes, QP)."""
    cons = pts_starts(runs, au, g, end)
    for q in range(20, 52, 2):
        new = build_gop(es, au, g, end, encode(frames, [q] * (end - g)), cons)
        if new:
            return new, q
    raise SystemExit(f"GOP {g}-{end} does not fit at QP 50")


def pts_starts(runs, au, g, end):
    """{k: (a, b)}: AU g+k is the first AU starting in a PES packet with a PTS (ES bytes a..b-1), so it must still
    start there; every other AU boundary is free (the decoder finds AUs by their AUD)."""
    cons = {}
    for e, f, n, pts in runs:
        if pts and au[g] <= e + n and e < au[end]:
            k = next(i for i in range(len(au)) if au[i] >= e)
            assert au[k] < e + n, "a PTS packet with no AU start"
            if g < k < end:
                cons[k - g] = (e, e + n)
    return cons


def patch_movie(name, log):
    data = bytearray((SRC / name).read_bytes())
    es, runs = video_es(data)
    au = access_units(es)
    n = len(au) - 1
    idr = [k for k in range(n) if any(b[h] & 0x1F == 5 for b in [es[au[k]:au[k + 1]]] for s, h, e in nals(b))]
    gops = sorted({max(i for i in idr if i <= f) for a, b, _ in WINDOWS[name] for f in range(a, b)})
    log[name] = {"frames": n}
    edited = {}
    for g in gops:
        end = min([i for i in idr if i > g] + [n])
        frames = decode(SRC / name, g, end).copy()
        rects = {}
        for k in range(len(frames)):
            win = [rel for a, b, rel in WINDOWS[name] if a <= g + k < b]
            if win:
                frames[k], rect = clean(frames[k], win[0])
                if rect:
                    rects[g + k] = rect
        if not rects:
            continue
        new, qp = fit_gop(es, au, runs, g, end, frames)
        put_es(data, runs, au[g], new)
        edited[g] = {"end": end, "rects": len(rects), "qp": qp}
        before = decode(SRC / name, g, end)
        for k in sorted(rects)[:: max(1, len(rects) // 4)]:
            from PIL import Image
            Image.fromarray(np.concatenate([before[k - g], frames[k - g]], 1)).save(OUT / f"{name[:-4]}_{k:04d}.png")
    log[name]["gops"] = edited
    return bytes(data)


def build_gop(es, au, g, end, h264, cons):
    """Original AUs g..end-1 with x264's slices (AUD / SPS / PPS / SEI kept), laid out in the original GOP's bytes
    with each pts_starts AU still in its packet; padding = filler NAL / zero bytes. None if it does not fit."""
    xn = nals(h264)
    sps = next(h264[h:e] for s, h, e in xn if h264[h] & 0x1F == 7)
    pps = next(h264[h:e] for s, h, e in xn if h264[h] & 0x1F == 8)
    xp = x264_params(sps, pps)
    j = g  # the active SPS / PPS: the last AU up to g that carries them (some IDRs repeat none)
    while not any(es[au[j]:au[j + 1]][h] & 0x1F == 8 for s, h, e in nals(es[au[j]:au[j + 1]])):
        j -= 1
    o = es[au[j]:au[j + 1]]
    op = x264_params(*(next(o[h:e] for s, h, e in nals(o) if o[h] & 0x1F == t) for t in (7, 8)))
    slices = [h264[h:e] for s, h, e in xn if h264[h] & 0x1F in (1, 5)]
    assert len(slices) == end - g, (len(slices), g, end)
    out = bytearray()
    for k, sl in enumerate(slices):
        orig = es[au[g + k]:au[g + k + 1]]
        on = nals(orig)
        oslice = [x for x in on if orig[x[1]] & 0x1F in (1, 5)]
        assert len(oslice) == 1
        s0, h0, e0 = oslice[0]
        idr_pic_id = 0
        if orig[h0] & 0x1F == 5:
            r = Bits(unescape(orig[h0 + 1:e0]))
            r.ue(), r.ue(), r.ue(), r.u(op[0])
            idr_pic_id = r.ue()
        else:
            assert not any(orig[h] & 0x1F in (7, 8) for s, h, e in on), "parameter sets only in the IDR AU"
        assert (sl[0] & 0x1F == 5) == (k == 0)
        assert not orig[e0:].strip(b"\0"), "the slice ends the AU"
        pos = au[g] + len(out)
        nxt = min((c for c in cons if c >= k), default=None)
        if nxt == k:
            a, b = cons[k]
            if pos >= b:
                return None
            out += filler(max(0, a - pos))  # pads the previous AU up to the packet
        elif nxt is not None and pos >= cons[nxt][0]:
            return None  # would become the first AU of a later PTS packet
        out += orig[:s0] + b"\0\0\1" + rewrite_slice(sl, xp, op, k, idr_pic_id)
    pad = au[end] - au[g] - len(out)
    if pad < 0:
        return None
    out += filler(pad)
    return bytes(out)


def src_hash():
    h = hashlib.sha1(Path(__file__).read_bytes())
    for m in MOVIES:
        h.update((SRC / m).read_bytes())
    return h.hexdigest()


def verify(m, gops):
    """The patched movie decodes with no error, has the same frame count, and differs only inside edited GOPs."""
    def dec(path):
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v", "-f", "rawvideo", "-pix_fmt",
                            "gray", "-"], capture_output=True)
        return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W), r.stderr.decode()
    a, _ = dec(SRC / m)
    b, err = dec(OUT / m)
    assert not err.strip(), f"{m}: {err[:500]}"
    assert len(a) == len(b), (m, len(a), len(b))
    out = [k for k in range(len(a)) if (a[k] != b[k]).any() and not any(int(g) <= k < v["end"] for g, v in gops.items())]
    assert not out, f"{m}: frames outside the edited GOPs changed: {out[:10]}"


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    log = {}
    for m in MOVIES:
        (OUT / m).write_bytes(patch_movie(m, log))
        verify(m, log[m]["gops"])
    log["hash"] = src_hash()
    (OUT / "log.json").write_text(json.dumps(log, indent=1))
    print(json.dumps({m: log[m]["gops"] for m in MOVIES}))


def patched():
    log = OUT / "log.json"
    if not log.exists() or json.loads(log.read_text()).get("hash") != src_hash():
        build()
    return {f"/PSP_GAME/USRDIR/{m}": (OUT / m).read_bytes() for m in MOVIES}


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]:
        build()
    else:
        sys.exit(__doc__)
