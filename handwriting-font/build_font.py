"""칸별 잉크 PNG들 -> 손글씨 폰트(.ttf).
사용: python3 -I build_font.py <cells폴더> <출력.ttf> [폰트이름]
cells폴더 안의 p*_cells.json 을 모두 읽는다(여러 쪽 지원)."""
import sys, os, json, glob, re
import numpy as np, cv2, potrace
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen

UP = 4            # 윤곽 따기 전 확대 배율
BOX_PX = 210      # 쓰는 칸 한 변(px) = 폰트 1000단위
K = 1000 / BOX_PX
HANGUL_H = 700    # 한글 글자 높이 목표(단위)
DIGIT_H = 640     # 숫자·영문 높이 목표(대문자 높이쯤)
MAX_SCALE = 2.6
BOLD_PX = 5       # 윤곽 따기 전 살짝 굵게(확대 이미지 기준 px)

UPK = K / UP      # 확대 이미지 1px = 폰트 몇 단위
SKIP_EQ = set(".,:;'\"")   # 너무 작아서 깎으면 사라질 기호는 굵기 보정에서 뺀다
EQ_R_MIN, EQ_R_MAX = -12, 12  # 확대 이미지 기준 깎기/부풀리기 한도(px)

def prep_mask(png):
    ink = cv2.imread(png, 0)
    if ink is None or (ink > 0).sum() < 3: return None
    big = cv2.resize(ink, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), 1.6)
    return (big > 110).astype(np.uint8) * 255

def offset_mask(big, r):
    """r>0: 부풀리기(굵게), r<0: 깎기(가늘게). 단위는 확대 이미지 px."""
    if r == 0: return big
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*abs(r)+1,)*2)
    return cv2.dilate(big, k) if r > 0 else cv2.erode(big, k)

def stroke_w(mask):
    """획 굵기 추정(px): 획 중심선 위 거리변환값의 중간값 x 2"""
    dt = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    mx = cv2.dilate(dt, np.ones((3, 3), np.float32))
    ridge = (dt >= mx - 1e-6) & (dt > 1.0)
    return 2 * float(np.median(dt[ridge])) if ridge.any() else None

def trace_mask(big, margin):
    if big is None or (big > 0).sum() < 3: return None
    pl = potrace.Bitmap(255 - big).trace(turdsize=3, alphamax=1.1, opticurve=True, opttolerance=0.3)
    conv = lambda p: ((p.x / UP - margin) * K, (margin + BOX_PX - p.y / UP) * K - 200)  # 칸 -> 폰트좌표
    contours = []
    for curve in pl:
        segs = [("M", conv(curve.start_point))]
        for s in curve.segments:
            if s.is_corner: segs += [("L", conv(s.c)), ("L", conv(s.end_point))]
            else: segs.append(("C", conv(s.c1), conv(s.c2), conv(s.end_point)))
        contours.append(segs)
    return contours or None

def bbox(contours):
    pts = [p for c in contours for s in c for p in s[1:]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

def transform(contours, fx):
    return [[(s[0],) + tuple(fx(*p) for p in s[1:]) for s in c] for c in contours]

CONS = "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ"
BLEND = 0.85   # 높이 차이를 줄이는 정도(1이면 완전히 같게, 0이면 그대로)

def fit_height(cs, target, center, max_w=980):
    """글자 높이를 target 쪽으로 맞추고 세로 중심을 center에 둔다(가로폭은 max_w 넘지 않게)."""
    x0, y0, x1, y1 = bbox(cs); h = max(y1 - y0, 1); w = max(x1 - x0, 1)
    k = 1 + BLEND * (target / h - 1)
    k = max(0.6, min(1.6, k, max_w / w))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return transform(cs, lambda x, y: ((x - cx) * k + cx, (y - cy) * k + center))

SYL_W = 720          # 한글 글자 폭 목표(현재 중간값 ~723)
BLEND_TALL = 0.6     # 키 큰 글자(좋·을·를 등)는 덜 줄인다
MAX_STRETCH = 1.3    # 좁은 글자를 가로로 늘리는 최대 배율
BLEND_W = 0.8

def fit_syllable(cs, target_h, center, target_w=SYL_W, max_w=980):
    """한글 글자: 높이는 target_h 쪽으로(키 큰 글자는 덜), 좁은 글자는 가로로 넓혀 폭을 target_w 쪽으로 맞춘다."""
    x0, y0, x1, y1 = bbox(cs); h = max(y1 - y0, 1); w = max(x1 - x0, 1)
    ky = 1 + (BLEND if h <= target_h else BLEND_TALL) * (target_h / h - 1)
    ky = max(0.6, min(1.6, ky))
    kx = ky
    if w * ky < target_w:
        kx = ky * min(MAX_STRETCH, 1 + BLEND_W * (target_w / (w * ky) - 1))
    kx = min(kx, max_w / w)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return transform(cs, lambda x, y: ((x - cx) * kx + cx, (y - cy) * ky + center))

def fit_digit(cs, target):
    """숫자 높이를 맞추고 바닥을 기준선(y=0)에 앉힌다."""
    x0, y0, x1, y1 = bbox(cs); h = max(y1 - y0, 1)
    k = max(0.6, min(1.6, 1 + BLEND * (target / h - 1)))
    return transform(cs, lambda x, y: (x * k, (y - y0) * k))

# 기호가 놓일 높이(숫자 높이 DIGIT_H의 비율). c=세로 중심, b=아래끝, t=위끝
SYM_ANCHOR = {"-": ("c", 0.42), "~": ("c", 0.55), "(": ("c", 0.40), ")": ("c", 0.40), "/": ("c", 0.40),
              ".": ("b", 0.0), ",": ("t", 0.15), ":": ("b", 0.0), ";": ("b", -0.12),
              "'": ("t", 1.0), '"': ("t", 1.0), "^": ("t", 1.0),
              "_": ("c", -0.12), "`": ("t", 1.0), "*": ("t", 1.0),
              "+": ("c", 0.45), "=": ("c", 0.45), "<": ("c", 0.45), ">": ("c", 0.45),
              "[": ("c", 0.40), "]": ("c", 0.40), "{": ("c", 0.40), "}": ("c", 0.40), "|": ("c", 0.40), "\\": ("c", 0.40)}

# 영문 글자 종류별 높이 규칙(DIGIT_H에 대한 비율). 바닥은 바닥선(y=0)에 앉힌다.
FIT_H = {c: 1.0 for c in "ABCDEFGHIKLMNOPRSTUVWXYZbdfhkli#$%&@"}
FIT_H.update({"t": 0.85}); FIT_H.update({c: 0.70 for c in "acemnorsuvwxz"})
TOP_ANCHOR = {"g": 0.70, "p": 0.70, "q": 0.70, "y": 0.70, "j": 1.0, "J": 1.0, "Q": 1.0}  # 윗선 맞춤(꼬리는 아래로)

# 템플릿에서 새로 쓴 기호: 가장 긴 변이 DIGIT_H 의 몇 배가 되게 맞춘다(화살표처럼 납작한 기호도 크기가 폭주하지 않게)
NEWSYM_MAX = {"₩": 0.95, "…": 0.55, "★": 0.95, "☆": 0.95, "→": 0.95, "←": 0.95, "↑": 0.95, "↓": 0.95, "♪": 0.9, "※": 0.85, "×": 0.7, "÷": 0.7, "°": 0.3}
SYM_ANCHOR.update({"₩": ("b", 0.0), "…": ("b", 0.0), "★": ("c", 0.5), "☆": ("c", 0.5), "→": ("c", 0.5), "←": ("c", 0.5), "↑": ("c", 0.5), "↓": ("c", 0.5),
                   "♪": ("c", 0.5), "※": ("c", 0.5), "×": ("c", 0.42), "÷": ("c", 0.42), "°": ("t", 1.0)})

def fit_max(cs, target):
    x0, y0, x1, y1 = bbox(cs); k = target / max(x1 - x0, y1 - y0, 1)
    return transform(cs, lambda x, y: ((x - x0) * k + x0, (y - y0) * k + y0))

def place_symbol(cs, ch):
    mode, r = SYM_ANCHOR[ch]; target = r * DIGIT_H
    x0, y0, x1, y1 = bbox(cs)
    cur = {"c": (y0 + y1) / 2, "b": y0, "t": y1}[mode]
    return transform(cs, lambda x, y: (x, y + target - cur))

def to_glyph(contours):
    rec = RecordingPen()
    for c in contours:
        rec.moveTo(c[0][1])
        for s in c[1:]:
            if s[0] == "L": rec.lineTo(s[1])
            else: rec.curveTo(s[1], s[2], s[3])
        rec.closePath()
    # 바깥 윤곽이 시계방향이 되도록(TrueType 규칙)
    best, area_best = None, 0
    for c in contours:
        pts = [c[0][1]] + [s[-1] for s in c[1:]]
        a = sum(x1*y2 - x2*y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / 2
        if abs(a) > abs(area_best): area_best = a
    pen = TTGlyphPen(None)
    target = ReverseContourPen(Cu2QuPen(pen, 1.0)) if area_best > 0 else Cu2QuPen(pen, 1.0)
    rec.replay(target)
    return pen.glyph()

def finalize(ch, kind, cs, s_h, s_l):
    """윤곽(칸 좌표) -> 최종 글자 모양과 폭. 크기·높이·위치 규칙은 전부 여기."""
    if kind == "latin":
        s = s_l
        cs = transform(cs, lambda x, y: (x * s, y * s))            # 바닥선(y=0) 기준 확대
        if ch in "0123456789!?": cs = fit_digit(cs, DIGIT_H)
        elif ch in FIT_H: cs = fit_digit(cs, DIGIT_H * FIT_H[ch])
        elif ch in TOP_ANCHOR:
            ymax_ = bbox(cs)[3]; cs = transform(cs, lambda x, y: (x, y + TOP_ANCHOR[ch] * DIGIT_H - ymax_))
        elif ch in NEWSYM_MAX: cs = place_symbol(fit_max(cs, NEWSYM_MAX[ch] * DIGIT_H), ch)
        elif ch in SYM_ANCHOR: cs = place_symbol(cs, ch)
        xmin, _, xmax, _ = bbox(cs)
        cs = transform(cs, lambda x, y: (x - xmin + 70, y))
        adv = max(260, int(xmax - xmin + 140))
    else:
        s = s_h
        cs = transform(cs, lambda x, y: ((x - 500) * s + 500, (y - 300) * s + 330))  # 칸 중심 기준 확대
        if kind == "hangul": cs = fit_syllable(cs, HANGUL_H, 330)
        elif ch in CONS: cs = fit_height(cs, HANGUL_H * 0.90, 350)
        else:
            _, y0_, _, y1_ = bbox(cs); cs = transform(cs, lambda x, y: (x, y - (y0_ + y1_) / 2 + 350))
        xmin, _, xmax, _ = bbox(cs)
        w = xmax - xmin
        adv = max(1000, int(w + 90)) if kind == "hangul" else max(520, int(w + 140))
        dx = (adv - w) / 2 - xmin
        cs = transform(cs, lambda x, y: (x + dx, y))
    return cs, adv

def main(cells_dir, out_ttf, family="MyHand", equal=True):
    virt_set = set()   # 조합으로 만든 가상 칸(크기 기준 계산에서 제외)
    loaded = {}   # 글자 -> (글자, 종류, 확대 마스크, 여백px). 같은 글자가 여러 쪽에 있으면 나중 쪽이 앞 쪽을 덮어쓴다(다시 쓴 글자 반영)
    page_no = lambda p: int(re.search(r"p(\d+)_cells", os.path.basename(p)).group(1))
    redone = []
    for jf in sorted(glob.glob(os.path.join(cells_dir, "p*_cells.json")), key=page_no):
        for m in json.load(open(jf)):
            path = os.path.join(cells_dir, m["file"])
            if m.get("ink_px", 3) < 3: continue                      # 잉크가 없는 칸은 건너뜀
            if m["char"] in loaded: redone.append(m["char"])
            loaded[m["char"]] = (m["char"], m["kind"], path, m["margin_px"])   # 마스크 대신 경로(메모리 절약)
            (virt_set.add if m.get("virtual") else virt_set.discard)(m["char"])
    raw = list(loaded.values())
    print("읽은 글자 수:", len(raw), "| 다시 쓴 글자로 덮어쓴 것:", "".join(redone) or "없음")
    # 1차: 기본 굵기로 윤곽을 따서 그룹별 확대 비율을 정한다
    first = {}
    for ch, kind, path, mg in raw:
        _b = prep_mask(path); first[ch] = trace_mask(offset_mask(_b, BOLD_PX), mg) if _b is not None else None
    def med(kinds, only=None):
        hs = [bbox(first[ch])[3] - bbox(first[ch])[1] for ch, k, _, _ in raw if k in kinds and first[ch] and ch not in virt_set and (only is None or ch in only)]
        return float(np.median(hs)) if hs else None
    hh = med(("hangul",)) or med(("jamo",))
    dh = med(("latin",), only="0123456789")
    s_h = min(MAX_SCALE, HANGUL_H / hh) if hh else 1.0
    s_l = min(MAX_SCALE, DIGIT_H / dh) if dh else 1.0
    print(f"한글 중간 높이 {hh and round(hh)} -> 확대 x{s_h:.2f} | 숫자 중간 높이 {dh and round(dh)} -> 확대 x{s_l:.2f}")

    def eff_scale(ch, kind, cs):
        """원래 윤곽 -> 최종 윤곽의 실제 확대 비율(균일 확대라 높이비로 구한다)"""
        a0 = bbox(cs); a1 = bbox(finalize(ch, kind, cs, s_h, s_l)[0])
        r_h = (a1[3] - a1[1]) / max(a0[3] - a0[1], 1e-6)
        r_w = (a1[2] - a1[0]) / max(a0[2] - a0[0], 1e-6)
        return (r_h * r_w) ** 0.5     # 세로·가로 확대의 기하평균

    # 목표 굵기 = 지금 굵기들의 중간값(전체 느낌 유지)
    target = None
    if equal:
        ws = []
        for ch, kind, path, mg in raw:
            if ch in SKIP_EQ or ch in virt_set or not first[ch]: continue      # 조합 글자는 목표 계산에서 제외
            w = stroke_w(offset_mask(prep_mask(path), BOLD_PX))
            if w: ws.append(w * UPK * eff_scale(ch, kind, first[ch]))
        target = float(np.median(ws))
        print(f"굵기 보정: 목표 {target:.0f}단위 (보정 전 글자별 {min(ws):.0f}~{max(ws):.0f}, 표준편차 {np.std(ws):.1f})")

    built, radii = {}, {}
    for ch, kind, path, mg in raw:
        r = BOLD_PX
        cs = first[ch]
        if cs is None: continue
        big = prep_mask(path)
        if equal and ch not in SKIP_EQ:
            w0 = stroke_w(big)
            for _ in range(2 if ch in virt_set else 3):      # 부풀리면 글자 크기도 변해서 되풀이(조합 글자는 2번)
                k = eff_scale(ch, kind, cs)
                r = int(round((target / (k * UPK) - w0) / 2))
                r = max(EQ_R_MIN, min(EQ_R_MAX, r))
                nxt = trace_mask(offset_mask(big, r), mg)
                if not nxt: r = BOLD_PX; break
                cs = nxt
            if r != BOLD_PX: cs = trace_mask(offset_mask(big, r), mg) or first[ch]
        radii[ch] = r
        _cs, _adv = finalize(ch, kind, cs, s_h, s_l)
        built[ch] = (to_glyph(_cs), _adv); first[ch] = None; del big
    if equal:
        lim = [c for c, r in radii.items() if r in (EQ_R_MIN, EQ_R_MAX) and c not in SKIP_EQ]
        print(f"굵기 보정: 깎은 글자 {sum(1 for r in radii.values() if r < 0)}개, 부푼 글자 {sum(1 for r in radii.values() if r > BOLD_PX)}개, 한도에 걸린 글자 {len(lim)}개", "".join(lim[:40]))

    glyphs, metrics, cmap, order = {}, {}, {}, [".notdef", "space"]
    pen = TTGlyphPen(None)
    outer = [(60, -100), (60, 800), (740, 800), (740, -100)]
    inner = [(130, -30), (670, -30), (670, 730), (130, 730)]
    pen.moveTo(outer[0]); [pen.lineTo(p) for p in outer[1:]]; pen.closePath()
    pen.moveTo(inner[0]); [pen.lineTo(p) for p in inner[1:]]; pen.closePath()
    glyphs[".notdef"] = pen.glyph(); metrics[".notdef"] = 800
    glyphs["space"] = TTGlyphPen(None).glyph(); metrics["space"] = 450
    cmap[0x20] = "space"
    for ch, (gl, adv) in built.items():
        name = "uni%04X" % ord(ch)
        glyphs[name] = gl; metrics[name] = adv
        cmap[ord(ch)] = name; order.append(name)
    # 네가 쓰지 않은 한글은 자음·모음 부품으로 조합해서 채운다(환경변수 COMPOSE=all 또는 COMPOSE_CHARS=글자들)
    compose_chars = os.environ.get("COMPOSE_CHARS", "")
    if os.environ.get("COMPOSE") == "all": compose_chars = "".join(chr(c) for c in range(0xAC00, 0xD7A4))
    if compose_chars:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # 안전 모드(-I)에서도 같은 폴더의 compose.py를 찾게
        import compose
        parts = compose.load_parts(cells_dir)
        todo = [c for c in dict.fromkeys(compose_chars) if 0xAC00 <= ord(c) <= 0xD7A3 and c not in loaded]
        print("조합으로 채울 글자:", len(todo), "| 부품:", len(parts), "개")
        for ch in todo:
            cs = compose.canvas_to_contours(compose.compose_canvas(ch, parts, target if target else 46.0))
            if not cs: continue
            x0_, _, x1_, _ = bbox(cs); w_ = x1_ - x0_
            adv = max(1000, int(w_ + 90)); dx = (adv - w_) / 2 - x0_
            cs = transform(cs, lambda x, y, dx=dx: (x + dx, y))
            name = "uni%04X" % ord(ch)
            glyphs[name] = to_glyph(cs); metrics[name] = adv; cmap[ord(ch)] = name; order.append(name)
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef", "space"] + order[2:])
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    glyf = fb.font["glyf"]; hm = {}
    for n, g in glyphs.items():
        g.recalcBounds(glyf); hm[n] = (metrics[n], getattr(g, "xMin", 0) if g.numberOfContours else 0)
    fb.setupHorizontalMetrics(hm)
    fb.setupHorizontalHeader(ascent=880, descent=-240)
    fb.setupNameTable({"familyName": family, "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=880, sTypoDescender=-240, usWinAscent=1000, usWinDescent=300, sxHeight=480, sCapHeight=700)
    fb.setupPost(); fb.save(out_ttf)
    print("폰트 저장:", out_ttf, "| 글자 수:", len(cmap))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "MyHand", equal=os.environ.get("NO_EQUAL") is None)
