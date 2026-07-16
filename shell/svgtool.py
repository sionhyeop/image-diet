"""이미지 -> SVG 벡터화. index.html 2949-3320,3505-3560 포팅. Pillow만 사용.

웹앱(index.html)의 알고리즘을 그대로 옮긴다:
  - quantizePalette(2949-3007)  -> _palette_from_image (팔레트 산출만 Pillow
    quantize(MEDIANCUT)로 대체 허용됨. 서브샘플링 로직은 원본 그대로 포팅했고,
    이후 픽셀별 nearest-color 배정은 원본과 동일한 가중 거리(2:4:3)로 직접 계산한다)
  - traceLoops(3008-3044)       -> _trace_loops           (그대로 포팅)
  - simplifyLoop/smoothLoopPts  -> _simplify_loop/_smooth_loop_pts (그대로 포팅)
  - dpSimplify/dpClosed(3505-)  -> _dp_simplify/_dp_closed (그대로 포팅)
  - polyArea/loopToPath/rgbHex  -> _poly_area/_loop_to_path/_rgb_hex (그대로 포팅)
  - vectorizeToSvg(3173-3282)   -> vectorize               (그대로 포팅)
  - buildSvgFromEntries(3285-)  -> _build_svg_from_entries (그대로 포팅)
"""
import math

from PIL import Image

RES = [128, 192, 320, 448, 640]
TOL = [0.3, 0.6, 1.0, 1.6, 2.4]
AREA = [0, 3, 9, 24, 60]

PRESETS = {
    "logo":   {"colors": 4,  "detail": 5, "simplify": 2, "noise": 3, "smooth": True},
    "illust": {"colors": 8,  "detail": 4, "simplify": 1, "noise": 2, "smooth": True},
    "photo":  {"colors": 16, "detail": 5, "simplify": 1, "noise": 1, "smooth": True},
}


def default_opts():
    return {"colors": 6, "detail": 3, "simplify": 2, "noise": 2, "gap": 1.0, "smooth": True}


def opts_from_controls(colors, detail, simplify, noise, gap, smooth):
    return {
        "colors": int(colors),
        "workRes": RES[int(detail) - 1],
        "tol": TOL[int(simplify)],
        "minArea": AREA[int(noise)],
        "gap": float(gap),
        "smooth": bool(smooth),
    }


# ---------------------------------------------------------------------------
# number formatting helpers (JS Math.round()/toString() 재현)
# ---------------------------------------------------------------------------

def _js_round(v):
    """JS Math.round와 동일: 0.5는 +Infinity 방향으로 반올림."""
    return math.floor(v + 0.5)


def _fmt(v, prec):
    """loopToPath()의 내부 f() 포팅. prec==1이면 정수, 아니면 소수 1자리."""
    if prec == 1:
        return str(_js_round(v))
    r = _js_round(v * 10) / 10
    s = f"{r:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    if s == "-0":
        s = "0"
    return s


def _js_num(v):
    """JS 숫자 -> 문자열(정수면 소수점 없이)."""
    if v == int(v):
        return str(int(v))
    return str(v)


# ---------------------------------------------------------------------------
# quantizePalette (2949-3007) 포팅 — 서브샘플링은 그대로, 박스분할은
# Pillow quantize(MEDIANCUT)로 대체(브리프에서 명시적으로 허용됨).
# ---------------------------------------------------------------------------

def _palette_from_image(rgba_img, n):
    w, h = rgba_img.size
    px = rgba_img.load()
    total = w * h
    # JS: step = max(1, floor((data.length/4)/60000)) * 4  (여기선 픽셀 단위로 환산)
    step = max(1, total // 60000)
    samples = []
    i = 0
    while i < total:
        x = i % w
        y = i // w
        r, g, b, a = px[x, y]
        if a >= 128:
            samples.append((r, g, b))
        i += step
    if not samples:
        return []
    n_colors = max(1, min(256, int(n), len(samples)))
    tmp = Image.new("RGB", (len(samples), 1))
    tmp.putdata(samples)
    pal_img = tmp.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
    if hasattr(pal_img, "get_flattened_data"):
        used = sorted(set(pal_img.get_flattened_data()))
    else:  # pragma: no cover - older Pillow fallback
        used = sorted(set(pal_img.getdata()))
    raw_pal = pal_img.getpalette() or []
    palette = []
    for pidx in used:
        base = pidx * 3
        if base + 2 < len(raw_pal):
            palette.append((raw_pal[base], raw_pal[base + 1], raw_pal[base + 2]))
    return palette


def _assign_indices(rgba_img, palette):
    """vectorizeToSvg(3181-3191) 픽셀별 nearest-color 배정을 그대로 포팅."""
    w, h = rgba_img.size
    px = rgba_img.load()
    idx = [-1] * (w * h)
    for y in range(h):
        row = y * w
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 128:
                continue
            best, bd = 0, float("inf")
            for c, (pr, pg, pb) in enumerate(palette):
                dr = r - pr
                dg = g - pg
                db = b - pb
                d2 = dr * dr * 2 + dg * dg * 4 + db * db * 3
                if d2 < bd:
                    bd = d2
                    best = c
            idx[row + x] = best
    return idx


def _dissolve_thin_clusters(idx, rgba_img, palette, w, h):
    """vectorizeToSvg(3192-3260) 안티앨리어싱 실금 클러스터 흡수 로직 포팅."""
    n_colors = len(palette)
    if n_colors <= 2:
        return idx
    px = rgba_img.load()
    tot = [0] * n_colors
    interior = [0] * n_colors
    for sy in range(h):
        for sx in range(w):
            sp = sy * w + sx
            me = idx[sp]
            if me < 0:
                continue
            tot[me] += 1
            if 0 < sx < w - 1 and 0 < sy < h - 1:
                same = 0
                for oy in (-1, 0, 1):
                    for ox in (-1, 0, 1):
                        if idx[sp + oy * w + ox] == me:
                            same += 1
                if same == 9:
                    interior[me] += 1
    dissolved = [False] * n_colors
    any_dissolved = False
    alive = 0
    for dc in range(n_colors):
        d = tot[dc] > 0 and (interior[dc] / tot[dc]) < 0.06 and tot[dc] < w * h * 0.2
        dissolved[dc] = d
        if d:
            any_dissolved = True
        elif tot[dc] > 0:
            alive += 1
    if not alive:
        any_dissolved = False
    if not any_dissolved:
        return idx

    idx = list(idx)
    for _pass in range(3):
        nxt = list(idx)
        changed = False
        for pp in range(len(idx)):
            cur = idx[pp]
            if cur < 0 or not dissolved[cur]:
                continue
            cx = pp % w
            cy = pp // w
            best_n, best_c = -1, 0
            votes = {}
            for vy in range(max(0, cy - 1), min(h - 1, cy + 1) + 1):
                for vx in range(max(0, cx - 1), min(w - 1, cx + 1) + 1):
                    nv = idx[vy * w + vx]
                    if nv < 0 or dissolved[nv]:
                        continue
                    votes[nv] = votes.get(nv, 0) + 1
                    if votes[nv] > best_c:
                        best_c = votes[nv]
                        best_n = nv
            if best_n >= 0:
                nxt[pp] = best_n
                changed = True
        idx = nxt
        if not changed:
            break

    for rp in range(len(idx)):
        rc = idx[rp]
        if rc < 0 or not dissolved[rc]:
            continue
        rx = rp % w
        ry = rp // w
        r, g, b, _a = px[rx, ry]
        r_best, r_bd = -1, float("inf")
        for rk in range(n_colors):
            if dissolved[rk]:
                continue
            pr, pg, pb = palette[rk]
            dr = r - pr
            dg = g - pg
            db = b - pb
            rd = 2 * dr * dr + 4 * dg * dg + 3 * db * db
            if rd < r_bd:
                r_bd = rd
                r_best = rk
        if r_best >= 0:
            idx[rp] = r_best
    return idx


# ---------------------------------------------------------------------------
# traceLoops (3008-3044) — 그대로 포팅
# ---------------------------------------------------------------------------

def _trace_loops(mask, w, h):
    w1 = w + 1
    edges = {}

    def add_edge(x1, y1, x2, y2):
        k = y1 * w1 + x1
        v = y2 * w1 + x2
        if k in edges:
            edges[k].append(v)
        else:
            edges[k] = [v]

    for y in range(h):
        row = y * w
        for x in range(w):
            if not mask[row + x]:
                continue
            if y == 0 or not mask[(y - 1) * w + x]:
                add_edge(x, y, x + 1, y)
            if x == w - 1 or not mask[row + x + 1]:
                add_edge(x + 1, y, x + 1, y + 1)
            if y == h - 1 or not mask[(y + 1) * w + x]:
                add_edge(x + 1, y + 1, x, y + 1)
            if x == 0 or not mask[row + x - 1]:
                add_edge(x, y + 1, x, y)

    loops = []
    for start_key, ends in edges.items():
        while ends:
            loop = [start_key]
            cur = ends.pop()
            broken = False
            while cur != start_key:
                loop.append(cur)
                outs = edges.get(cur)
                if not outs:
                    broken = True
                    break
                cur = outs.pop()
            if not broken and len(loop) >= 4:
                pts = [(k % w1, k // w1) for k in loop]
                loops.append(pts)
    return loops


# ---------------------------------------------------------------------------
# smoothLoopPts / simplifyLoop / dpSimplify / dpClosed — 그대로 포팅
# ---------------------------------------------------------------------------

def _smooth_loop_pts(pts):
    n = len(pts)
    if n < 8:
        return pts
    out = [None] * n
    for i in range(n):
        pm2 = pts[(i + n - 2) % n]
        pm1 = pts[(i + n - 1) % n]
        p0 = pts[i]
        pp1 = pts[(i + 1) % n]
        pp2 = pts[(i + 2) % n]
        ax, ay = p0[0] - pm2[0], p0[1] - pm2[1]
        bx, by = pp2[0] - p0[0], pp2[1] - p0[1]
        la = math.sqrt(ax * ax + ay * ay) or 1
        lb = math.sqrt(bx * bx + by * by) or 1
        cos = (ax * bx + ay * by) / (la * lb)
        if cos < 0.35:
            out[i] = p0
        else:
            out[i] = (
                (pm2[0] + pm1[0] + p0[0] + pp1[0] + pp2[0]) / 5,
                (pm2[1] + pm1[1] + p0[1] + pp1[1] + pp2[1]) / 5,
            )
    return out


def _dp_simplify(pts, tol):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        s, e = stack.pop()
        ax, ay = pts[s]
        abx, aby = pts[e][0] - ax, pts[e][1] - ay
        ab2 = (abx * abx + aby * aby) or 1
        mi, md = -1, tol * tol
        for i in range(s + 1, e):
            t = ((pts[i][0] - ax) * abx + (pts[i][1] - ay) * aby) / ab2
            t = 0 if t < 0 else (1 if t > 1 else t)
            qx = ax + t * abx - pts[i][0]
            qy = ay + t * aby - pts[i][1]
            d = qx * qx + qy * qy
            if d > md:
                md = d
                mi = i
        if mi >= 0:
            keep[mi] = True
            stack.append((s, mi))
            stack.append((mi, e))
    return [pts[j] for j in range(len(pts)) if keep[j]]


def _simplify_loop(pts, tol):
    n = len(pts)
    out = []
    for i in range(n):
        a = pts[(i + n - 1) % n]
        b = pts[i]
        c = pts[(i + 1) % n]
        if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
            continue
        out.append(b)
    out = _smooth_loop_pts(out)
    if tol <= 0 or len(out) < 5:
        return out
    far, fd = 0, -1
    for j in range(1, len(out)):
        dx = out[j][0] - out[0][0]
        dy = out[j][1] - out[0][1]
        d = dx * dx + dy * dy
        if d > fd:
            fd = d
            far = j
    h1 = _dp_simplify(out[: far + 1], tol)
    h2 = _dp_simplify(out[far:] + [out[0]], tol)
    return h1[:-1] + h2[:-1]


def _dp_closed(pts, tol):
    if tol <= 0 or len(pts) < 5:
        return pts
    far, fd = 0, -1
    for j in range(1, len(pts)):
        dx = pts[j][0] - pts[0][0]
        dy = pts[j][1] - pts[0][1]
        d = dx * dx + dy * dy
        if d > fd:
            fd = d
            far = j
    h1 = _dp_simplify(pts[: far + 1], tol)
    h2 = _dp_simplify(pts[far:] + [pts[0]], tol)
    return h1[:-1] + h2[:-1]


def _poly_area(pts):
    s = 0.0
    n = len(pts)
    for i in range(n):
        a = pts[i]
        b = pts[(i + 1) % n]
        s += a[0] * b[1] - b[0] * a[1]
    return s / 2


# ---------------------------------------------------------------------------
# loopToPath / rgbHex — 그대로 포팅
# ---------------------------------------------------------------------------

def _loop_to_path(pts, smooth, prec):
    def f(v):
        return _fmt(v, prec)

    if not smooth or len(pts) < 4:
        d = f"M{f(pts[0][0])} {f(pts[0][1])}"
        for p in pts[1:]:
            d += f"L{f(p[0])} {f(p[1])}"
        return d + "Z"

    n = len(pts)
    sharp = [False] * n
    for i in range(n):
        pa = pts[(i + n - 1) % n]
        pv = pts[i]
        pcn = pts[(i + 1) % n]
        ax, ay = pv[0] - pa[0], pv[1] - pa[1]
        bx, by = pcn[0] - pv[0], pcn[1] - pv[1]
        la = math.sqrt(ax * ax + ay * ay) or 1
        lb = math.sqrt(bx * bx + by * by) or 1
        sharp[i] = (ax * bx + ay * by) / (la * lb) < 0.3

    def tangent(vi):
        if sharp[vi]:
            return [0.0, 0.0]
        p0 = pts[(vi + n - 1) % n]
        p2 = pts[(vi + 1) % n]
        return [(p2[0] - p0[0]) / 6, (p2[1] - p0[1]) / 6]

    d = f"M{f(pts[0][0])} {f(pts[0][1])}"
    for i in range(n):
        p1 = pts[i]
        p2b = pts[(i + 1) % n]
        seg_len = math.sqrt((p2b[0] - p1[0]) ** 2 + (p2b[1] - p1[1]) ** 2) or 1
        t1 = tangent(i)
        t2 = tangent((i + 1) % n)
        m1 = math.sqrt(t1[0] * t1[0] + t1[1] * t1[1])
        if m1 > seg_len / 2:
            t1[0] *= seg_len / 2 / m1
            t1[1] *= seg_len / 2 / m1
        m2 = math.sqrt(t2[0] * t2[0] + t2[1] * t2[1])
        if m2 > seg_len / 2:
            t2[0] *= seg_len / 2 / m2
            t2[1] *= seg_len / 2 / m2
        d += (
            f"C{f(p1[0] + t1[0])} {f(p1[1] + t1[1])} "
            f"{f(p2b[0] - t2[0])} {f(p2b[1] - t2[1])} {f(p2b[0])} {f(p2b[1])}"
        )
    return d + "Z"


def _rgb_hex(c):
    return "#" + "".join(f"{int(v) & 0xFF:02x}" for v in c)


# ---------------------------------------------------------------------------
# buildSvgFromEntries (3285-3308) — 그대로 포팅
# ---------------------------------------------------------------------------

def _build_svg_from_entries(entries, w, h, sw, sh, smooth, prec, stroke_w):
    if stroke_w is None:
        stroke_w = 1
    paths = []
    for e in entries:
        d = ""
        for pts in e["loops"]:
            d += _loop_to_path(pts, smooth, prec)
        if d:
            color = _rgb_hex([_js_round(e["color"][0]), _js_round(e["color"][1]), _js_round(e["color"][2])])
            paths.append({"color": color, "d": d, "area": e["count"]})
    paths.sort(key=lambda p: -p["area"])
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{sw}" height="{sh}">'
    ]
    for pp in paths:
        stroke_attr = (
            f' stroke="{pp["color"]}" stroke-width="{_js_num(stroke_w)}" stroke-linejoin="round"'
            if stroke_w > 0
            else ""
        )
        lines.append(f'  <path fill="{pp["color"]}"{stroke_attr} fill-rule="evenodd" d="{pp["d"]}"/>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# vectorizeToSvg (3173-3282) — 그대로 포팅
# ---------------------------------------------------------------------------

def vectorize(img, opts):
    rgba = img.convert("RGBA")
    sw, sh = rgba.size
    if not sw or not sh:
        sw = sw or 512
        sh = sh or 512
    scale = min(1, opts["workRes"] / max(sw, sh))
    w = max(1, _js_round(sw * scale))
    h = max(1, _js_round(sh * scale))
    if (w, h) != rgba.size:
        work = rgba.resize((w, h), Image.LANCZOS)
    else:
        work = rgba

    palette = _palette_from_image(work, opts["colors"])
    if not palette:
        raise ValueError("이미지에서 색을 찾지 못했어요.")

    idx = _assign_indices(work, palette)
    idx = _dissolve_thin_clusters(idx, work, palette, w, h)

    entries = []
    for pc in range(len(palette)):
        mask = [1 if v == pc else 0 for v in idx]
        count = sum(mask)
        if not count:
            continue
        loops = _trace_loops(mask, w, h)
        keep = []
        for loop in loops:
            pts = _simplify_loop(loop, opts["tol"])
            if len(pts) < 3:
                continue
            if abs(_poly_area(pts)) < opts["minArea"]:
                continue
            keep.append(pts)
        if keep:
            entries.append({"color": list(palette[pc]), "loops": keep, "count": count})

    if not entries:
        raise ValueError(
            "추적할 만한 색 면을 찾지 못했어요. 추적 정밀도를 높이거나 잡티 제거를 낮춰 보세요."
        )

    svg = _build_svg_from_entries(entries, w, h, sw, sh, opts["smooth"], 0, opts["gap"])
    return svg
